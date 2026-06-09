#!/bin/bash
# =============================================================================
# Pin bge-m3 in Ollama memory permanently
# Multilingual embedding model (~1.2GB) used for every RAG/KB query.
# The global keep_alive of 5m would otherwise unload it between uses.
#
# NOTE on Ollama install (TESTED 2026-06-08):
#   Use the official Ollama.app from https://ollama.com — NOT the Homebrew
#   bottle. As of brew's `ollama` 0.30.6, the bottle is missing the
#   `llama-server` binary that Ollama 0.30+ split out, so /api/embed and
#   /api/chat both 500 with:
#     "error starting llama-server: llama-server binary not found".
#   The Ollama.app at /Applications/Ollama.app/Contents/Resources/ollama
#   has everything bundled and works fine.
# =============================================================================

EMBED_MODEL="${EMBED_MODEL:-bge-m3}"

# Wait for Ollama to be ready
for i in {1..30}; do
    curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null 2>&1 && break
    sleep 2
done

if ! curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama did not become ready after 60s — skipping pin" >&2
    exit 1
fi

# Pin the embedding model with keep_alive=-1 (never unload).
# /api/embed is the right endpoint for embedding models — /api/generate
# would 400 on models that lack a chat template.
curl -s http://localhost:11434/api/embed -d "{
  \"model\": \"$EMBED_MODEL\",
  \"input\": \"\",
  \"keep_alive\": -1
}" > /dev/null 2>&1

echo "$EMBED_MODEL pinned in memory"
