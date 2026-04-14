import { NextResponse } from "next/server"

export const GET = async () => {
  const ollamaUrl = process.env.OLLAMA_URL ?? "http://localhost:11434"
  try {
    const response = await fetch(`${ollamaUrl}/api/tags`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000)
    })
    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ models: [] })
  }
}
