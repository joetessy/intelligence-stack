import { NextRequest, NextResponse } from "next/server"
import { SERVICES } from "@/lib/services"

interface RouteContext {
  params: Promise<{ service: string }>
}

// When running in Docker, use internal service URLs from env vars.
// Falls back to the public localhost URL for local dev.
const SERVER_URLS: Record<string, string | undefined> = {
  "open-webui": process.env.OPEN_WEBUI_URL,
  searxng: process.env.SEARXNG_URL,
  "whisper-stt": process.env.WHISPER_URL,
  "kokoro-tts": process.env.TTS_URL,
  ollama: process.env.OLLAMA_URL,
}

export const GET = async (_request: NextRequest, { params }: RouteContext) => {
  const { service: serviceId } = await params
  const config = SERVICES.find((s) => s.id === serviceId)

  if (!config) {
    return NextResponse.json({ error: "Unknown service" }, { status: 404 })
  }

  const url = SERVER_URLS[serviceId] ?? config.healthUrl
  const start = Date.now()
  try {
    await fetch(url, {
      signal: AbortSignal.timeout(3000),
      cache: "no-store"
    })
    return NextResponse.json({ online: true, latencyMs: Date.now() - start })
  } catch {
    return NextResponse.json({ online: false, latencyMs: Date.now() - start })
  }
}
