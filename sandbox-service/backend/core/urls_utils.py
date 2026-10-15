from urllib.parse import urlencode, urlsplit, urlunsplit

from django.conf import settings


def public_url(path):
	return f"{settings.PUBLIC_BASE_URL}{path}"


def with_query(url, params):
	parts = urlsplit(url)
	query = f"{parts.query}&{urlencode(params)}" if parts.query else urlencode(params)
	return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
