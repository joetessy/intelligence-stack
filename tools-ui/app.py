#!/usr/bin/env python3
"""
app.py — OCR web UI for the Intelligence Stack.

Two tabs, served on 0.0.0.0:5005 (browser: http://localhost:5005):
  * OCR                       — image/PDF -> text or Markdown (Baidu Unlimited-OCR)
  * Sheet music -> MuseScore  — image/PDF -> .mscz (homr, via the musescore CLI)

Host-native (not Docker). The OCR model is loaded lazily, kept WARM between
requests, and auto-unloaded after idle (TOOLS_UI_IDLE_UNLOAD seconds, default
900; 0 = never) to free ~13 GB — the same idea as llama-swap's TTL. Set
TOOLS_UI_PRELOAD=1 to warm it at startup. Music runs by shelling out to
~/Projects/musescore/omr/sheet2mscz, so the music tooling stays localized.

Run:  ~/Projects/intelligence-stack/ocr/.venv/bin/python tools-ui/app.py
"""
from __future__ import annotations

import gc
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # stay offline

HOME = Path.home()
OCR_DIR = HOME / "Projects" / "intelligence-stack" / "ocr"
SHEET2MSCZ = HOME / "Projects" / "musescore" / "omr" / "sheet2mscz"
PORT = int(os.environ.get("TOOLS_UI_PORT", "5005"))
IDLE_UNLOAD = float(os.environ.get("TOOLS_UI_IDLE_UNLOAD", "900"))  # seconds; 0 = never
UPLOAD_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".pdf"]

# Reuse the OCR CLI as a library — the OCR venv already has torch/transformers/fitz.
sys.path.insert(0, str(OCR_DIR))
import ocr as ocrmod  # noqa: E402
import gradio as gr  # noqa: E402


