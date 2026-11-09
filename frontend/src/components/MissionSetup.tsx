import { useState, type FormEvent } from 'react'
import { ChevronDown, Crosshair, Dices, SlidersHorizontal } from 'lucide-react'
import { algorithms } from '../format'
import type { Algorithm, Scenario, SimulationConfig, Snapshot } from '../types'

interface Props {
  frame: Snapshot
  scenarios: Scenario[]
  command: (path: string, body?: unknown) => void
  disabled: boolean
}

type NumericKey = Exclude<keyof SimulationConfig, 'algorithm'>
const advanced: { key: NumericKey; label: string; min: number; max: number; step?: string }[] = [
  { key: 'width', label: 'Arena width', min: 640, max: 2200 },
  { key: 'height', label: 'Arena height', min: 480, max: 1500 },
  { key: 'agent_speed', label: 'Drone speed', min: 25, max: 125, step: 'any' },
  { key: 'obstacle_density', label: 'Obstacle density', min: 0, max: 35 },
  { key: 'target_count', label: 'Target points', min: 1, max: 24 },
  { key: 'duration', label: 'Duration (s)', min: 20, max: 900 },
  { key: 'packet_loss', label: 'Packet loss (%)', min: 0, max: 100, step: 'any' },
  { key: 'delay_ms', label: 'Radio delay (ms)', min: 0, max: 1000 },
  { key: 'update_hz', label: 'Stream rate (Hz)', min: 2, max: 20 },
  { key: 'seed', label: 'Arena seed', min: 0, max: 4294967295 },
]
const boids = [
  { key: 'separation', label: 'Separation', min: 0, max: 4, step: 'any' },
  { key: 'alignment', label: 'Alignment', min: 0, max: 4, step: 'any' },
  { key: 'cohesion', label: 'Cohesion', min: 0, max: 4, step: 'any' },
] as const
const speeds = [0.25, 0.5, 1, 1.5, 2, 3, 4]

export default function MissionSetup({ frame, scenarios, command, disabled }: Props) {
  const { config } = frame
  const scenario = scenarios.find(item => item.id === frame.scenario)
  const [algorithm, setAlgorithm] = useState(config.algorithm)
  const [fleet, setFleet] = useState(config.agent_count)
  const [range, setRange] = useState(config.communication_range)
  const fields = [
    ...advanced.filter(field => field.key !== 'target_count' || (scenario?.target_count ?? 0) > 0),
    ...(algorithm === 'boids' ? boids : []),
  ]
  const speedOptions = speeds.includes(config.speed) ? speeds : [...speeds, config.speed].sort((a, b) => a - b)

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const changes: Partial<SimulationConfig> = { algorithm, agent_count: fleet, communication_range: range }
    for (const { key } of fields) {
      const field = form.get(key)
      if (field !== null) changes[key] = Number(field) / (key === 'packet_loss' ? 100 : 1)
    }
    command('/simulation/configure', changes)
  }

  function randomize() {
    const seed = crypto.getRandomValues(new Uint32Array(1))[0]
    command('/simulation/configure', { seed: seed === config.seed ? (seed + 1) >>> 0 : seed })
  }

  return <section className="panel setup-panel" aria-labelledby="setup-title">
    <div className="panel-heading panel-title">
      <span className="panel-symbol"><SlidersHorizontal size={17} /></span>
      <div><p className="eyebrow">OPERATIONS</p><h2 id="setup-title">Mission setup</h2></div>
    </div>
    <div className="setup-body">
      <label className="field">
        <span>Mission scenario</span>
        <select value={frame.scenario} disabled={disabled || !scenarios.length} onChange={event => command('/scenarios/' + event.target.value + '/load')}>
          {scenarios.length ? scenarios.map(item => <option key={item.id} value={item.id}>{item.name}</option>) : <option value={frame.scenario}>Loading scenarios…</option>}
        </select>
      </label>
      {scenario && <div className="objective">
        <Crosshair size={15} />
        <div><p className="eyebrow">OBJECTIVE</p><p>{scenario.objective}</p></div>
      </div>}
      <form className="settings-form" onSubmit={submit} onInvalid={event => event.currentTarget.querySelector('details')?.setAttribute('open', '')}>
        <label className="field">
          <span>Swarm algorithm</span>
          <select value={algorithm} disabled={disabled} onChange={event => setAlgorithm(event.target.value as Algorithm)}>
            {Object.entries(algorithms).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
          </select>
        </label>
        <label className="field range-field">
          <span>Agent count <strong aria-hidden="true">{fleet}</strong></span>
          <input type="range" aria-label="Agent count" min={5} max={100} value={fleet} disabled={disabled} onChange={event => setFleet(Number(event.target.value))} />
        </label>
        <label className="field range-field">
          <span>Radio range <strong aria-hidden="true">{range} u</strong></span>
          <input type="range" aria-label="Radio range" min={40} max={700} step="any" value={range} disabled={disabled} onChange={event => setRange(Math.round(Number(event.target.value)))} />
        </label>
        <label className="field speed-field">
          <span>Playback speed</span>
          <select disabled={disabled} value={config.speed} onChange={event => command('/simulation/configure', { speed: Number(event.target.value) })}>
            {speedOptions.map(speed => <option key={speed} value={speed}>{speed}×</option>)}
          </select>
        </label>
        <details className="advanced-settings">
          <summary>Advanced settings <ChevronDown size={15} /></summary>
          <div className="advanced-fields">
            {fields.map(({ key, label, min, max, step }) => <label className="field" key={key}>
              <span>{label}</span>
              <input type="number" name={key} defaultValue={config[key] * (key === 'packet_loss' ? 100 : 1)}
                min={min} max={max} step={step ?? 1} required disabled={disabled} />
            </label>)}
          </div>
        </details>
        <div className="setup-actions">
          <button className="button primary" type="submit" disabled={disabled}>Apply configuration</button>
          <button className="button subtle icon-button" type="button" disabled={disabled} title="Randomize arena" aria-label="Randomize arena" onClick={randomize}><Dices size={17} /></button>
        </div>
        <p className="field-hint">Applying changed settings starts a fresh run. Playback speed updates live.</p>
      </form>
    </div>
  </section>
}
