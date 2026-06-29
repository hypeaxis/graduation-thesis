"""Streaming — ConnectionManager (WebSocket) + ReplayEngine (play/pause/reset/speed).

Tách rõ: ConnectionManager chỉ lo kết nối/broadcast; ReplayEngine chỉ lo vòng phát.
"""
from __future__ import annotations

import asyncio
import json

from .scenarios import ScenarioService

BASE_RATE = 6.0   # flows/giây ở tốc độ 1× (speed là hệ số nhân)


async def in_thread(fn, *args):
    """Chạy hàm đồng bộ trong thread (tương thích Python 3.8, thay asyncio.to_thread)."""
    return await asyncio.get_event_loop().run_in_executor(None, fn, *args)


class ConnectionManager:
    def __init__(self):
        self.clients: set = set()

    def add(self, ws):
        self.clients.add(ws)

    def remove(self, ws):
        self.clients.discard(ws)

    async def broadcast(self, msg: dict):
        data = json.dumps(msg)
        for ws in list(self.clients):
            try:
                await ws.send_text(data)
            except Exception:
                self.clients.discard(ws)


class ReplayEngine:
    """Phát từng flow của 1 kịch bản qua WebSocket; hỗ trợ pause + đổi tốc độ runtime."""

    def __init__(self, scenarios: ScenarioService, manager: ConnectionManager):
        self.scenarios = scenarios
        self.manager = manager
        self.task: asyncio.Task | None = None
        self.paused = False
        self.speed = 2.0
        self.scenario: str | None = None

    async def play(self, scenario: str, speed: float):
        self.stop()
        self.paused = False
        self.speed = speed
        self.scenario = scenario
        await self.manager.broadcast({"type": "loading", "what": self.scenarios.label(scenario)})
        events = await in_thread(self.scenarios.events, scenario)
        if not events:
            return False
        await self.manager.broadcast({"type": "reset"})
        self.task = asyncio.create_task(self._loop(events, scenario))
        return True

    def stop(self):
        if self.task:
            self.task.cancel()
            self.task = None

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def set_speed(self, speed: float):
        self.speed = max(0.25, min(speed, 16.0))

    async def _loop(self, events: list, scenario: str):
        n = len(events)
        await self.manager.broadcast({"type": "play", "scenario": scenario,
                                      "label": self.scenarios.label(scenario), "n": n})
        i = 0
        try:
            while i < n:
                if self.paused:
                    await asyncio.sleep(0.1)
                    continue
                e = events[i]
                await self.manager.broadcast({"type": "flow", "idx": i,
                                              "src": e["src"], "dst": e["dst"], "dst_port": e["dst_port"],
                                              "truth": e["true"], "pred": e["pred"], "conf": e["conf"]})
                i += 1
                if i % 20 == 0 or i == n:
                    await self.manager.broadcast({"type": "progress", "i": i, "n": n})
                await asyncio.sleep((1.0 / BASE_RATE) / max(self.speed, 0.1))
            await self.manager.broadcast({"type": "done", "i": i, "n": n})
        except asyncio.CancelledError:
            pass
