#!/bin/bash
# =============================================================================
# Pin nomic-embed-text in Ollama memory permanently
# This model is only 274MB and is needed for every RAG/KB query.
# The global keep_alive of 5m would otherwise unload it between uses.
# =============================================================================

# Wait for Ollama to be ready
for i in {1..30}; do
    curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null 2>&1 && break
    sleep 2
done

if ! curl -s --connect-timeout 2 http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama did not become ready after 60s — skipping pin" >&2
    exit 1
fi

# Pin the embedding model with keep_alive=-1 (never unload)
curl -s http://localhost:11434/api/generate -d '{
  "model": "nomic-embed-text",
  "prompt": "",
  "keep_alive": -1
}' > /dev/null 2>&1

echo "nomic-embed-text pinned in memory"
