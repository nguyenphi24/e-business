# B2B E-Procurement — ProcureHub

Đề tài môn **Hệ kinh doanh điện tử (E-Business)**, lớp IS6101.11.CH, Trường Đại học Công nghệ Thông tin – ĐHQG-HCM. Giảng viên hướng dẫn: TS. Trần Văn Hải Triều.

**Nhóm 2:** Tăng Quốc Hưng (trưởng nhóm), Trần Nguyễn Phi, Trần Thanh Vũ, Lê Trọng Đạo.

ProcureHub là nền tảng mua sắm điện tử B2B theo mô hình SaaS cho doanh nghiệp vừa và nhỏ, có Buyer Portal và Supplier Portal trên cùng một hệ thống đa doanh nghiệp. Hệ thống số hóa chuỗi Source-to-Pay ở mức ghi nhận:

```text
Đề nghị mua (PR) → phê duyệt → RFQ → báo giá (ký số) → bảng điểm trọng số → duyệt lựa chọn
→ đơn đặt hàng (PO) → nhận hàng → hóa đơn VAT + hóa đơn điện tử → thanh toán qua cổng → đánh giá NCC
```

Điểm nhấn: tách quyền và audit log, thông báo realtime (SSE), chấm điểm báo giá công khai công thức, KPI mua sắm, và tích hợp đối tác (cổng thanh toán, hóa đơn điện tử, chữ ký số) qua một dịch vụ giả lập. **Mọi thanh toán, hóa đơn điện tử và chữ ký trong demo đều là giả lập, không có giá trị pháp lý.**

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| [`procurehub/`](procurehub/) | Nền tảng chính: Django + DRF (backend), Vite + React + Ant Design (frontend), PostgreSQL |
| [`sandbox-service/`](sandbox-service/) | Dịch vụ giả lập đối tác: cổng thanh toán, hóa đơn điện tử + cơ quan thuế cấp mã, ký số từ xa + CA |
| [`docs/`](docs/) | Báo cáo (.docx + Markdown), URD/SRS/HLD, sơ đồ, ảnh chụp màn hình |

Mỗi project có `README.md` (chạy local), `AGENTS.md` và `.ai/` (bối cảnh cho người sửa code), `docs/API.md` (hợp đồng API).

## Chạy demo local

Yêu cầu: Docker Desktop (đang chạy), Python 3.11+ (khuyến nghị pyenv `3.11.15`), Node 22+ (khuyến nghị nvm `22.23.2`).

### Cách nhanh

```bash
./run.local.sh          # kiểm tra môi trường → cài phụ thuộc còn thiếu → bật PostgreSQL, backend, frontend, sandbox-service
./run.local.sh check    # chỉ kiểm tra và cài, không khởi động
./run.local.sh stop     # tắt các tiến trình đã bật (từ terminal khác); hoặc Ctrl+C ở terminal đang chạy
```

Script kiểm tra Python và Node cài sẵn trên máy trước, không đủ phiên bản thì tìm pyenv/nvm; tạo `.venv311` (ưu tiên pyenv `3.11.15`) và `node_modules` khi thiếu hoặc khi `requirements`/`package-lock.json` đổi; lần đầu tạo hai file `.env` với secret ngẫu nhiên, dùng chung `SANDBOX_API_KEY`/`SANDBOX_WEBHOOK_SECRET`; nạp dữ liệu demo nếu database trống. Log nằm ở `.run/logs/`. Script không tự tắt tiến trình lạ đang chiếm cổng — báo ra để bạn xử lý.

### Từng bước (thủ công)

| Thành phần | Cổng |
|---|---|
| PostgreSQL (Docker) | 45432 |
| ProcureHub backend | 48000 |
| ProcureHub frontend | 43000 |
| sandbox-service | 28080 |

1. **Cấu hình:** `cp procurehub/.env.example procurehub/.env` và `cp sandbox-service/.env.example sandbox-service/.env`. Điền `SECRET_KEY` riêng cho mỗi bên; `SANDBOX_API_KEY` và `SANDBOX_WEBHOOK_SECRET` **phải giống nhau ở hai file** (`openssl rand -hex 32`).
2. **sandbox-service:** làm theo [`sandbox-service/README.md`](sandbox-service/README.md) (`migrate`, `runserver 127.0.0.1:28080`).
3. **ProcureHub:** làm theo [`procurehub/README.md`](procurehub/README.md) (`docker compose up -d`, `migrate`, `seed_demo`, `runserver 48000`, `npm run dev`).
4. Mở `http://localhost:43000`, đăng nhập bằng tài khoản demo (mật khẩu chung `Demo@2026`):

| Email | Vai trò |
|---|---|
| `buyer@vnptmedia.demo` | Người mua hàng |
| `manager@vnptmedia.demo` | Quản lý phê duyệt |
| `finance@vnptmedia.demo` | Kế toán |
| `sales@techvision.demo`, `sales@digitalsupply.demo` | Nhà cung cấp |

Không chạy sandbox-service thì để trống `SANDBOX_BASE_URL` trong `procurehub/.env`: hệ thống vẫn chạy, thanh toán dùng nút mô phỏng nội bộ, không có hóa đơn điện tử và ký số.

## Kiểm thử

```bash
# ProcureHub — 47 test; bản PostgreSQL: procurehub/scripts/acceptance_postgres.sh
cd procurehub/backend && SECRET_KEY=test USE_SQLITE=true SANDBOX_WEBHOOK_SECRET=test python manage.py test

# sandbox-service — 13 test
cd sandbox-service/backend && SECRET_KEY=test SANDBOX_API_KEY=test SANDBOX_WEBHOOK_SECRET=test python manage.py test
```

Kịch bản demo 8–12 phút và kết quả chạy thật: [`docs/specs/04_Test_Demo.md`](docs/specs/04_Test_Demo.md).
