import asyncio
import json
from contextlib import suppress

from fastapi import WebSocket, WebSocketDisconnect

from .simulation import Simulation


class FrameCache:
    def __init__(self):
        self.key: tuple[str, int] | None = None
        self.payload = ""

    def encode(self, simulation: Simulation) -> str:
        key = simulation.session_id, simulation.revision
        if key != self.key:
            self.payload = json.dumps(simulation.snapshot(), separators=(",", ":"), allow_nan=False)
            self.key = key
        return self.payload


async def stream(websocket: WebSocket, simulation: Simulation, cache: FrameCache) -> None:
    await websocket.accept()

    async def disconnect() -> None:
        while (await websocket.receive())["type"] != "websocket.disconnect":
            pass

    receiver = asyncio.create_task(disconnect())
    sent = -1
    try:
        while not receiver.done():
            if simulation.revision != sent:
                sent = simulation.revision
                await asyncio.wait_for(websocket.send_text(cache.encode(simulation)), timeout=3)
            await asyncio.wait((receiver,), timeout=1 / simulation.config.update_hz)
    except (WebSocketDisconnect, OSError):
        pass
    except TimeoutError:
        with suppress(WebSocketDisconnect, OSError, RuntimeError):
            await asyncio.wait_for(websocket.close(code=1013), timeout=1)
    finally:
        receiver.cancel()
        with suppress(asyncio.CancelledError):
            await receiver
