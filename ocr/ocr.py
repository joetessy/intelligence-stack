#!/usr/bin/env python3
"""
ocr.py — Unlimited-OCR (Baidu) document OCR for the Intelligence Stack.

Runs baidu/Unlimited-OCR — a 3B DeepSeek-V2 + SAM/CLIP vision-language OCR model
(successor to DeepSeek-OCR) — on Apple Silicon via the MPS backend, using the
community "Universal" fork that patches the reference code for MPS/CPU.

This model is NOT a GGUF and cannot be served by llama-swap: it ships custom
`trust_remote_code` modeling code, not a llama.cpp architecture. So it lives here
as a stand-alone on-demand CLI with its own Python 3.12 venv (see setup.sh).

Why fp32 on MPS: bf16 rounding is amplified by the MoE router and decode drifts
into repeated garbage on Apple Silicon; fp32 (~13 GB RAM) is the correct choice.

Usage:
  ocr scan.jpg                    # parse one image -> Markdown on stdout
  ocr scan.jpg --task text        # plain-text extraction (no layout)
  ocr scan.png --mode base        # single-scale (faster; clean pages)
  ocr report.pdf                  # multi-page PDF -> one-shot parse
  ocr report.pdf --pages 1-5      # subset of pages (--dpi 200 default)
  ocr a.png b.png c.png           # several images -> one multi-page parse
  ocr scan.jpg --save out/        # also write result.md (+ boxed image)
Run `ocr --help` for all flags.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

# Must be set BEFORE torch is imported: unsupported MPS ops fall back to CPU
# instead of raising. torch is imported lazily inside the functions below.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

DEFAULT_MODEL_DIR = Path(
    os.environ.get("OCR_MODEL_DIR", Path.home() / "models" / "Unlimited-OCR-Universal")
)

# mode name -> (base_size, image_size, crop_mode)
MODES = {
    "gundam": (1024, 640, True),   # hi-res tiling — best for dense / small text
    "base":   (1024, 1024, False), # single-scale — faster, good for clean pages
}
# task -> the instruction that follows the <image> token
TASKS = {
    "parse": "document parsing.",  # layout-aware Markdown + bounding boxes
    "text":  "Free OCR.",          # plain text only, no layout
}
# task -> multi-page instruction
MULTI_TASKS = {
    "parse": "Multi page parsing.",
    "text":  "Free OCR.",
}


def _as_text(res) -> str:
    """The custom infer methods return either a str or a (text, tokens) tuple
    depending on version; normalise both to a string."""
    if isinstance(res, (tuple, list)):
        res = res[0] if res else ""
    if res is None:
        return ""
    return res if isinstance(res, str) else str(res)


_DET_RE = re.compile(r"<\|det\|>.*?<\|/det\|>", re.DOTALL)
_TAG_RE = re.compile(r"<\|/?(?:ref|det)\|>")


def clean_output(text: str) -> str:
    """Strip the model's <|det|>…<|/det|> grounding tokens, leaving clean
    text/Markdown. Pass --raw to keep them (e.g. to recover bounding boxes)."""
    text = _DET_RE.sub("", text)
    text = _TAG_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def parse_pages(spec: str | None, n: int) -> list[int]:
    """'1-5' / '1,3,7' / '2' -> 0-based page indices (default: all)."""
    if not spec:
        return list(range(n))
    out: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a) - 1, int(b)))
        else:
            out.append(int(part) - 1)
    return [i for i in out if 0 <= i < n]


def pdf_to_images(pdf_path: Path, out_dir: Path, dpi: int, pages_spec: str | None) -> list[str]:
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    idxs = parse_pages(pages_spec, doc.page_count)
    paths: list[str] = []
    for i in idxs:
        pix = doc[i].get_pixmap(dpi=dpi)
        p = out_dir / f"page_{i + 1:04d}.png"
        pix.save(p)
        paths.append(str(p))
    doc.close()
    if not paths:
        sys.exit("no pages selected")
    return paths


def pick_device(override: str | None):
    import torch

    if override:
        dev = override
    elif torch.cuda.is_available():
        dev = "cuda"
    elif torch.backends.mps.is_available():
        dev = "mps"
    else:
        dev = "cpu"
    # bf16 only on CUDA; fp32 everywhere else (bf16 drifts on MPS).
    dtype = torch.bfloat16 if dev == "cuda" else torch.float32
    return dev, dtype


def load_model(model_dir: Path, device: str, dtype):
    from transformers import AutoModel, AutoTokenizer

    if not model_dir.exists():
        sys.exit(f"model not found at {model_dir}\nRun ocr/setup.sh to download it (~6.7 GB).")
    tok = AutoTokenizer.from_pretrained(str(model_dir), trust_remote_code=True)
    model = AutoModel.from_pretrained(
        str(model_dir),
        trust_remote_code=True,
        use_safetensors=True,
        dtype=dtype,
        attn_implementation="eager",  # flash-attn is unavailable on MPS
    )
    return model.eval().to(device), tok


def run_single(model, tok, image: Path, prompt: str, mode: str, max_length: int, save_dir: Path | None) -> str:
    base_size, image_size, crop_mode = MODES[mode]
    common = dict(
        tokenizer=tok,
        prompt=prompt,
        image_file=str(image),
        base_size=base_size,
        image_size=image_size,
        crop_mode=crop_mode,
        max_length=max_length,
        no_repeat_ngram_size=35,  # guards against MoE repeat-garbage
        ngram_window=128,
        temperature=0.0,
    )
    # infer() unconditionally does os.makedirs(output_path), so it must be a real
    # directory even when we only want the text back (hence the temp dir).
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        model.infer(output_path=str(save_dir), save_results=True, **common)
        md = save_dir / "result.md"
        return md.read_text() if md.exists() else ""
    with tempfile.TemporaryDirectory() as td:
        return _as_text(model.infer(output_path=td, eval_mode=True, **common))


def run_multi(model, tok, images: list[str], prompt: str, max_length: int, save_dir: Path | None) -> str:
    def _call(out_path: str) -> str:
        return _as_text(
            model.infer_multi(
                tokenizer=tok,
                prompt=prompt,
                image_files=images,
                output_path=out_path,
                image_size=1024,
                max_length=max_length,
                no_repeat_ngram_size=35,
                ngram_window=1024,
                temperature=0.0,
            )
        )

    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)
        text = _call(str(save_dir))
        (save_dir / "result.md").write_text(text)
        return text
    with tempfile.TemporaryDirectory() as td:
        return _call(td)


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="ocr",
        description="Unlimited-OCR document OCR (Apple Silicon / MPS).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("inputs", nargs="+", help="image and/or PDF file(s)")
    ap.add_argument("--task", choices=TASKS, default="parse",
                    help="parse = layout Markdown (default); text = plain text")
    ap.add_argument("--mode", choices=MODES, default="gundam",
                    help="gundam = hi-res tiling (default); base = single-scale (faster)")
    ap.add_argument("--prompt", help="override the full prompt (include a leading <image> token)")
    ap.add_argument("--pages", help="PDF pages, e.g. '1-5' or '1,3,7' (default: all)")
    ap.add_argument("--dpi", type=int, default=200, help="PDF rasterization DPI (default 200)")
    ap.add_argument("--max-length", type=int, default=32768, help="max output tokens (default 32768)")
    ap.add_argument("--save", metavar="DIR", help="write result.md (+ boxed image for single) to DIR")
    ap.add_argument("--model-dir", default=str(DEFAULT_MODEL_DIR), help="model directory")
    ap.add_argument("--device", choices=["mps", "cpu", "cuda"], help="override auto device selection")
    ap.add_argument("--raw", action="store_true", help="keep the model's <|det|> grounding/bbox tokens")
    args = ap.parse_args()

    save_dir = Path(args.save).expanduser() if args.save else None
    model_dir = Path(args.model_dir).expanduser()

    inputs = [Path(p).expanduser() for p in args.inputs]
    for p in inputs:
        if not p.exists():
            sys.exit(f"not found: {p}")

    device, dtype = pick_device(args.device)
    print(f"[ocr] device={device} dtype={str(dtype).rsplit('.', 1)[-1]} "
          f"model={model_dir.name}", file=sys.stderr)
    if not model_dir.exists():
        sys.exit(f"model not found at {model_dir}\nRun ocr/setup.sh to download it (~6.7 GB).")

    # Rasterize + validate PDFs BEFORE the ~13 GB model load, so a bad --pages
    # spec or unreadable PDF fails in seconds instead of after the ~40 s load.
    is_pdf = len(inputs) == 1 and inputs[0].suffix.lower() == ".pdf"
    if is_pdf:
        mprompt = args.prompt or ("<image>" + MULTI_TASKS[args.task])
        with tempfile.TemporaryDirectory() as td:
            imgs = pdf_to_images(inputs[0], Path(td), args.dpi, args.pages)
            print(f"[ocr] {inputs[0].name}: {len(imgs)} page(s) @ {args.dpi} dpi", file=sys.stderr)
            model, tok = load_model(model_dir, device, dtype)
            text = run_multi(model, tok, imgs, mprompt, args.max_length, save_dir)
    elif len(inputs) > 1:
        mprompt = args.prompt or ("<image>" + MULTI_TASKS[args.task])
        with tempfile.TemporaryDirectory() as td:
            imgs: list[str] = []
            for k, p in enumerate(inputs):
                if p.suffix.lower() == ".pdf":
                    # Per-PDF subdir: pdf_to_images names pages page_NNNN.png,
                    # so a shared dir would collide across documents.
                    sub = Path(td) / f"doc_{k:03d}"
                    sub.mkdir()
                    pages = pdf_to_images(p, sub, args.dpi, args.pages)
                    print(f"[ocr] {p.name}: {len(pages)} page(s) @ {args.dpi} dpi", file=sys.stderr)
                    imgs.extend(pages)
                else:
                    imgs.append(str(p))
            model, tok = load_model(model_dir, device, dtype)
            text = run_multi(model, tok, imgs, mprompt, args.max_length, save_dir)
    else:
        prompt = args.prompt or ("<image>" + TASKS[args.task])
        model, tok = load_model(model_dir, device, dtype)
        text = run_single(model, tok, inputs[0], prompt, args.mode, args.max_length, save_dir)

    if not args.raw:
        text = clean_output(text)
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    if save_dir:
        print(f"[ocr] saved -> {save_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
