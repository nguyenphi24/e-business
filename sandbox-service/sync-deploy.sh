#!/usr/bin/env bash
# Đồng bộ thư mục deploy/ lên host production qua rsync/SSH.
#
# Chạy ở MÁY DEV (như build.sh), không chạy trên server — chỉ đưa file lên,
# không tự SSH vào chạy deploy.prod.sh thay bạn. Cuối script in sẵn lệnh để
# bạn tự chạy bước đó.
#
# Dùng:
#   cp .env.sync.example .env.sync   # điền SSH_HOST/SSH_USER/DEPLOY_PATH
#   ./sync-deploy.sh
#
# .env.sync ở ROOT (không phải deploy/) vì chỉ mình script này — chạy ở máy
# dev — đọc nó; không script nào trên server cần tới, khác .env.prod/
# .env.registry (bắt buộc nằm trong deploy/ vì server chỉ có mỗi thư mục
# đó — xem standard/deploy.md).
#
# KHÔNG đụng .env.prod / .env.registry đã có sẵn trên server — hai file đó
# là nguồn xác định server đang chạy tag nào và cách kết nối registry; ghi đè
# bằng bản local (có khi cũ hơn hoặc không tồn tại) sẽ vô tình rollback ngầm.
# Lần đầu tạo chúng trực tiếp trên server, từ .example.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

ENV_FILE="${SYNC_ENV_FILE:-.env.sync}"
if [[ ! -f "$ENV_FILE" ]]; then
	echo "Thiếu $ENV_FILE — copy .env.sync.example sang $ENV_FILE rồi điền." >&2
	exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${SSH_HOST:?SSH_HOST thiếu trong $ENV_FILE}"
: "${SSH_USER:?SSH_USER thiếu trong $ENV_FILE}"
: "${DEPLOY_PATH:?DEPLOY_PATH thiếu trong $ENV_FILE — thư mục gốc trên server sẽ chứa nội dung deploy/}"
SSH_PORT="${SSH_PORT:-22}"

SSH_OPTS=(-p "$SSH_PORT")
[[ -n "${SSH_KEY:-}" ]] && SSH_OPTS+=(-i "$SSH_KEY")

echo "==> Kiểm SSH tới ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" exit 2>/dev/null; then
	echo "!! Chưa SSH được bằng key (chưa có key, hoặc key chưa được copy lên server)." >&2

	if [[ ! -t 0 ]]; then
		echo "!! Shell không tương tác — không tự hỏi được. Tạo key + ssh-copy-id tay rồi chạy lại." >&2
		exit 1
	fi

	read -r -p "Tạo SSH key mới (nếu chưa có) và copy lên server luôn? [y/N] " confirm
	if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
		echo "Dừng lại. Tự chuẩn bị SSH key rồi chạy lại script." >&2
		exit 1
	fi

	KEY_PATH="${SSH_KEY:-$HOME/.ssh/id_ed25519}"
	if [[ ! -f "$KEY_PATH" ]]; then
		echo "==> Tạo key mới tại $KEY_PATH"
		ssh-keygen -t ed25519 -f "$KEY_PATH" -C "sync-deploy"
	else
		echo "==> Đã có key tại $KEY_PATH, dùng lại"
	fi

	echo "==> Copy key lên server (sẽ hỏi password của ${SSH_USER}@${SSH_HOST})"
	ssh-copy-id -p "$SSH_PORT" -i "${KEY_PATH}.pub" "${SSH_USER}@${SSH_HOST}"

	SSH_OPTS=(-p "$SSH_PORT" -i "$KEY_PATH")
	if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" exit 2>/dev/null; then
		echo "!! Vẫn chưa SSH được sau khi copy key — kiểm tra lại thủ công." >&2
		exit 1
	fi
fi
echo "==> SSH OK"

echo "==> Đảm bảo $DEPLOY_PATH tồn tại trên server"
ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "mkdir -p '$DEPLOY_PATH'"

echo "==> rsync deploy/ -> ${SSH_HOST}:${DEPLOY_PATH}"
# Không --delete: script chỉ thêm/cập nhật, không tự xoá gì trên server (có
# thể có volume mount log/media ngay trong deploy/ mà local không biết tới).
rsync -avz \
	-e "ssh -p ${SSH_PORT}${SSH_KEY:+ -i ${SSH_KEY}}" \
	--exclude ".env.prod" \
	--exclude ".env.registry" \
	deploy/ "${SSH_USER}@${SSH_HOST}:${DEPLOY_PATH}/"

echo "==> Đã sync xong"

MISSING=()
for f in .env.prod .env.registry; do
	if ! ssh "${SSH_OPTS[@]}" "${SSH_USER}@${SSH_HOST}" "test -f '${DEPLOY_PATH}/${f}'" 2>/dev/null; then
		MISSING+=("$f")
	fi
done
if [[ "${#MISSING[@]}" -gt 0 ]]; then
	echo "!! Trên server còn thiếu: ${MISSING[*]}" >&2
	echo "!! Tạo trực tiếp trên server từ bản .example tương ứng trước khi deploy." >&2
fi

echo "==> Xong. Deploy thật thì tự SSH vào chạy:"
echo "    ssh -p ${SSH_PORT} ${SSH_USER}@${SSH_HOST} 'cd ${DEPLOY_PATH} && ./deploy.prod.sh'"
