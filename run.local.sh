#!/usr/bin/env bash
# Chạy toàn bộ demo ở máy dev: PostgreSQL (Docker) → ProcureHub backend → frontend → sandbox-service.
#
#   ./run.local.sh          kiểm tra môi trường, cài phụ thuộc còn thiếu, khởi động, Ctrl+C để tắt hết
#   ./run.local.sh reset    như trên nhưng làm mới dữ liệu demo cả hai bên trước (dùng trước mỗi buổi demo)
#   ./run.local.sh check    chỉ kiểm tra môi trường, không khởi động
#   ./run.local.sh stop     tắt các tiến trình do script này khởi động (container PostgreSQL giữ nguyên)
#
# Chỉ dùng cho máy dev: database luôn ở localhost, mật khẩu seed chỉ dành cho demo.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PH_DIR="$ROOT_DIR/procurehub"
SBX_DIR="$ROOT_DIR/sandbox-service"
RUN_DIR="$ROOT_DIR/.run"
LOG_DIR="$RUN_DIR/logs"

PY_MIN_MINOR=11          # cần Python 3.11+
PY_PREFERRED="3.11.15"   # bản pyenv theo .ai/conventions.md
NODE_MIN_MAJOR=22
NODE_PREFERRED="22.23.2" # bản nvm theo .ai/conventions.md

PG_PORT=45432
BE_PORT=48000
FE_PORT=43000
SBX_PORT=28080
RESET_DATA=0

