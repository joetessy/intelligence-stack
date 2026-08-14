#!/bin/bash
# =============================================================================
# MLX-LM Server for Intelligence Stack
# Runs an OpenAI-compatible server that dynamically loads MLX models
#
# Start:  ./mlx-server.sh
# Stop:   Ctrl+C (or: launchctl unload ~/Library/LaunchAgents/com.intelligence-stack.mlx-server.plist)
# Test:   curl http://localhost:5001/v1/models
#
# Available models (pass as "model" in API requests):
#
#   Multimodal / general (DEFAULT)
#     mlx-community/Qwen3.6-27B-4bit              vision + text, 27B dense, ~15GB
#     mlx-community/Qwen3.6-27B-8bit              same model, higher quality, ~28GB
#     mlx-community/Qwen3.6-27B-OptiQ-4bit        OptiQ-optimised 4-bit quant
#
#   Fast chat (MoE — ~3B active params, very low latency)
#     mlx-community/Qwen3.6-35B-A3B-4bit          MULTIMODAL MoE, 35B/3B-active, ~22GB
#     mlx-community/Qwen3-30B-A3B-4bit            30B/3B-active text-only, ~16GB
#
#   Coding (prefer Qwen3-Coder; faster + better than Qwen2.5-Coder)
#     mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit   MoE coder, ~16GB
#     mlx-community/Qwen2.5-Coder-32B-Instruct-4bit     legacy dense coder
#
#   Big dense (slower but high quality)
#     mlx-community/Qwen3.6-35B-A3B-6bit          higher-quality 35B MoE, ~32GB
#     mlx-community/Qwen3.6-35B-A3B-8bit          same, 8-bit quant, ~40GB
#
# The server auto-swaps models based on the request.
# Only one model is loaded in memory at a time.
# =============================================================================

# Use python3.13 explicitly — mlx_lm is installed there, not in the
# Homebrew 3.14 that PATH might otherwise pick up.
PYBIN="$(command -v python3.13 || command -v python3)"

# mlx-lm version pin: 0.31.1
#   0.31.2 and 0.31.3 regress on multi-threaded GPU streams: every other
#   request raises "RuntimeError: There is no Stream(gpu, 0) in current
#   thread" from inside the HTTP server's per-request thread. 0.31.1 is the
#   last known-good. Reinstall with:
#     pip install "mlx-lm==0.31.1" "mlx==0.31.1" "mlx-metal==0.31.1"
EXPECTED_MLX_LM="0.31.1"
ACTUAL_MLX_LM="$("$PYBIN" -m pip show mlx-lm 2>/dev/null | awk '/^Version:/ {print $2}')"
if [[ "$ACTUAL_MLX_LM" != "$EXPECTED_MLX_LM" ]]; then
  echo "WARNING: mlx-lm $ACTUAL_MLX_LM installed; pinned version is $EXPECTED_MLX_LM" >&2
fi

# Notes on log noise:
#   The "BrokenPipeError: [Errno 32]" tracebacks in mlx-server.log are HARMLESS.
#   They come from Python's http.server printing when a client disconnects
#   mid-stream (common with TTS / cancellation in Open WebUI). They don't
#   indicate a problem with the server or the model.
#
# Qwen3.6 thinking-mode quirk (READ THIS if direct API calls return empty):
#   Qwen3.6 ships with chain-of-thought ENABLED by default. mlx_lm emits the
#   reasoning into a non-spec `reasoning` delta field (OpenAI standard is
#   `reasoning_content`). Net effect: a curl/Python client expecting the
#   regular `content` field sees an empty string until a real LOT of tokens
#   later when the model finally produces the final answer.
#     - Open WebUI: handled cleanly. Qwen3.6 also wraps reasoning in <think>
#       tags, and the strip_thinking_tags filter installed by provision-webui.sh
#       removes them before display + TTS.
#     - Direct API users: pass `chat_template_kwargs: {"enable_thinking": false}`
#       in each request, OR enable globally via --chat-template-args below.
#
# Tuning knobs (see `python3 -m mlx_lm server --help`):
#   --draft-model <small-model>     speculative decoding (~1.5-2× speed-up on
#                                   token-rich workloads — pair the 27B with a
#                                   2-4B draft of the same family)
#   --chat-template-args '{"enable_thinking":false}'
#                                   force-disable Qwen3 chain-of-thought
#                                   server-wide (faster, less verbose, but
#                                   you lose the reasoning trace)
#   --temp / --top-p / --top-k      sampling defaults (per-request overrides win)
#   --prompt-concurrency N          batch up to N prefills in parallel
#
# To turn on speculative decoding:
#   1. huggingface-cli download mlx-community/Qwen3.5-2B-4bit
#   2. Uncomment the --draft-model / --num-draft-tokens lines below.
#   Caveat: --draft-model pins the active model to --model (no dynamic swap).
# Speculative-decoding caveats (TESTED 2026-06-08):
#   1. mlx_lm 0.31.2 with --prompt-cache-size N uses ArraysCache, which is
#      NOT trimmable — required for spec-dec. Error at runtime:
#        "ValueError: Speculative decoding requires a trimmable prompt cache"
#   2. Qwen3.5-2B and Qwen3.6-27B have different tokenizers despite same
#      family. mlx_lm warns "Draft model tokenizer does not match model
#      tokenizer. Speculative decoding may not work as expected."
#   3. Combined, attempting spec-dec caused a Metal GPU timeout that crashed
#      the server (SIGABRT). KeepAlive would then restart-and-crash forever.
#   Wait for: mlx_lm to support QuantizedKVCache trimming + a Qwen3.5 draft
#   that ships with the Qwen3.6 tokenizer. Until then, leave it off.
# No --model on purpose: with a default model set, mlx_lm eagerly loads all
# ~15 GB at every launchd start (RunAtLoad + each KeepAlive crash-restart) and
# macOS just pages it out again while idle — pure boot I/O and swap churn that
# also risks Metal OOM alongside llama-swap's 18 GB chat models. Requests load
# their named model on demand; /v1/models still lists everything in the HF
# cache. All current clients (Open WebUI, dashboard, status.sh) name a model.
"$PYBIN" -m mlx_lm server \
  --prompt-cache-size 64 \
  --max-tokens 32768 \
  --host 0.0.0.0 \
  --port 5001 \
  --log-level INFO
