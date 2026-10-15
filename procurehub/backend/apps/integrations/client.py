"""Adapter gọi sandbox-service. Đổi sang nhà cung cấp thật thì thay lớp này, không đụng nghiệp vụ."""
import json
import urllib.error
import urllib.request

from django.conf import settings


class IntegrationError(Exception):
    pass


def is_enabled():
    return bool(settings.SANDBOX_BASE_URL)


def callback_url(path):
    return f"{settings.CALLBACK_BASE_URL}{path}"


class SandboxClient:
    def _request(self, method, path, payload=None):
        if not is_enabled():
            raise IntegrationError("Sandbox integration is not configured.")
        data = json.dumps(payload, default=str).encode() if payload is not None else None
        request = urllib.request.Request(
            f"{settings.SANDBOX_BASE_URL}{path}", data=data, method=method,
            headers={"Content-Type": "application/json", "X-Api-Key": settings.SANDBOX_API_KEY},
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.SANDBOX_TIMEOUT_SECONDS) as response:
                body = json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            try:
                error = json.loads(exc.read() or b"{}").get("error", {})
            except ValueError:
                error = {}
            raise IntegrationError(f"Sandbox HTTP {exc.code}: {error.get('message', exc.reason)}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise IntegrationError(f"Cannot reach sandbox: {getattr(exc, 'reason', exc)}") from exc
        if not body.get("success"):
            raise IntegrationError(str(body.get("error", "Unexpected sandbox response.")))
        return body["data"]

    def create_payment(self, merchant_ref, amount, description, return_url, ipn_url):
        return self._request("POST", "/api/v1/gateway/transactions", {
            "merchant_ref": merchant_ref, "amount": str(amount), "description": description,
            "return_url": return_url, "ipn_url": ipn_url,
        })

    def create_einvoice(self, payload):
        return self._request("POST", "/api/v1/einvoices", payload)

    def get_einvoice(self, einvoice_id):
        return self._request("GET", f"/api/v1/einvoices/{einvoice_id}")

    def create_sign_request(self, external_ref, signer, document_hash, document_label, callback):
        return self._request("POST", "/api/v1/esign/requests", {
            "external_ref": external_ref, "signer": signer, "document_hash": document_hash,
            "document_label": document_label, "callback_url": callback,
        })

    def get_certificate_authority(self):
        return self._request("GET", "/api/v1/esign/ca")
