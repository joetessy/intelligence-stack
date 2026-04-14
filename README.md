# Intelligence Stack

A fully self-hosted, offline-capable AI stack on Apple Silicon. No accounts, no cloud, no data leaving your machine.

## Prerequisites

- macOS with Apple Silicon (M-series chip)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com) installed natively
- Python 3.13+ with `mlx-lm` installed (`pip install mlx-lm`)

## Setup

```bash
# 1. Copy env file and fill in your secret keys
cp .env.example .env
# Generate keys with: openssl rand -hex 32

# 2. Start Docker services
docker compose up -d

# 3. MLX-LM starts automatically via LaunchAgent
#    Manual start if needed: ./mlx-server.sh

# 4. Open http://localhost:3000 and create an admin account

# 5. Check everything
./status.sh
```

The dashboard is at **http://localhost:3001**.

---

## UIs

| Interface | URL | Purpose |
|-----------|-----|---------|
| **Open WebUI** | http://localhost:3000 | Chat, RAG, voice, web search |
| **Dashboard** | http://localhost:3001 | Service health + model browser |
| **SearXNG** | http://localhost:8080 | Search engine (direct access) |
| **Open Terminal** | http://localhost:3000 | Web terminal (via Open WebUI sidebar) |

## Screenshots

| | |
|---|---|
| ![Open WebUI](docs/webui.png) | ![Dashboard](docs/dashboard.png) |
| **Open WebUI** — chat interface with all local models (Ollama + MLX) | **Dashboard** — live service health and model browser |
| ![SearXNG](docs/searchxng.png) | ![Status](docs/status_command.png) |
| **SearXNG** — self-hosted metasearch with category tabs | **`./status.sh`** — terminal health check |

---

## Architecture

```
Docker:
  Open WebUI (3000)  ----->  SearXNG (8080)  ----->  FlareSolverr (internal)
       |                         search engine         cloudflare bypass
       |
       +--->  Faster-Whisper (8765)    speech-to-text
       +--->  openedai-speech (8880)   text-to-speech
       +--->  Open Terminal (8888)     web terminal (shell access)

  Dashboard (3001)   health monitor for all services

Native on host:
  MLX-LM (5001)     Apple Silicon inference (OpenAI-compatible API)
  Ollama (11434)    GGUF models + embeddings

Optional (host-native):
  MCP Filesystem (8901)  file read/write for Open WebUI models
  MCP Memory (8902)      persistent knowledge graph for Open WebUI models
```

## Services

