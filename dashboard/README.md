# Dashboard

Local health-check dashboard for the Intelligence Stack. Polls each backing
service every 10 s and shows online state, latency, and the list of available
Ollama + MLX models.

Reachable at **http://localhost:3001** when the stack is up.

## What it polls

- **Service health** (`GET /api/health/[service]`) — fetches each service's
  health endpoint with a 3 s timeout. `online` is `true` iff the response is
  2xx; any other status (404, 5xx) or fetch error reports offline.
- **MCP server health** (`GET /api/mcp-health/[id]`) — same idea but lenient:
  any HTTP response means the supergateway is listening (MCP itself lives at
  `/mcp`, not `/`, so non-2xx replies are normal).
- **Ollama models** (`GET /api/models`) — proxies `GET ${OLLAMA_URL}/api/tags`.
- **MLX models** (`GET /api/mlx-models`) — proxies `GET ${MLX_URL}/v1/models`.

Service URLs are read from env vars (`OPEN_WEBUI_URL`, `OLLAMA_URL`,
`MLX_URL`, etc.) with safe localhost defaults — see `lib/services.ts`.

## Stack

- Next.js 16 (App Router) — note the breaking changes flagged in
  `AGENTS.md`; consult `node_modules/next/dist/docs/` before touching APIs.
- React 19, TanStack Query 5 (10 s refetch interval, 5 s stale time).
- Tailwind 4, lucide-react icons.
- Vitest 4 + @testing-library/react. Run with `npm test`.

## Develop

```bash
npm install
npm run dev        # http://localhost:3001
npm test           # 19 tests, jsdom env
npm run build      # production build (used by the Dockerfile)
```

The container build is multi-stage on `node:22-alpine`, using
`next build --output standalone`, copying only the standalone output + static
assets into the runtime image.
