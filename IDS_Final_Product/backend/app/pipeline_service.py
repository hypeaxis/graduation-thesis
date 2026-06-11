from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inference.snort_two_stage_inference import (
    AUTOENCODER_THRESHOLD,
    DEFAULT_AE_CHECKPOINT,
    DEFAULT_FEATURE_COLUMNS,
    DEFAULT_FT_CHECKPOINT,
    DEFAULT_INFERENCE_CONFIG,
    DEFAULT_SCALER,
    calibrate_autoencoder_threshold,
    load_models,
    pick_device,
    predict,
)
from inference.snort_preprocess_122 import (
    align_to_122_features,
    build_feature_rows,
    load_snort_alerts,
    maybe_scale,
)

from .simulator import generate_alert_rows, write_snort_csv

SIMULATION_DIR = PROJECT_ROOT / "backend" / "data" / "simulations"
MODELS_DIR = PROJECT_ROOT / "models"
DATASET_PROFILE_PATH = MODELS_DIR / "dataset_profile.json"
TRAIN_STATS_PATH = MODELS_DIR / "train_stats.json"
TEST_STATS_PATH = MODELS_DIR / "test_stats.json"

RUNTIME_STATE: dict[str, object] = {
    "threshold": None,
    "smoke_report": None,
}


def _load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default or {}
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _require_artifacts() -> None:
    required = {
        "FT checkpoint": DEFAULT_FT_CHECKPOINT,
        "Autoencoder checkpoint": DEFAULT_AE_CHECKPOINT,
        "Feature columns": DEFAULT_FEATURE_COLUMNS,
        "Scaler": DEFAULT_SCALER,
    }
    missing = [f"{name}: {path}" for name, path in required.items() if not Path(path).exists()]
    if missing:
        raise FileNotFoundError("Missing required model artifacts:\n" + "\n".join(missing))


def _load_dataset_profile() -> dict:
    if DATASET_PROFILE_PATH.exists():
        profile = _load_json(DATASET_PROFILE_PATH, default={})
        return {
            "total_rows": int(profile.get("total_rows", 0)),
            "selected_features": list(profile.get("selected_features", [])),
            "feature_means": dict(profile.get("feature_means", {})),
            "feature_p95": dict(profile.get("feature_p95", {})),
            "label_counts": {str(k): int(v) for k, v in profile.get("label_counts", {}).items()},
        }

    train_stats = _load_json(TRAIN_STATS_PATH, default={})
    return {
        "total_rows": int(train_stats.get("known_rows", 0)),
        "selected_features": [],
        "feature_means": {},
        "feature_p95": {},
        "label_counts": {str(k): int(v) for k, v in train_stats.get("raw_label_counts", {}).items()},
    }


def _build_input_profile(feature_df: pd.DataFrame) -> dict:
    selected = [
        "count",
        "srv_count",
        "same_srv_rate",
        "diff_srv_rate",
        "dst_host_count",
        "dst_host_srv_count",
        "serror_rate",
        "rerror_rate",
    ]
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for col in selected:
        if col in feature_df.columns:
            means[col] = float(feature_df[col].mean())
            stds[col] = float(feature_df[col].std(ddof=0))

    slow_attack_score_mean = float(feature_df["slow_attack_score"].mean()) if "slow_attack_score" in feature_df.columns else 0.0
    slow_attack_ratio = float(feature_df["slow_attack_flag"].mean()) if "slow_attack_flag" in feature_df.columns else 0.0

    return {
        "selected_feature_means": means,
        "selected_feature_std": stds,
        "slow_attack_score_mean": slow_attack_score_mean,
        "slow_attack_ratio": slow_attack_ratio,
    }


def _dominant_label(counts: dict[str, int]) -> tuple[str, float]:
    if not counts:
        return "NA", 0.0
    total = max(sum(counts.values()), 1)
    label = max(counts.items(), key=lambda item: item[1])[0]
    share = float(counts[label] / total)
    return label, share


