import { useEffect, useState } from 'react'
import { BellRing, CircleDot, Radio, ShieldAlert, Target, Terminal, Workflow } from 'lucide-react'
import { request } from '../api'
import { clock } from '../format'
import type { SimEvent, Snapshot } from '../types'

const categories = [
  { id: 'mission', label: 'Mission', icon: CircleDot, types: ['MISSION_READY', 'RUN_STARTED', 'RUN_PAUSED', 'RUN_RESUMED', 'MISSION_COMPLETED', 'MISSION_TIMEOUT'] },
  { id: 'fault', label: 'Agent faults', icon: ShieldAlert, types: ['AGENT_FAILURE', 'AGENT_RESTORED', 'BATTERY_WARNING', 'BATTERY_CHARGED'] },
  { id: 'radio', label: 'Radio', icon: Radio, types: ['COMMUNICATION_LOST', 'COMMUNICATION_RESTORED'] },
  { id: 'task', label: 'Tasks', icon: Target, types: ['TARGET_DISCOVERED', 'TASK_ASSIGNMENT', 'TASK_COMPLETED'] },
  { id: 'coordination', label: 'Coordination', icon: Workflow, types: ['LEADER_UPDATE', 'CONSENSUS_REACHED'] },
]

function mergeEvents(previous: SimEvent[], incoming: SimEvent[]) {
  const byId = new Map(previous.map(event => [event.id, event]))
  for (const event of incoming) byId.set(event.id, event)
  return [...byId.values()].sort((a, b) => b.id - a.id).slice(0, 240)
}

export default function EventLog({ frame }: { frame: Snapshot }) {
  const { session_id: session, run_id: run, events: incoming } = frame
  const [filter, setFilter] = useState('all')
  const [events, setEvents] = useState(() => mergeEvents([], incoming))
  useEffect(() => {
    setEvents(previous => (incoming.at(-1)?.id ?? 0) > (previous[0]?.id ?? 0) ? mergeEvents(previous, incoming) : previous)
  }, [incoming])

  useEffect(() => {
    const abort = new AbortController()
    request<{ session_id: string; run_id: number; events: SimEvent[] }>('/events', undefined, 'GET', abort.signal)
      .then(result => { if (!abort.signal.aborted && result.session_id === session && result.run_id === run) setEvents(previous => mergeEvents(previous, result.events)) })
      .catch(() => {})
    return () => abort.abort()
  }, [session, run])

  const filtered = filter === 'all' ? events : events.filter(event => categories.find(item => item.id === filter)?.types.includes(event.type))
  return <section className="panel event-panel" aria-labelledby="log-title">
    <div className="panel-heading event-heading">
      <div className="panel-title">
        <span className="panel-symbol"><Terminal size={18} /></span>
        <div><p className="eyebrow">SYSTEM JOURNAL</p><h2 id="log-title">Event log</h2></div>
      </div>
      <select aria-label="Filter events" value={filter} onChange={event => setFilter(event.target.value)}>
        <option value="all">All events</option>
        {categories.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select>
    </div>
    {filtered.length ? <ol className="event-list" aria-label="Simulation events" tabIndex={0}>
      {filtered.map(event => {
        const category = categories.find(item => item.types.includes(event.type))
        const Icon = category?.icon ?? BellRing
        return <li key={event.id} className={'event-row ' + (category?.id ?? 'mission')}>
          <time>{clock(event.time, true)}</time><span className="event-icon"><Icon size={15} /></span>
          <div><p>{event.message}</p><span>{event.type.replaceAll('_', ' ').toLowerCase()}</span></div>
        </li>
      })}
    </ol> : <p className="empty-events">Events matching this filter will appear here.</p>}
  </section>
}
