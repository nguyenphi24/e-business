# ProcureHub API

Base URL local: `http://127.0.0.1:48000/api/v1`

## Authentication

- `POST /auth/login` — body `{email, password}`; trả `access` và đặt refresh token vào httpOnly cookie.
- `POST /auth/refresh` — xoay refresh cookie, trả access token mới.
- `POST /auth/logout` — blacklist refresh token và xóa cookie.
- `GET /auth/me` — user, company và roles hiện tại.

Gửi access token bằng `Authorization: Bearer <token>`. API yêu cầu authentication mặc định; lỗi chưa đăng nhập trả HTTP 401.

Mọi response có header `X-Request-ID`. Client có thể gửi `X-Request-ID` (1–64 ký tự `A-Za-z0-9._-`) để nối log; giá trị không hợp lệ bị thay bằng ID mới. ID được lưu trong audit event.

Lỗi dùng shape `{code, message, field_errors}`. Mã lỗi: `invalid_transition` (409), `validation_error` (422), `permission_denied` (403), `separation_of_duties` (403), `not_found` (404), `deadline_passed` (409), `payment_exceeds_balance` (422), `sandbox_disabled` (403), `invalid_signature` (401), `amount_mismatch` (422), `integration_unavailable` (409), `integration_error` (502).

Vai trò: `BUYER`, `MANAGER`, `FINANCE`, `SUPPLIER`, `COMPANY_ADMIN`, `SYSTEM_ADMIN`. Bản ghi ngoài company scope trả 404.

## Purchase request

- `GET/POST /purchase-requests` — body tạo có thêm `estimated_budget` (tùy chọn, ≥ 0); response có `submitted_at`.
- `GET/PATCH /purchase-requests/{id}`
- `POST /purchase-requests/{id}/submit`
- `POST /purchase-requests/{id}/approve`
- `POST /purchase-requests/{id}/reject` — body bắt buộc `{reason}`.
- `POST /purchase-requests/{id}/cancel`

## Sourcing

- `GET /suppliers` — supplier relationship active trong company của buyer, kèm `rating_average` (1–5) và `rating_count`.
- `GET/POST /rfqs` — body tạo nhận `scoring_weights` tùy chọn `{price, delivery, rating, payment_terms}` (số nguyên 0–100, tổng 100; mặc định 45/25/20/10). Response có `scoring_weights`, `published_at`.
- `POST /rfqs/{id}/publish`, `/close`, `/cancel`, `/invitations`
- `POST /rfqs/{id}/scoring-weights` — Buyer; body `{scoring_weights: {...}}`; chỉ khi RFQ `DRAFT`/`OPEN`/`CLOSED`, sai tổng trả 422, sau `AWARDED` trả 409.
- `GET /rfqs/{id}/comparison` — trả `rfq`, `quotations` và `scoring` `{weights, formula, neutral_rating, results[]}`; mỗi result có `quotation_id`, `supplier`, `components {price, delivery, rating, payment_terms}`, `rating_available`, `total_score`, `rank`.
- `GET/POST /rfqs/{id}/quotation` — body nhận thêm `payment_term_days` (0–365).
- `POST /quotations/{id}/submit`, `/revise`; `PATCH /quotations/{id}` khi còn draft.
- `POST /quotations/{id}/sign` — Supplier sở hữu; báo giá `SUBMITTED`; cần bật tích hợp (`SANDBOX_BASE_URL`), không thì 409 `integration_unavailable`. Tạo (hoặc trả lại) yêu cầu ký cho revision hiện tại: `{id, status, revision, sign_url}`; mở `sign_url` để nhập OTP. Dịch vụ ký không phản hồi thì 502 `integration_error`.
- Quotation có khối `signature` cho revision hiện tại: `state` ∈ `UNSIGNED`, `PENDING`, `VALID`, `INVALID`, `REJECTED`, `FAILED`, `UNVERIFIABLE`; khi đã ký có `signer`, `signer_tax_code`, `certificate_serial`, `issuer`, `signed_at`; `INVALID` kèm `reason` (ví dụ nội dung bị sửa sau khi ký). `sign_url` chỉ trả cho Supplier sở hữu.
- `POST /rfqs/{id}/selection` — lưu `score_snapshot` (trọng số, điểm của báo giá được chọn, bảng xếp hạng).
- `POST /selections/{id}/approve`, `/reject`

## Purchase order

- `POST /purchase-orders/generate` — cần header `Idempotency-Key`.
- `POST /purchase-orders/{id}/issue`
- `POST /purchase-orders/{id}/acknowledge`
- `POST /purchase-orders/{id}/decline` — body reason khi cần.
- `POST /purchase-orders/{id}/deliveries`
- `POST /purchase-orders/{id}/complete`
- `POST /purchase-orders/{id}/cancel`
- `POST /purchase-orders/{id}/invoice` — Supplier của PO; chỉ khi PO `DELIVERED`/`COMPLETED`; body `{note?}`; trả hóa đơn (201). Đã có hóa đơn chưa hủy trả 409. Hóa đơn tính VAT 10%: `subtotal` = tổng PO, `vat_amount` = 10%, `total` = số phải trả. Nếu bật tích hợp, hệ thống gửi luôn sang nhà cung cấp hóa đơn điện tử.
- `POST /purchase-orders/{id}/evaluation` — Buyer/Manager/Company Admin; chỉ khi `COMPLETED`, một lần; body `{quality_score, delivery_score, comment?}` (1–5).

