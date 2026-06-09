import { NextRequest, NextResponse } from "next/server"
import { SERVICES } from "@/lib/services"

interface RouteContext {
  params: Promise<{ service: string }>
}

export const GET = async (_request: NextRequest, { params }: RouteContext) => {
  const { service: serviceId } = await params
  const config = SERVICES.find((s) => s.id === serviceId)

  if (!config) {
    return NextResponse.json({ error: "Unknown service" }, { status: 404 })
  }

  const start = Date.now()
  try {
    const res = await fetch(config.healthUrl, {
      signal: AbortSignal.timeout(3000),
      cache: "no-store"
    })
    return NextResponse.json({ online: res.ok, latencyMs: Date.now() - start })
  } catch {
    return NextResponse.json({ online: false, latencyMs: Date.now() - start })
  }
}
