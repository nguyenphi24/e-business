#!/usr/bin/env bash
# Deploy trên host production: pull image theo tag ghim, đổi container, chờ
# healthy, rồi mới xoá image cũ.
#
# Backend (db + app, docker-compose.yml), frontend
# (docker-compose.frontend.prod.yml) và admin (docker-compose.admin.prod.yml)
# — hai cái sau chỉ tồn tại khi repo có frontend/ / admin/ — là các stack
# Compose ĐỘC LẬP: không network chung, không depends_on nhau. Script này
# lần lượt thử backend rồi frontend rồi admin (deploy_stack trong _stack.sh);
# mỗi bên tự pull/health check/rollback riêng và CHỈ dừng+khởi động lại nếu
# tag đang chạy khác tag đích — một bản chỉ sửa một trong ba không bounce
# hai cái còn lại, kể cả về mặt "có bị restart hay không", chứ không chỉ về
# biến môi trường.
#
# QUAN TRỌNG: một stack FAIL (vd backend không healthy) KHÔNG chặn các stack
# còn lại — deploy_stack trả về (return) chứ không tự exit, mỗi lời gọi nằm
# trong `if ! deploy_stack ...`. Backend tạch không có nghĩa frontend cũng bị
# bỏ qua theo; script tổng kết đúng-sai từng stack ở cuối rồi mới exit khác 0
# nếu có ít nhất một stack fail.
#
# KHÔNG build gì — image phải có sẵn trên registry (chạy ./build.sh ở máy dev
# trước). Chạy script này TRÊN host production, trong chính thư mục deploy/
# này: đây là thứ duy nhất cần tồn tại trên server.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# shellcheck disable=SC1091
source ./_env.sh
# shellcheck disable=SC1091
source ./_stack.sh

: "${REGISTRY_USER:?REGISTRY_USER thiếu}"
: "${REGISTRY_PASS:?REGISTRY_PASS thiếu}"

# Repo không có database (init.sh --db none, hoặc --db sqlite — nhúng file
# trong container app, không phải service riêng) thì app không có
# `depends_on:` (chỉ xuất hiện khi có service database riêng — postgres/
# mysql/mongo/clickhouse — để chờ nó healthy trước). Nhận ra qua chính file
# này thay vì hỏi init.sh đã chọn gì (deploy/ phải tự chứa, không có nguồn
# nào khác để tra). KHÔNG grep tên service cố định ("db") vì giờ service
# database mang tên engine thật, khác nhau giữa 4 lựa chọn.
if grep -q 'depends_on:' docker-compose.prod.yml; then
	: "${SANDBOX_SERVICE_DB_PASSWORD:?SANDBOX_SERVICE_DB_PASSWORD thiếu trong $APP_ENV_FILE}"
fi

# Cố ý không có default "latest": tag đó bị push đè mỗi lần build nên deploy nó
# thì không biết đang chạy bản nào, và rollback kéo lại cùng tag chưa chắc ra
# đúng bits cũ. Mỗi lần deploy phải chỉ đích danh một tag bất biến.
: "${SANDBOX_SERVICE_IMAGE_TAG:?SANDBOX_SERVICE_IMAGE_TAG thiếu — đặt bằng git short SHA build.sh đã push, không bao giờ \"latest\"}"
export SANDBOX_SERVICE_IMAGE="${IMAGE_BASE}:${SANDBOX_SERVICE_IMAGE_TAG}"

# Frontend/admin optional — chỉ deploy khi file compose của nó tồn tại (repo
# có frontend/ / admin/) VÀ .env.prod đã điền tag tương ứng. Có file compose
# nhưng thiếu tag thì BÁO RÕ vì sao bị bỏ qua — im lặng bỏ qua khiến người
# chạy tưởng script hỏng, phải tự bash -x mới ra được lý do.
FRONTEND_ENABLED=0
if [[ -f docker-compose.frontend.prod.yml ]]; then
	if [[ -n "${SANDBOX_SERVICE_FRONTEND_IMAGE_TAG:-}" ]]; then
		FRONTEND_ENABLED=1
		export SANDBOX_SERVICE_FRONTEND_IMAGE="${IMAGE_BASE}-frontend:${SANDBOX_SERVICE_FRONTEND_IMAGE_TAG}"
	else
		echo "==> [frontend] Bỏ qua: SANDBOX_SERVICE_FRONTEND_IMAGE_TAG trống trong $APP_ENV_FILE — điền tag build.sh vừa push rồi chạy lại nếu muốn deploy frontend." >&2
	fi
