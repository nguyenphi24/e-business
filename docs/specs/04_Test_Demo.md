# Kiểm thử, demo và trạng thái triển khai

## 1. Môi trường kiểm thử

| Hạng mục | Giá trị |
|---|---|
| Ngày chạy | 14–15/10/2026 |
| Backend | Django 5.2, Python 3.11.15 (`.venv311`) |
| Database | SQLite (test nhanh) và PostgreSQL 16 qua `scripts/acceptance_postgres.sh` |
| Frontend | Vite + React 19, Node 22.23.2 |
| Bộ test tự động | ProcureHub: 47 test backend — pass trên SQLite và PostgreSQL. sandbox-service: 13 test |
| Kiểm thử khác | E2E qua HTTP thật giữa ProcureHub và sandbox-service (script Python), `scripts/smoke_demo.sh`, ảnh chụp UI bằng Chrome headless, build và chạy thử image Docker của sandbox-service |

## 2. Test case ưu tiên

| ID | Tình huống | Kết quả mong đợi | Test tự động | Kết quả |
|---|---|---|---|---|
| TC-01 | Tạo PR, gửi, Manager duyệt | Chỉ Manager quyết định, người tạo không tự duyệt, có audit | `test_api` | Pass |
| TC-02 | Supplier không được mời mở RFQ | Không thấy nội dung | `test_sourcing_api` | Pass |
| TC-03 | Supplier A xem báo giá Supplier B | Bị chặn | `test_sourcing_api` | Pass |
| TC-04 | Chấm điểm báo giá | Điểm thành phần và tổng khớp công thức ở Phụ lục B mục 5 | `ScoringFormulaTests` | Pass |
| TC-04b | Trọng số tổng ≠ 100; đổi sau `AWARDED` | 422; 409 | `ScoringApiTests` | Pass |
| TC-05 | Hai trình duyệt Buyer/Supplier | Thông báo đến không cần refresh | `NotificationStreamTests` + E2E | Pass; E2E đo 0,8 giây từ publish RFQ đến khi Supplier nhận |
| TC-06 | Webhook gửi trùng `event_id` | Không ghi nhận hai lần | `test_webhook_rejects_bad_signature_and_ignores_duplicates` | Pass |
| TC-07 | Thanh toán 30% rồi phần còn lại | `PARTIALLY_PAID` → `PAID`, số dư 0 | `test_partial_then_full_payment` + E2E | Pass |
| TC-08 | Mất kết nối SSE | Thông báo chưa đọc vẫn có qua REST; nối lại bằng `after` không phát trùng | `test_inbox_is_private_and_can_be_marked_read`, `test_stream_replays_after_last_event_id_for_recipient_only` | Pass |
| TC-09 | Tenant A đổi URL sang tenant B | 404, không lộ dữ liệu | `test_other_tenant_cannot_see_invoice`, smoke cross-company | Pass |
| TC-10 | Webhook sai chữ ký | 401 `invalid_signature` | billing tests + smoke | Pass |
| TC-11 | Thanh toán vượt số dư / thiếu Idempotency-Key / Buyer tạo thanh toán | 422 / 422 / 403 | `test_payment_validation` | Pass |
| TC-12 | Lập hóa đơn khi PO chưa giao; lập trùng | 409; 409 | `test_invoice_requires_delivered_po`, `test_invoice_uses_po_terms_and_is_unique` | Pass |
| TC-13 | Đánh giá NCC trước khi hoàn tất; đánh giá lần hai; điểm ngoài 1–5 | 409; 409; 422 | `test_evaluation_rules_and_rating_summary` | Pass |
| TC-14 | KPI dashboard | Đủ 6 KPI, có `n`; Supplier không nhận KPI | `test_dashboard_reports_kpis_for_buyer_side_only` | Pass |
| TC-15 | Request ID | Header được trả lại và lưu vào audit; ID sai định dạng bị thay | `RequestIdTests` | Pass |
| TC-16 | Thiếu `SANDBOX_WEBHOOK_SECRET` (cả hai service) | Ứng dụng dừng khi khởi động | Kiểm tra thủ công (`KeyError`) | Pass |
| TC-17 | Thanh toán qua cổng | Payment `SANDBOX_GW` có `checkout_url`; số dư đổi sau IPN; IPN sai số tiền bị từ chối | `PaymentGatewayTests` + E2E | Pass |
| TC-18 | Cổng thanh toán không phản hồi | Payment `FAILED`, tạo lại được lệnh cho toàn bộ số dư | `test_gateway_unreachable_marks_payment_failed_and_frees_balance` | Pass |
| TC-19 | Hóa đơn VAT 10% và hóa đơn điện tử | Trước thuế = tổng PO, VAT 10%; chờ cấp mã → `ISSUED`; callback trùng bỏ qua; đã có mã không hủy được | `EInvoiceTests` + E2E | Pass |
| TC-20 | Ký số báo giá và phát hiện sửa dữ liệu | Ký OTP → `VALID`; sửa giá trong DB → `INVALID`; CA lạ / sai MST → `FAILED` | `QuotationSignatureTests` + E2E | Pass |
| TC-21 | Sandbox: chặn callback/redirect ngoài allowlist, OTP sai 3 lần, số học hóa đơn sai | 400 / `LOCKED` / 400 | test của sandbox-service | Pass |

## 3. Kịch bản demo đã chạy thử (E2E)

Chạy trên PostgreSQL với dữ liệu mẫu, qua HTTP thật tới `runserver`:

