from dataclasses import dataclass, field
from enum import StrEnum
from math import atan2

from .environment import Environment
from .geometry import Point, ZERO, add, distance, dot, limit, norm, scale, subtract
from .protocol import Memory


class AgentState(StrEnum):
    IDLE = "IDLE"
    EXPLORING = "EXPLORING"
    MOVING = "MOVING"
    COMMUNICATING = "COMMUNICATING"
    AVOIDING = "AVOIDING_OBSTACLE"
    EXECUTING = "EXECUTING_TASK"
    RETURNING = "RETURNING"
    FAILED = "FAILED"


@dataclass(slots=True)
class Agent:
    id: int
    position: Point
    max_speed: float
    velocity: Point = ZERO
    acceleration: Point = ZERO
    heading: float = 0.0
    battery: float = 100.0
    state: AgentState = AgentState.IDLE
    kind: str = "scout"
    health: float = 1.0
    radio_enabled: bool = True
    neighbors: tuple[int, ...] = ()
    task_id: int | None = None
    distance_travelled: float = 0.0
    memory: Memory = field(default_factory=Memory)
    avoid_side: int = 0
    avoid_ticks: int = 0
    interaction_id: int | None = None
    dwell: int = 0

    @property
    def active(self) -> bool:
        return self.state != AgentState.FAILED

    @property
    def online(self) -> bool:
        return self.active and self.radio_enabled

    def advance(self, desired: Point, arena: Environment, dt: float) -> None:
        if not self.active:
            return
        delta = limit(subtract(limit(desired, self.max_speed), self.velocity), 190 * dt)
        self.acceleration = scale(delta, 1 / dt)
        self.velocity = limit(add(self.velocity, delta), self.max_speed)
        self.position, previous = arena.clamp(add(self.position, scale(self.velocity, dt))), self.position
        self.velocity = scale(subtract(self.position, previous), 1 / dt)
        if norm(self.velocity) > 1:
            self.heading = atan2(self.velocity[1], self.velocity[0])
        travelled = distance(self.position, previous)
        self.distance_travelled += travelled
        self.battery = max(0.0, self.battery - 0.085 * dt - 0.0022 * travelled)

    def stop_normal(self, normal: Point) -> None:
        inward = dot(self.velocity, normal)
        if inward < 0:
            self.velocity = subtract(self.velocity, scale(normal, inward))

    def fail(self) -> None:
        self.state, self.health, self.velocity, self.acceleration = AgentState.FAILED, 0.0, ZERO, ZERO
        self.task_id, self.neighbors = None, ()
        self.interaction_id, self.dwell = None, 0
        self.memory.bid = self.memory.leader = None
        self.memory.reports.clear()

    def restore(self) -> None:
        self.state, self.health, self.battery, self.radio_enabled = AgentState.IDLE, 1.0, 100.0, True

    def snapshot(self) -> dict[str, object]:
        return {
            "id": self.id, "x": round(self.position[0], 2), "y": round(self.position[1], 2),
            "vx": round(self.velocity[0], 2), "vy": round(self.velocity[1], 2), "heading": round(self.heading, 3),
            "battery": round(self.battery, 2), "state": self.state, "kind": self.kind, "health": self.health,
            "online": self.online, "neighbor_count": len(self.neighbors), "task_id": self.task_id,
        }
