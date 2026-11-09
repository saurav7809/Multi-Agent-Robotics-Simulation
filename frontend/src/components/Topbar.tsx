import { useRef } from 'react'
import { ArrowDownToLine, ChevronDown, FileJson, FileSpreadsheet, Network } from 'lucide-react'
import type { Connection } from '../useTelemetry'

const connectionLabel: Record<Connection, string> = {
  connecting: 'Connecting', streaming: 'Telemetry live', polling: 'Polling API', offline: 'API offline',
}

export default function Topbar({ connection, canExport }: { connection: Connection; canExport: boolean }) {
  const menu = useRef<HTMLDetailsElement>(null)
  return <header className="topbar">
    <div className="topbar-inner">
      <div className="brand">
        <div className="brand-mark"><Network size={19} strokeWidth={2.1} aria-hidden="true" /></div>
        <span>Swarm<span className="brand-accent">Lab</span></span>
        <span className="brand-tag">ROBOTICS CONSOLE</span>
      </div>
      <div className="topbar-actions">
        <span className={'connection-badge ' + connection} role="status"><i />{connectionLabel[connection]}</span>
        {canExport && <details className="export-menu" ref={menu} onKeyDown={event => {
          if (event.key === 'Escape') {
            menu.current?.removeAttribute('open')
            menu.current?.querySelector('summary')?.focus()
          }
        }}>
          <summary className="button subtle" aria-label="Export results"><ArrowDownToLine size={15} /> <span>Export</span><ChevronDown size={13} /></summary>
          <div className="export-options">
            <a download href="/api/simulation/export?format=csv" onClick={() => menu.current?.removeAttribute('open')}><FileSpreadsheet size={16} /> Metrics CSV</a>
            <a download href="/api/simulation/export?format=json" onClick={() => menu.current?.removeAttribute('open')}><FileJson size={16} /> Full run JSON</a>
          </div>
        </details>}
      </div>
    </div>
  </header>
}
