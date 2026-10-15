# ProcureHub — task board

## Đã hoàn thành

- [x] Django 5.2 + PostgreSQL local qua Docker.
- [x] Auth JWT access memory-only, refresh cookie rotation và logout blacklist.
- [x] RBAC, company scope và state transition cho PR/RFQ/quotation/selection/PO.
- [x] Dashboard, audit timeline, supplier relationship và smoke test.
- [x] Frontend client-side workflow cho PR, RFQ/báo giá và PO.
- [x] Migrate frontend từ Next.js sang Vite + React Router SPA thuần.
- [x] Acceptance suite trên PostgreSQL.

## Mở rộng Source-to-Pay (14/10/2026) — theo `../docs/Ke_hoach_cap_nhat_source.md`

- [x] A. Request ID trong audit, `audit.services`, vai trò `FINANCE`.
- [x] B. Notification inbox + SSE, gọi ở mọi transition, gunicorn `threads = 8`.
- [x] C. Trọng số chấm điểm, bảng điểm trong comparison, `score_snapshot`.
- [x] D. Hóa đơn Net N, thanh toán sandbox, webhook HMAC idempotent.
- [x] E. Đánh giá NCC, ngân sách PR, KPI dashboard.
- [x] F. Seed, frontend (chuông thông báo, bảng điểm, trang Hóa đơn, đánh giá, KPI), tài liệu, smoke test.
- [x] G. Tích hợp `../sandbox-service` (15/10/2026): cổng thanh toán (redirect + IPN), hóa đơn điện tử + VAT 10%, ký số báo giá (OTP, xác minh Ed25519, phát hiện sửa dữ liệu). 47 test pass trên SQLite và PostgreSQL; chạy luồng thật qua HTTP.
- [ ] Ký số PO và hóa đơn; tự thử lại callback bị lỡ.
- [ ] Xác nhận có đổi cổng local sang dải `20000–29999` theo chuẩn chung không.
- [ ] Global response envelope, `RequestLoggingMiddleware`, `/metrics` theo `stacks/django.md`.
- [ ] P2: chat RFQ, đính kèm/OCR, ký số, cổng thanh toán thật, ERP, AI, email, phê duyệt theo hạn mức.

## Cần làm tiếp

- [x] Bổ sung production Dockerfile, gunicorn, `deploy/` self-contained và healthcheck theo chuẩn service.
- [x] Chuẩn hóa biến môi trường theo `SECRET_KEY`, `DEBUG`, `DATABASE_*`; bỏ default secret khỏi Django settings.
- [x] Chuẩn hóa PostgreSQL `45432`, backend `48000`, frontend `43000` trong dải `40000–49999`.
- [ ] Bổ sung test cho từng transition lỗi và permission matrix.
- [ ] Hoàn thiện tài liệu API bằng response/error thực tế từ `curl`.
- [ ] Bổ sung migration/seed strategy cho môi trường demo và production riêng biệt.

## Ghi chú phạm vi

Frontend là SPA thuần Vite + React Router; dữ liệu nghiệp vụ fetch phía client và không có SSR.
