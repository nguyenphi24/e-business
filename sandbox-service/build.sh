#!/usr/bin/env bash
# Build image production cho linux/amd64 (chạy được trên host x86 kể cả khi
# build từ Mac Apple Silicon) rồi push lên registry.
#
# Image:
#   ${PROJECT_PATH}            backend  (backend/Dockerfile)
#   ${PROJECT_PATH}-frontend   frontend (frontend/Dockerfile) — chỉ build khi
#                              thư mục frontend/ đã tồn tại
#   ${PROJECT_PATH}-admin      admin    (admin/Dockerfile) — chỉ build khi
#                              thư mục admin/ đã tồn tại
#
# Dùng:
#   ./build.sh                     # tag theo git short SHA + latest
#   IMAGE_TAG=v1.2.3 ./build.sh    # tag thêm nhãn tường minh
#
# Đọc REGISTRY_* / PROJECT_PATH từ .env.registry (cùng thư mục với script này;
# mẫu ở deploy/.env.registry.example) trừ khi đã export sẵn trong môi trường.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

ENV_FILE="${REGISTRY_ENV_FILE:-.env.registry}"
if [[ -f "$ENV_FILE" ]]; then
	set -a
	# shellcheck disable=SC1090
	source "$ENV_FILE"
	set +a
elif [[ -z "${REGISTRY_HOST:-}" ]]; then
	echo "Thiếu $ENV_FILE và cũng không có biến REGISTRY_*/PROJECT_PATH trong môi trường." >&2
	echo "Copy deploy/.env.registry.example sang $ENV_FILE rồi điền giá trị thật." >&2
	exit 1
fi

: "${REGISTRY_HOST:?REGISTRY_HOST bắt buộc}"
: "${PROJECT_PATH:?PROJECT_PATH bắt buộc, dạng <namespace>/<repo>}"
: "${REGISTRY_USER:?REGISTRY_USER bắt buộc}"
: "${REGISTRY_PASS:?REGISTRY_PASS bắt buộc}"

if ! command -v git >/dev/null 2>&1 || ! git rev-parse --short HEAD >/dev/null 2>&1; then
	echo "Cần git để lấy tag mặc định (thư mục này không phải git checkout?)." >&2
	exit 1
fi
if [[ -n "$(git status --porcelain)" ]]; then
	echo "!! Working tree còn thay đổi chưa commit — nhãn revision của image sẽ" >&2
	echo "!! không khớp với thứ đang thật sự chạy. Commit hoặc stash trước." >&2
	if [[ -t 0 ]]; then
		read -r -p "Vẫn tiếp tục? [y/N] " confirm
		[[ "$confirm" =~ ^[Yy]$ ]] || exit 1
	else
		echo "!! Shell không tương tác (CI?) — từ chối build cây bẩn. Đặt ALLOW_DIRTY=1 để bỏ qua." >&2
		[[ "${ALLOW_DIRTY:-0}" == "1" ]] || exit 1
	fi
fi

GIT_SHA="$(git rev-parse --short HEAD)"
IMAGE_BASE="${REGISTRY_HOST}/${PROJECT_PATH}"
FRONTEND_IMAGE_BASE="${IMAGE_BASE}-frontend"
ADMIN_IMAGE_BASE="${IMAGE_BASE}-admin"
PLATFORM="${PLATFORM:-linux/amd64}"
BUILDER_NAME="sandbox-service-builder"

BUILD_FRONTEND=0
[[ -f frontend/Dockerfile ]] && BUILD_FRONTEND=1
BUILD_ADMIN=0
[[ -f admin/Dockerfile ]] && BUILD_ADMIN=1

echo "==> Image:    ${IMAGE_BASE}"
[[ "$BUILD_FRONTEND" -eq 1 ]] && echo "              ${FRONTEND_IMAGE_BASE}" \
	|| echo "              (bỏ qua frontend — chưa có frontend/Dockerfile)"
[[ "$BUILD_ADMIN" -eq 1 ]] && echo "              ${ADMIN_IMAGE_BASE}" \
	|| echo "              (bỏ qua admin — chưa có admin/Dockerfile)"
echo "==> Tag:      ${GIT_SHA}, latest${IMAGE_TAG:+, ${IMAGE_TAG}}"
echo "==> Platform: ${PLATFORM}"

echo "==> Đăng nhập ${REGISTRY_HOST}"
echo "${REGISTRY_PASS}" | docker login "${REGISTRY_HOST}" -u "${REGISTRY_USER}" --password-stdin

# buildx cho phép build chéo kiến trúc (QEMU) — chậm hơn native nhưng không
# cần cài thêm gì ngoài Docker Desktop.
if ! docker buildx inspect "$BUILDER_NAME" >/dev/null 2>&1; then
	docker buildx create --name "$BUILDER_NAME" --use
else
	docker buildx use "$BUILDER_NAME"
fi

TAG_ARGS=(-t "${IMAGE_BASE}:${GIT_SHA}" -t "${IMAGE_BASE}:latest")
FRONTEND_TAG_ARGS=(-t "${FRONTEND_IMAGE_BASE}:${GIT_SHA}" -t "${FRONTEND_IMAGE_BASE}:latest")
ADMIN_TAG_ARGS=(-t "${ADMIN_IMAGE_BASE}:${GIT_SHA}" -t "${ADMIN_IMAGE_BASE}:latest")
if [[ -n "${IMAGE_TAG:-}" ]]; then
	TAG_ARGS+=(-t "${IMAGE_BASE}:${IMAGE_TAG}")
	FRONTEND_TAG_ARGS+=(-t "${FRONTEND_IMAGE_BASE}:${IMAGE_TAG}")
	ADMIN_TAG_ARGS+=(-t "${ADMIN_IMAGE_BASE}:${IMAGE_TAG}")
fi

echo "==> Build/push backend"
docker buildx build --platform "${PLATFORM}" \
	--label "org.opencontainers.image.revision=${GIT_SHA}" \
	"${TAG_ARGS[@]}" --push backend

if [[ "$BUILD_FRONTEND" -eq 1 ]]; then
	echo "==> Build/push frontend"
	docker buildx build --platform "${PLATFORM}" \
		--label "org.opencontainers.image.revision=${GIT_SHA}" \
		"${FRONTEND_TAG_ARGS[@]}" --push frontend
fi

if [[ "$BUILD_ADMIN" -eq 1 ]]; then
	echo "==> Build/push admin"
	docker buildx build --platform "${PLATFORM}" \
		--label "org.opencontainers.image.revision=${GIT_SHA}" \
		"${ADMIN_TAG_ARGS[@]}" --push admin
fi

echo "==> Đã push tag ${GIT_SHA}"
echo "==> Trên host production: đặt SANDBOX_SERVICE_IMAGE_TAG=${GIT_SHA} trong deploy/.env.prod"
[[ "$BUILD_FRONTEND" -eq 1 ]] && echo "==>   và SANDBOX_SERVICE_FRONTEND_IMAGE_TAG=${GIT_SHA} (cùng tag, build chung một lần)"
[[ "$BUILD_ADMIN" -eq 1 ]] && echo "==>   và SANDBOX_SERVICE_ADMIN_IMAGE_TAG=${GIT_SHA} (cùng tag, build chung một lần)"
echo "==> rồi chạy (trong deploy/) ./deploy.prod.sh"
