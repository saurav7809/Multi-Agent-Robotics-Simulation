from ..agents import Agent, AgentState
from ..geometry import arrive
from .core import Decision, LocalView, patrol


def decide(agent: Agent, view: LocalView) -> Decision:
    goal = patrol(agent, view)
    if view.destination:
        # Independent lanes spread arrivals around the goal without central assignments.
        x, y = view.destination
        goal = (x + ((agent.id - 1) // 9 % 5 - 2) * 23, y + ((agent.id - 1) % 9 - 4) * 25)
    return arrive(agent.position, goal, agent.max_speed), AgentState.MOVING
