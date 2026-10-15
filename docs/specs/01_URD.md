# URD — Yêu cầu người dùng ProcureHub

## 1. Phạm vi tài liệu

Tài liệu mô tả yêu cầu người dùng của ProcureHub: vai trò, phạm vi, quy trình, user stories, quy tắc nghiệp vụ và tiêu chí nghiệm thu. Đặc tả phần mềm ở Phụ lục B, kiến trúc ở Phụ lục C, kết quả kiểm thử ở Phụ lục D.

Quy ước trạng thái từng yêu cầu: **Proposed** (đề xuất), **Implemented** (đã có trong mã nguồn), **Tested** (có test tự động chạy pass). Trạng thái thực tế ghi ở Phụ lục D mục 4.


## 2. Tóm tắt

ProcureHub là nền tảng SaaS E-Procurement B2B có **Buyer Portal** và **Supplier Portal** trên cùng một hệ thống đa doanh nghiệp (multi-tenant). Hệ thống bao phủ chuỗi Source-to-Order (PR → phê duyệt → RFQ → báo giá → so sánh → duyệt lựa chọn → PO → nhận hàng) và mở rộng thành **Source-to-Pay ở mức ghi nhận**:

- thông báo thời gian thực (SSE) và hộp thư thông báo lưu trong database;
- chấm điểm báo giá theo trọng số có công bố công thức;
- hóa đơn có VAT 10%, công nợ theo điều khoản Net N ngày, thanh toán nhiều lần qua **cổng thanh toán giả lập** có webhook idempotent;
- **hóa đơn điện tử giả lập**: gửi hóa đơn sang nhà cung cấp hóa đơn điện tử, "cơ quan thuế" cấp mã, tra cứu được;
- **ký số báo giá** qua dịch vụ ký số từ xa giả lập (OTP, chứng thư do CA giả lập cấp), phát hiện được dữ liệu bị sửa sau khi ký;
- đánh giá nhà cung cấp sau giao hàng và bộ KPI mua sắm trên dashboard.

Ba dịch vụ bên ngoài (cổng thanh toán, hóa đơn điện tử, ký số) được giả lập bằng một service riêng (`sandbox-service`) để demo đúng mô hình tích hợp: gọi API bằng khóa, người dùng thao tác trên trang của nhà cung cấp, kết quả trả về bằng callback có chữ ký.

ProcureHub **không giữ tiền và không thu phí giao dịch**: thanh toán thật diễn ra ngoài nền tảng (ngân hàng của doanh nghiệp); nền tảng chỉ ghi nhận, đối soát và mô phỏng.

## 3. Bối cảnh và vấn đề

Ở SME, mua sắm phân tán trên email, Excel, Zalo: khó truy lại báo giá, phê duyệt không rõ trách nhiệm, chọn nhà cung cấp theo cảm tính, và sau khi đặt hàng thì công nợ được theo dõi trên một bảng tính khác. Ngoài luồng đặt hàng, hệ thống giải quyết thêm hai điểm nghẽn:

1. Các bên phải tự vào hệ thống kiểm tra trạng thái → **thông báo realtime** rút ngắn thời gian phản hồi RFQ và phê duyệt.
2. Dữ liệu dừng ở PO → **hóa đơn, hạn trả và lịch sử thanh toán** gắn với PO giúp Finance đối soát và giúp đo chu trình mua sắm đầy đủ.

## 4. Mục tiêu và tiêu chí thành công

| Mục tiêu | Tiêu chí đo |
|---|---|
| Số hóa luồng mua từ nhu cầu đến đối soát thanh toán | Demo trọn một giao dịch PR → … → Invoice → Payment trên dữ liệu seed |
| Hợp tác trực tiếp Buyer–Supplier | Supplier nhận lời mời, báo giá, xác nhận PO, lập hóa đơn trong Supplier Portal |
| Kiểm soát và minh bạch | RBAC + tách quyền + audit log cho 100% thao tác đổi trạng thái; công thức chấm điểm hiển thị |
| Hỗ trợ quyết định | Bảng so sánh có điểm trọng số; dashboard có 6 KPI định nghĩa rõ |
| Phản hồi nhanh | Thông báo xuất hiện ở trình duyệt người nhận mà không cần refresh |

