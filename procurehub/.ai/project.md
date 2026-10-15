# Project context

## Mục tiêu

ProcureHub mô phỏng nền tảng E-Procurement B2B cho bên mua, nhà cung cấp, quản lý và system admin. Phạm vi bám theo spec tại `../docs/specs/` (Source-to-Pay mức ghi nhận: notification realtime, chấm điểm trọng số, hóa đơn Net N, thanh toán sandbox, đánh giá NCC, KPI), kế thừa `../docs/` v1.1.

## Trạng thái thật

- Backend Django 5.2 chạy được với SQLite cho test nhanh và PostgreSQL 16 qua Docker.
- Frontend Vite + React 19 đã có các màn hình workflow chính.
- Seed demo có đủ nhiều company để kiểm tra company isolation, thêm user Finance, đánh giá NCC và một hóa đơn đã trả 30%.
- Test backend và acceptance PostgreSQL đã chạy pass trước khi ghi file này.

## Quyết định đã chốt

- Backend dùng Django REST Framework và JWT.
- Refresh token nằm trong httpOnly cookie; access token chỉ giữ trong memory phía frontend.
- Frontend dùng Vite + React Router SPA, client-side data fetching và không có SSR.
- PostgreSQL là database mục tiêu; SQLite chỉ là fallback phục vụ test nhanh.
- Realtime dùng SSE đọc bảng `notifications`, không dùng WebSocket/Channels/Redis.
- Thanh toán chỉ là sandbox: không giữ tiền, không thu phí giao dịch, không nhận dữ liệu thẻ. `SANDBOX_WEBHOOK_SECRET` bắt buộc; nút mô phỏng nội bộ chỉ chạy khi `PAYMENT_SANDBOX_ENABLED=true` và chỉ cho payment `MOCK`.
- Tích hợp cổng thanh toán, hóa đơn điện tử, ký số đi qua repo `../sandbox-service` (giả lập). `SANDBOX_BASE_URL` trống thì tắt tích hợp và hệ thống vẫn chạy (nút mô phỏng, không HĐĐT, không ký số).
- VAT cố định 10%, chỉ tính ở bước lập hóa đơn; báo giá, PO, bảng điểm, KPI vẫn dùng giá trước thuế.
- Vai trò Buyer gộp Requester + Procurement Officer trong tài liệu phân tích; thêm vai trò `FINANCE`.

## Cố tình để dở

- P2 của spec chưa làm: chat RFQ, đính kèm/OCR, cổng thanh toán và hóa đơn điện tử thật (hiện là sandbox), ERP, AI gợi ý, email, phê duyệt nhiều cấp theo hạn mức, worker outbox riêng.
- Ký số mới áp dụng cho báo giá (chưa ký PO, chưa ký hóa đơn); không tự thử lại callback bị lỡ — người dùng bấm "Làm mới"/"Phát hành lại".
- API của PO vẫn nằm trong `apps/procurement/api.py` (chưa tách sang `purchase_orders`), giữ để không đổi import khi mở rộng.
- System Admin đọc dữ liệu toàn cục để hỗ trợ demo (sai khác có chủ đích so với tài liệu phân tích).

- Có production Docker/deploy skeleton; chưa chạy rollout trên server thật.
- Cấu hình env dùng `SECRET_KEY`, `DEBUG`, `DATABASE_*`; production vẫn cần inject secret thật qua môi trường deploy.
- Cổng local thống nhất trong dải `40000–49999`: PostgreSQL `45432`, backend `48000`, frontend `43000`.
