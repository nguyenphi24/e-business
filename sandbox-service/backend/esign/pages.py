from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from esign.models import SignRequest
from esign.services import submit


@require_http_methods(["GET", "POST"])
def sign_page(request, pk):
	sign_request = get_object_or_404(SignRequest, pk=pk)
	error = ""
	if request.method == "POST":
		sign_request, error = submit(sign_request.pk, request.POST.get("action", ""), request.POST.get("otp", ""))
	return render(request, "esign/sign.html", {"sign_request": sign_request, "error": error})
