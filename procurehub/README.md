# ProcureHub — mã nguồn demo

Hệ thống mua sắm điện tử B2B (môn Hệ kinh doanh điện tử). Tài liệu thiết kế nằm ở `../docs/specs` (URD, SRS, HLD, Test & demo); báo cáo môn học ở `../docs/report`.

Agent đọc `AGENTS.md` trước, sau đó xem `.ai/` để nắm kiến trúc và các quyết định riêng của repo. Hợp đồng API dành cho người tích hợp nằm ở `docs/API.md`; backlog nằm ở `TASKS.md`.

## Trạng thái hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Docker Compose PostgreSQL 16 | Xong |
| Production Dockerfile, gunicorn, healthcheck và deploy skeleton | Xong |
| Django project, cấu hình JWT/CORS/OpenAPI | Xong |
| Mô hình dữ liệu theo HLD mục 6 + D-09, migration | Xong |
| Seed theo Addendum mục 4 (chạy lại được) | Xong |
| `GET /api/v1/health`, Swagger `/api/v1/docs` | Xong |
| Auth API (login, refresh cookie, me) | Xong (refresh token httpOnly cookie, rotation, blacklist) |
| RBAC, company scope và lỗi API chuẩn hóa | Xong cho Purchase Request |
| Purchase Request API và state transition | Xong: create, edit, submit, approve, reject, cancel |
| RFQ, quotation và selection workflow | Xong: publish, close, quotation submit/revise, comparison, selection approve/reject |
| PO workflow API | Xong: generate idempotent, issue, acknowledge/decline, delivery, complete/cancel |
| Dashboard và audit timeline API | Xong: company scope, counts, pending actions, recent activity và bộ lọc audit |
| Frontend UI MVP | Xong: login, dashboard, Purchase Request, RFQ/báo giá, Purchase Order |
| Thông báo realtime (inbox + SSE) | Xong: `/notifications`, `/notifications/stream`, chuông thông báo |
| Chấm điểm báo giá theo trọng số | Xong: `/rfqs/{id}/scoring-weights`, khối `scoring` trong comparison |
| Hóa đơn Net N + VAT 10%, thanh toán nhiều lần, webhook HMAC | Xong: `/invoices`, `/payments/{id}/simulate`, `/webhooks/payment` |
| Tích hợp sandbox-service: cổng thanh toán, hóa đơn điện tử, ký số báo giá | Xong: `/quotations/{id}/sign`, `/invoices/{id}/einvoice`, `/webhooks/{payment,einvoice,esign}` |
| Đánh giá NCC, KPI dashboard, vai trò Finance | Xong |

## Chạy local

Yêu cầu: Docker, pyenv và Python 3.11+ (khuyến nghị `3.11.15`).

```bash
cd procurehub
cp .env.example .env
# thay SECRET_KEY bằng kết quả: openssl rand -base64 48
# thay SANDBOX_WEBHOOK_SECRET bằng kết quả: openssl rand -hex 32, và SANDBOX_API_KEY —
# hai giá trị này phải trùng với .env của ../sandbox-service (để trống SANDBOX_BASE_URL nếu không chạy sandbox)
docker compose up -d --wait            # PostgreSQL ở localhost:45432

cd backend
pyenv local 3.11.15
python -m venv .venv311 && source .venv311/bin/activate
python -m pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo             # lần đầu
python manage.py seed_demo --reset     # xóa sạch rồi nạp lại
python manage.py runserver 48000       # http://localhost:48000
```

Port local thống nhất dùng đầu `4`: PostgreSQL `45432`, backend `48000`, frontend `43000`. Có thể override `DATABASE_PORT` nếu cần, nhưng vẫn giữ trong dải `40000–49999`.
Chưa có Docker: đặt `USE_SQLITE=true` trong `.env` để chạy thử nhanh bằng SQLite (chỉ để thử, không dùng khi demo).

Kiểm tra: mở `http://localhost:48000/api/v1/health` (trả `{"status": "ok"}`) và `http://localhost:48000/api/v1/docs`.