## 5. Stakeholder và vai trò

Cột "Tên gọi nghiệp vụ" là cách gọi thường gặp trong tài liệu mua sắm.

| Vai trò (mã) | Tên gọi nghiệp vụ | Nhu cầu chính |
|---|---|---|
| Buyer (`BUYER`) | Requester + Procurement Officer | Lập PR, tạo RFQ, mời NCC, so sánh/chấm điểm, đề xuất NCC, phát hành PO, nhận hàng, đánh giá NCC |
| Manager (`MANAGER`) | Approver/Manager | Duyệt/từ chối PR và lựa chọn NCC; không tự duyệt bản ghi do mình tạo |
| Finance (`FINANCE`) — **mới** | Finance | Xem hóa đơn, hạn trả, công nợ; ghi nhận và mô phỏng thanh toán |
| Supplier (`SUPPLIER`) | Supplier User | Nhận lời mời, báo giá trước hạn, xác nhận/từ chối PO, lập hóa đơn |
| Company Admin (`COMPANY_ADMIN`) | Organization Admin | Quản trị user, vai trò, quan hệ NCC của doanh nghiệp |
| System Admin (`SYSTEM_ADMIN`) | Platform Admin | Vận hành nền tảng, hỗ trợ demo |

Ghi chú: nhiều hệ thống tách Requester và Procurement Officer; ProcureHub gộp thành Buyer vì SME mục tiêu thường chỉ có một người mua hàng. Tách quyền vẫn được bảo đảm vì Manager là người duyệt.

## 6. Phạm vi

### 6.1 Phân mức ưu tiên

| Mức | Phạm vi |
|---|---|
| **P0 — bắt buộc cho demo** | Auth, RBAC, tenant, PR, RFQ, quotation, selection, PO, delivery, dashboard, audit **+** notification (inbox + SSE) **+** chấm điểm báo giá theo trọng số **+** request ID trong audit |
| **P1 — nên có** | Hóa đơn VAT 10%, Net N ngày, thanh toán nhiều lần qua cổng giả lập + webhook idempotent; hóa đơn điện tử giả lập; ký số báo giá giả lập; vai trò Finance; đánh giá NCC; KPI dashboard; ngân sách ước tính của PR |
| **P2 — mở rộng sau MVP** | Chat theo RFQ; đính kèm tệp/OCR báo giá; ký số PO và hóa đơn; kết nối cổng thanh toán, nhà cung cấp hóa đơn điện tử và dịch vụ ký số thật; tích hợp ERP/kế toán; gợi ý NCC bằng AI; email notification; phê duyệt nhiều cấp theo hạn mức |

### 6.2 Ngoài phạm vi

Logistics thật, chuyển tiền thật, hóa đơn điện tử có giá trị pháp lý theo Nghị định 123/2020 (sửa đổi bởi Nghị định 70/2025), chữ ký số do tổ chức chứng thực được cấp phép cấp, nhiều thuế suất VAT, đa tiền tệ có quy đổi, mô hình AI huấn luyện mới.

## 7. Giả định và ràng buộc

- Company và user được seed sẵn; không có luồng tự đăng ký (D-01).
- Báo giá, PO, bảng điểm và KPI dùng giá trước thuế. VAT cố định 10%, chỉ tính khi lập hóa đơn: tổng hóa đơn = tổng PO + 10%.
- Thanh toán, hóa đơn điện tử và chữ ký đều giả lập; mọi màn hình liên quan gắn nhãn **"Sandbox/Giả lập"**, không nhận dữ liệu thẻ hay tài khoản ngân hàng, không có giá trị pháp lý.
- Một hóa đơn còn hiệu lực cho mỗi PO trong MVP.
- Mỗi doanh nghiệp là một tenant; Supplier chỉ thấy dữ liệu thuộc quan hệ được mời.

## 8. Quy trình nghiệp vụ TO-BE (Source-to-Pay)

