"use client"

import { useQuery } from "@tanstack/react-query"
import {
  MessageSquare,
  Search,
  Mic,
  Volume2,
  Cpu,
  ExternalLink,
  type LucideIcon
} from "lucide-react"
import type { ServiceConfig, ServiceStatus } from "@/types"

const ICON_MAP: Record<string, LucideIcon> = {
  "open-webui": MessageSquare,
  searxng: Search,
  "whisper-stt": Mic,
  "kokoro-tts": Volume2,
  ollama: Cpu
}

const getLatencyColor = (ms: number): string => {
  if (ms < 100) return "text-go"
  if (ms < 300) return "text-warn"
  return "text-stop"
}

interface ServiceCardProps {
  service: ServiceConfig
  animationDelay?: number
}

const ServiceCard = ({ service, animationDelay = 0 }: ServiceCardProps) => {
  const { data, isLoading } = useQuery<ServiceStatus>({
    queryKey: ["health", service.id],
    queryFn: async () => {
      const res = await fetch(`/api/health/${service.id}`)
      return res.json()
    },
    refetchInterval: 10_000
  })

  const Icon = ICON_MAP[service.id] ?? Cpu
  const isOnline = data?.online ?? false
  const latency = data?.latencyMs

  const accentColor = isLoading ? "#2e2e2e" : isOnline ? "#00e87a" : "#ff3b5c"

  return (
    <div
      className="animate-in relative rounded-xl border border-edge bg-card p-5
                 hover:border-edge-hover hover:bg-card-hover transition-all duration-300
                 group overflow-hidden"
      style={{
        borderLeftColor: accentColor,
        borderLeftWidth: "2px",
        animationDelay: `${animationDelay}ms`
      }}
    >
      {/* Subtle radial glow on hover based on status color */}
      <div
        className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
        style={{
          background: `radial-gradient(ellipse at 40% 0%, ${accentColor}0a 0%, transparent 65%)`
        }}
      />

      {/* Icon + name */}
      <div className="flex items-start gap-3 mb-5">
        <div className="p-2 rounded-lg border border-edge bg-canvas shrink-0">
          <Icon size={14} className="text-ink-muted" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-ink leading-none">{service.name}</h3>
          <p className="mt-1 font-mono text-[11px] text-ink-muted">{service.description}</p>
        </div>
      </div>

      {/* Status row */}
      <div className="flex items-center justify-between">
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
          <span className={`font-mono text-[11px] ${getLatencyColor(latency)}`}>{latency}ms</span>
        )}
      </div>

      {/* URL link */}
      <div className="mt-4 pt-3 border-t border-edge">
        <a
          href={service.hostUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 font-mono text-[11px] text-ink-dim
                     hover:text-ink-muted transition-colors group/link"
        >
          <span className="truncate">{service.hostUrl}</span>
          <ExternalLink
            size={9}
            className="shrink-0 opacity-0 group-hover/link:opacity-100 transition-opacity"
          />
        </a>
      </div>
    </div>
  )
}

export default ServiceCard
