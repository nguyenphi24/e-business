# SRS — Đặc tả yêu cầu phần mềm ProcureHub

## 1. Phạm vi tài liệu

Tài liệu đặc tả hành vi phần mềm có thể kiểm thử, xuất phát từ yêu cầu ở Phụ lục A; kiến trúc ở Phụ lục C.

Công nghệ: backend Django 5.2 + Django REST Framework + JWT; frontend Vite + React 19 + React Router + Ant Design (SPA, không SSR); PostgreSQL 16. Không dùng Redis hay object storage trong MVP.


## 2. Vai trò và ma trận quyền

### 2.1 Ma trận quyền chức năng (mặc định)

| Tác vụ | Buyer | Manager | Finance | Supplier | Company Admin |
|---|---|---|---|---|---|
| Tạo/sửa/gửi PR | Có | — | — | — | Có |
| Duyệt/từ chối PR | — | Có¹ | — | — | — |
| Tạo RFQ, mời NCC, đặt trọng số, đóng RFQ | Có | — | — | — | Có |
| Gửi/sửa báo giá | — | — | — | Có² | — |
| Ký số báo giá (qua dịch vụ ký từ xa) | — | — | — | Có² | — |
| Xem bảng so sánh có điểm | Có | Có | — | — | Có |
| Đề xuất NCC | Có | — | — | — | Có |
| Duyệt lựa chọn NCC | — | Có¹ | — | — | — |
| Sinh và phát hành PO, ghi nhận giao hàng, hoàn tất | Có | — | — | — | Có |
| Hủy PO | Có | Có | — | — | Có |
| Xác nhận/từ chối PO | — | — | — | Có² | — |
| Lập/hủy hóa đơn, phát hành hóa đơn điện tử | — | — | — | Có² | — |
| Xem hóa đơn | Có | Có | Có | Có² | Có |
| Tạo lệnh thanh toán (qua cổng thanh toán) | — | — | Có | — | — |
| Đánh giá NCC | Có | Có | — | — | Có |
| Xem thông báo của mình | Có | Có | Có | Có | Có |

¹ Không được duyệt bản ghi do chính mình tạo hoặc đề xuất (`separation_of_duties`, 403).
² Chỉ với RFQ/PO/hóa đơn thuộc company của Supplier.
System Admin có quyền đọc toàn cục để hỗ trợ demo (lý do và giới hạn ở Phụ lục C mục 9).

### 2.2 Cô lập dữ liệu (object-level)

Mọi query được giới hạn theo company suy ra từ user đăng nhập (không tin `company_id` client gửi). Supplier được truy cập qua quan hệ `RFQInvitation`, `PurchaseOrder.supplier_company` hoặc `Invoice.supplier_company`. Truy cập bản ghi ngoài scope trả **404** (không xác nhận sự tồn tại).

## 3. Yêu cầu chức năng

### 3.0 Nhóm chức năng nền

| Nhóm | Yêu cầu chính |
|---|---|
| FR-AUTH | Đăng nhập email/mật khẩu; access JWT 15 phút trong bộ nhớ, refresh token trong cookie httpOnly có rotation; trả thông tin user, company, vai trò; đăng xuất thu hồi refresh token; từ chối user inactive và sai vai trò. |
| FR-ORG | Company Admin quản lý hồ sơ và người dùng company mình; mọi bản ghi nghiệp vụ có company sở hữu hoặc quan hệ rõ ràng. |
| FR-SUP | Buyer/Company Admin tạo hoặc kích hoạt quan hệ với NCC có sẵn; trạng thái invited, active, inactive, blocked. |
| FR-PR | Tạo, sửa, hủy PR nháp; gửi duyệt; Manager duyệt hoặc từ chối có lý do, không tự duyệt; chỉ PR đã duyệt tạo được RFQ. |
| FR-RFQ | Tạo RFQ từ PR đã duyệt, mời ≥ 2 NCC active, đặt hạn chót; publish, đóng (kể cả đóng sớm), hủy; hạn chót kiểm tra theo giờ máy chủ. |
| FR-QUO | NCC lưu nháp, gửi, sửa lại báo giá trước hạn; giá đủ mọi dòng; tổng tính bằng số thập phân ở máy chủ; khóa sau khi có quyết định lựa chọn. |
| FR-CMP | Bảng so sánh mọi báo giá đã gửi; Buyer đề xuất kèm lý do khi RFQ đã đóng; Manager duyệt/từ chối; chỉ lựa chọn đã duyệt mới sinh PO (idempotent). |
| FR-PO | Sinh PO từ lựa chọn đã duyệt; phát hành; NCC xác nhận/từ chối có lý do; ghi nhận giao từng phần hoặc đủ; hoàn tất; hủy theo trạng thái. |
| FR-DASH | Số liệu theo vai trò, việc cần xử lý, hoạt động gần đây, chỉ trong phạm vi quyền. |
| FR-AUD | Ghi người thực hiện, hành động, bản ghi, thời điểm cho thao tác quan trọng; lỗi API dùng chung một cấu trúc. |

