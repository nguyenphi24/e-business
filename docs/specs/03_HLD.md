# HLD — Thiết kế cấp cao ProcureHub

## 1. Phạm vi tài liệu

Tài liệu mô tả kiến trúc hiện thực hóa yêu cầu ở Phụ lục A và B.


## 2. Tóm tắt kiến trúc

ProcureHub là **modular monolith** đa tenant: một ứng dụng Django chia module theo domain, một database PostgreSQL dùng chung schema (shared schema, mỗi bản ghi gắn company sở hữu), một SPA React phục vụ cả Buyer Portal và Supplier Portal (menu theo vai trò). Realtime dùng **Server-Sent Events** đọc từ bảng `notifications`. Ba dịch vụ bên ngoài — cổng thanh toán, nhà cung cấp hóa đơn điện tử, dịch vụ ký số từ xa — được giả lập bằng một service riêng (**sandbox-service**), tích hợp qua API key và callback ký HMAC giống cách tích hợp nhà cung cấp thật.

Lý do chọn modular monolith thay vì microservices: nhóm 4 người, 4 tuần làm MVP, một database giao dịch cần tính nhất quán mạnh (duyệt lựa chọn → sinh PO → hóa đơn → thanh toán). Ranh giới module rõ ràng cho phép tách service sau này nếu tải tăng.

## 3. Sơ đồ ngữ cảnh (C4 mức 1)

```text
[Buyer / Manager / Finance]  --HTTPS-->  [ProcureHub]  <--HTTPS--  [Supplier]
                                              |
                                              +--API key / callback HMAC--  [sandbox-service: cổng thanh toán,
                                              |                               hóa đơn điện tử + cơ quan thuế, ký số + CA]
                                              +--(P2) email / ERP / nhà cung cấp thật
```

## 4. Sơ đồ container (C4 mức 2)

| Container | Công nghệ | Trách nhiệm |
|---|---|---|
| Web SPA | Vite + React 19 + React Router + Ant Design, nginx phục vụ tệp tĩnh | Buyer Portal, Supplier Portal, Finance; access token chỉ trong bộ nhớ; nhận SSE bằng `fetch` streaming |
| API | Django 5.2 + DRF, gunicorn `gthread` | REST `/api/v1`, SSE `/api/v1/notifications/stream`, webhook; auth JWT, RBAC, tenant scope, transaction |
| Database | PostgreSQL 16 | Dữ liệu giao dịch, audit, notification, idempotency |
| sandbox-service | Django + DRF, SQLite, trang HTML (repo riêng, cổng 28080) | Giả lập cổng thanh toán (trang thanh toán, IPN), hóa đơn điện tử (ký hiệu/số, cơ quan thuế cấp mã bất đồng bộ, tra cứu, XML), ký số từ xa (CA Ed25519, chứng thư theo MST, OTP) |

Luồng: Browser → HTTPS (nginx reverse proxy) → API → Auth & Tenant Guard → module domain → PostgreSQL.

## 5. Module backend

| Module (Django app) | Trách nhiệm | Thực thể chính |
|---|---|---|
| `identity` | User, company, vai trò, JWT, seed | Company, User, UserRole |
| `suppliers` | Quan hệ Buyer–Supplier, đánh giá NCC | SupplierRelationship, SupplierEvaluation |
| `procurement` | PR, RFQ, lời mời, báo giá, chấm điểm, lựa chọn; hiện chứa cả API của PO | PurchaseRequest, RFQ, RFQInvitation, Quotation, SupplierSelection |
| `purchase_orders` | PO, dòng PO, giao nhận | PurchaseOrder, PurchaseOrderLine, DeliveryRecord |
| `billing` (mới) | Hóa đơn (VAT 10%), công nợ, thanh toán, hóa đơn điện tử | Invoice, Payment, PaymentEvent |
| `integrations` (mới) | Adapter gọi sandbox-service, xác thực webhook HMAC, xác minh chữ ký số, ghim khóa CA | TrustAnchor |
| `notifications` (mới) | Inbox, quy tắc người nhận, SSE | Notification |
| `audit` | Audit trail append-only, scope truy cập, request ID | AuditEvent |
| `dashboard` | Truy vấn tổng hợp, pending action, KPI | (không có bảng riêng) |

