# ProcureHub — hướng dẫn cho agent

ProcureHub là service Django + Django REST Framework cho quy trình mua sắm B2B: purchase request, RFQ, quotation (chấm điểm trọng số), selection, purchase order, hóa đơn và thanh toán sandbox, thông báo realtime (SSE), đánh giá nhà cung cấp và audit.

## Đọc trước khi sửa

1. `README.md` — chạy local, seed và smoke test.
2. `.ai/project.md` — trạng thái và phần còn dang dở.
3. `.ai/architecture.md` — mô hình dữ liệu và luồng nghiệp vụ.
4. `.ai/conventions.md` — các quyết định riêng của repo và gotcha.
5. `.ai/agents.md` — ràng buộc và lệnh kiểm tra.
6. `docs/API.md` — hợp đồng API hiện tại.

Tài liệu nghiệp vụ: `../docs/specs/` (URD, SRS, HLD, Test & demo) — nguồn chuẩn khi code và tài liệu mâu thuẫn.

## Bố cục

- `backend/`: Django project và các app nghiệp vụ.
- `frontend/`: Vite + React SPA; toàn bộ dữ liệu nghiệp vụ fetch phía client.
- `scripts/`: acceptance PostgreSQL và smoke test read-only.
- `docs/`: tài liệu API dành cho người tích hợp.

## Ràng buộc cứng

- Không commit hoặc push thay người dùng.
- Mọi mutation phải kiểm tra authentication, role, company scope, state transition và ghi audit event.
- Database trực tiếp chỉ dùng `localhost`/`127.0.0.1`; database demo hiện chạy bằng Docker PostgreSQL local.
- Không đưa secret thật vào file hoặc log. Mật khẩu seed chỉ dành cho demo. `SANDBOX_WEBHOOK_SECRET` là secret bắt buộc, không có mặc định; bật tích hợp thì `SANDBOX_API_KEY` cũng bắt buộc.
- Thanh toán, hóa đơn điện tử, ký số chỉ là sandbox (repo `../sandbox-service`); không thêm luồng nhận dữ liệu thẻ/tài khoản ngân hàng, không gọi mạng bên trong transaction.
- Khi sửa endpoint, cập nhật đồng thời `docs/API.md` và `.ai/architecture.md`.
- Giữ Python qua pyenv `3.11.15`, frontend qua nvm `22.23.2`.
