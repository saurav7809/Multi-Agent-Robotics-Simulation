from math import pi

import pytest

from app.agents import Agent
from app.algorithms import POLICIES, auction, boids, consensus, coverage, leader
from app.algorithms.core import LocalView
from app.config import Algorithm, SimulationConfig
from app.environment import Environment, Obstacle
from app.geometry import arrive, distance, norm
from app.navigation import Contact, steer
from app.protocol import Beacon, Bid, Report, TaskObservation
from app.simulation import DT, Simulation


def report(sender, *, leader=None, bid=None, estimate=0.5, visited=0, intent=None):
    return Report(sender, 1.0, (100, 100), visited, 0, intent, estimate, leader, bid)


def view(contacts=(), time=1.0, goal=None):
    return LocalView(time, SimulationConfig(), contacts, ((60, 50), (100, 100), (150, 100)), (1, 2, 4), goal)


def test_flock_terms_separation_alignment_cohesion():
    own = Agent(1, (100, 100), 68, velocity=(0, 10))
    peer = Contact(2, (125, 100), (40, 0), True)
    separation, alignment, cohesion = boids.flock_terms(own, view((peer,)))
    assert separation[0] < 0 and separation[1] == 0
    assert alignment == (40, -10)
    assert cohesion[0] > 0 and cohesion[1] == 0


def test_formation_rotates_and_re_elects_after_expiry():
    own = Agent(2, (100, 100), 68)
    original = Beacon(1, 1.0, (180, 100), (20, 0), 0)
    turned = Beacon(1, 1.0, (180, 100), (0, 20), pi / 2)
    assert leader.station(2, original) != leader.station(2, turned)
    own.memory.receive(report(1, leader=original))
    leader.decide(own, view())
    assert own.memory.leader == original
    leader.decide(own, view(time=5))
    assert own.memory.leader.agent_id == own.id


def test_consensus_uses_fresh_neighbor_samples_once():
    own = Agent(2, (100, 100), 68)
    own.memory.estimate = 0.2
    own.memory.receive(report(1, estimate=0.8))
    consensus.decide(own, view())
    assert own.memory.estimate == pytest.approx(0.488)
    own.radio_enabled = False
    consensus.decide(own, view(time=1.4))
    assert own.memory.estimate == pytest.approx(0.488)


def test_auction_yields_to_lower_bid_and_reclaims_expired_assignment():
    own = Agent(2, (100, 100), 68)
    own.memory.observe(TaskObservation(1, (120, 100), 'inspect', False))
    own.memory.observe(TaskObservation(2, (185, 100), 'coverage', False))
    own.memory.receive(report(1, bid=Bid(1, 1, 0.1)))
    auction.decide(own, view())
    assert own.task_id == 2
    own.memory.observe(TaskObservation(2, (185, 100), 'coverage', True))
    auction.decide(own, view(time=4))
    assert own.task_id == 1


def test_coverage_avoids_reported_cells_and_claims():
    own = Agent(2, (100, 100), 68)
    own.memory.receive(report(1, visited=2, intent=0))
    coverage.decide(own, view())
    assert own.memory.intent == 2


def test_avoidance_routes_around_a_blocking_obstacle():
    arena = Environment(SimulationConfig(obstacle_density=0))
    arena.obstacles.append(Obstacle(1, 300, 240, 33, 0, 4))
    agent = Agent(1, (190, 240), 70)
    goal = (440, 240)
    avoided = False
    for _ in range(240):
        arena.advance(DT)
        velocity, turn = steer(agent, arrive(agent.position, goal, agent.max_speed), (), arena)
        avoided |= turn
        agent.advance(velocity, arena, DT)
        assert arena.clear(agent.position, 8)
    assert avoided and distance(agent.position, goal) < 15


@pytest.mark.parametrize('algorithm', list(Algorithm))
def test_all_policies_run_through_engine(algorithm):
    assert algorithm in POLICIES
    sim = Simulation(SimulationConfig(algorithm=algorithm))
    sim.start()
    for _ in range(30):
        sim.tick()
    assert all(norm(agent.velocity) <= agent.max_speed + 1e-8 for agent in sim.agents)
    assert sum(agent.distance_travelled for agent in sim.agents) > 50
