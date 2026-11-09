import asyncio
import csv
from contextlib import asynccontextmanager, suppress
from io import StringIO
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, JsonValue, StrictBool, ValidationError

from .agents import Agent
from .config import SimulationConfig
from .metrics import Metrics
from .scenarios import SCENARIOS
from .simulation import Simulation, run_clock
from .stream import FrameCache, stream


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.simulation = Simulation()
    application.state.frames = FrameCache()
    clock = asyncio.create_task(run_clock(application.state.simulation))
    try:
        yield
    finally:
        clock.cancel()
        with suppress(asyncio.CancelledError):
            await clock


app = FastAPI(title="Swarm Lab", version="1.0.0", lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/simulation/status")
async def status(request: Request) -> dict[str, object]:
    return request.app.state.simulation.snapshot()


@app.post("/api/simulation/start")
async def start(request: Request) -> dict[str, object]:
    request.app.state.simulation.start()
    return request.app.state.simulation.snapshot()


@app.post("/api/simulation/pause")
async def pause(request: Request) -> dict[str, object]:
    request.app.state.simulation.pause()
    return request.app.state.simulation.snapshot()


@app.post("/api/simulation/resume")
async def resume(request: Request) -> dict[str, object]:
    request.app.state.simulation.resume()
    return request.app.state.simulation.snapshot()


@app.post("/api/simulation/reset")
async def reset(request: Request) -> dict[str, object]:
    request.app.state.simulation.reset()
    return request.app.state.simulation.snapshot()


@app.post("/api/simulation/configure")
async def configure(request: Request, changes: dict[str, JsonValue]) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    try:
        config = SimulationConfig.model_validate({**simulation.config.model_dump(), **changes})
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=error.errors(include_context=False, include_input=False, include_url=False)) from error
    simulation.configure(config)
    return simulation.snapshot()


@app.get("/api/agents")
async def agents(request: Request) -> list[dict[str, object]]:
    simulation: Simulation = request.app.state.simulation
    return [agent.snapshot() for agent in simulation.agents]


@app.get("/api/agents/{agent_id}")
async def agent_details(request: Request, agent_id: int) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    agent = find_agent(simulation, agent_id)
    latest = max(agent.memory.reports.values(), key=lambda report: report.time, default=None)
    return {
        **agent.snapshot(), "neighbors": agent.neighbors, "acceleration": agent.acceleration,
        "max_speed": agent.max_speed, "distance_travelled": agent.distance_travelled,
        "last_packet": {"sender": latest.sender, "time": latest.time, "types": simulation.radio.packet_types(latest)} if latest else None,
    }


def find_agent(simulation: Simulation, agent_id: int) -> Agent:
    if not 1 <= agent_id <= len(simulation.agents):
        raise HTTPException(status_code=404, detail="Agent ID is outside the current fleet")
    return simulation.agents[agent_id - 1]


@app.post("/api/agents/random-failure")
async def random_failure(request: Request) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    if simulation.random_failure() is None:
        raise HTTPException(status_code=409, detail="All agents are already failed")
    return simulation.snapshot()


@app.post("/api/agents/{agent_id}/fail")
async def fail(request: Request, agent_id: int) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    simulation.fail(find_agent(simulation, agent_id))
    return simulation.snapshot()


@app.post("/api/agents/{agent_id}/restore")
async def restore(request: Request, agent_id: int) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    simulation.restore(find_agent(simulation, agent_id))
    return simulation.snapshot()


@app.post("/api/agents/{agent_id}/deplete")
async def deplete(request: Request, agent_id: int) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    agent = find_agent(simulation, agent_id)
    if not agent.active:
        raise HTTPException(status_code=409, detail="Restore the agent before depleting its battery")
    simulation.deplete(agent)
    return simulation.snapshot()


class RadioSetting(BaseModel):
    model_config = ConfigDict(extra="forbid")
    online: StrictBool


@app.post("/api/agents/{agent_id}/communication")
async def radio(request: Request, agent_id: int, setting: RadioSetting) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    agent = find_agent(simulation, agent_id)
    if not agent.active:
        raise HTTPException(status_code=409, detail="Restore the agent before setting its radio")
    simulation.set_radio(agent, setting.online)
    return simulation.snapshot()


@app.get("/api/scenarios")
async def scenarios() -> list[dict[str, object]]:
    return [scenario.descriptor() for scenario in SCENARIOS.values()]


@app.post("/api/scenarios/{scenario_id}/load")
async def load(request: Request, scenario_id: str) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Unknown mission scenario")
    simulation.reset(scenario.configure(simulation.config), scenario)
    return simulation.snapshot()


@app.get("/api/metrics", response_model=None)
async def metrics(request: Request) -> Metrics:
    simulation: Simulation = request.app.state.simulation
    return simulation.metrics


@app.get("/api/metrics/history")
async def metric_history(request: Request, after: float = -1) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    return {
        "session_id": simulation.session_id, "run_id": simulation.run_id,
        "samples": [sample for sample in simulation.samples() if sample["time"] > after],
    }


@app.get("/api/events")
async def events(request: Request) -> dict[str, object]:
    simulation: Simulation = request.app.state.simulation
    return {"session_id": simulation.session_id, "run_id": simulation.run_id, "events": list(simulation.events)}


@app.get("/api/simulation/export")
async def export(request: Request, format: Literal["json", "csv"] = "json") -> Response:
    simulation: Simulation = request.app.state.simulation
    samples = simulation.samples()
    headers = {"Content-Disposition": f'attachment; filename="swarm-run-{simulation.run_id:04d}.{format}"'}
    if format == "json":
        return JSONResponse({"snapshot": simulation.snapshot(), "samples": samples, "events": list(simulation.events)}, headers=headers)

    context = {
        "run_id": simulation.run_id, "scenario": simulation.scenario.id,
        "algorithm": simulation.config.algorithm, "seed": simulation.config.seed,
    }
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=[*context, "time", *simulation.metrics])
    writer.writeheader()
    writer.writerows({**context, "time": sample["time"], **sample["metrics"]} for sample in samples)
    return Response(output.getvalue(), media_type="text/csv", headers=headers)


@app.websocket("/ws/simulation")
async def simulation_stream(websocket: WebSocket) -> None:
    await stream(websocket, websocket.app.state.simulation, websocket.app.state.frames)
