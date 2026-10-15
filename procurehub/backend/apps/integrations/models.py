from django.db import models


class TrustAnchor(models.Model):
    """Khóa công khai CA được ghim lần đầu lấy từ sandbox; sau đó xác minh chữ ký không cần gọi mạng."""

    name = models.CharField(max_length=50, unique=True)
    issuer = models.CharField(max_length=255)
    public_key = models.CharField(max_length=64)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "trust_anchors"