| Service | Purpose | Port |
|---------|---------|------|
| [Open WebUI](https://github.com/open-webui/open-webui) | Chat interface, RAG, tools | 3000 |
| Dashboard | Service health monitor + model browser | 3001 |
| [SearXNG](https://github.com/searxng/searxng) | Self-hosted metasearch (web grounding) | 8080 |
| [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) | Cloudflare bypass proxy for SearXNG | internal |
| [Faster-Whisper](https://github.com/fedirz/faster-whisper-server) | Local speech-to-text | 8765 |
| [openedai-speech](https://github.com/matatonic/openedai-speech) | Local Piper-based text-to-speech | 8880 |
| [Open Terminal](https://github.com/open-webui/open-terminal) | Web-based terminal with shell access | 8888 |
| [MLX-LM](https://github.com/ml-explore/mlx-lm) | Apple Silicon optimized inference (OpenAI-compatible API) | 5001 |
| [Ollama](https://ollama.com) | GGUF model inference + embeddings | 11434 |

---

## Web Search (SearXNG + Open WebUI)

SearXNG is a self-hosted metasearch engine that queries Brave, DuckDuckGo, Google, Bing, and others simultaneously and deduplicates the results. It runs entirely locally — no search query leaves your machine.

Open WebUI is wired directly to SearXNG via its internal Docker network (`searxng:8080`). When web search is active in a chat, Open WebUI sends the user's query to SearXNG's JSON API, injects the returned results into the model's context window, and the model answers with live web grounding.

**To use web search in a chat:**
1. Click the **+** icon in the message input bar
2. Toggle **Web Search** on
3. Ask anything — the model will search before answering and cite its sources

To enable web search by default for all chats: Admin Panel → Settings → Web Search → toggle on.

**Direct SearXNG access** at http://localhost:8080 gives you the full search UI with category tabs (General, Images, Videos, News, Science, Map) — useful for browsing results directly without going through a model.

---

## MLX-LM

MLX-LM runs as a native server on port 5001, providing an OpenAI-compatible API optimized for Apple Silicon. It dynamically swaps models based on the request — only one model is loaded in memory at a time.

Open WebUI connects to it as an OpenAI-compatible backend alongside Ollama. Both appear in the model selector — MLX models are prefixed with `mlx-community/`. Models are downloaded on first use and cached in `~/.cache/huggingface/hub/`.

Edit `mlx-server.sh` to change the default model or server options. The LaunchAgent starts the server automatically on login.

### Memory management

Apple Silicon uses unified memory shared between MLX and Ollama. Large models cannot run simultaneously. Ollama auto-unloads models after 5 minutes of inactivity (configured in `~/.ollama/config.json`). MoE (mixture-of-experts) models use significantly less memory than their parameter count suggests.

---

## Configuration

| File | Purpose |
|------|---------|
| `.env` | Secret keys (gitignored) |
| `.env.example` | Template for `.env` |
| `docker-compose.yml` | Docker service definitions |
| `searxng/settings.yml` | SearXNG engines, timeouts, proxy config |
| `mlx-server.sh` | MLX-LM server startup script |
| `mcp-servers.sh` | MCP tool servers for Open WebUI (optional) |
| `provision-webui.sh` | Registers MCP servers and Open Terminal with Open WebUI |
| `status.sh` | Stack health dashboard |
| `pin-embeddings.sh` | Pins an Ollama embedding model in memory for RAG |

### Environment variables

| Variable | Purpose |
|----------|---------|
| `WEBUI_SECRET_KEY` | Open WebUI JWT signing key |
| `SEARXNG_SECRET` | SearXNG CSRF protection key |
| `OPEN_TERMINAL_API_KEY` | Bearer key securing the Open Terminal server |

### LaunchAgents (auto-start on login)

| Plist | Purpose |
|-------|---------|
| `~/Library/LaunchAgents/com.intelligence-stack.mlx-server.plist` | MLX-LM server on port 5001 |
| `~/Library/LaunchAgents/com.intelligence-stack.pin-embeddings.plist` | Pin embedding model in Ollama |
| `~/Library/LaunchAgents/com.intelligence-stack.mcp-servers.plist` | MCP tool servers on ports 8901/8902 (optional) |

---

## Commands

```bash
# Start/stop Docker services
docker compose up -d
docker compose down

# Stack status (all services, models, memory)
./status.sh

# Restart a single service
docker compose restart open-webui

# Tail logs
docker compose logs open-webui -f

# MLX-LM logs
tail -f /tmp/mlx-server.log

# Manually start/stop MLX-LM server
./mlx-server.sh
launchctl unload ~/Library/LaunchAgents/com.intelligence-stack.mlx-server.plist

# Update all Docker images
docker compose pull && docker compose up -d
```

---

## Open Terminal

Open Terminal is a web-based shell that runs inside Docker and connects to Open WebUI. It gives models (and you) a real terminal in the browser.

It starts automatically with `docker compose up -d` and is registered with Open WebUI by `./provision-webui.sh`. No manual setup needed beyond that.

Access it via the **terminal icon** in the Open WebUI sidebar. It is secured with a Bearer key (`OPEN_TERMINAL_API_KEY` in `.env`).

The dashboard shows its live health status and latency.

### Usage examples

**As a user** — click the terminal icon in the Open WebUI sidebar to get a live shell:

```bash
# You're now in a bash session inside the open-terminal container
ls ~/Projects
docker ps
htop
```

**Via a model** — ask the model to run commands for you (requires terminal access enabled for the model):

```
Run `docker ps` and tell me which containers are currently running.
```
```
Check disk usage with df -h and summarise the results.
```
```
List running processes sorted by memory usage.
```

The terminal runs inside Docker but has access to the host via `host.docker.internal`.

---

## MCP Tool Servers (optional)

MCP (Model Context Protocol) servers give models in Open WebUI the ability to take real actions — reading and writing files, maintaining persistent memory across conversations.

Two servers are included, both **off by default**. Enable them when you want models to access your local filesystem or remember things between chats.

**Prerequisite:** Node.js must be installed (`brew install node`).

### Setup

```bash
# Start the servers (foreground — Ctrl-C stops both)
./mcp-servers.sh

# Then register them in Open WebUI (auto-detects running servers)
./provision-webui.sh

# Or auto-start on login with a LaunchAgent
cp com.intelligence-stack.mcp-servers.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.intelligence-stack.mcp-servers.plist
```

After provisioning, activate the tools for a model: **Workspace → Models → (select model) → Tools → enable Filesystem and Memory**.

The dashboard (http://localhost:3001) shows live MCP server status and has copy buttons for the SSE URLs.

### What each server provides

| Server | Port | Capability |
|--------|------|-----------|
| Filesystem | 8901 | Read/write files in `~/Documents`, `~/Projects`, `~/Downloads` |
| Memory | 8902 | Persistent knowledge graph — models can store and recall facts across conversations |

### Usage examples

**Filesystem** — ask the model to interact with your local files:

```
Read ~/Projects/my-app/main.py and explain what it does.
```
```
List the markdown files in ~/Documents/notes.
```
```
Write a summary of our conversation to ~/Documents/ai-session.md.
```

**Memory** — facts persist across conversations:

```
Remember that I prefer 2-space indentation and TypeScript strict mode.
```
```
What do you remember about my coding preferences?
```
```
Remember that my main project is the intelligence-stack repo at ~/Projects/intelligence-stack.
```

The memory server stores a knowledge graph that survives model restarts and new chat sessions.
