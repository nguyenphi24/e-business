from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class MetaPageNumberPagination(PageNumberPagination):
	page_size = settings.REST_FRAMEWORK.get("PAGE_SIZE", 50)
	page_size_query_param = "page_size"
	page_query_param = "page"

	def get_paginated_response(self, data):
		return Response(
			{
				"success": True,
				"data": data,
				"meta": {
					"page": self.page.number,
					"page_size": self.get_page_size(self.request),
					"count": self.page.paginator.count,
					"next": self.get_next_link(),
					"previous": self.get_previous_link(),
				},
			}
		)
