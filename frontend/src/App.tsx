import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { CircleAlert, Radar } from 'lucide-react'
import { request } from './api'
import AgentInspector from './components/AgentInspector'
import ArenaPanel from './components/ArenaPanel'
import EventLog from './components/EventLog'
import MetricCards from './components/MetricCards'
import MissionSetup from './components/MissionSetup'
import Topbar from './components/Topbar'
import { clock, runId, runStates } from './format'
import type { Scenario, Snapshot } from './types'
import { useTelemetry } from './useTelemetry'

const AnalyticsPanel = lazy(() => import('./components/AnalyticsPanel'))

export default function App() {
  const { latest, frame, connection, ingest } = useTelemetry()
  const [selection, select] = useState<{ run: string; id: number | null } | null>(null)
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [busy, setBusy] = useState(false)
  const commandLock = useRef(false)
  const [error, setError] = useState('')
  const session = frame?.session_id
  const run = session + '/' + frame?.run_id
  const selected = selection?.run === run ? selection.id : null
  const disabled = busy || connection === 'offline'

  useEffect(() => {
    if (!session || connection === 'offline') return
    const abort = new AbortController()
    let timer: number
    function load() {
      request<Scenario[]>('/scenarios', undefined, 'GET', abort.signal)
        .then(data => { if (!abort.signal.aborted) setScenarios(data) })
        .catch(() => { if (!abort.signal.aborted) timer = window.setTimeout(load, 2000) })
    }
    load()
    return () => { abort.abort(); clearTimeout(timer) }
  }, [session, connection])

  async function command(path: string, body?: unknown) {
    if (commandLock.current) return
    commandLock.current = true
    setBusy(true)
    setError('')
    try {
      ingest(await request<Snapshot>(path, body, 'POST'), true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The simulator did not accept the command.')
    } finally {
      commandLock.current = false
      setBusy(false)
    }
  }

  function onSelect(id: number | null) {
    select({ run, id })
  }

  return <>
    <Topbar connection={connection} canExport={Boolean(frame && connection !== 'offline')} />
    <main className="console">
      <section className="page-heading" aria-labelledby="page-title">
        <div>
          <p className="eyebrow workspace-label"><Radar size={15} /> SWARM SIMULATION WORKSPACE</p>
          <h1 id="page-title">Mission control</h1>
          <p className="page-summary">Run decentralized missions and track fleet behavior in real time.</p>
        </div>
        {frame && <div className="run-summary">
          <div><span>RUN</span><strong>{runId(frame.run_id)}</strong></div>
          <div><span>SIM TIME</span><strong>{clock(frame.time, true)}</strong></div>
          <span className={'run-badge ' + frame.status}><i />{runStates[frame.status]}</span>
        </div>}
      </section>
      {error && <div className="error-banner" role="alert"><CircleAlert size={17} />{error}</div>}
      {frame ? <>
        <MetricCards metrics={frame.metrics} />
        <div className="workspace">
          <ArenaPanel frame={frame} latest={latest} selected={selected} onSelect={onSelect} command={command} disabled={disabled} />
          <aside className="command-column" aria-label="Mission and agent controls">
            <MissionSetup key={run} frame={frame} scenarios={scenarios} command={command} disabled={disabled} />
            <AgentInspector frame={frame} selected={selected} onSelect={onSelect} command={command} disabled={disabled} />
          </aside>
          <div className="analysis-column">
            <Suspense fallback={<div className="panel connecting-panel">Loading analytics…</div>}><AnalyticsPanel frame={frame} /></Suspense>
            <EventLog key={run} frame={frame} />
          </div>
        </div>
      </> : <div className="panel connecting-panel"><Radar size={22} /><p>{connection === 'offline' ? 'Start the local FastAPI service to open the console.' : 'Connecting to the simulation engine…'}</p></div>}
    </main>
  </>
}
