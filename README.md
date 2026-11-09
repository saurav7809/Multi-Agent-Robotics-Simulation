# Swarm Lab

Swarm Lab is a browser-based 2D simulator for decentralized drone coordination. It runs locally with 5–100 agents, seven mission scenarios, six interchangeable policies, and a dashboard for observing behavior under normal operation and injected faults.

## What it demonstrates

When an agent only has nearby observations and range-limited messages, it must decide where to move, which task to claim, and how to adapt when neighbors disappear. Swarm Lab makes those decisions observable. You can vary the fleet size, radio range, packet loss, and arena seed, then measure how the changes affect a mission.

- **Autonomous agents** have independent position, velocity, heading, health, battery, task state, and local memory. A drone with low battery returns to its launch station, recharges, and rejoins the mission.
- **Live arena** displays fixed and moving obstacles, links, movement trails, coverage cells, targets, and agent state. Select a drone on Canvas or in the inspector. Zoom in to pan.
- **Fault injection** lets you fail or restore a drone, disable its radio, or drain its battery. The leader-failure preset elects a replacement through local messages.
- **Telemetry and export** include mission progress, coverage, battery, connectivity, collisions, task distribution, and consensus. Save a reference snapshot for comparison in the browser or download CSV and JSON.

## Quick start on Windows

Install Python 3.11 or later and a supported Node.js version such as Node 22.12 or later. Run the commands from the repository root in PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Set-Location frontend
npm.cmd ci
Set-Location ..
```

Start the API in the first terminal.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal from the repository root.

```powershell
Set-Location frontend
npm.cmd run dev
```

Open the [local dashboard](http://127.0.0.1:5173/) and click **Start**. The initial Area Exploration mission launches ten drones. If port 5173 is occupied, run `npm.cmd run dev -- --port 5174` and open the URL printed by Vite. See the [user guide](docs/user-guide.md) for mission setup, fault injection, and comparison workflows.

## Architecture and stack

The Python engine owns the simulation and advances in fixed 1/30-second steps. A shared NumPy distance matrix supports perception and neighbor discovery. Each policy chooses movement from an agent's own memory and local observations. Navigation checks the resulting velocity for potential contacts before the engine integrates it.

FastAPI and Pydantic handle commands and validation. A WebSocket streams compact snapshots to the React and TypeScript dashboard through Vite's local proxy. Canvas renders motion independently of React dashboard updates. Tailwind CSS, Recharts, and Lucide provide styling, charts, and icons.

| Backend | Frontend |
| --- | --- |
| `backend/app/simulation.py` runs the clock, lifecycle, and mission scoring | `frontend/src/useTelemetry.ts` ingests WebSocket frames and falls back to REST |
| `backend/app/algorithms/` contains the six selectable policies | `frontend/src/simulation/` renders the arena and handles selection and pan |
| `backend/app/agents.py`, `environment.py`, and `navigation.py` handle dynamics and geometry | `frontend/src/components/` contains controls, metrics, charts, and the event log |
| `backend/app/communication.py` models radio delivery and `protocol.py` defines agent memory | `frontend/e2e/` tests the browser against live servers |

The [architecture guide](docs/architecture.md) describes agent state, radio transport, and the telemetry path. See the [algorithm guide](docs/algorithms.md) for equations and examples.

## Mission scenarios

| Scenario | Default policy | Completion |
| --- | --- | --- |
| Formation control | Leader–follower | Reach the gate with 75% of available drones near their formation stations |
| Area exploration | Area coverage | Survey 80% of valid grid cells |
| Search and rescue | Task auction | Discover and service every distress beacon |
| Obstacle navigation | Obstacle avoidance | Fly 80% of available drones through the gate zone |
| Leader failure | Leader–follower | Recover from the scheduled loss of the primary leader and complete formation |
| Communication failure | Distributed consensus | Restore the radio component and hold agreement for two simulated seconds after the outage |
| Multi-target allocation | Task auction | Complete every exploration, inspection, and coverage objective |

Boids uses weighted separation, alignment, and cohesion. Leader–follower rotates each drone's assigned station with its locally known leader. Consensus averages fresh peer estimates to pick a rendezvous. The auction scores locally known work by distance, battery, and switching cost. Coverage exchanges visited and claimed cells. Every policy uses predictive collision avoidance.

## Metrics and API

Metrics derive from the actual run. [Metric definitions](docs/metrics.md) document the formulas and how to interpret the charts. The [API reference](docs/api.md) lists lifecycle, scenario, agent, export, and telemetry endpoints. FastAPI serves [interactive API documentation](http://127.0.0.1:8000/docs) when the backend is running.

The WebSocket defaults to 12 Hz and supports 2–20 Hz. Playback speed sets a target pace. The clock limits catch-up work when a dense run or a suspended process falls behind.

## Tests

From the repository root, run the backend tests.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
```

From `frontend`, run unit tests, type-check and build, then exercise both local services with Playwright.

```powershell
npm.cmd test
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
```

Playwright launches isolated servers on ports 5199 and 8099. To use an installed Chromium browser, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to the executable path before running the suite.

## Extension points

The policy registry can host new planners or learning policies. The simulation clock and telemetry contract support future replay, 3D rendering, benchmark suites, and digital-twin adapters. [Project status](PROJECT_STATUS.md) records the checks performed during development.
