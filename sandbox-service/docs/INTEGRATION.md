# Integration Guide — sandbox-service

Chi tiết từng endpoint ở [`API.md`](API.md); file này nói về cách ghép nối và chỗ dễ sai.

## 0. Service này là gì / không phải gì

- **Là:** đồ giả lập cổng thanh toán, nhà cung cấp hóa đơn điện tử (kèm cơ quan thuế cấp mã) và dịch vụ ký số từ xa, đủ giống luồng thật để demo và test tích hợp.
- **Không phải:** cổng thanh toán, hóa đơn điện tử hay chữ ký số có giá trị pháp lý. Không xử lý tiền, không nhận dữ liệu thẻ, không kết nối cơ quan thuế, chứng thư không phải X.509 và không do tổ chức chứng thực nào cấp.

## 1. Base URL & môi trường

| Môi trường | Base URL |
|---|---|
| Local | `http://127.0.0.1:28080` |
| Production | Theo `PUBLIC_BASE_URL` khi triển khai (chưa triển khai) |

## 2. Xác thực

Merchant gửi `X-Api-Key`. Không có token, không hết hạn; đổi key = đổi biến môi trường ở cả hai bên. Callback về merchant ký HMAC-SHA256 (`X-Sandbox-Signature`) — merchant **phải** kiểm chữ ký trên raw body trước khi parse JSON, và so sánh bằng hàm hằng thời gian.

## 3. Phân quyền

Một merchant duy nhất (một API key). Trang người dùng không đăng nhập: ai có link trang thanh toán/ký thì thao tác được — chấp nhận cho sandbox; dịch vụ thật sẽ xác thực người ký/người trả tiền.

## 4. Luồng tích hợp điển hình

1. **Thanh toán:** tạo giao dịch → chuyển trình duyệt tới `checkout_url` → nhận IPN (nguồn sự thật) → người dùng quay về `return_url` (chỉ để hiển thị; đừng ghi nhận tiền từ query string).
2. **Hóa đơn điện tử:** gửi hóa đơn ngay sau khi lập → lưu `einvoice_id`, ký hiệu, số, mã tra cứu → chờ callback cấp mã (hoặc gọi `GET` để làm mới).
3. **Ký số:** tính SHA-256 trên nội dung chuẩn hóa → tạo yêu cầu ký → mở `sign_url` cho người ký → nhận callback → xác minh chứng thư bằng khóa CA đã ghim và chữ ký trên mã băm → lưu. Khi hiển thị, tính lại mã băm từ dữ liệu hiện tại để phát hiện dữ liệu bị sửa sau khi ký.

Merchant phải xử lý idempotent: IPN có thể đến nhiều lần cùng `event_id`, và sự kiện mới cho giao dịch đã chốt cần bỏ qua.

## 5. Xử lý lỗi — bảng ánh xạ cho client

| HTTP | Mã lỗi | Client nên làm |
|---|---|---|
| 400 | `ValidationError` | Sửa dữ liệu theo `details` (thường là sai số học hóa đơn hoặc URL ngoài allowlist) |
| 403 | — | Kiểm tra `X-Api-Key` |
| 404 | — | Mã định danh sai |
| 409 | `not_completed` | Giao dịch chưa có kết quả, chưa gửi lại IPN được |
| Lỗi mạng | — | Đánh dấu thất bại ở phía merchant, cho người dùng thử lại; không giữ chỗ số dư |

## 6. Khi API thay đổi

API phục vụ demo đồ án, chưa đóng băng. Đổi shape callback hoặc cách chuẩn hóa JSON phải sửa cùng lúc phía ProcureHub (`apps/integrations/`).
