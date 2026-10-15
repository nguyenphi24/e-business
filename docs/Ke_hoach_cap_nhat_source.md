# Kế hoạch cập nhật mã nguồn ProcureHub (mở rộng Source-to-Pay)

Nguồn yêu cầu: `docs/specs/` (URD, SRS, HLD). Chuẩn code: `~/workspace/conventions` (`standard/*`, `stacks/django.md`) và các quyết định riêng của repo trong `procurehub/.ai/conventions.md`.

## 0. Chuẩn bị

| Việc | Ghi chú |
|---|---|
| Backup mã nguồn trước khi cập nhật | Bản nén lưu ngoài repo (lúc đó chưa có git) |
| Baseline test | 15 test backend pass trên SQLite trước khi sửa |
| Khuyến nghị | `git init -b main` rồi commit baseline trước khi áp dụng thay đổi để có diff rõ ràng |

## 1. Nguyên tắc

- Giữ tên vai trò, trạng thái và API `/api/v1` hiện có; chỉ **thêm**, không đổi tên.
- Mọi mutation mới: kiểm tra authentication, role, company scope, state transition, ghi `AuditEvent` (ràng buộc cứng trong `AGENTS.md`).
- Module mới là Django app riêng (`billing`, `notifications`), không nhồi thêm vào `procurement/api.py`.
- Secret mới đọc bằng `os.environ[...]`, không giá trị mặc định (stacks/django.md).
- Đổi endpoint thì cập nhật cùng lúc `docs/API.md` và `.ai/architecture.md`; số liệu trong tài liệu sinh bằng lệnh thật.
- Không commit/push thay người dùng; chỉ chạy migration/seed trên `localhost`.

## 2. Các giai đoạn

### Giai đoạn A — Nền tảng chung (P0)

| # | Việc | File chính |
|---|---|---|
| A1 | Tách hàm `audit()` sang `apps/audit/services.py`; thêm `request_id` vào `AuditEvent` | `apps/audit/*`, `apps/procurement/api.py` |
| A2 | Middleware `RequestIdMiddleware` (contextvar + header `X-Request-ID`) | `common/middleware.py`, `config/settings.py` |
| A3 | Vai trò `FINANCE`; permission helper | `apps/identity/models.py`, `permissions.py` |

### Giai đoạn B — Notification + SSE (P0)

| # | Việc | File chính |
|---|---|---|
| B1 | App `notifications`: model `Notification` (id tự tăng), service `notify_event()` với bảng người nhận SRS 3.3 | `apps/notifications/models.py`, `services.py` |
| B2 | REST inbox: list, unread-count, read, read-all | `apps/notifications/api.py` |
| B3 | SSE `GET /notifications/stream`: xác thực JWT thủ công, `StreamingHttpResponse`, poll 2 giây, tối đa 25 giây, `Last-Event-ID`/`after` | `apps/notifications/stream.py` |
| B4 | Gọi `notify_event()` tại mọi transition trong PR/RFQ/quotation/selection/PO | `apps/procurement/api.py` |
| B5 | gunicorn tăng `threads` cho kết nối SSE | `backend/gunicorn.conf.py` |

### Giai đoạn C — Chấm điểm báo giá (P0)

| # | Việc | File chính |
|---|---|---|
| C1 | Cột `RFQ.scoring_weights`, `RFQ.published_at`, `Quotation.payment_term_days`, `SupplierSelection.score_snapshot` | `apps/procurement/models.py` + migration |
| C2 | Module thuần `scoring.py` (công thức SRS mục 5) + unit test | `apps/procurement/scoring.py` |
| C3 | `POST /rfqs/{id}/scoring-weights`; comparison trả `scoring`; selection lưu snapshot | `apps/procurement/api.py`, `serializers.py` |

### Giai đoạn D — Hóa đơn, thanh toán sandbox (P1)

| # | Việc | File chính |
|---|---|---|
| D1 | `PurchaseOrder.payment_term_days`, `delivered_at`; snapshot khi sinh PO | `apps/purchase_orders/models.py` |
| D2 | App `billing`: `Invoice`, `Payment`, `PaymentEvent` | `apps/billing/models.py` |
| D3 | API hóa đơn: lập (Supplier), hủy, list/detail theo scope, lọc overdue | `apps/billing/api.py` |
| D4 | Lệnh thanh toán (Idempotency-Key), `simulate`, webhook HMAC idempotent | `apps/billing/api.py`, `services.py`, `mock_provider.py` |
| D5 | Biến môi trường `SANDBOX_WEBHOOK_SECRET` (tên ban đầu `PAYMENT_WEBHOOK_SECRET`, đổi ở mục 7), `PAYMENT_SANDBOX_ENABLED` | `settings.py`, `.env.example`, `deploy/*` |

### Giai đoạn E — Đánh giá NCC, KPI (P1)

| # | Việc | File chính |
|---|---|---|
| E1 | `SupplierEvaluation` + `POST /purchase-orders/{id}/evaluation`; `GET /suppliers` có điểm trung bình | `apps/suppliers/*`, `apps/procurement/api.py` |
| E2 | `PurchaseRequest.estimated_budget`, `submitted_at` | `apps/procurement/models.py` |
| E3 | `kpis.py` tính 6 KPI (SRS mục 6); dashboard thêm pending action Finance/Supplier, số liệu hóa đơn | `apps/dashboard/*` |

### Giai đoạn F — Seed, frontend, tài liệu

