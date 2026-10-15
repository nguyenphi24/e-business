# Kịch bản demo ProcureHub (10–12 phút)

Một công ty mua (VNPT Media) cần báo giá thiết bị phòng họp, mời hai nhà cung cấp (TechVision, Digital Supply). Kịch bản đi trọn chuỗi Source-to-Pay: đề nghị mua → duyệt → mời báo giá → nhà cung cấp xác nhận và báo giá (có ký số) → chấm điểm, đề xuất, duyệt → đơn đặt hàng → nhận hàng → hóa đơn VAT và hóa đơn điện tử → thanh toán qua cổng → dashboard.

Thanh toán, hóa đơn điện tử và chữ ký số chạy trên sandbox-service, là đối tác giả lập, không có giá trị pháp lý.

## 1. Chuẩn bị (trước giờ demo 10 phút)

```bash
./run.local.sh reset     # làm mới dữ liệu demo của ProcureHub và sandbox-service, rồi khởi động
```

Dữ liệu sau khi reset:

- 4 công ty, 8 tài khoản (bảng dưới), mật khẩu chung `Demo@2026`.
- Sẵn một chuỗi mẫu đã hoàn tất (RFQ-2026-0001, PO-2026-0001, INV-2026-0001 trả một phần) để dashboard có số liệu, và một PR "Bàn phím và chuột cho phòng họp" đã duyệt (PR-2026-0001) để dùng khi cần rút ngắn.
- sandbox-service: CA giả lập và chứng thư ký số cho hai nhà cung cấp; không còn giao dịch, hóa đơn điện tử, yêu cầu ký cũ. Số hóa đơn điện tử bắt đầu lại từ `SBX26/1`.

Mở 5 cửa sổ trình duyệt riêng, mỗi cửa sổ một vai trò. Các tab trong cùng một trình duyệt dùng chung phiên đăng nhập, nên phải dùng profile khác nhau hoặc cửa sổ ẩn danh của các trình duyệt khác nhau (ví dụ Chrome, Chrome ẩn danh, Edge, Firefox, Safari).

| Cửa sổ | Tài khoản | Người dùng | Vai trò trong kịch bản |
|---|---|---|---|
| 1 | `buyer@vnptmedia.demo` | Nguyễn Minh Anh (Mua hàng) | Tạo PR, RFQ, đề xuất, PO, nhận hàng |
| 2 | `manager@vnptmedia.demo` | Trần Quốc Bảo (Trưởng phòng mua hàng) | Duyệt PR, duyệt lựa chọn, xem dashboard |
| 3 | `finance@vnptmedia.demo` | Lê Thu Hà (Kế toán công nợ) | Nhận hóa đơn, thanh toán |
| 4 | `sales@techvision.demo` | Võ Hoàng Nam (Kinh doanh TechVision) | Nhà cung cấp 1: báo giá rẻ, ký số |
| 5 | `sales@digitalsupply.demo` | Đặng Thùy Linh (Kinh doanh Digital Supply) | Nhà cung cấp 2: báo giá giao nhanh |

Tài khoản khác: `buyer@otherbuyer.demo` (công ty khác, dùng thử truy cập trái quyền), `admin@vnptmedia.demo`, `sysadmin@procurehub.demo`.

Giao diện: http://localhost:43000 · sandbox-service: http://localhost:28080

## 2. Kịch bản

