"""API layer — create_app(): FastAPI nhận services qua tham số (Dependency Injection),
không tự khởi tạo model/loader → dễ test, dễ thay thế."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .explain import ExplainService
from .model import Classifier
from .scenarios import SCENARIOS, ScenarioService
from .streaming import ConnectionManager, LiveEngine, ReplayEngine


class PlayReq(BaseModel):
    scenario: str = "mixed"
    speed: float = 2.0


class SpeedReq(BaseModel):
    speed: float = 2.0


def create_app(*, scenarios: ScenarioService, explain: ExplainService,
               engine: ReplayEngine, manager: ConnectionManager,
               classifier: Classifier, dashboard_path: Path,
               live_engine: LiveEngine | None = None) -> FastAPI:
    app = FastAPI(title="Replay-based Live Detection (V8.5)")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/scenarios")
    def api_scenarios():
        return {"scenarios": scenarios.list(), "classes": classifier.classes_,
                "attacker_ip": scenarios.loader.settings.attacker_ip}

    @app.get("/api/explain/{cls}")
    def api_explain(cls: str):
        return {"cls": cls, "features": explain.for_class(cls)}

    @app.post("/api/live/start")
    async def api_live_start():
        if live_engine is None:
            return JSONResponse({"ok": False, "error": "LiveEngine chưa được cấu hình."}, 501)
        engine.stop()                       # live và replay loại trừ nhau
        await live_engine.start()
        return {"ok": True, "mode": "live"}

    @app.post("/api/live/stop")
    async def api_live_stop():
        if live_engine is not None:
            live_engine.stop()
        return {"ok": True}

    @app.post("/api/play")
    async def api_play(req: PlayReq):
        if req.scenario not in SCENARIOS:
            return JSONResponse({"ok": False, "error": f"Kịch bản không hợp lệ: {req.scenario}"}, 400)
        if live_engine is not None:
            live_engine.stop()              # dừng live nếu đang chạy
        ok = await engine.play(req.scenario, req.speed)
        if not ok:
            return JSONResponse({"ok": False, "error": f"Không có dữ liệu cho '{req.scenario}'."}, 404)
        return {"ok": True, "scenario": req.scenario}

    @app.post("/api/pause")
    async def api_pause():
        engine.pause()
        await manager.broadcast({"type": "paused", "paused": True})
        return {"ok": True}

    @app.post("/api/resume")
    async def api_resume():
        engine.resume()
        await manager.broadcast({"type": "paused", "paused": False})
        return {"ok": True}

    @app.post("/api/reset")
    async def api_reset():
        engine.stop()
        engine.resume()
        await manager.broadcast({"type": "reset"})
        return {"ok": True}

    @app.post("/api/speed")
    async def api_speed(req: SpeedReq):
        engine.set_speed(req.speed)
        return {"ok": True, "speed": engine.speed}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        manager.add(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            manager.remove(ws)
        except Exception:
            manager.remove(ws)

    @app.get("/")
    def index():
        return HTMLResponse(dashboard_path.read_text(encoding="utf-8"))

    return app
