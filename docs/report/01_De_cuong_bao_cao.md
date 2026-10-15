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

Tại nhiều doanh nghiệp vừa và nhỏ (SME), mua sắm vẫn diễn ra qua email, bảng tính và tin nhắn rời rạc. Cách làm này kéo dài thời gian xử lý, khó truy lại báo giá, khó kiểm soát ngân sách và khiến việc chọn nhà cung cấp phụ thuộc kinh nghiệm cá nhân. Sau khi đặt hàng, hóa đơn và công nợ lại được theo dõi ở một bảng tính khác, nên doanh nghiệp không biết một khoản mua mất bao lâu từ lúc có nhu cầu đến lúc thanh toán xong.

Vấn đề nghiên cứu: làm thế nào thiết kế một hệ thống E-Procurement B2B vừa giảm thao tác thủ công, vừa bảo đảm phê duyệt tách quyền, minh bạch báo giá, có kiến trúc kỹ thuật đủ tin cậy và có mô hình kinh doanh khả thi cho SME Việt Nam?

Nhóm đề xuất ProcureHub, nền tảng E-Procurement B2B cung cấp theo mô hình phần mềm dịch vụ (SaaS), có Buyer Portal cho bên mua và Supplier Portal cho nhà cung cấp trên cùng một hệ thống đa doanh nghiệp. ProcureHub giúp SME số hóa chuỗi Source-to-Pay ở mức ghi nhận: từ đề nghị mua hàng (Purchase Request – PR), phê duyệt, mời nhà cung cấp (NCC) báo giá (Request for Quotation – RFQ), so sánh và chấm điểm, duyệt lựa chọn, phát hành đơn đặt hàng (Purchase Order – PO), ghi nhận giao hàng, đến hóa đơn, công nợ và đối soát thanh toán. Nền tảng không giữ tiền: thanh toán thật vẫn đi qua ngân hàng của doanh nghiệp; trong bản demo, cổng thanh toán, hóa đơn điện tử và chữ ký số được giả lập bằng một dịch vụ riêng để minh họa đúng cách tích hợp với đối tác. Mọi số liệu tài chính trong báo cáo là giả định minh họa, sẽ được hiệu chỉnh sau khảo sát doanh nghiệp.

## 1.2. Mục tiêu, đối tượng, phạm vi và phương pháp

Bảng 1.1. Mục tiêu, đối tượng, phạm vi và phương pháp nghiên cứu

| Nội dung | Mô tả |
|---|---|
| Mục tiêu | (1) Phân tích quy trình mua sắm B2B và điểm nghẽn; (2) xây dựng chiến lược E-business; (3) chọn mô hình kinh doanh và doanh thu; (4) thiết kế kiến trúc hệ thống và giải pháp công nghệ, kế hoạch triển khai; (5) xây dựng KPI và mô hình tài chính. |
| Đối tượng | Quy trình mua hàng gián tiếp (vật tư bảo trì – vận hành MRO, văn phòng phẩm, thiết bị CNTT) của SME và các vai trò: người mua hàng (Buyer), quản lý phê duyệt (Manager), kế toán (Finance), nhà cung cấp (Supplier), quản trị doanh nghiệp và quản trị nền tảng. |
| Phạm vi nghiệp vụ | P0: PR → phê duyệt → RFQ → báo giá → so sánh có chấm điểm → duyệt lựa chọn → PO → ghi nhận giao hàng; thông báo realtime; audit log. P1: hóa đơn VAT 10% và Net N, hóa đơn điện tử, thanh toán nhiều lần qua cổng thanh toán, ký số báo giá (ba dịch vụ đối tác ở dạng giả lập), đánh giá NCC, KPI. P2 (lộ trình): kết nối đối tác thật, chat, OCR, tích hợp ERP/kế toán, AI. |
| Phạm vi công nghệ | Web app SPA, REST API, Server-Sent Events, phân quyền theo vai trò và theo doanh nghiệp, audit log, chữ ký số Ed25519, tích hợp đối tác qua API và callback ký HMAC (cổng thanh toán, hóa đơn điện tử, ký số đều giả lập). Không xử lý tiền thật; hóa đơn và chữ ký không có giá trị pháp lý. |
| Phương pháp | Nghiên cứu tài liệu; phân tích chiến lược; phỏng vấn 6–10 người tại 3–5 doanh nghiệp; mô hình hóa quy trình; prototype; kiểm thử tự động và kiểm thử khả dụng 5–8 người dùng. |

## 1.3. Thành viên và phân công

Bảng 1.2. Thành viên và phân công công việc của Nhóm 2

| Họ và tên | MSHV | Vai trò | Nội dung phụ trách |
|---|---|---|---|
| Tăng Quốc Hưng | 26848075 | Trưởng nhóm | Điều phối, tổng hợp và biên tập báo cáo; Mục 1, 9, 10 |
| Trần Nguyễn Phi | 26848163 | Thành viên | Cơ sở lý thuyết; mô hình kinh doanh và doanh thu; Mục 2, 5 |
| Trần Thanh Vũ | 26848269 | Thành viên | Phân tích nghiệp vụ, kiến trúc hệ thống, mô hình tài chính; Mục 3, 6, 8 |
| Lê Trọng Đạo | 26848032 | Thành viên | Chiến lược E-business theo Chương 2, kế hoạch triển khai; Mục 4, 7 |

# 2. CƠ SỞ LÝ THUYẾT

## 2.1. E-business, buy-side e-commerce và E-Procurement

E-business là việc dùng Internet, intranet, extranet và các mạng khác để kết nối quy trình kinh doanh, giao dịch, giao tiếp và cộng tác trong doanh nghiệp cũng như với khách hàng và nhà cung cấp; E-commerce chỉ là phần giao dịch mua bán (Chaffey, 2011). E-Procurement thuộc phía buy-side (giao dịch giữa doanh nghiệp và nhà cung cấp); cùng giao dịch đó, với nhà cung cấp là kênh sell-side để nhận RFQ, gửi báo giá và lập hóa đơn. Phần nội bộ (PR, phê duyệt, so sánh, đối soát, audit) vận hành như một intranet; Supplier Portal là một extranet chỉ hiển thị dữ liệu thuộc quan hệ của từng nhà cung cấp.

E-Procurement dùng công nghệ số cho tìm nguồn cung, yêu cầu báo giá, chọn nhà cung cấp, đặt hàng và quản lý giao dịch. Mức độ ứng dụng phát triển dần từ số hóa trao đổi thông tin đến tích hợp vào hệ thống doanh nghiệp (Davila et al., 2003), và hiệu quả phụ thuộc vào cách tổ chức triển khai và mức chấp nhận của người dùng (Croom & Brandon-Jones, 2007). Hadi Putra và Santoso (2020) xếp E-procurement vào nhóm ứng dụng E-business chính của SME. Chuỗi Source-to-Pay đầy đủ gồm tìm nguồn, đặt hàng, nhận hàng, hóa đơn và thanh toán. Đề tài bao phủ trọn phần Source-to-Order và phần hóa đơn, đối soát thanh toán ở mức ghi nhận, chưa thực hiện chuyển tiền.

## 2.2. Các mô hình lý thuyết áp dụng

Báo cáo dùng quy trình chiến lược E-business (Chaffey, 2011; Trần, 2026) làm khung chung cho Mục 4–8. Để phân tích cạnh tranh, báo cáo dùng Five Forces và chuỗi giá trị (Porter, 2001). Để rút ra chiến lược và đặt mục tiêu, báo cáo dùng SWOT, SMART và Balanced Scorecard (Kaplan & Norton, 1992). Mục 5 dựa trên tám yếu tố của mô hình kinh doanh, mô hình doanh thu và mô hình B2B (Laudon & Traver, 2021). Lý thuyết chi phí giao dịch (Transaction Cost Economics – TCE; Williamson, 1981) giải thích giá trị kinh tế qua chi phí tìm kiếm, thương lượng và giám sát; mỗi loại chi phí được gắn với một KPI. UTAUT (Venkatesh et al., 2003) là khung khảo sát chấp nhận công nghệ, TAM (Davis, 1989) cho bộ câu hỏi ngắn, thang SUS (Brooke, 1996) đo mức khả dụng.

## 2.3. Cơ sở cho thiết kế kiến trúc

Mục 6 dùng thêm bốn khái niệm kỹ thuật. Thứ nhất, mô hình C4 mô tả kiến trúc theo các mức ngữ cảnh, container, thành phần (Brown, 2018); báo cáo dùng hai mức đầu để người đọc phi kỹ thuật vẫn theo dõi được. Thứ hai, SaaS đa doanh nghiệp (multi-tenant) cho nhiều khách hàng dùng chung một bản ứng dụng và một cơ sở dữ liệu, đổi lại phải kiểm soát chặt việc tách dữ liệu giữa các doanh nghiệp (Bezemer & Zaidman, 2010). Thứ ba, mẫu transactional outbox ghi sự kiện cần phát đi trong cùng transaction với thay đổi dữ liệu để không mất hoặc phát sai sự kiện (Richardson, 2018). Thứ tư, mã xác thực thông điệp HMAC cho phép bên nhận kiểm tra webhook thật sự đến từ cổng thanh toán và không bị sửa (Krawczyk et al., 1997).

# 3. PHÂN TÍCH BÀI TOÁN VÀ GIẢI PHÁP NGHIỆP VỤ

## 3.1. Quy trình hiện tại (AS-IS) và quy trình đề xuất (TO-BE)

Quy trình hiện tại dưới đây là giả thuyết, sẽ được xác minh bằng phỏng vấn ở mốc M1. Quy trình đề xuất chuẩn hóa từng công đoạn, mỗi trạng thái có người phụ trách, có dấu vết kiểm tra và có thông báo cho bên liên quan.

Bảng 3.1. Đối chiếu quy trình mua sắm hiện tại và đề xuất

