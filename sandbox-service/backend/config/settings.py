import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# File .env ở ROOT repo (../.env từ backend/), xem
# repo conventions/standard/repo-layout.md mục ".env cục bộ".
# override=False (mặc định) + không set biến tay thì production (không có
# .env, biến thật do deploy/docker-compose.prod.yml bơm qua environment)
# vẫn chạy bình thường — load_dotenv trên file không tồn tại là no-op.
load_dotenv(BASE_DIR.parent / ".env")

# Secret bắt buộc — KHÔNG đặt default. os.environ[...] (không phải
# .get()) ném KeyError ngay lúc import settings, tức là app chết lúc khởi
# động khi thiếu, không chạy bằng khoá yếu mà không ai biết. Xem
# repo conventions/standard/deploy.md mục "Bí mật".
SECRET_KEY = os.environ["SECRET_KEY"]

# So sánh tường minh với "true"/"false" — KHÔNG dùng kiểu
# `os.getenv("DEBUG", "0") == "0"` (giá trị mặc định khi thiếu biến sẽ là
# DEBUG=True, và set DEBUG=1 lại tắt debug — ngược trực giác, dễ để lọt
# DEBUG=True lên production mà không ai phát hiện). Mặc định false: thiếu
# biến thì an toàn, không phải hướng ngược lại.
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost").split(",") if h.strip()]

INSTALLED_APPS = [
	"django.contrib.admin",
	"django.contrib.auth",
	"django.contrib.contenttypes",
	"django.contrib.sessions",
	"django.contrib.messages",
	"django.contrib.staticfiles",
	"rest_framework",
	# Metric HTTP (latency histogram + request count theo status) qua
	# /metrics — xem repo conventions/stacks/django.md mục "Metrics".
	"django_prometheus",
	"core",
	"gateway",
	"einvoice",
	"esign",
]

MIDDLEWARE = [
	# PrometheusBeforeMiddleware phải là middleware ĐẦU TIÊN (đo trọn thời
	# gian xử lý, giống lý do RequestLoggingMiddleware ở ngay dưới đặt sớm),
	# PrometheusAfterMiddleware phải là middleware CUỐI CÙNG trong danh sách
	# này — yêu cầu của chính django-prometheus, xem
	# repo conventions/stacks/django.md mục "Metrics".
	"django_prometheus.middleware.PrometheusBeforeMiddleware",
	# Đặt sớm để đo gần trọn thời gian xử lý (mọi middleware/view khác chạy
	# bên trong get_response) — xem core/middleware.py và
	# repo conventions/stacks/django.md mục "Logging".
	"core.middleware.RequestLoggingMiddleware",
	"django.middleware.security.SecurityMiddleware",
	"django.contrib.sessions.middleware.SessionMiddleware",
	"django.middleware.common.CommonMiddleware",
	"django.middleware.csrf.CsrfViewMiddleware",
	"django.contrib.auth.middleware.AuthenticationMiddleware",
	"django.contrib.messages.middleware.MessageMiddleware",
	"django.middleware.clickjacking.XFrameOptionsMiddleware",
	"django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
	{
		"BACKEND": "django.template.backends.django.DjangoTemplates",
		"DIRS": [],
		"APP_DIRS": True,
		"OPTIONS": {
			"context_processors": [
				"django.template.context_processors.debug",
				"django.template.context_processors.request",
				"django.contrib.auth.context_processors.auth",
				"django.contrib.messages.context_processors.messages",
			],
		},
	},
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite nhúng: DATABASE_PATH tương đối thì tính từ ROOT repo (cùng chỗ với .env).
_database_path = Path(os.getenv("DATABASE_PATH") or "./data/sandbox_service.db")
if not _database_path.is_absolute():
	_database_path = BASE_DIR.parent / _database_path
_database_path.parent.mkdir(parents=True, exist_ok=True)
DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.sqlite3",
		"NAME": _database_path,
		# Timer cấp mã hóa đơn chạy ở thread khác; chờ khóa ghi thay vì lỗi "database is locked".
		"OPTIONS": {"timeout": 20},
	}
}

