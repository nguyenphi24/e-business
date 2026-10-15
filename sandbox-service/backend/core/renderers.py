from rest_framework.renderers import JSONRenderer


class CustomRenderer(JSONRenderer):
	"""Envelope chuẩn cho MỌI response REST — `{success, data}` hay
	`{success: false, error: {...}}`. MỘT chỗ duy nhất quyết định shape,
	view không tự build response tay."""

	def render(self, data, accepted_media_type=None, renderer_context=None):
		response = renderer_context.get("response") if renderer_context else None

		# Response đã tự format sẵn (success_response/error_response, hoặc
		# MetaPageNumberPagination) — giữ nguyên, không bọc thêm lần nữa.
		if isinstance(data, dict) and "success" in data:
			return super().render(data, accepted_media_type, renderer_context)

		if response is not None and response.status_code >= 400:
			return super().render({"success": False, "error": data}, accepted_media_type, renderer_context)

		return super().render({"success": True, "data": data}, accepted_media_type, renderer_context)
