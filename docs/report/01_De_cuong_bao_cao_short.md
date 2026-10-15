ĐẠI HỌC QUỐC GIA THÀNH PHỐ HỒ CHÍ MINH
TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN
KHOA HỆ THỐNG THÔNG TIN
[logo]
BÁO CÁO PROJECT MÔN HỌC
HỆ KINH DOANH ĐIỆN TỬ (E-BUSINESS)
Đề tài: B2B E-PROCUREMENT SYSTEM
Nền tảng mua sắm điện tử giữa doanh nghiệp với doanh nghiệp: Buyer Portal và Supplier Portal
Đề cương báo cáo – Lớp IS6101.11.CH
Giảng viên hướng dẫn: TS. Trần Văn Hải Triều
Nhóm học viên thực hiện: Nhóm 2
1. Tăng Quốc Hưng (Trưởng nhóm) – MSHV: 26848075
2. Trần Nguyễn Phi – MSHV: 26848163
3. Trần Thanh Vũ – MSHV: 26848269
4. Lê Trọng Đạo – MSHV: 26848032
TP. HỒ CHÍ MINH, THÁNG 10 NĂM 2026

[toc]

# 1. GIỚI THIỆU ĐỀ TÀI

## 1.1. Bối cảnh và vấn đề nghiên cứu

Tại nhiều SME, mua sắm vẫn diễn ra qua email, bảng tính và tin nhắn rời rạc: khó truy lại báo giá, khó kiểm soát ngân sách, chọn nhà cung cấp theo kinh nghiệm cá nhân, còn hóa đơn và công nợ được theo dõi ở một bảng tính khác.

**Vấn đề nghiên cứu:** làm thế nào thiết kế một hệ thống E-Procurement B2B vừa giảm thao tác thủ công, vừa bảo đảm phê duyệt tách quyền, minh bạch báo giá, có kiến trúc đủ tin cậy và có mô hình kinh doanh khả thi cho SME Việt Nam?

Nhóm đề xuất **ProcureHub**, nền tảng E-Procurement B2B theo mô hình SaaS, có Buyer Portal và Supplier Portal trên cùng một hệ thống đa doanh nghiệp. Hệ thống bao phủ chuỗi **Source-to-Pay ở mức ghi nhận**: PR → phê duyệt → RFQ → báo giá → so sánh có chấm điểm → duyệt lựa chọn → PO → nhận hàng → hóa đơn → đối soát thanh toán. Nền tảng không giữ tiền; trong demo, cổng thanh toán, hóa đơn điện tử và chữ ký số là các đối tác giả lập, tích hợp đúng cách như đối tác thật. Mọi số liệu tài chính là giả định minh họa.

## 1.2. Mục tiêu, phạm vi và phương pháp

Bảng 1.1. Mục tiêu, phạm vi và phương pháp

| Nội dung | Mô tả |
|---|---|
| Mục tiêu | Phân tích quy trình mua sắm B2B; xây dựng chiến lược E-business; chọn mô hình kinh doanh và doanh thu; thiết kế kiến trúc hệ thống; xây dựng KPI và mô hình tài chính. |
| Đối tượng | Mua hàng gián tiếp (MRO, văn phòng phẩm, thiết bị CNTT) của SME; vai trò Buyer, Manager, Finance, Supplier, quản trị. |
| Phạm vi | P0: luồng PR → PO, thông báo realtime, chấm điểm báo giá, audit. P1: hóa đơn VAT 10%, hóa đơn điện tử, thanh toán qua cổng, ký số báo giá (đối tác giả lập), đánh giá NCC, KPI. P2 (lộ trình): kết nối đối tác thật, ERP/kế toán, OCR, AI. |
| Phương pháp | Nghiên cứu tài liệu; phỏng vấn 6–10 người tại 3–5 doanh nghiệp; mô hình hóa quy trình; prototype; kiểm thử tự động và kiểm thử khả dụng 5–8 người dùng. |

## 1.3. Phân công

Tăng Quốc Hưng (trưởng nhóm): điều phối, biên tập, Mục 1, 9, 10. Trần Nguyễn Phi: cơ sở lý thuyết, mô hình kinh doanh, Mục 2, 5. Trần Thanh Vũ: phân tích nghiệp vụ, kiến trúc hệ thống, tài chính, Mục 3, 6, 8. Lê Trọng Đạo: chiến lược E-business, triển khai, Mục 4, 7.