Các yêu cầu chi tiết cho những chức năng mở rộng:

### 3.1 Purchase Request

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-PR-07 | PR có trường `estimated_budget` (Decimal ≥ 0, tùy chọn) dùng làm giá tham chiếu cho KPI tiết kiệm. | P1 |
| FR-PR-08 | Hệ thống lưu `submitted_at` mỗi lần submit để đo approval lead time. | P1 |

### 3.2 RFQ và chấm điểm báo giá

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-RFQ-07 | RFQ có `scoring_weights` gồm 4 tiêu chí `price`, `delivery`, `rating`, `payment_terms`; mặc định 45/25/20/10; nhận khi tạo RFQ hoặc qua endpoint riêng. | P0 |
| FR-RFQ-08 | Trọng số là số nguyên 0–100, tổng đúng 100; sai trả 422. Chỉ đổi khi RFQ ở `DRAFT`, `OPEN`, `CLOSED`. | P0 |
| FR-RFQ-09 | Lưu `published_at` khi publish để đo RFQ response time. | P1 |
| FR-RFQ-10 | NCC được mời xác nhận tham gia (`POST /rfqs/{id}/accept-invitation`) hoặc từ chối kèm lý do bắt buộc (`POST /rfqs/{id}/decline-invitation`) khi RFQ đang `OPEN`; trả lời lần hai trả 409. Mở chi tiết RFQ lần đầu chuyển lời mời sang `VIEWED`; gửi báo giá tự chuyển sang `ACCEPTED`. | P1 |
| FR-QUO-08 | Quotation có `payment_term_days` (số ngày công nợ đề nghị, số nguyên ≥ 0, tùy chọn). | P0 |
| FR-CMP-05 | `GET /rfqs/{id}/comparison` trả thêm khối `scoring`: trọng số, công thức, điểm thành phần và tổng điểm từng báo giá, xếp hạng. | P0 |
| FR-CMP-06 | Khi đề xuất NCC, hệ thống lưu `score_snapshot` (điểm và trọng số tại thời điểm đó) vào selection. | P0 |

### 3.3 Thông báo

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-NOTI-01 | Sự kiện nghiệp vụ tạo bản ghi `Notification` trong cùng transaction với thay đổi trạng thái. | P0 |
| FR-NOTI-02 | `GET /notifications` trả hộp thư của user hiện tại, lọc `unread=true`, phân trang. | P0 |
| FR-NOTI-03 | `GET /notifications/unread-count`, `POST /notifications/{id}/read`, `POST /notifications/read-all`. | P0 |
| FR-NOTI-04 | `GET /notifications/stream` là luồng Server-Sent Events; hỗ trợ `Last-Event-ID`/`?after=` để không mất thông báo khi kết nối lại. | P0 |
| FR-NOTI-05 | Nội dung thông báo chỉ gồm số chứng từ, loại sự kiện và tên công ty; không chứa giá. | P0 |

Bảng người nhận:

