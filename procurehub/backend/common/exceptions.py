from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(exceptions.APIException):
    status_code = 409
    default_code = "business_error"

    def __init__(self, code, message, status_code=409, field_errors=None):
        self.status_code = status_code
        self.detail = {
            "code": code,
            "message": message,
            "field_errors": field_errors or {},
        }


def _as_field_errors(detail):
    if isinstance(detail, dict):
        return {str(key): value for key, value in detail.items()}
    if isinstance(detail, list):
        return {"non_field_errors": detail}
    return {"non_field_errors": [detail]}


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, DomainError):
        return response

    if isinstance(exc, exceptions.ValidationError):
        response.status_code = 422
        response.data = {
            "code": "validation_error",
            "message": "Request validation failed.",
            "field_errors": _as_field_errors(response.data),
        }
    elif isinstance(exc, exceptions.NotFound):
        response.data = {
            "code": "not_found",
            "message": "The requested resource was not found.",
            "field_errors": {},
        }
    elif isinstance(exc, exceptions.PermissionDenied):
        response.data = {
            "code": "permission_denied",
            "message": "You do not have permission to perform this action.",
            "field_errors": {},
        }
    elif isinstance(exc, exceptions.NotAuthenticated):
        response.data = {
            "code": "authentication_required",
            "message": "Authentication credentials were not provided.",
            "field_errors": {},
        }
    return response
