from math import cos, sin, sqrt

from ..agents import Agent, AgentState
from ..geometry import Point, add, arrive
from .core import Decision, LocalView


def meeting_point(view: LocalView, estimate: float) -> Point:
    if view.destination:
        return view.destination[0], view.destination[1] + (estimate - 0.5) * view.config.height * 0.28
    return view.config.width * (0.36 + 0.28 * estimate), view.config.height * 0.5


def decide(agent: Agent, view: LocalView) -> Decision:
    memory = agent.memory
    updated = False
    if view.decision_tick:
        samples = view.reports(agent)
        if samples and max(report.time for report in samples) > memory.estimate_stamp:
            mean = sum(report.estimate for report in samples) / len(samples)
            memory.estimate += 0.48 * (mean - memory.estimate)
            memory.estimate_stamp = max(report.time for report in samples)
            updated = True
    phase = (agent.id - 1) * 2.399963
    radius = 15 * sqrt(agent.id - 1)
    goal = add(meeting_point(view, memory.estimate), (radius * cos(phase), radius * sin(phase)))
    return arrive(agent.position, goal, agent.max_speed * 0.75), AgentState.COMMUNICATING if updated else AgentState.MOVING