| Sự kiện | Người nhận |
|---|---|
| `PR_SUBMITTED` | Manager của company |
| `PR_APPROVED`, `PR_REJECTED` | Requester |
| `RFQ_PUBLISHED` | User Supplier của các company được mời |
| `INVITATION_ACCEPTED`, `INVITATION_DECLINED` | Buyer của company sở hữu RFQ |
| `QUOTATION_SUBMITTED` | Buyer của company sở hữu RFQ |
| `SELECTION_PROPOSED` | Manager của company |
| `SELECTION_APPROVED`, `SELECTION_REJECTED` | Người đề xuất |
| `PO_ISSUED`, `PO_CANCELLED` | User Supplier của company nhận PO |
| `PO_ACKNOWLEDGED`, `PO_DECLINED` | Buyer của company |
| `INVOICE_ISSUED` | Finance của company mua |
| `EINVOICE_ISSUED` | Finance của company mua và User Supplier của company bán |
| `QUOTATION_SIGNED` | Buyer của company sở hữu RFQ |
| `PAYMENT_SUCCEEDED`, `PAYMENT_FAILED` | Finance của company mua và User Supplier của company bán |

Actor không nhận thông báo về hành động của chính mình.

### 3.4 Hóa đơn và công nợ

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-INV-01 | Supplier lập hóa đơn cho PO của mình ở `DELIVERED` hoặc `COMPLETED`; tối đa một hóa đơn chưa hủy mỗi PO. | P1 |
| FR-INV-02 | Số hóa đơn `INV-YYYY-NNNN`; `subtotal` = tổng PO, `vat_rate` = 10, `vat_amount` = 10% `subtotal` (làm tròn 0,01), `total` = `subtotal` + `vat_amount`; `due_date` = ngày lập + `payment_term_days` của PO (mặc định 30). | P1 |
| FR-INV-03 | Hóa đơn có `paid_amount`, `balance`, cờ `is_overdue` (đến hạn mà còn số dư). | P1 |
| FR-INV-04 | Supplier hủy hóa đơn khi chưa có thanh toán thành công hoặc đang chờ, và hóa đơn điện tử chưa gửi cơ quan thuế. | P1 |
| FR-INV-05 | Danh sách hóa đơn lọc theo `status`, `overdue=true`. | P1 |

### 3.5 Thanh toán

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-PAY-01 | Finance tạo lệnh thanh toán `POST /invoices/{id}/payments` với `amount`, bắt buộc header `Idempotency-Key`; tạo Payment `PENDING`, `external_ref` duy nhất. Khi bật tích hợp: `provider = SANDBOX_GW`, gọi cổng thanh toán lấy `checkout_url`; cổng không phản hồi thì Payment `FAILED`. Khi tắt: `provider = MOCK`. | P1 |
| FR-PAY-02 | `amount` > 0 và ≤ số dư trừ các lệnh đang chờ; sai trả 422. | P1 |
| FR-PAY-03 | `POST /webhooks/payment` nhận IPN `{event_id, external_ref, status, amount?}`, xác thực HMAC-SHA256 qua header `X-Sandbox-Signature`; chữ ký sai trả 401; `amount` khác số tiền Payment trả 422. | P1 |
| FR-PAY-04 | Sự kiện trùng `event_id` trả 200 với `duplicate: true` và không đổi dữ liệu. | P1 |
| FR-PAY-05 | `SUCCEEDED` cộng vào `paid_amount` và chuyển hóa đơn sang `PARTIALLY_PAID`/`PAID`; `FAILED` không đổi số dư. Payment đã ở trạng thái cuối không đổi nữa. | P1 |
| FR-PAY-06 | `POST /payments/{id}/simulate` (Finance, chỉ Payment `MOCK`, chỉ khi `PAYMENT_SANDBOX_ENABLED=true`) mô phỏng kết quả khi không chạy cổng: xử lý qua cùng hàm với webhook. | P1 |

