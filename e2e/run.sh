#!/usr/bin/env bash
# End-to-end test: real Home Assistant container + stub model + headless Chromium.
# Usage: e2e/run.sh [ha-image]   (needs docker, python3, node)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${1:-ghcr.io/home-assistant/home-assistant:2026.10.2}"
HA_PORT=18123
STUB_PORT="${STUB_PORT:-18080}"
WORK="$(mktemp -d)"
NAME="llm-agent-e2e-$$"
cleanup() {
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  [[ -n "${STUB_PID:-}" ]] && kill "$STUB_PID" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "$WORK/config/custom_components"
cp "$ROOT/e2e/configuration.yaml" "$WORK/config/"
cp -r "$ROOT/custom_components/llm_agent" "$WORK/config/custom_components/"
chmod -R a+rwX "$WORK/config"

python3 "$ROOT/e2e/stub_openai.py" "$STUB_PORT" &
STUB_PID=$!

docker run -d --name "$NAME" --network host -e TZ=UTC -v "$WORK/config:/config" "$IMAGE" >/dev/null
python3 "$ROOT/e2e/setup_ha.py" "http://127.0.0.1:$HA_PORT" "http://127.0.0.1:$STUB_PORT/v1" > "$WORK/tokens.json" \
  || { docker logs "$NAME" 2>&1 | tail -50; exit 1; }

cd "$ROOT/e2e"
[[ -d node_modules ]] || npm install --no-audit --no-fund >/dev/null
node panel.mjs "http://127.0.0.1:$HA_PORT" "$WORK/tokens.json" "$WORK/config" "${SHOTS:-$WORK}" \
  || { docker logs "$NAME" 2>&1 | grep -i "llm_agent\|error" | tail -40; exit 1; }
if docker logs "$NAME" 2>&1 | grep -q "Error.*llm_agent\|Traceback.*llm_agent"; then
  docker logs "$NAME" 2>&1 | grep -B2 -A20 "llm_agent" | tail -60
  echo "FAIL: errors from llm_agent in the HA log"; exit 1
fi
echo "screenshots: ${SHOTS:-$WORK}"