| Công đoạn | AS-IS (giả thuyết) | TO-BE ProcureHub | Chỉ số đánh giá |
|---|---|---|---|
| Yêu cầu mua | Email/chat, thiếu mã định danh | PR chuẩn hóa, có mã, người phụ trách và ngân sách ước tính | Thời gian tạo PR; tỷ lệ thiếu trường |
| Phê duyệt | Chuyển tiếp thủ công, khó truy trách nhiệm | Manager duyệt/từ chối, tách quyền, nhận thông báo ngay | Thời gian chờ duyệt |
| RFQ | Gửi riêng từng nhà cung cấp | Một RFQ gửi ≥ 2 nhà cung cấp có quan hệ, đặt trọng số chấm điểm | Số lượt trao đổi ngoài hệ thống |
| Báo giá | Tệp rời, nhiều phiên bản, không biết bị sửa hay chưa | Báo giá có cấu trúc, lưu phiên bản, NCC ký số; sửa sau khi ký là phát hiện được | Tỷ lệ NCC phản hồi; tỷ lệ báo giá có ký số |
| Chọn nhà cung cấp | So sánh bằng Excel, lý do không nhất quán | Bảng điểm trọng số công khai công thức, ghi lý do, Manager duyệt | Thời gian so sánh; audit coverage |
| PO và nhận hàng | Email và ghi chép thủ công | PO khóa giá và điều khoản Net N, NCC xác nhận, nhận từng dòng | Tỷ lệ PO hoàn tất; giao đúng hạn |
| Hóa đơn và thanh toán | Bảng tính riêng, khó biết khoản nào quá hạn | NCC lập hóa đơn từ PO (VAT 10%), phát hành hóa đơn điện tử có mã cơ quan thuế, Finance trả nhiều lần qua cổng thanh toán, số dư đối soát qua IPN | Số hóa đơn quá hạn; chu trình PR → thanh toán |
| Đánh giá NCC | Ghi nhớ cá nhân | Chấm điểm chất lượng và giao hàng sau mỗi PO, dùng lại khi chấm báo giá | Điểm uy tín trung bình |

![Hình 3.1. Luồng Source-to-Pay TO-BE theo vai trò](figures/fig_3_1_source_to_pay.png) {landscape}

## 3.2. Quy tắc nghiệp vụ bảo đảm minh bạch

Buyer tạo PR theo mẫu, Manager duyệt; PR được duyệt chuyển thành RFQ có hạn chót, gửi ít nhất hai nhà cung cấp trong danh bạ. Sau khi RFQ đóng, Buyer xem bảng so sánh theo giá từng dòng, tổng tiền, thời gian giao, thời hạn hiệu lực, số ngày công nợ và điểm uy tín, rồi đề xuất một nhà cung cấp kèm lý do; chỉ khi Manager duyệt lựa chọn, PO mới được sinh. Các quy tắc chính:

- **Tách quyền:** người tạo PR hoặc người đề xuất nhà cung cấp không được tự duyệt; máy chủ từ chối thao tác vi phạm và ghi log.
- **Bảo mật báo giá:** nhà cung cấp không thấy danh tính, giá hay kết quả của đối thủ; hạn chót được kiểm tra theo giờ máy chủ, không nhận sửa sau hạn; thông báo không chứa giá.
- **Điểm hỗ trợ, con người quyết định:** trọng số chấm điểm do Buyer đặt, tổng bằng 100 và hiển thị công thức; điểm được lưu lại tại thời điểm đề xuất. Buyer có thể chọn nhà cung cấp không đứng đầu bảng điểm nhưng phải ghi lý do. Cơ chế này là chấm điểm trọng số, không gọi là AI.
- **Khóa và lưu vết:** mỗi lần gửi báo giá được lưu phiên bản; khi lựa chọn được duyệt, báo giá bị khóa và PO giữ nguyên giá, thời gian giao và số ngày công nợ đã chốt.
- **Chữ ký số báo giá:** NCC ký số mỗi lần gửi báo giá; bên mua chỉ tin chữ ký do tổ chức chứng thực tin cậy cấp cho đúng mã số thuế của NCC, và mọi thay đổi nội dung sau khi ký làm chữ ký trở thành "không hợp lệ".
- **Hóa đơn và thanh toán:** hóa đơn chỉ lập khi PO đã giao đủ, tiền trước thuế bằng tổng PO cộng VAT 10%, hạn trả bằng ngày lập cộng số ngày công nợ; hóa đơn được gửi sang nhà cung cấp hóa đơn điện tử để cơ quan thuế cấp mã, và đã gửi thì không được hủy. Thanh toán chỉ được ghi nhận khi máy chủ nhận sự kiện có chữ ký hợp lệ từ cổng thanh toán; cùng một sự kiện gửi lại không được ghi hai lần; tổng các lần trả không vượt giá trị hóa đơn.
- **Ngoại lệ:** RFQ không có báo giá hợp lệ được hủy kèm lý do; nhà cung cấp từ chối PO thì Buyer chọn lại; nhận hàng từng phần không vượt số lượng PO; hóa đơn chỉ hủy được khi chưa có thanh toán. Mỗi nhà cung cấp là một tài khoản công ty dùng chung, kết nối với từng bên mua qua quan hệ do bên mua mời.

## 3.3. Giá trị E-business tạo ra

Theo bốn cách E-business tạo giá trị (Chaffey, 2011), ProcureHub đóng góp như sau. Thứ nhất, gia tăng giá trị: dữ liệu báo giá có cấu trúc và bảng điểm trọng số giúp so sánh dễ hơn và nhất quán hơn. Thứ hai, giảm chi phí: giảm giờ công tổng hợp báo giá và chi phí tìm kiếm, thương lượng, giám sát (TCE); thông báo realtime giảm thời gian chờ giữa các bên. Thứ ba, quản lý rủi ro: tách quyền, khóa báo giá, đối soát thanh toán có chữ ký và audit log hạn chế rủi ro vận hành và pháp lý. Thứ tư, tạo cách làm mới: dữ liệu mua sắm vốn rời rạc trở thành dữ liệu dùng chung để đo chu trình và phân tích chi tiêu.

Trong chuỗi giá trị của Porter, mua sắm (procurement) là hoạt động hỗ trợ cho mọi hoạt động chính. Khi nhiều bên mua và nhà cung cấp cùng dùng một nền tảng, các chuỗi giá trị riêng lẻ nối thành mạng giá trị (value web), và ProcureHub là điểm điều phối thông tin (Laudon & Traver, 2021). Về tri thức, kinh nghiệm chọn nhà cung cấp vốn là tri thức ẩn; lịch sử RFQ, điểm tại thời điểm lựa chọn, lý do lựa chọn, đánh giá nhà cung cấp và audit log chuyển nó thành tri thức hiện, dùng lại được khi nhân sự thay đổi.

# 4. CHIẾN LƯỢC E-BUSINESS

Từ bài toán và giải pháp nghiệp vụ ở Mục 3, mục này phân tích môi trường để xác định ProcureHub cạnh tranh ở đâu và bằng cách nào.

## 4.1. Cách tiếp cận chiến lược

Báo cáo áp dụng mô hình quy trình chiến lược bốn bước: phân tích tình huống, thiết lập mục tiêu, định nghĩa chiến lược và triển khai (Chaffey, 2011). Theo mô hình chiến lược động, mỗi sprint là một vòng thiết kế → triển khai → phản hồi, và số liệu đo ở M1 dùng để điều chỉnh mục tiêu. Chiến lược xét ở hai cấp:

- **Cấp khách hàng (buy-side):** ProcureHub giúp SME thực hiện bốn việc của chiến lược buy-side: tự động hóa quy trình mua nội bộ; liên kết quy trình nội bộ với hoạt động mua bên ngoài (ProcureHub liên kết đến hóa đơn và đối soát thanh toán trong nền tảng, tích hợp kế toán/ERP thuộc lộ trình); ưu tiên nhà cung cấp cộng tác qua kênh số; và có lộ trình ứng dụng rõ ràng.
- **Cấp nền tảng (sell-side):** ProcureHub là doanh nghiệp SaaS bán dịch vụ cho SME, nên mục tiêu được đặt theo các nhóm Acquisition – Conversion – Retention – Service – Profitability và phải quản lý tích hợp giữa kênh bán trực tiếp với kênh đối tác.

Theo Porter (2001), câu hỏi then chốt là dùng Internet như thế nào, nên ProcureHub tạo khác biệt bằng minh bạch và tốc độ triển khai, không chạy đua số lượng tính năng. Vì vậy các tính năng chính đều phục vụ trực tiếp hai trục này: thông báo realtime rút ngắn thời gian, bảng điểm công khai công thức tăng minh bạch, đối soát thanh toán có chữ ký tăng kiểm soát.

## 4.2. Phân tích môi trường vĩ mô (SLEPT)

- **Xã hội:** SME quen dùng Zalo, Excel; ngại thay đổi và lo lộ dữ liệu giá. Thông báo tức thời trên nền tảng là cách cạnh tranh trực tiếp với thói quen nhắn tin.
- **Pháp lý và đạo đức:** Luật Giao dịch điện tử 20/2023/QH15 công nhận giá trị pháp lý của thông điệp dữ liệu; hóa đơn, chứng từ theo Nghị định 123/2020/NĐ-CP sửa đổi bởi Nghị định 70/2025/NĐ-CP (nền cho giai đoạn Invoice-to-Pay; hóa đơn điện tử trong bản demo đi qua nhà cung cấp giả lập, không thay hóa đơn điện tử có giá trị pháp lý). Luật Giao dịch điện tử 2023 cũng là cơ sở cho chữ ký số trên chứng từ điện tử như báo giá; Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và Nghị định 356/2025/NĐ-CP hiệu lực từ 01/01/2026 (Quốc hội, 2023, 2025; Chính phủ, 2025a, 2025b). Về đạo đức, nền tảng phải bảo đảm minh bạch, tránh xung đột lợi ích khi chọn nhà cung cấp và không để thanh toán, hóa đơn và chữ ký giả lập bị hiểu là thật.
- **Kinh tế, chính sách, công nghệ:** SME nhạy cảm chi phí và ưu tiên thuê bao tháng; Quyết định 749/QĐ-TTg về Chương trình Chuyển đổi số quốc gia (Thủ tướng Chính phủ, 2020) tạo bối cảnh thuận lợi; cloud và SaaS giảm chi phí hạ tầng cho nền tảng nhỏ.

