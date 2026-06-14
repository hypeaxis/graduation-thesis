from __future__ import annotations

import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .pipeline_service import (
    DEFAULT_FT_CHECKPOINT,
    DEFAULT_INFERENCE_CONFIG,
    SIMULATION_DIR,
    build_summary,
    new_session_id,
    run_detection_from_alert_csv,
)
from .schemas import DetectionRequest, DetectionResponse, SimulationRequest, SimulationResponse, StatsResponse
from .simulator import SNORT_ALERT_COLUMNS, generate_alert_rows, write_snort_csv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FINAL_LOG_ALERT = PROJECT_ROOT / "final" / "log" / "alert.csv"

app = FastAPI(title="IDS Simulation and Detection API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions: dict[str, dict] = {}


def _safe_output_name(raw_name: str) -> str:
    base = Path(raw_name).name
    if not base.endswith(".csv"):
        base = f"{base}.csv"
    return re.sub(r"[^a-zA-Z0-9._-]", "_", base)


def _copy_to_default_alert(src: Path) -> None:
    FINAL_LOG_ALERT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, FINAL_LOG_ALERT)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/config")
def config() -> dict:
    return {
        "project_root": str(PROJECT_ROOT),
        "checkpoint": str(DEFAULT_FT_CHECKPOINT),
        "checkpoint_exists": DEFAULT_FT_CHECKPOINT.exists(),
        "inference_config": str(DEFAULT_INFERENCE_CONFIG),
        "inference_config_exists": DEFAULT_INFERENCE_CONFIG.exists(),
        "snort_columns": SNORT_ALERT_COLUMNS,
    }


@app.post("/api/simulate", response_model=SimulationResponse)
def simulate(req: SimulationRequest) -> SimulationResponse:
    session_id = new_session_id()
    output_name = _safe_output_name(req.output_name)
    output_csv = SIMULATION_DIR / f"{session_id}_{output_name}"

    rows = generate_alert_rows(
        scenario=req.scenario,
        total_events=req.total_events,
        benign_ratio=req.benign_ratio,
    )
    write_snort_csv(rows, output_csv)
    _copy_to_default_alert(output_csv)

    sessions[session_id] = {
        "session_id": session_id,
        "scenario": req.scenario,
        "total_events": req.total_events,
        "alert_csv": str(output_csv),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    preview_rows = [row.as_list() for row in rows[: min(8, len(rows))]]
    return SimulationResponse(
        session_id=session_id,
        scenario=req.scenario,
        total_events=req.total_events,
        output_csv=str(output_csv),
        created_at=datetime.now(timezone.utc),
        preview_rows=preview_rows,
    )


@app.post("/api/detect", response_model=DetectionResponse)
def detect(req: DetectionRequest) -> DetectionResponse:
    session_id = new_session_id()

    if req.alert_csv_path:
        alert_csv_path = Path(req.alert_csv_path)
    else:
        scenario = req.scenario or "mixed"
        rows = generate_alert_rows(
            scenario=scenario,
            total_events=req.total_events,
            benign_ratio=req.benign_ratio,
        )
        alert_csv_path = SIMULATION_DIR / f"{session_id}_adhoc_alerts.csv"
        write_snort_csv(rows, alert_csv_path)

    if not alert_csv_path.exists():
        raise HTTPException(status_code=404, detail=f"Alert CSV not found: {alert_csv_path}")

    generated_features_csv = SIMULATION_DIR / f"{session_id}_features_122.csv"
    predictions_csv = SIMULATION_DIR / f"{session_id}_predictions.csv"

    try:
        _, predictions = run_detection_from_alert_csv(
            alert_csv_path=alert_csv_path,
            window_seconds=req.window_seconds,
            generated_features_path=generated_features_csv,
            predictions_path=predictions_csv,
            device_choice="cpu",
        )
    except Exception as exc:  # pylint: disable=broad-except
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    summary = build_summary(predictions)

    response = DetectionResponse(
        session_id=session_id,
        input_alert_csv=str(alert_csv_path),
        generated_features_csv=str(generated_features_csv),
        predictions_csv=str(predictions_csv),
        model_checkpoint=str(DEFAULT_FT_CHECKPOINT),
        total_vectors=int(len(predictions)),
        summary=summary,
        sample_predictions=predictions.head(12).to_dict(orient="records"),
        created_at=datetime.now(timezone.utc),
    )

    sessions[session_id] = response.model_dump()
    return response


@app.get("/api/sessions")
def list_sessions(limit: int = 20) -> dict:
    limit = max(1, min(limit, 100))
    ordered = sorted(sessions.values(), key=lambda x: x.get("created_at", ""), reverse=True)
    return {"items": ordered[:limit], "total": len(ordered)}


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    data = sessions.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data


@app.get("/api/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    total_vectors = 0
    attack_counts: dict[str, int] = {}
    confidence_sum = 0.0
    confidence_count = 0

    for session_data in sessions.values():
        summary = session_data.get("summary")
        if not summary:
            continue
        counts = summary.get("predicted_counts", {}) if isinstance(summary, dict) else {}
        for label, count in counts.items():
            total_vectors += int(count)
            attack_counts[label] = attack_counts.get(label, 0) + int(count)
        mean_conf = summary.get("mean_confidence", 0) if isinstance(summary, dict) else 0
        if mean_conf:
            confidence_sum += float(mean_conf)
            confidence_count += 1

    return StatsResponse(
        total_sessions=len(sessions),
        total_vectors=total_vectors,
        attack_counts=attack_counts,
        overall_mean_confidence=confidence_sum / confidence_count if confidence_count else 0.0,
    )


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend file not found")
    return FileResponse(index_file)
