# Dùng chung bởi mọi script trong deploy/ (compose.*.sh, deploy.prod.sh):
# nạp .env.registry + .env.prod, validate hai biến registry cơ bản, tính
# sẵn IMAGE_BASE. `source` file này — KHÔNG tự chạy được, và không tự cd,
# script gọi nó phải cd vào deploy/ trước (mỗi script đã làm vậy).
#
# Không dùng "set -euo pipefail" ở đây: kế thừa từ script gọi (mỗi script
# đó đã tự bật), lặp lại vô hại nhưng thừa.

REGISTRY_ENV_FILE="${REGISTRY_ENV_FILE:-.env.registry}"
APP_ENV_FILE="${APP_ENV_FILE:-.env.prod}"

for f in "$REGISTRY_ENV_FILE" "$APP_ENV_FILE"; do
	[[ -f "$f" ]] || { echo "Thiếu $f — copy ${f}.example sang $f rồi điền." >&2; exit 1; }
done

set -a
# shellcheck disable=SC1090,SC1091
source "$REGISTRY_ENV_FILE"
# shellcheck disable=SC1090,SC1091
source "$APP_ENV_FILE"
set +a

: "${REGISTRY_HOST:?REGISTRY_HOST thiếu trong $REGISTRY_ENV_FILE}"
: "${PROJECT_PATH:?PROJECT_PATH thiếu trong $REGISTRY_ENV_FILE}"
IMAGE_BASE="${REGISTRY_HOST}/${PROJECT_PATH}"