## 4.3. Phân tích cạnh tranh theo Five Forces

Phạm vi phân tích: thị trường SaaS E-Procurement cho SME tại Việt Nam.

Bảng 4.1. Phân tích Five Forces (Porter, 2001)

| Lực lượng | Mức độ | Nhận định và hàm ý chiến lược |
|---|---|---|
| Cạnh tranh hiện tại | Trung bình – cao | Có bộ Source-to-Pay quốc tế, phân hệ ERP, phần mềm trong nước. Ứng phó: tập trung ngách, không đối đầu toàn diện. |
| Đối thủ mới | Cao | Rào cản gia nhập SaaS thấp; hãng kế toán/ERP có thể thêm tính năng. Ứng phó: lợi thế bằng dữ liệu (lịch sử báo giá, đánh giá NCC), đối tác. |
| Sản phẩm thay thế | Cao | Email, Excel, Zalo miễn phí, quen thuộc. Ứng phó: gói Free, onboarding nhanh, thông báo tức thời, chứng minh lợi ích bằng KPI. |
| Quyền lực khách hàng | Cao | SME dễ hủy thuê bao. Ứng phó: thuê bao tháng, giá rõ, chứng minh ROI bằng dashboard. |
| Quyền lực nhà cung cấp đầu vào | Thấp – trung bình | Cloud, mã nguồn mở có nhiều lựa chọn. Ứng phó: công nghệ phổ biến, không phụ thuộc dịch vụ độc quyền (không dùng hàng đợi hay cache riêng của một nhà cung cấp cloud). |

Áp lực lớn nhất đến từ sản phẩm thay thế miễn phí và quyền lực khách hàng, nên ProcureHub tập trung ngách và khác biệt hóa bằng minh bạch. Rủi ro cần theo dõi là counter-mediation: hãng kế toán/ERP tự lập trung gian mua hàng riêng.

## 4.4. Mức độ phát triển E-business của khách hàng mục tiêu

Theo mô hình buy-side sáu bậc (Chaffey, 2011), SME mục tiêu ở bậc 1. MVP đưa họ lên bậc 4 bằng luồng RFQ (không cần catalogue ở bậc 2–3). Hóa đơn, công nợ và đối soát thanh toán ngay trong nền tảng là bước chuẩn bị cho bậc 5 nhưng chưa phải bậc 5, vì dữ liệu chưa tích hợp với hệ thống kế toán/ERP của doanh nghiệp.

Bảng 4.2. Mô hình giai đoạn buy-side và vị trí của ProcureHub

| Bậc | Hiện trạng SME mục tiêu | ProcureHub |
|---|---|---|
| 1. Review suppliers | Tìm NCC qua danh sách cũ, Zalo | Đã triển khai: danh bạ NCC, mời ≥ 2 NCC, điểm uy tín từ đánh giá |
| 2. Stock availability | Hỏi tồn kho qua điện thoại | Ngoài phạm vi (NCC ghi thời gian giao) |
| 3. Online catalogues | Chưa có | Lộ trình: danh mục MRO giá đã chốt |
| 4. Online ordering | PO gửi qua email | Đã triển khai: PO sau duyệt lựa chọn; NCC xác nhận online |
| 5. Integrate databases | — | Một phần: hóa đơn, hóa đơn điện tử, công nợ, đối soát với cổng thanh toán; tích hợp kế toán/ERP là lộ trình |
| 6. Supply chain optimization | — | Bước đầu: KPI chu trình, tỷ lệ phản hồi, tiết kiệm; gợi ý NCC bằng AI là lộ trình |

Theo portfolio analysis, mua sắm là nhóm Strategic với doanh nghiệp B2B; vì SME có năng lực số thấp, ProcureHub chọn market driving kết hợp capability building (hướng dẫn, đào tạo khách hàng).

## 4.5. Phân tích SWOT và chiến lược kết hợp

Bảng 4.3. Ma trận SWOT và chiến lược kết hợp

| | S: quy trình chuẩn có tách quyền, audit trail; bảng điểm minh bạch; thông báo realtime; triển khai nhanh; chi phí thấp nhờ cloud, mã nguồn mở | W: chưa có khách hàng, dữ liệu thật; thương hiệu mới; cổng thanh toán, hóa đơn điện tử, ký số mới tích hợp ở mức giả lập; chưa tích hợp ERP |
|---|---|---|
| O: chuyển đổi số; SME còn dùng email/Excel; xu hướng thuê bao; đối tác kế toán/ERP cần giải pháp mua sắm | SO – Attacking: tiếp cận SME bậc 1 qua kênh đối tác kế toán/ERP; dùng dashboard KPI làm bằng chứng bán hàng | WO – Build strengths for attacking: pilot có case study; tích hợp kế toán và cổng thanh toán qua đối tác thay vì tự xây |
| T: công cụ miễn phí; counter-mediation; SME ngại thay đổi, lo lộ giá; xung đột kênh; tuân thủ dữ liệu cá nhân | ST – Defensive: lấy tách quyền, audit trail, đối soát có chữ ký làm khác biệt; công bố chính sách bảo mật báo giá | WT – Build strengths for defensive: phạm vi hẹp, không đầu tư lớn trước khi kiểm chứng; giới hạn gói Free; gắn nhãn sandbox rõ ràng |

## 4.6. Tầm nhìn, sứ mệnh và mục tiêu chiến lược

**Tầm nhìn:** trở thành công cụ mua hàng minh bạch quen thuộc của SME Việt Nam, bổ trợ (complement) chứ không thay thế phần mềm kế toán/ERP doanh nghiệp đang dùng.

**Sứ mệnh:** giúp SME chuyển việc mua hàng từ email và Excel sang một quy trình có phê duyệt, có báo giá so sánh được, có công nợ theo dõi được và có dấu vết, dùng được ngay trong ngày đầu.

Mục tiêu viết theo SMART và mẫu Mục tiêu – Chiến lược – KPI (Chaffey, 2011); mốc thời gian tính từ ngày ra mắt thương mại sau pilot.

Bảng 4.4. Mục tiêu SMART

| Mục tiêu | Chiến lược thực hiện | KPI (SMART) |
|---|---|---|
| Khách hàng mua sắm hiệu quả hơn | Chuẩn hóa luồng PR → RFQ → PO → hóa đơn trên một hệ thống | Giảm ≥ 30% thời gian PR → PO sau 3 tháng sử dụng; giảm chi phí mua hàng gián tiếp 5% năm đầu (chốt lại sau baseline) |
| Có khách hàng trả phí (Acquisition, Conversion) | Pilot 1–2 SME, chuyển đổi từ gói Free | 3 khách hàng trả phí sau 6 tháng; tỷ lệ Free → trả phí ≥ 10% |
| Hòa vốn vận hành (Profitability) | Bán trực tiếp và qua đối tác kế toán/ERP | ≥ 18 khách hàng trả phí trong 18 tháng (kịch bản cơ sở, Mục 8.2) |
| Giữ chân khách hàng (Retention, Service) | Onboarding có hướng dẫn, chăm sóc theo gói | Tỷ lệ rời bỏ (churn) ≤ 3%/tháng; ≥ 60% tài khoản mới tạo RFQ đầu tiên trong 14 ngày |
| Kích hoạt nhà cung cấp | RFQ có cấu trúc, tài khoản NCC miễn phí, thông báo tức thời | ≥ 70% lời mời RFQ được phản hồi đúng hạn; trung vị thời gian phản hồi ≤ 48 giờ |

Bảng 4.5. Balanced Scorecard (Kaplan & Norton, 1992)

| Góc nhìn | Objective | Measure | Target | Initiative |
|---|---|---|---|---|
| Tài chính | Hòa vốn vận hành | Số khách hàng trả phí; doanh thu định kỳ tháng (MRR) | ≥ 18 khách hàng trong 18 tháng | Bán trực tiếp và qua đối tác |
| Khách hàng | Giữ chân, tăng giá trị khách hàng | Churn; LTV/CAC; tỷ lệ Free → trả phí | ≤ 3%/tháng; ≥ 3; ≥ 10% | Onboarding, chăm sóc theo gói |
| Quy trình nội bộ | Ra quyết định mua nhanh, minh bạch | Thời gian PR → PO; tỷ lệ NCC phản hồi; % hành động có audit log | Giảm ≥ 30%; ≥ 70%; 100% | Chuẩn hóa luồng PR → RFQ → PO, thông báo realtime |
| Học hỏi và phát triển | Nâng năng lực đội ngũ | Tỷ lệ hoàn thành sprint; ticket hỗ trợ xử lý/người; hài lòng nhân viên | Đặt sau M1 | Đào tạo theo vai trò; retro mỗi sprint |

# 5. MÔ HÌNH KINH DOANH VÀ ĐỊNH NGHĨA CHIẾN LƯỢC

Các kết luận chiến lược ở Mục 4 được cụ thể hóa thành mô hình kinh doanh, mô hình doanh thu và tám quyết định chiến lược.

## 5.1. Lựa chọn mô hình kinh doanh B2B

