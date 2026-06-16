import { NextResponse } from "next/server"

// Models are served by llama-swap (llama.cpp) over the OpenAI API. We map its
// GET /v1/models list into the { models: [...] } shape the dashboard already
// renders. Sizes aren't exposed by the OpenAI endpoint, so they're omitted.
export const GET = async () => {
  const baseUrl = process.env.LLAMASWAP_URL ?? "http://localhost:9292"
  try {
    const response = await fetch(`${baseUrl}/v1/models`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000)
    })
    if (!response.ok) return NextResponse.json({ models: [] })
    const data = await response.json()
    const models = (data?.data ?? []).map((m: { id: string }) => ({
      name: m.id,
      model: m.id,
      size: 0,
      details: {}
    }))
    return NextResponse.json({ models })
  } catch {
    return NextResponse.json({ models: [] })
  }
}
