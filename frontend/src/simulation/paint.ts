import type { Agent, AgentState, Point, Snapshot } from '../types'

export const stateColors: Record<AgentState, string> = {
  IDLE: '#7de7ea', EXPLORING: '#61e9c6', MOVING: '#78c9ff', COMMUNICATING: '#8bb8ff',
  AVOIDING_OBSTACLE: '#f2b46d', EXECUTING_TASK: '#a8ee82', RETURNING: '#c2a2ff', FAILED: '#f27d8d',
}

export interface View { width: number; height: number; zoom: number; pan: Point; pixelRatio: number }
export interface Layers { grid: boolean; links: boolean; trails: boolean }

export function transform(view: View, frame: Snapshot) {
  const { width, height } = frame.config
  const scale = Math.min((view.width - 54) / width, (view.height - 40) / height) * view.zoom
  return { scale, x: (view.width - width * scale) / 2 + view.pan[0], y: (view.height - height * scale) / 2 + view.pan[1] }
}

function circle(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number) {
  ctx.beginPath()
  ctx.arc(x, y, radius, 0, Math.PI * 2)
}

function marker(ctx: CanvasRenderingContext2D, [x, y]: Point, label: string, color: string, radius: number) {
  ctx.save()
  circle(ctx, x, y, radius)
  ctx.fillStyle = `${color}12`; ctx.fill()
  ctx.setLineDash([5, 5]); ctx.strokeStyle = `${color}80`; ctx.stroke(); ctx.setLineDash([])
  ctx.translate(x, y); ctx.rotate(Math.PI / 4)
  ctx.strokeStyle = color; ctx.strokeRect(-5, -5, 10, 10)
  ctx.restore()
  ctx.fillStyle = color
  ctx.fillText(label, x + radius + 7, y + 4)
}

function drone(ctx: CanvasRenderingContext2D, agent: Agent, selected: boolean, labelled: boolean) {
  const color = stateColors[agent.state]
  ctx.save()
  ctx.translate(agent.x, agent.y)
  if (agent.leader === agent.id && agent.state !== 'FAILED') {
    circle(ctx, 0, 0, 13)
    ctx.strokeStyle = '#e9b973'; ctx.lineWidth = 1.3; ctx.stroke()
  }
  if (selected) {
    circle(ctx, 0, 0, 16)
    ctx.strokeStyle = '#d7fcf0'; ctx.lineWidth = 1.5; ctx.stroke()
  }
  if (agent.state === 'FAILED') {
    ctx.beginPath()
    ctx.moveTo(-5, -5); ctx.lineTo(5, 5)
    ctx.moveTo(-5, 5); ctx.lineTo(5, -5)
    ctx.strokeStyle = color; ctx.lineWidth = 2.4; ctx.stroke()
  } else {
    ctx.rotate(agent.heading)
    ctx.beginPath()
    ctx.moveTo(10, 0); ctx.lineTo(-7, 6); ctx.lineTo(-3, 0); ctx.lineTo(-7, -6); ctx.closePath()
    ctx.fillStyle = color; ctx.strokeStyle = '#08131a'; ctx.lineWidth = 1.4
    ctx.stroke(); ctx.fill()
  }
  ctx.restore()
  if (selected || labelled) {
    ctx.fillStyle = selected ? '#e4fff8' : '#a7c9cb'
    ctx.fillText(String(agent.id).padStart(2, '0'), agent.x + 11, agent.y - 9)
  }
}