def _analyze_prediction_health(
    predictions: pd.DataFrame,
    stage_diagnostics: dict,
    high_confidence_threshold: float,
    dominant_label_threshold: float,
) -> dict:
    total = max(len(predictions), 1)
    counts = predictions["predicted_label"].value_counts(dropna=False).to_dict()
    label, label_share = _dominant_label({str(k): int(v) for k, v in counts.items()})

    conf_series = predictions["confidence"] if "confidence" in predictions.columns else pd.Series(dtype=float)
    mean_conf = float(conf_series.mean()) if len(conf_series) else 0.0
    high_conf_share = float((conf_series >= high_confidence_threshold).mean()) if len(conf_series) else 0.0

    abnormal_flags: list[str] = []
    if label_share >= dominant_label_threshold:
        abnormal_flags.append(f"Dominant label concentration is high: {label} ({label_share:.2%})")
    if mean_conf >= 0.9 and high_conf_share >= 0.7:
        abnormal_flags.append("Confidence distribution is unusually high; inspect calibration and data drift")

    normal_gate = float(stage_diagnostics.get("stage1_normal_gate_rate", 0.0))
    if normal_gate < 0.05:
        abnormal_flags.append("Stage-1 normal gate rate is too low (<5%); likely over-filtering to attack branch")
    if normal_gate > 0.98:
        abnormal_flags.append("Stage-1 normal gate rate is too high (>98%); likely missing attacks")

    slow_ratio = float(stage_diagnostics.get("slow_attack_ratio", 0.0))
    if slow_ratio >= 0.25:
        abnormal_flags.append("Slow attack pattern ratio is elevated; review slow-scan traffic")

    return {
        "dominant_label": label,
        "dominant_label_share": label_share,
        "high_confidence_share": high_conf_share,
        "total_vectors": total,
        "abnormal_flags": abnormal_flags,
    }


def _probability_columns(predictions: pd.DataFrame) -> list[str]:
    return [col for col in predictions.columns if col.startswith("prob_")]


def _recompute_prediction_ranks(predictions: pd.DataFrame, top_k: int = 3) -> None:
    prob_cols = _probability_columns(predictions)
    if not prob_cols or predictions.empty:
        return

    probs = predictions[prob_cols].to_numpy(dtype=np.float32)
    row_sums = probs.sum(axis=1, keepdims=True)

    invalid_rows = row_sums.squeeze() <= 0
    if np.any(invalid_rows):
        probs[invalid_rows, :] = 0.0
        normal_index = prob_cols.index("prob_Normal") if "prob_Normal" in prob_cols else 0
        probs[invalid_rows, normal_index] = 1.0
        row_sums = probs.sum(axis=1, keepdims=True)

    probs = probs / np.clip(row_sums, 1e-9, None)
    predictions.loc[:, prob_cols] = probs

    class_names = [col[5:] for col in prob_cols]
    top_k = max(1, min(int(top_k), len(class_names)))
    top_indices = np.argsort(-probs, axis=1)[:, :top_k]
    predicted_indices = top_indices[:, 0]

    predictions["predicted_index"] = predicted_indices.astype(np.int32)
    predictions["predicted_label"] = [class_names[idx] for idx in predicted_indices]
    predictions["confidence"] = probs[np.arange(len(predicted_indices)), predicted_indices]

    for rank in range(top_k):
        predictions[f"top_{rank + 1}_label"] = [class_names[idx] for idx in top_indices[:, rank]]
        predictions[f"top_{rank + 1}_confidence"] = probs[np.arange(len(predicted_indices)), top_indices[:, rank]]