Laudon và Traver (2021) chia mô hình B2B thành Net marketplace (e-distributor, e-procurement, exchange, industry consortium) và Private industrial network. ProcureHub chọn mô hình **E-procurement**: nhà cung cấp dịch vụ B2B dạng SaaS giúp doanh nghiệp mua hàng gián tiếp và MRO, thu phí dịch vụ. Các mô hình khác bị loại: e-distributor đòi hỏi sở hữu hàng hóa; exchange cần lượng giao dịch lớn và ép nhà cung cấp cạnh tranh giá; industry consortium cần doanh nghiệp đầu ngành bảo trợ. Danh bạ nhà cung cấp riêng của mỗi bên mua gần với private industrial network; ProcureHub cung cấp năng lực này cho SME dưới dạng dịch vụ.

ProcureHub **không phải marketplace công khai**: nhà cung cấp chỉ thấy RFQ được mời và giao dịch trực tiếp liên quan. Việc thêm hóa đơn và thanh toán không đổi mô hình: nền tảng ghi nhận và đối soát, không thu tiền hộ, không giữ tiền và không đứng giữa dòng tiền như một trung gian thanh toán.

Về tái cấu trúc thị trường, ProcureHub là trung gian mới về quy trình và thông tin (re-intermediation) cho mạng đối tác do bên mua tự mời, không loại bỏ nhà phân phối hiện có, đồng thời phải đề phòng counter-mediation từ các hãng kế toán/ERP.

Tên ProcureHub ghép từ procure (mua sắm) và hub (trung tâm kết nối), thể hiện vai trò điểm điều phối thông tin giữa bên mua và nhà cung cấp. Vì từ "procure" còn lạ với người dùng SME Việt Nam, thương hiệu đi kèm tagline "ProcureHub – Mua hàng minh bạch cho doanh nghiệp". Trước khi thương mại hóa, nhóm cần tra cứu trùng nhãn hiệu tại Cục Sở hữu trí tuệ và kiểm tra tên miền.

## 5.2. Tám yếu tố của mô hình kinh doanh

Bảng 5.1. Tám yếu tố của mô hình kinh doanh ProcureHub (Laudon & Traver, 2021)

| Yếu tố | ProcureHub |
|---|---|
| Value proposition | Bên mua: reduction of product search and price discovery; kiểm soát phê duyệt, bảng điểm minh bạch, theo dõi công nợ, truy vết. NCC: RFQ có cấu trúc, thông báo tức thời, một tài khoản cho nhiều bên mua, biết hóa đơn đã được trả đến đâu. |
| Revenue model | Thuê bao có freemium giới hạn; phí triển khai (Mục 5.3). Không thu phí giao dịch. |
| Market opportunity | Ngách: SME TP.HCM mua hàng gián tiếp 10–30 PR/tháng, có ≥ 2 vai trò phê duyệt. Thị trường có thể chiếm lĩnh (SOM) = số khách hàng tiếp cận được trong 12–24 tháng × doanh thu bình quân mỗi khách hàng (ARPA) × 12; số doanh nghiệp lấy từ thống kê chính thức ở M1. |
| Competitive environment | Trực tiếp: SAP Ariba, Coupa, Odoo Purchase, phần mềm trong nước. Gián tiếp: email, Excel, Zalo. |
| Competitive advantage | Ban đầu: triển khai trong ngày, minh bạch, chi phí thấp. Bền vững: dữ liệu báo giá và đánh giá NCC tích lũy, quan hệ đối tác. |
| Market strategy | Gói Free, pilot có case study, bán qua đối tác (D1, Bảng 5.4). |
| Organizational development | Nhóm nhỏ đa năng, tuyển chuyên trách khi tăng trưởng (Mục 7.1). |
| Management team | Bốn thành viên kiêm nhiệm; cần cố vấn mua hàng doanh nghiệp và cố vấn kế toán khi mở rộng Invoice-to-Pay. |

## 5.3. Mô hình doanh thu và bảng giá

Trong năm mô hình doanh thu (quảng cáo, thuê bao/freemium, phí giao dịch, bán hàng, liên kết), ProcureHub chọn **thuê bao có freemium giới hạn** làm nguồn thu chính vì doanh thu định kỳ, dễ dự báo và hợp với SME; bán dịch vụ triển khai, đào tạo là nguồn thu phụ; liên kết (hoa hồng giới thiệu phần mềm kế toán, hóa đơn điện tử, cổng thanh toán) áp dụng sau MVP.

ProcureHub có chức năng ghi nhận thanh toán nhưng vẫn **không thu phí giao dịch**, vì ba lý do: (1) tiền vẫn chuyển qua ngân hàng của doanh nghiệp, nền tảng chỉ ghi nhận và đối soát; (2) phí theo giá trị PO khiến khách ngại đưa đơn lớn vào hệ thống, làm hỏng dữ liệu KPI; (3) thu phí trên dòng tiền kéo theo nghĩa vụ pháp lý của trung gian thanh toán, không phù hợp năng lực giai đoạn đầu. Khi tích hợp cổng thanh toán thật, phí cổng (nếu có) do đối tác thu và minh bạch với khách hàng. Không dùng quảng cáo vì sẽ phá tính trung lập của bảng điểm báo giá. Nền tảng thu phí bên mua và miễn phí cho nhà cung cấp.

Bảng 5.2. Bảng giá giả định

| Gói | Giá (giả định) | Giới hạn chính | Đối tượng |
|---|---|---|---|
| Free | 0 đồng | 3 người dùng, 3 RFQ/tháng, dashboard cơ bản; không có hóa đơn và KPI | Dùng thử, doanh nghiệp rất nhỏ |
| Starter | 2 triệu đồng/tháng | 10 người dùng, 20 RFQ/tháng, thông báo realtime, hóa đơn và công nợ | SME mua 10–20 lần/tháng |
| Business | 4 triệu đồng/tháng | 30 người dùng, không giới hạn RFQ, KPI mua sắm, đánh giá NCC, xuất audit log | SME mua thường xuyên |
| Enterprise | Từ 8 triệu đồng/tháng | Theo hợp đồng: tích hợp kế toán/ERP, cổng thanh toán đối tác, SLA, phê duyệt nhiều cấp | Doanh nghiệp vừa, nhiều phòng ban |

Phí triển khai một lần 5–15 triệu đồng; trả theo năm được giảm tương đương hai tháng. Gói Free bị giới hạn chặt vì "dịch vụ miễn phí" là nguyên nhân thất bại thường gặp của E-business. Module hóa đơn và KPI được đặt ở gói trả phí vì đó là phần tạo giá trị đo được (Mục 8.2), làm động lực nâng cấp từ Free.

## 5.4. Tám quyết định định nghĩa chiến lược

Bảng 5.3. Tám quyết định chiến lược của ProcureHub (Chaffey, 2011)

| Quyết định | Lựa chọn của ProcureHub |
|---|---|
| D1. Ưu tiên kênh | Website, gói Free để thu hút; bán trực tiếp và đối tác để chuyển đổi (right-channeling); khách hàng chuyển từ "bricks and mortar" sang "bricks and clicks". |
| D2. Thị trường – sản phẩm | Thâm nhập SME TP.HCM → phát triển sản phẩm (Invoice-to-Pay tích hợp, AI) → mở rộng ra tỉnh khác. |
| D3. Định vị | Tập trung ngách + khác biệt hóa bằng minh bạch. Giá trị khách hàng = (Chất lượng sản phẩm × Chất lượng dịch vụ) / (Giá × Thời gian đáp ứng): tăng tử số bằng quy trình chuẩn, bảng điểm, onboarding; giảm mẫu số bằng thuê bao tháng, thông báo realtime, RFQ đầu tiên trong ngày. |
| D4. Mô hình kinh doanh, doanh thu | E-procurement SaaS; thuê bao có freemium giới hạn; phí triển khai; không phí giao dịch. |
| D5. Tái cấu trúc thị trường | Re-intermediation; đề phòng counter-mediation. |
| D6. Năng lực chuỗi cung ứng | Extranet cho NCC; Invoice-to-Pay ở mức ghi nhận và đối soát; chỉ hàng gián tiếp/MRO; không tham gia exchange. |
| D7. Quản trị tri thức | Tri thức ẩn → tri thức hiện qua lịch sử RFQ, điểm tại thời điểm lựa chọn, lý do lựa chọn, đánh giá NCC, audit log. |
| D8. Nguồn lực tổ chức | In-house giai đoạn đầu → đối tác chiến lược với đơn vị kế toán/ERP và cổng thanh toán. |

## 5.5. Business Model Canvas

Bảng 5.4. Business Model Canvas của ProcureHub

| Khối | Nội dung |
|---|---|
| Phân khúc khách hàng | SME mua hàng gián tiếp/MRO (bên trả phí); nhà cung cấp của họ (người dùng miễn phí) |
| Giá trị đề xuất | Mua hàng minh bạch, nhanh, có dấu vết từ PR đến đối soát thanh toán; NCC có một cổng chung để nhận RFQ, PO, theo dõi hóa đơn |
| Kênh | Website và gói Free; bán trực tiếp; đối tác kế toán/ERP; webinar, case study |
| Quan hệ khách hàng | Onboarding có hướng dẫn; chăm sóc theo gói; cộng đồng người dùng |
| Dòng doanh thu | Thuê bao tháng/năm; phí triển khai, đào tạo; hoa hồng liên kết (sau MVP) |
| Nguồn lực chính | Nền tảng phần mềm, dữ liệu báo giá và đánh giá NCC tích lũy, đội ngũ sản phẩm và onboarding |
| Hoạt động chính | Phát triển và vận hành nền tảng, bảo mật dữ liệu, onboarding khách hàng, phát triển kênh đối tác |
| Đối tác chính | Nhà cung cấp cloud; hãng kế toán/ERP; cổng thanh toán; nhà cung cấp hóa đơn điện tử; tổ chức cung cấp dịch vụ chữ ký số (điểm tích hợp đã dựng sẵn ở dạng giả lập) |
| Cơ cấu chi phí | Nhân sự (chi phí cố định chính), hạ tầng cloud, chi phí thu hút khách hàng, hỗ trợ |

