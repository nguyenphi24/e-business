bind = "0.0.0.0:8000"

workers = 4
worker_class = "gthread"
threads = 2

timeout = 30
graceful_timeout = 15
keepalive = 2

max_requests = 1500
max_requests_jitter = 200

preload_app = False
worker_tmp_dir = "/dev/shm"


# Access log tắt ở đây (None) — gunicorn ghi nguyên request line kèm query
# string, không tự che field nhạy cảm (token, password...) được. Access
# log thật do core.middleware.RequestLoggingMiddleware đảm nhiệm (che field
# nhạy cảm trước khi ra log, giống hệt cả dev lẫn production) — xem
# repo conventions/stacks/django.md mục "Logging".
accesslog = None
errorlog = "-"
loglevel = "info"
