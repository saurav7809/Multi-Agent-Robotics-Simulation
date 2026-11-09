import asyncio
from collections import deque
from enum import StrEnum
from math import ceil, sqrt
from uuid import uuid4

import numpy as np

from .agents import Agent, AgentState
from .algorithms import POLICIES
from .algorithms.core import LocalView
from .communication import RadioNetwork
from .config import Algorithm, SimulationConfig
from .environment import Environment
from .geometry import ZERO, Point, arrive, distance
from .metrics import Metrics, Sample, calculate
from .missions import INCIDENT_AT, RADIO_RESTORE_AT, TARGET_HOLD_SECONDS, TARGET_RADIUS, Mission
from .navigation import SENSOR_RANGE, SpatialIndex, resolve_contacts, steer
from .protocol import Beacon, TaskObservation
from .scenarios import DEFAULT_SCENARIO, Scenario

TICKS_PER_SECOND = 30
DT = 1 / TICKS_PER_SECOND
RADIO_INTERVAL = 6
PRODUCTIVE = frozenset((AgentState.MOVING, AgentState.EXPLORING, AgentState.EXECUTING, AgentState.COMMUNICATING))


class RunState(StrEnum):
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    TIMED_OUT = "timed_out"


def unit_label(agent_id: int) -> str:
    return f"U-{agent_id:02d}"


