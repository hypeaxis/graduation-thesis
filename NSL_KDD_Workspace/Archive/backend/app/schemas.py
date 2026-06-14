from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AttackScenario = Literal[
    "normal",
    "port_scan",
    "dos_syn_flood",
    "brute_force",
    "mixed",
]


class SimulationRequest(BaseModel):
    scenario: AttackScenario = "mixed"
    total_events: int = Field(default=80, ge=5, le=5000)
    benign_ratio: float = Field(default=0.35, ge=0.0, le=1.0)
    window_seconds: float = Field(default=2.0, gt=0.1, le=30.0)
    output_name: str = Field(default="simulated_alerts.csv", min_length=3, max_length=120)


class DetectionRequest(BaseModel):
    alert_csv_path: Optional[str] = None
    scenario: Optional[AttackScenario] = None
    total_events: int = Field(default=80, ge=5, le=5000)
    benign_ratio: float = Field(default=0.35, ge=0.0, le=1.0)
    window_seconds: float = Field(default=2.0, gt=0.1, le=30.0)


class SimulationResponse(BaseModel):
    session_id: str
    scenario: AttackScenario
    total_events: int
    output_csv: str
    created_at: datetime
    preview_rows: List[List[str]]


class DetectionSummary(BaseModel):
    predicted_counts: Dict[str, int]
    mean_confidence: float
    max_confidence: float


class DetectionResponse(BaseModel):
    session_id: str
    input_alert_csv: str
    generated_features_csv: str
    predictions_csv: str
    model_checkpoint: str
    total_vectors: int
    summary: DetectionSummary
    sample_predictions: List[Dict]
    created_at: datetime


class StatsResponse(BaseModel):
    total_sessions: int
    total_vectors: int
    attack_counts: Dict[str, int]
    overall_mean_confidence: float
