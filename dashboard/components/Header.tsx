interface HeaderProps {
  lastUpdated: number
}

const Header = ({ lastUpdated }: HeaderProps) => {
  const formattedTime = lastUpdated
    ? new Date(lastUpdated).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
      })
    : "—"

  return (
    <header className="mb-10">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-ink">Intelligence Stack</h1>
          <p className="mt-1 font-mono text-xs text-ink-muted">Local AI · No accounts · No cloud</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-[10px] text-ink-dim uppercase tracking-widest">
            Last refresh
          </p>
          <p className="font-mono text-xs text-ink-muted mt-0.5">{formattedTime}</p>
        </div>
      </div>
      <div className="mt-5 h-px bg-edge" />
    </header>
  )
}

export default Header
