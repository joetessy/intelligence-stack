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

echo "Starting MCP filesystem server on :8901..."
npx -y supergateway \
  --stdio "npx -y @modelcontextprotocol/server-filesystem $ALLOWED_DIRS" \
  --port 8901 \
  --outputTransport streamableHttp &
FS_PID=$!

echo "MCP filesystem server running (PID=$FS_PID)"
echo ""
echo "Register in Open WebUI: Admin Panel → Settings → Connections → Tool Servers"
echo "  http://host.docker.internal:8901/mcp"

trap "kill $FS_PID 2>/dev/null; exit 0" INT TERM
wait
