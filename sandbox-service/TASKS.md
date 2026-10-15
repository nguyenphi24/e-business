# TASKS — sandbox-service

Nguồn sự thật cho tiến độ. Task `[x]` là đã làm **và** đã verify thật, không chỉ compile.

## Phase 1 — Nền tảng

- [x] TASK-001 Khởi tạo project + build file
- [x] TASK-002 Cấu hình theo biến môi trường, secret không có default
- [x] TASK-003 Migration schema
- [x] TASK-004 Envelope response + xử lý lỗi tập trung
- [x] TASK-005 Health endpoint

## Phase 2 — Nghiệp vụ

- [x] TASK-006 Cổng thanh toán giả lập: tạo giao dịch, trang thanh toán, IPN ký HMAC, gửi lại IPN
- [x] TASK-011 Hóa đơn điện tử giả lập: kiểm tra số học/VAT, ký hiệu–số, cấp mã bất đồng bộ, tra cứu, XML
- [x] TASK-012 Ký số từ xa giả lập: CA Ed25519, chứng thư theo MST, OTP, callback chữ ký
- [x] TASK-013 Chạy luồng thật cùng ProcureHub qua HTTP

## Phase 3 — Vận hành

- [ ] TASK-007 Dockerfile multi-stage, user non-root UID cố định
- [x] TASK-008 Compose dev — không cần: SQLite nhúng
- [ ] TASK-009 `build.sh` + `deploy/` tự chứa
- [x] TASK-010 Tài liệu `.ai/` + `docs/`

## Definition of Done

Một task chỉ được đánh `[x]` khi:

1. Build sạch.
2. Chạm database/migration → chạy thật với database thật.
3. Chạm API → gọi thật, kiểm tra **cả mã HTTP lẫn shape JSON**.
4. Tài liệu liên quan đã cập nhật trong cùng lần thay đổi.