if [[ -t 1 ]]; then
	BOLD=$'\033[1m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; RESET=$'\033[0m'
else
	BOLD=""; GREEN=""; YELLOW=""; RED=""; RESET=""
fi
step() { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RESET"; }
ok()   { printf '  %s✓%s %s\n' "$GREEN" "$RESET" "$1"; }
warn() { printf '  %s!%s %s\n' "$YELLOW" "$RESET" "$1"; }
die()  { printf '  %s✗ %s%s\n' "$RED" "$1" "$RESET" >&2; exit 1; }

# ---------------------------------------------------------------- tiến trình nền

stop_all() {
	[[ -d "$RUN_DIR" ]] || return 0
	local pidfile pid name
	for pidfile in "$RUN_DIR"/*.pid; do
		[[ -e "$pidfile" ]] || continue
		name="$(basename "$pidfile" .pid)"
		pid="$(cat "$pidfile")"
		if kill -0 "$pid" 2>/dev/null; then
			# runserver/vite sinh tiến trình con: dừng cả nhóm con trước rồi tới tiến trình chính
			pkill -TERM -P "$pid" 2>/dev/null || true
			kill -TERM "$pid" 2>/dev/null || true
			printf '  đã dừng %s (pid %s)\n' "$name" "$pid"
		fi
		rm -f "$pidfile"
	done
}

start_bg() { # start_bg <tên> <thư mục> <lệnh...>
	local name="$1" dir="$2"; shift 2
	( cd "$dir" && exec "$@" ) >"$LOG_DIR/$name.log" 2>&1 &
	echo $! >"$RUN_DIR/$name.pid"
}

wait_http() { # wait_http <tên> <url> <số giây>
	local name="$1" url="$2" timeout="$3" i
	for ((i = 0; i < timeout; i++)); do
		if curl -sf -o /dev/null "$url"; then ok "$name sẵn sàng: $url"; return 0; fi
		if ! kill -0 "$(cat "$RUN_DIR/$name.pid")" 2>/dev/null; then break; fi
		sleep 1
	done
	printf '  %s✗ %s không lên được. 30 dòng log cuối (%s):%s\n' "$RED" "$name" "$LOG_DIR/$name.log" "$RESET" >&2
	tail -n 30 "$LOG_DIR/$name.log" >&2 || true
	exit 1
}

# ---------------------------------------------------------------- kiểm tra công cụ

version_ge() { # version_ge 3.11.4 3.11 → đúng nếu bản thứ nhất >= bản thứ hai
	[[ "$(printf '%s\n%s\n' "$2" "$1" | sort -t. -k1,1n -k2,2n -k3,3n | head -n1)" == "$2" ]]
}

PYTHON_BIN=""
find_python() {
	step "Python (cần 3.$PY_MIN_MINOR+)"
	local candidate version native=""
	# 1) bản cài sẵn trên máy
	for candidate in python3 python3.13 python3.12 python3.11; do
		command -v "$candidate" >/dev/null 2>&1 || continue
		version="$("$candidate" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
		if version_ge "$version" "3.$PY_MIN_MINOR"; then
			native="$(command -v "$candidate")"
			ok "native: $native ($version)"
			break
		fi
		warn "native $candidate là $version — thấp hơn 3.$PY_MIN_MINOR"
	done
	# 2) môi trường dựng venv: ưu tiên đúng bản đã chốt của pyenv để mọi máy giống nhau
	local pyenv_root="${PYENV_ROOT:-$HOME/.pyenv}"
	if [[ -x "$pyenv_root/versions/$PY_PREFERRED/bin/python" ]]; then
		PYTHON_BIN="$pyenv_root/versions/$PY_PREFERRED/bin/python"
		ok "dựng venv bằng pyenv $PY_PREFERRED"
		return
	fi
	if [[ -n "$native" ]]; then
		PYTHON_BIN="$native"
		version="$("$native" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
		version_ge "3.13" "$version" || warn "Python $version mới hơn bản đã kiểm thử (3.11) — nên cài: pyenv install $PY_PREFERRED"
		ok "dựng venv bằng native $PYTHON_BIN"
		return
	fi
	for candidate in "$pyenv_root"/versions/3.1[1-9]*/bin/python; do
		[[ -x "$candidate" ]] || continue
		PYTHON_BIN="$candidate"; ok "dựng venv bằng pyenv: $PYTHON_BIN"; return
	done
	die "Không tìm thấy Python 3.$PY_MIN_MINOR+. Cài: pyenv install $PY_PREFERRED"
}

NODE_READY=0
find_node() {
	step "Node (cần $NODE_MIN_MAJOR+)"
	local version
	# 1) bản cài sẵn trên máy
	if command -v node >/dev/null 2>&1; then
		version="$(node -v | sed 's/^v//')"
		if version_ge "$version" "$NODE_MIN_MAJOR"; then
			ok "native: $(command -v node) (v$version)"; NODE_READY=1; return
		fi
		warn "native node là v$version — thấp hơn $NODE_MIN_MAJOR"
	fi
	# 2) nvm
	local nvm_sh="${NVM_DIR:-$HOME/.nvm}/nvm.sh"
	if [[ -s "$nvm_sh" ]]; then
		set +u; # nvm.sh dùng biến chưa khai báo
		# shellcheck disable=SC1090
		source "$nvm_sh"
		if nvm use "$NODE_PREFERRED" >/dev/null 2>&1 || nvm use "$NODE_MIN_MAJOR" >/dev/null 2>&1; then
			set -u
			ok "nvm: $(command -v node) ($(node -v))"; NODE_READY=1; return
		fi
		set -u
		die "nvm có nhưng chưa cài Node $NODE_MIN_MAJOR. Cài: nvm install $NODE_PREFERRED"
	fi
	die "Không tìm thấy Node $NODE_MIN_MAJOR+. Cài nvm rồi: nvm install $NODE_PREFERRED"
}

check_tools() {
	step "Công cụ khác"
	local tool
	for tool in docker curl openssl lsof; do
		command -v "$tool" >/dev/null 2>&1 || die "Thiếu $tool"
	done
	docker info >/dev/null 2>&1 || die "Docker chưa chạy — mở Docker Desktop rồi chạy lại"
	ok "docker, curl, openssl, lsof"
}

check_ports() {
	step "Cổng local"
	local port label busy=0
	for port in $BE_PORT $FE_PORT $SBX_PORT; do
		case $port in
			"$BE_PORT") label="backend";; "$FE_PORT") label="frontend";; *) label="sandbox-service";;
		esac
		if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
			warn "cổng $port ($label) đang bị chiếm: $(lsof -nP -iTCP:"$port" -sTCP:LISTEN | awk 'NR==2{print $1" pid "$2}')"
			busy=1
		else
			ok "cổng $port ($label) trống"
		fi
	done
	# PostgreSQL bận là bình thường nếu chính container của project đang chạy
	if lsof -nP -iTCP:"$PG_PORT" -sTCP:LISTEN >/dev/null 2>&1 && ! docker compose -f "$PH_DIR/docker-compose.yml" ps --status running -q 2>/dev/null | grep -q .; then
		warn "cổng $PG_PORT đang bị tiến trình khác (không phải PostgreSQL của project) chiếm"
		busy=1
	fi
	[[ $busy -eq 0 ]] || die "Giải phóng cổng (hoặc chạy ./run.local.sh stop) rồi chạy lại — script không tự tắt tiến trình của người khác"
}