def _apply_slow_attack_risk_override(predictions: pd.DataFrame, inference_config: dict) -> dict:
    report = {
        "risk_override_applied": False,
        "risk_override_count": 0,
        "risk_override_reason": "not-triggered",
    }

    required_columns = {"predicted_label", "slow_attack_flag", "slow_attack_score"}
    if predictions.empty or not required_columns.issubset(predictions.columns):
        report["risk_override_reason"] = "missing-slow-attack-columns"
        return report

    prob_cols = _probability_columns(predictions)
    if "prob_Probe" not in prob_cols or "prob_Normal" not in prob_cols:
        report["risk_override_reason"] = "missing-probability-columns"
        return report

    stage1_normal_gate_rate = float((predictions["stage1_is_attack"] == 0).mean()) if "stage1_is_attack" in predictions.columns else 0.0
    slow_attack_ratio = float(predictions["slow_attack_flag"].mean())

    gate_threshold = float(inference_config.get("stage1_normal_gate_override_threshold", 0.985))
    slow_ratio_threshold = float(inference_config.get("slow_attack_ratio_override_threshold", 0.35))
    slow_score_threshold = float(inference_config.get("slow_attack_score_override_threshold", 0.65))
    min_rows = max(1, int(inference_config.get("slow_attack_override_min_rows", 4)))

    if stage1_normal_gate_rate < gate_threshold and slow_attack_ratio < slow_ratio_threshold:
        report["risk_override_reason"] = "gate-and-ratio-below-threshold"
        return report

    candidate_mask = (
        (predictions["predicted_label"] == "Normal")
        & (predictions["slow_attack_flag"] > 0)
        & (predictions["slow_attack_score"] >= slow_score_threshold)
    )
    candidate_indices = predictions.index[candidate_mask]
    if len(candidate_indices) < min_rows:
        report["risk_override_reason"] = "insufficient-candidates"
        return report

    probe_idx = prob_cols.index("prob_Probe")
    normal_idx = prob_cols.index("prob_Normal")

    candidate_probs = predictions.loc[candidate_indices, prob_cols].to_numpy(dtype=np.float32)
    slow_scores = predictions.loc[candidate_indices, "slow_attack_score"].to_numpy(dtype=np.float32)
    score_span = max(1.0 - slow_score_threshold, 1e-6)
    risk_levels = np.clip((slow_scores - slow_score_threshold) / score_span, 0.0, 1.0)
    target_probe_conf = np.clip(0.62 + 0.30 * risk_levels, 0.62, 0.92)

    for i in range(len(candidate_indices)):
        candidate_probs[i, probe_idx] = max(candidate_probs[i, probe_idx], float(target_probe_conf[i]))

        if candidate_probs[i, normal_idx] >= candidate_probs[i, probe_idx]:
            candidate_probs[i, normal_idx] = max(0.0, candidate_probs[i, probe_idx] - 0.05)

        row_sum = float(candidate_probs[i].sum())
        if row_sum <= 0:
            candidate_probs[i, :] = 0.0
            candidate_probs[i, probe_idx] = 1.0
        else:
            candidate_probs[i, :] = candidate_probs[i, :] / row_sum

        best_idx = int(np.argmax(candidate_probs[i]))
        if best_idx != probe_idx:
            desired_probe = min(0.95, max(candidate_probs[i, best_idx] + 0.01, candidate_probs[i, probe_idx]))
            remaining = 1.0 - desired_probe
            other_indices = [j for j in range(candidate_probs.shape[1]) if j != probe_idx]
            other_sum = float(candidate_probs[i, other_indices].sum())
            if other_sum <= 0:
                candidate_probs[i, :] = 0.0
                candidate_probs[i, probe_idx] = 1.0
            else:
                candidate_probs[i, other_indices] = candidate_probs[i, other_indices] * (remaining / other_sum)
                candidate_probs[i, probe_idx] = desired_probe

    predictions.loc[candidate_indices, prob_cols] = candidate_probs
    if "risk_override" not in predictions.columns:
        predictions["risk_override"] = "none"
    predictions.loc[candidate_indices, "risk_override"] = "slow_scan_heuristic"
    predictions.loc[candidate_indices, "traffic_pattern_label"] = "SlowAttackSuspected"

    report["risk_override_applied"] = True
    report["risk_override_count"] = int(len(candidate_indices))
    report["risk_override_reason"] = "slow-scan-candidates-promoted"
    return report


