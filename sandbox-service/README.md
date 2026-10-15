# sandbox-service

Service giả lập ba nhà cung cấp bên ngoài cho ProcureHub (đề tài B2B E-Procurement, môn Hệ kinh doanh điện tử): **cổng thanh toán** (SandboxPay), **nhà cung cấp hóa đơn điện tử kèm bước cơ quan thuế cấp mã** (SandboxInvoice) và **dịch vụ ký số từ xa có CA riêng** (SandboxSign). Mục đích là để demo đúng mô hình tích hợp thật: merchant gọi API bằng API key, người dùng thao tác trên trang của nhà cung cấp, kết quả trả về bằng callback có chữ ký HMAC. **Không có giao dịch tiền thật, hóa đơn và chữ ký không có giá trị pháp lý.**

## Tài liệu

- [`AGENTS.md`](AGENTS.md) — entry point cho AI agent, trỏ vào [`.ai/`](.ai/).
- [`TASKS.md`](TASKS.md) — tiến độ theo task.
- [`docs/API.md`](docs/API.md) — API reference cho team viết client.
- [`docs/INTEGRATION.md`](docs/INTEGRATION.md) — hướng dẫn tích hợp.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — triển khai production.

## Chạy local

Cổng local: **28080** (dải `20000–29999`). Database là SQLite nhúng ở `data/sandbox_service.db` (gitignore), không cần container.

```bash
cp .env.example .env          # ở ROOT; điền SECRET_KEY, SANDBOX_API_KEY, SANDBOX_WEBHOOK_SECRET
# SANDBOX_API_KEY và SANDBOX_WEBHOOK_SECRET phải trùng với .env của procurehub

cd backend
~/.pyenv/versions/3.11.15/bin/python -m venv .venv311
.venv311/bin/pip install -r requirements/dev.txt
.venv311/bin/python manage.py migrate
.venv311/bin/python manage.py runserver 127.0.0.1:28080
```

Kiểm tra: `curl http://127.0.0.1:28080/health/` trả `{"status": "ok"}`. Trang người dùng: `/gateway/checkout/<id>/`, `/esign/sign/<id>/`, `/einvoice/lookup/?code=<mã>`.

## Test

```bash
cd backend
SECRET_KEY=test SANDBOX_API_KEY=test SANDBOX_WEBHOOK_SECRET=test .venv311/bin/python manage.py test
```

Test bắt callback bằng cách thay `urllib.request.urlopen` (`core/testing.py`), không gọi mạng thật. **Build xanh không phải bằng chứng đủ** — chạy thêm luồng thật cùng ProcureHub (xem [`docs/INTEGRATION.md`](docs/INTEGRATION.md)).

## Build & deploy

```bash
cp deploy/.env.registry.example .env.registry   # điền REGISTRY_USER / REGISTRY_PASS
./build.sh

cp .env.sync.example .env.sync                  # điền SSH_HOST/SSH_USER/DEPLOY_PATH
./sync-deploy.sh                                # đồng bộ deploy/ lên server qua SSH

# rồi SSH vào server (lệnh sync-deploy.sh vừa in ra), trong deploy/
cp .env.prod.example .env.prod   # lần đầu
./deploy.prod.sh
```

Chi tiết: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
