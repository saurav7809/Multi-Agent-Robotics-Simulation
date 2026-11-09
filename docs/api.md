# API reference

FastAPI listens on `http://127.0.0.1:8000` by default. Vite proxies `/api` and `/ws` on the dashboard's origin. The local API serves Swagger UI at `/docs` and its schema at `/openapi.json`.

## Run control

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/health` | Reports process health |
| GET | `/api/simulation/status` | Reads the current snapshot |
| POST | `/api/simulation/start` | Starts a ready run |
| POST | `/api/simulation/pause` | Pauses a running mission |
| POST | `/api/simulation/resume` | Resumes a paused mission |
| POST | `/api/simulation/reset` | Recreates the current mission with the same settings and seed |
| POST | `/api/simulation/configure` | Applies a partial configuration and returns a snapshot |
| GET | `/api/scenarios` | Lists the seven presets and their objectives |
| POST | `/api/scenarios/{scenario_id}/load` | Loads a preset and creates a ready run |

Configuration accepts any subset of the fields in `snapshot.config`. A request changing only `speed` updates playback in place. Other changed fields reset the mission. Unknown fields and out-of-range values return 422. Loading a scenario updates the algorithm, obstacle count, target count, and time limit from the preset.

Example configure body for a fleet of 24 with 10% radio packet loss and a delay of 120 ms.

```json
{
  "agent_count": 24,
  "algorithm": "coverage",
  "communication_range": 220,
  "packet_loss": 0.1,
  "delay_ms": 120
}
```

## Agent and fault operations

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/agents` | Reads summaries for every drone |
| GET | `/api/agents/{agent_id}` | Reads details including neighbors and the latest received packet |
| POST | `/api/agents/{agent_id}/fail` | Disables the specified drone |
| POST | `/api/agents/random-failure` | Disables one seeded random operational drone |
| POST | `/api/agents/{agent_id}/restore` | Restores a failed drone with a full battery |
| POST | `/api/agents/{agent_id}/deplete` | Drops battery to at most 12% and triggers return |
| POST | `/api/agents/{agent_id}/communication` | Sets the radio from a body such as `{"online": false}` |

Agent IDs are one-based integers within the current fleet. An unknown agent or preset returns 404. A fault command that needs an operational drone can return 409 when none is available. Mutating endpoints return the updated snapshot.

## Telemetry and exports

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/metrics` | Reads the latest calculated metrics |
| GET | `/api/metrics/history?after=5` | Reads recorded samples with simulated times greater than five seconds |
| GET | `/api/events` | Reads up to 240 recent events for the run |
| GET | `/api/simulation/export?format=csv` | Downloads time-series metrics with scenario, algorithm, run ID, and seed |
| GET | `/api/simulation/export?format=json` | Downloads the snapshot, metric samples, and retained events |
| WS | `/ws/simulation` | Streams the latest changed snapshot at the configured rate |

Snapshots contain `session_id`, `run_id`, `revision`, simulated `time`, `status`, `scenario`, `config`, `agents`, `obstacles`, `targets`, `links`, `grid`, `metrics`, and recent `events`. A WebSocket sends an initial snapshot on connection. Revisions increase within a backend session. Grid cells form a row-major string with `0` for unseen, `1` for scanned, and `2` for blocked cells.