class Simulation:
    def __init__(self, config: SimulationConfig | None = None):
        self.session_id = uuid4().hex
        self.revision = self.run_id = 0
        self.scenario = DEFAULT_SCENARIO
        self.reset(config or SimulationConfig())

    def reset(self, config: SimulationConfig | None = None, scenario: Scenario | None = None) -> None:
        self.config = config or self.config
        self.scenario = scenario or self.scenario
        self.mission = Mission(self.scenario)
        self.arena = Environment(self.config, self.scenario.target_kinds)
        self.agents = self._spawn()
        self.homes = tuple(agent.position for agent in self.agents)
        self.radio = RadioNetwork(self.config)
        self.radio.discover(self.agents, SpatialIndex(self.agents))
        self.state = RunState.READY
        self.step = self.collisions = 0
        self.contacts: set[tuple[str, int, int]] = set()
        self.events: deque[dict[str, object]] = deque(maxlen=240)
        self.event_id = 0
        self.history: list[Sample] = []
        self.operational_ticks = self.productive_ticks = 0
        self.stable_since: float | None = None
        self.consensus_time: float | None = None
        self.leader_id: int | None = None
        self.rendezvous: Point | None = None
        self.run_id += 1
        self.revision += 1
        self.random = np.random.default_rng(self.config.seed + 3)
        rng = np.random.default_rng(self.config.seed + 1)
        first = self.agents[0]
        leader = Beacon(first.id, 0.0, first.position, first.velocity, first.heading)
        for agent in self.agents:
            agent.memory.estimate = float(rng.uniform(0.04, 0.96))
            if self.config.algorithm == Algorithm.LEADER_FOLLOWER:
                agent.memory.leader = leader
            self._sense(agent, execute=False, scan_terrain=True)
        self._emit("MISSION_READY", f"{self.scenario.name} loaded with seed {self.config.seed}.")
        self._refresh_metrics()
        self._record_sample()

    def _sense(self, agent: Agent, execute: bool, scan_terrain: bool) -> None:
        grid = self.arena.grid
        seen = grid.sense(agent.position)
        agent.memory.visited |= seen
        grid.visited |= seen & grid.valid
        x, y = agent.position
        if scan_terrain:
            for obstacle in self.arena.obstacles:
                if not obstacle.moving and distance(agent.position, obstacle.position) <= SENSOR_RANGE + obstacle.radius:
                    agent.memory.blocked |= self.arena.block_masks[obstacle.id]
        interaction = None
        closest = TARGET_RADIUS**2
        for task in self.arena.targets:
            gap_sq = (x - task.x)**2 + (y - task.y)**2
            if not task.discovered and gap_sq <= 76**2:
                task.discovered, task.discovered_at = True, self.time
                self._emit("TARGET_DISCOVERED", f"{unit_label(agent.id)} discovered distress beacon T{task.id:02d}.", agent.id)
            if task.discovered and gap_sq <= 175**2:
                known = agent.memory.tasks.get(task.id)
                completed = task.completed_at is not None
                if known is None or (completed and not known.completed):
                    agent.memory.observe(TaskObservation(task.id, task.position, task.kind, completed))
            if execute and gap_sq <= closest and task.completed_at is None and agent.task_id in (None, task.id):
                interaction, closest = task, gap_sq
        if interaction is None:
            agent.interaction_id, agent.dwell = None, 0
        else:
            agent.dwell = agent.dwell + 1 if agent.interaction_id == interaction.id else 1
            agent.interaction_id = interaction.id
            if agent.dwell >= ceil(TARGET_HOLD_SECONDS[interaction.kind] * TICKS_PER_SECOND):
                interaction.completed_at, interaction.completed_by = self.time, agent.id
                agent.memory.observe(TaskObservation(interaction.id, interaction.position, interaction.kind, True))
                self._emit("TASK_COMPLETED", f"{unit_label(agent.id)} completed {interaction.kind} target T{interaction.id:02d}.", agent.id)

    def _emit(self, event_type: str, message: str, agent_id: int | None = None) -> None:
        self.event_id += 1
        self.events.append({
            "id": self.event_id, "type": event_type, "time": round(self.time, 3),
            "message": message, "agent_id": agent_id,
        })

    def _spawn(self) -> list[Agent]:
        bx, by = self.arena.base
        spacing = 24
        row_spacing = spacing * sqrt(3) / 2
        candidates = [
            (bx + (col + (row % 2) / 2) * spacing, by + row * row_spacing)
            for row in range(-12, 13) for col in range(-12, 16)
        ]
        candidates.sort(key=lambda point: distance(point, self.arena.base))
        positions = [point for point in candidates if self.arena.clamp(point, 16) == point and self.arena.clear(point, 13)]
        return [Agent(index + 1, point, self.config.agent_speed) for index, point in enumerate(positions[:self.config.agent_count])]

    @property
    def time(self) -> float:
        return self.step / TICKS_PER_SECOND

    def start(self) -> None:
        if self.state == RunState.READY:
            self.state = RunState.RUNNING
            self._emit("RUN_STARTED", "Simulation started.")
            self.revision += 1

    def configure(self, config: SimulationConfig) -> None:
        if config == self.config:
            return
        if config.model_dump(exclude={"speed"}) == self.config.model_dump(exclude={"speed"}):
            self.config = config
            self.revision += 1
        else:
            self.reset(config)

    def pause(self) -> None:
        if self.state == RunState.RUNNING:
            self.state = RunState.PAUSED
            self._emit("RUN_PAUSED", "Simulation paused.")
            self._refresh_metrics()
            self.revision += 1

    def resume(self) -> None:
        if self.state == RunState.PAUSED:
            self.state = RunState.RUNNING
            self._emit("RUN_RESUMED", "Simulation resumed.")
            self.revision += 1

    def _fail(self, agent: Agent, reason: str) -> bool:
        if not agent.active:
            return False
        agent.fail()
        self.radio.flush(agent.id)
        self.mission.jammed.discard(agent.id)
        self._emit("AGENT_FAILURE", f"{unit_label(agent.id)} failed ({reason}).", agent.id)
        return True

    def fail(self, agent: Agent, reason: str = "manual fault") -> None:
        if self._fail(agent, reason):
            self._after_fault()

    def random_failure(self) -> Agent | None:
        active = [agent for agent in self.agents if agent.active]
        if not active:
            return None
        chosen = active[int(self.random.integers(len(active)))]
        self.fail(chosen, "random fault")
        return chosen

    def restore(self, agent: Agent) -> None:
        if agent.active:
            return
        agent.restore()
        if not self.arena.clear(agent.position, 8):
            agent.position = self.homes[agent.id - 1]
        self._emit("AGENT_RESTORED", f"{unit_label(agent.id)} returned to service.", agent.id)
        self._after_fault()

    def _return_to_base(self, agent: Agent) -> None:
        agent.state, agent.task_id = AgentState.RETURNING, None
        agent.memory.bid, agent.memory.intent = None, None
        if agent.memory.leader is not None and agent.memory.leader.agent_id == agent.id:
            agent.memory.leader = None
        self._emit("BATTERY_WARNING", f"{unit_label(agent.id)} has low battery and is returning to base.", agent.id)

    def deplete(self, agent: Agent) -> None:
        agent.battery = min(agent.battery, 12)
        if agent.state != AgentState.RETURNING:
            self._return_to_base(agent)
        self._after_fault()

    def _set_radio(self, agent: Agent, online: bool) -> bool:
        if not agent.active or online == agent.radio_enabled:
            return False
        agent.radio_enabled = online
        agent.memory.reports.clear()
        self.radio.flush(agent.id)
        event_type, description = ("COMMUNICATION_RESTORED", "radio restored") if online else ("COMMUNICATION_LOST", "lost radio contact")
        self._emit(event_type, f"{unit_label(agent.id)} {description}.", agent.id)
        return True

    def set_radio(self, agent: Agent, online: bool) -> None:
        self.mission.jammed.discard(agent.id)
        if self._set_radio(agent, online):
            self._after_fault()

    def _after_fault(self) -> None:
        self.radio.discover(self.agents, SpatialIndex(self.agents))
        self._refresh_metrics()
        self.revision += 1

    def _incident(self) -> None:
        mission = self.mission
        if self.scenario.incident and not mission.incident_started and self.time >= INCIDENT_AT:
            mission.incident_started = True
            if self.scenario.incident == "leader":
                leader = next((agent for agent in self.agents if agent.id == self.leader_id and agent.active), None)
                if leader:
                    mission.previous_leader = leader.id
                    self._fail(leader, "scheduled leader failure")
            else:
                for agent in self.agents[1::3]:
                    if self._set_radio(agent, False):
                        mission.jammed.add(agent.id)
                        # An isolated drone observes a local shift in rendezvous preference.
                        delta = 0.24 if agent.id % 2 else -0.24
                        agent.memory.estimate = min(0.98, max(0.02, agent.memory.estimate + delta))
        if self.scenario.incident == "radio" and mission.incident_started and not mission.incident_finished and self.time >= RADIO_RESTORE_AT:
            mission.incident_finished = True
            for agent_id in sorted(mission.jammed):
                self._set_radio(self.agents[agent_id - 1], True)
            mission.jammed.clear()

    def _decision(self, agent: Agent, view: LocalView) -> tuple[Point, AgentState]:
        if agent.battery <= 18 and agent.state != AgentState.RETURNING:
            self._return_to_base(agent)
        if agent.state == AgentState.RETURNING:
            home = self.homes[agent.id - 1]
            if distance(agent.position, home) <= 24:
                agent.battery = min(100, agent.battery + 16 * DT)
                if agent.battery >= 94:
                    agent.state = AgentState.IDLE
                    self._emit("BATTERY_CHARGED", f"{unit_label(agent.id)} recharged and rejoined the mission.", agent.id)
                else:
                    return ZERO, AgentState.RETURNING
            else:
                return arrive(agent.position, home, agent.max_speed * 0.84, 33), AgentState.RETURNING
        previous = agent.task_id
        desired, state = POLICIES[self.config.algorithm](agent, view)
        if agent.task_id is not None and agent.task_id != previous:
            self._emit("TASK_ASSIGNMENT", f"{unit_label(agent.id)} claimed target T{agent.task_id:02d}.", agent.id)
        return desired, state

    def _refresh_metrics(self) -> None:
        leader = None
        if self.config.algorithm == Algorithm.LEADER_FOLLOWER:
            leader = next(
                (agent for agent in self.agents if agent.active and agent.state != AgentState.RETURNING
                 and agent.memory.leader is not None and agent.memory.leader.agent_id == agent.id), None,
            )
        leader_id = leader.id if leader else None
        if leader_id != self.leader_id and leader_id is not None:
            self._emit("LEADER_UPDATE", f"{unit_label(leader_id)} is the primary formation leader.", leader_id)
            if self.mission.previous_leader is not None and leader_id != self.mission.previous_leader:
                self.mission.incident_finished = True
        self.leader_id = leader_id

        operational = [agent for agent in self.agents if agent.active]
        is_consensus = self.config.algorithm == Algorithm.CONSENSUS
        estimates = [agent.memory.estimate for agent in operational] if is_consensus else []
        spread = max(estimates) - min(estimates) if len(estimates) >= 2 else None
        if estimates:
            estimate = sum(estimates) / len(estimates)
            self.rendezvous = (self.arena.width * (0.36 + 0.28 * estimate), self.arena.height * 0.5)
            if self.scenario.has_destination:
                x, y = self.arena.destination
                self.rendezvous = (x, y + (estimate - 0.5) * self.arena.height * 0.28)
        stable = len(operational) >= 2 and self.radio.largest == len(operational)
        if is_consensus:
            stable = stable and spread is not None and spread <= 0.025 and self.radio.delivered > 0
        if stable:
            if self.stable_since is None:
                self.stable_since = self.time
        else:
            self.stable_since = None
        reached = is_consensus and self.stable_since is not None and self.time - self.stable_since >= 2
        if reached and self.consensus_time is None:
            self.consensus_time = round(self.time, 2)
            self._emit("CONSENSUS_REACHED", "Connected agents held agreement for 2 simulated seconds.")
        progress = self.mission.evaluate(self.arena, self.agents, leader, self.time, self.stable_since, spread)
        self.metrics: Metrics = calculate(
            self.agents, self.arena, self.radio, progress, self.collisions, self.productive_ticks, self.operational_ticks,
            spread, self.consensus_time, reached,
        )

    def _record_sample(self) -> None:
        self.history.append({"time": round(self.time, 3), "metrics": self.metrics})

    def samples(self) -> list[Sample]:
        last = {"time": round(self.time, 3), "metrics": self.metrics}
        if self.history[-1]["time"] == last["time"]:
            return [*self.history[:-1], last]
        return [*self.history, last]

    def tick(self) -> None:
        if self.state != RunState.RUNNING:
            return
        self.step += 1
        self.arena.advance(DT)
        self._incident()
        spatial = SpatialIndex(self.agents)
        grid = self.arena.grid
        decision_tick = self.step % RADIO_INTERVAL == 1
        if decision_tick:
            self.radio.discover(self.agents, spatial)
            self.radio.broadcast(self.agents, self.time)
        self.radio.deliver(self.agents, self.time)
        destination = self.arena.destination if self.scenario.has_destination else None
        sight_radius = SENSOR_RANGE if self.config.algorithm == Algorithm.BOIDS else 81
        failed = False
        for index, agent in enumerate(self.agents):
            if not agent.active:
                continue
            nearby = spatial.nearby(index, sight_radius)
            view = LocalView(self.time, self.config, nearby, grid.centers, grid.bits, destination, decision_tick)
            desired, state = self._decision(agent, view)
            velocity, avoiding = steer(agent, desired, nearby, self.arena)
            agent.state = AgentState.AVOIDING if avoiding and state != AgentState.RETURNING else state
            agent.advance(velocity, self.arena, DT)
            if agent.battery == 0:
                failed |= self._fail(agent, "battery depleted")
        contacts = resolve_contacts(self.agents, self.arena)
        self.collisions += len(contacts - self.contacts)
        self.contacts = contacts
        for agent in self.agents:
            if agent.active:
                self.operational_ticks += 1
                self.productive_ticks += agent.state in PRODUCTIVE
                self._sense(agent, execute=agent.state != AgentState.RETURNING, scan_terrain=decision_tick)
        if failed or self.step in (int(INCIDENT_AT * TICKS_PER_SECOND), int(RADIO_RESTORE_AT * TICKS_PER_SECOND)):
            self.radio.discover(self.agents, SpatialIndex(self.agents))
        second = self.step % TICKS_PER_SECOND == 0
        if decision_tick or second or failed:
            self._refresh_metrics()
            if self.metrics["mission_progress"] >= 100:
                self.state = RunState.COMPLETED
                self._emit("MISSION_COMPLETED", f"{self.scenario.name} completed.")
            elif self.step >= self.config.duration * TICKS_PER_SECOND:
                self.state = RunState.TIMED_OUT
                self._emit("MISSION_TIMEOUT", "The mission reached its time limit.")
            if second or self.state != RunState.RUNNING:
                self._record_sample()
        self.revision += 1

    def snapshot(self) -> dict[str, object]:
        grid = self.arena.grid
        return {
            "session_id": self.session_id, "revision": self.revision, "run_id": self.run_id, "status": self.state, "time": round(self.time, 3),
            "scenario": self.scenario.id, "config": self.config.model_dump(mode="json"), "base": self.arena.base,
            "destination": self.arena.destination if self.scenario.has_destination else None,
            "rendezvous": self.rendezvous, "leader_id": self.leader_id, "metrics": self.metrics,
            "grid": {"cols": grid.cols, "rows": grid.rows, "cells": grid.cells()},
            "obstacles": [{"id": item.id, "x": round(item.x, 2), "y": round(item.y, 2), "r": item.radius, "moving": item.moving} for item in self.arena.obstacles],
            "targets": [{"id": item.id, "x": round(item.x, 2), "y": round(item.y, 2), "kind": item.kind, "completed": item.completed_at is not None} for item in self.arena.targets if item.discovered],
            "agents": [
                {**agent.snapshot(), "leader": agent.memory.leader.agent_id if agent.memory.leader else None,
                 "estimate": round(agent.memory.estimate, 4) if self.config.algorithm == Algorithm.CONSENSUS else None}
                for agent in self.agents
            ],
            "links": self.radio.links, "events": list(self.events)[-32:],
        }


async def run_clock(simulation: Simulation) -> None:
    loop = asyncio.get_running_loop()
    previous, carry, run_id = loop.time(), 0.0, simulation.run_id
    while True:
        await asyncio.sleep(1 / 60)
        now = loop.time()
        if simulation.state == RunState.RUNNING and run_id == simulation.run_id:
            # Cap catch-up after suspension to keep the API responsive.
            carry = min(10 * DT, carry + (now - previous) * simulation.config.speed)
            while carry >= DT and simulation.state == RunState.RUNNING:
                simulation.tick()
                carry -= DT
        else:
            carry = 0.0
        previous, run_id = now, simulation.run_id
