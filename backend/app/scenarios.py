from dataclasses import dataclass
from enum import StrEnum

from .config import Algorithm, SimulationConfig


class Objective(StrEnum):
    COVERAGE = "coverage"
    FORMATION = "formation"
    TARGETS = "targets"
    NAVIGATION = "navigation"
    RECOVERY = "recovery"


@dataclass(frozen=True, slots=True)
class Scenario:
    id: str
    name: str
    description: str
    objective: str
    scoring: Objective
    algorithm: Algorithm
    obstacle_density: int
    target_count: int
    duration: int
    target_kinds: tuple[str, ...] = ()
    incident: str | None = None

    @property
    def has_destination(self) -> bool:
        return self.scoring in (Objective.FORMATION, Objective.NAVIGATION)

    def configure(self, current: SimulationConfig) -> SimulationConfig:
        return current.model_copy(update={
            "algorithm": self.algorithm,
            "obstacle_density": self.obstacle_density,
            "target_count": self.target_count,
            "duration": self.duration,
        })

    def descriptor(self) -> dict[str, object]:
        return {
            "id": self.id, "name": self.name, "description": self.description, "objective": self.objective,
            "algorithm": self.algorithm, "obstacle_density": self.obstacle_density,
            "target_count": self.target_count if self.target_kinds else 0, "duration": self.duration,
            "scoring": self.scoring, "incident": self.incident,
        }


SCENARIOS = {scenario.id: scenario for scenario in (
    Scenario("formation-control", "Formation control",
             "Fly a rotating formation from launch to the eastern gate.",
             "Reach the gate with at least 75% of available drones near their formation stations.",
             Objective.FORMATION, Algorithm.LEADER_FOLLOWER, 5, 1, 95),
    Scenario("area-exploration", "Area exploration",
             "Scout unknown territory and share visited cells over local radio.",
             "Survey at least 80% of the traversable grid.",
             Objective.COVERAGE, Algorithm.COVERAGE, 9, 5, 180, ("explore",)),
    Scenario("search-and-rescue", "Search and rescue",
             "Locate hidden beacons and dwell long enough to confirm each rescue.",
             "Discover and service every hidden distress beacon.",
             Objective.TARGETS, Algorithm.AUCTION, 12, 5, 180, ("rescue",)),
    Scenario("obstacle-navigation", "Obstacle navigation",
             "Thread the fleet through a dense field of fixed and moving obstacles.",
             "Guide at least 80% of the available drones through the gate zone.",
             Objective.NAVIGATION, Algorithm.AVOIDANCE, 23, 1, 120),
    Scenario("leader-failure", "Leader failure",
             "The primary leader fails at 8 seconds. Radio beacons let survivors elect a replacement.",
             "Elect a replacement and arrive at the gate with at least 75% of available drones in formation.",
             Objective.FORMATION, Algorithm.LEADER_FOLLOWER, 7, 1, 120, incident="leader"),
    Scenario("communication-failure", "Communication failure",
             "A radio blackout isolates part of the fleet from 8 to 16 seconds.",
             "Restore the full radio component and hold agreement for 2 simulated seconds after the blackout.",
             Objective.RECOVERY, Algorithm.CONSENSUS, 5, 1, 100, incident="radio"),
    Scenario("multi-target-allocation", "Multi-target allocation",
             "Use local bids to distribute exploration, inspection, and coverage objectives.",
             "Complete every assigned objective in the arena.",
             Objective.TARGETS, Algorithm.AUCTION, 10, 8, 180, ("explore", "inspect", "coverage")),
)}

DEFAULT_SCENARIO = SCENARIOS["area-exploration"]
