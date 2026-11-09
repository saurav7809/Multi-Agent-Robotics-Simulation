from ..agents import Agent, AgentState
from ..geometry import arrive, distance
from ..protocol import Bid
from . import coverage
from .core import Decision, LocalView


def decide(agent: Agent, view: LocalView) -> Decision:
    memory = agent.memory
    if view.decision_tick:
        competitors: dict[int, tuple[float, int]] = {}
        for report in view.reports(agent):
            if report.bid is not None:
                bid = report.bid
                rank = (bid.cost, bid.agent_id)
                competitors[bid.task_id] = min(rank, competitors.get(bid.task_id, rank))
        previous = agent.task_id
        winner = None
        for task in memory.tasks.values():
            if task.completed:
                continue
            switching = 2.5 if previous not in (None, task.id) else 0.0
            cost = distance(agent.position, task.position) / agent.max_speed + (100 - agent.battery) * 0.075 + switching
            rank = (cost, agent.id)
            if rank < competitors.get(task.id, (float('inf'), 0)) and (winner is None or cost < winner.cost):
                winner = Bid(agent.id, task.id, cost)
        memory.bid = winner
        agent.task_id = winner.task_id if winner else None
    if agent.task_id is None:
        return coverage.decide(agent, view)
    memory.intent = None
    task = memory.tasks[agent.task_id]
    return arrive(agent.position, task.position, agent.max_speed, 27), AgentState.EXECUTING
