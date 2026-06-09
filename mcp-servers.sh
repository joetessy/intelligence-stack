#!/usr/bin/env bash
# mcp-servers.sh — MCP tool server for Open WebUI
#
# Runs the filesystem MCP server that Open WebUI can use as a tool during chat:
#   :8901  filesystem — read/write files in ~/Documents, ~/Projects, ~/Downloads
#
# Usage:
#   ./mcp-servers.sh          run in foreground (Ctrl-C to stop)
#   launchctl load ~/Library/LaunchAgents/com.intelligence-stack.mcp-servers.plist

set -euo pipefail

ALLOWED_DIRS="$HOME/Documents $HOME/Projects $HOME/Downloads"

# Pin both packages to specific versions so KeepAlive restarts don't have to
# hit npm for a version-resolve round-trip. Bump these by hand when you want
# to upgrade — `npm view <pkg> version` shows the latest.
SUPERGATEWAY_VERSION="3.4.3"
FS_MCP_VERSION="2026.1.14"

echo "Starting MCP filesystem server on :8901..."
npx -y "supergateway@${SUPERGATEWAY_VERSION}" \
  --stdio "npx -y @modelcontextprotocol/server-filesystem@${FS_MCP_VERSION} $ALLOWED_DIRS" \
  --port 8901 \
  --outputTransport streamableHttp &
FS_PID=$!

echo "MCP filesystem server running (PID=$FS_PID)"
echo ""
echo "Register in Open WebUI: Admin Panel → Settings → Connections → Tool Servers"
echo "  http://host.docker.internal:8901/mcp"

trap "kill $FS_PID 2>/dev/null; exit 0" INT TERM
wait
