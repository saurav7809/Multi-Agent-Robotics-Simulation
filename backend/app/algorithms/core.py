from collections.abc import Sequence
from dataclasses import dataclass
from math import cos, sin

from ..agents import Agent, AgentState
from ..config import SimulationConfig
from ..geometry import Point
from ..navigation import Contact
from ..protocol import Report

Decision = tuple[Point, AgentState]


@dataclass(frozen=True, slots=True)
class LocalView:
    time: float
    config: SimulationConfig
    contacts: Sequence[Contact]
    cell_centers: tuple[Point, ...]
    cell_bits: tuple[int, ...]
    destination: Point | None = None
    decision_tick: bool = True

    def reports(self, agent: Agent) -> list[Report]:
        ttl = 1.6 + self.config.delay_ms / 1000
        return [report for report in agent.memory.reports.values() if self.time - report.time <= ttl] if agent.online else []


def patrol(agent: Agent, view: LocalView) -> Point:
    angle = int(view.time / 6) * 1.12 + agent.id * 2.39996
    return view.config.width * (0.5 + 0.38 * cos(angle)), view.config.height * (0.5 + 0.38 * sin(angle))
