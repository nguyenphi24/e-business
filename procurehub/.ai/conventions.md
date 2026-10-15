# Repo-specific conventions

Shared standards được tham khảo từ `/Users/tnphi/workspace/conventions/standard/` và `/Users/tnphi/workspace/conventions/stacks/django.md`; không copy nội dung chuẩn chung vào repo.

## Backend

- `backend/` là source server duy nhất; Django app nằm dưới `backend/apps/`.
- Dùng pyenv `3.11.15` và virtualenv `.venv311`.
- Settings đọc `.env` ở repo root; secret bắt buộc là `SECRET_KEY`, database dùng nhóm biến `DATABASE_*`.
- PostgreSQL acceptance phải chạy cùng test suite vì lock/query behavior khác SQLite.
- Không log body request/response hoặc token.

## Frontend

- Dùng nvm `22.23.2`.
- UI là SPA thuần Vite + React Router; page component dùng client-side fetch.
- Không thêm SSR, server actions hoặc server-side token storage nếu chưa cập nhật quyết định kiến trúc.
- Access token không lưu localStorage; refresh cookie khôi phục access token khi cần.

## Dễ sai

- Không gọi `close_old_connections()` trong generator SSE: nó đóng kết nối DB dùng chung của `TestCase` trên PostgreSQL (SQLite không lộ lỗi). Django tự đóng kết nối qua `request_finished` khi response streaming kết thúc.
- Kiểm tra SSE bằng trình duyệt/puppeteer không dùng `networkidle`: kết nối stream luôn mở nên trang không bao giờ "idle".
- Thông báo phải gọi `notify_event()` bên trong `transaction.atomic()` của transition, không gọi sau commit, để thông báo và dữ liệu đi cùng nhau.
- `select_for_update(of=("self",))` cho mọi object chính bị khóa, kể cả `Invoice`/`Payment` trong `process_payment_event`.
- Không gọi `SandboxClient` bên trong `transaction.atomic()`: lời gọi mạng giữ khóa dòng. Tạo bản ghi trong transaction, gọi mạng sau đó, lỗi thì ghi trạng thái `FAILED`.
- Chuẩn hóa JSON (`integrations.security.canonical_json`) phải giống hệt sandbox-service; lệch một tham số là mọi chữ ký HMAC/CA sai.
- Định dạng số trong `quotation_document()` cố định (`:.3f` số lượng, `:.2f` tiền); đổi format là mọi chữ ký báo giá cũ thành INVALID.
- `os.getenv("X", default)` trả chuỗi rỗng khi compose truyền biến trống — dùng `os.getenv("X") or default` cho URL cấu hình.
- Webhook đọc `request.body` (raw) để tính HMAC trước khi parse JSON; đừng đổi sang `request.data`.

## Demo deviations

- Response hiện là JSON theo từng API view, chưa chuyển sang global renderer envelope.
- Production deploy và global response envelope vẫn chưa nằm trong MVP demo.
- Chưa có `RequestLoggingMiddleware` và `django-prometheus` theo `stacks/django.md`; hiện mới có `RequestIdMiddleware`.
- Cổng local dùng dải `40000–49999` (PostgreSQL `45432`, backend `48000`, frontend `43000`), khác dải `20000–29999` của chuẩn chung; giữ nguyên cho tới khi người dùng quyết định đổi.
