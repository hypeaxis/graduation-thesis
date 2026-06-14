from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AttackScenario = Literal[
    "normal",
    "port_scan",
    "slow_port_scan",
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
    effective_attack_ratio: float
    dominant_label: str
    dominant_label_share: float
    high_confidence_share: float
    autoencoder_threshold: float
    stage1_normal_gate_rate: float
    stage1_attack_gate_rate: float
    slow_attack_count: int
    slow_attack_ratio: float
    risk_override_applied: bool
    risk_override_count: int
    abnormal_flags: List[str]


class InputProfile(BaseModel):
    selected_feature_means: Dict[str, float]
    selected_feature_std: Dict[str, float]
    slow_attack_score_mean: float
    slow_attack_ratio: float


class DatasetProfile(BaseModel):
    total_rows: int
    selected_features: List[str]
    feature_means: Dict[str, float]
    feature_p95: Dict[str, float]
    label_counts: Dict[str, int]


class DetectionResponse(BaseModel):
    session_id: str
    input_alert_csv: str
    generated_features_csv: str
    predictions_csv: str
    model_checkpoint: str
    total_vectors: int
    summary: DetectionSummary
    diagnostics: Dict[str, Any]
    input_profile: InputProfile
    dataset_profile: DatasetProfile
    sample_features: List[Dict[str, Any]]
    sample_predictions: List[Dict]
    created_at: datetime


class StatsResponse(BaseModel):
    total_sessions: int
    total_vectors: int
    attack_counts: Dict[str, int]
    overall_mean_confidence: float
