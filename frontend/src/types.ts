export type Algorithm = 'boids' | 'leader-follower' | 'consensus' | 'auction' | 'avoidance' | 'coverage'
export type RunState = 'ready' | 'running' | 'paused' | 'completed' | 'timed_out'
export type AgentState = 'IDLE' | 'EXPLORING' | 'MOVING' | 'COMMUNICATING' | 'AVOIDING_OBSTACLE' | 'EXECUTING_TASK' | 'RETURNING' | 'FAILED'
export type Point = [number, number]
export type ScenarioId = 'formation-control' | 'area-exploration' | 'search-and-rescue' | 'obstacle-navigation' |
  'leader-failure' | 'communication-failure' | 'multi-target-allocation'

export interface Scenario {
  id: ScenarioId
  name: string
  description: string
  objective: string
  algorithm: Algorithm
  obstacle_density: number
  target_count: number
  duration: number
  scoring: 'coverage' | 'formation' | 'targets' | 'navigation' | 'recovery'
  incident: 'leader' | 'radio' | null
}

export interface SimulationConfig {
  agent_count: number
  width: number
  height: number
  speed: number
  agent_speed: number
  communication_range: number
  obstacle_density: number
  target_count: number
  duration: number
  algorithm: Algorithm
  seed: number
  update_hz: number
  packet_loss: number
  delay_ms: number
  separation: number
  alignment: number
  cohesion: number
}

export interface Agent {
  id: number
  x: number
  y: number
  vx: number
  vy: number
  heading: number
  battery: number
  state: AgentState
  kind: string
  health: number
  online: boolean
  neighbor_count: number
  task_id: number | null
  leader: number | null
  estimate: number | null
}

export interface Obstacle { id: number; x: number; y: number; r: number; moving: boolean }
export interface Target { id: number; x: number; y: number; kind: string; completed: boolean }

export interface Metrics {
  total_agents: number
  active_agents: number
  failed_agents: number
  returning_agents: number
  offline_agents: number
  mission_progress: number
  coverage: number
  average_battery: number
  failure_rate: number
  collisions: number
  connectivity: number
  average_task_time: number | null
  average_distance: number
  coordination_efficiency: number
  consensus_spread: number | null
  consensus_time: number | null
  consensus_reached: boolean
  tasks_total: number
  tasks_discovered: number
  tasks_completed: number
  tasks_assigned: number
  visited_cells: number
  valid_cells: number
  radio_links: number
  packets_sent: number
  packets_delivered: number
}

export interface Sample { time: number; metrics: Metrics }
export interface SimEvent { id: number; type: string; time: number; message: string; agent_id: number | null }

export interface Snapshot {
  session_id: string
  revision: number
  run_id: number
  status: RunState
  time: number
  scenario: ScenarioId
  config: SimulationConfig
  base: Point
  destination: Point | null
  rendezvous: Point | null
  leader_id: number | null
  grid: { cols: number; rows: number; cells: string }
  agents: Agent[]
  obstacles: Obstacle[]
  targets: Target[]
  links: [number, number][]
  metrics: Metrics
  events: SimEvent[]
}
