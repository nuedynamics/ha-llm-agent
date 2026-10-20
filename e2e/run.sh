#!/usr/bin/env bash
# End-to-end test: real Home Assistant container + stub model + headless Chromium.
# Usage: e2e/run.sh [ha-image]   (needs docker, python3, node)
# LIVE_MODEL=<model> runs e2e/live_check.py against a real model in the running Ollama
# container named by OLLAMA_CONTAINER (default hla-ollama) instead of the browser test.
# LIVE_PROVIDER=anthropic uses Anthropic instead, with the API key read from LIVE_KEY_FILE
# (default ~/.config/hla/anthropic.key). The key never leaves this machine except to the
# provider, and the throwaway HA config that held it is deleted afterwards.
# With SHOTS=<dir> it also saves README screenshots of those conversations there.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${1:-ghcr.io/home-assistant/home-assistant:2026.10.2}"
HA_PORT=18123
STUB_PORT="${STUB_PORT:-18089}"
WORK="$(mktemp -d)"
NAME="llm-agent-e2e-$(basename "$WORK" | tr -c "a-zA-Z0-9\n" "-" | tr "A-Z" "a-z")"
cleanup() {
  [[ -n "${KEEP:-}" ]] && { echo "kept $NAME, config in $WORK"; return; }
  # HA writes .storage as root (it can hold an API key): delete it from inside first.
  docker exec "$NAME" rm -rf /config/.storage >/dev/null 2>&1 || true
  docker rm -f "$NAME" "$NAME-stub" >/dev/null 2>&1 || true
  docker network rm "$NAME" >/dev/null 2>&1 || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

mkdir -p "$WORK/config/custom_components"
cp "$ROOT/e2e/configuration.yaml" "$WORK/config/"
touch "$WORK/config/automations.yaml" "$WORK/config/scripts.yaml" "$WORK/config/scenes.yaml"
cp -r "$ROOT/custom_components/llm_agent" "$WORK/config/custom_components/"
chmod -R a+rwX "$WORK/config"

# The stub model runs in its own container on a private network, using the HA image's Python.
docker network create "$NAME" >/dev/null
docker run -d --name "$NAME-stub" --network "$NAME" --network-alias stub \
  -v "$ROOT/e2e/stub_openai.py:/stub.py:ro" --entrypoint python3 "$IMAGE" /stub.py "$STUB_PORT" 0.0.0.0 >/dev/null

docker run -d --name "$NAME" --network "$NAME" -p "127.0.0.1:$HA_PORT:8123" -e TZ=UTC -v "$WORK/config:/config" "$IMAGE" >/dev/null
if [[ -n "${LIVE_MODEL:-}" ]]; then
  if [[ "${LIVE_PROVIDER:-ollama}" == "anthropic" ]]; then
    KEY_FILE="${LIVE_KEY_FILE:-$HOME/.config/hla/anthropic.key}"
    [[ -r "$KEY_FILE" ]] || { echo "no API key file at $KEY_FILE"; exit 1; }
    LLM_TYPE=anthropic LLM_NAME=Anthropic LLM_KEY="$(<"$KEY_FILE")" LLM_MODEL="$LIVE_MODEL" \
      python3 "$ROOT/e2e/setup_ha.py" "http://127.0.0.1:$HA_PORT" "https://api.anthropic.com" > "$WORK/tokens.json" \
      || { docker logs "$NAME" 2>&1 | tail -50; exit 1; }
  else
    OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-hla-ollama}"
    docker network connect --alias ollama "$NAME" "$OLLAMA_CONTAINER"
    trap 'docker network disconnect "$NAME" "$OLLAMA_CONTAINER" >/dev/null 2>&1 || true; cleanup' EXIT
    LLM_TYPE=ollama LLM_NAME=Ollama LLM_KEY="" LLM_MODEL="$LIVE_MODEL" \
      python3 "$ROOT/e2e/setup_ha.py" "http://127.0.0.1:$HA_PORT" "http://ollama:11434/v1" > "$WORK/tokens.json" \
      || { docker logs "$NAME" 2>&1 | tail -50; exit 1; }
  fi
  docker cp "$ROOT/e2e/live_check.py" "$NAME:/live_check.py" >/dev/null
  TOKEN="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["access_token"])' "$WORK/tokens.json")"
  status=0
  docker exec "$NAME" python3 /live_check.py "$TOKEN" || status=$?
  if [[ -n "${SHOTS:-}" ]]; then
    (cd "$ROOT/e2e" && { [[ -d node_modules ]] || npm install --no-audit --no-fund >/dev/null; } \
      && node shots.mjs "http://127.0.0.1:$HA_PORT" "$WORK/tokens.json" "$SHOTS") || status=1
  fi
  docker logs "$NAME" 2>&1 | grep -i "error.*llm_agent\|traceback" | tail -20 || true
  exit "$status"
fi

python3 "$ROOT/e2e/setup_ha.py" "http://127.0.0.1:$HA_PORT" "http://stub:$STUB_PORT/v1" > "$WORK/tokens.json" \
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