```text
Buyer tạo PR (kèm ngân sách ước tính) → Manager duyệt
→ Buyer tạo RFQ, đặt trọng số chấm điểm, mời ≥ 2 NCC → publish  [thông báo NCC]
→ NCC gửi/sửa báo giá trước hạn, ký số báo giá bằng OTP           [thông báo Buyer]
→ Buyer đóng RFQ, xem bảng so sánh có điểm, đề xuất NCC + lý do   [thông báo Manager]
→ Manager duyệt lựa chọn (không tự duyệt)                          [thông báo Buyer]
→ Buyer sinh và phát hành PO (khóa giá, điều khoản, Net N)         [thông báo NCC]
→ NCC xác nhận/từ chối PO → Buyer ghi nhận giao hàng → hoàn tất PO
→ NCC lập hóa đơn (VAT 10%, hạn trả = ngày lập + N ngày)           [thông báo Finance]
→ hóa đơn gửi sang nhà cung cấp hóa đơn điện tử → CQT cấp mã      [thông báo Finance + NCC]
→ Finance tạo lệnh thanh toán (một hoặc nhiều lần) → trang cổng thanh toán
→ cổng gọi IPN có chữ ký → backend đối soát, cập nhật số dư        [thông báo Finance + NCC]
→ Buyer đánh giá NCC (dùng cho điểm uy tín ở các RFQ sau)
```

## 9. User stories

| ID | User story | Ưu tiên |
|---|---|---|
| UR-01 | Là Buyer, tôi muốn tạo PR gồm mặt hàng, số lượng, ngày cần và ngân sách ước tính. | P0 (ngân sách: P1) |
| UR-02 | Là Manager, tôi muốn duyệt hoặc trả lại PR kèm lý do. | P0 |
| UR-03 | Là Buyer, tôi muốn tạo RFQ từ PR đã duyệt và mời ít nhất hai NCC có quan hệ. | P0 |
| UR-04 | Là Supplier, tôi muốn chỉ thấy RFQ được mời và gửi báo giá mà đối thủ không xem được. | P0 |
| UR-05 | Là Buyer, tôi muốn so sánh báo giá theo tiêu chí có trọng số do tôi điều chỉnh, và thấy công thức. | P0 |
| UR-06 | Là Manager, tôi muốn duyệt lựa chọn NCC trước khi PO được phát hành. | P0 |
| UR-07 | Là người liên quan, tôi muốn nhận thông báo ngay khi trạng thái nghiệp vụ thay đổi, và vẫn xem được thông báo đã lỡ khi mất kết nối. | P0 |
| UR-08 | Là Supplier, tôi muốn xác nhận PO và lập hóa đơn sau khi giao hàng. | P1 |
| UR-09 | Là Finance, tôi muốn theo dõi hóa đơn, ngày đến hạn, quá hạn và ghi nhận thanh toán một phần hoặc nhiều lần. | P1 |
| UR-10 | Là Buyer, tôi muốn chấm điểm NCC sau khi hoàn tất PO. | P1 |
| UR-11 | Là Manager, tôi muốn xem KPI mua sắm (thời gian duyệt, chu trình, tỷ lệ báo giá, giao đúng hạn, tiết kiệm). | P1 |
| UR-12 | Là Supplier, tôi muốn ký số báo giá đã gửi để bên mua tin rằng giá không bị sửa. | P1 |
| UR-13 | Là Buyer, tôi muốn thấy báo giá nào đã ký số hợp lệ và biết ngay nếu dữ liệu bị thay đổi sau khi ký. | P1 |
| UR-14 | Là Finance, tôi muốn hóa đơn có mã cơ quan thuế và tra cứu được, rồi thanh toán qua cổng thanh toán. | P1 |

## 10. Quy tắc nghiệp vụ