# 2. CƠ SỞ LÝ THUYẾT

E-business dùng Internet, intranet và extranet để kết nối quy trình, giao dịch và cộng tác với khách hàng, nhà cung cấp; E-commerce chỉ là phần giao dịch mua bán (Chaffey, 2011). E-Procurement thuộc phía buy-side; phần nội bộ (PR, phê duyệt, đối soát) vận hành như intranet, Supplier Portal là extranet. Hiệu quả E-procurement phụ thuộc mức tích hợp và mức chấp nhận của người dùng (Davila et al., 2003; Croom & Brandon-Jones, 2007).

Khung phân tích: quy trình chiến lược E-business (Chaffey, 2011; Trần, 2026); Five Forces (Porter, 2001); SWOT, SMART, Balanced Scorecard (Kaplan & Norton, 1992); mô hình kinh doanh B2B (Laudon & Traver, 2021); chi phí giao dịch TCE (Williamson, 1981); UTAUT và SUS (Venkatesh et al., 2003; Brooke, 1996); mô hình kiến trúc C4 (Brown, 2018) và SaaS đa doanh nghiệp (Bezemer & Zaidman, 2010).

# 3. PHÂN TÍCH BÀI TOÁN VÀ GIẢI PHÁP NGHIỆP VỤ

## 3.1. Quy trình AS-IS và TO-BE

Bảng 3.1. Đối chiếu quy trình hiện tại (giả thuyết, xác minh ở M1) và đề xuất

| Công đoạn | AS-IS | TO-BE ProcureHub |
|---|---|---|
| Yêu cầu, phê duyệt | Email/chat, khó truy trách nhiệm | PR chuẩn hóa có ngân sách; Manager duyệt, tách quyền, nhận thông báo ngay |
| RFQ, báo giá | Gửi riêng từng NCC, tệp rời | Một RFQ mời ≥ 2 NCC; báo giá có cấu trúc, lưu phiên bản, NCC ký số |
| Chọn NCC | So sánh Excel, lý do không nhất quán | Bảng điểm trọng số công khai công thức, ghi lý do, Manager duyệt |
| PO, nhận hàng | Email, ghi chép thủ công | PO khóa giá và điều khoản Net N, NCC xác nhận online |
| Hóa đơn, thanh toán | Bảng tính riêng | Hóa đơn VAT 10% từ PO, hóa đơn điện tử có mã cơ quan thuế, Finance trả nhiều lần qua cổng, đối soát IPN |

![Hình 3.1. Luồng Source-to-Pay TO-BE theo vai trò](figures/fig_3_1_source_to_pay.png) {landscape}

## 3.2. Quy tắc nghiệp vụ và giá trị tạo ra

- **Tách quyền:** người tạo PR hoặc đề xuất NCC không được tự duyệt; máy chủ chặn và ghi log.
- **Bảo mật báo giá:** NCC không thấy giá đối thủ; hạn chót theo giờ máy chủ; thông báo không chứa giá.
- **Điểm hỗ trợ, con người quyết định:** trọng số do Buyer đặt (tổng 100), công thức công khai; chọn NCC không đứng đầu phải ghi lý do.
- **Chữ ký số báo giá:** chỉ tin chữ ký do CA tin cậy cấp cho đúng mã số thuế NCC; nội dung đổi sau khi ký thì chữ ký "không hợp lệ".
- **Hóa đơn và thanh toán:** chỉ lập hóa đơn khi PO đã giao; hóa đơn đã gửi cơ quan thuế không hủy được; thanh toán chỉ ghi nhận khi có IPN có chữ ký, đúng số tiền; gửi lại không ghi hai lần.

Theo bốn cách E-business tạo giá trị (Chaffey, 2011): gia tăng giá trị nhờ báo giá có cấu trúc; giảm chi phí giao dịch (TCE) và thời gian chờ; quản lý rủi ro nhờ tách quyền, đối soát có chữ ký, audit log; tạo cách làm mới khi dữ liệu mua sắm thành dữ liệu dùng chung, chuyển tri thức ẩn thành tri thức hiện.

# 4. CHIẾN LƯỢC E-BUSINESS

## 4.1. Phân tích môi trường