def _calibrate_threshold_once(
    ft_model,
    ae_model,
    class_names: list[str],
    device,
    feature_columns: list[str],
    calibration_quantile: float,
    baseline_threshold: float,
) -> tuple[float, dict]:
    cached_threshold = RUNTIME_STATE.get("threshold")
    cached_report = RUNTIME_STATE.get("smoke_report")
    if isinstance(cached_threshold, float) and isinstance(cached_report, dict):
        return cached_threshold, cached_report

    SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
    calibration_alert_csv = SIMULATION_DIR / "_calibration_normal_alerts.csv"
    calibration_rows = generate_alert_rows(
        scenario="normal",
        total_events=240,
        benign_ratio=1.0,
        seed=42,
    )
    write_snort_csv(calibration_rows, calibration_alert_csv)

    raw_df = load_snort_alerts(calibration_alert_csv)
    feature_df = build_feature_rows(raw_df, window_seconds=2.0)
    aligned = align_to_122_features(feature_df, feature_columns)
    model_ready = maybe_scale(aligned, DEFAULT_SCALER, strict=True)

    threshold = calibrate_autoencoder_threshold(
        ae_model=ae_model,
        calibration_features=model_ready,
        quantile=calibration_quantile,
        min_threshold=baseline_threshold,
    )

    slow_scores = feature_df["slow_attack_score"].to_numpy(dtype=np.float32) if "slow_attack_score" in feature_df.columns else None
    slow_flags = feature_df["slow_attack_flag"].to_numpy(dtype=np.float32) if "slow_attack_flag" in feature_df.columns else None

    smoke_predictions, smoke_diag = predict(
        ft_model=ft_model,
        ae_model=ae_model,
        feature_df=model_ready,
        ft_class_names=class_names,
        device=device,
        top_k=3,
        autoencoder_threshold=threshold,
        slow_attack_scores=slow_scores,
        slow_attack_flags=slow_flags,
    )

    normal_rate = float((smoke_predictions["predicted_label"] == "Normal").mean()) if len(smoke_predictions) else 0.0
    if normal_rate < 0.45:
        fallback_threshold = float(smoke_predictions["stage1_mse"].quantile(0.995))
        threshold = max(threshold, fallback_threshold)
        smoke_predictions, smoke_diag = predict(
            ft_model=ft_model,
            ae_model=ae_model,
            feature_df=model_ready,
            ft_class_names=class_names,
            device=device,
            top_k=3,
            autoencoder_threshold=threshold,
            slow_attack_scores=slow_scores,
            slow_attack_flags=slow_flags,
        )
        normal_rate = float((smoke_predictions["predicted_label"] == "Normal").mean()) if len(smoke_predictions) else 0.0

    smoke_report = {
        "smoke_passed": bool(normal_rate >= 0.45),
        "calibration_quantile": float(calibration_quantile),
        "threshold": float(threshold),
        "normal_rate": normal_rate,
        "sample_size": int(len(smoke_predictions)),
        "stage1_normal_gate_rate": float(smoke_diag.get("stage1_normal_gate_rate", 0.0)),
    }

    if not smoke_report["smoke_passed"]:
        raise RuntimeError(
            "Two-stage smoke test failed on benign calibration data "
            f"(normal_rate={normal_rate:.3f}, threshold={threshold:.6f})"
        )

    RUNTIME_STATE["threshold"] = float(threshold)
    RUNTIME_STATE["smoke_report"] = smoke_report
    return float(threshold), smoke_report


