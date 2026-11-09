from dataclasses import dataclass, field

from .geometry import Point


@dataclass(frozen=True, slots=True)
class Beacon:
    agent_id: int
    time: float
    position: Point
    velocity: Point
    heading: float


@dataclass(frozen=True, slots=True)
class Bid:
    agent_id: int
    task_id: int
    cost: float


@dataclass(frozen=True, slots=True)
class TaskObservation:
    id: int
    position: Point
    kind: str
    completed: bool


@dataclass(frozen=True, slots=True)
class TaskManifest:
    items: tuple[TaskObservation, ...] = ()
    known: int = 0
    completed: int = 0


@dataclass(frozen=True, slots=True)
class Report:
    sender: int
    time: float
    position: Point
    visited: int
    blocked: int
    intent: int | None
    estimate: float
    leader: Beacon | None
    bid: Bid | None
    tasks: TaskManifest = TaskManifest()
    low_battery: bool = False


@dataclass(slots=True)
class Memory:
    visited: int = 0
    blocked: int = 0
    intent: int | None = None
    intent_until: float = 0.0
    estimate: float = 0.5
    estimate_stamp: float = -1.0
    leader: Beacon | None = None
    bid: Bid | None = None
    tasks: dict[int, TaskObservation] = field(default_factory=dict)
    reports: dict[int, Report] = field(default_factory=dict)
    _manifest: TaskManifest | None = None
    _known_tasks: int = 0
    _completed_tasks: int = 0

    def observe(self, task: TaskObservation) -> None:
        old = self.tasks.get(task.id)
        if old is None or (task.completed and not old.completed):
            self.tasks[task.id] = task
            self._known_tasks |= 1 << task.id
            if task.completed:
                self._completed_tasks |= 1 << task.id
            self._manifest = None

    def task_manifest(self) -> TaskManifest:
        if self._manifest is None:
            self._manifest = TaskManifest(tuple(self.tasks.values()), self._known_tasks, self._completed_tasks)
        return self._manifest

    def receive(self, report: Report) -> None:
        old = self.reports.get(report.sender)
        if old is not None and old.time >= report.time:
            return
        self.reports[report.sender] = report
        self.visited |= report.visited
        self.blocked |= report.blocked
        novel = (report.tasks.known & ~self._known_tasks) | (report.tasks.completed & ~self._completed_tasks)
        if novel:
            for task in report.tasks.items:
                if novel & (1 << task.id):
                    self.observe(task)
