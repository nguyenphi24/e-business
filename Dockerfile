# syntax=docker/dockerfile:1
# Một image duy nhất cho cả demo: nginx(:80) -> SPA tĩnh + ProcureHub API + sandbox-service + PostgreSQL nhúng.
#   docker build -t procurehub-demo .
#   docker run -d -p 8080:80 -v procurehub-data:/data -e PUBLIC_URL=https://demo.example.com procurehub-demo

# ---------- 1) build frontend (SPA gọi API cùng origin: /api/v1) ----------
FROM node:22-alpine AS fe
WORKDIR /fe
COPY procurehub/frontend/package.json procurehub/frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY procurehub/frontend/ ./
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ---------- 2) runtime ----------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive TZ=Asia/Ho_Chi_Minh

RUN apt-get update && apt-get install -y --no-install-recommends \
      postgresql nginx supervisor gosu openssl curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/lib/postgresql/*/bin /usr/local/pgbin \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /srv
COPY procurehub/backend/requirements.txt /tmp/ph-req.txt
COPY sandbox-service/backend/requirements/ /tmp/sb-req/
RUN pip install -r /tmp/ph-req.txt -r /tmp/sb-req/prod.txt

COPY procurehub/backend/ /srv/procurehub/
COPY sandbox-service/backend/ /srv/sandbox/
COPY --from=fe /fe/dist /usr/share/nginx/html

COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/supervisord.conf /etc/supervisor/conf.d/procurehub.conf
COPY deploy/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /data && chown app:app /data

VOLUME /data
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 CMD curl -fsS http://127.0.0.1/health/ | grep -q '"status": *"ok"' || exit 1
ENTRYPOINT ["/entrypoint.sh"]