class OCRModel:
    """Lazy-load, keep warm, auto-unload after idle. Thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model = None
        self._tok = None
        self._last_used = 0.0
        self._loading = False
        self._busy = 0  # in-flight requests; janitor must not unload while > 0
        threading.Thread(target=self._janitor, daemon=True).start()

    def get(self, progress=None):
        with self._lock:
            if self._model is None:
                self._loading = True
                try:
                    if progress:
                        progress(0.15, desc="Loading OCR model (first run ~40s)…")
                    dev, dtype = ocrmod.pick_device(None)
                    self._model, self._tok = ocrmod.load_model(ocrmod.DEFAULT_MODEL_DIR, dev, dtype)
                finally:
                    self._loading = False
            self._last_used = time.monotonic()
            self._busy += 1  # only after a successful load; a failed load leaves 0
            return self._model, self._tok

    def done(self) -> None:
        with self._lock:
            self._busy = max(0, self._busy - 1)  # max(): harmless if get() raised
            self._last_used = time.monotonic()
        _empty_mps_cache()

    def status(self) -> str:
        if self._loading:
            return "loading"
        return "warm" if self._model is not None else "idle"

    def _janitor(self) -> None:
        while True:
            time.sleep(30)
            if IDLE_UNLOAD <= 0:
                continue
            with self._lock:
                idle = self._busy == 0 and self._model is not None and (time.monotonic() - self._last_used) > IDLE_UNLOAD
                if idle:
                    self._model = None
                    self._tok = None
                    _empty_mps_cache()
                    gc.collect()


def _empty_mps_cache() -> None:
    try:
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass


OCR = OCRModel()


def _status_badge() -> str:
    dot = {"warm": "🟢", "loading": "🟡", "idle": "⚪"}[OCR.status()]
    label = {"warm": "warm (fast)", "loading": "loading…", "idle": "idle (first run ~40s)"}[OCR.status()]
    return f"**OCR model:** {dot} {label}"


def run_ocr(file_path, task, mode, pages, dpi, progress=gr.Progress()):
    if not file_path:
        return "*Upload an image or PDF first.*", "", None
    p = Path(file_path)
    # get() inside the try so `finally: OCR.done()` always rebalances _busy.
    try:
        model, tok = OCR.get(progress)
        progress(0.6, desc="Reading…")
        if p.suffix.lower() == ".pdf":
            with tempfile.TemporaryDirectory() as td:
                imgs = ocrmod.pdf_to_images(p, Path(td), int(dpi), pages.strip() or None)
                prompt = "<image>" + ocrmod.MULTI_TASKS[task]
                text = ocrmod.run_multi(model, tok, imgs, prompt, 32768, None)
        else:
            prompt = "<image>" + ocrmod.TASKS[task]
            text = ocrmod.run_single(model, tok, p, prompt, mode, 32768, None)
        text = ocrmod.clean_output(text)
    except Exception as e:  # surface errors in the UI rather than 500ing
        return f"**Error:** {e}", str(e), None
    finally:
        OCR.done()
    # Write a downloadable copy next to Gradio's temp area.
    suffix = ".md" if task == "parse" else ".txt"
    tmp = tempfile.NamedTemporaryFile("w", suffix=f"-{p.stem}{suffix}", delete=False, encoding="utf-8")
    tmp.write(text)
    tmp.close()
    return (text or "*(no text found)*"), text, tmp.name


def run_score(file_path, progress=gr.Progress()):
    if not file_path:
        return None, None, "Upload a sheet-music image or PDF first."
    if not SHEET2MSCZ.exists():
        return None, None, "Score tool not installed — run `musescore/omr/setup.sh`."
    progress(0.2, desc="Recognizing notation (homr)…")
    outdir = Path(tempfile.mkdtemp(prefix="omr-"))
    try:
        subprocess.run(
            [str(SHEET2MSCZ), file_path, "--out", str(outdir)],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        return None, None, f"**Error:**\n```\n{(e.stderr or e.stdout or '').strip()[-1500:]}\n```"
    files = sorted(outdir.glob("*.mscz")) + sorted(outdir.glob("*.musicxml"))
    teaser = next(iter(sorted(outdir.glob("*_teaser.png"))), None)
    if not files:
        return None, (str(teaser) if teaser else None), "No output — the image may be too low-res or not notation."
    note = ("**Done.** Download the `.mscz` and open it in MuseScore to proofread — "
            "accidentals first. **Maqam microtones are dropped and must be added by hand.** "
            "The preview shows what homr recognized.")
    return [str(f) for f in files], (str(teaser) if teaser else None), note


CSS = """
.gradio-container { max-width: 1080px !important; margin: 0 auto !important; }
#hdr h1 { margin-bottom: 2px; }
#badge { font-size: 0.9em; opacity: 0.9; }
footer { visibility: hidden; }
"""

with gr.Blocks(title="OCR — Intelligence Stack", theme=gr.themes.Soft(), css=CSS) as demo:
    with gr.Column(elem_id="hdr"):
        gr.Markdown("# OCR")
        gr.Markdown("Local & offline. **OCR reads the _text_; the score tab reads the _notes_.**")
    badge = gr.Markdown(_status_badge(), elem_id="badge")
    gr.Timer(3.0).tick(_status_badge, outputs=badge)

    with gr.Tabs():
        with gr.Tab("OCR — text from images / PDFs"):
            with gr.Row():
                with gr.Column(scale=2):
                    ocr_in = gr.File(label="Image or PDF", file_types=UPLOAD_EXTS, type="filepath")
                    with gr.Row():
                        ocr_task = gr.Radio(["parse", "text"], value="parse", label="Output",
                                            info="parse = layout Markdown · text = plain text")
                        ocr_mode = gr.Radio(["gundam", "base"], value="gundam", label="Mode",
                                            info="gundam = dense/small text · base = faster")
                    with gr.Accordion("PDF options", open=False):
                        ocr_pages = gr.Textbox(label="Pages", placeholder="all — e.g. 1-5 or 1,3,7", value="")
                        ocr_dpi = gr.Slider(120, 400, value=200, step=20, label="Rasterization DPI")
                    ocr_btn = gr.Button("Run OCR", variant="primary")
                with gr.Column(scale=3):
                    with gr.Tabs():
                        with gr.Tab("Rendered"):
                            ocr_md = gr.Markdown()
                        with gr.Tab("Raw"):
                            ocr_raw = gr.Textbox(label="Result", lines=20, show_copy_button=True)
                    ocr_file = gr.File(label="Download result")
            # concurrency_id "heavy" is shared with the score tab: Gradio's
            # default_concurrency_limit is PER-LISTENER, so without a shared
            # group a 13 GB OCR inference and a homr run could overlap.
            ocr_btn.click(run_ocr, [ocr_in, ocr_task, ocr_mode, ocr_pages, ocr_dpi],
                          [ocr_md, ocr_raw, ocr_file],
                          concurrency_id="heavy", concurrency_limit=1)

        with gr.Tab("Sheet music → MuseScore"):
            with gr.Row():
                with gr.Column(scale=2):
                    sc_in = gr.File(label="Sheet-music image or PDF", file_types=UPLOAD_EXTS, type="filepath")
                    sc_btn = gr.Button("Recognize → MuseScore", variant="primary")
                    sc_msg = gr.Markdown()
                with gr.Column(scale=3):
                    sc_preview = gr.Image(label="What homr recognized (preview)", type="filepath", height=340)
                    sc_out = gr.File(label="Download (.mscz / .musicxml)", file_count="multiple")
            sc_btn.click(run_score, [sc_in], [sc_out, sc_preview, sc_msg],
                         concurrency_id="heavy", concurrency_limit=1)

    gr.Markdown(
        "_OCR: Baidu Unlimited-OCR (MPS/fp32), warm-loaded. Scores: homr → MuseScore. "
        "Model auto-unloads after 15 min idle. For multi-page scores with a correction UI, use **Audiveris**._"
    )

if __name__ == "__main__":
    if os.environ.get("TOOLS_UI_PRELOAD") == "1":
        threading.Thread(target=lambda: OCR.get(), daemon=True).start()
    # 0.0.0.0 so the dashboard container's health check can reach it via
    # host.docker.internal; the browser still uses http://localhost:5005.
    demo.queue(default_concurrency_limit=1).launch(server_name="0.0.0.0", server_port=PORT)