Quy tắc phụ thuộc: module domain gọi `audit.services.audit()` và `notifications.services.notify_*()`; `notifications` và `audit` không import ngược module domain (trừ `audit.scope` dùng để lọc).

## 6. Mô hình dữ liệu khái niệm

```text
Company 1─* User 1─* UserRole
Company(BUYER) 1─* SupplierRelationship *─1 Company(SUPPLIER)
Company 1─* PurchaseRequest 1─* PurchaseRequestLine
PurchaseRequest 1─* RFQ 1─* RFQLine ; RFQ 1─* RFQInvitation *─1 Company(SUPPLIER)
RFQ 1─* Quotation 1─* QuotationLine ; Quotation 1─* QuotationRevision
RFQ 1─* SupplierSelection *─1 Quotation
SupplierSelection 1─1 PurchaseOrder 1─* PurchaseOrderLine 1─* DeliveryRecord
PurchaseOrder 1─* Invoice (tối đa 1 chưa hủy) 1─* Payment 1─* PaymentEvent
PurchaseOrder 1─0..1 SupplierEvaluation
Quotation 1─* QuotationSignature (tối đa 1 PENDING/SIGNED mỗi revision)
User 1─* Notification ; AuditEvent (actor, entity_type, entity_id, request_id)
```

## 7. Luồng sự kiện realtime

```text
1. API nhận POST /quotations/{id}/submit
2. transaction.atomic():
     cập nhật Quotation, lưu QuotationRevision
     ghi AuditEvent (kèm request_id)
     ghi Notification cho từng Buyer của company mua   ← cùng transaction
3. commit
4. Client Buyer đang mở GET /notifications/stream (fetch streaming, Bearer token)
   → generator mỗi 2 giây truy vấn Notification(recipient=user, id > last_id)
   → gửi "id: <id>\nevent: notification\ndata: {...}\n\n"
5. Client hiện badge + toast; nếu mất kết nối, nối lại với ?after=<id cuối>
6. Offline: đăng nhập lại → GET /notifications?unread=true
```

Vì Notification được ghi trong cùng transaction với thay đổi nghiệp vụ, bảng `notifications` đóng vai trò **outbox**: không có trường hợp đổi trạng thái thành công mà mất thông báo, và rollback thì không phát thông báo "ma". Mở rộng: thêm worker đọc outbox để gửi email/push khi cần.

Lựa chọn SSE thay vì WebSocket: luồng chỉ một chiều server → client, chạy trên HTTP thường, không cần Channels/Redis. Kết nối giới hạn 25 giây rồi đóng để không giữ thread gunicorn lâu; gunicorn tăng `threads` để đủ chỗ cho các kết nối song song.

## 8. Thanh toán, hóa đơn điện tử và ký số qua sandbox-service

Nguyên tắc chung: ProcureHub gọi nhà cung cấp qua adapter `SandboxClient` (header `X-Api-Key`), **ngoài** transaction; kết quả về bằng callback có `X-Sandbox-Signature` (HMAC-SHA256 trên raw body). Lỗi kết nối ghi `FAILED` và cho thử lại.

### 8.1 Thanh toán qua cổng

```text
Finance ──POST /invoices/{id}/payments (Idempotency-Key, amount)──> API
API: khóa Invoice, amount ≤ balance − pending → Payment PENDING (provider SANDBOX_GW) → commit
API ──POST /gateway/transactions──> sandbox → checkout_url
SPA chuyển trình duyệt tới checkout_url → người dùng chọn ngân hàng, kết quả
sandbox ──POST /webhooks/payment (IPN, HMAC)──> API → process_payment_event
sandbox ──302──> SPA /invoices?payment=... (chỉ để hiển thị, không ghi nhận tiền)
process_payment_event:
    PaymentEvent.get_or_create(event_id) → trùng thì trả duplicate
    khóa Invoice + Payment (select_for_update)
    PENDING → SUCCEEDED: paid_amount += amount; status PARTIALLY_PAID/PAID
    PENDING → FAILED: giữ số dư
    audit + notify Finance và Supplier
```

