import { useState } from 'react'
import { Activity, Pin, X } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { algorithms, clock, percent, runId } from '../format'
import type { Sample, Snapshot } from '../types'
import { useRunHistory } from '../useRunHistory'

const green = '#62dfc4', blue = '#79b6fd', amber = '#ecb876', red = '#ee8392', violet = '#ba9bff'
const panels = ['Mission', 'Fleet', 'Network', 'Tasks', 'Consensus'] as const
type Tab = (typeof panels)[number]
type Series = { key: string; name: string; color: string }

const axis = { fill: '#8798ae', fontSize: 10, fontFamily: 'Consolas, monospace' }
const tooltip = { background: '#182333', border: '1px solid #314358', borderRadius: 9, fontSize: 12 }

function Timeline({ samples, series, limit, suffix = '' }: { samples: Sample[]; series: Series[]; limit?: number; suffix?: string }) {
  const rows = samples.map(({ time, metrics }) => ({
    ...metrics, time,
    delivery: metrics.packets_sent ? 100 * metrics.packets_delivered / metrics.packets_sent : null,
    spread: metrics.consensus_spread === null ? null : 100 * metrics.consensus_spread,
  }))
  return <div className="chart-frame">
    <ResponsiveContainer width="100%" height={214} minWidth={0}>
      <LineChart data={rows} margin={{ top: 12, left: -10, right: 24, bottom: 0 }}>
        <CartesianGrid stroke="#253345" strokeDasharray="4 5" vertical={false} />
        <XAxis dataKey="time" type="number" domain={[0, Math.max(5, rows.at(-1)?.time ?? 5)]} tickFormatter={value => clock(value)} tick={axis} axisLine={false} tickLine={false} />
        <YAxis domain={[0, limit ?? 'auto']} tick={axis} axisLine={false} tickLine={false} tickFormatter={value => String(value) + suffix} />
        <Tooltip contentStyle={tooltip} labelStyle={{ color: '#a9b8cc' }} labelFormatter={value => clock(Number(value), true)}
          formatter={(value) => typeof value === 'number' ? String(Number(value.toFixed(2))) + suffix : '—'} />
        <Legend wrapperStyle={{ fontSize: 11 }} iconType="plainline" />
        {series.map(item => <Line key={item.key} dataKey={item.key} name={item.name} type="monotone" stroke={item.color}
          strokeWidth={2} isAnimationActive={false} dot={rows.length <= 2 ? { r: 3 } : false} />)}
      </LineChart>
    </ResponsiveContainer>
  </div>
}

