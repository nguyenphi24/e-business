#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
POSTGRES_PORT="${POSTGRES_PORT:-45432}"
PYTHON_BIN="${PYTHON_BIN:-$BACKEND_DIR/.venv311/bin/python}"

command -v docker >/dev/null 2>&1 || { printf 'Docker CLI is required.\n' >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { printf 'OpenSSL is required.\n' >&2; exit 1; }
[[ -x "$PYTHON_BIN" ]] || { printf 'Python venv not found: %s\n' "$PYTHON_BIN" >&2; exit 1; }

export SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 48)}"
export SANDBOX_WEBHOOK_SECRET="${SANDBOX_WEBHOOK_SECRET:-$(openssl rand -hex 32)}"
export DEBUG="${DEBUG:-false}"
export ALLOWED_HOSTS="${ALLOWED_HOSTS:-localhost,127.0.0.1}"
export DATABASE_NAME="${DATABASE_NAME:-procurehub}"
export DATABASE_USER="${DATABASE_USER:-procurehub}"
export DATABASE_PASSWORD="${DATABASE_PASSWORD:-procurehub}"
export DATABASE_HOST="${DATABASE_HOST:-localhost}"
export DATABASE_PORT="$POSTGRES_PORT"

printf 'Starting PostgreSQL on port %s...\n' "$POSTGRES_PORT"
POSTGRES_PORT="$POSTGRES_PORT" docker compose -f "$ROOT_DIR/docker-compose.yml" up -d --wait

printf 'Applying migrations...\n'
(cd "$BACKEND_DIR" && POSTGRES_PORT="$POSTGRES_PORT" "$PYTHON_BIN" manage.py migrate --noinput)

printf 'Seeding demo data...\n'
(cd "$BACKEND_DIR" && POSTGRES_PORT="$POSTGRES_PORT" "$PYTHON_BIN" manage.py seed_demo --reset)

printf 'Running checks and tests on PostgreSQL...\n'
(cd "$BACKEND_DIR" && POSTGRES_PORT="$POSTGRES_PORT" "$PYTHON_BIN" manage.py check && POSTGRES_PORT="$POSTGRES_PORT" "$PYTHON_BIN" manage.py test)

printf 'PostgreSQL acceptance passed.\n'