### 3.5a Tích hợp nhà cung cấp ngoài (giả lập)

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-INT-01 | Mọi lời gọi tới nhà cung cấp ngoài đi qua một adapter (`SandboxClient`) dùng `X-Api-Key`; đổi sang nhà cung cấp thật chỉ thay adapter. Không gọi mạng bên trong transaction. | P1 |
| FR-INT-02 | Cấu hình `SANDBOX_BASE_URL` trống thì tắt tích hợp; hệ thống vẫn hoạt động (nút mô phỏng thanh toán, không phát hành hóa đơn điện tử, không ký số). | P1 |
| FR-EINV-01 | Sau khi lập hóa đơn, hệ thống gửi hóa đơn (người bán, người mua, dòng hàng, trước thuế, VAT, tổng) sang nhà cung cấp hóa đơn điện tử; lưu ký hiệu, số, mã tra cứu, link tra cứu, link XML. | P1 |
| FR-EINV-02 | `POST /webhooks/einvoice` nhận kết quả cơ quan thuế cấp mã; lưu mã, chuyển `einvoice_status` sang `ISSUED`; thông báo Finance và Supplier. Gọi lại khi đã `ISSUED` thì bỏ qua. | P1 |
| FR-EINV-03 | Gửi lỗi thì `einvoice_status = FAILED`; Supplier phát hành lại hoặc làm mới bằng `POST /invoices/{id}/einvoice`. | P1 |
| FR-SIGN-01 | Supplier yêu cầu ký số báo giá `SUBMITTED` (`POST /quotations/{id}/sign`): hệ thống chuẩn hóa nội dung báo giá, tính SHA-256, gửi yêu cầu ký và trả `sign_url` để nhập OTP. | P1 |
| FR-SIGN-02 | `POST /webhooks/esign` chỉ chấp nhận chữ ký khi chứng thư do CA tin cậy (khóa CA được ghim lần đầu) ký, đúng mã số thuế nhà cung cấp, còn hiệu lực tại thời điểm ký, và chữ ký khớp mã băm; không thì yêu cầu ký `FAILED`. | P1 |
| FR-SIGN-03 | Báo giá trả khối `signature` cho revision hiện tại; trạng thái tính lại từ dữ liệu đang lưu mỗi lần đọc: `VALID` khi khớp, `INVALID` khi nội dung đã đổi sau khi ký. Bên mua thấy trạng thái, chỉ Supplier sở hữu thấy `sign_url`. | P1 |

### 3.6 Đánh giá nhà cung cấp

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-EVAL-01 | Buyer/Manager đánh giá PO `COMPLETED` một lần: `quality_score`, `delivery_score` (1–5), `comment`. | P1 |
| FR-EVAL-02 | `GET /suppliers` trả `rating_average`, `rating_count` theo company mua. | P1 |
| FR-EVAL-03 | Điểm uy tín dùng trong chấm điểm báo giá = trung bình (chất lượng + giao hàng)/2 các đánh giá của company mua dành cho NCC đó. | P1 |

### 3.7 Dashboard KPI

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-DASH-05 | Dashboard của bên mua trả khối `kpis` với 6 chỉ số ở mục 6, kèm định nghĩa và cỡ mẫu `n`. | P1 |
| FR-DASH-06 | Pending action bổ sung: Finance — hóa đơn chờ thanh toán/quá hạn; Supplier — PO đã giao chưa lập hóa đơn. | P1 |

### 3.8 Audit

| ID | Yêu cầu | Mức |
|---|---|---|
| FR-AUD-04 | Mỗi request có `X-Request-ID` (nhận từ client hoặc sinh mới), trả lại trong response header và lưu vào `AuditEvent.request_id`. | P0 |
| FR-AUD-05 | Webhook ghi audit với actor rỗng và `payload.source` (`payment_gateway`, `einvoice_provider`, `esign_provider`). | P1 |

## 4. State machine

### 4.0 Đối tượng mua sắm

```text
PR:         DRAFT --submit--> PENDING_APPROVAL --approve--> APPROVED
            PENDING_APPROVAL --reject--> REJECTED --sửa, gửi lại--> PENDING_APPROVAL
            DRAFT|REJECTED --cancel--> CANCELLED
RFQ:        DRAFT --publish--> OPEN --close/hết hạn--> CLOSED --Manager duyệt lựa chọn--> AWARDED
            DRAFT|OPEN --cancel--> CANCELLED
Lời mời:    INVITED --NCC mở RFQ--> VIEWED --xác nhận/gửi báo giá--> ACCEPTED
            INVITED|VIEWED --từ chối (có lý do)--> DECLINED
Quotation:  DRAFT --submit--> SUBMITTED --revise trước hạn--> DRAFT
            SUBMITTED --lựa chọn được duyệt--> AWARDED | NOT_SELECTED
Selection:  PROPOSED --approve--> APPROVED ; PROPOSED --reject--> REJECTED
            APPROVED --NCC từ chối PO--> REJECTED_BY_SUPPLIER
PO:         DRAFT --issue--> ISSUED --acknowledge--> ACKNOWLEDGED
            ISSUED --decline (có lý do)--> DECLINED
            ISSUED|ACKNOWLEDGED --giao một phần--> PARTIALLY_DELIVERED --giao đủ--> DELIVERED
            ISSUED|ACKNOWLEDGED --giao đủ một lần--> DELIVERED --complete--> COMPLETED
            DRAFT|ISSUED|ACKNOWLEDGED --cancel--> CANCELLED
```

