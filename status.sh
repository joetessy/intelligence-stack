#!/bin/bash
# =============================================================================
# Intelligence Stack — Status Dashboard
# Shows health of all services, loaded models, and memory usage
# =============================================================================

BOLD='\033[1m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
RESET='\033[0m'

ok() { echo -e "  ${GREEN}●${RESET} $1"; }
fail() { echo -e "  ${RED}●${RESET} $1"; }
warn() { echo -e "  ${YELLOW}●${RESET} $1"; }

echo ""
echo -e "${BOLD}Intelligence Stack Status${RESET}"
echo -e "${DIM}$(date '+%Y-%m-%d %H:%M:%S')${RESET}"
echo ""

# ---------------------------------------------------------------------------
# Docker services
# ---------------------------------------------------------------------------
echo -e "${BOLD}Docker Services${RESET}"
for svc in open-webui searxng flaresolverr faster-whisper openedai-speech; do
    status=$(docker inspect -f '{{.State.Status}}' "$svc" 2>/dev/null)
    if [ "$status" = "running" ]; then
        ok "$svc"
    elif [ -n "$status" ]; then
        fail "$svc ($status)"
    else
        fail "$svc (not found)"
    fi
done
echo ""

# ---------------------------------------------------------------------------
# MLX-LM server
# ---------------------------------------------------------------------------
echo -e "${BOLD}MLX-LM Server${RESET} ${DIM}(port 5001)${RESET}"
MLX_RESPONSE=$(curl -s --connect-timeout 2 http://localhost:5001/v1/models 2>/dev/null)
if [ $? -eq 0 ] && echo "$MLX_RESPONSE" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    ok "Running"
    MODELS=$(echo "$MLX_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('data', []):
    name = m['id'].replace('mlx-community/', '')
    print(f'    {name}')
" 2>/dev/null)
    echo -e "  ${DIM}Available models:${RESET}"
    echo "$MODELS"
else
    fail "Not running"
    echo -e "  ${DIM}Start with: ./mlx-server.sh${RESET}"
fi
echo ""

# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
echo -e "${BOLD}Ollama${RESET} ${DIM}(port 11434)${RESET}"
OLLAMA_PS=$(curl -s --connect-timeout 2 http://localhost:11434/api/ps 2>/dev/null)
if [ $? -eq 0 ]; then
    ok "Running"
    LOADED=$(echo "$OLLAMA_PS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])
if not models:
    print('    (no models loaded)')
else:
    for m in models:
        size_gb = m.get('size_vram', 0) / 1e9
        print(f'    {m[\"name\"]} ({size_gb:.1f}GB)')
" 2>/dev/null)
    echo -e "  ${DIM}Loaded in memory:${RESET}"
    echo "$LOADED"

    INSTALLED=$(ollama list 2>/dev/null | tail -n +2 | awk '{printf "    %-30s %s\n", $1, $3" "$4}')
    echo -e "  ${DIM}Installed:${RESET}"
    echo "$INSTALLED"
else
    fail "Not running"
fi
echo ""

# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------
echo -e "${BOLD}Memory${RESET}"
python3 -c "
import subprocess, json

# Get memory pressure
result = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
total_bytes = int(result.stdout.strip())
total_gb = total_bytes / (1024**3)

# Get memory usage from vm_stat
result = subprocess.run(['vm_stat'], capture_output=True, text=True)
lines = result.stdout.strip().split('\n')
page_size = 16384  # Apple Silicon default
stats = {}
for line in lines[1:]:
    if ':' in line:
        key, val = line.split(':')
        val = val.strip().rstrip('.')
        try:
            stats[key.strip()] = int(val)
        except ValueError:
            pass

used_pages = stats.get('Pages active', 0) + stats.get('Pages wired down', 0) + stats.get('Pages speculative', 0)
used_gb = (used_pages * page_size) / (1024**3)
free_gb = total_gb - used_gb

print(f'  Total: {total_gb:.0f}GB unified memory')
print(f'  Used:  {used_gb:.1f}GB')
print(f'  Free:  {free_gb:.1f}GB (approx)')
" 2>/dev/null
echo ""

# ---------------------------------------------------------------------------
# Quick links
# ---------------------------------------------------------------------------
echo -e "${BOLD}Quick Links${RESET}"
echo -e "  Open WebUI    ${CYAN}http://localhost:3000${RESET}"
echo -e "  SearXNG       ${CYAN}http://localhost:8080${RESET}"
echo -e "  MLX-LM API    ${CYAN}http://localhost:5001/v1/models${RESET}"
echo -e "  Ollama API    ${CYAN}http://localhost:11434${RESET}"
echo -e "  MLX logs      ${DIM}/tmp/mlx-server.log${RESET}"
echo ""
