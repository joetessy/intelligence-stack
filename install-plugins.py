#!/usr/bin/env python3
"""
install-plugins.py — push the Python plugins under open-webui/ into Open WebUI.

Installs (or updates) every function in open-webui/functions/ and every tool
in open-webui/tools/. Idempotent: re-running it overwrites existing entries
with the on-disk content, so the canonical source is always the repo.

Env vars:
  OPEN_WEBUI_URL      base URL (default http://localhost:3000)
  OPENWEBUI_API_KEY   admin API key (required)

Plugin metadata is parsed from the file's leading docstring. Recognised keys:
  title:        human-readable name (defaults to file stem)
  description:  one-line summary (optional)

Functions named "strip_*", "always_*" or marked with `# global: true` in their
docstring are toggled on globally after install. Other functions are merely
created (you still need to enable them per-model in the UI). Tools are always
created in disabled state — enable per-model under Workspace → Models → Tools.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
FUNCTIONS_DIR = REPO_ROOT / "open-webui" / "functions"
TOOLS_DIR = REPO_ROOT / "open-webui" / "tools"

WEBUI_URL = os.environ.get("OPEN_WEBUI_URL", "http://localhost:3000").rstrip("/")
API_KEY = os.environ.get("OPENWEBUI_API_KEY", "")

GREEN, YELLOW, RED, DIM, NC = "\033[0;32m", "\033[1;33m", "\033[0;31m", "\033[2m", "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}✓{NC} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{NC} {msg}")


def err(msg: str) -> None:
    print(f"  {RED}✗{NC} {msg}")


def parse_metadata(content: str, fallback_id: str) -> tuple[str, str]:
    """Return (name, description) extracted from the file's leading docstring."""
    docstring_match = re.match(r'^\s*"""(.*?)"""', content, re.DOTALL)
    if not docstring_match:
        return fallback_id.replace("_", " ").title(), ""

    header = docstring_match.group(1)
    title_match = re.search(r"^\s*title:\s*(.+?)\s*$", header, re.MULTILINE)
    desc_match = re.search(r"^\s*description:\s*(.+?)\s*$", header, re.MULTILINE)
    name = title_match.group(1) if title_match else fallback_id.replace("_", " ").title()
    description = desc_match.group(1) if desc_match else ""
    return name, description


def http(method: str, path: str, body: dict | None = None) -> tuple[int, dict | None]:
    """Send a JSON request to Open WebUI. Returns (status_code, parsed_body_or_None)."""
    req = urllib.request.Request(
        f"{WEBUI_URL}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(body).encode() if body is not None else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else None
        except json.JSONDecodeError:
            return e.code, {"raw": raw.decode(errors="replace")}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {"error": str(e)}


def install_plugin(kind: str, file_path: Path) -> None:
    """Create-or-update a single plugin. kind is 'functions' or 'tools'."""
    plugin_id = file_path.stem.lower()
    if not plugin_id.replace("_", "").isalnum():
        warn(f"{file_path.name}: id '{plugin_id}' is not alphanumeric+underscore — skipping")
        return

    content = file_path.read_text()
    name, description = parse_metadata(content, plugin_id)

    body: dict = {
        "id": plugin_id,
        "name": name,
        "content": content,
        "meta": {"description": description, "manifest": {}},
    }
    if kind == "tools":
        body["access_grants"] = []

    status, _ = http("GET", f"/api/v1/{kind}/id/{plugin_id}")
    if status == 200:
        # Already exists — update in place.
        code, resp = http("POST", f"/api/v1/{kind}/id/{plugin_id}/update", body)
        if 200 <= code < 300:
            ok(f"updated {kind[:-1]}: {name} ({plugin_id})")
        else:
            err(f"update {plugin_id} failed: HTTP {code} {resp}")
        return

    # Doesn't exist — create.
    code, resp = http("POST", f"/api/v1/{kind}/create", body)
    if 200 <= code < 300:
        ok(f"created {kind[:-1]}: {name} ({plugin_id})")
        # For functions, optionally toggle on globally (filters that should
        # apply to every chat — e.g. strip_thinking_tags).
        if kind == "functions" and _is_global_function(plugin_id, content):
            tcode, _ = http("POST", f"/api/v1/functions/id/{plugin_id}/toggle")
            gcode, _ = http("POST", f"/api/v1/functions/id/{plugin_id}/toggle/global")
            if 200 <= tcode < 300 and 200 <= gcode < 300:
                ok(f"  enabled + globalised {plugin_id}")
            else:
                warn(f"  could not enable globally (toggle={tcode}, global={gcode})")
    else:
        err(f"create {plugin_id} failed: HTTP {code} {resp}")


def _is_global_function(plugin_id: str, content: str) -> bool:
    """Heuristic: filters whose name starts with strip_/always_ or carry an
    explicit `global: true` line in the docstring should be on by default."""
    if plugin_id.startswith(("strip_", "always_")):
        return True
    return bool(re.search(r"^\s*global:\s*true\s*$", content, re.IGNORECASE | re.MULTILINE))


def discover(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.py") if p.is_file() and not p.name.startswith("_"))


def main() -> int:
    if not API_KEY:
        err("OPENWEBUI_API_KEY not set — see provision-webui.sh for how it's resolved")
        return 1

    functions = discover(FUNCTIONS_DIR)
    tools = discover(TOOLS_DIR)

    if not functions and not tools:
        warn("no plugins found under open-webui/{functions,tools}/ — nothing to do")
        return 0

    print(f"Installing plugins into {WEBUI_URL}")
    if functions:
        print(f"{DIM}functions:{NC}")
        for f in functions:
            install_plugin("functions", f)
    if tools:
        print(f"{DIM}tools:{NC}")
        for t in tools:
            install_plugin("tools", t)

    return 0


if __name__ == "__main__":
    sys.exit(main())