### 4.1 Invoice

```text
(PO DELIVERED|COMPLETED) --supplier issue--> ISSUED
ISSUED --payment SUCCEEDED, còn số dư--> PARTIALLY_PAID
ISSUED|PARTIALLY_PAID --payment SUCCEEDED, hết số dư--> PAID
ISSUED --supplier cancel (không có payment PENDING/SUCCEEDED)--> CANCELLED
is_overdue = status ∈ {ISSUED, PARTIALLY_PAID} và due_date < hôm nay (UTC)
```

`PAID` và `CANCELLED` là trạng thái kết thúc. "Overdue" là thuộc tính suy ra, không phải trạng thái lưu, để không cần job định kỳ.

### 4.2 Payment

```text
PENDING --IPN SUCCEEDED--> SUCCEEDED
PENDING --IPN FAILED (thất bại hoặc người dùng hủy)--> FAILED
PENDING --không tạo được giao dịch ở cổng--> FAILED
```

### 4.2a Hóa đơn điện tử và chữ ký báo giá

```text
einvoice_status: NOT_SENT --gửi được--> PENDING_TAX_CODE --callback cấp mã--> ISSUED
                 NOT_SENT|PENDING_TAX_CODE --lỗi kết nối--> FAILED --phát hành lại--> PENDING_TAX_CODE|ISSUED
QuotationSignature: PENDING --chữ ký hợp lệ--> SIGNED
                    PENDING --từ chối / khóa OTP / hết hạn--> REJECTED
                    PENDING --chứng thư hoặc chữ ký không hợp lệ--> FAILED
Hiển thị (tính lại mỗi lần đọc): SIGNED + mã băm hiện tại khớp → VALID; lệch → INVALID
```

### 4.3 Đối chiếu thuật ngữ nghiệp vụ với trạng thái hệ thống

| Đối tượng | Thuật ngữ nghiệp vụ thường dùng | ProcureHub |
|---|---|---|
| PR | Draft → PendingApproval → Approved/Rejected → Converted/Cancelled | `DRAFT → PENDING_APPROVAL → APPROVED/REJECTED`, `CANCELLED`; "Converted" suy ra khi PR có RFQ |
| RFQ | Draft → Open → Closed/Cancelled | thêm `AWARDED` khi Manager duyệt lựa chọn |
| Quotation | Draft → Submitted → Withdrawn/Accepted/Rejected | `DRAFT → SUBMITTED → AWARDED/NOT_SELECTED`; rút lại = `revise` về `DRAFT` |
| PO | Issued → Confirmed/Declined → PartiallyDelivered → Delivered → Closed | `DRAFT → ISSUED → ACKNOWLEDGED/DECLINED → PARTIALLY_DELIVERED → DELIVERED → COMPLETED`, `CANCELLED` |
| Invoice | Draft → Issued → PartiallyPaid → Paid/Overdue/Cancelled | `ISSUED → PARTIALLY_PAID → PAID`, `CANCELLED`; overdue là cờ |

## 5. Thuật toán chấm điểm báo giá

Với mỗi báo giá `i` đã nộp của một RFQ:

