import { BatteryMedium, Crosshair, Grid2X2, Radio, TriangleAlert, Users } from 'lucide-react'
import { percent } from '../format'
import type { Metrics } from '../types'

export default function MetricCards({ metrics }: { metrics: Metrics }) {
  const cards = [
    { label: 'Active fleet', icon: Users, value: String(metrics.active_agents), unit: ' / ' + metrics.total_agents, note: metrics.failed_agents + ' failed', tone: 'mint' },
    { label: 'Mission progress', icon: Crosshair, value: percent(metrics.mission_progress), note: 'Objective completion', tone: 'blue' },
    { label: 'Area coverage', icon: Grid2X2, value: percent(metrics.coverage), note: metrics.visited_cells + ' of ' + metrics.valid_cells + ' cells', tone: 'mint' },
    { label: 'Connectivity', icon: Radio, value: percent(metrics.connectivity), note: metrics.radio_links + ' radio links', tone: 'purple' },
    { label: 'Average battery', icon: BatteryMedium, value: percent(metrics.average_battery), note: metrics.returning_agents + ' returning', tone: 'mint' },
    { label: 'Collisions', icon: TriangleAlert, value: String(metrics.collisions), note: 'Contact events', tone: 'amber' },
  ]
  return <section className="metric-grid" aria-label="Mission metrics">
    {cards.map(({ label, icon: Icon, value, unit, note, tone }) => <article className={'metric-card ' + tone} key={label}>
      <div className="metric-label"><span className="metric-icon"><Icon size={15} aria-hidden="true" /></span>{label}</div>
      <div className="metric-value">{value}{unit && <span>{unit}</span>}</div>
      <p>{note}</p>
    </article>)}
  </section>
}
