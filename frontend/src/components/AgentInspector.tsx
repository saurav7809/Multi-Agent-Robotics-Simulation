import { BatteryWarning, Crosshair, Dices, Radio, ScanFace, ShieldAlert, ShieldCheck, Unplug } from 'lucide-react'
import { agentStates, percent, targetId, unitId } from '../format'
import { stateColors } from '../simulation/paint'
import type { Snapshot } from '../types'

interface Props {
  frame: Snapshot
  selected: number | null
  onSelect: (id: number | null) => void
  command: (path: string, body?: unknown) => void
  disabled: boolean
}

export default function AgentInspector({ frame, selected, onSelect, command, disabled }: Props) {
  const agent = frame.agents.find(item => item.id === selected)
  const task = frame.targets.find(item => item.id === agent?.task_id)
  const failed = agent?.state === 'FAILED'
  const role = agent?.leader === agent?.id ? 'Leader' : agent?.leader ? 'Follower' : 'Scout'

  return <section className="panel inspector-panel" aria-labelledby="inspector-title">
    <div className="panel-heading panel-title">
      <span className="panel-symbol"><ScanFace size={18} /></span>
      <div><p className="eyebrow">FLEET TELEMETRY</p><h2 id="inspector-title">Agent inspector</h2></div>
    </div>
    <div className="inspector-body">
      <label className="field">
        <span>Select agent</span>
        <select value={selected ?? ''} onChange={event => onSelect(event.target.value ? Number(event.target.value) : null)}>
          <option value="">Choose a drone</option>
          {frame.agents.map(item => <option key={item.id} value={item.id}>{unitId(item.id)} · {agentStates[item.state]}</option>)}
        </select>
      </label>
      {agent ? <>
        <div className="unit-heading"><strong>{unitId(agent.id)}</strong><span>{role}</span>
          <span className="unit-state" style={{ color: stateColors[agent.state] }}><i />{agentStates[agent.state]}</span>
        </div>
        <dl className="unit-grid">
          <div><dt>POSITION (X, Y)</dt><dd>{agent.x.toFixed(1)}, {agent.y.toFixed(1)}</dd></div>
          <div><dt>VELOCITY (X, Y)</dt><dd>{agent.vx.toFixed(1)}, {agent.vy.toFixed(1)}</dd></div>
          <div><dt>NEIGHBORS</dt><dd>{agent.neighbor_count}</dd></div>
          <div><dt>RADIO</dt><dd>{agent.online ? 'Online' : 'Offline'}</dd></div>
          <div><dt>TASK</dt><dd>{task ? targetId(task.id) + ' · ' + task.kind : 'Unassigned'}</dd></div>
          <div><dt>{agent.estimate !== null ? 'ESTIMATE' : 'HEALTH'}</dt><dd>{agent.estimate !== null ? agent.estimate.toFixed(3) : percent(agent.health * 100)}</dd></div>
        </dl>
        <div className="battery-readout">
          <div><span>Battery</span><strong>{percent(agent.battery)}</strong></div>
          <progress max={100} value={agent.battery} aria-label="Selected agent battery" />
        </div>
        <div className="fault-actions">
          <button type="button" className={failed ? 'button subtle' : 'button danger'} disabled={disabled}
            onClick={() => command('/agents/' + agent.id + (failed ? '/restore' : '/fail'))}>
            {failed ? <ShieldCheck size={15} /> : <ShieldAlert size={15} />}{failed ? 'Restore agent' : 'Fail agent'}
          </button>
          <button type="button" className="button subtle" disabled={disabled || failed}
            onClick={() => command('/agents/' + agent.id + '/deplete')}><BatteryWarning size={15} />Drain battery</button>
          <button type="button" className="button subtle" disabled={disabled || failed}
            onClick={() => command('/agents/' + agent.id + '/communication', { online: !agent.online })}>
            {agent.online ? <Unplug size={15} /> : <Radio size={15} />}{agent.online ? 'Disable radio' : 'Restore radio'}
          </button>
        </div>
      </> : <div className="inspect-hint"><Crosshair size={18} /><p>Pick an agent in the arena or use the fleet selector to inspect its state and inject faults.</p></div>}
      <button type="button" className="button subtle random-fault" disabled={disabled || !frame.metrics.active_agents}
        onClick={() => command('/agents/random-failure')}><Dices size={15} />Random failure</button>
    </div>
  </section>
}
