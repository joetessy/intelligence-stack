import { NextRequest, NextResponse } from "next/server"
import { MCP_SERVERS } from "@/lib/services"

interface RouteContext {
  params: Promise<{ id: string }>
}

export const GET = async (_req: NextRequest, { params }: RouteContext) => {
  const { id } = await params
  const server = MCP_SERVERS.find((s) => s.id === id)

  if (!server) {
    return NextResponse.json({ error: "Unknown MCP server" }, { status: 404 })
  }

  const start = Date.now()
  try {
    await fetch(server.healthUrl, {
      signal: AbortSignal.timeout(3000),
      cache: "no-store",
    })
    // Any HTTP response (including 404) means the server is listening
    return NextResponse.json({ online: true, latencyMs: Date.now() - start })
  } catch {
    return NextResponse.json({ online: false, latencyMs: Date.now() - start })
  }
}
