// @vitest-environment jsdom

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import type { Scenario, Snapshot } from './types'

vi.mock('./simulation/ArenaCanvas', () => ({ default: () => <canvas aria-label="Simulation arena" /> }))
vi.mock('./components/AnalyticsPanel', () => ({ default: () => <section aria-label="Live analytics" /> }))

const scenario: Scenario = {
  id: 'area-exploration', name: 'Area exploration', description: 'Survey unknown terrain.',
  objective: 'Survey at least 80% of the traversable grid.', algorithm: 'coverage',
  obstacle_density: 9, target_count: 5, duration: 180, scoring: 'coverage', incident: null,
}

function initialFrame(): Snapshot {
  return {
    session_id: 'initial-session', revision: 1, run_id: 1, status: 'ready', time: 0,
    scenario: scenario.id, base: [160, 290], destination: null, rendezvous: null, leader_id: null,
    config: {
      agent_count: 10, width: 1000, height: 580, speed: 1, agent_speed: 68, communication_range: 185,
      obstacle_density: 9, target_count: 5, duration: 180, algorithm: 'coverage', seed: 42, update_hz: 12,
      packet_loss: 0, delay_ms: 0, separation: 1.65, alignment: 0.85, cohesion: 0.75,
    },
    grid: { cols: 2, rows: 2, cells: '1000' }, obstacles: [], targets: [], links: [], events: [],
    agents: Array.from({ length: 10 }, (_, index) => ({
      id: index + 1, x: 160 + index * 24, y: 290, vx: 0, vy: 0, heading: 0, battery: 100,
      state: 'IDLE', kind: 'scout', health: 1, online: true, neighbor_count: 3,
      task_id: null, leader: null, estimate: null,
    })),
    metrics: {
      total_agents: 10, active_agents: 10, failed_agents: 0, returning_agents: 0, offline_agents: 0,
      mission_progress: 31.25, coverage: 25, average_battery: 100, failure_rate: 0,
      collisions: 0, connectivity: 100, average_task_time: null, average_distance: 0,
      coordination_efficiency: 0, consensus_spread: null, consensus_time: null, consensus_reached: false,
      tasks_total: 5, tasks_discovered: 5, tasks_completed: 0, tasks_assigned: 0, visited_cells: 1,
      valid_cells: 4, radio_links: 15, packets_sent: 0, packets_delivered: 0,
    },
  }
}

class FakeSocket {
  static connections: FakeSocket[] = []
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null

  constructor(public readonly url: URL) {
    FakeSocket.connections.push(this)
  }

  close() { this.onclose?.() }

  sendFrame(frame: Snapshot) { this.onmessage?.({ data: JSON.stringify(frame) }) }
}

let current: Snapshot
let commands: { path: string; body?: Record<string, unknown> }[]

beforeEach(() => {
  current = initialFrame()
  commands = []
  FakeSocket.connections = []
  vi.stubGlobal('WebSocket', FakeSocket)
  vi.stubGlobal('fetch', vi.fn(async (path: string, options?: RequestInit) => {
    if (path === '/api/scenarios') return Response.json([scenario])
    if (path === '/api/events') return Response.json({ session_id: current.session_id, run_id: current.run_id, events: [] })
    if (options?.method === 'POST') {
      const body = typeof options.body === 'string' ? JSON.parse(options.body) : undefined
      commands.push({ path, body })
      current = { ...current, revision: current.revision + 1 }
      if (path.endsWith('/start') || path.endsWith('/resume')) current.status = 'running'
      if (path.endsWith('/pause')) current.status = 'paused'
      if (path.endsWith('/reset')) current = { ...initialFrame(), revision: current.revision + 1, run_id: current.run_id + 1 }
      if (path.endsWith('/configure')) {
        current = { ...current, run_id: current.run_id + 1, config: { ...current.config, ...body } }
      }
      if (path.endsWith('/agents/2/fail')) {
        current.agents = current.agents.map(agent => agent.id === 2 ? { ...agent, state: 'FAILED', online: false } : agent)
        current.metrics = { ...current.metrics, active_agents: 9, failed_agents: 1 }
      }
    }
    return Response.json(current)
  }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('mission console', () => {
  it('renders the arena, metrics, scenario, and inspector from the API', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Mission control' })).toBeTruthy()
    expect(await screen.findByRole('heading', { name: 'Simulation arena' })).toBeTruthy()
    expect(screen.getByText('25%')).toBeTruthy()
    expect(await screen.findByText(scenario.objective)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Agent inspector' })).toBeTruthy()
  })

  it('sends start, pause, resume, and reset commands', async () => {
    render(<App />)
    for (const label of ['Start', 'Pause', 'Resume', 'Reset']) {
      fireEvent.click(await screen.findByRole('button', { name: label }))
      await waitFor(() => expect(commands.at(-1)?.path).toBe('/api/simulation/' + label.toLowerCase()))
    }
    expect(await screen.findByRole('button', { name: 'Start' })).toBeTruthy()
  })

  it('stages an algorithm change until configuration is applied', async () => {
    render(<App />)
    fireEvent.change(await screen.findByLabelText('Swarm algorithm'), { target: { value: 'boids' } })
    expect(commands).toHaveLength(0)
    fireEvent.click(screen.getByRole('button', { name: 'Apply configuration' }))
    await waitFor(() => expect(commands.at(-1)?.body?.algorithm).toBe('boids'))
  })

  it('selects a drone and reports its failed state', async () => {
    render(<App />)
    fireEvent.change(await screen.findByLabelText('Select agent'), { target: { value: '2' } })
    expect(screen.getByText('U-02', { exact: true })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Fail agent' }))
    expect(await screen.findByRole('button', { name: 'Restore agent' })).toBeTruthy()
    expect(commands.at(-1)?.path).toBe('/api/agents/2/fail')
  })

  it('uses new WebSocket frames and rejects older revisions in the same session', async () => {
    render(<App />)
    await screen.findByRole('button', { name: 'Start' })
    await waitFor(() => expect(FakeSocket.connections).toHaveLength(1))
    const socket = FakeSocket.connections[0]
    expect(socket.url.pathname).toBe('/ws/simulation')
    act(() => socket.sendFrame({ ...current, revision: 5, status: 'running', time: 2 }))
    expect(await screen.findByText('Telemetry live')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Pause' })).toBeTruthy()
    act(() => socket.sendFrame({ ...current, revision: 3, status: 'paused' }))
    expect(screen.queryByRole('button', { name: 'Resume' })).toBeNull()
    act(() => socket.sendFrame({ ...initialFrame(), session_id: 'restarted-server' }))
    expect(await screen.findByRole('button', { name: 'Start' })).toBeTruthy()
  })
})
