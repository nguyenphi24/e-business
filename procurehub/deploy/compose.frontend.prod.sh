#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
: "${PROCUREHUB_FRONTEND_IMAGE_TAG:?PROCUREHUB_FRONTEND_IMAGE_TAG is required}"
export PROCUREHUB_FRONTEND_IMAGE="${REGISTRY_HOST}/${PROJECT_PATH}-frontend:${PROCUREHUB_FRONTEND_IMAGE_TAG}"
exec docker compose -f docker-compose.frontend.prod.yml "$@"
