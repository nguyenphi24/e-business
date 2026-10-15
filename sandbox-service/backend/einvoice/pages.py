from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from einvoice.models import EInvoice
from einvoice.services import build_xml, issue_if_due


@require_GET
def lookup(request):
	code = request.GET.get("code", "").strip().upper()
	einvoice = EInvoice.objects.filter(lookup_code=code).first() if code else None
	if einvoice:
		einvoice = issue_if_due(einvoice)
	return render(request, "einvoice/lookup.html", {"code": code, "einvoice": einvoice, "searched": bool(code)})


@require_GET
def xml(request, lookup_code):
	einvoice = issue_if_due(get_object_or_404(EInvoice, lookup_code=lookup_code.upper()))
	response = HttpResponse(build_xml(einvoice), content_type="application/xml; charset=utf-8")
	response["Content-Disposition"] = f'attachment; filename="{einvoice.symbol}-{einvoice.number:07d}.xml"'
	return response
