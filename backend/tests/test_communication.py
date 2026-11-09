from fastapi.testclient import TestClient

from app.agents import Agent
from app.communication import RadioNetwork
from app.config import SimulationConfig
from app.main import app
from app.navigation import SpatialIndex


def test_neighbor_discovery_and_delayed_packet_delivery():
    agents = [Agent(1, (60, 60), 68), Agent(2, (95, 60), 68), Agent(3, (240, 60), 68)]
    agents[0].memory.visited = 42
    network = RadioNetwork(SimulationConfig(communication_range=65, delay_ms=300))
    network.discover(agents, SpatialIndex(agents))
    assert agents[0].neighbors == (2,) and not agents[2].neighbors and network.largest == 2
    network.broadcast(agents, 1)
    network.deliver(agents, 1.2)
    assert not agents[1].memory.reports
    network.deliver(agents, 1.3)
    assert agents[1].memory.reports[1].time == 1 and agents[1].memory.visited == 42
    assert network.sent == network.delivered == 2


def test_offline_receiver_loses_pending_packets():
    agents = [Agent(1, (60, 60), 68), Agent(2, (95, 60), 68)]
    network = RadioNetwork(SimulationConfig(delay_ms=300))
    network.discover(agents, SpatialIndex(agents))
    network.broadcast(agents, 1)
    agents[1].radio_enabled = False
    network.deliver(agents, 2)
    network.discover(agents, SpatialIndex(agents))
    assert network.sent == 2 and network.delivered == 0 and network.largest == 1
    assert not network.links and not agents[1].memory.reports


def test_total_packet_loss_breaks_links():
    agents = [Agent(1, (60, 60), 68), Agent(2, (95, 60), 68)]
    network = RadioNetwork(SimulationConfig(packet_loss=1))
    network.discover(agents, SpatialIndex(agents))
    network.broadcast(agents, 1)
    network.deliver(agents, 2)
    assert not network.links and network.delivered == 0


def test_stream_and_agent_details():
    with TestClient(app) as client, client.websocket_connect('/ws/simulation') as socket:
        initial = socket.receive_json()
        assert initial['status'] == 'ready' and initial['links']
        assert client.post('/api/simulation/start').json()['status'] == 'running'
        update = socket.receive_json()
        assert update['status'] == 'running' and update['revision'] > initial['revision']
        assert client.get('/api/agents/1').json()['neighbors']
        assert client.get('/api/agents/100').status_code == 404
