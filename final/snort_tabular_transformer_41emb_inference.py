from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from MLAnomalyDetection.tabular_transformer_41emb import TabularTransformer41Emb
from final.snort_preprocess_41emb import CATEGORICAL_COLUMNS, NUMERIC_COLUMNS
from final.snort_preprocess_41emb import main as _unused  # noqa: F401
from final.snort_preprocess_41emb import parse_args as _unused_args  # noqa: F401


DEFAULT_CHECKPOINT = PROJECT_ROOT / 'MLAnomalyDetection' / 'outputs' / 'tabular_transformer_41emb' / 'models' / 'best_model.pt'
DEFAULT_INFERENCE_CONFIG = PROJECT_ROOT / 'MLAnomalyDetection' / 'outputs' / 'tabular_transformer_41emb' / 'models' / 'inference_config.json'
DEFAULT_INPUT = PROJECT_ROOT / 'final' / 'snort_features_41emb.csv'
DEFAULT_OUTPUT = PROJECT_ROOT / 'final' / 'snort_tabular_transformer_41emb_predictions.csv'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run 41-feature tabular transformer inference for Snort pipeline.')
    parser.add_argument('--checkpoint', default=str(DEFAULT_CHECKPOINT))
    parser.add_argument('--inference-config', default=str(DEFAULT_INFERENCE_CONFIG))
    parser.add_argument('--input-features', default=str(DEFAULT_INPUT))
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--device', default='auto', choices=['auto', 'cpu', 'cuda', 'mps'])
    parser.add_argument('--top-k', type=int, default=3)
    return parser.parse_args()


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


def main() -> None:
    args = parse_args()
    checkpoint_path = Path(args.checkpoint)
    inference_config_path = Path(args.inference_config)
    input_path = Path(args.input_features)
    output_path = Path(args.output)
    device = pick_device(args.device)

    if not checkpoint_path.exists():
        raise FileNotFoundError(f'Checkpoint not found: {checkpoint_path}')
    if not input_path.exists():
        raise FileNotFoundError(f'Input feature CSV not found: {input_path}')

    checkpoint = torch.load(checkpoint_path, map_location=device)
    with open(inference_config_path, 'r', encoding='utf-8') as file:
        inference_config = json.load(file)

    model = TabularTransformer41Emb(**inference_config['model_kwargs']).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    feature_df = pd.read_csv(input_path)
    x_numeric = torch.as_tensor(feature_df[NUMERIC_COLUMNS].to_numpy(), dtype=torch.float32, device=device)
    x_categorical = torch.as_tensor(feature_df[CATEGORICAL_COLUMNS].to_numpy(), dtype=torch.long, device=device)

    with torch.no_grad():
        logits = model(x_numeric, x_categorical)
        probabilities = torch.softmax(logits, dim=1).cpu().numpy()

    class_names = inference_config['class_names']
    predicted_indices = probabilities.argmax(axis=1)
    predictions = pd.DataFrame({
        'predicted_index': predicted_indices,
        'predicted_label': [class_names[index] for index in predicted_indices],
        'confidence': probabilities[range(len(predicted_indices)), predicted_indices],
    })

    top_k = max(1, min(args.top_k, probabilities.shape[1]))
    top_indices = probabilities.argsort(axis=1)[:, ::-1][:, :top_k]
    for rank in range(top_k):
        predictions[f'top_{rank + 1}_label'] = [class_names[index] for index in top_indices[:, rank]]
        predictions[f'top_{rank + 1}_confidence'] = probabilities[range(len(predicted_indices)), top_indices[:, rank]]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_path, index=False)
    print(f'Using checkpoint: {checkpoint_path}')
    print(f'Input vectors: {len(feature_df)}')
    print(f'Feature dimension: {feature_df.shape[1]}')
    print(f'Saved predictions: {output_path}')


if __name__ == '__main__':
    main()