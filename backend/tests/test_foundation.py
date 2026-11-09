import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import SimulationConfig
from app.environment import Environment, distance
from app.main import app


def test_health():
    assert TestClient(app).get("/api/health").json() == {"status": "ok"}


def test_configuration_validation():
    assert SimulationConfig().agent_count == 10
    for settings in ({"agent_count": 101}, {"speed": float("nan")}, {"packet_loss": -1}, {"surprise": 1}):
        with pytest.raises(ValidationError):
            SimulationConfig(**settings)


def test_seeded_arena_and_boundaries():
    config = SimulationConfig(seed=172, obstacle_density=12)
    arena = Environment(config, ("inspect",))
    assert arena.obstacles == Environment(config, ("inspect",)).obstacles
    assert len(arena.targets) == 5
    assert all(distance(arena.base, obstacle.position) > obstacle.radius + 110 for obstacle in arena.obstacles)
    assert arena.clamp((-20, config.height + 5)) == (8, config.height - 8)
