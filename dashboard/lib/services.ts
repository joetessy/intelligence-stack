import type { ServiceConfig, MCPServerConfig } from "@/types"

const LLAMASWAP_URL = process.env.LLAMASWAP_URL ?? "http://localhost:9292"
const OPEN_WEBUI_URL = process.env.OPEN_WEBUI_URL ?? "http://localhost:3000"
const SEARXNG_URL = process.env.SEARXNG_URL ?? "http://localhost:8080"
const WHISPER_URL = process.env.WHISPER_URL ?? "http://localhost:8765"
const TTS_URL = process.env.TTS_URL ?? "http://localhost:8880"
const MLX_URL = process.env.MLX_URL ?? "http://localhost:5001"
const TOOLS_UI_URL = process.env.TOOLS_UI_URL ?? "http://localhost:5005"

const MCP_FS_URL = process.env.MCP_FS_URL ?? "http://localhost:8901"

export const MCP_SERVERS: readonly MCPServerConfig[] = [
  {
    id: "mcp-filesystem",
    name: "Filesystem",
    description: "Read & write local files",
    port: 8901,
    healthUrl: MCP_FS_URL,
    openwebuiUrl: "http://host.docker.internal:8901/mcp",
    displayUrl: "http://localhost:8901/mcp",
  },
]

export const SERVICES: readonly ServiceConfig[] = [
  {
    id: "open-webui",
    name: "Open WebUI",
    description: "Chat interface",
    hostUrl: "http://localhost:3000",
    healthUrl: `${OPEN_WEBUI_URL}/health`
  },
  {
    id: "searxng",
    name: "SearXNG",
    description: "Web search",
    hostUrl: "http://localhost:8080",
    healthUrl: `${SEARXNG_URL}`
  },
  {
    id: "whisper-stt",
    name: "Whisper STT",
    description: "Speech-to-text",
    hostUrl: "http://localhost:8765",
    healthUrl: `${WHISPER_URL}`
  },
  {
    id: "openedai-speech",
    name: "openedai-speech",
    description: "Text-to-speech",
    hostUrl: "http://localhost:8880",
    healthUrl: `${TTS_URL}/v1/models`
  },
  {
    id: "llama-swap",
    name: "llama.cpp",
    description: "LLM inference (GGUF, hot-swap)",
    hostUrl: "http://localhost:9292/ui",
    healthUrl: `${LLAMASWAP_URL}/v1/models`
  },
  {
    id: "mlx-lm",
    name: "MLX-LM",
    description: "LLM inference (Apple Silicon)",
    hostUrl: "http://localhost:5001",
    healthUrl: `${MLX_URL}/v1/models`
  },
  {
    id: "tools-ui",
    name: "OCR",
    description: "Documents (image/PDF) → Markdown",
    hostUrl: "http://localhost:5005",
    healthUrl: `${TOOLS_UI_URL}`
  },
]
