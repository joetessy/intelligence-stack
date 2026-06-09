#!/bin/bash
# =============================================================================
# Intelligence Stack — backup
# Snapshots the open-webui-data Docker volume (chat history, knowledge bases,
# uploaded files, API keys, model configs) and the .env secrets.
#
# Output: ~/Documents/intelligence-stack-backups/YYYY-MM-DD-HHMM/
#
# Usage:
#   ./backup.sh                     one-shot backup
#   ./backup.sh --keep 7            keep last 7 backups, prune older
# =============================================================================

# NOTE: deliberately NOT using `set -e`. Docker Desktop on macOS sometimes
# returns "error waiting for container: unexpected EOF" even when the
# container's tar finished — set -e would abort the script and skip the
# verify step, leaving a silently corrupt archive on disk. We check each
# archive explicitly instead and treat the failed ones as failures.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/Documents/intelligence-stack-backups}"
STAMP="$(date +%Y-%m-%d-%H%M)"
DEST="$BACKUP_ROOT/$STAMP"
KEEP=0
FAILED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --keep) KEEP="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$BACKUP_ROOT" "$DEST"

GREEN='\033[0;32m'; RED='\033[0;31m'; YEL='\033[1;33m'; DIM='\033[2m'; NC='\033[0m'
ok()   { echo -e "  ${GREEN}✓${NC} $*"; }
warn() { echo -e "  ${YEL}⚠${NC} $*"; }
fail() { echo -e "  ${RED}✗${NC} $*"; FAILED=$((FAILED+1)); }

# Verify a tar.gz archive is fully readable end-to-end. Returns 0 on success.
verify_tarball() {
  local path="$1"
  tar -tzf "$path" > /dev/null 2>&1
}

# Snapshot a Docker named volume to a host-side tar.gz, with one retry on the
# infamous "error waiting for container: unexpected EOF" Docker-Desktop bug.
# Streams the tar over stdout so we never depend on a second bind-mount.
snapshot_volume() {
  local vol_short="$1" out_path="$2"
  local vol_full="intelligence-stack_$vol_short"

  if ! docker volume inspect "$vol_full" >/dev/null 2>&1; then
    warn "$vol_short not found — skipping"
    return 0
  fi

  for attempt in 1 2; do
    docker run --rm -i \
      -v "$vol_full:/data:ro" \
      alpine tar -C / -cz data > "$out_path" 2>/dev/null
    if verify_tarball "$out_path"; then
      ok "$vol_short → $(du -h "$out_path" | cut -f1)"
      return 0
    fi
    warn "$vol_short attempt $attempt produced unreadable tar — retrying"
    sleep 2
  done
  fail "$vol_short backup corrupt after 2 attempts (Docker hiccup)"
  rm -f "$out_path"
  return 1
}

echo "Backing up to $DEST"

# Pre-pull alpine so the first docker run doesn't race the image fetch.
docker image inspect alpine:latest >/dev/null 2>&1 || docker pull -q alpine:latest >/dev/null

snapshot_volume open-webui-data        "$DEST/open-webui-data.tar.gz"
snapshot_volume openedai-speech-voices "$DEST/openedai-speech-voices.tar.gz"
snapshot_volume openedai-speech-config "$DEST/openedai-speech-config.tar.gz"

# --- Secrets + configs -------------------------------------------------------
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  cp "$SCRIPT_DIR/.env" "$DEST/.env"
  chmod 600 "$DEST/.env"
  ok ".env saved"
fi
cp "$SCRIPT_DIR/docker-compose.yml" "$DEST/docker-compose.yml"
cp -R "$SCRIPT_DIR/searxng" "$DEST/searxng"
ok "compose + searxng config saved"

# --- Ollama model list (so a restore knows what to pull) ---------------------
if curl -sf --connect-timeout 2 http://localhost:11434/api/tags > "$DEST/ollama-models.json" 2>/dev/null; then
  ok "ollama-models.json saved"
fi

# --- Prune old backups -------------------------------------------------------
if [[ "$KEEP" -gt 0 ]]; then
  pruned=$(ls -1dt "$BACKUP_ROOT"/2*-*-*-* 2>/dev/null | tail -n +$((KEEP+1)))
  if [[ -n "$pruned" ]]; then
    echo -e "${DIM}Pruning backups older than the most recent $KEEP:${NC}"
    while IFS= read -r path; do
      rm -rf "$path"
      echo -e "  ${DIM}removed $(basename "$path")${NC}"
    done <<< "$pruned"
  fi
fi

echo ""
if [[ "$FAILED" -gt 0 ]]; then
  echo "Done with $FAILED failure(s). $(du -sh "$DEST" | cut -f1) in $DEST"
  exit 1
fi
echo "Done. $(du -sh "$DEST" | cut -f1) total in $DEST"