export function paint(ctx: CanvasRenderingContext2D, view: View, frame: Snapshot, agents: Agent[], selectedId: number | null, layers: Layers, trails: Map<number, Point[]>) {
  const { width, height } = frame.config
  const { x, y, scale } = transform(view, frame)
  ctx.setTransform(view.pixelRatio, 0, 0, view.pixelRatio, 0, 0)
  ctx.clearRect(0, 0, view.width, view.height)
  ctx.save(); ctx.translate(x, y); ctx.scale(scale, scale)
  ctx.font = `${Math.max(10, 9 / scale)}px ui-monospace, Consolas, monospace`
  ctx.lineWidth = 1 / scale
  ctx.fillStyle = '#101a26'; ctx.fillRect(0, 0, width, height)
  const { cols, rows, cells } = frame.grid
  const dx = width / cols, dy = height / rows
  ctx.fillStyle = '#153335'
  for (let index = 0; index < cells.length; index++) {
    if (cells[index] === '1') ctx.fillRect((index % cols) * dx + 1, Math.floor(index / cols) * dy + 1, dx - 2, dy - 2)
  }
  if (layers.grid) {
    ctx.beginPath()
    for (let col = 1; col < cols; col++) { ctx.moveTo(col * dx, 0); ctx.lineTo(col * dx, height) }
    for (let row = 1; row < rows; row++) { ctx.moveTo(0, row * dy); ctx.lineTo(width, row * dy) }
    ctx.strokeStyle = '#1c2c3b'; ctx.stroke()
  }
  ctx.strokeStyle = '#344b5e'; ctx.strokeRect(0, 0, width, height)
  ctx.fillStyle = '#677f97'
  for (let col = 0; col <= width; col += 200) ctx.fillText(String(col).padStart(3, '0'), col + 4, -8 / scale)
  ctx.textAlign = 'right'
  for (let row = 100; row < height; row += 100) ctx.fillText(String(row), -7 / scale, row + 3)
  ctx.textAlign = 'left'
  ctx.save(); ctx.beginPath(); ctx.rect(0, 0, width, height); ctx.clip()

  for (const obstacle of frame.obstacles) {
    circle(ctx, obstacle.x, obstacle.y, obstacle.r)
    ctx.fillStyle = obstacle.moving ? '#352b32' : '#273745'
    ctx.strokeStyle = obstacle.moving ? '#9e7584' : '#526779'
    ctx.fill(); ctx.stroke()
    ctx.save(); ctx.clip(); ctx.beginPath()
    for (let offset = -2 * obstacle.r; offset < 2 * obstacle.r; offset += 8) {
      ctx.moveTo(obstacle.x + offset, obstacle.y + obstacle.r)
      ctx.lineTo(obstacle.x + offset + 2 * obstacle.r, obstacle.y - obstacle.r)
    }
    ctx.strokeStyle = obstacle.moving ? '#503b48' : '#354a5d'; ctx.stroke(); ctx.restore()
    if (obstacle.moving) {
      circle(ctx, obstacle.x, obstacle.y, obstacle.r + 5)
      ctx.setLineDash([3, 5]); ctx.strokeStyle = '#936977'; ctx.stroke(); ctx.setLineDash([])
    }
  }
  marker(ctx, frame.base, 'BASE', '#61e9c6', 24)
  if (frame.destination) marker(ctx, frame.destination, 'GATE', '#86b8ff', 34)
  if (frame.rendezvous) marker(ctx, frame.rendezvous, 'RENDEZVOUS', '#b7a9ff', 30)
  for (const target of frame.targets) marker(ctx, [target.x, target.y], `T${String(target.id).padStart(2, '0')}`, target.completed ? '#8ce3a9' : '#e9b973', 13)

  const byId = new Map(agents.map(agent => [agent.id, agent]))
  const selected = selectedId === null ? undefined : byId.get(selectedId)
  if (selected?.online && layers.links) {
    circle(ctx, selected.x, selected.y, frame.config.communication_range)
    ctx.fillStyle = '#65dec409'; ctx.fill()
    ctx.strokeStyle = '#66cbb977'; ctx.setLineDash([6, 6]); ctx.stroke(); ctx.setLineDash([])
  }
  if (layers.links) {
    ctx.beginPath()
    for (const [a, b] of frame.links) {
      const source = byId.get(a), target = byId.get(b)
      if (source && target) { ctx.moveTo(source.x, source.y); ctx.lineTo(target.x, target.y) }
    }
    ctx.strokeStyle = '#62e5c74a'; ctx.stroke()
  }
  if (layers.trails) {
    for (const agent of agents) {
      const trail = trails.get(agent.id)
      if (!trail || trail.length < 2) continue
      ctx.beginPath(); ctx.moveTo(...trail[0])
      for (let index = 1; index < trail.length; index++) ctx.lineTo(...trail[index])
      ctx.strokeStyle = `${stateColors[agent.state]}${selectedId === agent.id ? 'aa' : '55'}`; ctx.stroke()
    }
  }
  for (const agent of agents) drone(ctx, agent, selectedId === agent.id, agents.length <= 20 && scale >= 0.55)
  ctx.restore(); ctx.restore()
}
