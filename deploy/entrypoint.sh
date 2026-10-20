#!/bin/bash
# Khởi động demo một-image: tạo secret (lần đầu), sinh cấu hình từ PUBLIC_URL, init PostgreSQL, migrate, seed, rồi chạy supervisord.
set -euo pipefail

PGBIN=/usr/local/pgbin
PUBLIC_URL="${PUBLIC_URL:-http://localhost:8080}"
PUBLIC_URL="${PUBLIC_URL%/}"
PUBLIC_HOST="${PUBLIC_URL#*://}"; PUBLIC_HOST="${PUBLIC_HOST%%/*}"; PUBLIC_HOSTNAME="${PUBLIC_HOST%%:*}"

mkdir -p /data && chown app:app /data

# --- secret: sinh một lần, lưu trong volume (có thể ghi đè bằng biến môi trường) ---
SECRETS=/data/secrets.env
if [ ! -s "$SECRETS" ]; then
  umask 077
  {
    echo "GEN_BACKEND_SECRET_KEY=$(openssl rand -hex 48)"
    echo "GEN_SANDBOX_SECRET_KEY=$(openssl rand -hex 48)"
    echo "GEN_SANDBOX_API_KEY=$(openssl rand -hex 32)"
    echo "GEN_WEBHOOK_SECRET=$(openssl rand -hex 32)"
    echo "GEN_DB_PASSWORD=$(openssl rand -hex 16)"
  } > "$SECRETS"
fi
. "$SECRETS"
DB_NAME=procurehub; DB_USER=procurehub; DB_PASS="${DATABASE_PASSWORD:-$GEN_DB_PASSWORD}"
API_KEY="${SANDBOX_API_KEY:-$GEN_SANDBOX_API_KEY}"
WEBHOOK="${SANDBOX_WEBHOOK_SECRET:-$GEN_WEBHOOK_SECRET}"

# --- cấu hình hai service (viết lại mỗi lần khởi động theo PUBLIC_URL hiện tại) ---
CORS_ORIGINS="${PUBLIC_URL},http://${PUBLIC_HOSTNAME},https://${PUBLIC_HOSTNAME},http://${PUBLIC_HOSTNAME}:8080,https://${PUBLIC_HOSTNAME}:8080"
RETURN_PREFIXES="${PUBLIC_URL}/,http://${PUBLIC_HOSTNAME}/,https://${PUBLIC_HOSTNAME}/,http://${PUBLIC_HOSTNAME}:8080/,https://${PUBLIC_HOSTNAME}:8080/"
umask 077
cat > /data/backend.env <<EOF
SECRET_KEY=${SECRET_KEY:-$GEN_BACKEND_SECRET_KEY}
DEBUG=false
ALLOWED_HOSTS=${PUBLIC_HOSTNAME},localhost,127.0.0.1,*
CORS_ALLOWED_ORIGINS=${CORS_ORIGINS}
USE_SQLITE=false
DATABASE_NAME=${DB_NAME}
DATABASE_USER=${DB_USER}
DATABASE_PASSWORD=${DB_PASS}
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432
SANDBOX_BASE_URL=http://127.0.0.1:8000
SANDBOX_API_KEY=${API_KEY}
SANDBOX_WEBHOOK_SECRET=${WEBHOOK}
CALLBACK_BASE_URL=http://127.0.0.1:8080
FRONTEND_URL=${PUBLIC_URL}
PAYMENT_SANDBOX_ENABLED=${PAYMENT_SANDBOX_ENABLED:-true}
NOTIFICATION_STREAM_MAX_SECONDS=${NOTIFICATION_STREAM_MAX_SECONDS:-25}
EOF
cat > /data/sandbox.env <<EOF
SECRET_KEY=${GEN_SANDBOX_SECRET_KEY}
DEBUG=false
ALLOWED_HOSTS=${PUBLIC_HOSTNAME},localhost,127.0.0.1,*
CSRF_TRUSTED_ORIGINS=${CORS_ORIGINS}
SANDBOX_API_KEY=${API_KEY}
SANDBOX_WEBHOOK_SECRET=${WEBHOOK}
PUBLIC_BASE_URL=${PUBLIC_URL}
ALLOWED_CALLBACK_PREFIXES=http://127.0.0.1:8080/
ALLOWED_RETURN_PREFIXES=${RETURN_PREFIXES}
DATABASE_PATH=/data/sandbox_service.db
EINVOICE_TAX_DELAY_SECONDS=${EINVOICE_TAX_DELAY_SECONDS:-3}
EOF
chown app:app /data/backend.env /data/sandbox.env

# --- PostgreSQL nhúng ---
if [ ! -s /data/pg/PG_VERSION ]; then
  echo "[init] tạo cluster PostgreSQL mới"
  chown postgres:postgres /data
  gosu postgres "$PGBIN/initdb" -D /data/pg -E UTF8 --auth=trust >/dev/null
  chown app:app /data
fi
chown -R postgres:postgres /data/pg
gosu postgres "$PGBIN/pg_ctl" -D /data/pg -o "-c listen_addresses=127.0.0.1" -w start >/dev/null
gosu postgres psql -Atc "select 1 from pg_roles where rolname='$DB_USER'" | grep -q 1 \
  && gosu postgres psql -qc "alter role \"$DB_USER\" password '$DB_PASS'" \
  || gosu postgres psql -qc "create role \"$DB_USER\" login password '$DB_PASS'"
gosu postgres psql -Atc "select 1 from pg_database where datname='$DB_NAME'" | grep -q 1 \
  || gosu postgres psql -qc "create database \"$DB_NAME\" owner \"$DB_USER\""

# --- migrate + seed ---
run_backend() { gosu app bash -c "set -a; . /data/backend.env; set +a; cd /srv/procurehub && $*"; }
run_sandbox() { gosu app bash -c "set -a; . /data/sandbox.env; set +a; cd /srv/sandbox && $*"; }

run_backend python manage.py migrate --noinput -v0
run_sandbox python manage.py migrate --noinput -v0
if [ "${RESET_DATA:-0}" = "1" ]; then
  run_backend python manage.py seed_demo --reset
  run_sandbox python manage.py seed_sandbox --reset
else
  run_backend python manage.py seed_demo || echo "[init] dữ liệu demo đã có, giữ nguyên (RESET_DATA=1 để nạp lại)"
  run_sandbox python manage.py seed_sandbox
fi

gosu postgres "$PGBIN/pg_ctl" -D /data/pg -m fast -w stop >/dev/null
echo "[init] sẵn sàng — PUBLIC_URL=${PUBLIC_URL}"
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