PO response có thêm `payment_term_days` (snapshot từ báo giá, mặc định 30), `delivered_at`, `invoice` (tóm tắt hóa đơn chưa hủy hoặc `null`), `evaluation`.

## Invoice và thanh toán sandbox

- `GET /invoices` — phân trang; lọc `status`, `overdue=true`. Bên mua thấy hóa đơn của company mình, Supplier thấy hóa đơn mình lập.
- `GET /invoices/{id}` — gồm `subtotal`, `vat_rate`, `vat_amount`, `total`, `paid_amount`, `balance`, `is_overdue`, `due_date`, `payment_term_days`, `einvoice {status, symbol, number, lookup_code, tax_code, lookup_url, xml_url, error}`, `payments[]`. `einvoice.status` ∈ `NOT_SENT`, `PENDING_TAX_CODE`, `ISSUED`, `FAILED`.
- `POST /invoices/{id}/cancel` — Supplier; chỉ khi `ISSUED`, không có payment chờ/thành công và hóa đơn điện tử chưa gửi cơ quan thuế (đã gửi thì 409).
- `POST /invoices/{id}/einvoice` — Supplier; phát hành lại khi `NOT_SENT`/`FAILED`, hoặc làm mới khi `PENDING_TAX_CODE`.
- `POST /invoices/{id}/payments` — Finance; header bắt buộc `Idempotency-Key`; body `{amount}`; tạo payment `PENDING`. Vượt (số dư − lệnh đang chờ) trả 422 `payment_exceeds_balance`. Gọi lại cùng key trả 200 với response cũ. Khi bật tích hợp: `provider = "SANDBOX_GW"`, response có `checkout_url` để chuyển người dùng sang cổng; cổng không phản hồi thì payment trả về `FAILED` (không giữ chỗ số dư). Khi tắt: `provider = "MOCK"`.
- `POST /payments/{id}/simulate` — Finance, chỉ cho payment `MOCK`; body `{outcome: "SUCCEEDED" | "FAILED"}`; chỉ khi server bật `PAYMENT_SANDBOX_ENABLED`, không thì 403 `sandbox_disabled`.

## Webhook từ nhà cung cấp (sandbox-service)

Không dùng JWT. Header `X-Sandbox-Signature` = hex HMAC-SHA256 của raw body với `SANDBOX_WEBHOOK_SECRET`; sai trả 401 `invalid_signature`.

- `POST /webhooks/payment` — IPN cổng thanh toán `{event_id, external_ref, status, amount?, failure_reason?}`. Cùng `event_id` lần hai trả `{duplicate: true}`; `amount` khác số tiền của payment trả 422 `amount_mismatch`; sự kiện mới cho payment đã chốt trả `{ignored: true}`.
- `POST /webhooks/einvoice` — kết quả cấp mã `{event_id, external_ref (= số hóa đơn), einvoice_id, status: "ISSUED", tax_code, symbol, number, lookup_code, lookup_url, xml_url}`; gọi lại khi đã `ISSUED` trả `{ignored: true}`.
- `POST /webhooks/esign` — kết quả ký `{event_id, external_ref (= id yêu cầu ký), status, document_hash, signature?, signed_at?, certificate?}`. Chỉ nhận chữ ký nếu chứng thư do CA tin cậy cấp, đúng MST nhà cung cấp, còn hiệu lực và chữ ký khớp mã băm; không thì yêu cầu ký thành `FAILED`.

Trạng thái hóa đơn: `ISSUED` → `PARTIALLY_PAID` → `PAID`; `CANCELLED`. Payment: `PENDING` → `SUCCEEDED`/`FAILED`.

## Notification

- `GET /notifications` — hộp thư của user hiện tại; `unread=true`, `limit` (1–100, mặc định 20). Trả `count`, `unread_count`, `results[]` `{id, event_type, entity_type, entity_id, title, payload {number, status, path}, read_at, created_at}`.
- `GET /notifications/unread-count`
- `POST /notifications/{id}/read`, `POST /notifications/read-all`
- `GET /notifications/stream` — Server-Sent Events (`text/event-stream`), xác thực bằng header Bearer. Nhận `?after=<id>` hoặc header `Last-Event-ID`; không truyền thì chỉ nhận thông báo mới. Mỗi sự kiện: `id: <id>`, `event: notification`, `data: <json như trên>`. Server gửi `: ping` khi rảnh và đóng kết nối sau `NOTIFICATION_STREAM_MAX_SECONDS` (mặc định 25); client nối lại với id cuối.

Nội dung thông báo không chứa giá báo giá.

## Monitoring

- `GET /health`
- `GET /dashboard` — counts (gồm `invoices`), `receivables {open_balance, overdue_count}`, pending actions, activity và `kpis` (bên mua; Supplier nhận `null`). Mỗi KPI `{value, n, unit, definition}`: `approval_lead_time_hours`, `rfq_response_time_hours`, `quote_participation_rate`, `procurement_cycle_time_days`, `on_time_delivery_rate`, `estimated_savings` (thêm `rate`).
- `GET /audit-events` — filter `action`, `entity_type`, `entity_id`, `from`, `to`, `limit`.
- `GET /docs` — Swagger UI.

Mọi mutation workflow kiểm tra role, company scope, state transition và ghi audit event. Chi tiết nghiệp vụ nằm trong `../../docs/specs/`.
