# sandbox-service — AI agent entry point

Service Django giả lập cổng thanh toán, nhà cung cấp hóa đơn điện tử và dịch vụ ký số từ xa để ProcureHub tích hợp khi demo. Không có tiền thật, không có giá trị pháp lý.

Bối cảnh chi tiết nằm trong `.ai/` (tool-agnostic). Đọc theo thứ tự:

- [`.ai/agents.md`](.ai/agents.md) — ràng buộc cứng, quy trình verify.
- [`.ai/project.md`](.ai/project.md) — dự án là gì, trạng thái, quyết định đã chốt.
- [`.ai/architecture.md`](.ai/architecture.md) — data model, luồng chính, lý do thiết kế.
- [`.ai/conventions.md`](.ai/conventions.md) — pattern code cụ thể.
- [`TASKS.md`](TASKS.md) — nguồn sự thật cho tiến độ.
- [`README.md`](README.md) — build/chạy/test ở máy dev.
- [`docs/`](docs/) — tài liệu cho người tích hợp (API, INTEGRATION, DEPLOYMENT).

## Bố cục

```text
sandbox-service/
├── .ai/        bối cảnh nội bộ
├── docs/       tài liệu client-facing
├── backend/    mã server — mọi lệnh build chạy ở đây
├── deploy/     tự chứa cho production
└── build.sh    build & push image
```

## Ràng buộc cứng

- Không thêm default cho secret (`SECRET_KEY`, `SANDBOX_API_KEY`, `SANDBOX_WEBHOOK_SECRET`).
- Giữ nhãn "giả lập / không có giá trị pháp lý"; không làm định dạng hóa đơn, mã cơ quan thuế, chứng thư giống thật.
- Không gửi callback/redirect ngoài allowlist; không log body.
- Đổi cách chuẩn hóa JSON hoặc shape callback phải sửa cùng lúc phía ProcureHub (`../procurehub/backend/apps/integrations/`).

- **Không tự `git commit`/`git push`** — làm xong thì báo lại, hỏi xác nhận rồi mới commit.
- **Đang ở nhánh `main`/`master`/`prod` thì cảnh báo trước khi sửa hoặc commit trên đó**, đề nghị tạo nhánh mới, trừ khi người dùng đã nói rõ muốn làm thẳng trên nhánh đó.
- **Không tự ý SSH vào server.** Mọi thao tác trên server (kể cả chỉ để xem log) phải hỏi xác nhận người dùng trước.
- **Chỉ thao tác trực tiếp với database (query, migration, seed...) khi host là `localhost`/`127.0.0.1`.** Host khác — IP nội bộ, IP public, tên miền — đều phải dừng lại và hỏi trước. `DATABASE_HOST` trong `deploy/docker-compose.prod.yml` (giá trị là tên service database nội bộ — `postgres`/`mysql`/`mongo`/`clickhouse` tuỳ engine đã chọn) là cấu hình của app, không phải agent tự kết nối — không tính vào rule này.
