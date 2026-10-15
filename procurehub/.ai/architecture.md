# Architecture

## Components

- `backend/`: Django project, REST API, JWT authentication và domain apps.
- `frontend/`: Vite + React SPA; gọi API bằng `frontend/lib/api.ts`.
- PostgreSQL: database chính trong local Docker Compose.

Backend apps: `integrations` (adapter `SandboxClient`, HMAC webhook, xác minh chữ ký Ed25519, `TrustAnchor`), `identity`, `suppliers` (quan hệ + `SupplierEvaluation`), `procurement` (PR, RFQ, quotation, selection, `scoring.py`; hiện chứa cả API của PO), `purchase_orders`, `billing` (Invoice, Payment, PaymentEvent, mock provider, webhook), `notifications` (inbox, quy tắc người nhận, SSE), `audit` (`services.audit()`, scope), `dashboard` (`kpis.py`).

## Domain flow

1. Buyer tạo và submit Purchase Request.
2. Manager approve hoặc reject request.
3. Buyer tạo RFQ từ request đã approve, mời supplier và publish.
4. Supplier tạo, submit hoặc revise quotation.
5. Buyer lập selection từ comparison; Manager approve selection.
6. Buyer generate và issue PO; supplier acknowledge/decline; buyer ghi delivery và complete.
7. Supplier lập hóa đơn cho PO `DELIVERED`/`COMPLETED`; `due_date = issued_at + PO.payment_term_days` (Net N, mặc định 30).
8. Finance tạo payment `PENDING` (Idempotency-Key) → cổng giả lập hoặc webhook HMAC gửi sự kiện → `billing.services.process_payment_event()` cập nhật số dư (`PARTIALLY_PAID`/`PAID`). `event_id` unique làm webhook idempotent; payment đã ở trạng thái cuối bỏ qua sự kiện mới.
9. Buyer/Manager đánh giá NCC sau PO `COMPLETED`; điểm trung bình dùng làm tiêu chí uy tín trong `procurement.scoring`.
10. Mọi mutation ghi `AuditEvent` (kèm `request_id` từ `RequestIdMiddleware`); dashboard, audit, invoice, payment lọc theo company scope trong `audit/scope.py`.

## Notification và SSE

`notifications.services.notify_event(event_type, entity, actor)` chứa bảng người nhận (SRS mục 3.3) và được gọi trong cùng transaction với thay đổi trạng thái, nên bảng `notifications` đóng vai trò outbox. `GET /api/v1/notifications/stream` là view Django thuần: xác thực Bearer bằng `JWTAuthentication`, poll DB mỗi `NOTIFICATION_STREAM_POLL_SECONDS`, đóng sau `NOTIFICATION_STREAM_MAX_SECONDS` để không giữ thread gunicorn; client nối lại với `?after=<id>`. Frontend đọc bằng `fetch` streaming (không dùng EventSource vì phải gửi header Authorization).

## Tích hợp nhà cung cấp ngoài (sandbox-service)

Repo `../sandbox-service` giả lập cổng thanh toán, hóa đơn điện tử và ký số. ProcureHub chỉ nói chuyện qua `apps/integrations/client.py` (đổi sang nhà cung cấp thật thì thay adapter). Mọi lời gọi mạng nằm **ngoài** transaction; kết quả về qua `apps/integrations/webhooks.py` (HMAC `X-Sandbox-Signature`).

- **Thanh toán:** `billing.api.payments` tạo Payment `PENDING` (provider `SANDBOX_GW`) → `services.start_gateway_payment()` lấy `checkout_url` → IPN vào `process_payment_event()` (idempotent theo `event_id`, kiểm `amount`).
- **Hóa đơn + VAT:** `issue_invoice()` tính VAT 10% (`subtotal` = tổng PO). Sau commit, `send_einvoice()` gửi hóa đơn; callback `apply_einvoice_event()` ghi mã cơ quan thuế. Hóa đơn đã gửi cơ quan thuế không hủy được.
- **Ký số báo giá:** `procurement/esign.py` chuẩn hóa nội dung báo giá (`quotation_document`) → SHA-256 → yêu cầu ký. Callback chỉ được chấp nhận khi chứng thư do CA đã ghim (`TrustAnchor`, lấy lần đầu từ `GET /esign/ca`) ký, đúng MST, còn hiệu lực, chữ ký khớp mã băm. `signature_summary()` tính lại mã băm từ dữ liệu hiện tại mỗi lần hiển thị nên phát hiện được dữ liệu bị sửa trực tiếp trong DB (lệnh demo: `manage.py demo_tamper_quotation`).

## Chấm điểm báo giá

`procurement/scoring.py` là hàm thuần (không DB). Comparison trả khối `scoring`; selection lưu `score_snapshot`. Trọng số lưu ở `RFQ.scoring_weights`, đổi được tới trước `AWARDED`.

## Isolation and authorization

Company scope được suy ra từ user/company relationship, không tin company id do client gửi. Supplier chỉ thấy RFQ được mời hoặc có quan hệ active. Các transition được kiểm tra ở API layer trước khi ghi database.

## Transaction gotcha

Các mutation workflow dùng `transaction.atomic()` và khóa object chính bằng `select_for_update(of=("self",))`. PostgreSQL sẽ lỗi nếu khóa luôn phía nullable của outer join do `select_related`; SQLite không bắt lỗi này nên acceptance PostgreSQL là bắt buộc.

## Source documents

Tài liệu nghiệp vụ: `../docs/specs/01_URD.md`, `02_SRS.md`, `03_HLD.md`, `04_Test_Demo.md` — nguồn chuẩn khi mâu thuẫn với code.