function TaskChart({ frame }: { frame: Snapshot }) {
  const m = frame.metrics
  if (!m.tasks_total) return <div className="chart-empty">This mission scores fleet movement and coordination. Choose a target mission to chart task distribution.</div>
  const distribution = [
    { stage: 'Completed', count: m.tasks_completed, color: green },
    { stage: 'Claimed', count: m.tasks_assigned, color: blue },
    { stage: 'Open', count: Math.max(0, m.tasks_discovered - m.tasks_completed - m.tasks_assigned), color: amber },
    { stage: 'Unseen', count: m.tasks_total - m.tasks_discovered, color: violet },
  ]
  return <div className="chart-frame">
    <ResponsiveContainer width="100%" height={214} minWidth={0}>
      <BarChart data={distribution} layout="vertical" margin={{ right: 20, top: 10 }}>
        <CartesianGrid stroke="#253345" horizontal={false} strokeDasharray="4 5" />
        <XAxis type="number" domain={[0, m.tasks_total]} allowDecimals={false} tick={axis} tickLine={false} axisLine={false} />
        <YAxis dataKey="stage" type="category" width={83} tick={axis} tickLine={false} axisLine={false} />
        <Tooltip contentStyle={tooltip} cursor={{ fill: '#253448' }} />
        <Bar dataKey="count" name="Objectives" isAnimationActive={false} barSize={17} radius={[0, 4, 4, 0]}>
          {distribution.map(item => <Cell key={item.stage} fill={item.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </div>
}

function Chart({ tab, samples, frame }: { tab: Tab; samples: Sample[]; frame: Snapshot }) {
  if (tab === 'Tasks') return <TaskChart frame={frame} />
  if (tab === 'Fleet') return <div className="chart-pair">
    <Timeline samples={samples} limit={frame.metrics.total_agents} series={[{ key: 'active_agents', name: 'Active', color: green }, { key: 'failed_agents', name: 'Failed', color: red }]} />
    <Timeline samples={samples} limit={100} suffix="%" series={[{ key: 'average_battery', name: 'Average battery', color: blue }]} />
  </div>
  if (tab === 'Network') return <div className="chart-pair">
    <Timeline samples={samples} limit={100} suffix="%" series={[{ key: 'connectivity', name: 'Connectivity', color: violet }, { key: 'delivery', name: 'Packet delivery', color: green }]} />
    <Timeline samples={samples} series={[{ key: 'collisions', name: 'Collisions', color: amber }]} />
  </div>
  if (tab === 'Consensus') return <Timeline samples={samples} limit={100} suffix="%" series={[{ key: 'spread', name: 'Estimate spread', color: violet }]} />
  return <Timeline samples={samples} limit={100} suffix="%" series={[{ key: 'coverage', name: 'Area coverage', color: green }, { key: 'mission_progress', name: 'Mission progress', color: blue }]} />
}

export default function AnalyticsPanel({ frame }: { frame: Snapshot }) {
  const [tab, setTab] = useState<Tab>('Mission')
  const [reference, setReference] = useState<Snapshot | null>(null)
  const samples = useRunHistory(frame)
  const available = panels.filter(item => item !== 'Consensus' || frame.config.algorithm === 'consensus')
  const current = available.includes(tab) ? tab : 'Mission'
  const m = frame.metrics
  const stats = [
    ['Avg. distance', m.average_distance.toFixed(1) + ' u'],
    ['Avg. task time', m.average_task_time === null ? '—' : m.average_task_time.toFixed(1) + ' s'],
    ['Coordination', percent(m.coordination_efficiency)],
    ['Failure rate', percent(m.failure_rate)],
  ]
  const compare = reference ? [
    ['Coverage', m.coverage - reference.metrics.coverage, ' pp'],
    ['Connectivity', m.connectivity - reference.metrics.connectivity, ' pp'],
    ['Avg. distance', m.average_distance - reference.metrics.average_distance, ' u'],
    ['Collisions', m.collisions - reference.metrics.collisions, ''],
  ] as const : []

  return <section className="panel analytics-panel" aria-labelledby="analytics-title">
    <div className="panel-heading analytics-heading">
      <div className="panel-title">
        <span className="panel-symbol"><Activity size={18} /></span>
        <div><p className="eyebrow">PERFORMANCE</p><h2 id="analytics-title">Live analytics</h2></div>
      </div>
      <button type="button" className="button subtle" disabled={frame.time === 0} onClick={() => setReference(frame)}><Pin size={14} />Save reference</button>
    </div>
    <div className="analytics-body">
      <div className="analytics-tabs" aria-label="Analytics views">
        {available.map(item => <button key={item} type="button" aria-pressed={item === current} onClick={() => setTab(item)}>{item}</button>)}
      </div>
      <Chart tab={current} samples={samples} frame={frame} />
      {current === 'Consensus' && <p className="chart-note">Agreement {m.consensus_reached ? 'held' : 'pending'} · First convergence {m.consensus_time === null ? '—' : m.consensus_time + ' s'}</p>}
      <dl className="secondary-metrics">{stats.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      {reference && <div className="reference-panel">
        <div className="reference-heading">
          <div><h3>Change from reference run {runId(reference.run_id)}</h3>
            <p>{algorithms[reference.config.algorithm]} · {reference.scenario.replaceAll('-', ' ')} · seed {reference.config.seed} · {clock(reference.time, true)}</p></div>
          <button type="button" aria-label="Clear reference" className="button subtle icon-button" onClick={() => setReference(null)}><X size={15} /></button>
        </div>
        <dl className="secondary-metrics">
          {compare.map(([label, delta, unit]) => <div key={label}><dt>{label}</dt><dd>{delta > 0 ? '+' : ''}{Number(delta.toFixed(2))}{unit}</dd></div>)}
        </dl>
      </div>}
    </div>
  </section>
}
