import { useState, type RefObject } from 'react'
import { Focus, Grid2X2, Link2, Minus, Pause, Play, Plus, RotateCcw, ScanLine, Spline } from 'lucide-react'
import ArenaCanvas from '../simulation/ArenaCanvas'
import type { Layers } from '../simulation/paint'
import { clock } from '../format'
import type { Snapshot } from '../types'

interface Props {
  frame: Snapshot
  latest: RefObject<Snapshot | null>
  selected: number | null
  onSelect: (id: number | null) => void
  command: (path: string) => void
  disabled: boolean
}

const layerTools = [
  { key: 'grid', label: 'Grid', icon: Grid2X2 },
  { key: 'links', label: 'Links', icon: Link2 },
  { key: 'trails', label: 'Trails', icon: Spline },
] as const

export default function ArenaPanel({ frame, latest, selected, onSelect, command, disabled }: Props) {
  const [layers, setLayers] = useState<Layers>({ grid: true, links: true, trails: true })
  const [zoom, setZoom] = useState(1)
  const action = frame.status === 'running' ? 'Pause' : frame.status === 'paused' ? 'Resume' : 'Start'
  const Icon = action === 'Pause' ? Pause : Play
  const finished = frame.status === 'completed' || frame.status === 'timed_out'

  return <section className="panel arena-panel" aria-labelledby="arena-title">
    <div className="panel-heading arena-heading">
      <div className="panel-title">
        <span className="panel-symbol"><ScanLine size={18} /></span>
        <div><p className="eyebrow">TACTICAL VIEW</p><h2 id="arena-title">Simulation arena</h2></div>
      </div>
      <div className="arena-actions">
        <button className="button primary" type="button" disabled={disabled || finished} onClick={() => command('/simulation/' + action.toLowerCase())}><Icon size={15} />{action}</button>
        <button className="button subtle" type="button" disabled={disabled} onClick={() => command('/simulation/reset')}><RotateCcw size={15} />Reset</button>
      </div>
    </div>
    <div className="arena-tools">
      <span className="arena-dimensions">{frame.config.width} × {frame.config.height} <span>WORLD UNITS</span></span>
      <div className="view-buttons">
        <div className="segmented" aria-label="Arena overlays">
          {layerTools.map(({ key, label, icon: LayerIcon }) => <button key={key} type="button" title={label} aria-pressed={layers[key]}
            onClick={() => setLayers(previous => ({ ...previous, [key]: !previous[key] }))}><LayerIcon size={14} /><span>{label}</span></button>)}
        </div>
        <div className="segmented zoom-buttons" aria-label="Arena zoom">
          <button type="button" title="Zoom out" aria-label="Zoom out" disabled={zoom === 1} onClick={() => setZoom(previous => Math.max(1, previous - 0.25))}><Minus size={14} /></button>
          <button type="button" title="Fit arena" aria-label="Fit arena" onClick={() => setZoom(1)}><Focus size={14} /></button>
          <button type="button" title="Zoom in" aria-label="Zoom in" disabled={zoom >= 2.75} onClick={() => setZoom(previous => Math.min(2.75, previous + 0.25))}><Plus size={14} /></button>
        </div>
      </div>
    </div>
    <ArenaCanvas latest={latest} selectedId={selected} onSelect={onSelect} layers={layers} zoom={zoom} />
    <div className="arena-footer">
      <div className="arena-key" aria-label="Arena legend">
        <span><i className="key-agent" /> Drone</span><span><i className="key-leader" /> Leader</span><span><i className="key-failed" /> Failed</span>
        <span><i className="key-static" /> Static</span><span><i className="key-moving" /> Moving</span>
        <span><i className="key-target" /> Target</span><span><i className="key-scan" /> Scanned</span>
      </div>
      <span className="arena-seed">SEED {frame.config.seed} <span>· LIMIT {clock(frame.config.duration)}</span></span>
    </div>
  </section>
}
