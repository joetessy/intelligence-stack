#!/usr/bin/env bash
# mcp-servers.sh — MCP tool servers for Open WebUI
#
# Runs two MCP servers that Open WebUI can use as tools during chat:
#   :8901  filesystem — read/write files in ~/Documents, ~/Projects, ~/Downloads
#   :8902  memory     — persistent knowledge graph across conversations
#
# Register in Open WebUI: Admin Panel → Tools → Add Tool Server
#   Filesystem: http://host.docker.internal:8901/sse
#   Memory:     http://host.docker.internal:8902/sse
#
# Usage:
#   ./mcp-servers.sh          run in foreground (Ctrl-C to stop both)
#   launchctl load ~/Library/LaunchAgents/com.intelligence-stack.mcp-servers.plist

set -euo pipefail

ALLOWED_DIRS="$HOME/Documents $HOME/Projects $HOME/Downloads"

echo "Starting MCP filesystem server on :8901..."
npx -y supergateway \
  --stdio "npx -y @modelcontextprotocol/server-filesystem $ALLOWED_DIRS" \
  --port 8901 \
  --outputTransport streamableHttp &
FS_PID=$!

echo "Starting MCP memory server on :8902..."
npx -y supergateway \
  --stdio "npx -y @modelcontextprotocol/server-memory" \
  --port 8902 \
  --outputTransport streamableHttp &
MEM_PID=$!

echo "MCP servers running (fs PID=$FS_PID  mem PID=$MEM_PID)"
echo ""
echo "Open WebUI → Admin Panel → Tools → Add Tool Server:"
echo "  http://host.docker.internal:8901/mcp"
echo "  http://host.docker.internal:8902/mcp"

trap "kill $FS_PID $MEM_PID 2>/dev/null; exit 0" INT TERM
wait