# 6. KIẾN TRÚC HỆ THỐNG VÀ GIẢI PHÁP CÔNG NGHỆ

Mục này mô tả nền tảng công nghệ hiện thực hóa Mục 5. Nguyên tắc xuyên suốt: mỗi quyết định kiến trúc phải trả lời được nó phục vụ lập luận kinh doanh nào. Đặc tả đầy đủ ở Phụ lục B (SRS) và Phụ lục C (HLD).

## 6.1. Từ chiến lược đến kiến trúc

Bảng 6.1. Truy vết quyết định kinh doanh sang quyết định kiến trúc

| Lập luận kinh doanh | Quyết định kiến trúc |
|---|---|
| Khác biệt hóa bằng minh bạch và tách quyền (D3, SWOT-ST) | RBAC + chống tự duyệt ở máy chủ + audit log chỉ ghi thêm, có request ID + module duyệt lựa chọn |
| SME nhạy cảm chi phí, cần dùng được ngay (Five Forces, D1) | Modular monolith, một CSDL dùng chung schema, Docker; không Redis, Kafka hay microservices |
| NCC dùng miễn phí, extranet, value web (D6) | Supplier Portal trong cùng SPA, truy cập theo quan hệ được mời |
| Bảo mật báo giá, giảm chi phí giám sát (TCE) | Phân quyền theo từng bản ghi, hạn chót theo giờ máy chủ, thông báo không chứa giá |
| Giảm chi phí tìm kiếm và so sánh (TCE) | Báo giá có cấu trúc + chấm điểm trọng số công khai công thức |
| Giảm thời gian đáp ứng (D3, mẫu số giá trị khách hàng) | Hộp thư thông báo + Server-Sent Events |
| Không thu phí giao dịch, không giữ tiền (Mục 5.3) | Tiền đi qua cổng thanh toán của đối tác; nền tảng chỉ ghi nhận và đối soát IPN có chữ ký; không lưu dữ liệu thẻ |
| Đối tác chính là cổng thanh toán, hóa đơn điện tử, chữ ký số (BMC, D8) | Một adapter tích hợp, đổi sang đối tác thật chỉ thay adapter; kết quả về bằng callback ký HMAC |
| Bảo mật báo giá, chống chối bỏ | Ký số báo giá; xác minh chứng thư bằng khóa CA tin cậy; phát hiện dữ liệu bị sửa sau khi ký |
| Tri thức ẩn → tri thức hiện (D7) | Phiên bản báo giá, score snapshot, lý do lựa chọn, đánh giá NCC, audit log |
| Kiểm soát bằng KPI (SMART, BSC) | Lưu mốc thời gian (gửi PR, publish RFQ, giao đủ) và module dashboard tính KPI |

## 6.2. Kiến trúc tổng thể

Ở mức ngữ cảnh (C4 mức 1), ProcureHub có ba nhóm người dùng bên ngoài: nhân sự bên mua (Buyer, Manager, Finance), nhân sự nhà cung cấp, và ba hệ thống ngoài: cổng thanh toán, nhà cung cấp hóa đơn điện tử (kèm bước cơ quan thuế cấp mã) và dịch vụ ký số từ xa. Trong bản demo, cả ba được giả lập trong một dịch vụ riêng (sandbox-service). Email và ERP/kế toán là hệ thống ngoài của lộ trình P2.

Ở mức container (Hình 6.1), hệ thống gồm bốn khối. **Web SPA** (Vite, React 19, Ant Design) chạy trên trình duyệt, phục vụ cả Buyer Portal và Supplier Portal, menu theo vai trò. **API** (Django 5.2, Django REST Framework, gunicorn) là nơi duy nhất kiểm tra quyền và đổi trạng thái. **PostgreSQL 16** lưu toàn bộ dữ liệu giao dịch. **sandbox-service** là dịch vụ riêng giả lập ba đối tác: ProcureHub gọi nó bằng khóa API, người dùng thao tác trên trang của nó (trang thanh toán, trang nhập OTP để ký, trang tra cứu hóa đơn), và nó gửi kết quả về API bằng callback ký HMAC. Trình duyệt gọi API qua HTTPS bằng REST có JWT, và nhận thông báo qua một luồng SSE riêng.

![Hình 6.1. Kiến trúc container của ProcureHub (C4 mức 2)](figures/fig_6_1_architecture.png) {landscape}

ProcureHub chọn **modular monolith** thay vì microservices. Với nhóm bốn người và MVP bốn tuần, một ứng dụng chia module theo nghiệp vụ cho phép phát triển nhanh và giữ tính nhất quán mạnh cho chuỗi thao tác liên quan nhau (duyệt lựa chọn → sinh PO → hóa đơn → thanh toán) trong một transaction. Ranh giới module rõ ràng giữ khả năng tách thành service riêng khi tải tăng.

## 6.3. Các module và trách nhiệm

Bảng 6.2. Module backend

| Module | Trách nhiệm | Thực thể chính |
|---|---|---|
| identity | Người dùng, doanh nghiệp, vai trò, JWT, dữ liệu mẫu | Company, User, UserRole |
| suppliers | Quan hệ bên mua – NCC, đánh giá NCC | SupplierRelationship, SupplierEvaluation |
| procurement | PR, RFQ, lời mời, báo giá, chấm điểm, lựa chọn | PurchaseRequest, RFQ, Quotation, SupplierSelection |
| purchase_orders | PO, dòng PO, giao nhận | PurchaseOrder, DeliveryRecord |
| billing | Hóa đơn (VAT 10%), công nợ, thanh toán, hóa đơn điện tử | Invoice, Payment, PaymentEvent |
| integrations | Adapter gọi đối tác, xác thực callback HMAC, xác minh chữ ký số, lưu khóa CA tin cậy | TrustAnchor |
| notifications | Hộp thư, quy tắc người nhận, luồng SSE | Notification |
| audit | Audit log, request ID, phạm vi truy cập | AuditEvent |
| dashboard | Tổng hợp số liệu, việc cần xử lý, KPI | — |

Các module nghiệp vụ gọi hai dịch vụ dùng chung là ghi audit và tạo thông báo; hai dịch vụ này không phụ thuộc ngược vào module nghiệp vụ.

## 6.4. Mô hình dữ liệu

Hệ thống dùng chung một cơ sở dữ liệu cho nhiều doanh nghiệp (shared schema). Mọi bản ghi nghiệp vụ gắn với doanh nghiệp sở hữu, hoặc với quan hệ giữa hai doanh nghiệp (lời mời RFQ, PO, hóa đơn) để xác định ai được thấy. PO là bản chụp (snapshot) báo giá được chọn, nên thay đổi ở báo giá gốc không làm đổi PO đã phát hành. Tiền dùng kiểu số thập phân, không dùng số thực.

![Hình 6.2. Mô hình dữ liệu khái niệm](figures/fig_6_2_erd.png) {landscape}

## 6.5. Đa doanh nghiệp, phân quyền và bảo mật

Bảng 6.3. Ma trận quyền tóm tắt

| Tác vụ | Buyer | Manager | Finance | Supplier |
|---|---|---|---|---|
| Tạo, gửi PR; tạo RFQ; đề xuất NCC; phát hành PO; nhận hàng | Có | — | — | — |
| Duyệt PR và lựa chọn NCC | — | Có (không tự duyệt) | — | — |
| Gửi báo giá, xác nhận PO, lập hóa đơn | — | — | — | Có (chỉ dữ liệu của mình) |
| Tạo lệnh thanh toán, mô phỏng kết quả | — | — | Có | — |
| Xem bảng điểm, đánh giá NCC | Có | Có | — | — |

Bảng 6.4. Biện pháp bảo mật theo lớp

| Lớp | Biện pháp |
|---|---|
| Xác thực | Access token 15 phút chỉ giữ trong bộ nhớ trình duyệt; refresh token trong cookie httpOnly, xoay vòng và thu hồi khi đăng xuất |
| Phân quyền chức năng | Phân quyền theo vai trò (RBAC) kiểm tra ở máy chủ |
| Phân quyền theo bản ghi | Mọi truy vấn lọc theo doanh nghiệp suy ra từ người đăng nhập, không tin mã doanh nghiệp do client gửi; bản ghi ngoài phạm vi trả 404 để chống dò ID (IDOR) |
| Toàn vẹn | Transaction và khóa dòng cho mọi chuyển trạng thái; khóa chống lặp (Idempotency-Key) khi sinh PO và tạo thanh toán |
| Webhook | Chữ ký HMAC-SHA256 trên nội dung gốc, so sánh hằng thời gian; secret bắt buộc từ môi trường, không có giá trị mặc định |
| Truy vết | Audit log chỉ ghi thêm, mỗi sự kiện có request ID trả về cho client |
| Dữ liệu | Thông báo không chứa giá; không ghi log nội dung request, token hay chữ ký; không lưu dữ liệu thẻ |
| Chữ ký số | Chứng thư xác minh bằng khóa CA tin cậy đã ghim; kiểm mã số thuế, thời hạn; tính lại mã băm mỗi lần hiển thị |

Hệ thống được nghiệm thu qua các kịch bản: không đọc chéo dữ liệu giữa hai bên mua hoặc giữa các nhà cung cấp; không tự duyệt; không sửa báo giá sau hạn; hai yêu cầu phát hành PO đồng thời chỉ tạo một PO; webhook trùng không ghi nhận hai lần; chữ ký từ CA lạ hoặc sai mã số thuế bị từ chối; dữ liệu báo giá bị sửa sau khi ký bị phát hiện; khôi phục bản sao lưu thành công.

## 6.6. Thông báo thời gian thực

