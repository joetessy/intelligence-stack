import { NextResponse } from "next/server"

export const GET = async () => {
  const mlxUrl = process.env.MLX_URL ?? "http://localhost:5001"
  try {
    const response = await fetch(`${mlxUrl}/v1/models`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000)
    })
    const data = await response.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ object: "list", data: [] })
  }
}