AUTH_PASSWORD_VALIDATORS = [
	{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
	{"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
	{"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
	{"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "vi"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Merchant (ProcureHub) gọi API bằng header X-Api-Key; mọi callback gửi ngược lại được ký
# HMAC-SHA256 bằng SANDBOX_WEBHOOK_SECRET. Cả hai bắt buộc, không có default.
SANDBOX_API_KEY = os.environ["SANDBOX_API_KEY"]
SANDBOX_WEBHOOK_SECRET = os.environ["SANDBOX_WEBHOOK_SECRET"]

# Chỉ gửi callback tới URL bắt đầu bằng một trong các tiền tố này (chặn dùng sandbox để gọi
# địa chỉ tùy ý).
ALLOWED_CALLBACK_PREFIXES = [
	p.strip() for p in (os.getenv("ALLOWED_CALLBACK_PREFIXES") or "http://127.0.0.1:48000/,http://localhost:48000/").split(",") if p.strip()
]
# Sau khi thanh toán, trình duyệt chỉ được chuyển về các địa chỉ này (chặn open redirect).
ALLOWED_RETURN_PREFIXES = [
	p.strip() for p in (os.getenv("ALLOWED_RETURN_PREFIXES") or "http://localhost:43000/,http://127.0.0.1:43000/").split(",") if p.strip()
]
# URL công khai của chính sandbox, dùng để sinh link trang thanh toán / ký / tra cứu.
# Dùng `or` vì docker compose truyền chuỗi rỗng khi biến không được đặt.
PUBLIC_BASE_URL = (os.getenv("PUBLIC_BASE_URL") or "http://localhost:28080").rstrip("/")
# Thời gian "cơ quan thuế" cấp mã hóa đơn (giây). 0 = cấp ngay trong request.
EINVOICE_TAX_DELAY_SECONDS = float(os.getenv("EINVOICE_TAX_DELAY_SECONDS") or "3")
CALLBACK_TIMEOUT_SECONDS = float(os.getenv("CALLBACK_TIMEOUT_SECONDS") or "5")

REST_FRAMEWORK = {
	# Không dùng session/basic auth: API chỉ xác thực bằng X-Api-Key (core.auth.HasMerchantApiKey).
	"DEFAULT_AUTHENTICATION_CLASSES": [],
	"UNAUTHENTICATED_USER": None,
	"DEFAULT_PAGINATION_CLASS": "core.pagination.MetaPageNumberPagination",
	"PAGE_SIZE": 50,
	"DEFAULT_RENDERER_CLASSES": ("core.renderers.CustomRenderer",),
	"EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# logging.file để trống — dev/`manage.py runserver` chỉ log console.
# Production nên set biến trỏ path trên bind mount (xem
# deploy/docker-compose.prod.yml) để log sống sót qua redeploy/restart,
# thêm khi thật sự cần, đừng bật sẵn "cho chắc".
LOGGING = {
	"version": 1,
	"disable_existing_loggers": False,
	"formatters": {
		"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
	},
	"handlers": {
		"console": {"class": "logging.StreamHandler", "formatter": "simple"},
	},
	"root": {
		"handlers": ["console"],
		"level": "INFO",
	},
	"loggers": {
		# manage.py runserver tự in request line THÔ (không qua
		# mask_query_string) ra console qua logger này — production dùng
		# gunicorn nên không đụng logger này, nhưng dev vẫn là một đường rò
		# rỉ field nhạy cảm song song với access log đã mask của
		# core.middleware.RequestLoggingMiddleware. Tắt hẳn (handlers rỗng +
		# propagate False) để chỉ còn đúng một dòng log — bản đã mask. Xem
		# repo conventions/stacks/django.md mục "Logging".
		"django.server": {"handlers": [], "propagate": False},
	},
}