Thêm kiểm tra: `amount` trong IPN phải bằng số tiền Payment. Khi tắt tích hợp, nút mô phỏng nội bộ (`mock_provider`) dựng sự kiện và đi qua cùng `process_payment_event`.

Điều khoản Net N: `due_date = issued_at.date() + PO.payment_term_days` (mặc định 30). Overdue tính khi đọc, không cần cron.

### 8.2 Hóa đơn điện tử

```text
Supplier lập hóa đơn → issue_invoice: subtotal = tổng PO, VAT 10%, total = subtotal + VAT → commit
send_einvoice ──POST /einvoices──> sandbox (kiểm số học, cấp ký hiệu SBXyy + số, mã tra cứu)
    → einvoice_status PENDING_TAX_CODE
sau vài giây "cơ quan thuế" cấp mã ──POST /webhooks/einvoice──> apply_einvoice_event → ISSUED, thông báo
```

Ký hiệu, mã cơ quan thuế và XML cố ý mang dấu "giả lập" (tiền tố `SBX`, thẻ `HoaDonGiaLap`) để không bị nhầm với hóa đơn điện tử thật. Hóa đơn đã gửi cơ quan thuế không được hủy.

### 8.3 Ký số báo giá

```text
Supplier ──POST /quotations/{id}/sign──> API
API: document = quotation_document(q) (chuẩn hóa JSON), hash = SHA-256 → QuotationSignature PENDING
API ──POST /esign/requests (hash, MST người ký)──> sandbox → sign_url
Supplier mở sign_url, nhập OTP → sandbox ký hash bằng khóa của chứng thư theo MST (CA giả lập ký chứng thư)
sandbox ──POST /webhooks/esign──> apply_sign_event:
    xác minh chứng thư bằng khóa CA đã ghim (TrustAnchor) → đúng MST → còn hiệu lực → chữ ký khớp hash
    → SIGNED (hoặc FAILED kèm lý do), thông báo Buyer
Mỗi lần hiển thị: tính lại hash từ dữ liệu hiện tại; khác hash đã ký → INVALID
```

Ghim khóa CA lần đầu (trust on first use) đủ cho demo; với nhà cung cấp thật, khóa gốc của tổ chức chứng thực được cấu hình sẵn.

## 9. Bảo mật

| Lớp | Biện pháp |
|---|---|
| Xác thực | JWT access 15 phút trong bộ nhớ; refresh trong cookie httpOnly, SameSite=Lax, rotation + blacklist; kiểm tra Origin cho refresh/logout |
| Phân quyền chức năng | RBAC theo `UserRole`; permission class DRF + kiểm tra trong action |
| Phân quyền đối tượng | Queryset luôn lọc theo company/quan hệ; bản ghi ngoài scope trả 404 (chống IDOR) |
| Tách quyền | `actor != requester` (PR), `actor != proposed_by` (selection) |
| Toàn vẹn | `transaction.atomic()` + `select_for_update(of=("self",))`; Idempotency-Key cho sinh PO và tạo thanh toán; `event_id` unique cho webhook |
| Webhook | HMAC-SHA256 trên raw body, `hmac.compare_digest`; secret từ môi trường, không mặc định; IPN phải khớp số tiền |
| Chữ ký số | Chứng thư xác minh bằng khóa CA đã ghim, kiểm MST và thời hạn; tính lại mã băm mỗi lần hiển thị để phát hiện dữ liệu bị sửa |
| Tích hợp | Sandbox chỉ gọi lại / chuyển hướng về URL trong allowlist; API key bắt buộc khi bật tích hợp |
| Truy vết | AuditEvent append-only có `request_id`; header `X-Request-ID` trả về client |
| Dữ liệu | Thông báo không chứa giá; không log body/token/chữ ký; không lưu dữ liệu thẻ |

Lưu ý: System Admin đọc được toàn cục để hỗ trợ demo; production nên giới hạn bằng quyền hỗ trợ có thời hạn và audit riêng.

## 10. Triển khai