def run_detection_from_alert_csv(
    alert_csv_path: Path,
    window_seconds: float,
    generated_features_path: Path | None = None,
    predictions_path: Path | None = None,
    device_choice: str = "cpu",
) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict, dict]:
    if not alert_csv_path.exists():
        raise FileNotFoundError(f"Alert CSV not found: {alert_csv_path}")

    _require_artifacts()

    if generated_features_path is None:
        generated_features_path = SIMULATION_DIR / "snort_features_122_generated.csv"
    if predictions_path is None:
        predictions_path = SIMULATION_DIR / "predictions_generated.csv"

    inference_config = _load_json(DEFAULT_INFERENCE_CONFIG, default={})
    with open(DEFAULT_FEATURE_COLUMNS, "r", encoding="utf-8") as file:
        feature_columns = json.load(file)

    raw_df = load_snort_alerts(alert_csv_path)
    feature_df = build_feature_rows(raw_df, window_seconds=window_seconds)
    aligned = align_to_122_features(feature_df, feature_columns)
    model_ready = maybe_scale(aligned, DEFAULT_SCALER, strict=True)

    device = pick_device(device_choice)
    ft_model, ae_model, class_names = load_models(DEFAULT_FT_CHECKPOINT, DEFAULT_AE_CHECKPOINT, DEFAULT_INFERENCE_CONFIG, device)

    if model_ready.shape[1] != ft_model.num_features:
        raise ValueError(
            f"Model expects {ft_model.num_features} features but got {model_ready.shape[1]}"
        )

    calibration_quantile = float(inference_config.get("threshold_calibration_quantile", 0.99))
    baseline_threshold = float(inference_config.get("autoencoder_threshold", AUTOENCODER_THRESHOLD))
    runtime_threshold, smoke_report = _calibrate_threshold_once(
        ft_model=ft_model,
        ae_model=ae_model,
        class_names=class_names,
        device=device,
        feature_columns=feature_columns,
        calibration_quantile=calibration_quantile,
        baseline_threshold=baseline_threshold,
    )

    slow_scores = feature_df["slow_attack_score"].to_numpy(dtype=np.float32) if "slow_attack_score" in feature_df.columns else None
    slow_flags = feature_df["slow_attack_flag"].to_numpy(dtype=np.float32) if "slow_attack_flag" in feature_df.columns else None

    predictions, stage_diagnostics = predict(
        ft_model=ft_model,
        ae_model=ae_model,
        feature_df=model_ready,
        ft_class_names=class_names,
        device=device,
        top_k=3,
        autoencoder_threshold=runtime_threshold,
        slow_attack_scores=slow_scores,
        slow_attack_flags=slow_flags,
    )

    override_report = _apply_slow_attack_risk_override(predictions, inference_config)
    if override_report.get("risk_override_applied"):
        _recompute_prediction_ranks(predictions, top_k=3)

    high_conf_threshold = float(inference_config.get("high_confidence_threshold", 0.95))
    dominant_warn_threshold = float(inference_config.get("dominant_label_warning_threshold", 0.9))
    health_diagnostics = _analyze_prediction_health(
        predictions=predictions,
        stage_diagnostics=stage_diagnostics,
        high_confidence_threshold=high_conf_threshold,
        dominant_label_threshold=dominant_warn_threshold,
    )

    if override_report.get("risk_override_applied"):
        health_diagnostics.setdefault("abnormal_flags", []).append(
            "Risk override activated: promoted slow-scan candidates to reduce false-normal risk"
        )

    diagnostics = {
        **stage_diagnostics,
        **health_diagnostics,
        **override_report,
        "smoke_report": smoke_report,
    }

    feature_export = model_ready.copy()
    for col in [
        "flow_inter_arrival_sec",
        "src_conn_count_60s",
        "src_unique_dst_ports_60s",
        "slow_attack_score",
        "slow_attack_flag",
    ]:
        if col in feature_df.columns:
            feature_export[col] = feature_df[col].astype(float)

    generated_features_path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path.parent.mkdir(parents=True, exist_ok=True)

    feature_export.to_csv(generated_features_path, index=False)
    predictions.to_csv(predictions_path, index=False)

    input_profile = _build_input_profile(feature_df)
    dataset_profile = _load_dataset_profile()

    return feature_export, predictions, diagnostics, input_profile, dataset_profile


def build_summary(predictions: pd.DataFrame, diagnostics: dict) -> dict:
    predicted_counts = predictions["predicted_label"].value_counts(dropna=False).sort_index().to_dict()
    total = max(int(len(predictions)), 1)
    normal_count = int(predicted_counts.get("Normal", 0))
    return {
        "predicted_counts": {str(key): int(value) for key, value in predicted_counts.items()},
        "mean_confidence": float(predictions["confidence"].mean()) if len(predictions) else 0.0,
        "max_confidence": float(predictions["confidence"].max()) if len(predictions) else 0.0,
        "effective_attack_ratio": float((total - normal_count) / total),
        "dominant_label": str(diagnostics.get("dominant_label", "NA")),
        "dominant_label_share": float(diagnostics.get("dominant_label_share", 0.0)),
        "high_confidence_share": float(diagnostics.get("high_confidence_share", 0.0)),
        "autoencoder_threshold": float(diagnostics.get("autoencoder_threshold", AUTOENCODER_THRESHOLD)),
        "stage1_normal_gate_rate": float(diagnostics.get("stage1_normal_gate_rate", 0.0)),
        "stage1_attack_gate_rate": float(diagnostics.get("stage1_attack_gate_rate", 0.0)),
        "slow_attack_count": int(diagnostics.get("slow_attack_count", 0)),
        "slow_attack_ratio": float(diagnostics.get("slow_attack_ratio", 0.0)),
        "risk_override_applied": bool(diagnostics.get("risk_override_applied", False)),
        "risk_override_count": int(diagnostics.get("risk_override_count", 0)),
        "abnormal_flags": list(diagnostics.get("abnormal_flags", [])),
    }


def new_session_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
