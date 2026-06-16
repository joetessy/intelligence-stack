#!/bin/bash
# =============================================================================
# Warm the always-on models in llama-swap at login.
#
# llama-swap already keeps these loaded: they're in the "always-on" group with
# ttl:0 (never unload) and listed in `hooks.on_startup.preload` in
# llama-swap/config.yaml. This script is belt-and-suspenders — it nudges the
# embedding model ready in case the LaunchAgent fires before llama-swap is up.
#
# Replaces the old Ollama keep_alive=-1 pin. Ollama is no longer used; pinning
# is now declared in llama-swap/config.yaml instead of imperatively here.
# =============================================================================

ENDPOINT="${LLAMASWAP_URL:-http://localhost:9292}"
EMBED_MODEL="${EMBED_MODEL:-bge-m3}"

# Wait for llama-swap to be ready
for i in {1..30}; do
    curl -s --connect-timeout 2 "$ENDPOINT/v1/models" > /dev/null 2>&1 && break
    sleep 2
done

if ! curl -s --connect-timeout 2 "$ENDPOINT/v1/models" > /dev/null 2>&1; then
    echo "ERROR: llama-swap not ready after 60s — skipping warm-up" >&2
    exit 1
fi

# Touch the embedding model so it's hot for the first RAG query (ttl:0 in the
# config means llama-swap then keeps it loaded indefinitely).
curl -s "$ENDPOINT/v1/embeddings" \
  -H 'Content-Type: application/json' \
  -d "{\"model\": \"$EMBED_MODEL\", \"input\": \"warm\"}" > /dev/null 2>&1

echo "$EMBED_MODEL warmed via llama-swap"