# ---------------------------------------------------------------- môi trường ảo + phụ thuộc

ensure_venv() { # ensure_venv <thư mục backend> <file requirements>
	local backend="$1" req="$2" venv="$1/.venv311" hash
	hash="$(cat "$backend/$req" | shasum | awk '{print $1}')"
	if [[ ! -x "$venv/bin/python" ]]; then
		warn "chưa có $venv — tạo mới bằng $PYTHON_BIN"
		"$PYTHON_BIN" -m venv "$venv"
	elif ! version_ge "$("$venv/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" "3.$PY_MIN_MINOR"; then
		die "$venv dùng Python cũ hơn 3.$PY_MIN_MINOR — xóa thư mục này rồi chạy lại"
	fi
	if [[ "$(cat "$venv/.requirements.sha" 2>/dev/null)" != "$hash" ]]; then
		warn "cài phụ thuộc từ $req (log: $LOG_DIR/pip-$(basename "$(dirname "$backend")").log)"
		"$venv/bin/python" -m pip install -q --upgrade pip >/dev/null
		"$venv/bin/python" -m pip install -r "$backend/$req" >"$LOG_DIR/pip-$(basename "$(dirname "$backend")").log" 2>&1 \
			|| die "pip install thất bại — xem log ở trên"
		echo "$hash" >"$venv/.requirements.sha"
	fi
	ok "$venv ($("$venv/bin/python" --version))"
}

ensure_node_modules() {
	local fe="$PH_DIR/frontend" hash
	hash="$(cat "$fe/package-lock.json" 2>/dev/null | shasum | awk '{print $1}')"
	if [[ ! -d "$fe/node_modules" || "$(cat "$fe/node_modules/.lock.sha" 2>/dev/null)" != "$hash" ]]; then
		warn "cài node_modules (log: $LOG_DIR/npm.log)"
		( cd "$fe" && npm install ) >"$LOG_DIR/npm.log" 2>&1 || die "npm install thất bại — xem $LOG_DIR/npm.log"
		echo "$hash" >"$fe/node_modules/.lock.sha"
	fi
	ok "$fe/node_modules"
}

# ---------------------------------------------------------------- .env

env_value() { # env_value <file> <KEY> — rỗng nếu chưa có file hoặc chưa có biến (không làm set -e dừng script)
	[[ -f "$1" ]] || return 0
	grep -E "^$2=" "$1" | head -n1 | cut -d= -f2- || true
}

set_env() { # set_env <file> <KEY> <giá trị>
	local file="$1" key="$2" value="$3"
	if grep -qE "^$key=" "$file"; then
		sed -i.bak "s|^$key=.*|$key=$value|" "$file" && rm -f "$file.bak"
	else
		printf '%s=%s\n' "$key" "$value" >>"$file"
	fi
}

