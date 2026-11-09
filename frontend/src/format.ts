import type { AgentState, Algorithm, RunState } from './types'

export const algorithms: Record<Algorithm, string> = {
  coverage: 'Area coverage',
  boids: 'Boids / flocking',
  'leader-follower': 'Leader–follower',
  consensus: 'Distributed consensus',
  auction: 'Distributed task auction',
  avoidance: 'Obstacle avoidance',
}

export const agentStates: Record<AgentState, string> = {
  IDLE: 'Idle', EXPLORING: 'Exploring', MOVING: 'Moving', COMMUNICATING: 'Communicating',
  AVOIDING_OBSTACLE: 'Avoiding', EXECUTING_TASK: 'Executing', RETURNING: 'Returning', FAILED: 'Failed',
}

export const runStates: Record<RunState, string> = {
  ready: 'Ready', running: 'Running', paused: 'Paused', completed: 'Complete', timed_out: 'Timed out',
}

export const unitId = (id: number) => `U-${String(id).padStart(2, '0')}`
export const targetId = (id: number) => `T${String(id).padStart(2, '0')}`
export const runId = (id: number) => `#${String(id).padStart(4, '0')}`
export const percent = (value: number) => String(Number.isInteger(value) ? value : value.toFixed(1)) + '%'

export function clock(seconds: number, decimals = false) {
  const minutes = Math.floor(seconds / 60)
  const whole = Math.floor(seconds) % 60
  const fraction = decimals ? `.${Math.floor(seconds * 10) % 10}` : ''
  return `${String(minutes).padStart(2, '0')}:${String(whole).padStart(2, '0')}${fraction}`
}
