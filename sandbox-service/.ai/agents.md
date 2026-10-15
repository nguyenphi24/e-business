# Agents

Hướng dẫn cho AI agent khi làm việc trên repo này. Đọc cùng [`project.md`](project.md), [`architecture.md`](architecture.md), [`conventions.md`](conventions.md).

## Thứ tự đọc khi bắt đầu phiên

1. [`../TASKS.md`](../TASKS.md) — tiến độ, không đoán từ code.
2. [`project.md`](project.md) — việc cố tình để dở, quyết định đã chốt.
3. [`architecture.md`](architecture.md) — luồng chính, trước khi đổi service layer.
4. [`conventions.md`](conventions.md) — pattern code, mục "chỗ dễ sai nhất".
5. [`../docs/API.md`](../docs/API.md) — hợp đồng API, trước khi đổi controller/DTO.

## Phân tách tài liệu — nội bộ vs client

- **`docs/`** — cho người ngoài repo. Chỉ những gì cần để gọi API đúng. Không tên class, không lý do lịch sử.
- **`.ai/`, `README.md`, `TASKS.md`** — cho người/agent sửa chính repo này.
- Sửa một endpoint → cập nhật `docs/API.md` **và** `.ai/architecture.md` trong cùng lần thay đổi.

## Ràng buộc cứng — đừng vi phạm

- Không thêm default cho `SECRET_KEY`, `SANDBOX_API_KEY`, `SANDBOX_WEBHOOK_SECRET` — app phải chết khi thiếu.
- Không bỏ nhãn "GIẢ LẬP / không có giá trị pháp lý" trên trang và XML; không làm định dạng hóa đơn/chứng thư giống thật — tránh bị dùng nhầm.
- Không gửi callback ngoài `ALLOWED_CALLBACK_PREFIXES`, không redirect ngoài `ALLOWED_RETURN_PREFIXES` — chặn lạm dụng sandbox để gọi/chuyển hướng tùy ý.
- Không log body request/callback — có thể chứa dữ liệu hóa đơn.

- **Không** đọc, log, hay commit nội dung `.env` thật (khác `.env.example`). Cần biết file tồn tại thì `test -f`, không `cat`.

## Môi trường khi verify

- Cổng dev 28080; SQLite tại `data/sandbox_service.db`.
- Test: `cd backend && SECRET_KEY=test SANDBOX_API_KEY=test SANDBOX_WEBHOOK_SECRET=test .venv311/bin/python manage.py test`.
- Chạy cùng ProcureHub: hai bên dùng chung `SANDBOX_API_KEY` và `SANDBOX_WEBHOOK_SECRET`; ProcureHub đặt `SANDBOX_BASE_URL=http://127.0.0.1:28080`.

## Cập nhật tài liệu khi hoàn thành task

- Task xong → tick `TASKS.md` ngay.
- Quyết định kiến trúc mới → thêm vào `.ai/architecture.md`.
- Gotcha mới → thêm vào `.ai/conventions.md`, để phiên sau khỏi dò lại.
