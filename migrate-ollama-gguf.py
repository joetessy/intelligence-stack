#!/usr/bin/env python3
"""
migrate-ollama-gguf.py — Map Ollama's blob store to named GGUF files for llama.cpp.

Ollama stores every model as content-addressed blobs. Each manifest lists layers;
the `application/vnd.ollama.image.model` layer is a standalone GGUF, and
`application/vnd.ollama.image.projector` is the vision mmproj GGUF.

This script reads all manifests and produces a name -> {gguf, mmproj} mapping.

Modes:
  (default)   dry run — print the plan, touch nothing
  --apply     clone blobs into DEST as named .gguf files via APFS clonefile
              (`cp -c`): instant, shares disk blocks, zero extra space, and
              leaves Ollama's store intact for verification/rollback.
  --move      with --apply, rename instead of clone (frees space immediately
              but breaks Ollama's content-addressed store — only use when
              abandoning Ollama).

DEST defaults to ~/models. Names are sanitized from the Ollama model tag.
"""
import json
import os
import re
import sys
import subprocess
from pathlib import Path

OLLAMA_ROOT = Path(os.path.expanduser("~/.ollama/models"))
MANIFESTS = OLLAMA_ROOT / "manifests"
BLOBS = OLLAMA_ROOT / "blobs"
DEST = Path(os.path.expanduser(os.environ.get("DEST", "~/models")))

MODEL_MEDIA = "application/vnd.ollama.image.model"
PROJ_MEDIA = "application/vnd.ollama.image.projector"


def blob_path(digest: str) -> Path:
    # digest looks like "sha256:abcd..." -> blob file "sha256-abcd..."
    return BLOBS / digest.replace(":", "-")


def sanitize(name: str) -> str:
    """Turn an Ollama model ref into a clean filename stem.
    e.g. 'library/qwen3.6/latest' -> 'qwen3.6'
         'hf.co/huihui-ai/Huihui-Qwen3.6-27B-abliterated-MTP-GGUF/latest'
           -> 'huihui-qwen3.6-27b-abliterated-mtp'
         'huihui_ai/gemma-4-abliterated/e2b' -> 'gemma-4-abliterated-e2b'
    """
    parts = name.split("/")
    tag = parts[-1]
    base = parts[-2] if len(parts) >= 2 else parts[0]
    # Drop noisy suffixes
    stem = base
    stem = re.sub(r"-?GGUF$", "", stem, flags=re.IGNORECASE)
    if tag and tag != "latest":
        stem = f"{stem}-{tag}"
    stem = stem.lower()
    stem = re.sub(r"[^a-z0-9._-]+", "-", stem).strip("-")
    return stem


def iter_manifests():
    """Yield (model_ref, manifest_dict) for every manifest file."""
    for path in MANIFESTS.rglob("*"):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if "layers" not in data:
            continue
        ref = str(path.relative_to(MANIFESTS))
        # ref is like registry.ollama.ai/library/qwen3.6/latest
        ref = ref.split("/", 1)[1] if "/" in ref else ref  # drop registry host
        yield ref, data


def human(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"


def build_plan():
    plan = []
    for ref, manifest in iter_manifests():
        model_layer = None
        proj_layer = None
        for layer in manifest["layers"]:
            mt = layer.get("mediaType", "")
            if mt == MODEL_MEDIA:
                model_layer = layer
            elif mt == PROJ_MEDIA:
                proj_layer = layer
        if not model_layer:
            print(f"  ! {ref}: no model layer (skipping)", file=sys.stderr)
            continue
        stem = sanitize(ref)
        entry = {
            "ref": ref,
            "stem": stem,
            "gguf_src": blob_path(model_layer["digest"]),
            "gguf_dst": DEST / f"{stem}.gguf",
            "gguf_size": model_layer.get("size", 0),
            "mmproj_src": blob_path(proj_layer["digest"]) if proj_layer else None,
            "mmproj_dst": (DEST / f"{stem}.mmproj.gguf") if proj_layer else None,
            "mmproj_size": proj_layer.get("size", 0) if proj_layer else 0,
        }
        plan.append(entry)
    plan.sort(key=lambda e: e["stem"])
    return plan


def verify_gguf(path: Path) -> bool:
    """Check the file begins with the GGUF magic."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"GGUF"
    except OSError:
        return False


def clone_or_move(src: Path, dst: Path, move: bool):
    """APFS clonefile via `cp -c` (default) or `mv` (--move). cp -c is instant,
    shares blocks (no extra disk), and keeps the source intact."""
    if move:
        subprocess.run(["mv", str(src), str(dst)], check=True)
    else:
        # -c forces clonefile and errors if the FS can't clone (so we never
        # silently fall back to a slow full-byte copy).
        subprocess.run(["cp", "-c", str(src), str(dst)], check=True)


def main():
    apply = "--apply" in sys.argv
    do_move = "--move" in sys.argv

    if not MANIFESTS.exists():
        print(f"ERROR: {MANIFESTS} not found — is Ollama installed?", file=sys.stderr)
        sys.exit(1)

    plan = build_plan()
    if not plan:
        print("No models found.", file=sys.stderr)
        sys.exit(1)

    mode = ("MOVE" if do_move else "CLONE (cp -c)") if apply else "DRY RUN"
    print(f"\n=== Ollama → GGUF migration plan ({mode}) ===")
    print(f"Destination: {DEST}\n")
    total = 0
    issues = 0
    for e in plan:
        total += e["gguf_size"] + e["mmproj_size"]
        src_ok = e["gguf_src"].exists()
        magic_ok = verify_gguf(e["gguf_src"]) if src_ok else False
        flag = "ok" if (src_ok and magic_ok) else "MISSING/BAD"
        if flag != "ok":
            issues += 1
        vis = "  +vision mmproj" if e["mmproj_src"] else ""
        print(f"  [{flag:>11}] {e['ref']}")
        print(f"               -> {e['gguf_dst'].name}  ({human(e['gguf_size'])}){vis}")
        if e["mmproj_src"]:
            print(f"               -> {e['mmproj_dst'].name}  ({human(e['mmproj_size'])})")
    print(f"\n  Total: {len(plan)} models, {human(total)}")
    if issues:
        print(f"  WARNING: {issues} model(s) have a missing/non-GGUF blob — review before applying.", file=sys.stderr)

    if not apply:
        print("\nDry run only. Re-run with --apply (clone) or --apply --move to execute.")
        return

    if issues:
        print("\nRefusing to apply: resolve the missing/bad blobs first.", file=sys.stderr)
        sys.exit(1)

    DEST.mkdir(parents=True, exist_ok=True)
    verb = "move" if do_move else "clone"
    for e in plan:
        for src_key, dst_key in (("gguf_src", "gguf_dst"), ("mmproj_src", "mmproj_dst")):
            src = e[src_key]
            dst = e[dst_key]
            if not src:
                continue
            if dst.exists():
                print(f"  skip (exists): {dst.name}")
                continue
            print(f"  {verb}: {dst.name}")
            clone_or_move(src, dst, do_move)
    print("\nDone. Verify each model loads, then it's safe to remove Ollama.")


if __name__ == "__main__":
    main()