Smoke test read-only sau khi đã chạy backend và frontend:

```bash
cd procurehub
./scripts/smoke_demo.sh
```

Có thể đổi địa chỉ bằng `API_URL`, `WEB_URL` hoặc mật khẩu seed bằng `DEMO_PASSWORD`.

Acceptance trên PostgreSQL thật (dùng cổng `45432` mặc định):

```bash
cd procurehub
./scripts/acceptance_postgres.sh
```

Script sẽ bật PostgreSQL, migrate, seed lại dữ liệu demo và chạy toàn bộ backend test suite.

Production packaging nằm ở `backend/Dockerfile`, `frontend/Dockerfile` và `deploy/`. Build image bằng `build.sh` sau khi điền `.env.registry`; không chạy `deploy/deploy.prod.sh` nếu chưa điền `.env.prod` và `.env.registry` trên server thật.

Frontend:

```bash
cd procurehub/frontend
source "$HOME/.nvm/nvm.sh"
nvm install 22.23.2
nvm use 22.23.2
npm install
cp .env.example .env.local
npm run dev                       # http://localhost:43000
```

## Chạy cùng sandbox-service (cổng thanh toán, hóa đơn điện tử, ký số giả lập)

Repo `../sandbox-service` chạy ở cổng `28080` (xem README của repo đó). Hai bên dùng chung `SANDBOX_API_KEY` và `SANDBOX_WEBHOOK_SECRET`; `.env` của ProcureHub đặt `SANDBOX_BASE_URL=http://127.0.0.1:28080`. Thứ tự bật: PostgreSQL → sandbox-service → backend → frontend.

Kịch bản demo chữ ký số: Supplier gửi báo giá → bấm "Ký số báo giá" → nhập OTP trên trang sandbox → bảng so sánh của bên mua hiện "Chữ ký hợp lệ". Mô phỏng sửa trộm dữ liệu trong DB (chỉ dùng khi demo):

```bash
cd backend
python manage.py demo_tamper_quotation --rfq RFQ-2026-0002 --supplier-tax-code 0200000002 --unit-price 3999000
# bảng so sánh chuyển "Chữ ký KHÔNG hợp lệ"; lệnh in ra giá cũ để chạy lại khôi phục
```

## API đã triển khai

Auth:

- `POST /api/v1/auth/login` với `{ "email": "...", "password": "..." }` trả access token và đặt refresh token vào httpOnly cookie.
- `POST /api/v1/auth/refresh` xoay refresh cookie và trả access token mới.
- `POST /api/v1/auth/logout` blacklist refresh token và xóa cookie.
- `GET /api/v1/auth/me` trả user, company và roles hiện tại.

Purchase Request:

- `GET/POST /api/v1/purchase-requests`
- `GET/PATCH /api/v1/purchase-requests/{id}`
- `POST /api/v1/purchase-requests/{id}/submit`
- `POST /api/v1/purchase-requests/{id}/approve`
- `POST /api/v1/purchase-requests/{id}/reject` với `reason` bắt buộc
- `POST /api/v1/purchase-requests/{id}/cancel`

Sourcing:

- `GET /api/v1/suppliers` trả các supplier relationship `ACTIVE` trong company của buyer.
- `GET/POST /api/v1/rfqs`
- `POST /api/v1/rfqs/{id}/publish`, `/close`, `/cancel`, `/invitations`
- `POST /api/v1/rfqs/{id}/accept-invitation`, `/decline-invitation` (Supplier xác nhận/từ chối lời mời, từ chối cần `reason`)
- `GET /api/v1/rfqs/{id}/comparison`
- `GET/POST /api/v1/rfqs/{id}/quotation`
- `POST /api/v1/quotations/{id}/submit`, `/revise`; `PATCH /api/v1/quotations/{id}` khi còn draft
- `POST /api/v1/rfqs/{id}/selection`
- `POST /api/v1/selections/{id}/approve`, `/reject`