**SLEPT.** SME quen Zalo, Excel, lo lộ giá. Luật Giao dịch điện tử 20/2023/QH15 công nhận thông điệp dữ liệu; hóa đơn theo Nghị định 123/2020/NĐ-CP sửa đổi bởi Nghị định 70/2025/NĐ-CP (hóa đơn trong ProcureHub chỉ là chứng từ nội bộ); Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và Nghị định 356/2025/NĐ-CP. Quyết định 749/QĐ-TTg về chuyển đổi số tạo bối cảnh thuận lợi; cloud giảm chi phí hạ tầng.

Bảng 4.1. Five Forces – thị trường SaaS E-Procurement cho SME Việt Nam (Porter, 2001)

| Lực lượng | Mức độ | Hàm ý chiến lược |
|---|---|---|
| Cạnh tranh hiện tại | Trung bình – cao | Tập trung ngách, không đối đầu bộ Source-to-Pay quốc tế |
| Đối thủ mới | Cao | Lợi thế bằng dữ liệu báo giá, đánh giá NCC và đối tác |
| Sản phẩm thay thế | Cao | Gói Free, onboarding nhanh, thông báo tức thời |
| Quyền lực khách hàng | Cao | Thuê bao tháng, giá rõ, chứng minh ROI bằng dashboard |
| Quyền lực nhà cung cấp đầu vào | Thấp – trung bình | Công nghệ mã nguồn mở, không khóa vào một nhà cung cấp cloud |

Theo mô hình buy-side sáu bậc (Chaffey, 2011), SME mục tiêu ở bậc 1. ProcureHub đưa họ lên **bậc 4** (đặt hàng trực tuyến qua RFQ, PO); hóa đơn điện tử và đối soát với cổng thanh toán là bước chuẩn bị cho **bậc 5**, chưa đạt vì chưa tích hợp kế toán/ERP; KPI chi tiêu là bước đầu của bậc 6.

## 4.2. SWOT và mục tiêu chiến lược

Bảng 4.2. SWOT và chiến lược kết hợp

| | S: tách quyền, audit; bảng điểm minh bạch; realtime; chi phí thấp | W: chưa có khách hàng, dữ liệu thật; đối tác thanh toán, hóa đơn điện tử, ký số mới ở mức giả lập |
|---|---|---|
| O: chuyển đổi số; SME còn dùng Excel; đối tác kế toán/ERP | SO: tiếp cận SME qua đối tác kế toán/ERP, dùng KPI làm bằng chứng | WO: pilot có case study; tích hợp qua đối tác thay vì tự xây |
| T: công cụ miễn phí; counter-mediation; SME lo lộ giá | ST: lấy tách quyền, đối soát có chữ ký làm khác biệt | WT: phạm vi hẹp, giới hạn gói Free, nhãn sandbox rõ ràng |

**Tầm nhìn:** công cụ mua hàng minh bạch quen thuộc của SME Việt Nam, bổ trợ chứ không thay thế kế toán/ERP. **Sứ mệnh:** đưa việc mua hàng từ email, Excel sang quy trình có phê duyệt, báo giá so sánh được, công nợ theo dõi được, dùng được ngay ngày đầu.

Bảng 4.3. Mục tiêu SMART (tính từ ngày ra mắt sau pilot)

| Mục tiêu | KPI |
|---|---|
| Khách hàng mua sắm hiệu quả hơn | Giảm ≥ 30% thời gian PR → PO sau 3 tháng sử dụng |
| Có khách hàng trả phí | 3 khách hàng sau 6 tháng; Free → trả phí ≥ 10% |
| Hòa vốn vận hành | ≥ 18 khách hàng trả phí trong 18 tháng |
| Giữ chân khách hàng | Churn ≤ 3%/tháng; ≥ 60% tài khoản tạo RFQ đầu tiên trong 14 ngày |
| Kích hoạt nhà cung cấp | ≥ 70% lời mời được phản hồi đúng hạn |

# 5. MÔ HÌNH KINH DOANH

## 5.1. Mô hình B2B và tám yếu tố

ProcureHub chọn mô hình **E-procurement** trong nhóm Net marketplace (Laudon & Traver, 2021): nhà cung cấp dịch vụ SaaS giúp doanh nghiệp mua hàng gián tiếp, thu phí dịch vụ. Loại e-distributor (phải sở hữu hàng), exchange (cần lượng giao dịch lớn) và industry consortium (cần doanh nghiệp đầu ngành bảo trợ). ProcureHub không phải marketplace công khai và không đứng giữa dòng tiền; về tái cấu trúc thị trường là re-intermediation, cần đề phòng counter-mediation từ hãng kế toán/ERP.

