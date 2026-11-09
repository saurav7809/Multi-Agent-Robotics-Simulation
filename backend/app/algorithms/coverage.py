from math import cos, sin

from ..agents import Agent, AgentState
from ..geometry import arrive
from .core import Decision, LocalView, patrol


def decide(agent: Agent, view: LocalView) -> Decision:
    memory = agent.memory
    if view.decision_tick or memory.intent is None and memory.intent_until <= view.time:
        occupied = memory.visited | memory.blocked
        claimed = 0
        preferred_claims = 0
        for report in view.reports(agent):
            if report.intent is not None:
                bit = view.cell_bits[report.intent]
                claimed |= bit
                if report.sender < agent.id:
                    preferred_claims |= bit
        valid = memory.intent is not None and not (occupied | preferred_claims) & view.cell_bits[memory.intent]
        if not valid or memory.intent_until <= view.time:
            # Iterate only unseen, unclaimed cells. A small heading bias reduces zigzagging.
            available = ((1 << len(view.cell_centers)) - 1) & ~(occupied | claimed)
            previous = memory.intent
            memory.intent, best = None, float('inf')
            x, y = agent.position
            hx, hy = cos(agent.heading), sin(agent.heading)
            while available:
                bit = available & -available
                available ^= bit
                index = bit.bit_length() - 1
                cx, cy = view.cell_centers[index]
                dx, dy = cx - x, cy - y
                score = dx * dx + dy * dy - 18 * (hx * dx + hy * dy)
                if index == previous:
                    score += 140**2
                if score < best:
                    memory.intent, best = index, score
            memory.intent_until = view.time + (5 if memory.intent is not None else 1)
    goal = view.cell_centers[memory.intent] if memory.intent is not None else patrol(agent, view)
    return arrive(agent.position, goal, agent.max_speed, 29), AgentState.EXPLORING
