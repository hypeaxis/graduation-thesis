from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from MLAnomalyDetection.phase2_ft_transformer import FTTransformer
from final.snort_preprocess_122 import (
    align_to_122_features,
    build_feature_rows,
    load_snort_alerts,
    maybe_scale,
)


DEFAULT_CHECKPOINT = PROJECT_ROOT / 'MLAnomalyDetection' / 'outputs' / 'ft_transformer_nslkdd' / 'models' / 'best_model.pt'
DEFAULT_INFERENCE_CONFIG = PROJECT_ROOT / 'MLAnomalyDetection' / 'outputs' / 'ft_transformer_nslkdd' / 'models' / 'inference_config.json'
DEFAULT_FEATURE_COLUMNS = PROJECT_ROOT / 'MLAnomalyDetection' / 'artifacts_preprocess' / 'feature_columns.json'
DEFAULT_SCALER = PROJECT_ROOT / 'MLAnomalyDetection' / 'artifacts_preprocess' / 'scaler.pkl'
DEFAULT_SNORT_ALERT = PROJECT_ROOT / 'final' / 'log' / 'alert.csv'
DEFAULT_SNORT_FEATURES = PROJECT_ROOT / 'final' / 'snort_features_122.csv'
DEFAULT_OUTPUT = PROJECT_ROOT / 'final' / 'snort_ft_transformer_predictions.csv'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run FT-Transformer inference for the main Snort pipeline.')
    parser.add_argument('--checkpoint', default=str(DEFAULT_CHECKPOINT), help='Path to FT-Transformer checkpoint.')
    parser.add_argument('--inference-config', default=str(DEFAULT_INFERENCE_CONFIG), help='Path to inference_config.json exported by training.')
    parser.add_argument('--input-features', default=str(DEFAULT_SNORT_FEATURES), help='Path to 122-feature CSV for inference.')
    parser.add_argument('--snort-alert-csv', default=None, help='Optional raw Snort alert CSV. When provided, features are regenerated before inference.')
    parser.add_argument('--feature-columns', default=str(DEFAULT_FEATURE_COLUMNS), help='Path to feature_columns.json used for alignment.')
    parser.add_argument('--scaler', default=str(DEFAULT_SCALER), help='Path to scaler.pkl used for scaling Snort features.')
    parser.add_argument('--generated-features-output', default=str(DEFAULT_SNORT_FEATURES), help='Where to write regenerated features when --snort-alert-csv is used.')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Output CSV path for predictions.')
    parser.add_argument('--window-seconds', type=float, default=2.0, help='Sliding window size used when regenerating features from raw Snort alerts.')
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda', 'mps'], help='Inference device.')
    parser.add_argument('--top-k', type=int, default=3, help='How many top class probabilities to include in the output.')
    return parser.parse_args()