Tên ProcureHub ghép từ procure (mua sắm) và hub (trung tâm kết nối), thể hiện vai trò điểm điều phối thông tin giữa bên mua và nhà cung cấp. Vì từ "procure" còn lạ với người dùng SME Việt Nam, thương hiệu đi kèm tagline "ProcureHub – Mua hàng minh bạch cho doanh nghiệp". Trước khi thương mại hóa, nhóm cần tra cứu trùng nhãn hiệu tại Cục Sở hữu trí tuệ và kiểm tra tên miền.

Bảng 5.1. Tám yếu tố của mô hình kinh doanh

| Yếu tố | ProcureHub |
|---|---|
| Value proposition | Bên mua: giảm tìm kiếm và so sánh giá, kiểm soát phê duyệt, theo dõi công nợ. NCC: RFQ có cấu trúc, thông báo tức thời, một tài khoản cho nhiều bên mua. |
| Revenue model | Thuê bao có freemium giới hạn; phí triển khai; không phí giao dịch |
| Market opportunity | SME TP.HCM mua gián tiếp 10–30 PR/tháng; SOM = khách tiếp cận được × ARPA × 12 |
| Competitive environment | SAP Ariba, Coupa, Odoo Purchase, phần mềm trong nước; gián tiếp: email, Excel, Zalo |
| Competitive advantage | Triển khai trong ngày, minh bạch, chi phí thấp; bền vững nhờ dữ liệu tích lũy và đối tác |
| Market strategy | Gói Free, pilot có case study, bán qua đối tác |
| Organization, management | Nhóm nhỏ đa năng; cần cố vấn mua hàng và kế toán |

## 5.2. Mô hình doanh thu và bảng giá

ProcureHub thu **thuê bao có freemium giới hạn**, phí triển khai là nguồn phụ, hoa hồng liên kết sau MVP. ProcureHub có ghi nhận thanh toán nhưng **vẫn không thu phí giao dịch**: tiền đi qua ngân hàng của doanh nghiệp, nền tảng chỉ ghi nhận; phí theo giá trị PO làm khách ngại đưa đơn lớn vào hệ thống; thu phí trên dòng tiền kéo theo nghĩa vụ của trung gian thanh toán. Không dùng quảng cáo để giữ tính trung lập của bảng điểm. Nhà cung cấp dùng miễn phí.

Bảng 5.2. Bảng giá giả định

| Gói | Giá/tháng | Giới hạn chính |
|---|---|---|
| Free | 0 | 3 người dùng, 3 RFQ/tháng; không có hóa đơn và KPI |
| Starter | 2 triệu đồng | 10 người dùng, 20 RFQ/tháng, thông báo realtime, hóa đơn |
| Business | 4 triệu đồng | 30 người dùng, không giới hạn RFQ, KPI, đánh giá NCC, xuất audit |
| Enterprise | Từ 8 triệu đồng | Tích hợp kế toán/ERP, cổng thanh toán đối tác, SLA |

Phí triển khai 5–15 triệu đồng; trả theo năm giảm tương đương hai tháng.

## 5.3. Tám quyết định định nghĩa chiến lược

Bảng 5.3. Tám quyết định chiến lược (Chaffey, 2011)

| Quyết định | Lựa chọn |
|---|---|
| D1. Kênh | Website và gói Free thu hút; bán trực tiếp và qua đối tác để chuyển đổi |
| D2. Thị trường – sản phẩm | SME TP.HCM → Invoice-to-Pay tích hợp, AI → tỉnh khác |
| D3. Định vị | Ngách + khác biệt bằng minh bạch; tăng chất lượng, giảm giá và thời gian đáp ứng |
| D4. Mô hình doanh thu | E-procurement SaaS, thuê bao freemium, không phí giao dịch |
| D5. Tái cấu trúc thị trường | Re-intermediation; đề phòng counter-mediation |
| D6. Chuỗi cung ứng | Extranet cho NCC; Invoice-to-Pay mức ghi nhận |
| D7. Tri thức | Lịch sử RFQ, điểm khi lựa chọn, lý do, đánh giá NCC, audit |
| D8. Nguồn lực | In-house giai đoạn đầu → đối tác kế toán/ERP, cổng thanh toán |

# 6. KIẾN TRÚC HỆ THỐNG VÀ GIẢI PHÁP CÔNG NGHỆ

## 6.1. Từ chiến lược đến kiến trúc

