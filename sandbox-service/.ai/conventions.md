# Conventions

Chuẩn Django dùng chung: `~/workspace/conventions/stacks/django.md` (không chép lại ở đây). File này chỉ ghi điều riêng của repo.

## Ngôn ngữ & build

Python 3.11.15 qua pyenv, venv `backend/.venv311`. Django 5.2 + DRF. Thụt lề bằng **tab** (theo template init.sh); migration do Django sinh giữ nguyên dấu cách.

## Pattern code

- Mỗi module có `models.py`, `serializers.py` (validate + hàm `*_payload` dựng JSON trả về), `services.py` (nghiệp vụ, khóa dòng, gửi callback), `api.py` (DRF view), `pages.py` (trang HTML).
- API merchant dùng `permission_classes = [HasMerchantApiKey]`; `DEFAULT_AUTHENTICATION_CLASSES` rỗng.
- Tạo mới idempotent theo mã của merchant (`merchant_ref`, `external_ref`): gọi lại trả 200 với bản ghi cũ.
- Gửi callback **sau** khi transaction commit (trong `services`), không gửi trong khi đang giữ khóa.

## Chỗ dễ sai nhất repo này

- Chuẩn hóa JSON khi ký phải giống hệt bên merchant: `json.dumps(..., separators=(",", ":"), sort_keys=True, ensure_ascii=False)`. Đổi một tham số là mọi chữ ký HMAC/CA bên ProcureHub sai.
- Template init.sh để gunicorn nghe **8000** nhưng compose ban đầu ánh xạ 8080 — đã sửa thành `:8000`; health route là `/health/` có dấu `/`.
- Image không có sẵn `/data` thì named volume mới tạo thuộc root và user `app` (UID 10001) không tạo được file SQLite — Dockerfile phải `mkdir /data && chown app:app /data`. Đã gặp khi chạy thử container.
- `os.getenv("X", default)` không dùng được với biến compose để trống (compose truyền chuỗi rỗng) — dùng `os.getenv("X") or default`.
- Hiển thị số lượng trên trang hóa đơn phải qua filter `qty`: `10.000` (Decimal 3 chữ số) người Việt đọc thành mười nghìn.
- `core.exceptions` của template trả `message = str(exc)`; với `ValidationError` đó là repr Python — đã đổi thành "Request validation failed." (chi tiết ở `details`). Lỗi 403 thiếu API key giữ shape DRF `{"error": {"detail": ...}}` theo template.
- Trang ký và trang thanh toán có CSRF; script E2E phải lấy `csrfmiddlewaretoken` từ trang trước khi POST.

## Xác minh thay đổi

**Build thành công không phải bằng chứng đủ.**

1. Chạm database/migration → chạy thật với database thật.
2. Chạm API/xác thực → gọi thật, kiểm tra **cả mã HTTP lẫn shape JSON**.
3. Chạm callback → chạy cùng ProcureHub thật và xem merchant nhận/xác minh được.
4. Đừng báo "xong" chỉ vì build pass.