fi
ADMIN_ENABLED=0
if [[ -f docker-compose.admin.prod.yml ]]; then
	if [[ -n "${SANDBOX_SERVICE_ADMIN_IMAGE_TAG:-}" ]]; then
		ADMIN_ENABLED=1
		export SANDBOX_SERVICE_ADMIN_IMAGE="${IMAGE_BASE}-admin:${SANDBOX_SERVICE_ADMIN_IMAGE_TAG}"
	else
		echo "==> [admin] Bỏ qua: SANDBOX_SERVICE_ADMIN_IMAGE_TAG trống trong $APP_ENV_FILE — điền tag build.sh vừa push rồi chạy lại nếu muốn deploy admin." >&2
	fi
fi

echo "==> Đăng nhập ${REGISTRY_HOST}"
echo "${REGISTRY_PASS}" | docker login "${REGISTRY_HOST}" -u "${REGISTRY_USER}" --password-stdin

# ===== Backend (db + app) =====
BACKEND_OK=1
HOST_PORT="${SANDBOX_SERVICE_HOST_PORT:-8080}"
# Django route là /health/ (có dấu /); không có dấu / sẽ nhận 301 thay vì JSON.
if ! deploy_stack "backend" "./compose.prod.sh" "app" \
	"$SANDBOX_SERVICE_IMAGE" "$IMAGE_BASE" "http://127.0.0.1:${HOST_PORT}/health/"; then
	BACKEND_OK=0
fi

# ===== Frontend (nếu có) =====
FRONTEND_OK=1
if [[ "$FRONTEND_ENABLED" -eq 1 ]]; then
	FRONTEND_HOST_PORT="${SANDBOX_SERVICE_FRONTEND_HOST_PORT:-8081}"
	# Static file server — không có endpoint /health riêng, trang gốc trả
	# về được là container đã lên. Thử dù backend vừa fail — hai bên không
	# phụ thuộc nhau.
	if ! deploy_stack "frontend" "./compose.frontend.prod.sh" "frontend" \
		"$SANDBOX_SERVICE_FRONTEND_IMAGE" "${IMAGE_BASE}-frontend" "http://127.0.0.1:${FRONTEND_HOST_PORT}/"; then
		FRONTEND_OK=0
	fi
fi

# ===== Admin (nếu có) =====
ADMIN_OK=1
if [[ "$ADMIN_ENABLED" -eq 1 ]]; then
	ADMIN_HOST_PORT="${SANDBOX_SERVICE_ADMIN_HOST_PORT:-8082}"
	if ! deploy_stack "admin" "./compose.admin.prod.sh" "admin" \
		"$SANDBOX_SERVICE_ADMIN_IMAGE" "${IMAGE_BASE}-admin" "http://127.0.0.1:${ADMIN_HOST_PORT}/"; then
		ADMIN_OK=0
	fi
fi

# ===== Tổng kết =====
echo "==> Kết quả:"
if [[ "$BACKEND_OK" -eq 1 ]]; then
	echo "    backend:  OK — ${SANDBOX_SERVICE_IMAGE}"
else
	echo "    backend:  THẤT BẠI — xem log ở trên"
fi
if [[ "$FRONTEND_ENABLED" -eq 1 ]]; then
	if [[ "$FRONTEND_OK" -eq 1 ]]; then
		echo "    frontend: OK — ${SANDBOX_SERVICE_FRONTEND_IMAGE}"
	else
		echo "    frontend: THẤT BẠI — xem log ở trên"
	fi
fi
if [[ "$ADMIN_ENABLED" -eq 1 ]]; then
	if [[ "$ADMIN_OK" -eq 1 ]]; then
		echo "    admin:    OK — ${SANDBOX_SERVICE_ADMIN_IMAGE}"
	else
		echo "    admin:    THẤT BẠI — xem log ở trên"
	fi
fi

if [[ "$BACKEND_OK" -eq 0 ]]; then
	echo "!! Backend thất bại nghĩa là KHÔNG CÒN bản nào chạy (bản cũ đã bị" >&2
	echo "!! dừng trước khi thử bản mới), chứ không phải \"vẫn chạy bản cũ\"." >&2
	if [[ "$FRONTEND_OK" -eq 1 || "$ADMIN_OK" -eq 1 ]]; then
		echo "!! Frontend/admin ở trên báo OK chỉ có nghĩa container đó tự phục" >&2
		echo "!! vụ static file được — mọi tính năng gọi /api/ vẫn lỗi cho tới khi" >&2
		echo "!! backend lên lại. Nếu bản frontend/admin này đổi cùng lúc với" >&2
		echo "!! backend và cần API mới chưa từng chạy được, đừng coi đây là xong." >&2
	fi
fi

if [[ "$BACKEND_OK" -eq 0 || "$FRONTEND_OK" -eq 0 || "$ADMIN_OK" -eq 0 ]]; then
	exit 1
fi
