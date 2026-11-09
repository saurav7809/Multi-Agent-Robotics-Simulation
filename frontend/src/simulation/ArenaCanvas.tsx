import { useEffect, useRef, type PointerEvent, type RefObject } from 'react'
import type { Agent, Point, Snapshot } from '../types'
import { paint, transform, type Layers, type View } from './paint'

interface Props {
  latest: RefObject<Snapshot | null>
  selectedId: number | null
  onSelect: (id: number | null) => void
  layers: Layers
  zoom: number
}

export default function ArenaCanvas(props: Props) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const options = useRef(props)
  const view = useRef<View>({ width: 1, height: 1, zoom: 1, pan: [0, 0], pixelRatio: 1 })
  const drag = useRef<{ at: Point; pan: Point; moved: boolean } | null>(null)
  const dirty = useRef(true)

  useEffect(() => {
    options.current = props
    if (props.zoom === 1) view.current.pan = [0, 0]
    view.current.zoom = props.zoom
    dirty.current = true
  }, [props])

  useEffect(() => {
    const element = canvas.current
    const ctx = element?.getContext('2d')
    if (!element || !ctx) return
    const resize = new ResizeObserver(() => {
      const { width, height } = element.getBoundingClientRect()
      const pixelRatio = Math.min(2, window.devicePixelRatio || 1)
      element.width = Math.round(width * pixelRatio)
      element.height = Math.round(height * pixelRatio)
      Object.assign(view.current, { width, height, pixelRatio })
      dirty.current = true
    })
    resize.observe(element)
    let request = 0, receivedAt = 0
    let displayed: Snapshot | null = null
    let previous: Agent[] = []
    let drawn: Agent[] = []
    const trails = new Map<number, Point[]>()
    const render = (now: number) => {
      const { latest, selectedId, layers } = options.current
      const frame = latest.current
      if (frame && frame !== displayed) {
        const sameRun = frame.run_id === displayed?.run_id && frame.session_id === displayed.session_id
        if (!sameRun) trails.clear()
        previous = sameRun && frame.status === 'running' ? drawn : frame.agents
        receivedAt = now
        displayed = frame
        for (const agent of frame.agents) {
          const trail = trails.get(agent.id) ?? []
          const last = trail.at(-1)
          if (!last || Math.hypot(agent.x - last[0], agent.y - last[1]) >= 4) {
            trail.push([agent.x, agent.y])
            if (trail.length > 48) trail.shift()
            trails.set(agent.id, trail)
          }
        }
        dirty.current = true
      }
      if (displayed && view.current.width > 54 && view.current.height > 40 && dirty.current) {
        const t = Math.min(1, (now - receivedAt) * displayed.config.update_hz / 1000)
        drawn = displayed.agents.map((agent, index) => {
          const from = previous[index] ?? agent
          const angle = Math.atan2(Math.sin(agent.heading - from.heading), Math.cos(agent.heading - from.heading))
          return { ...agent, x: from.x + t * (agent.x - from.x), y: from.y + t * (agent.y - from.y), heading: from.heading + t * angle }
        })
        paint(ctx, view.current, displayed, drawn, selectedId, layers, trails)
        dirty.current = t < 1
      }
      request = requestAnimationFrame(render)
    }
    request = requestAnimationFrame(render)
    return () => { resize.disconnect(); cancelAnimationFrame(request) }
  }, [])

  function onPointerDown(event: PointerEvent<HTMLCanvasElement>) {
    if (event.button !== 0) return
    drag.current = { at: [event.clientX, event.clientY], pan: [...view.current.pan], moved: false }
    event.currentTarget.setPointerCapture(event.pointerId)
  }

  function onPointerMove(event: PointerEvent<HTMLCanvasElement>) {
    if (!drag.current || view.current.zoom === 1) return
    const offset = [event.clientX - drag.current.at[0], event.clientY - drag.current.at[1]] as const
    drag.current.moved ||= Math.hypot(...offset) > 4
    if (drag.current.moved) {
      const { width, height, zoom } = view.current
      const limitX = width * zoom / 2, limitY = height * zoom / 2
      view.current.pan = [Math.max(-limitX, Math.min(limitX, drag.current.pan[0] + offset[0])), Math.max(-limitY, Math.min(limitY, drag.current.pan[1] + offset[1]))]
      dirty.current = true
    }
  }

  function onPointerUp(event: PointerEvent<HTMLCanvasElement>) {
    const click = drag.current && !drag.current.moved
    drag.current = null
    const frame = props.latest.current
    if (!click || !frame) return
    const rect = event.currentTarget.getBoundingClientRect()
    const { x, y, scale } = transform(view.current, frame)
    const wx = (event.clientX - rect.left - x) / scale
    const wy = (event.clientY - rect.top - y) / scale
    let nearest: Agent | undefined, distance = 16 / scale
    for (const agent of frame.agents) {
      const gap = Math.hypot(agent.x - wx, agent.y - wy)
      if (gap < distance) { nearest = agent; distance = gap }
    }
    props.onSelect(nearest?.id ?? null)
  }

  return <canvas ref={canvas} className="arena-canvas" aria-label="Live two-dimensional simulation arena"
    onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp}
    onPointerCancel={() => { drag.current = null }} style={{ cursor: props.zoom > 1 ? 'grab' : 'crosshair', touchAction: props.zoom > 1 ? 'none' : 'pan-y' }} />
}
