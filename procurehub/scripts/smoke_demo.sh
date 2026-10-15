#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:48000}"
WEB_URL="${WEB_URL:-http://localhost:43000}"
PASSWORD="${DEMO_PASSWORD:-Demo@2026}"
COOKIE_JAR="$(mktemp)"
trap 'rm -f "$COOKIE_JAR"' EXIT

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

expect_status() {
  local expected="$1"
  shift
  local actual
  actual="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' "$@")"
  [[ "$actual" == "$expected" ]] || fail "expected HTTP $expected, got HTTP $actual for $*"
}

get_json() {
  curl --fail --silent --show-error "$@"
}

login() {
  local email="$1"
  get_json \
    --cookie "$COOKIE_JAR" \
    --cookie-jar "$COOKIE_JAR" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$PASSWORD\"}" \
    "$API_URL/api/v1/auth/login"
}

printf 'Checking backend health... '
health="$(get_json "$API_URL/api/v1/health")"
[[ "$(jq -r '.status' <<<"$health")" == 'ok' ]] || fail 'health status is not ok'
container_health="$(get_json "$API_URL/health/")"
[[ "$(jq -r '.status' <<<"$container_health")" == 'ok' ]] || fail 'container health status is not ok'
printf 'ok\n'

printf 'Checking frontend routes... '
expect_status 200 "$WEB_URL/login"
expect_status 200 "$WEB_URL/"
printf 'ok\n'

printf 'Checking buyer scope and dashboard... '
buyer_login="$(login buyer@vnptmedia.demo)"
buyer_access="$(jq -r '.access' <<<"$buyer_login")"
buyer_company_id="$(jq -r '.user.company.id' <<<"$buyer_login")"
[[ -n "$buyer_access" && "$buyer_access" != 'null' ]] || fail 'buyer access token is missing'
buyer_dashboard="$(get_json -H "Authorization: Bearer $buyer_access" "$API_URL/api/v1/dashboard")"
[[ "$(jq -r '.scope.company_id' <<<"$buyer_dashboard")" == "$buyer_company_id" ]] || fail 'buyer company scope is incorrect'
[[ "$(jq '.recent_activity | length' <<<"$buyer_dashboard")" -ge 1 ]] || fail 'buyer activity timeline is empty'
printf 'ok\n'

printf 'Checking audit filter... '
audit="$(get_json -H "Authorization: Bearer $buyer_access" "$API_URL/api/v1/audit-events?action=PO_COMPLETED")"
[[ "$(jq '.count' <<<"$audit")" -ge 1 ]] || fail 'PO_COMPLETED audit event is missing'
printf 'ok\n'

printf 'Checking refresh token rotation... '
refreshed="$(get_json --cookie "$COOKIE_JAR" --cookie-jar "$COOKIE_JAR" -X POST "$API_URL/api/v1/auth/refresh")"
refreshed_access="$(jq -r '.access' <<<"$refreshed")"
[[ -n "$refreshed_access" && "$refreshed_access" != 'null' ]] || fail 'refresh did not return a new access token'
printf 'ok\n'

printf 'Checking supplier visibility... '
supplier_login="$(login sales@techvision.demo)"
supplier_access="$(jq -r '.access' <<<"$supplier_login")"
supplier_rfqs="$(get_json -H "Authorization: Bearer $supplier_access" "$API_URL/api/v1/rfqs")"
[[ "$(jq '.count' <<<"$supplier_rfqs")" -ge 1 ]] || fail 'supplier cannot see the seeded RFQ'
printf 'ok\n'

printf 'Checking cross-company isolation... '
other_login="$(login buyer@otherbuyer.demo)"
other_access="$(jq -r '.access' <<<"$other_login")"
other_company_id="$(jq -r '.user.company.id' <<<"$other_login")"
other_dashboard="$(get_json -H "Authorization: Bearer $other_access" "$API_URL/api/v1/dashboard")"
[[ "$(jq -r '.scope.company_id' <<<"$other_dashboard")" == "$other_company_id" ]] || fail 'other buyer scope is incorrect'
other_rfqs="$(get_json -H "Authorization: Bearer $other_access" "$API_URL/api/v1/rfqs")"
[[ "$(jq '.count' <<<"$other_rfqs")" == 0 ]] || fail 'other buyer can see another company RFQ'
printf 'ok\n'

printf 'Checking dashboard KPIs and notifications... '
[[ "$(jq '.kpis | length' <<<"$buyer_dashboard")" == 6 ]] || fail 'buyer dashboard is missing KPIs'
get_json -H "Authorization: Bearer $buyer_access" "$API_URL/api/v1/notifications/unread-count" | jq -e '.unread_count >= 0' >/dev/null || fail 'notification inbox is unavailable'
printf 'ok\n'

printf 'Checking finance invoices... '
finance_login="$(login finance@vnptmedia.demo)"
finance_access="$(jq -r '.access' <<<"$finance_login")"
finance_invoices="$(get_json -H "Authorization: Bearer $finance_access" "$API_URL/api/v1/invoices")"
[[ "$(jq '.count' <<<"$finance_invoices")" -ge 1 ]] || fail 'finance cannot see the seeded invoice'
other_invoices="$(get_json -H "Authorization: Bearer $other_access" "$API_URL/api/v1/invoices")"
[[ "$(jq '.count' <<<"$other_invoices")" == 0 ]] || fail 'other buyer can see another company invoice'
printf 'ok\n'

printf 'Checking unauthenticated API rejection... '
expect_status 401 "$API_URL/api/v1/dashboard"
expect_status 401 "$API_URL/api/v1/notifications/stream"
expect_status 401 -X POST -H 'Content-Type: application/json' -d '{}' "$API_URL/api/v1/webhooks/payment"
printf 'ok\n'

printf 'Smoke demo passed.\n'