Bảng 6.1. Truy vết quyết định kinh doanh sang kiến trúc

| Lập luận kinh doanh | Quyết định kiến trúc |
|---|---|
| Khác biệt bằng minh bạch, tách quyền | RBAC, chống tự duyệt ở máy chủ, audit log chỉ ghi thêm có request ID |
| SME nhạy cảm chi phí, dùng được ngay | Modular monolith, một CSDL dùng chung, Docker; không Redis/Kafka |
| NCC dùng miễn phí, extranet | Supplier Portal trong cùng SPA, truy cập theo quan hệ được mời |
| Giảm chi phí tìm kiếm, giám sát (TCE) | Báo giá có cấu trúc, chấm điểm trọng số, phân quyền theo bản ghi |
| Giảm thời gian đáp ứng | Hộp thư thông báo + Server-Sent Events |
| Không thu phí giao dịch, không giữ tiền | Tiền đi qua cổng của đối tác; chỉ đối soát IPN ký HMAC; không lưu dữ liệu thẻ |
| Bảo mật báo giá, chống chối bỏ; đối tác chính | Ký số báo giá, xác minh bằng khóa CA tin cậy; adapter tích hợp đối tác thay được |
| Kiểm soát bằng KPI | Lưu mốc thời gian, module dashboard tính KPI |

![Hình 6.1. Kiến trúc container của ProcureHub (C4 mức 2)](figures/fig_6_1_architecture.png) {landscape}

![Hình 6.2. Mô hình dữ liệu khái niệm](figures/fig_6_2_erd.png) {landscape}

## 6.2. Kiến trúc tổng thể

Hệ thống gồm bốn khối (Hình 6.1): **Web SPA** (React, Ant Design) cho Buyer Portal và Supplier Portal; **API** (Django, Django REST Framework) là nơi duy nhất kiểm tra quyền và đổi trạng thái, chia 9 module: identity, suppliers, procurement, purchase_orders, billing, notifications, audit, dashboard, integrations; **PostgreSQL** lưu dữ liệu giao dịch, mỗi bản ghi gắn doanh nghiệp sở hữu; **sandbox-service** giả lập ba đối tác (cổng thanh toán, hóa đơn điện tử, ký số), nhận lời gọi bằng khóa API và báo kết quả bằng callback ký HMAC. Nhóm chọn modular monolith vì 4 người, MVP 4 tuần và chuỗi duyệt → PO → hóa đơn → thanh toán cần nhất quán trong một transaction; ranh giới module cho phép tách service sau.

## 6.3. Mô hình dữ liệu

Hệ thống dùng chung một cơ sở dữ liệu cho nhiều doanh nghiệp (shared schema, Hình 6.2). Mọi bản ghi nghiệp vụ gắn với doanh nghiệp sở hữu hoặc với quan hệ giữa hai doanh nghiệp (lời mời RFQ, PO, hóa đơn) để xác định ai được thấy. PO là bản chụp báo giá được chọn nên không đổi khi báo giá gốc thay đổi; tiền dùng kiểu số thập phân.

## 6.4. Các cơ chế chính

- **Bảo mật đa doanh nghiệp:** token ngắn hạn trong bộ nhớ; mọi truy vấn lọc theo doanh nghiệp của người đăng nhập; bản ghi ngoài phạm vi trả 404.
- **Thông báo realtime:** thông báo ghi cùng transaction với dữ liệu (outbox), đẩy qua SSE, mất kết nối thì nối lại từ thông báo cuối.
- **Chấm điểm:** giá, giao hàng, uy tín, điều khoản (0–100), trọng số mặc định 45/25/20/10; chạy thử: NCC giao nhanh 89,21 điểm, NCC rẻ hơn 79,28 — Buyer vẫn chọn NCC rẻ được nếu ghi lý do.
- **Tích hợp đối tác (giả lập):** gọi đối tác ngoài transaction, kết quả về bằng callback ký HMAC; đổi sang đối tác thật chỉ thay adapter. *Hóa đơn điện tử:* hóa đơn VAT 10% gửi sang nhà cung cấp, cơ quan thuế cấp mã sau vài giây, tra cứu được. *Thanh toán:* Finance được chuyển sang trang cổng; số dư chỉ đổi khi nhận IPN đúng số tiền, IPN trùng không ghi hai lần. *Ký số báo giá:* NCC nhập OTP, dịch vụ ký mã băm SHA-256 của báo giá; ProcureHub xác minh chứng thư bằng khóa CA tin cậy và tính lại mã băm mỗi lần hiển thị, nên sửa giá trong DB là bảng so sánh báo "chữ ký không hợp lệ".

