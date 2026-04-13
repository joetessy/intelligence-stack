"""
Open WebUI Filter: Strip Thinking Tags
=======================================
Strips <think>...</think> and <thinking>...</thinking> blocks from assistant
responses BEFORE they are displayed or sent to TTS.

This is critical for reasoning models (deepseek-r1, qwen3 with thinking, etc.)
that wrap chain-of-thought in these tags — without this filter, TTS speaks the
entire reasoning monologue instead of just the final answer.

How to install:
  Open WebUI → Admin Panel → Functions → [+] New Function → paste this file → Save
  Then toggle it enabled. It applies globally to all models.

The outlet() method intercepts every assistant message after generation,
before it reaches the UI renderer and TTS engine.
"""

import re
from pydantic import BaseModel

# Matches <think>...</think> and <thinking>...</thinking>
# Flags: DOTALL so . matches newlines, IGNORECASE for robustness
_THINK_RE = re.compile(
    r"<think(?:ing)?>\s*.*?\s*</think(?:ing)?>",
    re.DOTALL | re.IGNORECASE,
)


class Filter:
    class Valves(BaseModel):
        # No configurable options needed — filter is always-on when enabled.
        pass

    def __init__(self):
        self.valves = self.Valves()

    def outlet(self, body: dict, __user__: dict | None = None) -> dict:
        """
        Post-process assistant messages: remove thinking-tag blocks.
        Called for every response before display and TTS playback.
        """
        messages = body.get("messages", [])
        for msg in messages:
            if msg.get("role") == "assistant" and isinstance(msg.get("content"), str):
                cleaned = _THINK_RE.sub("", msg["content"]).strip()
                msg["content"] = cleaned
        return body