Khi một bên đổi trạng thái (ví dụ nhà cung cấp gửi báo giá), máy chủ ghi thay đổi, audit log và bản ghi thông báo cho người nhận trong **cùng một transaction**. Bảng thông báo vì vậy đóng vai trò outbox: không có trường hợp dữ liệu đã đổi mà mất thông báo, hoặc dữ liệu bị hoàn tác mà thông báo vẫn phát. Trình duyệt của người nhận giữ một kết nối Server-Sent Events; máy chủ kiểm tra thông báo mới mỗi hai giây và đẩy xuống. Kết nối tự đóng sau 25 giây để không chiếm tài nguyên máy chủ, rồi trình duyệt nối lại từ thông báo cuối cùng đã nhận. Người dùng offline vẫn xem được thông báo chưa đọc khi đăng nhập lại.

SSE được chọn thay WebSocket vì luồng chỉ đi một chiều từ máy chủ xuống, chạy trên HTTP thường và không cần thêm hạ tầng (Redis, Channels). Trình duyệt đọc luồng bằng fetch để gửi token qua header, không đưa token lên URL.

![Hình 6.3. Luồng thông báo khi nhà cung cấp gửi báo giá](figures/fig_6_3_notification_sequence.png) {landscape}

## 6.7. Chấm điểm báo giá theo trọng số

Mỗi báo giá được chấm bốn điểm thành phần trên thang 0–100: giá (S_price = 100 × giá thấp nhất / giá báo), thời gian giao (S_delivery = 100 × (ngày giao nhanh nhất + 1) / (ngày giao + 1)), uy tín (S_rating = 100 × điểm đánh giá trung bình / 5, NCC chưa có đánh giá dùng mức trung lập 3/5) và điều khoản (S_terms = 100 × số ngày công nợ / số ngày dài nhất). Tổng điểm là trung bình có trọng số; trọng số mặc định 45/25/20/10, Buyer chỉnh được trước khi chọn.

Trong lần chạy thử, TechVision báo giá thấp hơn nhưng giao 12 ngày, công nợ 30 ngày; Digital Supply đắt hơn nhưng giao 4 ngày, công nợ 45 ngày. Với trọng số mặc định, Digital Supply đạt 89,21 điểm, TechVision đạt 79,28 điểm. Buyer vẫn có thể chọn TechVision vì giá, nhưng phải ghi lý do và Manager duyệt. Đây chính là điểm khác biệt so với so sánh bằng Excel: tiêu chí và trọng số được công khai trước, điểm được lưu lại, và quyết định khác điểm phải có giải trình.

## 6.8. Tích hợp đối tác: hóa đơn điện tử, cổng thanh toán, chữ ký số

Ba đối tác này là điểm tích hợp thật của một nền tảng Source-to-Pay. Bản demo giả lập chúng trong một dịch vụ riêng nhưng giữ đúng cách tích hợp: gọi bằng khóa API, người dùng thao tác trên trang của đối tác, kết quả về bằng callback có chữ ký HMAC, và mọi lời gọi mạng đặt ngoài transaction để đối tác chậm không khóa dữ liệu. Đổi sang đối tác thật chỉ cần thay lớp adapter.

**Hóa đơn và hóa đơn điện tử.** Sau khi PO giao đủ, NCC lập hóa đơn trên Supplier Portal: tiền trước thuế bằng tổng PO, VAT 10%, hạn trả theo số ngày công nợ đã chốt (Net 30 nếu báo giá không ghi). Hóa đơn được gửi ngay sang nhà cung cấp hóa đơn điện tử; nhà cung cấp kiểm tra số học (thành tiền, tổng, thuế), cấp ký hiệu và số, rồi vài giây sau "cơ quan thuế" cấp mã và báo về. Hóa đơn có mã tra cứu và tải được XML. Hóa đơn đã gửi cơ quan thuế không được hủy (thực tế phải lập hóa đơn điều chỉnh).

**Thanh toán qua cổng.** Finance tạo một hoặc nhiều lệnh, mỗi lệnh không vượt số dư trừ các lệnh đang chờ; trình duyệt được chuyển sang trang cổng thanh toán để chọn ngân hàng. Số dư chỉ thay đổi khi máy chủ nhận IPN có chữ ký và đúng số tiền; IPN gửi lại cùng mã sự kiện không được ghi hai lần. Việc người dùng được chuyển về trang hóa đơn chỉ để hiển thị, không phải căn cứ ghi nhận tiền.

**Chữ ký số báo giá.** NCC bấm "Ký số báo giá", hệ thống chuẩn hóa nội dung báo giá (dòng hàng, giá, thời gian giao, điều khoản), tính mã băm SHA-256 và gửi sang dịch vụ ký từ xa; NCC nhập OTP, dịch vụ ký mã băm bằng khóa riêng của chứng thư cấp theo mã số thuế. ProcureHub chỉ chấp nhận chữ ký khi chứng thư do CA tin cậy cấp, đúng mã số thuế, còn hiệu lực và chữ ký khớp mã băm. Mỗi lần hiển thị, hệ thống tính lại mã băm từ dữ liệu đang lưu: chỉ cần ai đó sửa giá trực tiếp trong cơ sở dữ liệu, bảng so sánh của bên mua sẽ báo "chữ ký không hợp lệ".

Mọi trang của đối tác giả lập đều gắn nhãn "giả lập, không có giá trị pháp lý"; ký hiệu hóa đơn, mã cơ quan thuế và chứng thư cố ý mang định dạng khác thật để không bị dùng nhầm.

![Hình 6.4. Luồng thanh toán qua cổng và IPN idempotent](figures/fig_6_4_payment_sequence.png) {landscape}

## 6.9. Hạ tầng năm lớp, web server và hosting

Theo hạ tầng E-business năm lớp (Chaffey, 2011), ProcureHub gồm: (I) ứng dụng: Buyer Portal và Supplier Portal bằng React, Ant Design, Django REST Framework, JWT; (II) phần mềm hệ thống: Linux, NGINX, gunicorn, PostgreSQL, Docker Compose; (III) truyền tải: Internet, TCP/IP, HTTPS/TLS, DNS, REST API /api/v1, Server-Sent Events, webhook; (IV) lưu trữ và vật lý: máy chủ ảo, CSDL managed trên cloud (IaaS/PaaS), sao lưu định kỳ; (V) nội dung và dữ liệu: doanh nghiệp, quan hệ nhà cung cấp, PR, RFQ, báo giá có phiên bản, PO, phiếu nhận, hóa đơn, thanh toán, thông báo, audit log.

Web server cho B2B phải sẵn sàng 24/7, ổn định, có dự phòng và bảo mật. ProcureHub chọn NGINX vì hiệu năng cao, ít tốn tài nguyên, hỗ trợ cân bằng tải và là mã nguồn mở; NGINX được cấu hình không đệm (buffer) luồng SSE để thông báo đến ngay. Hệ thống thuê hosting cloud thay vì tự đặt máy chủ, dùng CSDL managed có bản sao dự phòng. ProcureHub cung cấp phần mềm dạng SaaS và tự vận hành trên IaaS/PaaS của nhà cung cấp cloud; cách này giảm chi phí hạ tầng nhưng chuyển một phần quyền kiểm soát dữ liệu cho bên thứ ba, nên cần mã hóa, sao lưu và giữ khả năng chuyển nhà cung cấp. Thông báo e-mail (P2) gửi qua dịch vụ SMTP bên thứ ba, chỉ chứa liên kết, không chứa nội dung báo giá.

## 6.10. AI và hướng mở rộng

AI không thuộc MVP; bảng điểm hiện tại là chấm điểm trọng số có công thức công khai. Hướng mở rộng gồm gợi ý nhà cung cấp theo lịch sử báo giá và đánh giá, phát hiện báo giá bất thường, trích xuất báo giá từ tệp PDF (OCR), luôn để người dùng duyệt trước khi quyết định. Các mở rộng P2 khác: kết nối cổng thanh toán, nhà cung cấp hóa đơn điện tử và tổ chức chứng thực chữ ký số thật (thay adapter), ký số PO và hóa đơn, kế toán/ERP, chat theo RFQ, phê duyệt nhiều cấp theo hạn mức.

## 6.11. Mã nguồn và trạng thái triển khai

Mã nguồn bản demo ProcureHub: https://drive.google.com/drive/folders/1IjBIgbUcX1YhkJ70pTUFpGuXhy2_oRSL

Bảng 6.5. Trạng thái triển khai tại ngày 14/10/2026

| Nhóm chức năng | Mức | Trạng thái |
|---|---|---|
| Đăng nhập, phân quyền, tách doanh nghiệp, PR, RFQ, báo giá, lựa chọn, PO, giao nhận, audit | P0 | Đã kiểm thử |
| Thông báo realtime (hộp thư + SSE), request ID | P0 | Đã kiểm thử |
| Chấm điểm báo giá theo trọng số | P0 | Đã kiểm thử |
| Vai trò Finance, hóa đơn VAT 10% và Net N, thanh toán nhiều lần, webhook có chữ ký | P1 | Đã kiểm thử |
| Tích hợp đối tác giả lập: cổng thanh toán, hóa đơn điện tử, ký số báo giá | P1 | Đã kiểm thử |
| Đánh giá NCC, ngân sách PR, KPI dashboard | P1 | Đã kiểm thử |
| Giao diện các tính năng trên | P0/P1 | Đã triển khai (kiểm tra bằng build và ảnh chụp, chưa có test giao diện tự động) |
| Kết nối đối tác thật, ký số PO/hóa đơn, chat, OCR, ERP, AI, email, phê duyệt theo hạn mức | P2 | Đề xuất |

"Đã kiểm thử" nghĩa là có test tự động chạy qua trên cả SQLite và PostgreSQL (47 test backend, cộng 13 test của dịch vụ giả lập đối tác), cùng các lần chạy toàn luồng qua HTTP thật giữa hai dịch vụ. Chi tiết ở Phụ lục D.

![Hình 6.5. Dashboard KPI của Manager](figures/screenshots/01_dashboard_kpi.png)

![Hình 6.6. Bảng điểm trọng số trong màn hình RFQ](figures/screenshots/02_rfq_scoring.png)

