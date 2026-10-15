#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/_env.sh"
: "${PROCUREHUB_IMAGE_TAG:?PROCUREHUB_IMAGE_TAG is required}"
export PROCUREHUB_IMAGE="${REGISTRY_HOST}/${PROJECT_PATH}:${PROCUREHUB_IMAGE_TAG}"
exec docker compose -f docker-compose.prod.yml "$@"
