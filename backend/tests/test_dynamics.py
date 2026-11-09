import pytest

from app.agents import Agent, AgentState
from app.config import SimulationConfig
from app.environment import Environment, Obstacle
from app.geometry import norm
from app.navigation import resolve_contacts
from app.simulation import DT, RunState, Simulation


def test_agent_dynamics_and_battery():
    arena = Environment(SimulationConfig(obstacle_density=0))
    agent = Agent(1, (100, 120), 35)
    assert agent.state == AgentState.IDLE and agent.battery == 100
    for _ in range(45):
        agent.advance((100, 0), arena, DT)
    assert agent.position[0] > 130 and agent.position[1] == 120
    assert norm(agent.velocity) == pytest.approx(35)
    assert agent.battery < 100
    agent.fail()
    previous = agent.position
    agent.advance((50, 40), arena, DT)
    assert agent.position == previous and not agent.online
    agent.restore()
    assert agent.active and agent.battery == 100


def test_physical_contacts_and_coverage():
    arena = Environment(SimulationConfig(obstacle_density=0))
    arena.obstacles.append(Obstacle(1, 250, 250, 20))
    agents = [Agent(1, (246, 250), 60), Agent(2, (248, 250), 60)]
    contacts = resolve_contacts(agents, arena)
    assert ('agent', 1, 2) in contacts and ('obstacle', 1, 1) in contacts
    assert arena.clear(agents[0].position, 8)
    arena.grid.visited = arena.grid.sense((100, 100)) & arena.grid.valid
    assert 0 < arena.grid.percentage < 100
    assert arena.grid.cells().count('1') == arena.grid.visited.bit_count()


def test_fixed_clock_lifecycle_and_seeded_reset():
    engine = Simulation()
    initial = engine.snapshot()['agents']
    engine.tick()
    assert engine.time == 0
    engine.start()
    for _ in range(30):
        engine.tick()
    assert engine.time == 1 and engine.snapshot()['agents'] != initial
    engine.pause()
    engine.tick()
    assert engine.time == 1
    engine.resume()
    engine.tick()
    assert engine.time == pytest.approx(31 * DT)
    engine.reset()
    assert engine.state == RunState.READY and engine.snapshot()['agents'] == initial


def test_maximum_fleet_spawns_within_bounds():
    engine = Simulation(SimulationConfig(agent_count=100, width=640, height=480, obstacle_density=35))
    assert len(engine.agents) == 100
    assert all(engine.arena.clamp(agent.position) == agent.position for agent in engine.agents)