![Hình 6.7. Thông báo realtime trên Supplier Portal](figures/screenshots/04_supplier_notifications.png)

![Hình 6.8. Trang nhập OTP của dịch vụ ký số từ xa (giả lập)](figures/screenshots/09_esign_otp.png)

![Hình 6.9. Bảng so sánh báo chữ ký không hợp lệ sau khi giá bị sửa trong cơ sở dữ liệu](figures/screenshots/12_comparison_signature_invalid.png)

![Hình 6.10. Hóa đơn có VAT và trạng thái hóa đơn điện tử (Finance)](figures/screenshots/06_invoices_einvoice.png)

![Hình 6.11. Trang tra cứu hóa đơn điện tử có mã cơ quan thuế (giả lập)](figures/screenshots/07_einvoice_lookup.png)

![Hình 6.12. Trang cổng thanh toán (giả lập)](figures/screenshots/08_payment_gateway.png)

# 7. TRIỂN KHAI CHIẾN LƯỢC

Mục này trình bày cách đưa chiến lược vào thực tế: phương pháp, nhân sự, kiểm thử và quản lý rủi ro.

## 7.1. Phương pháp, nguồn lực và nhân sự

Nhóm áp dụng Agile. Backlog được ưu tiên theo giá trị và rủi ro: P0 gồm luồng PR → PO, thông báo realtime, bảng điểm, dashboard và audit; P1 gồm hóa đơn, tích hợp đối tác (giả lập), đánh giá NCC và KPI; P2 gồm kết nối đối tác thật và các mở rộng khác. Cuối mỗi sprint nhóm kiểm thử, trình diễn và cập nhật backlog (Project Management Institute, 2017). Triển khai cho khách hàng không chỉ là cài phần mềm: đầu tư công nghệ chỉ có hiệu quả khi đi cùng chuẩn hóa quy trình mua, đào tạo theo vai trò và quản lý thay đổi (hiện tượng "nghịch lý năng suất"). E-marketing dùng nội dung hướng dẫn, case study pilot và webinar cùng đối tác.

Bảng 7.1. Lộ trình bốn giai đoạn của sản phẩm

| Giai đoạn | Đầu ra | Trạng thái |
|---|---|---|
| 1. Nền tảng | Thiết kế CSDL; đăng nhập, phân quyền, tách doanh nghiệp; dữ liệu mẫu Buyer/Supplier | Hoàn thành |
| 2. Mua sắm lõi | PR, phê duyệt, RFQ, báo giá, so sánh, lựa chọn, PO | Hoàn thành |
| 3. Trải nghiệm | Thông báo realtime, bảng điểm, audit timeline, giao diện theo vai trò | Hoàn thành |
| 4. Mở rộng và kiểm thử | Hóa đơn VAT, hóa đơn điện tử, thanh toán qua cổng, ký số báo giá (đối tác giả lập), đánh giá NCC, KPI, kiểm thử bảo mật, demo toàn luồng | Hoàn thành phần kỹ thuật; kiểm thử khả dụng với người dùng thật ở M3 |

**Nhân sự theo giai đoạn.** Trong học kỳ (M1–M5), bốn thành viên kiêm nhiệm khảo sát, thiết kế và làm prototype, không tính lương. Giai đoạn MVP và pilot (0–6 tháng) cần 1 PO/BA, 2 lập trình viên và 1 nhân sự bán hàng – onboarding, với đầu tư ban đầu 600 triệu đồng. Giai đoạn tăng trưởng (6–18 tháng) thêm 1 chăm sóc khách hàng và 1 quản lý kênh đối tác, lập trình viên bảo trì bán thời gian; chi phí cố định 39 triệu đồng/tháng.

## 7.2. Khảo sát, kiểm thử và pilot

- **Khảo sát M1:** phỏng vấn 6–10 người tại 3–5 doanh nghiệp (requester, manager, buyer, kế toán, supplier), có đồng ý và ẩn danh; thu 3–5 giao dịch PR → thanh toán gần nhất làm baseline (mẫu thuận tiện).
- **Định nghĩa đo:** cycle time = thời điểm phát hành PO − thời điểm gửi PR; báo cáo trung vị, không kết luận nhân quả khi thiếu nhóm đối chứng. Dashboard tính sẵn sáu KPI theo định nghĩa này.
- **Kiểm thử kỹ thuật:** 39 test tự động (phân quyền, chuyển trạng thái, chống truy cập chéo, chấm điểm, thông báo, hóa đơn, webhook) chạy trên SQLite và PostgreSQL; smoke test sau mỗi lần triển khai.
- **Kiểm thử khả dụng:** 5–8 người dùng làm theo kịch bản; đo tỷ lệ hoàn thành, thời gian và điểm SUS (Brooke, 1996).
- **Pilot:** chạy 2–3 tuần với giao dịch thật giá trị nhỏ nếu doanh nghiệp đồng ý (thanh toán vẫn qua ngân hàng, nền tảng chỉ ghi nhận); nếu không, gọi đúng là kiểm thử chấp nhận người dùng (UAT). Go/no-go theo KPI ở Mục 8.

## 7.3. Yếu tố thành công và rủi ro

ProcureHub đáp ứng bảy yếu tố thành công cho SME (Chaffey, 2011): hiệu quả, thuận tiện, kiểm soát, hình ảnh, cam kết, quan hệ đối tác và cải tiến quy trình.

Bảng 7.2. Rủi ro triển khai và biện pháp phòng ngừa

| Rủi ro / nguyên nhân thất bại | Biện pháp phòng ngừa |
|---|---|
| Đánh giá quá cao tốc độ chấp nhận; sai thời điểm | Có kịch bản tài chính bi quan; đo kích hoạt thực tế trước khi mở rộng |
| Dịch vụ miễn phí; mô hình kinh doanh yếu | Giới hạn gói Free; theo dõi tỷ lệ chuyển đổi; thử giá và đo mức sẵn sàng chi trả ở M1 |
| Tham vọng quá mức; phạm vi phình to | Khóa P0 trước; thanh toán và KPI là P1; OCR, AI, ERP là P2 |
| Nhà cung cấp ít phản hồi RFQ | Tài khoản NCC miễn phí, gửi báo giá không cần hồ sơ dài, thông báo tức thời; đo tỷ lệ phản hồi theo lời mời |
| Lộ dữ liệu chéo giữa doanh nghiệp | Lọc phạm vi tập trung ở máy chủ; test truy cập chéo cho từng loại dữ liệu mới |
| Thanh toán, hóa đơn, chữ ký giả lập bị hiểu là thật | Nhãn "giả lập" trên mọi trang, định dạng ký hiệu/mã/chứng thư khác thật, không nhận dữ liệu thẻ |
| Đối tác chậm hoặc ngừng dịch vụ | Gọi đối tác ngoài transaction, có thời gian chờ, ghi trạng thái lỗi và cho thử lại; tắt tích hợp thì nền tảng vẫn chạy |
| Báo cáo mô tả sai năng lực triển khai | Phân biệt Đề xuất / Đã triển khai / Đã kiểm thử (Bảng 6.5) |

# 8. KIỂM SOÁT HIỆU QUẢ DỰ ÁN

Hiệu quả của chiến lược được kiểm soát bằng bộ KPI và mô hình tài chính dưới đây.

## 8.1. Bộ KPI

Bảng 8.1. KPI kiểm soát hiệu quả theo nhóm

| Nhóm | Chỉ số | Cách đo | Ngưỡng |
|---|---|---|---|
| Quy trình | Thời gian PR → PO; thời gian duyệt PR; tỷ lệ RFQ đi đến PO | Dashboard (trung vị), so với baseline M1 | Giảm ≥ 30%; giảm ≥ 30%; ≥ 80% |
| Chi phí giao dịch | Số lần trao đổi ngoài hệ thống mỗi RFQ; tiết kiệm so với ngân sách ước tính | Buyer tự khai; dashboard | Giảm ≥ 50%; công bố phương pháp tính |
| Người dùng | Hoàn thành kịch bản không trợ giúp; SUS; CSAT | Kiểm thử khả dụng, bảng hỏi | ≥ 90%; SUS ≥ 68; CSAT ≥ 4/5 |
| Nhà cung cấp | Phản hồi RFQ đúng hạn; thời gian phản hồi; giao đúng hạn | Dashboard | ≥ 70%; ≤ 48 giờ; ≥ 90% |
| Tài chính khách hàng | Hóa đơn quá hạn; chu trình hóa đơn → đã thanh toán | Dashboard hóa đơn | Giảm so với baseline |
| Công nghệ | API p95; thông báo đến người nhận; uptime; lỗi lộ dữ liệu chéo; webhook ghi trùng; audit coverage; khôi phục backup | Smoke test, giám sát, test tự động | < 500 ms; ≤ 5 giây; ≥ 99%; 0; 0; 100%; ≥ 1 lần |

KPI công nghệ là release gate trước demo; các ngưỡng khác hiệu chỉnh sau baseline (SUS 68 là mốc trung bình). Số liệu trên dashboard demo là dữ liệu mẫu, không phải kết quả nghiên cứu.

## 8.2. Mô hình tài chính giả định

**a) ROI phía khách hàng.** Giả định: 30 PR/tháng; 6 giờ công thủ công mỗi PR; tiết kiệm 30% giờ công; chi phí lao động 100.000 đồng/giờ; gói Business 4 triệu đồng/tháng; phí triển khai 10 triệu đồng. Lợi ích = 30 × 6 × 30% × 0,1 = 5,4 triệu đồng/tháng, tức 64,8 triệu đồng năm đầu; tổng phí năm đầu = 12 × 4 + 10 = 58 triệu đồng; ROI năm đầu = (64,8 − 58) / 58 ≈ 11,7%. Khách hàng hòa vốn khi có khoảng 27 PR/tháng; doanh nghiệp 15 PR/tháng hợp gói Starter (lợi ích 32,4 so với chi phí 29 triệu đồng/năm). Tính toán này chưa gồm lợi ích từ theo dõi công nợ (giảm trễ hạn, giảm giờ công đối soát) và tiết kiệm giá mua; hai khoản này sẽ được ước lượng từ dữ liệu pilot thay vì giả định.

