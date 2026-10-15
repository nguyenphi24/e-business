# Tài liệu

| Thư mục / tệp | Nội dung |
|---|---|
| `report/01_De_cuong_bao_cao.docx` | Đề cương báo cáo đầy đủ: bối cảnh, cơ sở lý thuyết, phân tích nghiệp vụ, chiến lược E-business, mô hình kinh doanh, kiến trúc hệ thống, triển khai, KPI, tài chính |
| `report/01_De_cuong_bao_cao_short.docx` | Bản rút gọn 14 trang |
| `report/02_Phu_luc_URD_SRS_HLD.docx` | Phụ lục A–D: URD, SRS, HLD, kiểm thử và demo |
| `report/*.md` | Nguồn Markdown của các tệp .docx |
| `specs/` | URD, SRS, HLD, Test & demo — nguồn chuẩn cho phụ lục và cho mã nguồn |
| `figures/` | Sơ đồ (SVG + PNG), logo, ảnh chụp màn hình thật (`screenshots/`) |
| `build/` | Script sinh sơ đồ và chuyển Markdown → .docx |
| `Kich_ban_demo.md` | Kịch bản demo 10–12 phút: tài khoản từng vai trò, thao tác từng bước, cách reset dữ liệu |
| `Ke_hoach_cap_nhat_source.md` | Kế hoạch và kết quả cập nhật mã nguồn |

## Dựng lại tài liệu

Cần Python 3, Node 22+ và Google Chrome (để chuyển SVG sang PNG).

```bash
cd docs/build
npm install
npm run figures   # sơ đồ: figures/*.svg → *.png
npm run docx      # report/*.md + specs/*.md → report/*.docx
```

Mở .docx bằng Word và cập nhật trường (F9) để mục lục hiện số trang.
