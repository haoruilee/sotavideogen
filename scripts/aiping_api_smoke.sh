#!/usr/bin/env bash
# Smoke test aiping.cn video API (POST create + GET poll). Requires AIPING_TOKEN in env.
# Do not print the token. Intended for CI (GitHub Actions secret AIPING_TOKEN).

set -euo pipefail

BASE="${AIPING_API_BASE:-https://aiping.cn/api/v1}"
MAX_WAIT_SEC="${AIPING_POLL_MAX_SEC:-300}"
INTERVAL_SEC="${AIPING_POLL_INTERVAL_SEC:-5}"

if [[ -z "${AIPING_TOKEN:-}" ]]; then
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "AIPING_TOKEN is not set in CI. Add the secret in repo Settings → Secrets."
    exit 1
  fi
  echo "AIPING_TOKEN is not set; skipping API smoke test."
  exit 0
fi

json_escape() {
  python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"
}

PROMPT=$(json_escape "CI smoke: short abstract clip, no people, solid color background")

BODY=$(cat <<EOF
{
  "model": "Kling-V3-Omni",
  "prompt": ${PROMPT},
  "seconds": 5,
  "mode": "pro",
  "aspect_ratio": "1:1"
}
EOF
)

echo "POST ${BASE}/videos"
RESP=$(curl -sS -w "\n%{http_code}" -X POST "${BASE}/videos" \
  -H "Authorization: Bearer ${AIPING_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "${BODY}")

HTTP_BODY=$(echo "$RESP" | head -n -1)
HTTP_CODE=$(echo "$RESP" | tail -n 1)

echo "HTTP status: ${HTTP_CODE}"
echo "Response body (truncated):"
echo "$HTTP_BODY" | head -c 2000
echo ""

if [[ "$HTTP_CODE" != "200" && "$HTTP_CODE" != "201" && "$HTTP_CODE" != "202" ]]; then
  echo "Unexpected status from POST"
  exit 1
fi

TASK_ID=$(echo "$HTTP_BODY" | python3 -c "
import sys, json
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except json.JSONDecodeError:
    sys.exit(2)
# common shapes
for key in ('id', 'task_id', 'taskId'):
    v = d.get(key)
    if v is not None:
        print(v)
        sys.exit(0)
for key in ('data', 'result'):
    sub = d.get(key)
    if isinstance(sub, dict):
        for k2 in ('id', 'task_id', 'taskId'):
            v = sub.get(k2)
            if v is not None:
                print(v)
                sys.exit(0)
sys.exit(3)
") || true

if [[ -z "${TASK_ID:-}" ]]; then
  echo "Could not parse task id from POST response"
  exit 1
fi

echo "Task id: ${TASK_ID}"

deadline=$((SECONDS + MAX_WAIT_SEC))
while (( SECONDS < deadline )); do
  RESP=$(curl -sS -w "\n%{http_code}" -X GET "${BASE}/videos/${TASK_ID}" \
    -H "Authorization: Bearer ${AIPING_TOKEN}" \
    -H "Content-Type: application/json")

  HTTP_BODY=$(echo "$RESP" | head -n -1)
  HTTP_CODE=$(echo "$RESP" | tail -n 1)

  if [[ "$HTTP_CODE" != "200" ]]; then
    echo "GET unexpected status: ${HTTP_CODE}"
    echo "$HTTP_BODY" | head -c 1500
    exit 1
  fi

  STATUS=$(echo "$HTTP_BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for k in ('status', 'state', 'task_status'):
    if k in d:
        print(d[k])
        break
else:
    sub = d.get('data') or d.get('result')
    if isinstance(sub, dict):
        for k in ('status', 'state'):
            if k in sub:
                print(sub[k])
                break
" 2>/dev/null || echo "")

  echo "Poll status: ${STATUS:-unknown}"

  case "${STATUS,,}" in
    *success*|*completed*|*succeed*|*done*)
      echo "Smoke test OK (terminal success state)"
      exit 0
      ;;
    *fail*|*error*|*cancel*)
      echo "Task failed: ${STATUS}"
      echo "$HTTP_BODY" | head -c 2000
      exit 1
      ;;
  esac

  sleep "${INTERVAL_SEC}"
done

echo "Timeout after ${MAX_WAIT_SEC}s waiting for terminal status"
exit 1
