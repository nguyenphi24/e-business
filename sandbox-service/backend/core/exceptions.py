from rest_framework import exceptions
from rest_framework.views import exception_handler

from core.responses import error_response


def custom_exception_handler(exc, context):
	"""MỘT chỗ duy nhất map exception sang response — thêm loại lỗi mới chỉ
	cần thêm một case ở đây, không rải try/except tự build response ở
	từng view."""
	response = exception_handler(exc, context)

	if response is None:
		return error_response(code="SERVER_ERROR", message=str(exc), status=500)

	# Lỗi auth/permission đã đúng shape DRF chuẩn, không bọc lại.
	if isinstance(exc, (exceptions.AuthenticationFailed, exceptions.NotAuthenticated, exceptions.PermissionDenied)):
		return response

	# ValidationError: str(exc) là repr Python của dict lỗi — trả câu ngắn, chi tiết nằm ở `details`.
	message = "Request validation failed." if isinstance(exc, exceptions.ValidationError) else str(exc)
	return error_response(
		code=exc.__class__.__name__,
		message=message,
		details=response.data,
		status=response.status_code,
	)