| Môi trường | Cấu hình |
|---|---|
| Local | Docker Compose PostgreSQL `localhost:45432`, backend `48000`, frontend `43000` |
| Production (skeleton) | Image backend (gunicorn) + image frontend (nginx) + PostgreSQL; `deploy/` tự chứa; secret qua `.env.prod` |
| sandbox-service | Repo riêng, cổng local `28080`, SQLite trên volume `/data`; image gunicorn non-root |
| Biến | `SANDBOX_WEBHOOK_SECRET` (bắt buộc, trùng hai bên), `SANDBOX_BASE_URL` (trống = tắt tích hợp), `SANDBOX_API_KEY` (bắt buộc khi bật), `CALLBACK_BASE_URL`, `FRONTEND_URL`, `PAYMENT_SANDBOX_ENABLED`, `NOTIFICATION_STREAM_MAX_SECONDS` |

Reverse proxy cần tắt buffering cho `/api/v1/notifications/stream` (API trả header `X-Accel-Buffering: no`).

Hạ tầng năm lớp (Chaffey, 2011): (I) ứng dụng — SPA + API; (II) phần mềm hệ thống — Linux, nginx, gunicorn, PostgreSQL, Docker; (III) truyền tải — HTTPS/TLS, REST, SSE; (IV) lưu trữ — máy ảo/CSDL managed trên cloud, sao lưu; (V) dữ liệu — tenant, giao dịch, hóa đơn, thanh toán, audit, thông báo.

## 11. Truy vết quyết định kinh doanh → kiến trúc

| Lập luận kinh doanh | Quyết định kiến trúc |
|---|---|
| Khác biệt hóa bằng minh bạch và tách quyền | RBAC + chống tự duyệt + audit append-only có request ID + module duyệt lựa chọn |
| SME nhạy cảm chi phí, cần dùng được ngay | Modular monolith, shared schema, Docker, không Redis/Kafka |
| NCC dùng miễn phí, extranet, value web | Supplier Portal trong cùng SPA, truy cập qua quan hệ mời |
| Bảo mật báo giá, giảm chi phí giám sát (TCE) | Object-level authorization, hạn chót theo giờ server, thông báo không chứa giá |
| Giảm chi phí tìm kiếm và so sánh | Báo giá có cấu trúc + chấm điểm trọng số công khai công thức |
| Giảm thời gian chờ giữa các bên | Notification inbox + SSE |
| Không thu phí giao dịch, không giữ tiền | Thanh toán đi qua cổng của đối tác (giả lập), nền tảng chỉ ghi nhận và đối soát IPN; không lưu dữ liệu thẻ |
| Đối tác chính: cổng thanh toán, hóa đơn điện tử (BMC, D8) | Adapter `SandboxClient` thay được bằng nhà cung cấp thật; callback HMAC chuẩn hóa |
| Bảo mật báo giá, chống chối bỏ | Ký số báo giá, xác minh chứng thư theo CA tin cậy, phát hiện dữ liệu bị sửa sau khi ký |
| Tri thức ẩn → tri thức hiện | Revision báo giá, score snapshot, lý do lựa chọn, đánh giá NCC, audit |
| Kiểm soát bằng KPI (BSC, SMART) | Trường thời điểm (`submitted_at`, `published_at`, `delivered_at`) và module dashboard tính KPI |

## 12. Rủi ro kỹ thuật

| Rủi ro | Giảm thiểu |
|---|---|
| Kết nối SSE chiếm thread | Giới hạn 25 giây/kết nối, tăng `threads`; mở rộng: ASGI |
| Proxy buffer làm trễ SSE | Header `X-Accel-Buffering: no`, `Cache-Control: no-cache` |
| Cộng tiền hai lần | `event_id` unique + khóa dòng + trạng thái cuối của Payment |
| Lộ dữ liệu chéo tenant | Scope queryset tập trung; test IDOR cho từng resource mới |
| Payment, hóa đơn, chữ ký bị hiểu là thật | Nhãn "giả lập" trên mọi trang, định dạng ký hiệu/mã/XML cố ý khác thật, không nhận dữ liệu thẻ |
| Dịch vụ ngoài chậm hoặc chết | Gọi ngoài transaction, timeout 5 giây, ghi `FAILED`, cho thử lại; tắt tích hợp vẫn chạy được |
| Mất callback | Trạng thái lưu ở cả hai bên; làm mới bằng API GET (HĐĐT) hoặc gửi lại IPN |
