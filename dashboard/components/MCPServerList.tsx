"use client"

import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Wrench, Copy, Check, FolderOpen, Brain } from "lucide-react"
import { MCP_SERVERS } from "@/lib/services"
import type { MCPServerConfig, ServiceStatus } from "@/types"

const ICON_MAP: Record<string, React.ElementType> = {
  "mcp-filesystem": FolderOpen,
  "mcp-memory": Brain,
}

const CopyButton = ({ text, label }: { text: string; label: string }) => {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 px-2 py-1 rounded border border-edge
                 font-mono text-[10px] text-ink-muted hover:text-ink hover:border-edge-hover
                 transition-all duration-150 shrink-0"
      aria-label={label}
    >
      {copied ? (
        <><Check size={9} className="text-go" /><span className="text-go">Copied</span></>
      ) : (
        <><Copy size={9} /><span>Copy</span></>
      )}
    </button>
  )
}

const MCPServerCard = ({ server }: { server: MCPServerConfig }) => {
  const { data, isLoading } = useQuery<ServiceStatus>({
    queryKey: ["mcp-health", server.id],
    queryFn: async () => {
      const res = await fetch(`/api/mcp-health/${server.id}`)
      return res.json()
    },
    refetchInterval: 10_000,
  })

  const Icon = ICON_MAP[server.id] ?? Wrench
  const isOnline = data?.online ?? false
  const latency  = data?.latencyMs
  const accentColor = isLoading ? "#2e2e2e" : isOnline ? "#00e87a" : "#ff3b5c"

  return (
    <div
      className="relative rounded-xl border border-edge bg-card p-5
                 hover:border-edge-hover hover:bg-card-hover transition-all duration-300
                 group overflow-hidden"
      style={{ borderLeftColor: accentColor, borderLeftWidth: "2px" }}
    >
      <div
        className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse at 40% 0%, ${accentColor}0a 0%, transparent 65%)`,
        }}
      />

      {/* Icon + name */}
      <div className="flex items-start gap-3 mb-5">
        <div className="p-2 rounded-lg border border-edge bg-canvas shrink-0">
          <Icon size={14} className="text-ink-muted" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-ink leading-none">{server.name}</h3>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">{server.description}</p>
        </div>
      </div>

      {/* Status row */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {isLoading ? (
            <>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-ink-dim" />
              <span className="font-mono text-[11px] text-ink-dim">Checking</span>
            </>
          ) : isOnline ? (
            <>
              <span className="dot-online inline-block w-1.5 h-1.5 rounded-full bg-go" />
              <span className="font-mono text-[11px] text-go">Online</span>
            </>
          ) : (
            <>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-stop" />
              <span className="font-mono text-[11px] text-stop">Offline</span>
            </>
          )}
        </div>
        {latency !== undefined && !isLoading && (
          <span className={`font-mono text-[11px] ${isOnline ? "text-go" : "text-stop"}`}>
            {latency}ms
          </span>
        )}
      </div>

      {/* Bottom section: SSE URL when online, start hint when offline */}
      <div className="pt-3 border-t border-edge">
        {isOnline ? (
          <div>
            <p className="font-mono text-[10px] text-ink-dim mb-1.5">Open WebUI SSE URL</p>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-ink-muted truncate">
                {server.displayUrl}
              </span>
              <CopyButton text={server.openwebuiUrl} label={`Copy SSE URL for ${server.name}`} />
            </div>
          </div>
        ) : (
          <div>
            <p className="font-mono text-[10px] text-ink-dim mb-1.5">Start server</p>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-ink-muted truncate">
                ./mcp-servers.sh
              </span>
              <CopyButton text="./mcp-servers.sh" label="Copy start command" />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const MCPServerList = () => (
  <section className="mt-10">
    <div className="flex items-center gap-2 mb-4">
      <Wrench size={13} className="text-ink-muted" />
      <h2 className="text-sm font-medium text-ink">MCP Tool Servers</h2>
      <span className="font-mono text-[10px] text-ink-dim">· Open WebUI tools</span>
    </div>
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {MCP_SERVERS.map((server) => (
        <MCPServerCard key={server.id} server={server} />
      ))}
    </div>
  </section>
)

export default MCPServerList
