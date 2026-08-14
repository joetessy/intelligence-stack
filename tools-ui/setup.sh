#!/usr/bin/env bash
# =============================================================================
# setup.sh — provision the "OCR & Scores" web UI (tools-ui) on port 5005.
#
# Reuses the OCR venv (ocr/.venv) — which already has torch/transformers/pymupdf
# — and just adds Gradio. The Score tab shells out to musescore/omr/sheet2mscz,
# so the music tooling stays localized to the musescore project.
#
# Prereqs: run ocr/setup.sh first; musescore/omr/setup.sh for the Score tab.
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

OCR_VENV="$HOME/Projects/intelligence-stack/ocr/.venv"
command -v uv >/dev/null || { echo "uv not found — 'brew install uv'" >&2; exit 1; }
[[ -x "$OCR_VENV/bin/python" ]] || { echo "OCR venv missing — run ocr/setup.sh first" >&2; exit 1; }

echo "==> installing gradio into the OCR venv"
# Pin gradio<6 and huggingface-hub<1.0: gradio 6 pulls hub 1.x, which breaks
# transformers 4.57.1 (needs hub <1.0) and thus the OCR model load. gradio 5.x
# coexists with hub 0.36 + transformers 4.57.
VIRTUAL_ENV="$OCR_VENV" uv pip install 'gradio<6' 'huggingface-hub<1.0'

[[ -x "$HOME/Projects/musescore/omr/.venv/bin/python" ]] || \
  echo "note: run musescore/omr/setup.sh to enable the Sheet-music tab"

echo
echo "Done. Start it:"
echo "  \"$OCR_VENV/bin/python\" \"$PWD/app.py\"        # -> http://localhost:5005"
echo "Auto-start on login:"
echo "  cp ../com.intelligence-stack.tools-ui.plist ~/Library/LaunchAgents/"
echo "  launchctl load ~/Library/LaunchAgents/com.intelligence-stack.tools-ui.plist"
