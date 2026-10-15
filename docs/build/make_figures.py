"""Sinh các sơ đồ SVG cho báo cáo (cùng phong cách sơ đồ trong báo cáo của nhóm).

Chạy: python3 make_figures.py <thư mục ra>. Sau đó render_figures.js đổi SVG sang PNG.
"""
import sys
from html import escape
from pathlib import Path

NAVY = "#1f3864"
LANE_HEAD = "#dbe4f3"
LANE_FILL = "#f3f6fb"
LANE_LINE = "#8fa3c7"
NOTE_FILL = "#fff4d6"
NOTE_LINE = "#d4a017"
ACCENT = "#176b87"
MUTED = "#5b6b82"
FONT = "Times New Roman, Times, serif"


class Svg:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.parts = []

    def add(self, raw):
        self.parts.append(raw)

    def rect(self, x, y, w, h, fill="#fff", stroke=NAVY, sw=2, rx=10, dash=None):
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash_attr}/>')

    def text(self, x, y, lines, size=17, weight="normal", anchor="middle", color="#111", line_gap=1.2, italic=False):
        if isinstance(lines, str):
            lines = [lines]
        style = ' font-style="italic"' if italic else ""
        total = (len(lines) - 1) * size * line_gap
        start = y - total / 2
        for i, line in enumerate(lines):
            self.add(
                f'<text x="{x}" y="{start + i * size * line_gap:.1f}" font-family="{FONT}" font-size="{size}" '
                f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}" dominant-baseline="middle"{style}>{escape(line)}</text>'
            )

    def box(self, x, y, w, h, lines, size=16, fill="#fff", stroke=NAVY, weight="normal", dash=None, rx=10):
        self.rect(x, y, w, h, fill=fill, stroke=stroke, rx=rx, dash=dash)
        self.text(x + w / 2, y + h / 2, lines, size=size, weight=weight)

    def path(self, points, color=NAVY, sw=2, dash=None, arrow=True, both=False):
        d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in points)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        marker = ' marker-end="url(#arrow)"' if arrow else ""
        if both:
            marker += ' marker-start="url(#arrow-start)"'
        self.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{dash_attr}{marker}/>')

    def label(self, x, y, text, size=14, color=MUTED, anchor="middle", bg=True):
        if bg:
            width = len(text) * size * 0.48 + 10
            left = x - width / 2 if anchor == "middle" else (x if anchor == "start" else x - width)
            self.add(f'<rect x="{left:.1f}" y="{y - size * 0.75:.1f}" width="{width:.1f}" height="{size * 1.5:.1f}" fill="#fff" opacity="0.92"/>')
        self.text(x, y, text, size=size, color=color, anchor=anchor)

    def render(self):
        defs = (
            f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{NAVY}"/></marker>'
            f'<marker id="arrow-start" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{NAVY}"/></marker></defs>'
        )
        body = "\n".join(self.parts)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">{defs}<rect width="100%" height="100%" fill="#fff"/>{body}</svg>'
        )


def swimlane():
    lanes = ["Nhà cung cấp", "Manager", "Buyer", "Finance"]
    lane_h, top, head_w = 128, 20, 132
    col_w, box_w, box_h, x0 = 124, 112, 84, head_w + 14
    steps = [
        (2, ["Tạo PR", "(ngân sách", "ước tính)"]),
        (1, ["Duyệt PR"]),
        (2, ["Lập RFQ,", "trọng số,", "mời ≥ 2 NCC"]),
        (0, ["Gửi / sửa", "báo giá", "trước hạn"]),
        (2, ["Bảng điểm,", "đề xuất NCC", "+ lý do"]),
        (1, ["Duyệt", "lựa chọn"]),
        (2, ["Phát hành PO", "(khóa giá,", "Net N)"]),
        (0, ["Xác nhận /", "từ chối PO"]),
        (2, ["Nhận hàng,", "đánh giá NCC"]),
        (0, ["Lập hóa đơn", "(hạn = Net N)"]),
        (3, ["Thanh toán", "sandbox", "(nhiều lần)"]),
    ]
    width = x0 + col_w * len(steps) + 10
    note_y = top + lane_h * len(lanes) + 24
    svg = Svg(width, note_y + 70)
    for i, name in enumerate(lanes):
        y = top + i * lane_h
        svg.add(f'<rect x="4" y="{y}" width="{width - 8}" height="{lane_h}" fill="{LANE_FILL}" stroke="{LANE_LINE}" stroke-width="2"/>')
        svg.add(f'<rect x="4" y="{y}" width="{head_w}" height="{lane_h}" fill="{LANE_HEAD}" stroke="{LANE_LINE}" stroke-width="2"/>')
        svg.text(4 + head_w / 2, y + lane_h / 2, name.split(" ", 1) if name == "Nhà cung cấp" else [name], size=21, weight="bold")
    centers = []
    for c, (lane, lines) in enumerate(steps):
        x = x0 + c * col_w
        y = top + lane * lane_h + (lane_h - box_h) / 2
        svg.box(x, y, box_w, box_h, lines, size=16)
        centers.append((x, y, lane))
    for (x, y, lane), (nx, ny, nlane) in zip(centers, centers[1:]):
        start = (x + box_w, y + box_h / 2)
        mid_x = nx + box_w / 2
        if nlane == lane:
            svg.path([start, (nx, ny + box_h / 2)])
        else:
            end_y = ny if nlane > lane else ny + box_h
            svg.path([start, (mid_x, start[1]), (mid_x, end_y)])
    svg.rect(x0, note_y, width - x0 - 14, 52, fill=NOTE_FILL, stroke=NOTE_LINE, rx=4)
    svg.text(
        x0 + (width - x0 - 14) / 2, note_y + 26,
        "Thông báo realtime (SSE) ở mỗi bước chuyển trạng thái  •  Audit log kèm request ID  •  Tách quyền: người tạo/đề xuất không tự duyệt  •  Thanh toán sandbox, không giữ tiền",
        size=16,
    )
    return svg.render()


