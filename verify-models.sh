#!/bin/bash
# verify-models.sh — Load every ~/models/*.gguf in llama-server and confirm it
# serves. Chat models get a 1-token /v1/chat/completions; embedding models get a
# /v1/embeddings call; vision models load with their mmproj. Sequential (one at a
# time) so we never exceed unified memory. Reports arch + chat-template status.
set -u
MODELS_DIR="${MODELS_DIR:-$HOME/models}"
PORT=8099
HOST=127.0.0.1
LLAMA_SERVER="$(command -v llama-server)"

GREEN='\033[0;32m'; RED='\033[0;31m'; YEL='\033[1;33m'; DIM='\033[2m'; NC='\033[0m'
pass=0; fail=0; declare -a FAILED

# Embedding models (need --embeddings; tested via /v1/embeddings)
EMBED_MODELS=" bge-m3 nomic-embed-text "
# Vision models (load with matching .mmproj.gguf)
VISION_MODELS=" moondream qwen3.8-27b huihui-qwen3.6-27b-abliterated-mtp huihui-qwen3.6-35b-a3b-claude-4.7-opus-abliterated-mtp "

is_in() { case "$2" in *" $1 "*) return 0;; esac; return 1; }

check() {
  local stem="$1"
  local gguf="$MODELS_DIR/$stem.gguf"
  local mmproj="$MODELS_DIR/$stem.mmproj.gguf"
  local log="/tmp/verify-$stem.log"
  local -a extra=()
  local kind="chat"

  if is_in "$stem" "$EMBED_MODELS"; then
    extra+=(--embeddings); kind="embed"
  elif is_in "$stem" "$VISION_MODELS"; then
    extra+=(--mmproj "$mmproj"); kind="vision"
  else
    extra+=(--flash-attn on --cache-type-k q8_0 --cache-type-v q8_0)
  fi

  printf "  %-52s " "$stem [$kind]"

  "$LLAMA_SERVER" -m "$gguf" "${extra[@]}" --host "$HOST" --port "$PORT" \
    -ngl auto -c 2048 --no-webui > "$log" 2>&1 &
  local pid=$!

  local ready=0
  for _ in $(seq 1 120); do
    if curl -sf "http://$HOST:$PORT/health" >/dev/null 2>&1; then ready=1; break; fi
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done

  if [[ $ready -eq 0 ]]; then
    echo -e "${RED}FAIL (did not load)${NC}"
    kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
    fail=$((fail+1)); FAILED+=("$stem")
    grep -iE "error|unknown model arch|failed|abort|assert" "$log" | head -3 | sed 's/^/        /'
    return
  fi

  # Exercise inference
  local rc body
  if [[ "$kind" == "embed" ]]; then
    body=$(curl -s "http://$HOST:$PORT/v1/embeddings" -H 'Content-Type: application/json' \
      -d "{\"model\":\"$stem\",\"input\":\"hello world\"}")
    echo "$body" | grep -q '"embedding"' && rc=0 || rc=1
  else
    body=$(curl -s "http://$HOST:$PORT/v1/chat/completions" -H 'Content-Type: application/json' \
      -d "{\"model\":\"$stem\",\"messages\":[{\"role\":\"user\",\"content\":\"Say OK\"}],\"max_tokens\":4}")
    echo "$body" | grep -q '"content"' && rc=0 || rc=1
  fi

  local arch tmpl
  arch=$(grep -oE "arch[[:space:]]+=[[:space:]]+[a-z0-9_.-]+" "$log" | head -1 | awk '{print $3}')
  if grep -qiE "chat template|chat_template" "$log"; then tmpl="tmpl:embedded"; else tmpl="tmpl:?"; fi

  kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null

  if [[ $rc -eq 0 ]]; then
    echo -e "${GREEN}PASS${NC} ${DIM}(${arch:-?} $tmpl)${NC}"
    pass=$((pass+1))
  else
    echo -e "${RED}FAIL (loaded but inference failed)${NC} ${DIM}(${arch:-?})${NC}"
    echo "$body" | head -c 300 | sed 's/^/        /'; echo
    fail=$((fail+1)); FAILED+=("$stem")
  fi
}

echo ""
echo "Verifying models in $MODELS_DIR with $LLAMA_SERVER"
echo ""

# Drain llama-swap before testing: a chat model held on :9292 double-books
# unified memory with the copy loaded here and Metal OOMs ("Compute error")
# once both near the working-set limit — bit us with qwen3.8-27b (18 GB × 2 on
# 48 GB). Pinned always-on models reload on their next request, or restart the
# service afterwards: launchctl kickstart -k gui/$(id -u)/com.intelligence-stack.llama-swap
curl -sf --max-time 10 "http://127.0.0.1:9292/unload" >/dev/null 2>&1 || true
for gguf in "$MODELS_DIR"/*.gguf; do
  stem="$(basename "$gguf" .gguf)"
  [[ "$stem" == *.mmproj ]] && continue   # skip projector files
  check "$stem"
done

echo ""
echo -e "  ${GREEN}$pass passed${NC}, ${RED}$fail failed${NC}"
if [[ $fail -gt 0 ]]; then
  echo -e "  ${YEL}Failed:${NC} ${FAILED[*]}"
  exit 1
fi
echo "  All models load and serve. Safe to proceed."
