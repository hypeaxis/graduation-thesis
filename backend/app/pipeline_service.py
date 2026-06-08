from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from final.snort_ft_transformer_inference_v5 import (
    DEFAULT_FT_CHECKPOINT,
    DEFAULT_AE_CHECKPOINT,
    DEFAULT_FEATURE_COLUMNS,
    DEFAULT_INFERENCE_CONFIG,
    DEFAULT_SCALER,
    load_models,
    pick_device,
    predict,
)
from final.snort_preprocess_122 import (
    align_to_122_features,
    build_feature_rows,
    load_snort_alerts,
    maybe_scale,
)

SIMULATION_DIR = PROJECT_ROOT / "backend" / "data" / "simulations"


def run_detection_from_alert_csv(
    alert_csv_path: Path,
    window_seconds: float,
    generated_features_path: Path | None = None,
    predictions_path: Path | None = None,
    device_choice: str = "cpu",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not alert_csv_path.exists():
        raise FileNotFoundError(f"Alert CSV not found: {alert_csv_path}")

    if generated_features_path is None:
        generated_features_path = SIMULATION_DIR / "snort_features_122_generated.csv"
    if predictions_path is None:
        predictions_path = SIMULATION_DIR / "predictions_generated.csv"

    with open(DEFAULT_FEATURE_COLUMNS, "r", encoding="utf-8") as file:
        feature_columns = json.load(file)

    raw_df = load_snort_alerts(alert_csv_path)
    feature_df = build_feature_rows(raw_df, window_seconds=window_seconds)
    aligned = align_to_122_features(feature_df, feature_columns)
    model_ready = maybe_scale(aligned, DEFAULT_SCALER)

    device = pick_device(device_choice)
    ft_model, ae_model, class_names = load_models(DEFAULT_FT_CHECKPOINT, DEFAULT_AE_CHECKPOINT, DEFAULT_INFERENCE_CONFIG, device)

    if model_ready.shape[1] != ft_model.num_features:
        raise ValueError(
            f"Model expects {ft_model.num_features} features but got {model_ready.shape[1]}"
        )

    predictions = predict(ft_model, ae_model, model_ready, class_names, device, top_k=3)

    generated_features_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.parent.mkdir(parents=True, exist_ok=True)

    model_ready.to_csv(generated_features_path, index=False)
    predictions.to_csv(predictions_path, index=False)

    return model_ready, predictions


def build_summary(predictions: pd.DataFrame) -> dict:
    predicted_counts = (
        predictions["predicted_label"].value_counts(dropna=False).sort_index().to_dict()
    )
    return {
        "predicted_counts": {str(key): int(value) for key, value in predicted_counts.items()},
        "mean_confidence": float(predictions["confidence"].mean()),
        "max_confidence": float(predictions["confidence"].max()),
    }


def new_session_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
