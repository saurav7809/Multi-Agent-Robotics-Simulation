from dataclasses import dataclass
from math import ceil, cos, floor, sin, tau

import numpy as np

from .config import SimulationConfig
from .geometry import Point, distance

AGENT_RADIUS = 8.0


@dataclass(slots=True)
class Obstacle:
    id: int
    x: float
    y: float
    radius: float
    vx: float = 0.0
    vy: float = 0.0

    @property
    def position(self) -> Point:
        return self.x, self.y

    @property
    def moving(self) -> bool:
        return bool(self.vx or self.vy)

    def advance(self, dt: float, width: int, height: int) -> None:
        if not self.moving:
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        if not self.radius <= self.x <= width - self.radius:
            self.x = min(width - self.radius, max(self.radius, self.x))
            self.vx = -self.vx
        if not self.radius <= self.y <= height - self.radius:
            self.y = min(height - self.radius, max(self.radius, self.y))
            self.vy = -self.vy


@dataclass(slots=True)
class Target:
    id: int
    x: float
    y: float
    kind: str
    discovered: bool = True
    completed_at: float | None = None
    completed_by: int | None = None
    discovered_at: float | None = None

    @property
    def position(self) -> Point:
        return self.x, self.y


class CoverageGrid:
    def __init__(self, width: int, height: int, obstacles: list[Obstacle]):
        self.cols, self.rows = ceil(width / 48), ceil(height / 48)
        self.dx, self.dy = width / self.cols, height / self.rows
        self.centers = tuple(
            ((col + 0.5) * self.dx, (row + 0.5) * self.dy)
            for row in range(self.rows) for col in range(self.cols)
        )
        self.bits = tuple(1 << index for index in range(len(self.centers)))
        self.valid = sum(
            bit for bit, point in zip(self.bits, self.centers)
            if all(distance(point, item.position) > item.radius + AGENT_RADIUS for item in obstacles if not item.moving)
        )
        self.visited = 0
        self.valid_count = self.valid.bit_count()

    def sense(self, position: Point, radius: float = 49) -> int:
        x, y = position
        mask = 0
        for row in range(max(0, floor((y - radius) / self.dy)), min(self.rows, floor((y + radius) / self.dy) + 1)):
            for col in range(max(0, floor((x - radius) / self.dx)), min(self.cols, floor((x + radius) / self.dx) + 1)):
                index = row * self.cols + col
                cx, cy = self.centers[index]
                if (cx - x) ** 2 + (cy - y) ** 2 <= radius**2:
                    mask |= self.bits[index]
        return mask

    @property
    def percentage(self) -> float:
        return 100 * self.visited.bit_count() / self.valid_count

    def cells(self) -> str:
        return ''.join('1' if self.visited & bit else '0' if self.valid & bit else '2' for bit in self.bits)


class Environment:
    """Seeded layout. Moving obstacles stay inside the arena and reflect at its walls."""

    def __init__(self, config: SimulationConfig, target_kinds: tuple[str, ...] = ()):
        self.width, self.height = config.width, config.height
        self.base = (round(self.width * 0.16), round(self.height * 0.52))
        self.destination = (round(self.width * 0.85), round(self.height * 0.49))
        self.obstacles: list[Obstacle] = []
        self.targets: list[Target] = []
        rng = np.random.default_rng(config.seed)
        for index in range(config.obstacle_density):
            radius = float(rng.uniform(17, 34))
            for _ in range(240):
                point = self._sample(rng, radius + 14)
                if not self.clear(point, radius + 14):
                    continue
                if distance(point, self.base) < radius + 115 or distance(point, self.destination) < radius + 88:
                    continue
                self.obstacles.append(self._obstacle(index, point, radius, rng))
                break

        target_count = config.target_count if target_kinds else 0
        for index in range(target_count):
            for _ in range(400):
                point = self._sample(rng, 44)
                if distance(point, self.base) < 125 or not self.clear(point, 23):
                    continue
                if any(distance(point, other.position) < 42 for other in self.targets):
                    continue
                self.targets.append(self._target(index, point, target_kinds))
                break
        if len(self.obstacles) != config.obstacle_density or len(self.targets) != target_count:
            self._place_dense_layout(config.obstacle_density, target_count, target_kinds, rng)
        self.grid = CoverageGrid(self.width, self.height, self.obstacles)
        self.block_masks = {
            item.id: self.grid.sense(item.position, item.radius + AGENT_RADIUS)
            for item in self.obstacles if not item.moving
        }

    def _sample(self, rng: np.random.Generator, margin: float) -> Point:
        return float(rng.uniform(margin, self.width - margin)), float(rng.uniform(margin, self.height - margin))

    @staticmethod
    def _obstacle(index: int, point: Point, radius: float, rng: np.random.Generator) -> Obstacle:
        angle = float(rng.uniform(0, tau))
        speed = float(rng.uniform(14, 25)) if index % 4 == 3 else 0.0
        return Obstacle(index + 1, *point, radius, speed * cos(angle), speed * sin(angle))

    @staticmethod
    def _target(index: int, point: Point, kinds: tuple[str, ...]) -> Target:
        kind = kinds[index % len(kinds)]
        hidden = kind == "rescue"
        return Target(index + 1, *point, kind, not hidden, discovered_at=None if hidden else 0.0)

    def _place_dense_layout(
        self, obstacle_count: int, target_count: int, kinds: tuple[str, ...], rng: np.random.Generator,
    ) -> None:
        # Minimum dimensions yield 130 slots. The two exclusion circles remove at most 61.
        # A 47-unit spacing with radii up to 14 leaves at least 19 units for a 16-unit drone.
        slots = [
            (float(x), float(y))
            for y in range(24, self.height - 23, 47) for x in range(24, self.width - 23, 47)
            if distance((x, y), self.base) >= 134 and distance((x, y), self.destination) >= 106
        ]
        rng.shuffle(slots)
        self.obstacles = [
            self._obstacle(index, slots[index], float(rng.uniform(10, 14)), rng)
            for index in range(obstacle_count)
        ]
        self.targets = [
            self._target(index, slots[obstacle_count + index], kinds)
            for index in range(target_count)
        ]

    def clamp(self, point: Point, margin: float = AGENT_RADIUS) -> Point:
        return min(self.width - margin, max(margin, point[0])), min(self.height - margin, max(margin, point[1]))

    def clear(self, point: Point, margin: float) -> bool:
        return all(distance(point, obstacle.position) >= obstacle.radius + margin for obstacle in self.obstacles)

    def advance(self, dt: float) -> None:
        for obstacle in self.obstacles:
            obstacle.advance(dt, self.width, self.height)
