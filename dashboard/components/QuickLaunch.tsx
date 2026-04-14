import { ExternalLink } from "lucide-react"

interface QuickLink {
  label: string
  url: string
  sublabel: string
}

const QUICK_LINKS: readonly QuickLink[] = [
  { label: "Open Chat", url: "http://localhost:3000", sublabel: "Open WebUI" },
  { label: "Search UI", url: "http://localhost:8080", sublabel: "SearXNG" },
  { label: "Ollama API", url: "http://localhost:11434/api/tags", sublabel: "REST" }
]

const QuickLaunch = () => {
  return (
    <div className="flex flex-wrap gap-3 mb-8">
      {QUICK_LINKS.map(({ label, url, sublabel }) => (
        <a
          key={url}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="group flex items-center gap-2.5 px-4 py-2.5 rounded-lg
                     border border-edge bg-card hover:border-edge-hover hover:bg-card-hover
                     transition-all duration-200"
        >
          <span className="font-mono text-xs text-ink-muted group-hover:text-ink transition-colors">
            {label}
          </span>
          <span className="font-mono text-[10px] text-ink-dim">·</span>
          <span className="font-mono text-[10px] text-ink-dim group-hover:text-ink-muted transition-colors">
            {sublabel}
          </span>
          <ExternalLink
            size={10}
            className="text-ink-dim group-hover:text-ink-muted transition-colors"
          />
        </a>
      ))}
    </div>
  )
}

export default QuickLaunch
