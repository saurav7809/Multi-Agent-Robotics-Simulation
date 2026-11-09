from ..agents import Agent, AgentState
from ..geometry import Point, ZERO, add, arrive, limit, norm, scale, subtract, unit
from .core import Decision, LocalView, patrol


def flock_terms(agent: Agent, view: LocalView) -> tuple[Point, Point, Point]:
    separation, alignment, center = ZERO, ZERO, ZERO
    count = 0
    for peer in view.contacts:
        if not peer.active:
            continue
        offset = subtract(agent.position, peer.position)
        gap = norm(offset)
        if gap < 52:
            separation = add(separation, scale(unit(offset), (52 - gap) / 52))
        alignment = add(alignment, peer.velocity)
        center = add(center, peer.position)
        count += 1
    if count == 0:
        return ZERO, ZERO, ZERO
    speed = agent.max_speed
    return (
        scale(limit(separation, 1), speed),
        subtract(scale(alignment, 1 / count), agent.velocity),
        limit(scale(subtract(scale(center, 1 / count), agent.position), 0.9), speed),
    )


def decide(agent: Agent, view: LocalView) -> Decision:
    separation, alignment, cohesion = flock_terms(agent, view)
    config = view.config
    bias = arrive(agent.position, view.destination or patrol(agent, view), agent.max_speed * 0.68)
    steering = add(scale(separation, config.separation), add(scale(alignment, config.alignment), scale(cohesion, config.cohesion)))
    return limit(add(bias, steering), agent.max_speed), AgentState.MOVING
