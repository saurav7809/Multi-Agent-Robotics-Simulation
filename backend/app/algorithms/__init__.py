from collections.abc import Callable

from ..agents import Agent
from ..config import Algorithm
from . import auction, avoidance, boids, consensus, coverage, leader
from .core import Decision, LocalView

POLICIES: dict[Algorithm, Callable[[Agent, LocalView], Decision]] = {
    Algorithm.BOIDS: boids.decide,
    Algorithm.LEADER_FOLLOWER: leader.decide,
    Algorithm.CONSENSUS: consensus.decide,
    Algorithm.AUCTION: auction.decide,
    Algorithm.AVOIDANCE: avoidance.decide,
    Algorithm.COVERAGE: coverage.decide,
}