Dashboard và audit:

- `GET /api/v1/dashboard` trả counts theo status, pending actions và 20 audit events gần nhất theo scope người dùng.
- `GET /api/v1/audit-events` hỗ trợ `action`, `entity_type`, `entity_id`, `from`, `to` và `limit` (1–100).
- `POST /api/v1/purchase-orders/generate` với header `Idempotency-Key`
- `POST /api/v1/purchase-orders/{id}/issue`, `/acknowledge`, `/decline`, `/deliveries`, `/complete`, `/cancel`

Mọi mutation workflow đều kiểm tra role, company scope, state transition và ghi `AuditEvent`.

## Convention và phạm vi

Repo tham khảo bộ chuẩn tại `/Users/tnphi/workspace/conventions`. ProcureHub hiện là bản demo local: frontend là SPA thuần Vite + React Router, còn production Docker/deploy chưa nằm trong phạm vi đã hoàn tất. Các việc cần chuẩn hóa trước deploy được ghi ở `TASKS.md`.

## Dữ liệu seed

Mật khẩu chung `Demo@2026` (chỉ dùng cho demo).

| Email | Company | Vai trò | Tên hiển thị |
|---|---|---|---|
| buyer@vnptmedia.demo | VNPT Media | Buyer | Nguyễn Minh Anh (Mua hàng) |
| manager@vnptmedia.demo | VNPT Media | Manager | Trần Quốc Bảo (Trưởng phòng mua hàng) |
| finance@vnptmedia.demo | VNPT Media | Finance | Lê Thu Hà (Kế toán công nợ) |
| admin@vnptmedia.demo | VNPT Media | Company Admin | Phạm Đức Long (Quản trị công ty) |
| sales@techvision.demo | TechVision | Supplier | Võ Hoàng Nam (Kinh doanh TechVision) |
| sales@digitalsupply.demo | Digital Supply | Supplier | Đặng Thùy Linh (Kinh doanh Digital Supply) |
| buyer@otherbuyer.demo | Other Buyer | Buyer | Bùi Văn Khánh (Mua hàng Other Buyer) |
| sysadmin@procurehub.demo | — | System Admin | Quản trị nền tảng |

`seed_demo` in bảng tài khoản này khi chạy. Kịch bản demo dùng các tài khoản trên: `../docs/Kich_ban_demo.md`. Trước buổi demo chạy `seed_demo --reset` cùng `seed_sandbox --reset` bên sandbox-service (hoặc `../run.local.sh reset`) để số chứng từ bắt đầu từ RFQ-2026-0002, INV-2026-0002 và hóa đơn điện tử `SBX26/1`.

Seed cũng tạo: đánh giá NCC cho PO mẫu, hóa đơn Net 30 đã thanh toán 30% qua sandbox; quan hệ active giữa VNPT Media với TechVision và Digital Supply; một Purchase Request APPROVED mẫu; một chuỗi request → RFQ → quotation → selection → PO COMPLETED mẫu cho Dashboard; một request nháp của Other Buyer để kiểm thử truy cập chéo company.

## Cấu trúc

```text
backend/
  config/            settings, urls
  apps/identity/     Company, User, UserRole + lệnh seed_demo
  apps/suppliers/    SupplierRelationship
  apps/procurement/  PR, RFQ, Quotation, Selection, DocumentSequence, IdempotencyKey
  apps/purchase_orders/  PO, PO line, DeliveryRecord
  apps/audit/        AuditEvent, audit service, company scope
  apps/billing/      Invoice, Payment, PaymentEvent, mock provider, webhook
  apps/notifications/ Notification, quy tắc người nhận, SSE stream
  apps/dashboard/    Dashboard, KPI
  apps/integrations/ Adapter sandbox-service, webhook HMAC, xác minh chữ ký số
  common/            base model
```

Số chứng từ cấp bằng `DocumentSequence.next_number("PR", năm)` (khóa dòng trong transaction).
