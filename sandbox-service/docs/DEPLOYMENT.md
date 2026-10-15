# Deployment — sandbox-service

Chạy ở máy dev xem [`../README.md`](../README.md).

Hai nửa tách biệt:

- **Máy dev/CI** — `build.sh` build image rồi push lên registry; `sync-deploy.sh` đưa nội dung `deploy/` lên server qua SSH.
- **Host production** — chỉ có `deploy/`. Tự chứa: copy nguyên thư mục này lên server (hoặc để `sync-deploy.sh` làm hộ) là đủ.

## 1. Biến môi trường

### `deploy/.env.registry`

| Biến | Ghi chú |
|---|---|
| `REGISTRY_HOST` | Host registry, không kèm scheme |
| `PROJECT_PATH` | `<namespace>/<repo>` |
| `REGISTRY_USER` / `REGISTRY_PASS` | Token. Quyền đọc là đủ trên production; máy build cần thêm quyền ghi |

### `deploy/.env.prod`

| Biến | Bắt buộc | Ghi chú |
|---|---|---|
| `SANDBOX_SERVICE_SECRET_KEY` | Có | Django `SECRET_KEY` |
| `SANDBOX_SERVICE_API_KEY` | Có | Trùng `SANDBOX_API_KEY` của merchant |
| `SANDBOX_SERVICE_WEBHOOK_SECRET` | Có | Trùng `SANDBOX_WEBHOOK_SECRET` của merchant |
| `SANDBOX_SERVICE_ALLOWED_HOSTS` | Có | Domain sandbox |
| `SANDBOX_SERVICE_PUBLIC_BASE_URL` | Có | URL công khai để sinh link trang |
| `SANDBOX_SERVICE_ALLOWED_CALLBACK_PREFIXES` | Có | Chỉ API webhook của merchant |
| `SANDBOX_SERVICE_ALLOWED_RETURN_PREFIXES` | Có | Chỉ SPA của merchant |
| `SANDBOX_SERVICE_EINVOICE_TAX_DELAY_SECONDS` | Không (3) | Thời gian giả lập cấp mã |
| `SANDBOX_SERVICE_DB_PATH` | Không (`/data/sandbox_service.db`) | Nằm trên volume |
| `SANDBOX_SERVICE_IMAGE_TAG` / `SANDBOX_SERVICE_HOST_PORT` | Có / Không (8080) | Tag do `build.sh` in ra; cổng host ánh xạ vào cổng 8000 của gunicorn |

### `.env.sync` (root, không phải `deploy/`)

Chỉ máy dev dùng (đọc bởi `sync-deploy.sh`) — không script nào trên server cần tới, nên không nằm trong `deploy/`.

| Biến | Ghi chú |
|---|---|
| `SSH_HOST` / `SSH_USER` / `SSH_PORT` | Đích SSH của host production. `SSH_PORT` bỏ trống thì mặc định 22 |
| `SSH_KEY` | Identity file cụ thể — bỏ trống thì dùng mặc định của ssh-agent/`~/.ssh/config` |
| `DEPLOY_PATH` | Thư mục gốc trên server sẽ chứa nội dung `deploy/` |

## 2. Kiểm tra trước khi deploy

1. `cd backend && SECRET_KEY=t SANDBOX_API_KEY=t SANDBOX_WEBHOOK_SECRET=t .venv311/bin/python manage.py test`.
2. Xác nhận app chết khi thiếu secret: `env -u SANDBOX_WEBHOOK_SECRET .venv311/bin/python manage.py check` phải báo `KeyError`.
3. Chạy luồng thật cùng ProcureHub (thanh toán, hóa đơn điện tử, ký số) trước khi build image.

## 3. Build & push

```bash
cp deploy/.env.registry.example .env.registry
./build.sh
```

Tag là git short SHA. `build.sh` từ chối build khi working tree còn thay đổi chưa commit.

## 4. Đồng bộ `deploy/` lên server

```bash
cp .env.sync.example .env.sync   # điền SSH_HOST/SSH_USER/DEPLOY_PATH
./sync-deploy.sh
```

Tự kiểm SSH bằng key trước; chưa kết nối được thì hỏi tạo key mới + `ssh-copy-id` (cần nhập password server một lần). Sync bằng rsync, **không** đụng `.env.prod`/`.env.registry` đã có sẵn trên server (`.env.sync` chỉ tồn tại ở máy dev, không có gì để đụng) — lần đầu tự tạo `.env.prod`/`.env.registry` trực tiếp trên server từ bản `.example`. Chạy xong không tự SSH vào deploy tiếp; script in sẵn lệnh SSH cho bước 5.

## 5. Deploy

SSH vào server (lệnh `sync-deploy.sh` vừa in ra), trong `deploy/`:

```bash
cp .env.prod.example .env.prod   # lần đầu, điền — gồm SANDBOX_SERVICE_IMAGE_TAG
./deploy.prod.sh
```

Chờ healthy rồi mới xoá image cũ. Không healthy thì thoát lỗi và giữ nguyên bản cũ để rollback.

## 6. Rollback

Đổi `SANDBOX_SERVICE_IMAGE_TAG` về SHA cũ rồi chạy lại `./deploy.prod.sh`.

Rollback **không** hoàn tác migration database.

## 7. Volume & dữ liệu

`sandbox_service_db_prod_data` chứa SQLite (giao dịch giả lập, hóa đơn, **khóa CA và khóa người ký**). Mất volume thì CA sinh lại khóa mới — merchant phải xóa khóa CA đã ghim (`trust_anchors` bên ProcureHub) và mọi chữ ký cũ không xác minh được nữa. Dữ liệu giả lập, không có kế hoạch backup.

## 8. Chưa có

Chưa có: CI, backup, monitoring ngoài `/metrics`; chưa từng triển khai lên server thật. TLS do nginx trên host đảm nhận (`deploy/nginx/`). Tài liệu
> nói mập mờ ở mục này nguy hiểm hơn là không nói.
