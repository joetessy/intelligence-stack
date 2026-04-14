"use client"

import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import { Copy, Check, Database } from "lucide-react"
import { formatBytes } from "@/lib/formatBytes"
import type { OllamaTagsResponse, OllamaModel } from "@/types"

interface CopyButtonProps {
  text: string
}

const CopyButton = ({ text }: CopyButtonProps) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 px-2 py-1 rounded border border-transparent
                 font-mono text-[10px] text-ink-muted hover:text-ink hover:border-edge
                 transition-all duration-150"
      aria-label={`Copy ${text}`}
    >
      {copied ? (
        <>
          <Check size={10} className="text-go" />
          <span className="text-go">Copied</span>
        </>
      ) : (
        <>
          <Copy size={10} />
          <span>Copy</span>
        </>
      )}
    </button>
  )
}

interface ModelRowProps {
  model: OllamaModel
}

const ModelRow = ({ model }: ModelRowProps) => (
  <tr className="border-b border-edge hover:bg-card-hover transition-colors group">
    <td className="py-3 pl-4 pr-4 min-w-0">
      <span className="font-mono text-xs text-ink block truncate">{model.name}</span>
    </td>
    <td className="py-3 pr-4 shrink-0">
      <span className="font-mono text-xs text-ink-muted">{formatBytes({ bytes: model.size })}</span>
    </td>
    <td className="py-3 pr-4 text-right shrink-0">
      <span className="opacity-0 group-hover:opacity-100 transition-opacity">
        <CopyButton text={model.name} />
      </span>
    </td>
  </tr>
)

const ModelList = () => {
  const { data, isLoading } = useQuery<OllamaTagsResponse>({
    queryKey: ["models"],
    queryFn: async () => {
      const res = await fetch("/api/models")
      return res.json()
    },
    refetchInterval: 60_000
  })

  const models = data?.models ?? []

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Database size={13} className="text-ink-muted" />
          <h2 className="text-sm font-medium text-ink">Ollama Models</h2>
          {!isLoading && (
            <span className="font-mono text-[10px] text-ink-dim">({models.length})</span>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-xl border border-edge bg-card px-4 py-10 text-center">
          <p className="font-mono text-xs text-ink-muted">Loading models…</p>
        </div>
      ) : models.length === 0 ? (
        <div className="rounded-xl border border-edge bg-card px-4 py-10 text-center">
          <p className="font-mono text-xs text-ink-muted">Ollama offline or no models pulled</p>
          <p className="mt-2 font-mono text-[10px] text-ink-dim">
            Run <code className="text-ink-muted">ollama pull &lt;model&gt;</code> to add models
          </p>
        </div>
      ) : (
        <div className="rounded-xl border border-edge bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-edge">
                <th className="py-2.5 pl-4 pr-4 text-left font-mono text-[10px] text-ink-dim font-normal uppercase tracking-wider">
                  Model
                </th>
                <th className="py-2.5 pr-4 text-left font-mono text-[10px] text-ink-dim font-normal uppercase tracking-wider">
                  Size
                </th>
                <th className="py-2.5 pr-4" />
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <ModelRow key={model.name} model={model} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default ModelList
