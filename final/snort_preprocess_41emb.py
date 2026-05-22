import argparse
import json
import pickle
from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from final.snort_preprocess_122 import build_feature_rows, load_snort_alerts


NUMERIC_COLUMNS = [
    'duration', 'src_bytes', 'dst_bytes', 'land', 'wrong_fragment', 'urgent', 'hot',
    'num_failed_logins', 'logged_in', 'num_compromised', 'root_shell', 'su_attempted',
    'num_root', 'num_file_creations', 'num_shells', 'num_access_files', 'num_outbound_cmds',
    'is_host_login', 'is_guest_login', 'count', 'srv_count', 'serror_rate',
    'srv_serror_rate', 'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate',
    'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate',
    'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate', 'dst_host_srv_diff_host_rate',
    'dst_host_serror_rate', 'dst_host_srv_serror_rate', 'dst_host_rerror_rate',
    'dst_host_srv_rerror_rate',
]

CATEGORICAL_COLUMNS = ['protocol_type', 'service', 'flag']


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Convert Snort CSV alerts into 41 logical features with encoded categorical columns.')
    parser.add_argument('--input', default='/home/ning/Graduation-Thesis/final/log/alert.csv')
    parser.add_argument('--categorical-vocabularies', default='/home/ning/Graduation-Thesis/MLAnomalyDetection/artifacts_preprocess_41emb/categorical_vocabularies.json')
    parser.add_argument('--numeric-scaler', default='/home/ning/Graduation-Thesis/MLAnomalyDetection/artifacts_preprocess_41emb/numeric_scaler.pkl')
    parser.add_argument('--output', default='/home/ning/Graduation-Thesis/final/snort_features_41emb.csv')
    parser.add_argument('--window-seconds', type=float, default=2.0)
    return parser.parse_args()


def encode_categoricals(feature_df: pd.DataFrame, vocabularies: dict) -> pd.DataFrame:
    output = feature_df.copy()
    output['protocol_type'] = [vocabularies['protocol_type'].get(str(value).strip(), 0) for value in feature_df['_protocol']]
    output['service'] = [vocabularies['service'].get(str(value).strip(), 0) for value in feature_df['_service']]
    output['flag'] = [vocabularies['flag'].get(str(value).strip(), 0) for value in feature_df['_flag']]
    return output


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    vocab_path = Path(args.categorical_vocabularies)
    scaler_path = Path(args.numeric_scaler)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f'Input Snort CSV not found: {input_path}')
    if not vocab_path.exists():
        raise FileNotFoundError(f'Categorical vocabularies not found: {vocab_path}')

    with open(vocab_path, 'r', encoding='utf-8') as file:
        vocabularies = json.load(file)
    with open(scaler_path, 'rb') as file:
        scaler = pickle.load(file)

    raw_df = load_snort_alerts(input_path)
    feature_df = build_feature_rows(raw_df, window_seconds=args.window_seconds)
    encoded_df = encode_categoricals(feature_df, vocabularies)

    numeric_df = encoded_df[NUMERIC_COLUMNS].copy()
    numeric_df.loc[:, :] = scaler.transform(numeric_df)
    output_df = pd.concat([numeric_df, encoded_df[CATEGORICAL_COLUMNS]], axis=1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(output_path, index=False)
    print(f'Snort input rows: {len(raw_df)}')
    print(f'Output vectors: {len(output_df)}')
    print(f'Feature dimension: {output_df.shape[1]}')
    print(f'Saved: {output_path}')


if __name__ == '__main__':
    main()