ensure_env() {
	step "Cấu hình .env"
	local ph_env="$PH_DIR/.env" sbx_env="$SBX_DIR/.env" api_key webhook_secret
	# Hai service phải dùng chung API key và webhook secret: lấy từ file đã có, nếu chưa có thì sinh mới.
	api_key="$(env_value "$sbx_env" SANDBOX_API_KEY)"
	[[ -n "$api_key" && "$api_key" != replace-* ]] || api_key="$(env_value "$ph_env" SANDBOX_API_KEY)"
	[[ -n "$api_key" && "$api_key" != replace-* ]] || api_key="$(openssl rand -hex 32)"
	webhook_secret="$(env_value "$sbx_env" SANDBOX_WEBHOOK_SECRET)"
	[[ -n "$webhook_secret" && "$webhook_secret" != replace-* ]] || webhook_secret="$(env_value "$ph_env" SANDBOX_WEBHOOK_SECRET)"
	[[ -n "$webhook_secret" && "$webhook_secret" != replace-* ]] || webhook_secret="$(openssl rand -hex 32)"

	local file
	for file in "$ph_env" "$sbx_env"; do
		if [[ ! -f "$file" ]]; then
			cp "$(dirname "$file")/.env.example" "$file"
			set_env "$file" SECRET_KEY "$(openssl rand -hex 48)"
			warn "tạo $file từ .env.example (secret sinh ngẫu nhiên)"
		fi
		[[ "$(env_value "$file" SECRET_KEY)" != replace-* ]] || set_env "$file" SECRET_KEY "$(openssl rand -hex 48)"
		set_env "$file" SANDBOX_API_KEY "$api_key"
		set_env "$file" SANDBOX_WEBHOOK_SECRET "$webhook_secret"
	done
	set_env "$ph_env" SANDBOX_BASE_URL "http://127.0.0.1:$SBX_PORT"
	ok "procurehub/.env và sandbox-service/.env dùng chung SANDBOX_API_KEY, SANDBOX_WEBHOOK_SECRET"
}

# ---------------------------------------------------------------- khởi động

start_postgres() {
	step "PostgreSQL (Docker, cổng $PG_PORT)"
	( cd "$PH_DIR" && docker compose up -d --wait ) >"$LOG_DIR/postgres.log" 2>&1 \
		|| { tail -n 20 "$LOG_DIR/postgres.log" >&2; die "docker compose up thất bại"; }
	ok "container PostgreSQL đang chạy"
}

start_backend() {
	step "ProcureHub backend (cổng $BE_PORT)"
	local py="$PH_DIR/backend/.venv311/bin/python"
	( cd "$PH_DIR/backend" && "$py" manage.py migrate --noinput ) >"$LOG_DIR/migrate-procurehub.log" 2>&1 \
		|| { tail -n 20 "$LOG_DIR/migrate-procurehub.log" >&2; die "migrate thất bại"; }
	ok "migrate xong"
	local seed_out
	if [[ $RESET_DATA -eq 1 ]]; then
		( cd "$PH_DIR/backend" && "$py" manage.py seed_demo --reset ) >"$LOG_DIR/seed-procurehub.log" 2>&1 \
			|| { tail -n 20 "$LOG_DIR/seed-procurehub.log" >&2; die "seed_demo --reset thất bại"; }
		ok "đã làm mới dữ liệu demo (tài khoản: xem $LOG_DIR/seed-procurehub.log)"
	elif seed_out="$(cd "$PH_DIR/backend" && "$py" manage.py seed_demo 2>&1)"; then
		ok "nạp dữ liệu demo lần đầu"
	elif grep -q "đã có dữ liệu" <<<"$seed_out"; then
		ok "dữ liệu demo đã có sẵn (giữ nguyên; muốn làm lại: manage.py seed_demo --reset)"
	else
		printf '%s\n' "$seed_out" >&2; die "seed_demo thất bại"
	fi
	start_bg backend "$PH_DIR/backend" "$py" manage.py runserver "127.0.0.1:$BE_PORT"
	wait_http backend "http://127.0.0.1:$BE_PORT/api/v1/health" 60
}

start_frontend() {
	step "ProcureHub frontend (cổng $FE_PORT)"
	start_bg frontend "$PH_DIR/frontend" npm run dev
	wait_http frontend "http://localhost:$FE_PORT/" 60
}

