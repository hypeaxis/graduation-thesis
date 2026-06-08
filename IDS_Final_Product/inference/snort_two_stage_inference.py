from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import tensorflow as tf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inference.phase2_ft_transformer import FTTransformer
from inference.snort_preprocess_122 import (
    align_to_122_features,
    build_feature_rows,
    load_snort_alerts,
    maybe_scale,
)

DEFAULT_FT_CHECKPOINT = PROJECT_ROOT / 'models' / 'best_model.pt'
DEFAULT_AE_CHECKPOINT = PROJECT_ROOT / 'models' / 'autoencoder_v2_best.h5'
DEFAULT_INFERENCE_CONFIG = PROJECT_ROOT / 'models' / 'inference_config.json'
DEFAULT_SCALER = PROJECT_ROOT / 'models' / 'scaler.pkl'
DEFAULT_FEATURE_COLUMNS = PROJECT_ROOT / 'models' / 'feature_columns.json'
DEFAULT_SNORT_ALERT = PROJECT_ROOT / 'log' / 'alert.csv'
DEFAULT_SNORT_FEATURES = PROJECT_ROOT / 'log' / 'snort_features_122.csv'
DEFAULT_OUTPUT = PROJECT_ROOT / 'log' / 'snort_ft_transformer_predictions.csv'

AUTOENCODER_THRESHOLD = 0.008481


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Two-Stage (Autoencoder + FT-Transformer) inference for Snort.')
    parser.add_argument('--ft-checkpoint', default=str(DEFAULT_FT_CHECKPOINT))
    parser.add_argument('--ae-checkpoint', default=str(DEFAULT_AE_CHECKPOINT))
    parser.add_argument('--inference-config', default=str(DEFAULT_INFERENCE_CONFIG))
    parser.add_argument('--input-features', default=str(DEFAULT_SNORT_FEATURES))
    parser.add_argument('--snort-alert-csv', default=None)
    parser.add_argument('--feature-columns', default=str(DEFAULT_FEATURE_COLUMNS))
    parser.add_argument('--scaler', default=str(DEFAULT_SCALER))
    parser.add_argument('--generated-features-output', default=str(DEFAULT_SNORT_FEATURES))
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--window-seconds', type=float, default=2.0)
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda', 'mps'])
    parser.add_argument('--top-k', type=int, default=3)
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
        raise ValueError('Unable to infer model shape from checkpoint')

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

    class_names = checkpoint.get('class_names') or (inference_config or {}).get('class_names') or ['DoS', 'Probe', 'R2L', 'U2R']
    return model_kwargs, class_names


def load_models(ft_checkpoint_path: Path, ae_checkpoint_path: Path, inference_config_path: Path | None, device: torch.device):
    # Load FT-Transformer
    checkpoint = torch.load(ft_checkpoint_path, map_location=device)
    raw_state_dict = checkpoint['model_state_dict']
    normalized_state_dict = normalize_legacy_state_dict(raw_state_dict)
    inference_config = None
    if inference_config_path and inference_config_path.exists():
        with open(inference_config_path, 'r', encoding='utf-8') as file:
            inference_config = json.load(file)

    model_kwargs, class_names = resolve_model_kwargs(checkpoint, inference_config)
    ft_model = FTTransformer(**model_kwargs).to(device)
    ft_model.load_state_dict(normalized_state_dict, strict=False)
    ft_model.eval()

    # Load Autoencoder
    ae_model = tf.keras.models.load_model(str(ae_checkpoint_path), compile=False)

    return ft_model, ae_model, class_names


def predict(ft_model: FTTransformer, ae_model: tf.keras.Model, feature_df: pd.DataFrame, ft_class_names: list[str], device: torch.device, top_k: int) -> pd.DataFrame:
    X_numpy = feature_df.to_numpy(dtype=np.float32)
    
    # Stage 1: Autoencoder
    X_pred = ae_model.predict(X_numpy, verbose=0)
    mse = np.mean(np.power(X_numpy - X_pred, 2), axis=1)
    is_attack = mse >= AUTOENCODER_THRESHOLD

    # Stage 2: FT-Transformer for attacks
    final_class_names = ['Normal'] + ft_class_names
    num_samples = len(feature_df)
    final_probabilities = np.zeros((num_samples, len(final_class_names)), dtype=np.float32)

    # 1.0 confidence for Normal if not attack
    final_probabilities[~is_attack, 0] = 1.0

    if np.any(is_attack):
        attack_features = X_numpy[is_attack]
        feature_tensor = torch.as_tensor(attack_features, dtype=torch.float32, device=device)
        with torch.no_grad():
            logits = ft_model(feature_tensor)
            attack_probs = torch.softmax(logits, dim=1).cpu().numpy()
        final_probabilities[is_attack, 1:] = attack_probs

    top_k = max(1, min(top_k, final_probabilities.shape[1]))
    top_indices = np.argsort(-final_probabilities, axis=1)[:, :top_k]
    predicted_indices = np.argmax(final_probabilities, axis=1)

    output = pd.DataFrame({
        'predicted_index': predicted_indices,
        'predicted_label': [final_class_names[idx] for idx in predicted_indices],
        'confidence': final_probabilities[np.arange(len(predicted_indices)), predicted_indices],
    })

    for class_index, class_name in enumerate(final_class_names):
        output[f'prob_{class_name}'] = final_probabilities[:, class_index]

    for rank in range(top_k):
        output[f'top_{rank + 1}_label'] = [final_class_names[idx] for idx in top_indices[:, rank]]
        output[f'top_{rank + 1}_confidence'] = final_probabilities[np.arange(len(predicted_indices)), top_indices[:, rank]]

    return output


def load_feature_frame(input_features_path: Path, num_features: int) -> pd.DataFrame:
    feature_df = pd.read_csv(input_features_path)
    if feature_df.shape[1] != num_features:
        raise ValueError(f'Expected {num_features} feature columns, got {feature_df.shape[1]}.')
    return feature_df


def main() -> None:
    args = parse_args()

    ft_checkpoint_path = Path(args.ft_checkpoint)
    ae_checkpoint_path = Path(args.ae_checkpoint)
    inference_config_path = Path(args.inference_config) if args.inference_config else None
    input_features_path = Path(args.input_features)
    snort_alert_csv = Path(args.snort_alert_csv) if args.snort_alert_csv else None
    feature_columns_path = Path(args.feature_columns)
    scaler_path = Path(args.scaler)
    generated_features_output = Path(args.generated_features_output)
    output_path = Path(args.output)

    if not ft_checkpoint_path.exists() or not ae_checkpoint_path.exists():
        raise FileNotFoundError(f'Checkpoints missing. Check paths.')

    if snort_alert_csv is not None:
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
    ft_model, ae_model, class_names = load_models(ft_checkpoint_path, ae_checkpoint_path, inference_config_path, device)

    if feature_df is None:
        feature_df = load_feature_frame(input_features_path, ft_model.num_features)

    predictions = predict(ft_model, ae_model, feature_df, class_names, device, args.top_k)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_path, index=False)

    print(f'Using Two-Stage Architecture')
    print(f'Using device: {device}')
    print(f'Input vectors: {len(feature_df)}')
    print(predictions[['predicted_label', 'confidence']].head().to_string(index=False))


if __name__ == '__main__':
    main()
