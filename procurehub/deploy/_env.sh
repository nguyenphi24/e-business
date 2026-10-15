#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

for file in .env.registry .env.prod; do
    [[ -f "$file" ]] || { printf 'Missing deploy/%s; copy the .example file first.\n' "$file" >&2; exit 1; }
done

set -a
source .env.registry
source .env.prod
set +a

: "${REGISTRY_HOST:?REGISTRY_HOST is required}"
: "${PROJECT_PATH:?PROJECT_PATH is required}"
