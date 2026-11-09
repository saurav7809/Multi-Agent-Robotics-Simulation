from math import cos, sin, sqrt

from ..agents import Agent, AgentState
from ..geometry import Point, add, arrive, limit, scale, subtract
from ..protocol import Beacon
from .core import Decision, LocalView, patrol


def station(agent_id: int, leader: Beacon) -> Point:
    if agent_id == leader.agent_id:
        return leader.position
    slot = agent_id - 1 - int(agent_id > leader.agent_id)
    angle = slot * 2.399963 + leader.heading
    radius = 17 * sqrt(slot + 1)
    return add(leader.position, (radius * cos(angle) - 19 * cos(leader.heading), radius * sin(angle) - 19 * sin(leader.heading)))


def decide(agent: Agent, view: LocalView) -> Decision:
    memory = agent.memory
    if view.decision_tick:
        candidates = [memory.leader, *(report.leader for report in view.reports(agent))]
        ttl = 2.4 + 2 * view.config.delay_ms / 1000
        current = min(
            (beacon for beacon in candidates if beacon is not None and beacon.agent_id < agent.id and view.time - beacon.time <= ttl),
            key=lambda beacon: (beacon.agent_id, -beacon.time),
            default=None,
        )
        memory.leader = current or Beacon(agent.id, view.time, agent.position, agent.velocity, agent.heading)
    leader = memory.leader
    if leader is None or leader.agent_id == agent.id:
        return arrive(agent.position, view.destination or patrol(agent, view), agent.max_speed * 0.70), AgentState.MOVING
    slot = add(station(agent.id, leader), scale(leader.velocity, min(0.4, view.time - leader.time)))
    velocity = add(scale(subtract(slot, agent.position), 1.15), leader.velocity)
    return limit(velocity, agent.max_speed), AgentState.MOVING