| ID | Quy tắc |
|---|---|
| BR-01 | Người dùng phải đăng nhập; mỗi request xác định company và vai trò; tài khoản bị vô hiệu hóa không đăng nhập được. |
| BR-02 | Company Admin chỉ quản lý người dùng của company mình. |
| BR-03 | NCC là company loại SUPPLIER có sẵn; bên mua tạo hoặc kích hoạt quan hệ (invited, active, inactive, blocked); chỉ NCC có quan hệ active được mời. |
| BR-04 | PR gồm mục đích, ngày cần hàng, tiền tệ và ít nhất một dòng; PR đã gửi chỉ sửa được sau khi bị từ chối; từ chối phải có lý do. |
| BR-05 | RFQ tạo từ PR đã duyệt, hạn chót ở tương lai. |
| BR-06 | Báo giá phải có giá cho mọi dòng RFQ, số lượng bằng số lượng RFQ, giá chưa gồm VAT; NCC sửa lại được trước hạn, mỗi lần gửi lưu bản chụp. |
| BR-07 | Buyer chỉ đề xuất NCC sau khi RFQ đóng, kèm lý do; Manager khác người đề xuất duyệt trước khi sinh PO. |
| BR-08 | PO lưu bản chụp NCC, dòng hàng, giá, điều khoản; NCC có thể từ chối PO kèm lý do, khi đó RFQ mở lại để chọn NCC khác. |
| BR-09 | Dashboard chỉ tính dữ liệu trong phạm vi quyền. |
| BR-10 | Sự kiện quan trọng lưu người thực hiện, hành động, bản ghi, thời điểm; audit chỉ ghi thêm. |
| BR-11 | Chỉ PR `APPROVED` được dùng để tạo RFQ; RFQ phải mời ≥ 2 NCC có quan hệ `ACTIVE`. |
| BR-12 | Hạn chót kiểm tra theo giờ máy chủ; không nhận hoặc sửa báo giá sau hạn. |
| BR-13 | Supplier chỉ thấy lời mời, báo giá, PO, hóa đơn của chính mình; không thấy báo giá đối thủ. |
| BR-14 | Tách quyền: người tạo PR không duyệt PR đó; người đề xuất NCC không duyệt lựa chọn đó. |
| BR-15 | Lựa chọn NCC luôn có lý do; điểm trọng số tại thời điểm đề xuất được lưu kèm để truy vết. Điểm là công cụ hỗ trợ, không tự động quyết định. |
| BR-16 | Trọng số chấm điểm là số nguyên 0–100, tổng = 100; chỉ đổi khi RFQ chưa `AWARDED`/`CANCELLED`. Không gọi cơ chế này là AI. |
| BR-17 | PO là snapshot báo giá được chọn (giá, thời gian giao, điều khoản, số ngày công nợ); không sửa sau khi sinh. |
| BR-18 | Hóa đơn chỉ lập khi PO đã `DELIVERED` hoặc `COMPLETED`; tiền trước thuế = tổng PO, VAT 10%, tổng phải trả = trước thuế + VAT; hạn trả = ngày lập + số ngày công nợ của PO (mặc định 30). |
| BR-19 | Thanh toán chỉ được ghi nhận khi backend nhận sự kiện từ cổng (webhook) đã xác thực chữ ký; frontend báo thành công không có giá trị. Sự kiện trùng `event_id` chỉ xử lý một lần. |
| BR-20 | Tổng các lệnh thanh toán đang chờ và đã thành công không vượt giá trị hóa đơn. |
| BR-21 | Mỗi PO `COMPLETED` được Buyer đánh giá tối đa một lần (chất lượng, giao hàng, thang 1–5). |
| BR-22 | Thông báo chỉ gửi đúng người nhận thuộc đúng tenant và không chứa giá báo giá. |
| BR-23 | Chữ ký số gắn với một lần gửi (revision) báo giá; chỉ chấp nhận chữ ký do CA tin cậy cấp cho đúng mã số thuế của nhà cung cấp. Nội dung báo giá đổi sau khi ký thì chữ ký phải hiển thị "không hợp lệ". |
| BR-24 | Hóa đơn đã gửi cơ quan thuế (đang chờ mã hoặc đã có mã) không được hủy; muốn sửa phải lập hóa đơn điều chỉnh (chưa hỗ trợ). |

## 11. Tiêu chí nghiệm thu