| Tiêu chí | Điểm thành phần (0–100) | Dữ liệu nguồn |
|---|---|---|
| Giá | `S_price = 100 × P_min / P_i` (nếu `P_i = 0` thì 100) | `total` (trước VAT) |
| Giao hàng | `S_delivery = 100 × (D_min + 1) / (D_i + 1)`; thiếu `delivery_days` thì 0 | `delivery_days` |
| Uy tín | `S_rating = 100 × R_i / 5`; NCC chưa có đánh giá dùng 60 (tương đương 3/5) và gắn cờ | đánh giá NCC của company mua |
| Điều khoản | `S_terms = 100 × T_i / T_max` (nếu `T_max = 0` thì mọi báo giá 100); thiếu `payment_term_days` thì 0 | `payment_term_days` |

`Tổng = (w_price·S_price + w_delivery·S_delivery + w_rating·S_rating + w_terms·S_terms) / 100`, làm tròn 2 chữ số, xếp hạng giảm dần. `+1` ở công thức giao hàng tránh chia cho 0 khi có NCC giao ngay trong ngày. Điểm là thông tin hỗ trợ: Buyer vẫn phải ghi lý do và Manager vẫn phải duyệt.

## 6. Định nghĩa KPI dashboard

| KPI | Định nghĩa | Nguồn |
|---|---|---|
| `approval_lead_time_hours` | Trung vị (`decided_at` − `submitted_at`) của PR đã duyệt/từ chối | PR |
| `rfq_response_time_hours` | Trung vị (lần nộp đầu của báo giá − `published_at` của RFQ) | QuotationRevision 1, RFQ |
| `quote_participation_rate` | Số lời mời đã có báo giá nộp / số lời mời của RFQ đã publish | RFQInvitation |
| `procurement_cycle_time_days` | Trung vị (`issued_at` của PO − `submitted_at` của PR gốc) | PO, PR |
| `on_time_delivery_rate` | PO có `delivered_at` ≤ `issued_at + delivery_days` / PO đã giao đủ | PO |
| `estimated_savings` | Σ (`estimated_budget` − tổng PO) trên các PO có PR khai báo ngân sách; kèm tỷ lệ % | PO, PR |

Dùng trung vị vì cỡ mẫu nhỏ và có ngoại lệ. Mỗi KPI trả cả `n`. Số liệu demo là dữ liệu seed, không phải kết quả nghiên cứu.

## 7. Dữ liệu

Thực thể nền: Company, User/UserRole, SupplierRelationship, PurchaseRequest (+Line), RFQ (+Line, Invitation), Quotation (+Line, Revision), SupplierSelection, PurchaseOrder (+Line), DeliveryRecord, AuditEvent, DocumentSequence, IdempotencyKey. Trường và bảng phục vụ các chức năng mở rộng:

| Thực thể / cột | Trường |
|---|---|
| `purchase_requests` | `estimated_budget`, `submitted_at` |
| `rfqs` | `scoring_weights` (JSON), `published_at` |
| `quotations` | `payment_term_days` |
| `supplier_selections` | `score_snapshot` (JSON) |
| `purchase_orders` | `payment_term_days`, `delivered_at` |
| `audit_events` | `request_id` |
| `notifications` (mới) | `id` (tự tăng, dùng làm SSE event id), `recipient_id`, `company_id`, `event_type`, `entity_type`, `entity_id`, `title`, `payload`, `read_at`, `created_at` |
| `invoices` (mới) | `id`, `number`, `purchase_order_id`, `buyer_company_id`, `supplier_company_id`, `status`, `currency`, `subtotal`, `vat_rate`, `vat_amount`, `total`, `paid_amount`, `issued_at`, `due_date`, `issued_by_id`, `cancelled_at`, `einvoice_status`, `einvoice_id`, `einvoice_symbol`, `einvoice_number`, `einvoice_lookup_code`, `einvoice_tax_code`, `einvoice_lookup_url`, `einvoice_xml_url`, `einvoice_error` |
| `payments` (mới) | `id`, `invoice_id`, `amount`, `status`, `provider` (`MOCK`/`SANDBOX_GW`), `external_ref` (unique), `gateway_transaction_id`, `checkout_url`, `created_by_id`, `settled_at`, `failure_reason` |
| `quotation_signatures` (mới) | `id`, `quotation_id`, `revision`, `document_hash`, `status`, `sign_request_id`, `sign_url`, `signature`, `certificate` (JSON), `signed_at`, `failure_reason`, `requested_by_id`; duy nhất một chữ ký `PENDING`/`SIGNED` cho mỗi revision |
| `trust_anchors` (mới) | `name` (unique), `issuer`, `public_key` — khóa CA được ghim |
| `payment_events` (mới) | `event_id` (unique), `payment_id`, `status`, `payload`, `received_at`, `duplicate_count` |
| `supplier_evaluations` (mới) | `purchase_order_id` (unique), `buyer_company_id`, `supplier_company_id`, `quality_score`, `delivery_score`, `comment`, `evaluated_by_id` |

