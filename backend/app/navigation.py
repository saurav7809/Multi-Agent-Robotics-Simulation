from collections.abc import Sequence
from dataclasses import dataclass
from math import cos, hypot, radians, sin

import numpy as np

from .agents import Agent
from .environment import AGENT_RADIUS, Environment
from .geometry import Point, add, distance, dot, limit, norm, scale, subtract, unit

SENSOR_RANGE = 140.0
ROTATIONS = tuple((angle, cos(radians(angle)), sin(radians(angle))) for angle in (
    18, -18, 34, -34, 53, -53, 72, -72, 92, -92, 120, -120, 155, -155, 180,
))


@dataclass(frozen=True, slots=True)
class Contact:
    id: int
    position: Point
    velocity: Point
    active: bool


class SpatialIndex:
    """One distance matrix shared by perception and radio discovery."""

    def __init__(self, agents: Sequence[Agent]):
        self.contacts = [Contact(agent.id, agent.position, agent.velocity, agent.active) for agent in agents]
        coords = np.asarray([contact.position for contact in self.contacts], dtype=float)
        self.distances_sq = _distances_squared(coords, coords)
        np.fill_diagonal(self.distances_sq, np.inf)

    def nearby(self, index: int, radius: float) -> list[Contact]:
        return [self.contacts[i] for i in np.flatnonzero(self.distances_sq[index] <= radius**2)]


def _distances_squared(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    delta = first[:, None, :] - second[None, :, :]
    return np.einsum('ijk,ijk->ij', delta, delta)


def steer(agent: Agent, desired: Point, nearby: Sequence[Contact], arena: Environment) -> tuple[Point, bool]:
    x, y = agent.position
    desired = limit(desired, agent.max_speed)
    velocity = desired
    heading = unit(desired)
    for peer in nearby:
        offset = subtract(agent.position, peer.position)
        if abs(offset[0]) > 57 or abs(offset[1]) > 57:
            continue
        gap = norm(offset)
        if gap < 27:
            velocity = add(velocity, scale(unit(offset), 2.9 * (27 - gap)))
        relative = subtract(desired, peer.velocity)
        if dot(offset, relative) < 0 and _closest(offset, relative, 0.43) < 21:
            # Each drone turns to its own side in a head-on encounter.
            velocity = add(velocity, scale((-heading[1], heading[0]), agent.max_speed * 0.42))
    vx = velocity[0] + 4.0 * (max(0, 27 - x) - max(0, x - (arena.width - 27)))
    vy = velocity[1] + 4.0 * (max(0, 27 - y) - max(0, y - (arena.height - 27)))
    velocity = limit((vx, vy), agent.max_speed)

    horizon = 0.87
    hazards: list[tuple[float, float, float, float, float, bool]] = []
    reach = 28 + horizon * (agent.max_speed + 27)
    for obstacle in arena.obstacles:
        ox, oy = x - obstacle.x, y - obstacle.y
        gap_sq = ox * ox + oy * oy
        if gap_sq < (obstacle.radius + reach)**2:
            margin = obstacle.radius + AGENT_RADIUS + 9
            hazards.append((ox, oy, obstacle.vx, obstacle.vy, margin, gap_sq < margin * margin))

    def clearance(candidate: Point) -> float:
        dx, dy = candidate
        cx, cy = x + dx * horizon, y + dy * horizon
        room = min(cx, cy, arena.width - cx, arena.height - cy) - AGENT_RADIUS
        for ox, oy, mx, my, margin, inside in hazards:
            rx, ry = dx - mx, dy - my
            approach = ox * rx + oy * ry
            if approach >= 0:
                # When already inside the safety buffer, score progress out of it.
                t = 0.22 if inside else 0.0
            else:
                t = min(horizon, -approach / max(0.001, rx * rx + ry * ry))
            room = min(room, hypot(ox + rx * t, oy + ry * t) - margin)
        return room

    agent.avoid_ticks = max(0, agent.avoid_ticks - 1)
    if clearance(velocity) >= 0:
        return velocity, distance(desired, velocity) > 11
    direction = unit(velocity) if norm(velocity) > 4 else (cos(agent.heading), sin(agent.heading))
    pace = min(agent.max_speed, max(norm(velocity), agent.max_speed * 0.62))
    score, best, side = -float('inf'), velocity, 0
    for angle, ca, sa in ROTATIONS:
        candidate = scale((ca * direction[0] - sa * direction[1], sa * direction[0] + ca * direction[1]), pace)
        gap = clearance(candidate)
        turn = 1 if angle > 0 else -1
        preference = 0.23 if agent.avoid_ticks and agent.avoid_side == turn else 0.0
        value = ca + preference + min(14, gap) * (0.018 if gap >= 0 else 0.16)
        if value > score:
            score, best, side = value, candidate, turn
    agent.avoid_side, agent.avoid_ticks = side, 22
    return best, True


def _closest(offset: Point, velocity: Point, horizon: float) -> float:
    speed_sq = dot(velocity, velocity)
    t = max(0.0, min(horizon, -dot(offset, velocity) / speed_sq)) if speed_sq > 0.001 else 0.0
    return norm(add(offset, scale(velocity, t)))


def resolve_contacts(agents: list[Agent], arena: Environment) -> set[tuple[str, int, int]]:
    contacts: set[tuple[str, int, int]] = set()
    obstacles = np.asarray([item.position for item in arena.obstacles], dtype=float).reshape(-1, 2)
    obstacle_limits = np.asarray([(item.radius + AGENT_RADIUS)**2 for item in arena.obstacles])
    operational = np.asarray([agent.active for agent in agents], dtype=bool)
    # Reproject after pair separation so contact corrections cannot leave a drone inside an obstacle.
    for _ in range(2):
        positions = np.asarray([agent.position for agent in agents], dtype=float)
        pairs = (_distances_squared(positions, positions) < (2 * AGENT_RADIUS)**2) & (operational[:, None] | operational[None, :])
        corrected = False
        for a, b in zip(*np.nonzero(np.triu(pairs, 1))):
            first, second = agents[a], agents[b]
            offset = subtract(first.position, second.position)
            gap = norm(offset)
            if gap >= 2 * AGENT_RADIUS:
                continue
            contacts.add(('agent', first.id, second.id))
            normal = unit(offset) if gap else (0.0, 1.0)
            overlap = 2 * AGENT_RADIUS - gap + 0.02
            split = overlap / (int(first.active) + int(second.active))
            if first.active:
                first.position = arena.clamp(add(first.position, scale(normal, split)))
                first.stop_normal(normal)
            if second.active:
                second.position = arena.clamp(add(second.position, scale(normal, -split)))
                second.stop_normal(scale(normal, -1))
            corrected = True
        if corrected:
            positions = np.asarray([agent.position for agent in agents], dtype=float)
        overlaps = (_distances_squared(positions, obstacles) < obstacle_limits) & operational[:, None]
        for index, obstacle_index in zip(*np.nonzero(overlaps)):
            agent, obstacle = agents[index], arena.obstacles[obstacle_index]
            offset = subtract(agent.position, obstacle.position)
            gap = norm(offset)
            minimum = obstacle.radius + AGENT_RADIUS
            if gap >= minimum:
                continue
            contacts.add(('obstacle', agent.id, obstacle.id))
            normal = unit(offset) if gap else (0.0, 1.0)
            agent.position = arena.clamp(add(obstacle.position, scale(normal, minimum + 0.02)))
            agent.stop_normal(normal)
            corrected = True
        if not corrected:
            break
    return contacts
