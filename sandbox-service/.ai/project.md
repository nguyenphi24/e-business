# Project

## Là gì

sandbox-service đứng ở vị trí "hệ thống bên ngoài" trong kiến trúc ProcureHub (repo `../procurehub`). Nó giả lập ba loại nhà cung cấp mà nền tảng mua sắm B2B cần tích hợp:

| Module | Giả lập | Người dùng thao tác ở đâu |
|---|---|---|
| `gateway` | Cổng thanh toán nội địa (redirect + IPN) | `/gateway/checkout/<id>/` |
| `einvoice` | Nhà cung cấp hóa đơn điện tử + cơ quan thuế cấp mã bất đồng bộ | `/einvoice/lookup/?code=` |
| `esign` | Dịch vụ ký số từ xa: CA gốc, chứng thư theo MST, OTP | `/esign/sign/<id>/` |

## Trạng thái

- 15 test tự động pass (`manage.py test`).
- Đã chạy luồng thật cùng ProcureHub qua HTTP: thanh toán 30% rồi phần còn lại qua cổng, IPN gửi lại không cộng tiền hai lần; hóa đơn điện tử chờ ~3 giây rồi được cấp mã và tra cứu được; ký OTP rồi ProcureHub xác minh chữ ký, phát hiện được dữ liệu báo giá bị sửa.
- Đã build image và chạy container local với named volume `/data`: health OK, thiếu secret thì dừng. Chưa triển khai lên server thật.

Việc còn mở, **cố tình để dở, đừng tưởng là bug**:

- Khóa riêng của CA và người ký lưu thẳng trong SQLite, không mã hóa — chấp nhận vì là sandbox; không dùng lại mã này cho hệ thống thật.
- Chứng thư là JSON do CA ký bằng Ed25519, **không phải X.509**; không có CRL/OCSP.
- Ký hiệu hóa đơn có tiền tố `SBX`, mã cơ quan thuế dạng `SBX<yy>-<hex>`, XML có thẻ gốc `HoaDonGiaLap` — cố ý không giống định dạng hóa đơn điện tử thật để không bị dùng nhầm.
- Callback gửi một lần, không tự thử lại; merchant hỏi lại bằng API GET hoặc gọi `resend-ipn` (dùng để demo xử lý trùng).
- Cấp mã hóa đơn dùng `threading.Timer`; timer mất khi tiến trình khởi động lại, bù bằng `issue_if_due()` khi có người đọc hóa đơn.

## Quyết định đáng chú ý (đọc trước khi thay đổi)

- **Một service gom ba nhà cung cấp** thay vì ba service: đây là đồ giả lập cho demo, tách ba repo chỉ thêm việc vận hành. Ba module độc lập, không import chéo, nên tách sau dễ.
- **Trang người dùng render bằng Django template**, không SPA: trang nhà cung cấp thật cũng là trang riêng của họ, và không cần build frontend.
- **SQLite**: dữ liệu giả lập, một tiến trình là đủ; không cần thêm container database.
- **Allowlist callback và return URL** (`ALLOWED_CALLBACK_PREFIXES`, `ALLOWED_RETURN_PREFIXES`): không cho dùng sandbox để gọi hay chuyển hướng tới địa chỉ tùy ý.