| # | Việc | File chính |
|---|---|---|
| F1 | Seed: `finance@vnptmedia.demo`; ngân sách PR mẫu; đánh giá + hóa đơn đã trả cho PO mẫu | `seed_demo.py` |
| F2 | Frontend: chuông thông báo + SSE (`fetch` streaming), trọng số và bảng điểm ở RFQ, trang Hóa đơn (Supplier/Finance, nhãn Sandbox), form đánh giá NCC ở PO, KPI ở Dashboard, ngân sách PR | `frontend/lib/*`, `frontend/app/*`, `components/*` |
| F3 | `docs/API.md`, `.ai/architecture.md`, `.ai/project.md`, `.ai/conventions.md`, `AGENTS.md`, `README.md`, `TASKS.md` trỏ sang `../docs/specs/` | repo |
| F4 | `scripts/smoke_demo.sh` kiểm tra thêm endpoint read-only mới | `scripts/` |

## 3. Kiểm thử

| Nhóm | Test mới |
|---|---|
| Scoring | Công thức đúng; trọng số sai tổng 422; đổi trọng số khi AWARDED 409 |
| Notification | Đúng người nhận; Supplier không được mời không nhận; inbox không lộ chéo user; SSE trả sự kiện sau `after` |
| Billing | Lập hóa đơn khi PO chưa giao 409; trùng hóa đơn 409; thanh toán vượt số dư 422; webhook sai chữ ký 401; trùng `event_id` không cộng hai lần; 30% → PARTIALLY_PAID, đủ → PAID; IDOR hóa đơn tenant khác 404 |
| Evaluation | Chỉ PO COMPLETED; một lần |
| KPI | Dashboard trả đủ 6 KPI có `n` |
| Audit | `request_id` được lưu và trả header |

Lệnh xác minh (theo `.ai/agents.md`): `manage.py check`, `manage.py makemigrations --check`, `manage.py test`, `scripts/acceptance_postgres.sh`, `npm exec tsc -- --noEmit`, `npm run build`.

## 4. Đối chiếu chuẩn `~/workspace/conventions`

| Chuẩn | Trạng thái sau cập nhật |
|---|---|
| Secret bắt buộc không mặc định (`os.environ[...]`) | Áp dụng cho `SANDBOX_WEBHOOK_SECRET` (và `SANDBOX_API_KEY` khi bật tích hợp) |
| `DEBUG` mặc định false | Giữ |
| `.env` duy nhất ở root, nạp bằng `python-dotenv` | Giữ |
| `deploy/` tự chứa, biến mới khai báo trong compose prod | Cập nhật |
| Không log body/token | Giữ; webhook không log chữ ký |
| Response envelope toàn cục (`{success, data}`) | **Chưa áp dụng** — sai khác đã ghi trong `.ai/conventions.md`; đổi sẽ phá frontend và hợp đồng API, để sau demo |
| `RequestLoggingMiddleware`, `django-prometheus` `/metrics` | **Chưa áp dụng** — đề xuất giai đoạn sau; lần cập nhật này chỉ thêm request ID |
| Cổng local dải `20000–29999` | Repo đang dùng `40000–49999` theo quyết định riêng; **cần người dùng xác nhận** có đổi không, chưa tự đổi |
| Tài liệu tách `docs/` (tích hợp) và `.ai/` (nội bộ) | Giữ |

## 5. Ngoài phạm vi lần cập nhật này (P2)

Chat theo RFQ, đính kèm/OCR, ký số, cổng thanh toán thật, ERP/kế toán, hóa đơn điện tử pháp lý, AI gợi ý NCC, email notification, phê duyệt nhiều cấp theo hạn mức, worker outbox riêng, ASGI cho SSE quy mô lớn.

## 6. Kết quả thực hiện

Ghi tại [specs/04_Test_Demo.md](specs/04_Test_Demo.md) mục 4 (bảng Proposed / Implemented / Tested) sau khi chạy kiểm thử thật.

## 7. Bổ sung: tích hợp đối tác giả lập (15/10/2026)

| # | Việc | Kết quả |
|---|---|---|
| H1 | Dựng repo `../sandbox-service` bằng `init.sh` (Django, SQLite): cổng thanh toán, hóa đơn điện tử + cơ quan thuế cấp mã, ký số từ xa + CA | 13 test; build và chạy thử image Docker |
| H2 | `procurehub/apps/integrations`: adapter `SandboxClient`, webhook HMAC dùng chung, xác minh chữ ký Ed25519, ghim khóa CA | Xong |
| H3 | Thanh toán chuyển sang trang cổng + IPN (kiểm số tiền); webhook đổi thành `/webhooks/payment`, secret đổi tên `SANDBOX_WEBHOOK_SECRET` | Xong |
| H4 | Hóa đơn VAT 10% (migration chuyển dữ liệu cho hóa đơn cũ), phát hành hóa đơn điện tử, chặn hủy hóa đơn đã gửi cơ quan thuế | Xong |
| H5 | Ký số báo giá, tính lại mã băm khi hiển thị, lệnh demo `demo_tamper_quotation` | Xong |
| H6 | Giao diện: nút ký số và cột chữ ký, cột hóa đơn điện tử, chuyển sang cổng thanh toán | Xong |
| H7 | Kiểm thử: 47 test ProcureHub (SQLite + PostgreSQL), E2E qua HTTP giữa hai service, ảnh chụp UI | Xong |
