from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Algorithm(StrEnum):
    BOIDS = "boids"
    LEADER_FOLLOWER = "leader-follower"
    CONSENSUS = "consensus"
    AUCTION = "auction"
    AVOIDANCE = "avoidance"
    COVERAGE = "coverage"


class SimulationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    agent_count: int = Field(10, ge=5, le=100)
    width: int = Field(1000, ge=640, le=2200)
    height: int = Field(580, ge=480, le=1500)
    speed: float = Field(1.0, ge=0.25, le=4)
    agent_speed: float = Field(68, ge=25, le=125)
    communication_range: float = Field(185, ge=40, le=700)
    obstacle_density: int = Field(9, ge=0, le=35)
    target_count: int = Field(5, ge=1, le=24)
    duration: int = Field(180, ge=20, le=900)
    algorithm: Algorithm = Algorithm.COVERAGE
    seed: int = Field(42, ge=0, le=2**32 - 1)
    update_hz: int = Field(12, ge=2, le=20)
    packet_loss: float = Field(0.0, ge=0, le=1)
    delay_ms: int = Field(0, ge=0, le=1000)
    separation: float = Field(1.65, ge=0, le=4)
    alignment: float = Field(0.85, ge=0, le=4)
    cohesion: float = Field(0.75, ge=0, le=4)
