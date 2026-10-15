# API Reference — sandbox-service

Tài liệu cho hệ thống tích hợp (merchant). Hướng dẫn chạy repo ở [`../README.md`](../README.md).

- Base URL local: `http://127.0.0.1:28080`
- API dưới `/api/v1`; trang người dùng (HTML) ở `/gateway/`, `/einvoice/`, `/esign/`
- **Giả lập**: không có tiền thật, hóa đơn và chữ ký không có giá trị pháp lý.

## Response envelope

```json
{"success": true, "data": { ... }}
{"success": false, "error": {"code": "ValidationError", "message": "Request validation failed.", "details": {"ipn_url": ["ipn_url is not an allowed callback URL."]}}}
```

Thiếu hoặc sai API key trả HTTP 403 với `{"success": false, "error": {"detail": "Missing or invalid X-Api-Key."}}`.

## Quy ước chung

- Field `snake_case`; thời gian ISO 8601 có múi giờ; tiền là chuỗi thập phân 2 chữ số (`"1500000.00"`).
- Định danh công khai là UUID (`transaction_id`, `einvoice_id`, `request_id`). Merchant tự đặt mã tham chiếu (`merchant_ref`, `external_ref`); gọi tạo lại với cùng mã trả **200** và bản ghi cũ thay vì tạo trùng.

## Xác thực

- API merchant: header `X-Api-Key: <SANDBOX_API_KEY>`.
- Không cần key: `GET /api/v1/esign/ca`, `GET /health/`, các trang HTML.
- Callback từ sandbox về merchant: `POST` JSON, header `X-Sandbox-Signature` = hex HMAC-SHA256 của **raw body** với `SANDBOX_WEBHOOK_SECRET`. Body được tuần tự hóa `sort_keys`, không khoảng trắng, UTF-8.

## Mã lỗi

| Mã | HTTP | Khi nào |
|---|---|---|
| `ValidationError` | 400 | Thiếu field, sai số học hóa đơn, URL ngoài allowlist |
| (DRF `detail`) | 403 | Thiếu/sai `X-Api-Key` |
| `NotFound` / `Http404` | 404 | Không có bản ghi |
| `not_completed` | 409 | `resend-ipn` khi giao dịch chưa có kết quả |

## Cổng thanh toán

### `POST /api/v1/gateway/transactions`

```bash
curl -X POST http://127.0.0.1:28080/api/v1/gateway/transactions -H "X-Api-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"merchant_ref":"PAY-DOC-001","amount":"1500000","description":"Thanh toán INV-2026-0001",
       "return_url":"http://localhost:43000/invoices","ipn_url":"http://127.0.0.1:48000/api/v1/webhooks/payment"}'
```

```json
{"success":true,"data":{"transaction_id":"da1ec529-5915-4a0e-81c8-f07e38bf0bde","merchant_ref":"PAY-DOC-001","amount":"1500000.00","currency":"VND","status":"PENDING","checkout_url":"http://localhost:28080/gateway/checkout/da1ec529-5915-4a0e-81c8-f07e38bf0bde/","created_at":"2026-10-14T17:09:55.808183+00:00","completed_at":null}}
```

`ipn_url` phải nằm trong `ALLOWED_CALLBACK_PREFIXES`, `return_url` trong `ALLOWED_RETURN_PREFIXES`.

### Trang `GET|POST /gateway/checkout/<transaction_id>/`

Người dùng chọn ngân hàng và kết quả (thành công / thất bại / hủy). Sau đó sandbox gửi IPN rồi redirect `302` về `return_url?payment_ref=<merchant_ref>&status=<SUCCEEDED|FAILED|CANCELLED>`.

IPN gửi tới `ipn_url`:

```json
{"amount":"1500000.00","event_id":"evt_…","external_ref":"PAY-DOC-001","failure_reason":"","status":"SUCCEEDED","transaction_id":"da1ec529-…"}
```

`status` chỉ có `SUCCEEDED` hoặc `FAILED` (hủy cũng báo `FAILED`, kèm `failure_reason`).

### `GET /api/v1/gateway/transactions/<id>` — trạng thái hiện tại.

### `POST /api/v1/gateway/transactions/<id>/resend-ipn`

Gửi lại **đúng** sự kiện đã gửi (cùng `event_id`) để kiểm tra merchant xử lý trùng. Trả `{"event_id": "...", "callback_status": 200}`.

## Hóa đơn điện tử

### `POST /api/v1/einvoices`

```bash
curl -X POST http://127.0.0.1:28080/api/v1/einvoices -H "X-Api-Key: $KEY" -H 'Content-Type: application/json' -d '{
  "external_ref":"INV-DOC-001",
  "seller":{"tax_code":"0200000002","name":"TechVision"}, "buyer":{"tax_code":"0100000001","name":"VNPT Media"},
  "issue_date":"2026-10-15",
  "lines":[{"name":"Màn hình","unit":"cái","quantity":"10","unit_price":"4000000.00","amount":"40000000.00"}],
  "subtotal":"40000000.00","vat_rate":"10","vat_amount":"4000000.00","total":"44000000.00",
  "callback_url":"http://127.0.0.1:48000/api/v1/webhooks/einvoice"}'
```

