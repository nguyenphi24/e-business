from django.db import models


class CallbackLog(models.Model):
	"""Mỗi lần sandbox gọi ngược về merchant (IPN thanh toán, kết quả cấp mã hóa đơn, kết quả ký)."""

	kind = models.CharField(max_length=30)
	object_id = models.CharField(max_length=64)
	url = models.URLField(max_length=500)
	event_id = models.CharField(max_length=100)
	status_code = models.PositiveIntegerField(null=True, blank=True)
	error = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "callback_logs"
		indexes = [models.Index(fields=["kind", "object_id"])]