start_sandbox() {
	step "sandbox-service (cổng $SBX_PORT)"
	local py="$SBX_DIR/backend/.venv311/bin/python"
	( cd "$SBX_DIR/backend" && "$py" manage.py migrate --noinput ) >"$LOG_DIR/migrate-sandbox.log" 2>&1 \
		|| { tail -n 20 "$LOG_DIR/migrate-sandbox.log" >&2; die "migrate sandbox thất bại"; }
	ok "migrate xong"
	local seed_args=()
	[[ $RESET_DATA -eq 1 ]] && seed_args=(--reset)
	( cd "$SBX_DIR/backend" && "$py" manage.py seed_sandbox ${seed_args[@]+"${seed_args[@]}"} ) >"$LOG_DIR/seed-sandbox.log" 2>&1 \
		|| { tail -n 20 "$LOG_DIR/seed-sandbox.log" >&2; die "seed_sandbox thất bại"; }
	if [[ $RESET_DATA -eq 1 ]]; then ok "đã xóa giao dịch/hóa đơn/yêu cầu ký cũ; CA và chứng thư 2 NCC sẵn sàng"; else ok "CA và chứng thư 2 NCC sẵn sàng"; fi
	start_bg sandbox "$SBX_DIR/backend" "$py" manage.py runserver "127.0.0.1:$SBX_PORT"
	wait_http sandbox "http://127.0.0.1:$SBX_PORT/health/" 60
}

prepare() {
	mkdir -p "$LOG_DIR"
	find_python
	find_node
	check_tools
	check_ports
	step "Môi trường ảo và phụ thuộc"
	ensure_venv "$PH_DIR/backend" requirements.txt
	ensure_venv "$SBX_DIR/backend" requirements/dev.txt
	ensure_node_modules
	ensure_env
}

main() {
	case "${1:-start}" in
		stop)
			# Báo cho terminal đang chạy script biết đây là dừng có chủ đích, không phải sự cố.
			mkdir -p "$RUN_DIR" && touch "$RUN_DIR/stop-requested"
			step "Dừng các tiến trình"; stop_all; exit 0 ;;
		check)
			prepare; step "Môi trường sẵn sàng"; exit 0 ;;
		start) ;;
		reset) RESET_DATA=1 ;;
		*) echo "Dùng: $0 [start|reset|check|stop]" >&2; exit 2 ;;
	esac

	prepare
	rm -f "$RUN_DIR/stop-requested"
	# Bất kỳ đường thoát nào (Ctrl+C, lỗi giữa chừng, tiến trình con chết) cũng dọn các tiến trình đã bật.
	trap 'step "Đang tắt"; stop_all' EXIT
	trap 'printf "\n"; exit 0' INT TERM
	start_postgres
	start_backend
	start_frontend
	start_sandbox

	step "Đã chạy đủ"
	cat <<EOF
  Giao diện       http://localhost:$FE_PORT   (mật khẩu demo: Demo@2026)
  API / Swagger   http://127.0.0.1:$BE_PORT/api/v1/docs
  sandbox-service http://127.0.0.1:$SBX_PORT/health/
  Log             $LOG_DIR/{backend,frontend,sandbox}.log

  Tài khoản: buyer@ / manager@ / finance@vnptmedia.demo, sales@techvision.demo, sales@digitalsupply.demo
  Ctrl+C để tắt tất cả (PostgreSQL giữ nguyên; tắt hẳn: cd procurehub && docker compose down)
EOF
	# Giữ script chạy; dừng nếu một tiến trình con chết.
	while true; do
		for name in backend frontend sandbox; do
			if ! kill -0 "$(cat "$RUN_DIR/$name.pid" 2>/dev/null)" 2>/dev/null; then
				if [[ -f "$RUN_DIR/stop-requested" ]]; then
					rm -f "$RUN_DIR/stop-requested"
					ok "đã dừng theo lệnh ./run.local.sh stop"
					exit 0
				fi
				warn "$name đã dừng bất ngờ — xem $LOG_DIR/$name.log"
				exit 1
			fi
		done
		sleep 3
	done
}

main "$@"
