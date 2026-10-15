#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"

: "${REGISTRY_USER:?REGISTRY_USER is required}"
: "${REGISTRY_PASS:?REGISTRY_PASS is required}"
: "${PROCUREHUB_IMAGE_TAG:?PROCUREHUB_IMAGE_TAG is required}"
: "${PROCUREHUB_FRONTEND_IMAGE_TAG:?PROCUREHUB_FRONTEND_IMAGE_TAG is required}"
export PROCUREHUB_IMAGE="${REGISTRY_HOST}/${PROJECT_PATH}:${PROCUREHUB_IMAGE_TAG}"
export PROCUREHUB_FRONTEND_IMAGE="${REGISTRY_HOST}/${PROJECT_PATH}-frontend:${PROCUREHUB_FRONTEND_IMAGE_TAG}"

printf '%s\n' "$REGISTRY_PASS" | docker login "$REGISTRY_HOST" --username "$REGISTRY_USER" --password-stdin

docker compose -f docker-compose.prod.yml pull postgres app
docker compose -f docker-compose.prod.yml up -d postgres
docker compose -f docker-compose.prod.yml run --rm app python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml up -d app

for attempt in $(seq 1 30); do
    container_id="$(docker compose -f docker-compose.prod.yml ps -q app)"
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}starting{{end}}' "$container_id" 2>/dev/null || true)"
    [[ "$status" == "healthy" ]] && break
    [[ "$status" == "unhealthy" ]] && { docker compose -f docker-compose.prod.yml logs app; exit 1; }
    sleep 2
done

container_id="$(docker compose -f docker-compose.prod.yml ps -q app)"
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$container_id")" == "healthy" ]] || {
    docker compose -f docker-compose.prod.yml logs app
    exit 1
}

docker compose -f docker-compose.frontend.prod.yml pull frontend
docker compose -f docker-compose.frontend.prod.yml up -d frontend
printf 'ProcureHub production stacks are healthy.\n'
