#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ -f .env.registry ]]; then
    set -a
    source .env.registry
    set +a
fi

: "${REGISTRY_HOST:?REGISTRY_HOST is required}"
: "${PROJECT_PATH:?PROJECT_PATH is required}"
: "${REGISTRY_USER:?REGISTRY_USER is required}"
: "${REGISTRY_PASS:?REGISTRY_PASS is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required; use an immutable tag}"

GIT_SHA="${GIT_SHA:-unknown}"
IMAGE_BASE="${REGISTRY_HOST}/${PROJECT_PATH}"
PLATFORM="${PLATFORM:-linux/amd64}"
VITE_API_URL="${VITE_API_URL:?VITE_API_URL is required for the frontend build}"

printf '%s\n' "$REGISTRY_PASS" | docker login "$REGISTRY_HOST" --username "$REGISTRY_USER" --password-stdin

docker build --platform "$PLATFORM" --build-arg GIT_SHA="$GIT_SHA" -t "$IMAGE_BASE:$IMAGE_TAG" backend
docker build --platform "$PLATFORM" --build-arg VITE_API_URL="$VITE_API_URL" -t "$IMAGE_BASE-frontend:$IMAGE_TAG" frontend
docker push "$IMAGE_BASE:$IMAGE_TAG"
docker push "$IMAGE_BASE-frontend:$IMAGE_TAG"

printf 'Pushed immutable images with tag %s.\n' "$IMAGE_TAG"