## 8. API của chức năng mở rộng

Base `/api/v1/`, JSON, lỗi dùng chung cấu trúc `{code, message, field_errors}`; mã lỗi nền: `invalid_transition` (409), `validation_error` (422), `permission_denied` (403), `separation_of_duties` (403), `not_found` (404), `deadline_passed` (409).

| Method / endpoint | Vai trò | Ý nghĩa |
|---|---|---|
| `POST /rfqs/{id}/scoring-weights` | Buyer | Đặt trọng số |
| `POST /rfqs/{id}/accept-invitation` | Supplier được mời | Xác nhận tham gia báo giá |
| `POST /rfqs/{id}/decline-invitation` | Supplier được mời | Từ chối lời mời, `reason` bắt buộc |
| `GET /rfqs/{id}/comparison` | Buyer, Manager | Thêm khối `scoring` |
| `GET /notifications` | Mọi user | Hộp thư; `?unread=true` |
| `GET /notifications/unread-count` | Mọi user | Số chưa đọc |
| `POST /notifications/{id}/read`, `POST /notifications/read-all` | Mọi user | Đánh dấu đã đọc |
| `GET /notifications/stream` | Mọi user | SSE (`text/event-stream`) |
| `GET /invoices`, `GET /invoices/{id}` | Bên mua, Supplier | Danh sách/chi tiết |
| `POST /purchase-orders/{id}/invoice` | Supplier | Lập hóa đơn |
| `POST /invoices/{id}/cancel` | Supplier | Hủy hóa đơn |
| `POST /invoices/{id}/payments` | Finance | Lệnh thanh toán sandbox (Idempotency-Key) |
| `POST /payments/{id}/simulate` | Finance | Mô phỏng kết quả cổng |
| `POST /quotations/{id}/sign` | Supplier | Yêu cầu ký số báo giá, trả `sign_url` |
| `POST /invoices/{id}/einvoice` | Supplier | Phát hành lại / làm mới hóa đơn điện tử |
| `POST /webhooks/payment` | Cổng thanh toán (HMAC) | IPN idempotent |
| `POST /webhooks/einvoice` | Nhà cung cấp HĐĐT (HMAC) | Kết quả cấp mã |
| `POST /webhooks/esign` | Dịch vụ ký số (HMAC) | Kết quả ký |
| `POST /purchase-orders/{id}/evaluation` | Buyer, Manager | Đánh giá NCC |

Mã lỗi mới: `invalid_signature` (401), `payment_exceeds_balance` (422), `sandbox_disabled` (403), `amount_mismatch` (422), `integration_unavailable` (409), `integration_error` (502).

## 9. Yêu cầu phi chức năng

