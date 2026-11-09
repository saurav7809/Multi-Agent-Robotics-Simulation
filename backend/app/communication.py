from collections import deque
from collections.abc import Sequence
from enum import StrEnum

import numpy as np

from .agents import Agent, AgentState
from .config import Algorithm, SimulationConfig
from .geometry import distance
from .navigation import SpatialIndex
from .protocol import Report


class MessageType(StrEnum):
    POSITION_UPDATE = "POSITION_UPDATE"
    COVERAGE_UPDATE = "COVERAGE_UPDATE"
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"
    TASK_COMPLETED = "TASK_COMPLETED"
    LEADER_UPDATE = "LEADER_UPDATE"
    CONSENSUS_UPDATE = "CONSENSUS_UPDATE"
    BATTERY_WARNING = "BATTERY_WARNING"


class RadioNetwork:
    """A radio round copies one immutable report to each reachable peer."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.random = np.random.default_rng(config.seed + 2)
        self.in_flight: deque[tuple[float, Report, tuple[int, ...]]] = deque()
        self.links: list[tuple[int, int]] = []
        self.edge_count = self.sent = self.delivered = self.largest = 0

    def discover(self, agents: Sequence[Agent], space: SpatialIndex) -> None:
        eligible = np.asarray([agent.online for agent in agents], dtype=bool)
        reachable = (space.distances_sq <= self.config.communication_range**2) & eligible[:, None] & eligible[None, :]
        if self.config.packet_loss == 1:
            reachable.fill(False)
        visible: set[tuple[int, int]] = set()
        self.edge_count = int(np.count_nonzero(reachable)) // 2
        for index, agent in enumerate(agents):
            peers = np.flatnonzero(reachable[index])
            agent.neighbors = tuple(agents[i].id for i in peers)
            if peers.size:
                # Keep the diagram and wire payload bounded in a fully connected fleet.
                nearest = peers[np.argsort(space.distances_sq[index, peers], kind="stable")[:4]]
                visible.update((min(agent.id, agents[i].id), max(agent.id, agents[i].id)) for i in nearest)
        self.links = sorted(visible)
        self.largest = self._largest_component(agents)

    @staticmethod
    def _largest_component(agents: Sequence[Agent]) -> int:
        by_id = {agent.id: agent.neighbors for agent in agents if agent.online}
        unseen = set(by_id)
        best = 0
        while unseen:
            pending = [unseen.pop()]
            size = 0
            while pending:
                size += 1
                for peer in by_id[pending.pop()]:
                    if peer in unseen:
                        unseen.remove(peer)
                        pending.append(peer)
            best = max(size, best)
        return best

    def broadcast(self, agents: Sequence[Agent], now: float) -> None:
        for agent in agents:
            if not agent.neighbors:
                continue
            memory = agent.memory
            packet = Report(
                agent.id, now, agent.position, memory.visited, memory.blocked, memory.intent,
                memory.estimate, memory.leader, memory.bid, memory.task_manifest(),
                agent.state == AgentState.RETURNING,
            )
            self.sent += len(agent.neighbors)
            receivers = agent.neighbors
            if self.config.packet_loss:
                draws = self.random.random(len(receivers))
                receivers = tuple(peer for peer, chance in zip(receivers, draws) if chance >= self.config.packet_loss)
            if receivers:
                self.in_flight.append((now + self.config.delay_ms / 1000, packet, receivers))

    def deliver(self, agents: Sequence[Agent], now: float) -> None:
        # Agent IDs are stable and contiguous for the lifetime of a run.
        while self.in_flight and self.in_flight[0][0] <= now + 1e-9:
            _, packet, receivers = self.in_flight.popleft()
            sender = agents[packet.sender - 1]
            if not sender.online:
                continue
            for recipient in receivers:
                receiver = agents[recipient - 1]
                if receiver.online and distance(sender.position, receiver.position) <= self.config.communication_range:
                    receiver.memory.receive(packet)
                    self.delivered += 1

    def flush(self, agent_id: int) -> None:
        self.in_flight = deque(
            (due, packet, tuple(peer for peer in recipients if peer != agent_id))
            for due, packet, recipients in self.in_flight if packet.sender != agent_id
        )

    def packet_types(self, report: Report) -> list[MessageType]:
        types = [MessageType.POSITION_UPDATE, MessageType.COVERAGE_UPDATE]
        if self.config.algorithm == Algorithm.CONSENSUS:
            types.append(MessageType.CONSENSUS_UPDATE)
        if report.leader is not None:
            types.append(MessageType.LEADER_UPDATE)
        if report.bid is not None:
            types.append(MessageType.TASK_ASSIGNMENT)
        if report.tasks.completed:
            types.append(MessageType.TASK_COMPLETED)
        if report.low_battery:
            types.append(MessageType.BATTERY_WARNING)
        return types
