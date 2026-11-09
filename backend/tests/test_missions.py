import pytest
from fastapi.testclient import TestClient

from app.agents import AgentState
from app.main import app
from app.scenarios import SCENARIOS
from app.simulation import TICKS_PER_SECOND, RunState, Simulation


@pytest.mark.parametrize("scenario", SCENARIOS.values(), ids=SCENARIOS.keys())
def test_default_scenario_reaches_completion(scenario):
    simulation = Simulation()
    simulation.reset(scenario.configure(simulation.config), scenario)
    simulation.start()
    for _ in range(simulation.config.duration * TICKS_PER_SECOND):
        simulation.tick()
        if simulation.state != RunState.RUNNING:
            break
    assert simulation.state == RunState.COMPLETED, (scenario.id, simulation.time, simulation.metrics)
    assert simulation.metrics["mission_progress"] == 100
    assert any(event["type"] == "MISSION_COMPLETED" for event in simulation.events)
    if scenario.incident:
        assert simulation.mission.incident_started and simulation.mission.incident_finished
    if scenario.incident == "leader":
        assert simulation.agents[0].state == AgentState.FAILED and simulation.leader_id != 1


def test_fault_injection_and_recovery_routes():
    with TestClient(app) as client:
        before = client.get("/api/simulation/status").json()
        response = client.post("/api/agents/1/fail")
        assert response.status_code == 200 and response.json()["metrics"]["failed_agents"] == 1
        assert client.post("/api/agents/1/fail").json()["revision"] == response.json()["revision"]
        assert client.post("/api/agents/1/restore").json()["agents"][0]["state"] == "IDLE"
        assert client.post("/api/agents/1/communication", json={"online": False}).json()["agents"][0]["online"] is False
        assert client.post("/api/agents/1/communication", json={"online": True}).json()["agents"][0]["online"] is True
        assert client.post("/api/agents/1/deplete").json()["agents"][0]["state"] == "RETURNING"
        assert client.post("/api/agents/random-failure").json()["metrics"]["failed_agents"] == 1
        assert client.post("/api/simulation/reset").json()["agents"] == before["agents"]


def test_config_and_scenario_inputs_are_validated():
    with TestClient(app) as client:
        assert len(client.get("/api/scenarios").json()) == 7
        assert client.post("/api/scenarios/missing/load").status_code == 404
        assert client.post("/api/simulation/configure", json={"agent_count": 101}).status_code == 422
        assert client.post("/api/simulation/configure", json={"agent_count": 25, "seed": 77}).json()["config"]["seed"] == 77
        loaded = client.post("/api/scenarios/search-and-rescue/load").json()
        assert loaded["config"]["agent_count"] == 25 and loaded["config"]["algorithm"] == "auction"
        assert loaded["metrics"]["tasks_total"] == 5
        assert loaded["metrics"]["tasks_discovered"] == 0 and not loaded["targets"]


def test_depleted_agent_recharges_and_returns_to_duty():
    simulation = Simulation()
    agent = simulation.agents[0]
    simulation.deplete(agent)
    simulation.start()
    for _ in range(7 * TICKS_PER_SECOND):
        simulation.tick()
    assert agent.battery > 85 and agent.state not in (AgentState.RETURNING, AgentState.FAILED)
