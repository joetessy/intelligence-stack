#!/usr/bin/env bash
# =============================================================================
# setup.sh — provision the Unlimited-OCR tool (Apple Silicon / MPS).
#
# Creates a self-contained Python 3.12 venv (the model requires >=3.12,<3.13),
# installs the pinned PyTorch/transformers stack, and downloads the model
# weights + MPS-patched modeling code (~6.7 GB) from the community fork.
#
#   Model   : sabafallah/Unlimited-OCR-Universal  (MIT; unchanged Baidu weights,
#             code patched for CUDA/MPS/CPU + forced fp32 on MPS)
#   Weights : ~/models/Unlimited-OCR-Universal    (override with OCR_MODEL_DIR)
#   Runtime : ~13 GB unified RAM in fp32 while a job runs
#
# Re-runnable: each step is skipped if already done. First run is download-bound
# (~10-15 min on a fast link: ~2 GB of wheels + 6.7 GB of weights).
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")"

MODEL_REPO="sabafallah/Unlimited-OCR-Universal"
MODEL_DIR="${OCR_MODEL_DIR:-$HOME/models/Unlimited-OCR-Universal}"

command -v uv >/dev/null || { echo "uv not found — 'brew install uv'" >&2; exit 1; }

echo "==> [1/3] Python 3.12 venv (.venv)"
uv venv --python 3.12 .venv

echo "==> [2/3] install pinned deps (torch / transformers / pymupdf …)"
VIRTUAL_ENV="$PWD/.venv" uv pip install -r requirements.txt

echo "==> [3/3] download model -> $MODEL_DIR"
if [[ -f "$MODEL_DIR/model-00001-of-000001.safetensors" ]]; then
  echo "    weights already present — skipping."
else
  HF="$(command -v hf || command -v huggingface-cli || true)"
  [[ -n "$HF" ]] || { echo "hf CLI not found — 'pip install huggingface_hub'" >&2; exit 1; }
  echo "    ~6.7 GB from $MODEL_REPO (first run only)…"
  "$HF" download "$MODEL_REPO" --local-dir "$MODEL_DIR"
fi

chmod +x ocr.py
echo
echo "Done. Quick check:  ./ocr.py --help"
echo "Put 'ocr' on PATH:  ln -sf \"$PWD/../bin/ocr\" ~/.local/bin/ocr"