Hạ tầng (Chaffey, 2011): Linux, NGINX, PostgreSQL, Docker trên cloud; luồng chi tiết và ảnh chụp ở Phụ lục C, D.

## 6.5. Trạng thái triển khai

Bảng 6.2. Trạng thái tại ngày 14/10/2026

| Nhóm chức năng | Trạng thái |
|---|---|
| Luồng PR → PO, phân quyền, tách doanh nghiệp, audit (P0) | Đã kiểm thử |
| Thông báo realtime, chấm điểm báo giá (P0) | Đã kiểm thử |
| Hóa đơn VAT, đánh giá NCC, KPI (P1) | Đã kiểm thử |
| Đối tác giả lập: cổng thanh toán, hóa đơn điện tử, ký số báo giá (P1) | Đã kiểm thử |
| Giao diện các tính năng trên | Đã triển khai, chưa có test giao diện tự động |
| Kết nối đối tác thật, ERP, OCR, AI (P2) | Đề xuất |

"Đã kiểm thử": 47 test tự động của nền tảng (SQLite và PostgreSQL) và 13 test của dịch vụ giả lập đối tác, cùng các lần chạy toàn luồng qua HTTP thật. Mã nguồn: https://drive.google.com/drive/folders/1IjBIgbUcX1YhkJ70pTUFpGuXhy2_oRSL

# 7. TRIỂN KHAI CHIẾN LƯỢC

Nhóm áp dụng Agile, backlog ưu tiên P0 → P1 → P2, cuối mỗi sprint kiểm thử và trình diễn (Project Management Institute, 2017). Nhân sự: trong học kỳ, bốn thành viên kiêm nhiệm; giai đoạn MVP và pilot (0–6 tháng) cần 1 PO/BA, 2 lập trình viên, 1 nhân sự bán hàng – onboarding, đầu tư 600 triệu đồng; giai đoạn tăng trưởng chi phí cố định 39 triệu đồng/tháng.

Khảo sát M1 thu 3–5 giao dịch làm baseline (báo cáo trung vị); kiểm thử khả dụng 5–8 người dùng (SUS); pilot 2–3 tuần hoặc UAT.

Bảng 7.1. Rủi ro chính

| Rủi ro | Phòng ngừa |
|---|---|
| Đánh giá quá cao tốc độ chấp nhận | Kịch bản tài chính bi quan; đo kích hoạt trước khi mở rộng |
| Gói miễn phí làm yếu doanh thu | Giới hạn Free; đặt hóa đơn, KPI ở gói trả phí |
| Phạm vi phình to | Khóa P0 trước; tích hợp đối tác (giả lập), KPI là P1; đối tác thật là P2 |
| Lộ dữ liệu chéo doanh nghiệp | Lọc phạm vi tập trung ở máy chủ; test truy cập chéo |
| Đối tác giả lập bị hiểu là thật | Nhãn "giả lập" mọi trang, định dạng hóa đơn/chứng thư khác thật, không nhận dữ liệu thẻ |

# 8. KIỂM SOÁT HIỆU QUẢ

## 8.1. Bộ KPI

Bảng 8.1. KPI theo nhóm

| Nhóm | Chỉ số | Ngưỡng |
|---|---|---|
| Quy trình | Thời gian PR → PO; thời gian duyệt PR | Giảm ≥ 30% so với baseline |
| Chi phí giao dịch | Trao đổi ngoài hệ thống mỗi RFQ; tiết kiệm so với ngân sách | Giảm ≥ 50%; công bố phương pháp |
| Người dùng | Hoàn thành kịch bản; SUS; CSAT | ≥ 90%; ≥ 68; ≥ 4/5 |
| Nhà cung cấp | Phản hồi RFQ đúng hạn; giao đúng hạn | ≥ 70%; ≥ 90% |
| Công nghệ | API p95; độ trễ thông báo; lộ dữ liệu chéo; webhook ghi trùng | < 500 ms; ≤ 5 giây; 0; 0 |

## 8.2. Mô hình tài chính giả định