| Bước | Kết quả quan sát |
|---|---|
| Buyer tạo PR (Màn hình ×10, Cáp HDMI ×20, Android Box ×5, ngân sách 70 triệu), Manager duyệt | Header `X-Request-ID` được trả lại |
| Buyer tạo RFQ, mời TechVision + Digital Supply, publish | Supplier nhận `RFQ_PUBLISHED` qua SSE sau 0,8 giây |
| TechVision: rẻ hơn, giao 12 ngày, Net 30; Digital Supply: đắt hơn, giao 4 ngày, Net 45 | Buyer nhận 2 thông báo `QUOTATION_SUBMITTED` |
| Bảng điểm với trọng số mặc định 45/25/20/10 | Digital Supply 89,21 điểm (hạng 1), TechVision 79,28 (hạng 2) |
| Buyer vẫn đề xuất TechVision kèm lý do; Buyer thử tự duyệt | 403; Manager duyệt thành công |
| PO → xác nhận → giao đủ → hoàn tất → đánh giá NCC | Thành công |
| TechVision lập hóa đơn | `INV-2026-0002`, hạn 13/11/2026 (Net 30); tenant khác nhận 404 |
| Finance thanh toán 30% (mô phỏng) rồi phần còn lại qua webhook HMAC | `PARTIALLY_PAID` → `PAID`, số dư 0; gửi lại webhook trả `duplicate: true` |

Lần chạy thứ hai (15/10/2026) có sandbox-service, qua HTTP thật giữa hai service:

| Bước | Kết quả quan sát |
|---|---|
| TechVision ký số báo giá: mở trang ký, nhập OTP | Bảng so sánh của bên mua: "Chữ ký hợp lệ" (TechVision) |
| Sửa trực tiếp đơn giá trong DB (`demo_tamper_quotation`), rồi khôi phục | "Chữ ký không hợp lệ – nội dung báo giá đã bị thay đổi sau khi ký" → khôi phục giá thì hợp lệ lại |
| TechVision lập hóa đơn | Trước thuế 42.400.000, VAT 4.240.000, tổng 46.640.000; hóa đơn điện tử "chờ cấp mã" → sau ~3 giây có ký hiệu `SBX26`, số 1 và mã cơ quan thuế giả lập; trang tra cứu hiển thị đúng tổng |
| Finance thanh toán 30% qua trang cổng, bấm "Thanh toán thành công" | Cổng chuyển về `/invoices?...&status=SUCCEEDED`; hóa đơn "trả một phần", còn 32.648.000 |
| Thanh toán phần còn lại, rồi cổng gửi lại IPN cùng `event_id` | Hóa đơn "đã thanh toán", số dư 0, không bị cộng tiền lần hai |
| Dashboard Manager | Thời gian duyệt PR 6 giờ (n = 3), tỷ lệ NCC báo giá 100% (n = 3), giao đúng hạn 100% (n = 2), tiết kiệm 26,1 triệu (20,1%) |

Lưu ý cho thuyết trình: bảng điểm xếp NCC giao nhanh lên đầu dù không rẻ nhất. Đây là điểm minh họa cho nguyên tắc "điểm hỗ trợ, con người quyết định": Buyer có thể chọn khác nhưng phải ghi lý do, và Manager duyệt.

Số liệu KPI ở trên là dữ liệu seed và dữ liệu thử nghiệm, không phải kết quả khảo sát doanh nghiệp.

## 4. Trạng thái triển khai

| Nhóm yêu cầu | Mức | Trạng thái |
|---|---|---|
| Auth, RBAC, tenant scope, PR, RFQ, quotation, selection, PO, delivery, audit | P0 | Tested |
| Request ID trong audit (FR-AUD-04) | P0 | Tested |
| Notification inbox + SSE (FR-NOTI-01..05) | P0 | Tested |
| Chấm điểm trọng số, score snapshot (FR-RFQ-07..09, FR-QUO-08, FR-CMP-05..06) | P0 | Tested |
| Vai trò Finance | P1 | Tested |
| Hóa đơn Net N (FR-INV-01..05) | P1 | Tested |
| Thanh toán qua cổng giả lập, webhook HMAC idempotent (FR-PAY-01..06) | P1 | Tested |
| Tích hợp sandbox-service: hóa đơn VAT 10% + hóa đơn điện tử, ký số báo giá (FR-INT, FR-EINV, FR-SIGN) | P1 | Tested |
| Đánh giá NCC (FR-EVAL-01..03) | P1 | Tested |
| Ngân sách PR, KPI dashboard (FR-PR-07..08, FR-DASH-05..06) | P1 | Tested |
| Giao diện (chuông thông báo, bảng điểm, trang Hóa đơn, đánh giá, KPI, chữ ký số, hóa đơn điện tử, chuyển sang cổng thanh toán) | P0/P1 | Implemented — kiểm tra bằng build, typecheck và ảnh chụp Chrome headless; chưa có test UI tự động |
| Chat RFQ, đính kèm/OCR, ký số PO và hóa đơn, kết nối cổng thanh toán / hóa đơn điện tử / ký số thật, ERP, AI, email, phê duyệt theo hạn mức | P2 | Proposed |
| Response envelope toàn cục, request logging, `/metrics` | Chuẩn kỹ thuật | Proposed |

## 5. Ảnh chụp màn hình

Ảnh chụp được trình bày ở thân báo cáo (Mục 6): dashboard KPI (Manager), bảng điểm trọng số (RFQ), hóa đơn và hóa đơn điện tử (Finance), chuông thông báo (Supplier), trang cổng thanh toán, trang ký OTP, trang tra cứu hóa đơn điện tử, bảng so sánh có chữ ký hợp lệ và không hợp lệ.