def load_feature_columns(path: Path) -> list[str]:
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def prepare_features_from_snort(
    snort_alert_csv: Path,
    feature_columns_path: Path,
    scaler_path: Path,
    output_path: Path,
    window_seconds: float,
) -> pd.DataFrame:
    raw_df = load_snort_alerts(snort_alert_csv)
    feature_df = build_feature_rows(raw_df, window_seconds=window_seconds)
    aligned = align_to_122_features(feature_df, load_feature_columns(feature_columns_path))
    model_ready = maybe_scale(aligned, scaler_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_ready.to_csv(output_path, index=False)
    return model_ready


def pick_device(choice: str) -> torch.device:
    if choice == 'cuda':
        return torch.device('cuda')
    if choice == 'mps':
        return torch.device('mps')
    if choice == 'cpu':
        return torch.device('cpu')
    if torch.cuda.is_available():
        return torch.device('cuda')
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


def normalize_legacy_state_dict(state_dict: dict) -> dict:
    normalized = {}
    for key, value in state_dict.items():
        new_key = key
        new_key = new_key.replace('feature_embedding.feature_embeddings', 'feature_embedding.feature_projections')
        new_key = new_key.replace('.W_q.', '.w_q.')
        new_key = new_key.replace('.W_k.', '.w_k.')
        new_key = new_key.replace('.W_v.', '.w_v.')
        new_key = new_key.replace('.W_o.', '.w_o.')
        normalized[new_key] = value
    return normalized


def infer_model_kwargs_from_state_dict(state_dict: dict) -> dict:
    cls_token = state_dict.get('feature_embedding.cls_token')
    if cls_token is None:
        raise ValueError('Unable to infer model shape from checkpoint: missing feature_embedding.cls_token')

    feature_pattern = re.compile(r'^feature_embedding\.feature_projections\.(\d+)\.weight$')
    layer_pattern = re.compile(r'^transformer_blocks\.(\d+)\.')

    feature_indices = []
    layer_indices = []
    for key in state_dict:
        feature_match = feature_pattern.match(key)
        if feature_match:
            feature_indices.append(int(feature_match.group(1)))

        layer_match = layer_pattern.match(key)
        if layer_match:
            layer_indices.append(int(layer_match.group(1)))

    if not feature_indices:
        raise ValueError('Unable to infer num_features from checkpoint state_dict')

    classifier_weight = state_dict.get('classifier.3.weight') if state_dict.get('classifier.3.weight') is not None else state_dict.get('classifier.3.bias')
    if classifier_weight is None:
        raise ValueError('Unable to infer num_classes from checkpoint state_dict')

    ffn_weight = state_dict.get('transformer_blocks.0.ffn.0.weight')
    if ffn_weight is None:
        raise ValueError('Unable to infer d_ff from checkpoint state_dict')

    return {
        'num_features': max(feature_indices) + 1,
        'num_classes': int(classifier_weight.shape[0]),
        'd_model': int(cls_token.shape[-1]),
        'num_heads': 8,
        'num_layers': max(layer_indices) + 1 if layer_indices else 4,
        'd_ff': int(ffn_weight.shape[0]),
        'dropout': 0.1,
    }


def resolve_model_kwargs(checkpoint: dict, inference_config: dict | None) -> tuple[dict, list[str]]:
    if inference_config and 'model_kwargs' in inference_config:
        model_kwargs = dict(inference_config['model_kwargs'])
    else:
        config = checkpoint.get('config', {})
        model_kwargs = {
            'num_features': checkpoint.get('num_features'),
            'num_classes': len(checkpoint.get('class_names', [])) or config.get('num_classes', 5),
            'd_model': config.get('d_model', 128),
            'num_heads': config.get('num_heads', 8),
            'num_layers': config.get('num_layers', 4),
            'd_ff': config.get('d_ff', 512),
            'dropout': config.get('dropout', 0.1),
        }

        if model_kwargs['num_features'] is None:
            model_kwargs = infer_model_kwargs_from_state_dict(normalize_legacy_state_dict(checkpoint['model_state_dict']))

    class_names = checkpoint.get('class_names') or (inference_config or {}).get('class_names') or ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
    return model_kwargs, class_names


def load_model(checkpoint_path: Path, inference_config_path: Path | None, device: torch.device) -> tuple[FTTransformer, list[str]]:
    checkpoint = torch.load(checkpoint_path, map_location=device)
    raw_state_dict = checkpoint['model_state_dict']
    normalized_state_dict = normalize_legacy_state_dict(raw_state_dict)
    inference_config = None
    if inference_config_path and inference_config_path.exists():
        with open(inference_config_path, 'r', encoding='utf-8') as file:
            inference_config = json.load(file)

    model_kwargs, class_names = resolve_model_kwargs(checkpoint, inference_config)
    if model_kwargs.get('num_features') is None:
        raise ValueError('Checkpoint does not define num_features; retrain using train_ft_transformer_nslkdd.py to export full inference metadata.')

    model = FTTransformer(**model_kwargs).to(device)
    load_result = model.load_state_dict(normalized_state_dict, strict=False)
    unexpected_keys = [key for key in load_result.unexpected_keys if not key.startswith('optimizer')]
    significant_missing = [
        key for key in load_result.missing_keys
        if not key.startswith('embedding_dropout') and not key.startswith('final_norm')
    ]
    if unexpected_keys or significant_missing:
        raise ValueError(
            'Checkpoint weights are not compatible with the current FT-Transformer implementation. '
            f'Unexpected keys: {unexpected_keys[:5]}, Missing keys: {significant_missing[:5]}'
        )
    model.eval()
    return model, class_names


def load_feature_frame(input_features_path: Path, num_features: int) -> pd.DataFrame:
    feature_df = pd.read_csv(input_features_path)
    if feature_df.shape[1] != num_features:
        raise ValueError(f'Expected {num_features} feature columns, got {feature_df.shape[1]}.')
    return feature_df


def predict(model: FTTransformer, feature_df: pd.DataFrame, class_names: list[str], device: torch.device, top_k: int) -> pd.DataFrame:
    feature_tensor = torch.as_tensor(feature_df.to_numpy(dtype=np.float32), dtype=torch.float32, device=device)

    with torch.no_grad():
        logits = model(feature_tensor)
        probabilities = torch.softmax(logits, dim=1).cpu().numpy()

    top_k = max(1, min(top_k, probabilities.shape[1]))
    top_indices = np.argsort(-probabilities, axis=1)[:, :top_k]
    predicted_indices = np.argmax(probabilities, axis=1)

    output = pd.DataFrame({
        'predicted_index': predicted_indices,
        'predicted_label': [class_names[index] for index in predicted_indices],
        'confidence': probabilities[np.arange(len(predicted_indices)), predicted_indices],
    })

    for class_index, class_name in enumerate(class_names):
        output[f'prob_{class_name}'] = probabilities[:, class_index]

    for rank in range(top_k):
        output[f'top_{rank + 1}_label'] = [class_names[index] for index in top_indices[:, rank]]
        output[f'top_{rank + 1}_confidence'] = probabilities[np.arange(len(predicted_indices)), top_indices[:, rank]]

    return output


def main() -> None:
    args = parse_args()

    checkpoint_path = Path(args.checkpoint)
    inference_config_path = Path(args.inference_config) if args.inference_config else None
    input_features_path = Path(args.input_features)
    snort_alert_csv = Path(args.snort_alert_csv) if args.snort_alert_csv else None
    feature_columns_path = Path(args.feature_columns)
    scaler_path = Path(args.scaler)
    generated_features_output = Path(args.generated_features_output)
    output_path = Path(args.output)

    if not checkpoint_path.exists():
        raise FileNotFoundError(f'Checkpoint not found: {checkpoint_path}')

    if snort_alert_csv is not None:
        if not snort_alert_csv.exists():
            raise FileNotFoundError(f'Snort alert CSV not found: {snort_alert_csv}')
        if not feature_columns_path.exists():
            raise FileNotFoundError(f'Feature schema not found: {feature_columns_path}')

        feature_df = prepare_features_from_snort(
            snort_alert_csv=snort_alert_csv,
            feature_columns_path=feature_columns_path,
            scaler_path=scaler_path,
            output_path=generated_features_output,
            window_seconds=args.window_seconds,
        )
        input_features_path = generated_features_output
    else:
        if not input_features_path.exists():
            raise FileNotFoundError(f'Feature CSV not found: {input_features_path}')
        feature_df = None

    device = pick_device(args.device)
    model, class_names = load_model(checkpoint_path, inference_config_path, device)

    if feature_df is None:
        feature_df = load_feature_frame(input_features_path, model.num_features)
    else:
        if feature_df.shape[1] != model.num_features:
            raise ValueError(f'Generated feature count {feature_df.shape[1]} does not match model expectation {model.num_features}.')

    predictions = predict(model, feature_df, class_names, device, args.top_k)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_path, index=False)

    print(f'Using checkpoint: {checkpoint_path}')
    print(f'Using device: {device}')
    print(f'Input vectors: {len(feature_df)}')
    print(f'Feature dimension: {feature_df.shape[1]}')
    print(f'Saved predictions: {output_path}')
    print(predictions[['predicted_label', 'confidence']].head().to_string(index=False))


if __name__ == '__main__':
    main()