**ROI khách hàng.** 30 PR/tháng × 6 giờ công × tiết kiệm 30% × 100.000 đồng/giờ = 64,8 triệu đồng năm đầu, so với phí gói Business 58 triệu đồng: ROI ≈ 11,7%, hòa vốn ở khoảng 27 PR/tháng. **Hòa vốn nền tảng:** chi phí cố định 39 triệu đồng/tháng, biến phí 0,8 triệu đồng/khách hàng, đầu tư 600 triệu đồng.

Bảng 8.2. Độ nhạy điểm hòa vốn (triệu đồng)

| Kịch bản | Starter / Business / Enterprise | ARPA | Hòa vốn (khách hàng) |
|---|---|---|---|
| Bi quan | 70% / 30% / 0% | 2,6 | 22 |
| Cơ sở | 50% / 50% / 0% | 3,0 | 18 |
| Thuận lợi | 20% / 70% / 10% | 4,0 | 13 |

Ở kịch bản cơ sở với 30 khách hàng, dòng tiền vận hành 27 triệu đồng/tháng, hoàn vốn khoảng 22 tháng; với CAC 15 triệu đồng và churn 3%/tháng, LTV/CAC ≈ 4,9 (churn 6% thì còn 2,4).

# 9. MILESTONES

Bảng 9.1. Milestones

| Mốc | Thời gian | Đầu ra |
|---|---|---|
| M0. Prototype | Đến 15/10/2026 | Mã nguồn, dịch vụ đối tác giả lập, 60 test, đề cương, URD/SRS/HLD (đã xong) |
| M1. Khảo sát | 16/10 – 29/10/2026 | Phỏng vấn, AS-IS, baseline, dữ liệu thị trường |
| M2. Hiệu chỉnh | 30/10 – 12/11/2026 | Điều chỉnh TO-BE, bảng giá, trọng số mặc định theo khảo sát |
| M3. Kiểm thử khả dụng | 13/11 – 24/11/2026 | Kiểm thử 5–8 người dùng, sửa lỗi, đạt release gate |
| M4. Báo cáo final | 25/11 – 01/12/2026 | Báo cáo, slide, tài chính cập nhật |
| M5. Thuyết trình | Tuần 13–15 | Demo 8–12 phút; sau môn học: pilot |

# 10. KẾT LUẬN

ProcureHub là giải pháp E-business buy-side giúp SME chuẩn hóa Source-to-Pay theo mô hình E-procurement SaaS, khác biệt bằng minh bạch; mỗi lập luận kinh doanh có quyết định kiến trúc và bằng chứng kiểm thử tương ứng. Giới hạn: chưa có dữ liệu thật, đối tác mới ở mức giả lập, chưa tích hợp ERP và AI; bước tiếp theo là khảo sát M1.

# TÀI LIỆU THAM KHẢO

Bezemer, C.-P., & Zaidman, A. (2010). Multi-tenant SaaS applications: Maintenance dream or nightmare? IWPSE-EVOL 2010, 88–92. ACM.

Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In Usability evaluation in industry (pp. 189–194). Taylor & Francis.

Brown, S. (2018). The C4 model for visualising software architecture. https://c4model.com

Chaffey, D. (2011). E-business and e-commerce management (5th ed.). Pearson Education.

Croom, S., & Brandon-Jones, A. (2007). Impact of e-procurement. Journal of Purchasing and Supply Management, 13(4), 294–303.

Davila, A., Gupta, M., & Palmer, R. (2003). Moving procurement systems to the Internet. European Management Journal, 21(1), 11–23.

Kaplan, R. S., & Norton, D. P. (1992). The balanced scorecard: Measures that drive performance. Harvard Business Review, 70(1), 71–79.

Laudon, K. C., & Traver, C. G. (2021). E-commerce 2021: Business, technology, society (16th ed.). Pearson Education.

Porter, M. E. (2001). Strategy and the Internet. Harvard Business Review, 79(3), 62–78.

Project Management Institute. (2017). Agile practice guide. Project Management Institute.

Trần, V. H. T. (2026). Bài giảng Hệ kinh doanh điện tử – Chương 2: E-business strategy [Slide bài giảng]. Trường Đại học Công nghệ Thông tin, ĐHQG-HCM.

Venkatesh, V., Morris, M. G., Davis, G. B., & Davis, F. D. (2003). User acceptance of information technology: Toward a unified view. MIS Quarterly, 27(3), 425–478.

Williamson, O. E. (1981). The economics of organization: The transaction cost approach. American Journal of Sociology, 87(3), 548–577.
