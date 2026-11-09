from collections.abc import Sequence
from typing import TypedDict

from .agents import Agent, AgentState
from .communication import RadioNetwork
from .environment import Environment


class Metrics(TypedDict):
    total_agents: int
    active_agents: int
    failed_agents: int
    returning_agents: int
    offline_agents: int
    mission_progress: float
    coverage: float
    average_battery: float
    failure_rate: float
    collisions: int
    connectivity: float
    average_task_time: float | None
    average_distance: float
    coordination_efficiency: float
    consensus_spread: float | None
    consensus_time: float | None
    consensus_reached: bool
    tasks_total: int
    tasks_discovered: int
    tasks_completed: int
    tasks_assigned: int
    visited_cells: int
    valid_cells: int
    radio_links: int
    packets_sent: int
    packets_delivered: int


class Sample(TypedDict):
    time: float
    metrics: Metrics


def calculate(
    agents: Sequence[Agent], arena: Environment, radio: RadioNetwork, progress: float, collisions: int,
    productive_ticks: int, operational_ticks: int, spread: float | None, consensus_time: float | None,
    consensus_reached: bool,
) -> Metrics:
    total = len(agents)
    active = sum(agent.active for agent in agents)
    completed = [target.completed_at - (target.discovered_at or 0.0) for target in arena.targets if target.completed_at is not None]
    open_targets = {target.id for target in arena.targets if target.discovered and target.completed_at is None}
    assigned = {agent.task_id for agent in agents if agent.active and agent.task_id in open_targets}
    return {
        "total_agents": total, "active_agents": active, "failed_agents": total - active,
        "returning_agents": sum(agent.state == AgentState.RETURNING for agent in agents),
        "offline_agents": sum(agent.active and not agent.online for agent in agents),
        "mission_progress": round(progress, 2), "coverage": round(arena.grid.percentage, 2),
        "average_battery": round(sum(agent.battery for agent in agents) / total, 2),
        "failure_rate": round(100 * (total - active) / total, 2), "collisions": collisions,
        "connectivity": round(100 * radio.largest / active, 2) if active else 0,
        "average_task_time": round(sum(completed) / len(completed), 2) if completed else None,
        "average_distance": round(sum(agent.distance_travelled for agent in agents) / total, 2),
        "coordination_efficiency": round(100 * productive_ticks / operational_ticks, 2) if operational_ticks else 0,
        "consensus_spread": round(spread, 4) if spread is not None else None,
        "consensus_time": consensus_time, "consensus_reached": consensus_reached,
        "tasks_total": len(arena.targets), "tasks_discovered": sum(target.discovered for target in arena.targets),
        "tasks_completed": len(completed), "tasks_assigned": len(assigned),
        "visited_cells": arena.grid.visited.bit_count(), "valid_cells": arena.grid.valid_count,
        "radio_links": radio.edge_count, "packets_sent": radio.sent, "packets_delivered": radio.delivered,
    }
