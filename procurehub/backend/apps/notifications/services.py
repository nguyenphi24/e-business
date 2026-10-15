"""Quy tắc người nhận thông báo (SRS mục 3.3).

Module này không import module domain: thực thể được đọc theo thuộc tính (number, company_id...).
Gọi `notify_event()` bên trong transaction của thay đổi trạng thái để thông báo và dữ liệu commit cùng lúc.
"""
from apps.identity.models import User
from apps.notifications.models import Notification


def users_with_roles(company_id, *roles):
    if not company_id:
        return []
    return list(
        User.objects.filter(company_id=company_id, is_active=True, roles__role_code__in=roles).distinct()
    )


def _rfq_number(quotation):
    return quotation.rfq.number


RULES = {
    # event_type: (người nhận, tiêu đề, đường dẫn trên SPA)
    "PR_SUBMITTED": (
        lambda pr: users_with_roles(pr.company_id, "MANAGER"),
        lambda pr: f"{pr.number} chờ duyệt",
        "/purchase-requests",
    ),
    "PR_APPROVED": (lambda pr: [pr.requester], lambda pr: f"{pr.number} đã được duyệt", "/purchase-requests"),
    "PR_REJECTED": (lambda pr: [pr.requester], lambda pr: f"{pr.number} bị từ chối", "/purchase-requests"),
    "RFQ_PUBLISHED": (
        lambda rfq: [
            user
            for invitation in rfq.invitations.all()
            for user in users_with_roles(invitation.supplier_company_id, "SUPPLIER")
        ],
        lambda rfq: f"Lời mời báo giá {rfq.number} từ {rfq.company.legal_name}",
        "/rfqs",
    ),
    "QUOTATION_SUBMITTED": (
        lambda quotation: users_with_roles(quotation.rfq.company_id, "BUYER"),
        lambda quotation: f"{quotation.supplier_company.legal_name} đã gửi báo giá cho {_rfq_number(quotation)}",
        "/rfqs",
    ),
    "SELECTION_PROPOSED": (
        lambda selection: users_with_roles(selection.rfq.company_id, "MANAGER"),
        lambda selection: f"Lựa chọn nhà cung cấp cho {selection.rfq.number} chờ duyệt",
        "/rfqs",
    ),
    "SELECTION_APPROVED": (
        lambda selection: [selection.proposed_by],
        lambda selection: f"Lựa chọn nhà cung cấp cho {selection.rfq.number} đã được duyệt",
        "/rfqs",
    ),
    "SELECTION_REJECTED": (
        lambda selection: [selection.proposed_by],
        lambda selection: f"Lựa chọn nhà cung cấp cho {selection.rfq.number} bị từ chối",
        "/rfqs",
    ),
    "PO_ISSUED": (
        lambda po: users_with_roles(po.supplier_company_id, "SUPPLIER"),
        lambda po: f"Đơn đặt hàng {po.number} từ {po.company.legal_name}",
        "/purchase-orders",
    ),
    "PO_CANCELLED": (
        lambda po: users_with_roles(po.supplier_company_id, "SUPPLIER"),
        lambda po: f"Đơn đặt hàng {po.number} đã bị hủy",
        "/purchase-orders",
    ),
    "PO_ACKNOWLEDGED": (
        lambda po: users_with_roles(po.company_id, "BUYER"),
        lambda po: f"{po.supplier_company.legal_name} đã xác nhận {po.number}",
        "/purchase-orders",
    ),
    "PO_DECLINED": (
        lambda po: users_with_roles(po.company_id, "BUYER"),
        lambda po: f"{po.supplier_company.legal_name} đã từ chối {po.number}",
        "/purchase-orders",
    ),
    "INVOICE_ISSUED": (
        lambda invoice: users_with_roles(invoice.buyer_company_id, "FINANCE"),
        lambda invoice: f"Hóa đơn {invoice.number} từ {invoice.supplier_company.legal_name}",
        "/invoices",
    ),
    "QUOTATION_SIGNED": (
        lambda quotation: users_with_roles(quotation.rfq.company_id, "BUYER"),
        lambda quotation: f"{quotation.supplier_company.legal_name} đã ký số báo giá cho {_rfq_number(quotation)}",
        "/rfqs",
    ),
    "EINVOICE_ISSUED": (
        lambda invoice: users_with_roles(invoice.buyer_company_id, "FINANCE")
        + users_with_roles(invoice.supplier_company_id, "SUPPLIER"),
        lambda invoice: f"Hóa đơn điện tử {invoice.number} đã được cấp mã cơ quan thuế (giả lập)",
        "/invoices",
    ),
    "PAYMENT_SUCCEEDED": (
        lambda invoice: users_with_roles(invoice.buyer_company_id, "FINANCE")
        + users_with_roles(invoice.supplier_company_id, "SUPPLIER"),
        lambda invoice: f"Thanh toán sandbox cho {invoice.number} thành công",
        "/invoices",
    ),
    "PAYMENT_FAILED": (
        lambda invoice: users_with_roles(invoice.buyer_company_id, "FINANCE")
        + users_with_roles(invoice.supplier_company_id, "SUPPLIER"),
        lambda invoice: f"Thanh toán sandbox cho {invoice.number} thất bại",
        "/invoices",
    ),
}


def notify_event(event_type, entity, actor=None):
    """Tạo Notification cho người nhận theo RULES; bỏ qua chính actor. Không đưa giá vào nội dung (FR-NOTI-05)."""
    recipients_of, title_of, path = RULES[event_type]
    seen = set()
    rows = []
    for user in recipients_of(entity):
        if user is None or user.id in seen or (actor is not None and user.id == actor.id):
            continue
        seen.add(user.id)
        rows.append(
            Notification(
                recipient=user,
                company_id=user.company_id,
                event_type=event_type,
                entity_type=entity._meta.label_lower,
                entity_id=entity.id,
                title=title_of(entity),
                payload={"number": getattr(entity, "number", ""), "status": getattr(entity, "status", ""), "path": path},
            )
        )
    Notification.objects.bulk_create(rows)
    return len(rows)