```json
{"success":true,"data":{"einvoice_id":"fd65bf4d-fcd9-46a6-874a-5ce4e9c32bd7","external_ref":"INV-DOC-001","symbol":"SBX26","number":2,"lookup_code":"C400C63259","status":"ISSUED","tax_code":"SBX26-2C82F618C2EE22CE","subtotal":"40000000.00","vat_rate":"10.00","vat_amount":"4000000.00","total":"44000000.00","lookup_url":"http://localhost:28080/einvoice/lookup/?code=C400C63259","xml_url":"http://localhost:28080/einvoice/C400C63259/xml/","issued_at":"2026-10-14T17:09:55.851379+00:00"}}
```

(Ví dụ chạy với `EINVOICE_TAX_DELAY_SECONDS=0`. Mặc định 3 giây: response trả `status: "PENDING_TAX_CODE"`, `tax_code: ""`; khi cấp mã xong sandbox gọi `callback_url` với cùng shape trên kèm `event_id`.)

Kiểm tra bắt buộc: `amount = quantity × unit_price`, `subtotal = Σ amount`, `vat_amount = subtotal × vat_rate / 100` (làm tròn 0,01), `total = subtotal + vat_amount`, `vat_rate ∈ {0, 5, 8, 10}`. Sai một điều kiện trả 400, ví dụ `{"details":{"vat_amount":["Must equal subtotal × vat_rate / 100."]}}`.

- `GET /api/v1/einvoices/<id>` — trạng thái; nếu đã quá thời gian chờ mà chưa cấp mã thì cấp luôn.
- Trang `GET /einvoice/lookup/?code=<lookup_code>` — tra cứu công khai (watermark GIẢ LẬP).
- `GET /einvoice/<lookup_code>/xml/` — tải XML (thẻ gốc `HoaDonGiaLap`).

## Ký số từ xa

### `GET /api/v1/esign/ca`

```json
{"success":true,"data":{"issuer":"ProcureHub Sandbox CA (giả lập, không có giá trị pháp lý)","algorithm":"Ed25519","public_key":"bg5Gw8Jfii1q3WjmCfTBRO9fzc5JuldCizdEyB9LR1g="}}
```

Merchant ghim `public_key` (base64, 32 byte) làm khóa tin cậy để xác minh chứng thư.

### `POST /api/v1/esign/requests`

```bash
curl -X POST http://127.0.0.1:28080/api/v1/esign/requests -H "X-Api-Key: $KEY" -H 'Content-Type: application/json' -d '{
  "external_ref":"QS-DOC-001","signer":{"tax_code":"0200000002","name":"TechVision"},
  "document_hash":"9f2c1a7e4b8d3f6a0c5e2d9b7a4f1e8c3b6d0a9f2e5c8b1d4a7f0e3c6b9d2a5f",
  "document_label":"Báo giá RFQ-2026-0002 – TechVision (lần gửi 1)",
  "callback_url":"http://127.0.0.1:48000/api/v1/webhooks/esign"}'
```

```json
{"success":true,"data":{"request_id":"bcc9f25c-d1fa-419d-8152-e99f645b2d6b","external_ref":"QS-DOC-001","status":"PENDING","document_hash":"9f2c1a7e…","sign_url":"http://localhost:28080/esign/sign/bcc9f25c-d1fa-419d-8152-e99f645b2d6b/","expires_at":"2026-10-14T17:24:55.881428+00:00","signed_at":null}}
```

`document_hash` là SHA-256 hex chữ thường. Yêu cầu hết hạn sau 15 phút; sai OTP 3 lần thì `LOCKED`.

Trang `GET|POST /esign/sign/<request_id>/`: hiển thị OTP giả lập, người ký nhập OTP rồi bấm Ký hoặc Từ chối. Callback:

```json
{"event_id":"evt_…","external_ref":"QS-DOC-001","request_id":"…","status":"SIGNED","document_hash":"9f2c…",
 "signature":"<base64 Ed25519 trên 32 byte của document_hash>","signed_at":"2026-…",
 "certificate":{"serial":"…","issuer":"ProcureHub Sandbox CA (…)","subject":{"tax_code":"0200000002","name":"TechVision"},
   "algorithm":"Ed25519","public_key":"<base64>","valid_from":"…","valid_to":"…","ca_signature":"<base64>"}}
```

`status` khác `SIGNED`: `REJECTED`, `LOCKED`, `EXPIRED` (không có chữ ký). Xác minh: bỏ `ca_signature` khỏi `certificate`, chuẩn hóa JSON, kiểm bằng khóa CA; rồi kiểm `signature` bằng `certificate.public_key` trên `bytes.fromhex(document_hash)`.

- `GET /api/v1/esign/requests/<id>` — trạng thái yêu cầu.
