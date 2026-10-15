import uuid

from django.db import transaction as db_transaction
from django.utils import timezone

from core.callbacks import deliver
from gateway.models import Transaction

OUTCOMES = {
	"pay": (Transaction.Status.SUCCEEDED, "SUCCEEDED", ""),
	"fail": (Transaction.Status.FAILED, "FAILED", "Ngân hàng từ chối giao dịch (giả lập)."),
	"cancel": (Transaction.Status.CANCELLED, "FAILED", "Người dùng hủy thanh toán."),
}


def complete(transaction, action, bank_code=""):
	"""Chốt kết quả giao dịch rồi gửi IPN. Giao dịch đã chốt thì giữ nguyên (trả về False)."""
	status, event_status, reason = OUTCOMES[action]
	with db_transaction.atomic():
		locked = Transaction.objects.select_for_update().get(pk=transaction.pk)
		if locked.status != Transaction.Status.PENDING:
			return False
		locked.status = status
		locked.bank_code = bank_code[:20]
		locked.completed_at = timezone.now()
		locked.last_event = {
			"event_id": f"evt_{uuid.uuid4().hex}",
			"external_ref": locked.merchant_ref,
			"transaction_id": str(locked.id),
			"status": event_status,
			"amount": str(locked.amount),
			"failure_reason": reason,
		}
		locked.save(update_fields=["status", "bank_code", "completed_at", "last_event"])
	transaction.refresh_from_db()
	deliver("payment", transaction.id, transaction.ipn_url, transaction.last_event)
	return True


def resend_ipn(transaction):
	"""Gửi lại đúng sự kiện cũ (cùng event_id) — dùng để demo merchant xử lý idempotent."""
	if not transaction.last_event:
		return None
	return deliver("payment", transaction.id, transaction.ipn_url, transaction.last_event)
