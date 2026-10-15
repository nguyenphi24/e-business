from rest_framework.response import Response


def success_response(data=None, meta=None, status=200):
	payload = {"success": True, "data": data}
	if meta is not None:
		payload["meta"] = meta
	return Response(payload, status=status)


def error_response(code, message, details=None, status=400):
	payload = {"success": False, "error": {"code": code, "message": message}}
	if details:
		payload["error"]["details"] = details
	return Response(payload, status=status)
