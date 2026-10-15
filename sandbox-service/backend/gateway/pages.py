from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from core.urls_utils import with_query
from gateway.models import Transaction
from gateway.services import OUTCOMES, complete

BANKS = [("VCB", "Vietcombank"), ("TCB", "Techcombank"), ("BIDV", "BIDV"), ("MB", "MB Bank"), ("QR", "Quét mã QR")]


@require_http_methods(["GET", "POST"])
def checkout(request, pk):
	transaction = get_object_or_404(Transaction, pk=pk)
	if request.method == "POST" and transaction.status == Transaction.Status.PENDING:
		action = request.POST.get("action")
		if action in OUTCOMES:
			complete(transaction, action, request.POST.get("bank", ""))
			transaction.refresh_from_db()
			return redirect(with_query(transaction.return_url, {"payment_ref": transaction.merchant_ref, "status": transaction.status}))
	return render(request, "gateway/checkout.html", {"transaction": transaction, "banks": BANKS})