**b) Hòa vốn của nền tảng.** Chi phí cố định 39 triệu đồng/tháng, biến phí 0,8 triệu đồng/khách hàng/tháng, đầu tư ban đầu 600 triệu đồng; ARPA xét theo ba kịch bản cơ cấu gói:

Bảng 8.2. Độ nhạy điểm hòa vốn vận hành theo cơ cấu gói (đơn vị: triệu đồng)

| Kịch bản | Starter / Business / Enterprise | ARPA | Đóng góp/khách hàng | Hòa vốn (khách hàng) |
|---|---|---|---|---|
| Bi quan | 70% / 30% / 0% | 2,6 | 1,8 | 22 |
| Cơ sở | 50% / 50% / 0% | 3,0 | 2,2 | 18 |
| Thuận lợi | 20% / 70% / 10% | 4,0 | 3,2 | 13 |

Ở kịch bản cơ sở với 30 khách hàng, dòng tiền vận hành đạt 90 − 63 = 27 triệu đồng/tháng; hoàn vốn lý thuyết khoảng 600 / 27 ≈ 22 tháng. Với chi phí thu hút một khách hàng (CAC) giả định 15 triệu đồng và tỷ lệ rời bỏ (churn) 3%/tháng, giá trị vòng đời khách hàng LTV ≈ 2,2 / 0,03 ≈ 73 triệu đồng và LTV/CAC ≈ 4,9, cao hơn ngưỡng 3 thường dùng cho SaaS; nếu churn lên 6%/tháng, LTV/CAC còn khoảng 2,4. Việc đặt hóa đơn và KPI ở gói trả phí (Mục 5.3) nhằm đẩy cơ cấu gói về phía kịch bản thuận lợi; hiệu quả thật sẽ đo bằng tỷ lệ nâng cấp gói sau pilot.

# 9. MILESTONES CỦA DỰ ÁN

Bảng 9.1. Kế hoạch milestones gắn với lịch học kỳ

| Mốc | Thời gian | Đầu ra chính | Điều kiện hoàn thành |
|---|---|---|---|
| M0. Prototype | Đến 15/10/2026 | Mã nguồn, dịch vụ giả lập đối tác, 60 test tự động, đề cương, URD/SRS/HLD | Đã xong |
| M1. Khảo sát | 16/10 – 29/10/2026 | Phỏng vấn, AS-IS, baseline (gồm hóa đơn, công nợ), dữ liệu thị trường | Có dữ liệu hoặc ghi rõ phần thiếu |
| M2. Thiết kế lại theo dữ liệu | 30/10 – 12/11/2026 | Điều chỉnh TO-BE, Business Model Canvas, bảng giá, trọng số mặc định theo khảo sát | Review chéo nghiệp vụ, bảo mật |
| M3. Kiểm thử khả dụng | 13/11 – 24/11/2026 | Kiểm thử 5–8 người dùng, sửa lỗi, đo KPI công nghệ | Demo toàn luồng; đạt release gate |
| M4. Báo cáo final | 25/11 – 01/12/2026 | Báo cáo final, slide, tài chính cập nhật | Nộp đúng hạn (tuần 12) |
| M5. Thuyết trình | Tuần 13–15 | Trình bày, demo 8–12 phút; sau môn học: pilot | Theo lịch của lớp; go/no-go (Mục 8) |

Kịch bản demo 8–12 phút: (1) vấn đề và vai trò; (2) Buyer tạo PR có ngân sách, Manager duyệt, Buyer tạo RFQ; (3) mở trình duyệt thứ hai cho Supplier, thông báo đến không cần làm mới trang, hai nhà cung cấp báo giá, TechVision ký số báo giá bằng OTP; (4) Buyer xem bảng điểm, đề xuất, Manager duyệt, phát hành PO; (5) Supplier xác nhận, Buyer nhận hàng, Supplier lập hóa đơn Net 30 có VAT, hóa đơn điện tử được cấp mã, Finance thanh toán 30% qua trang cổng rồi phần còn lại; (6) đánh giá nhà cung cấp, xem dashboard KPI, audit và thử truy cập trái quyền bị chặn.

# 10. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

ProcureHub là giải pháp E-business phía buy-side giúp SME chuẩn hóa chuỗi Source-to-Pay ở mức ghi nhận theo mô hình E-procurement SaaS, khác biệt hóa bằng minh bạch, triển khai theo Agile và kiểm soát bằng KPI. Báo cáo không dừng ở mô hình kinh doanh mà làm rõ cách mô hình đó được hiện thực: mỗi lập luận kinh doanh (tách quyền, giảm chi phí giao dịch, không thu phí giao dịch, tri thức hiện) có một quyết định kiến trúc tương ứng và một bằng chứng kiểm thử.

Giới hạn: chưa có dữ liệu thật về giao dịch, thị trường và giá đối thủ; cổng thanh toán, hóa đơn điện tử và chữ ký số mới tích hợp với đối tác giả lập; chưa tích hợp kế toán/ERP và AI; chưa kiểm thử khả dụng với người dùng thật. Bước tiếp theo: khảo sát, đo baseline ở M1, hiệu chỉnh trọng số mặc định và bảng giá theo dữ liệu, kiểm thử khả dụng ở M3 và cập nhật mô hình tài chính bằng dữ liệu thực.

# TÀI LIỆU THAM KHẢO

Bezemer, C.-P., & Zaidman, A. (2010). Multi-tenant SaaS applications: Maintenance dream or nightmare? In Proceedings of the Joint ERCIM Workshop on Software Evolution and International Workshop on Principles of Software Evolution (IWPSE-EVOL) (pp. 88–92). ACM. https://doi.org/10.1145/1862372.1862393

Brooke, J. (1996). SUS: A "quick and dirty" usability scale. In P. W. Jordan, B. Thomas, B. A. Weerdmeester, & I. L. McClelland (Eds.), Usability evaluation in industry (pp. 189–194). Taylor & Francis.

Brown, S. (2018). The C4 model for visualising software architecture. https://c4model.com

Chaffey, D. (2011). E-business and e-commerce management: Strategy, implementation and practice (5th ed.). Pearson Education.

Chính phủ. (2025a). Nghị định số 356/2025/NĐ-CP ngày 31 tháng 12 năm 2025 hướng dẫn Luật Bảo vệ dữ liệu cá nhân. https://vanban.chinhphu.vn/?classid=1&docid=216387&pageid=27160

Chính phủ. (2025b). Nghị định số 70/2025/NĐ-CP ngày 20 tháng 3 năm 2025 sửa đổi Nghị định số 123/2020/NĐ-CP về hóa đơn, chứng từ. https://vanban.chinhphu.vn/?docid=213179&lang=vi&pageid=27160

Croom, S., & Brandon-Jones, A. (2007). Impact of e-procurement: Experiences from implementation in the UK public sector. Journal of Purchasing and Supply Management, 13(4), 294–303. https://doi.org/10.1016/j.pursup.2007.09.015

Davila, A., Gupta, M., & Palmer, R. (2003). Moving procurement systems to the Internet: The adoption and use of e-procurement technology models. European Management Journal, 21(1), 11–23. https://doi.org/10.1016/S0263-2373(02)00155-X

Davis, F. D. (1989). Perceived usefulness, perceived ease of use, and user acceptance of information technology. MIS Quarterly, 13(3), 319–340. https://doi.org/10.2307/249008

Hadi Putra, P. O., & Santoso, H. B. (2020). Contextual factors and performance impact of e-business use in Indonesian small and medium enterprises (SMEs). Heliyon, 6(3), e03568. https://doi.org/10.1016/j.heliyon.2020.e03568

Kaplan, R. S., & Norton, D. P. (1992). The balanced scorecard: Measures that drive performance. Harvard Business Review, 70(1), 71–79.

Krawczyk, H., Bellare, M., & Canetti, R. (1997). HMAC: Keyed-hashing for message authentication (RFC 2104). Internet Engineering Task Force. https://doi.org/10.17487/RFC2104

Laudon, K. C., & Traver, C. G. (2021). E-commerce 2021: Business, technology, society (16th ed.). Pearson Education.

Porter, M. E. (2001). Strategy and the Internet. Harvard Business Review, 79(3), 62–78.

Project Management Institute. (2017). Agile practice guide. Project Management Institute.

Quốc hội. (2023). Luật Giao dịch điện tử số 20/2023/QH15. https://vanban.chinhphu.vn/?classid=1&docid=208421&pageid=27160&typegroupid=3

Quốc hội. (2025). Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15. https://vanban.chinhphu.vn/?classid=1&docid=214590&orggroupid=1&pageid=27160

Richardson, C. (2018). Microservices patterns: With examples in Java. Manning Publications.

Thủ tướng Chính phủ. (2020). Quyết định số 749/QĐ-TTg phê duyệt Chương trình Chuyển đổi số quốc gia đến năm 2025, định hướng đến năm 2030. https://vanban.chinhphu.vn/?docid=200163&pageid=27160&tagid=7&type=1

Trần, V. H. T. (2026). Bài giảng Hệ kinh doanh điện tử – Chương 2: E-business strategy (Part 1, Part 2) [Slide bài giảng]. Trường Đại học Công nghệ Thông tin, ĐHQG-HCM.

Venkatesh, V., Morris, M. G., Davis, G. B., & Davis, F. D. (2003). User acceptance of information technology: Toward a unified view. MIS Quarterly, 27(3), 425–478. https://doi.org/10.2307/30036540

Williamson, O. E. (1981). The economics of organization: The transaction cost approach. American Journal of Sociology, 87(3), 548–577. https://doi.org/10.1086/227496