| ID | Yêu cầu | Cách kiểm tra |
|---|---|---|
| NFR-SEC-01 | Mật khẩu dùng password hasher chuẩn của Django. | Kiểm tra cấu hình |
| NFR-SEC-02 | Access token trong bộ nhớ, refresh token cookie httpOnly có rotation; không dùng localStorage. | Test xác thực |
| NFR-SEC-03 | Mọi đọc/ghi kiểm tra phạm vi company hoặc quan hệ. | Test truy cập chéo |
| NFR-SEC-04 | Môi trường triển khai dùng HTTPS, secret từ biến môi trường. | Checklist triển khai |
| NFR-PERF-01 | p95 API danh sách/chi tiết dưới 500 ms trên dữ liệu demo. | Smoke test |
| NFR-REL-01 | Chuyển trạng thái sai trả lỗi xác định, không ghi dở dang. | Test transaction |
| NFR-REL-02 | Thao tác quan trọng chạy trong transaction, idempotent khi quy định. | Test gửi trùng |
| NFR-AUD-01 | Mốc thời gian audit theo UTC, audit chỉ ghi thêm. | Test audit |
| NFR-SEC-05 | Ngăn IDOR cho notification, invoice, payment: bản ghi ngoài scope trả 404. | Test truy cập chéo tenant |
| NFR-SEC-06 | Webhook xác thực HMAC-SHA256 so sánh hằng thời gian; secret `SANDBOX_WEBHOOK_SECRET` bắt buộc, không có giá trị mặc định; bật tích hợp thì `SANDBOX_API_KEY` bắt buộc. | Test chữ ký sai; khởi động thiếu biến |
| NFR-SEC-08 | Chữ ký số xác minh bằng khóa CA đã ghim, không tin khóa đi kèm callback; dịch vụ ngoài chỉ được gọi lại các URL nằm trong danh sách cho phép. | Test CA giả, sai MST |
| NFR-REL-06 | Không gọi mạng bên trong transaction; lỗi kết nối ghi trạng thái `FAILED` và cho thử lại, không giữ chỗ số dư. | Test dịch vụ ngoài không phản hồi |
| NFR-SEC-07 | Không log body request/response, token, chữ ký. | Review cấu hình log |
| NFR-REL-03 | Webhook idempotent theo `event_id`; tạo lệnh thanh toán idempotent theo `Idempotency-Key`. | Test gửi trùng |
| NFR-REL-04 | Thay đổi số dư hóa đơn trong transaction có khóa dòng hóa đơn (`select_for_update`). | Acceptance PostgreSQL |
| NFR-REL-05 | Mất kết nối SSE không mất thông báo: thông báo nằm trong DB, client nối lại bằng `after=<id cuối>`. | Test REST sau khi stream đóng |
| NFR-PERF-03 | Thông báo đến client ≤ 5 giây (chu kỳ poll 2 giây phía server). | Demo hai trình duyệt |
| NFR-OPS-01 | Kết nối SSE tự đóng sau tối đa 25 giây để không giữ worker; client tự nối lại. | Cấu hình `NOTIFICATION_STREAM_MAX_SECONDS` |

## 10. Tiêu chí nghiệm thu API

1. Đặt trọng số tổng ≠ 100 trả 422.
2. Bảng so sánh: báo giá rẻ nhất có `S_price = 100`; tổng điểm khớp công thức.
3. Supplier không được mời gọi comparison/notification của RFQ khác không thấy dữ liệu.
4. `GET /notifications` của user A không chứa thông báo của user B.
5. Lập hóa đơn khi PO chưa giao trả 409 `invalid_transition`.
6. Thanh toán vượt số dư trả 422 `payment_exceeds_balance`.
7. Webhook sai chữ ký trả 401; gửi lại cùng `event_id` không cộng tiền hai lần.
8. Thanh toán 30% → `PARTIALLY_PAID`, phần còn lại → `PAID`, `balance = 0`.
9. Đánh giá PO chưa `COMPLETED` trả 409; đánh giá lần hai trả 409.
10. Hóa đơn: `subtotal` = tổng PO, `vat_amount` = 10%, `total` = trước thuế + VAT; dữ liệu gửi nhà cung cấp HĐĐT có tổng dòng = `subtotal`.
11. Callback cấp mã HĐĐT chuyển `einvoice_status` sang `ISSUED`; gửi lại bị bỏ qua; hóa đơn đã có mã không hủy được (409).
12. Chữ ký báo giá hợp lệ → `VALID`; sửa giá trực tiếp trong DB → `INVALID`; chữ ký từ CA lạ hoặc sai MST → `FAILED`.
13. Cổng thanh toán không phản hồi → Payment `FAILED`, vẫn tạo được lệnh mới cho toàn bộ số dư.

## 11. Ràng buộc

Không thêm Kafka, Celery, Redis hay microservices trong MVP. Cổng thanh toán, hóa đơn điện tử và ký số chỉ kết nối dịch vụ giả lập (`sandbox-service`); kết nối nhà cung cấp thật là P2. Outbox/worker riêng là hướng mở rộng (Phụ lục C mục 7).

## 12. Trạng thái triển khai

Xem Phụ lục D mục 4.