| Bước | Thời gian | Cửa sổ | Thao tác | Điểm cần chỉ cho người xem |
|---|---|---|---|---|
| 0 | 0:00–1:30 | — | Giới thiệu vấn đề, vai trò, sơ đồ luồng | Mua sắm qua email/Excel khó so sánh, khó kiểm soát |
| 1 | 1:30–2:30 | Buyer | Purchase Requests → **Tạo yêu cầu**: mục đích "Thiết bị phòng họp tầng 5", cần trước 20 ngày, ngân sách 70.000.000; dòng 1 "Màn hình 27 inch" 10 cái, dòng 2 "Cáp HDMI 3m" 20 sợi → **Gửi duyệt** | Ngân sách ước tính dùng làm mốc tính KPI tiết kiệm |
| 2 | 2:30–3:00 | Manager | Chuông thông báo hiện "PR chờ duyệt" (không cần tải lại trang) → **Duyệt** | Thông báo realtime (SSE) |
| 3 | 3:00–4:00 | Buyer | RFQ & báo giá → **Tạo RFQ**: chọn PR vừa duyệt, tiêu đề "Báo giá thiết bị phòng họp", hạn 3 ngày, chọn cả TechVision và Digital Supply → **Tạo RFQ nháp** → **Phát hành** | Mời ≥ 2 nhà cung cấp; trọng số mặc định 45/25/20/10 |
| 4 | 4:00–5:00 | TechVision, Digital Supply | Chuông báo lời mời → mở RFQ (**Chi tiết**) → **Xác nhận tham gia** | Buyer mở chi tiết RFQ thấy bảng "Nhà cung cấp được mời" chuyển "Đã xem" → "Đã xác nhận", có thông báo |
| 5 | 5:00–6:30 | TechVision | Nhập báo giá: Màn hình 4.000.000, Cáp 120.000, giao 12 ngày, Net 30 → **Gửi báo giá** → **Ký số báo giá** → trang ký của sandbox, nhập mã OTP hiển thị trên trang → **Ký số** | Ký số qua đối tác ngoài, giá chưa gồm VAT |
| 5 | | Digital Supply | Màn hình 4.300.000, Cáp 110.000, giao 4 ngày, Net 45 → **Gửi báo giá** (không ký) | Có thể gửi trước giờ demo để tiết kiệm thời gian |
| 6 | 6:30–7:30 | Buyer | Mở RFQ → **Đóng** → xem bảng so sánh: Digital Supply 89,21 điểm, TechVision 79,28; cột "Chữ ký số": TechVision hợp lệ, Digital Supply chưa ký → **Đề xuất nhà cung cấp** TechVision, lý do "Giá thấp nhất, báo giá đã ký số; chấp nhận giao chậm hơn" | Điểm chỉ hỗ trợ, con người quyết định và phải ghi lý do |
| 7 | 7:30–8:00 | Manager | Thông báo "đề xuất chờ duyệt" → **Duyệt** | Tách nhiệm vụ: Buyer không tự duyệt được đề xuất của mình |
| 8 | 8:00–9:00 | Buyer → TechVision → Buyer | Buyer **Tạo PO** → Purchase Orders → **Phát hành**; TechVision nhận thông báo → **Xác nhận**; Buyer **Ghi nhận giao hàng** (đủ số lượng) → **Lưu giao hàng** → **Hoàn tất** | PO khóa giá và điều khoản Net 30 từ báo giá |
| 9 | 9:00–10:00 | TechVision | Purchase Orders → **Lập hóa đơn** → Hóa đơn & thanh toán: 42.400.000 + VAT 10% 4.240.000 = 46.640.000; cột "Hóa đơn điện tử" từ "chờ cấp mã" sang ký hiệu `SBX26`, số 1 sau vài giây, mở link tra cứu | Hóa đơn điện tử qua nhà cung cấp giả lập |
| 10 | 10:00–11:00 | Finance | Thông báo hóa đơn mới → **Thanh toán** → **30%** → **Tiếp tục tới cổng thanh toán** → trang cổng sandbox, chọn ngân hàng → **Thanh toán thành công** → quay về: "trả một phần", còn 32.648.000; làm lại với **Toàn bộ** → "đã thanh toán" | Nền tảng không giữ tiền; cổng báo kết quả bằng IPN có chữ ký; TechVision nhận thông báo đã thanh toán |
| 11 | 11:00–12:00 | Manager, Other Buyer | Tổng quan: 6 KPI (thời gian duyệt PR, tỷ lệ báo giá, giao đúng hạn, tiết kiệm…); đăng nhập `buyer@otherbuyer.demo` không thấy hóa đơn của VNPT Media | Dữ liệu mẫu, không phải kết quả khảo sát; cô lập dữ liệu giữa các công ty |

Bước tùy chọn (nếu còn thời gian, sau bước 6): sửa trộm đơn giá trong DB để thấy chữ ký báo giá chuyển "không hợp lệ", rồi khôi phục.

```bash
cd procurehub/backend
.venv311/bin/python manage.py demo_tamper_quotation --rfq RFQ-2026-0002 --supplier-tax-code 0200000002 --unit-price 3500000
# Buyer tải lại bảng so sánh: "Chữ ký không hợp lệ – nội dung báo giá đã bị thay đổi sau khi ký"
.venv311/bin/python manage.py demo_tamper_quotation --rfq RFQ-2026-0002 --supplier-tax-code 0200000002 --unit-price 4000000
```

Nhánh phụ nên biết để trả lời câu hỏi: nhà cung cấp có thể **Từ chối** lời mời (bắt buộc ghi lý do, Buyer nhận thông báo); NCC từ chối PO; Manager từ chối PR hoặc đề xuất; trên cổng thanh toán bấm **Giao dịch thất bại** thì hóa đơn giữ nguyên số dư.

## 3. Rút ngắn khi thiếu thời gian

- Bỏ bước 1–2: dùng PR-2026-0001 "Bàn phím và chuột cho phòng họp" đã duyệt sẵn để tạo RFQ.
- Cho Digital Supply xác nhận và gửi báo giá trước giờ demo.
- Bỏ bước 11 phần trái quyền.

## 4. Sự cố thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Đăng nhập vai trò này làm mất phiên vai trò kia | Hai vai trò đang dùng chung trình duyệt; mở cửa sổ ẩn danh hoặc profile khác |
| Không thấy nút ký số, hóa đơn điện tử "chưa gửi" | sandbox-service chưa chạy; `./run.local.sh check`, rồi `./run.local.sh` |
| Số chứng từ không phải RFQ-2026-0002 / INV-2026-0002 | Dữ liệu chưa reset; chạy `./run.local.sh reset` |
| Sau reset, chữ ký cũ báo không hợp lệ | Chỉ xảy ra khi chạy `seed_sandbox --reset-ca`; chạy lại `./run.local.sh reset` |

Kịch bản này đã chạy tự động qua API ngày 15/10/2026 trên dữ liệu vừa reset; kết quả ở `docs/specs/04_Test_Demo.md` mục 3.
