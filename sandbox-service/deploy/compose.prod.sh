#!/usr/bin/env bash
# Vỏ bọc `docker compose -f docker-compose.prod.yml`: nạp .env.registry +
# .env.prod rồi tính SANDBOX_SERVICE_IMAGE. Dùng cho vận hành hằng ngày
# (logs, ps, exec); việc deploy là của deploy.prod.sh.
#
#   ./compose.prod.sh ps
#   ./compose.prod.sh logs -f app
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# shellcheck disable=SC1091
source ./_env.sh

# Không có fallback ":latest" — xem ghi chú trong deploy.prod.sh.
: "${SANDBOX_SERVICE_IMAGE_TAG:?SANDBOX_SERVICE_IMAGE_TAG thiếu trong $APP_ENV_FILE}"
export SANDBOX_SERVICE_IMAGE="${IMAGE_BASE}:${SANDBOX_SERVICE_IMAGE_TAG}"

exec docker compose -f docker-compose.prod.yml "$@"
