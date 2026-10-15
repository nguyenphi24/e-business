# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	TZ=Asia/Ho_Chi_Minh

RUN apt-get update \
	&& apt-get install -y --no-install-recommends build-essential libpq-dev curl \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements trước source để cache layer dependency — sửa code
# không phải cài lại package mỗi lần build.
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir -r requirements/prod.txt

COPY . .

# build.sh set từ `git rev-parse --short HEAD` — soi được image đang chạy
# đúng commit nào: docker inspect <image> --format
# '{{index .Config.Labels "org.opencontainers.image.revision"}}'
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.revision="${GIT_SHA}"

# /data là nơi đặt file SQLite trên volume production (DATABASE_PATH=/data/...). Tạo sẵn và
# giao cho user app để named volume mới tạo kế thừa quyền ghi — thiếu bước này app chết vì
# PermissionError khi tạo file database.
# UID cố định (không phải giá trị mặc định của groupadd/useradd) để chown
# bind mount trên host là xác định qua các lần rebuild — xem
# repo conventions/standard/deploy.md mục "Volume production".
RUN groupadd --gid 10001 app \
	&& useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app \
	&& mkdir -p /app/staticfiles /app/media /data \
	&& chown -R app:app /app /data

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
	CMD curl -sf http://localhost:8000/health/ | grep -q '"status": *"ok"' || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "config.wsgi:application"]
