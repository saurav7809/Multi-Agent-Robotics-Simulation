from math import hypot

Point = tuple[float, float]
ZERO: Point = (0.0, 0.0)


def add(a: Point, b: Point) -> Point:
    return a[0] + b[0], a[1] + b[1]


def subtract(a: Point, b: Point) -> Point:
    return a[0] - b[0], a[1] - b[1]


def scale(point: Point, factor: float) -> Point:
    return point[0] * factor, point[1] * factor


def dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def norm(point: Point) -> float:
    return hypot(*point)


def distance(a: Point, b: Point) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def unit(point: Point) -> Point:
    length = norm(point)
    return scale(point, 1 / length) if length > 1e-9 else ZERO


def limit(point: Point, maximum: float) -> Point:
    length = norm(point)
    return scale(point, maximum / length) if length > maximum else point


def arrive(position: Point, goal: Point, speed: float, slow_radius: float = 46) -> Point:
    return limit(scale(subtract(goal, position), speed / slow_radius), speed)
