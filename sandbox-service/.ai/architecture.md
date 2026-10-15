# Architecture

## Bối cảnh & yêu cầu gốc

ProcureHub cần minh họa tích hợp với cổng thanh toán, hóa đơn điện tử và chữ ký số mà không dùng dịch vụ thật. Yêu cầu: luồng giống thật (API key, trang của nhà cung cấp, callback ký HMAC, xử lý bất đồng bộ), dễ chạy local, không bị nhầm là có giá trị pháp lý.

## Sơ đồ tổng quan

```text
ProcureHub API --(X-Api-Key)--> /api/v1/... (sandbox)
Trình duyệt --> /gateway/checkout | /esign/sign | /einvoice/lookup (trang sandbox)
sandbox --(POST JSON + X-Sandbox-Signature HMAC-SHA256)--> ProcureHub /api/v1/webhooks/{payment,einvoice,esign}
sandbox --> SQLite (data/sandbox_service.db)
```

## Data model

| Bảng | Ghi chú |
|---|---|
| `gateway_transactions` | `merchant_ref` unique (idempotent khi merchant gọi lại); `last_event` giữ nguyên sự kiện đã gửi để `resend-ipn` gửi lại cùng `event_id` |
| `einvoices` | Unique `(symbol, number)`; `lookup_code` unique; trạng thái `PENDING_TAX_CODE → ISSUED` |
| `esign_ca` | Một bản ghi CA gốc (Ed25519) |
| `esign_certificates` | Một chứng thư cho mỗi MST, do CA ký (`ca_signature` trên JSON chuẩn hóa) |
| `esign_requests` | OTP 6 số, tối đa 3 lần sai thì `LOCKED`, hết hạn sau 15 phút |
| `callback_logs` | Mỗi lần gọi ngược về merchant: URL, `event_id`, mã HTTP, lỗi — không lưu body |

## Luồng chính

1. **Thanh toán:** merchant tạo giao dịch → nhận `checkout_url` → người dùng bấm kết quả → `gateway.services.complete()` chốt trạng thái (khóa dòng), gửi IPN `{event_id, external_ref, status, amount}` → redirect về `return_url?payment_ref=&status=`.
2. **Hóa đơn điện tử:** merchant gửi hóa đơn → `EInvoiceCreateSerializer.validate` kiểm tra số học (thành tiền, tổng, VAT 0/5/8/10%) → cấp ký hiệu/số → sau `EINVOICE_TAX_DELAY_SECONDS` cấp mã cơ quan thuế và callback.
3. **Ký số:** merchant gửi mã băm SHA-256 → người ký nhập OTP → ký mã băm bằng khóa của chứng thư theo MST → callback kèm chữ ký và chứng thư. Merchant xác minh bằng khóa CA lấy từ `GET /api/v1/esign/ca` (ghim một lần).

`core/callbacks.py` là nơi duy nhất gửi callback: chuẩn hóa JSON (`sort_keys`, không khoảng trắng), ký HMAC, kiểm tra allowlist, ghi `CallbackLog`.

## Response envelope

`core.renderers.CustomRenderer` bọc mọi response REST: `{"success": true, "data": ...}` hoặc `{"success": false, "error": {"code", "message", "details"}}`. Lỗi đi qua một chỗ duy nhất `core.exceptions.custom_exception_handler`. Trang HTML không qua DRF.

## Package layout

```text
backend/
  config/      settings (biến môi trường), urls (API + trang)
  core/        envelope, xử lý lỗi, logging che dữ liệu nhạy cảm, auth API key, callbacks, template gốc
  gateway/     cổng thanh toán
  einvoice/    hóa đơn điện tử
  esign/       CA, chứng thư, yêu cầu ký
```
