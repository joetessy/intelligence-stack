#!/usr/bin/env bash
# provision-webui.sh — Register MCP tool servers and Open Terminal with Open WebUI.
#
# Run this once after initial setup to wire everything into the Open WebUI admin panel.
# Safe to re-run — it overwrites the existing registrations with the current state.
#
# Usage:
#   ./provision-webui.sh                             # auto-detects API key from DB
#   OPENWEBUI_API_KEY=sk-oi-... ./provision-webui.sh # supply key explicitly

set -euo pipefail

WEBUI_URL="${OPEN_WEBUI_URL:-http://localhost:3000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $*"; }
err()  { echo -e "  ${RED}✗${NC} $*"; }

# ── Wait for Open WebUI ──────────────────────────────────────────────────────
printf "Waiting for Open WebUI at %s" "$WEBUI_URL"
for i in $(seq 1 20); do
  if curl -sf "$WEBUI_URL/health" --max-time 3 > /dev/null 2>&1; then
    echo ""; break
  fi
  if [[ $i -eq 20 ]]; then
    echo ""
    err "Open WebUI is not reachable. Start it with: docker compose up -d"
    exit 1
  fi
  printf "."
  sleep 2
done

# ── Resolve admin API key ────────────────────────────────────────────────────
if [[ -n "${OPENWEBUI_API_KEY:-}" ]]; then
  API_KEY="$OPENWEBUI_API_KEY"
else
  printf "Fetching admin API key from Open WebUI database..."
  API_KEY="$(docker exec open-webui python3 -c "
import sqlite3, sys
try:
    conn = sqlite3.connect('/app/backend/data/webui.db')
    cur = conn.cursor()
    cur.execute(\"SELECT a.key FROM api_key a JOIN user u ON a.user_id = u.id WHERE u.role='admin' LIMIT 1\")
    row = cur.fetchone()
    if row: print(row[0])
    else: sys.exit(1)
except Exception as e:
    print(e, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null)" || true

  if [[ -z "$API_KEY" ]]; then
    echo ""
    err "Could not retrieve API key. Either:"
    echo "     • Create an admin account at $WEBUI_URL first, then re-run"
    echo "     • Or supply the key explicitly: OPENWEBUI_API_KEY=sk-oi-... ./provision-webui.sh"
    exit 1
  fi
  echo " done"
fi
ok "API key resolved"

# ── Resolve Open Terminal key from .env ──────────────────────────────────────
TERMINAL_KEY=""
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  TERMINAL_KEY="$(grep '^OPEN_TERMINAL_API_KEY=' "$SCRIPT_DIR/.env" 2>/dev/null | cut -d= -f2- || true)"
fi

# ── Helpers ──────────────────────────────────────────────────────────────────
webui_post() {
  local path="$1" body="$2"
  http_code=$(curl -s -o /tmp/provision-webui-resp.json -w "%{http_code}" \
    -X POST "$WEBUI_URL$path" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$body")
  if [[ "$http_code" != 2* ]]; then
    err "POST $path returned HTTP $http_code"
    cat /tmp/provision-webui-resp.json 2>/dev/null && echo ""
    return 1
  fi
}

port_open() { nc -z localhost "$1" 2>/dev/null; }

# ── MCP Tool Servers ─────────────────────────────────────────────────────────
echo ""
echo "==> MCP Tool Servers"

# Wait up to 60 s for the filesystem server (it may still be starting via LaunchAgent)
MCP_SKIP=false
ready=false
for i in $(seq 1 30); do
  if port_open 8901; then ready=true; break; fi
  sleep 2
done
if ! $ready; then
  warn "Port 8901 not reachable after 60 s — skipping MCP registration"
  MCP_SKIP=true
fi

if ! $MCP_SKIP; then
  webui_post "/api/v1/configs/tool_servers" '{
    "TOOL_SERVER_CONNECTIONS": [
      {
        "url": "http://host.docker.internal:8901/mcp",
        "path": "/",
        "type": "mcp",
        "auth_type": "none",
        "headers": null,
        "key": "",
        "config": {"enable": true},
        "info": {
          "id": "mcp-filesystem",
          "name": "Filesystem",
          "description": "Read & write files in ~/Documents, ~/Projects, ~/Downloads"
        }
      }
    ]
  }'
  ok "Filesystem server registered  →  http://host.docker.internal:8901/mcp"
  echo "     To activate: Workspace → Models → (select model) → Tools → enable Filesystem"
else
  warn "Skipped — start MCP server first: ./mcp-servers.sh"
fi

# ── Open Terminal ────────────────────────────────────────────────────────────
echo ""
echo "==> Open Terminal"

if ! port_open 8888; then
  warn "Port 8888 (Open Terminal) not listening"
  echo "     Start it: docker compose up -d open-terminal"
elif [[ -z "$TERMINAL_KEY" ]]; then
  warn "OPEN_TERMINAL_API_KEY not found in .env"
  echo "     Add it to .env, then re-run this script"
else
  webui_post "/api/v1/configs/terminal_servers" "{
    \"TERMINAL_SERVER_CONNECTIONS\": [
      {
        \"id\": \"open-terminal\",
        \"name\": \"Open Terminal\",
        \"enabled\": true,
        \"url\": \"http://open-terminal:8000\",
        \"path\": \"/openapi.json\",
        \"key\": \"$TERMINAL_KEY\",
        \"auth_type\": \"bearer\",
        \"config\": {}
      }
    ]
  }"
  ok "Open Terminal registered  →  http://open-terminal:8000"
  echo "     Access it via the terminal icon in the Open WebUI sidebar"
fi

echo ""
echo "Done. Open WebUI at $WEBUI_URL"
