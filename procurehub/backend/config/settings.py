import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "apps.identity",
    "apps.suppliers",
    "apps.procurement",
    "apps.purchase_orders",
    "apps.audit",
    "apps.notifications",
    "apps.billing",
    "apps.integrations",
]

MIDDLEWARE = [
    "common.middleware.RequestIdMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL là mặc định; USE_SQLITE=true chỉ để chạy thử nhanh khi chưa có Docker.
if os.getenv("USE_SQLITE", "false").lower() in {"1", "true", "yes"}:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DATABASE_NAME"],
            "USER": os.environ["DATABASE_USER"],
            "PASSWORD": os.environ["DATABASE_PASSWORD"],
            "HOST": os.environ["DATABASE_HOST"],
            "PORT": os.environ["DATABASE_PORT"],
        }
    }

AUTH_USER_MODEL = "identity.User"
AUTH_PASSWORD_VALIDATORS = []  # mật khẩu demo; bật lại khi dùng ngoài demo

LANGUAGE_CODE = "vi"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

SPECTACULAR_SETTINGS = {"TITLE": "ProcureHub API", "VERSION": "0.1.0"}

# Refresh cookie (D-08)
REFRESH_COOKIE_NAME = "ph_refresh"
REFRESH_COOKIE_SECURE = not DEBUG
REFRESH_COOKIE_SAMESITE = "Lax"

CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:43000").split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ["X-Request-ID"]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# Thông báo realtime (SSE): mỗi kết nối tự đóng sau tối đa N giây để không giữ thread gunicorn; client tự nối lại.
NOTIFICATION_STREAM_MAX_SECONDS = int(os.getenv("NOTIFICATION_STREAM_MAX_SECONDS", "25"))
NOTIFICATION_STREAM_POLL_SECONDS = float(os.getenv("NOTIFICATION_STREAM_POLL_SECONDS", "2"))

# Mọi callback từ sandbox-service (cổng thanh toán, hóa đơn điện tử, ký số) ký HMAC bằng secret này — bắt buộc.
SANDBOX_WEBHOOK_SECRET = os.environ["SANDBOX_WEBHOOK_SECRET"]
# Nút "mô phỏng kết quả" nội bộ (không qua cổng) chỉ bật khi PAYMENT_SANDBOX_ENABLED=true.
PAYMENT_SANDBOX_ENABLED = os.getenv("PAYMENT_SANDBOX_ENABLED", "false").lower() == "true"

# Tích hợp sandbox-service. Để trống SANDBOX_BASE_URL thì tắt tích hợp (thanh toán dùng nút mô phỏng,
# không phát hành hóa đơn điện tử, không ký số). Đã bật thì SANDBOX_API_KEY là bắt buộc.
SANDBOX_BASE_URL = os.getenv("SANDBOX_BASE_URL", "").rstrip("/")
SANDBOX_API_KEY = os.environ["SANDBOX_API_KEY"] if SANDBOX_BASE_URL else ""
if SANDBOX_BASE_URL and not SANDBOX_API_KEY:
    raise ImproperlyConfigured("SANDBOX_API_KEY is required when SANDBOX_BASE_URL is set.")
SANDBOX_TIMEOUT_SECONDS = float(os.getenv("SANDBOX_TIMEOUT_SECONDS") or "5")
# Địa chỉ sandbox dùng để gọi ngược về API này, và địa chỉ SPA để cổng thanh toán đưa người dùng quay lại.
# Dùng `or` vì docker compose truyền chuỗi rỗng khi biến không được đặt.
CALLBACK_BASE_URL = (os.getenv("CALLBACK_BASE_URL") or "http://127.0.0.1:48000").rstrip("/")
FRONTEND_URL = (os.getenv("FRONTEND_URL") or "http://localhost:43000").rstrip("/")
