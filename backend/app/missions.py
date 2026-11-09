from collections.abc import Sequence
from dataclasses import dataclass, field
from math import ceil, sqrt

from .agents import Agent, AgentState
from .algorithms.leader import station
from .environment import Environment
from .geometry import Point, distance
from .protocol import Beacon
from .scenarios import Objective, Scenario

TARGET_HOLD_SECONDS = {"explore": 0.55, "inspect": 1.25, "coverage": 0.85, "rescue": 1.4}
TARGET_RADIUS = 25
NAVIGATION_GATE_RADIUS = 116
COVERAGE_GOAL = 80
INCIDENT_AT = 8.0
RADIO_RESTORE_AT = 16.0


@dataclass(slots=True)
class Mission:
    scenario: Scenario
    arrived: set[int] = field(default_factory=set)
    incident_started: bool = False
    incident_finished: bool = False
    jammed: set[int] = field(default_factory=set)
    previous_leader: int | None = None

    def evaluate(
        self, arena: Environment, agents: Sequence[Agent], leader: Agent | None,
        time: float, stable_since: float | None, spread: float | None,
    ) -> float:
        objective = self.scenario.scoring
        if objective == Objective.COVERAGE:
            return min(100, 100 * arena.grid.percentage / COVERAGE_GOAL)
        if objective == Objective.TARGETS:
            return self._target_progress(arena)
        if objective == Objective.RECOVERY:
            return self._radio_progress(time, stable_since, spread)
        available = [agent for agent in agents if agent.active and agent.state != AgentState.RETURNING]
        if not available:
            return 0.0
        if objective == Objective.NAVIGATION:
            self.arrived.update(agent.id for agent in available if distance(agent.position, arena.destination) <= NAVIGATION_GATE_RADIUS)
            arrived = sum(agent.id in self.arrived for agent in available)
            return min(100, 100 * arrived / ceil(0.8 * len(available)))
        return self._formation_progress(arena, available, leader)

    def _target_progress(self, arena: Environment) -> float:
        if not arena.targets:
            return 0.0
        discovered = sum(target.discovered for target in arena.targets)
        completed = sum(target.completed_at is not None for target in arena.targets)
        if "rescue" in self.scenario.target_kinds:
            return 100 * (0.35 * discovered + 0.65 * completed) / len(arena.targets)
        return 100 * completed / len(arena.targets)

    def _radio_progress(self, time: float, stable_since: float | None, spread: float | None) -> float:
        if not self.incident_started:
            return min(25, 25 * time / INCIDENT_AT)
        if not self.incident_finished:
            return min(55, 25 + 30 * (time - INCIDENT_AT) / (RADIO_RESTORE_AT - INCIDENT_AT))
        if stable_since is not None and time - max(RADIO_RESTORE_AT, stable_since) >= 2:
            return 100.0
        return 55 + 39 * (1 - min(1, (spread or 0) * 2))

    def _formation_progress(self, arena: Environment, available: list[Agent], leader: Agent | None) -> float:
        center: Point
        if leader:
            center = leader.position
            beacon = Beacon(leader.id, 0, leader.position, leader.velocity, leader.heading)
            aligned = sum(distance(agent.position, station(agent.id, beacon)) <= 48 for agent in available)
        else:
            center = (
                sum(agent.position[0] for agent in available) / len(available),
                sum(agent.position[1] for agent in available) / len(available),
            )
            aligned = sum(distance(agent.position, center) <= 50 + 12 * sqrt(len(available)) for agent in available)
        gap = distance(center, arena.destination)
        recovered = self.scenario.incident != "leader" or self.incident_finished
        if gap <= 44 and aligned >= ceil(0.75 * len(available)) and len(available) >= 2 and recovered:
            return 100.0
        travel = max(0, 1 - gap / distance(arena.base, arena.destination))
        return min(99.0, 100 * travel * (0.75 + 0.25 * aligned / len(available)))
