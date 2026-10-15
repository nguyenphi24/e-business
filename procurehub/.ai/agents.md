# Agent constraints and verification

## Before editing

- Đọc `AGENTS.md`, `.ai/project.md`, `.ai/architecture.md` và tài liệu endpoint liên quan.
- Không sửa spec nghiệp vụ ở `../docs/specs/` nếu task không yêu cầu; xem đó là baseline nghiệp vụ.

## Verification

```bash
cd backend
pyenv local 3.11.15
.venv311/bin/python manage.py check
.venv311/bin/python manage.py test
```

Acceptance PostgreSQL:

```bash
cd procurehub
./scripts/acceptance_postgres.sh
```

Frontend:

```bash
cd frontend
source "$HOME/.nvm/nvm.sh"
nvm use 22.23.2
npm exec tsc -- --noEmit
npm run build
```

Smoke khi hai server đang chạy:

```bash
./scripts/smoke_demo.sh
```

Không chạy migration/seed vào host database ngoài `localhost` hoặc `127.0.0.1`.
