# Dùng chung bởi deploy.prod.sh cho cả ba stack (backend/frontend/admin):
# pull, CHỈ dừng+khởi động lại nếu tag đang chạy khác tag đích (hoặc
# container chưa chạy) — một bản chỉ đổi frontend không còn kéo theo restart
# backend dù backend chẳng có gì thay đổi — rồi chờ health, rồi mới xoá
# image cũ. `source` file này, không tự chạy được.
#
# TRẢ VỀ (return), KHÔNG exit — deploy.prod.sh gọi mỗi stack trong
# `if ! deploy_stack ...; then` để một stack fail (vd backend không healthy)
# không chặn các stack độc lập còn lại (frontend/admin) khỏi được thử. Vì
# vậy code bên trong tự kiểm tra `docker pull`/`up -d` thành công hay không
# thay vì dựa vào `set -e` của script gọi — bên trong một `if !`, set -e bị
# tắt cho toàn bộ hàm, dựa vào nó ở đây sẽ không dừng đúng chỗ.
#
#   deploy_stack <label> <compose_sh> <service> <image> <image_base> <health_url>
#     label       tên hiển thị trong log, vd "backend"
#     compose_sh  ./compose.prod.sh (hay bản frontend/admin)
#     service     tên service trong compose file, vd "app"
#     image       image đích đầy đủ (đã kèm tag)
#     image_base  tiền tố image của riêng stack này (để không lỡ xoá image
#                 của stack khác nếu nó trùng registry/project)
#     health_url  URL curl để coi là "lên" (endpoint /health thật, hoặc "/"
#                 với static file server không có health endpoint riêng)
deploy_stack() {
	local label="$1" compose_sh="$2" service="$3" image="$4" image_base="$5" health_url="$6"

	local prev_id prev_image prev_running
	prev_id="$("$compose_sh" ps -q "$service" 2>/dev/null || true)"
	prev_image=""
	prev_running=0
	if [[ -n "$prev_id" ]]; then
		prev_image="$(docker inspect "$prev_id" --format '{{.Config.Image}}' 2>/dev/null || true)"
		[[ "$(docker inspect "$prev_id" --format '{{.State.Running}}' 2>/dev/null || echo false)" == "true" ]] && prev_running=1
	fi

	echo "==> [$label] Pull ${image}"
	if ! docker pull "${image}"; then
		echo "!! [$label] Pull thất bại — dừng lại, không đụng container đang chạy." >&2
		return 1
	fi

	if [[ "$prev_running" -eq 1 && "$prev_image" == "$image" ]]; then
		echo "==> [$label] Đã chạy đúng tag này rồi — bỏ qua restart"
	else
		echo "==> [$label] Dừng container hiện tại (nếu có)"
		"$compose_sh" stop "$service" 2>/dev/null || true
		echo "==> [$label] Khởi động"
		if ! "$compose_sh" up -d; then
			echo "!! [$label] Không khởi động được container." >&2
			return 1
		fi
	fi

	echo "==> [$label] Chờ health trên $health_url"
	local healthy=0
	for _ in $(seq 1 45); do
		if curl -sf "$health_url" >/dev/null 2>&1; then
			healthy=1
			break
		fi
		sleep 2
	done

	if [[ "$healthy" -ne 1 ]]; then
		echo "!! [$label] không healthy sau 90s." >&2
		echo "!! Xem log: $compose_sh logs $service" >&2
		echo "!! Không xoá image cũ — vẫn còn đó để rollback." >&2
		return 1
	fi
	echo "==> [$label] healthy"

	if [[ -n "$prev_image" && "$prev_image" != "$image" && "$prev_image" == "${image_base}:"* ]]; then
		echo "==> [$label] Xoá image bị thay thế: ${prev_image}"
		docker rmi "$prev_image" 2>/dev/null || echo "    (còn được tham chiếu chỗ khác — bỏ qua)"
	fi
	return 0
}
