bind = "0.0.0.0:8080"

workers = 2
worker_class = "gthread"
threads = 8  # SSE giữ thread tối đa NOTIFICATION_STREAM_MAX_SECONDS mỗi kết nối
timeout = 30
graceful_timeout = 15
keepalive = 2
max_requests = 1500
max_requests_jitter = 200
preload_app = False
worker_tmp_dir = "/dev/shm"
accesslog = None
errorlog = "-"
loglevel = "info"