| ID | Tiêu chí |
|---|---|
| AC-01 | Buyer đăng nhập và tạo được PR có ít nhất hai dòng hàng. |
| AC-02 | PR đã gửi xuất hiện trong hàng đợi của Manager; Buyer không tự duyệt được. |
| AC-03 | PR đã duyệt tạo được RFQ mời ít nhất hai NCC active, hạn chót ở tương lai. |
| AC-04 | Mỗi NCC được mời gửi được báo giá đủ giá dòng và điều khoản. |
| AC-05 | Buyer xem được bảng so sánh mọi báo giá đã gửi, tổng tiền tính đúng. |
| AC-06 | Manager duyệt lựa chọn; chỉ sau đó hệ thống mới tạo PO. |
| AC-07 | PO giữ đúng NCC, giá và điều khoản của báo giá được chọn. |
| AC-08 | Buyer và NCC không truy cập được dữ liệu ngoài company hoặc quan hệ được phép. |
| AC-09 | Dashboard thay đổi theo hành động nghiệp vụ và chỉ hiển thị dữ liệu được phép. |
| AC-10 | Kiểm tra được ai đã tạo, duyệt, chọn và phát hành từng giao dịch. |
| AC-11 | Khi Supplier B gửi báo giá, Buyer của RFQ nhận thông báo realtime; Supplier C không nhận và không thấy nội dung. |
| AC-12 | Khi ngắt kết nối SSE rồi mở lại, người dùng vẫn thấy thông báo chưa đọc qua REST. |
| AC-13 | Bảng so sánh hiển thị điểm thành phần, trọng số và tổng điểm khớp công thức. |
| AC-14 | Webhook thanh toán gửi lại cùng `event_id` chỉ ghi nhận một lần; chữ ký sai bị từ chối. |
| AC-15 | Thanh toán 30% hóa đơn đưa hóa đơn sang `PARTIALLY_PAID` với số dư đúng; trả nốt thì `PAID`. |
| AC-16 | User tenant A gọi URL hóa đơn/thông báo của tenant B nhận 404, không lộ dữ liệu. |
| AC-17 | Supplier ký báo giá bằng OTP → bên mua thấy "chữ ký hợp lệ"; sửa giá trực tiếp trong DB → chuyển "không hợp lệ". |
| AC-18 | Hóa đơn được cấp ký hiệu, số, mã cơ quan thuế (giả lập) và tra cứu được bằng mã tra cứu. |
| AC-19 | Thanh toán qua trang cổng: số dư chỉ đổi khi backend nhận IPN có chữ ký; IPN gửi lại không cộng tiền hai lần. |

## 12. Kỳ vọng phi chức năng ở mức nghiệp vụ

- Thông báo hiển thị trong vài giây sau sự kiện (mục tiêu ≤ 5 giây ở môi trường demo).
- Mọi số tiền tính bằng Decimal; số dư hóa đơn luôn = tổng − đã trả thành công.
- Giao diện ghi rõ "Giá chưa bao gồm VAT" ở báo giá, tách tiền trước thuế/VAT/tổng ở hóa đơn, và nhãn "Sandbox/Giả lập" ở mọi màn hình thanh toán, hóa đơn điện tử, ký số.

## 13. Kịch bản demo (8–12 phút)

1. Phút 0–2: vấn đề, vai trò, sơ đồ Buyer/Supplier/Finance.
2. Phút 2–4: Buyer tạo PR (Màn hình ×10, Cáp HDMI ×20, Android Box ×5, ngân sách ước tính), Manager duyệt, Buyer tạo RFQ mời TechVision và Digital Supply.
3. Phút 4–6: mở trình duyệt thứ hai đăng nhập Supplier, chuông thông báo hiện lời mời không cần refresh; hai NCC gửi báo giá (TechVision rẻ hơn giao lâu hơn, Digital Supply đắt hơn giao nhanh hơn, khác số ngày công nợ); TechVision ký số báo giá bằng OTP.
4. Phút 6–8: Buyer nhận thông báo, đóng RFQ, chỉnh trọng số, xem bảng điểm và cột chữ ký số, đề xuất NCC; Manager duyệt; Buyer sinh và phát hành PO. (Tùy chọn: sửa trộm giá trong DB để thấy chữ ký chuyển "không hợp lệ".)
5. Phút 8–10: Supplier xác nhận PO; Buyer ghi nhận giao hàng; Supplier lập hóa đơn Net 30 có VAT 10%, vài giây sau có mã cơ quan thuế và mở trang tra cứu; Finance thanh toán 30% qua trang cổng thanh toán rồi phần còn lại.
6. Phút 10–12: Buyer đánh giá NCC; xem dashboard KPI, audit timeline; thử truy cập trái quyền (tenant khác) bị chặn.

## 14. Quyết định tạm hoãn

Phê duyệt nhiều cấp theo hạn mức (ví dụ < 20 triệu / 20–100 triệu / > 100 triệu) được ghi nhận làm cấu hình P2; MVP dùng một cấp Manager.