def architecture():
    svg = Svg(1480, 820)
    # Người dùng
    svg.box(40, 24, 300, 56, ["Buyer · Manager · Finance"], size=18, weight="bold", fill="#eef3fb")
    svg.box(40, 96, 300, 56, ["Supplier (nhà cung cấp)"], size=18, weight="bold", fill="#eef3fb")
    # Trình duyệt + SPA
    svg.rect(24, 190, 332, 400, fill=LANE_FILL, stroke=LANE_LINE, rx=14)
    svg.text(190, 214, "Trình duyệt", size=18, weight="bold", color=MUTED)
    svg.box(44, 236, 292, 330, [], size=16)
    svg.text(190, 262, "Web SPA", size=20, weight="bold")
    svg.text(190, 290, "Vite + React 19 + Ant Design", size=16, color=MUTED)
    for i, item in enumerate(["Buyer Portal", "Supplier Portal", "Finance · Hóa đơn"]):
        svg.box(66, 312 + i * 52, 248, 40, [item], size=16, fill="#f7f9fd")
    svg.text(190, 486, "Access token chỉ trong bộ nhớ", size=15, color=MUTED)
    svg.text(190, 510, "Refresh token: cookie httpOnly", size=15, color=MUTED)
    svg.text(190, 534, "Nhận SSE bằng fetch streaming", size=15, color=MUTED)
    svg.path([(190, 152), (190, 190)])
    # nginx
    svg.box(410, 330, 150, 110, ["nginx", "HTTPS / TLS", "reverse proxy"], size=16, fill="#f7f9fd")
    svg.path([(356, 360), (410, 360)])
    svg.label(383, 342, "REST", size=13)
    svg.path([(410, 412), (356, 412)], dash="6 4")
    svg.label(383, 430, "SSE", size=13)
    # API
    ax, ay, aw, ah = 610, 120, 520, 560
    svg.rect(ax, ay, aw, ah, fill="#fff", stroke=NAVY, rx=14)
    svg.text(ax + aw / 2, ay + 28, "API — Django 5.2 + DRF (gunicorn gthread)", size=20, weight="bold")
    svg.text(ax + aw / 2, ay + 54, "Modular monolith · REST /api/v1 · SSE · Webhook", size=15, color=MUTED)
    svg.box(ax + 20, ay + 74, aw - 40, 50, ["RequestId → JWT Auth → RBAC → Tenant Guard (company scope)"], size=15, fill="#eef3fb")
    modules = [
        ("identity", "User, Company, vai trò"),
        ("suppliers", "Quan hệ NCC, đánh giá"),
        ("procurement", "PR, RFQ, báo giá, chấm điểm"),
        ("purchase_orders", "PO, giao nhận"),
        ("billing", "Hóa đơn VAT, thanh toán, HĐĐT"),
        ("notifications", "Inbox, người nhận, SSE"),
        ("audit", "Audit log, request ID"),
        ("dashboard + integrations", "KPI · adapter, webhook, ký số"),
    ]
    for i, (name, desc) in enumerate(modules):
        cx = ax + 20 + (i % 2) * 250
        cy = ay + 146 + (i // 2) * 96
        svg.rect(cx, cy, 230, 80, fill="#f7f9fd", stroke=NAVY, rx=8)
        svg.text(cx + 115, cy + 28, name, size=17, weight="bold")
        svg.text(cx + 115, cy + 54, desc, size=14, color=MUTED)
    svg.path([(560, 360), (ax, 360)])
    svg.path([(ax, 412), (560, 412)], dash="6 4")
    # PostgreSQL
    dx, dy = 1230, 330
    svg.add(f'<path d="M {dx} {dy + 18} a 100 18 0 0 1 200 0 v 130 a 100 18 0 0 1 -200 0 z" fill="#f7f9fd" stroke="{NAVY}" stroke-width="2"/>')
    svg.add(f'<path d="M {dx} {dy + 18} a 100 18 0 0 0 200 0" fill="none" stroke="{NAVY}" stroke-width="2"/>')
    svg.text(dx + 100, dy + 52, "PostgreSQL 16", size=18, weight="bold")
    svg.text(dx + 100, dy + 108, ["Shared schema, có company", "notifications = outbox", "transaction + khóa dòng"], size=14, color=MUTED)
    svg.path([(ax + aw, 400), (dx, 400)], both=True)
    # Cổng giả lập
    svg.rect(1190, 110, 270, 200, fill=NOTE_FILL, stroke=NOTE_LINE, rx=12)
    svg.text(1325, 134, "sandbox-service (giả lập)", size=17, weight="bold")
    for i, item in enumerate(["Cổng thanh toán + IPN", "Hóa đơn điện tử + CQT cấp mã", "Ký số từ xa + CA (OTP)"]):
        svg.box(1205, 152 + i * 50, 240, 40, [item], size=15, fill="#fff", stroke=NOTE_LINE)
    svg.path([(ax + aw, 180), (1190, 180)])
    svg.label(1160, 164, "API key", size=13)
    svg.path([(1190, 260), (ax + aw, 260)])
    svg.label(1160, 278, "callback HMAC", size=13)
    # P2
    svg.box(1210, 560, 240, 120, ["Mở rộng P2", "Email · ERP/kế toán", "Nhà cung cấp thật", "(thanh toán, HĐĐT, ký số) · AI"], size=15, fill="#fff", stroke=MUTED, dash="7 5")
    svg.path([(ax + aw, 620), (1210, 620)], dash="7 5", color=MUTED)
    # Ghi chú
    svg.rect(24, 712, 1426, 84, fill=NOTE_FILL, stroke=NOTE_LINE, rx=4)
    svg.text(737, 738, "Mũi tên liền: REST có Bearer JWT; mũi tên đứt: luồng SSE /notifications/stream (server → client, đóng sau 25 giây, client nối lại với id cuối).", size=15)
    svg.text(737, 768, "Nhà cung cấp ngoài gọi qua adapter (đổi sang dịch vụ thật chỉ thay adapter); mọi kết quả về bằng callback ký HMAC, chữ ký số xác minh bằng khóa CA đã ghim.", size=15)
    return svg.render()


def erd():
    svg = Svg(1480, 940)
    entities = {
        "Company": (40, 40, ["id, legal_name, tax_code", "company_type, category"]),
        "User / UserRole": (400, 40, ["company_id, email", "role: BUYER, MANAGER,", "FINANCE, SUPPLIER, ADMIN"]),
        "Notification": (760, 40, ["recipient_id, event_type", "entity, title, read_at"]),
        "AuditEvent": (1120, 40, ["actor_id, action, entity", "payload, request_id"]),
        "SupplierRelationship": (40, 260, ["buyer_company_id", "supplier_company_id, status"]),
        "PurchaseRequest (+Line)": (400, 260, ["company_id, requester_id", "estimated_budget, submitted_at"]),
        "RFQ (+Line, Invitation)": (760, 260, ["deadline, status", "scoring_weights, published_at"]),
        "Quotation (+Line, Revision)": (1120, 260, ["supplier_company_id, total", "delivery_days, payment_term_days"]),
        "SupplierEvaluation": (40, 480, ["quality_score, delivery_score", "buyer/supplier company"]),
        "PurchaseOrder (+Line, Delivery)": (400, 480, ["snapshot giá, payment_term_days", "issued_at, delivered_at"]),
        "SupplierSelection": (760, 480, ["rationale, score_snapshot", "proposed_by, decided_by"]),
        "QuotationSignature": (1120, 480, ["revision, document_hash", "signature, certificate, status"]),
        "Invoice": (400, 700, ["subtotal, VAT 10%, total, due_date", "e-invoice: ký hiệu, số, mã CQT"]),
        "Payment": (760, 700, ["amount, status, provider", "external_ref, checkout_url"]),
        "PaymentEvent": (1120, 700, ["event_id (unique)", "status, duplicate_count"]),
    }
    w, h = 320, 130
    boxes = {}
    for name, (x, y, fields) in entities.items():
        svg.rect(x, y, w, h, fill="#fff", stroke=NAVY, rx=8)
        svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="40" rx="8" fill="{LANE_HEAD}" stroke="{NAVY}" stroke-width="2"/>')
        svg.text(x + w / 2, y + 21, name, size=18, weight="bold")
        svg.text(x + w / 2, y + 40 + (h - 40) / 2, fields, size=15, color=MUTED)
        boxes[name] = (x, y)

    def side(name, where):
        x, y = boxes[name]
        return {"r": (x + w, y + h / 2), "l": (x, y + h / 2), "t": (x + w / 2, y), "b": (x + w / 2, y + h)}[where]

    relations = [
        ("Company", "r", "User / UserRole", "l", "1 — *"),
        ("Company", "b", "SupplierRelationship", "t", "1 — * (buyer, supplier)"),
        ("User / UserRole", "r", "Notification", "l", "1 — *"),
        ("Notification", "r", "AuditEvent", "l", ""),
        ("User / UserRole", "b", "PurchaseRequest (+Line)", "t", "1 — * (requester)"),
        ("PurchaseRequest (+Line)", "r", "RFQ (+Line, Invitation)", "l", "1 — *"),
        ("RFQ (+Line, Invitation)", "r", "Quotation (+Line, Revision)", "l", "1 — *"),
        ("RFQ (+Line, Invitation)", "b", "SupplierSelection", "t", "1 — *"),
        ("SupplierSelection", "l", "PurchaseOrder (+Line, Delivery)", "r", "1 — 1"),
        ("PurchaseOrder (+Line, Delivery)", "l", "SupplierEvaluation", "r", "1 — 0..1"),
        ("PurchaseOrder (+Line, Delivery)", "b", "Invoice", "t", "1 — *"),
        ("Invoice", "r", "Payment", "l", "1 — *"),
        ("Payment", "r", "PaymentEvent", "l", "1 — *"),
    ]
    for a, sa, b, sb, text in relations:
        p1, p2 = side(a, sa), side(b, sb)
        if not text:
            continue
        svg.path([p1, p2], arrow=False)
        svg.label((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 - (14 if p1[1] == p2[1] else 0), text, size=14, color=NAVY)
    # Quotation — Selection (đường gấp khúc đi qua khe giữa hai cột)
    qx, qy = boxes["Quotation (+Line, Revision)"]
    sx, sy = side("SupplierSelection", "r")
    svg.path([(qx + 40, qy + h), (qx + 40, qy + h + 40), (qx - 20, qy + h + 40), (qx - 20, sy), (sx, sy)], arrow=False)
    svg.label(qx - 20, qy + h + 40, "1 — * (được chọn)", size=13, color=NAVY)
    # Quotation — QuotationSignature
    tx, ty = side("Quotation (+Line, Revision)", "b")
    svg.path([(tx + 60, ty), (tx + 60, boxes["QuotationSignature"][1])], arrow=False)
    svg.label(tx + 60, ty + 50, "1 — *", size=14, color=NAVY)
    svg.rect(40, 870, 1400, 44, fill=NOTE_FILL, stroke=NOTE_LINE, rx=4)
    svg.text(740, 892, "Mọi bản ghi nghiệp vụ gắn company sở hữu hoặc quan hệ (Invitation, PO, Invoice) để kiểm tra phạm vi truy cập. AuditEvent ghi actor (User) cho mọi thực thể.", size=15)
    return svg.render()


def sequence(title_participants, messages, height, notes=()):
    width = 1480
    count = len(title_participants)
    gap = (width - 320) / (count - 1)
    xs = [160 + i * gap for i in range(count)]
    svg = Svg(width, height)
    for x, name in zip(xs, title_participants):
        svg.box(x - 120, 20, 240, 60, name.split("\n"), size=17, weight="bold", fill=LANE_HEAD)
        svg.add(f'<line x1="{x}" y1="80" x2="{x}" y2="{height - 20}" stroke="{LANE_LINE}" stroke-width="2" stroke-dasharray="6 6"/>')
    y = 120
    for item in messages:
        kind = item[0]
        if kind == "msg":
            _, a, b, text, dashed = item
            x1, x2 = xs[a], xs[b]
            svg.path([(x1, y), (x2, y)], dash="7 5" if dashed else None)
            svg.label((x1 + x2) / 2, y - 16, text, size=15, color="#111")
            y += 58
        elif kind == "self":
            _, a, lines = item
            x = xs[a]
            box_h = 26 * len(lines) + 16
            left = x + 14 if x + 14 + 470 <= width - 10 else x - 14 - 470
            svg.rect(left, y - 14, 470, box_h, fill="#f7f9fd", stroke=NAVY, rx=6)
            for i, line in enumerate(lines):
                svg.text(left + 14, y + 6 + i * 26, line, size=15, anchor="start")
            y += box_h + 26
        elif kind == "note":
            _, text = item
            svg.rect(60, y - 18, width - 120, 40, fill=NOTE_FILL, stroke=NOTE_LINE, rx=4)
            svg.text(width / 2, y + 2, text, size=15)
            y += 58
    return svg.render()


def notification_sequence():
    return sequence(
        ["Supplier\n(trình duyệt)", "API Django", "PostgreSQL", "Buyer\n(trình duyệt)"],
        [
            ("msg", 3, 1, "GET /notifications/stream?after=N (Bearer, giữ kết nối)", False),
            ("msg", 0, 1, "POST /quotations/{id}/submit", False),
            ("self", 1, [
                "transaction.atomic():",
                "  cập nhật Quotation, lưu QuotationRevision",
                "  ghi AuditEvent (request_id)",
                "  ghi Notification cho Buyer (outbox)",
            ]),
            ("msg", 1, 2, "COMMIT (dữ liệu + thông báo cùng lúc)", False),
            ("msg", 1, 0, "200 SUBMITTED", True),
            ("msg", 1, 2, "poll mỗi 2 giây: Notification id > N của Buyer", False),
            ("msg", 1, 3, "id: N+1 · event: notification · data {title, path}", True),
            ("self", 3, ["Hiện badge + toast, không cần refresh"]),
            ("note", "Sau 25 giây server đóng luồng → client nối lại với after=N+1. Offline → đăng nhập lại và GET /notifications?unread=true."),
        ],
        height=760,
    )


def payment_sequence():
    return sequence(
        ["Finance\n(trình duyệt)", "API Django", "Cổng thanh toán\n(sandbox-service)", "PostgreSQL"],
        [
            ("msg", 0, 1, "POST /invoices/{id}/payments (Idempotency-Key, amount)", False),
            ("msg", 1, 3, "khóa Invoice; amount ≤ số dư − lệnh đang chờ; Payment PENDING; COMMIT", False),
            ("msg", 1, 2, "POST /gateway/transactions (X-Api-Key) — ngoài transaction", False),
            ("msg", 2, 1, "checkout_url", True),
            ("msg", 1, 0, "201 Payment PENDING + checkout_url", True),
            ("msg", 0, 2, "chuyển tới trang cổng, chọn ngân hàng, bấm thanh toán", False),
            ("msg", 2, 1, "POST /webhooks/payment (IPN) + X-Sandbox-Signature (HMAC)", False),
            ("self", 1, [
                "kiểm tra chữ ký (compare_digest), số tiền khớp",
                "PaymentEvent(event_id unique) — trùng → duplicate",
                "khóa Payment + Invoice, PENDING → SUCCEEDED",
                "paid_amount += amount → PARTIALLY_PAID / PAID",
                "audit + thông báo Finance và Supplier",
            ]),
            ("msg", 1, 3, "COMMIT", False),
            ("msg", 2, 0, "302 về /invoices?payment=…&status=SUCCEEDED (chỉ để hiển thị)", True),
            ("msg", 2, 1, "gửi lại cùng event_id → 200 {duplicate: true}, không đổi số dư", True),
        ],
        height=1000,
    )


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    figures = {
        "fig_3_1_source_to_pay.svg": swimlane(),
        "fig_6_1_architecture.svg": architecture(),
        "fig_6_2_erd.svg": erd(),
        "fig_6_3_notification_sequence.svg": notification_sequence(),
        "fig_6_4_payment_sequence.svg": payment_sequence(),
    }
    for name, content in figures.items():
        (out / name).write_text(content, encoding="utf-8")
        print(out / name)


if __name__ == "__main__":
    main()
