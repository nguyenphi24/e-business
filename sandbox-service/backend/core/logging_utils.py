"""Che field nhạy cảm trước khi ra log — dùng cho access log
(RequestLoggingMiddleware) và bất kỳ chỗ nào tự log query string/header.
Xem repo conventions/stacks/django.md mục "Logging"."""

MASK = "***"

# So khớp không phân biệt hoa/thường, dạng "chứa" (contains) — tên field
# thực tế hay có biến thể (apiKey/api_key/api-key, cardNumber/card_number).
# Mở rộng danh sách này khi dự án có field nhạy cảm riêng (OTP, số tài
# khoản ngân hàng...), đừng chỉ dựa bộ mặc định nếu domain cần thêm.
SENSITIVE_KEYWORDS = (
	"password", "token", "secret", "apikey", "api_key", "api-key",
	"authorization", "cookie", "creditcard", "card_number", "cardnumber", "ssn",
)


def _is_sensitive_key(key: str) -> bool:
	normalized = key.lower()
	return any(keyword in normalized for keyword in SENSITIVE_KEYWORDS)


def mask_query_string(query: str) -> str:
	"""Che value của key nhạy cảm trong query string, giữ nguyên key khác."""
	if not query:
		return query
	parts = []
	for pair in query.split("&"):
		key, sep, _value = pair.partition("=")
		parts.append(f"{key}={MASK}" if sep and _is_sensitive_key(key) else pair)
	return "&".join(parts)


def mask_header_value(name: str, value: str) -> str:
	"""Che giá trị header nếu tên header nằm trong danh sách nhạy cảm (Authorization, Cookie...)."""
	return MASK if _is_sensitive_key(name) else value
