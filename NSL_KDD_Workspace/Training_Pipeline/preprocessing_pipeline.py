import json
import pickle
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from sklearn.preprocessing import MinMaxScaler


RAW_COLUMNS = [
    'duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes',
    'land', 'wrong_fragment', 'urgent', 'hot', 'num_failed_logins', 'logged_in',
    'num_compromised', 'root_shell', 'su_attempted', 'num_root', 'num_file_creations',
    'num_shells', 'num_access_files', 'num_outbound_cmds', 'is_host_login',
    'is_guest_login', 'count', 'srv_count', 'serror_rate', 'srv_serror_rate',
    'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate',
    'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count',
    'dst_host_same_srv_rate', 'dst_host_diff_srv_rate',
    'dst_host_same_src_port_rate', 'dst_host_srv_diff_host_rate',
    'dst_host_serror_rate', 'dst_host_srv_serror_rate',
    'dst_host_rerror_rate', 'dst_host_srv_rerror_rate',
    'label', 'difficulty_level'
]

LABEL_GROUPS = {
    'Normal': 0,
    'DoS': 1,
    'Probe': 2,
    'R2L': 3,
    'U2R': 4,
}

LABEL_MAP = {
    # DoS
    'back': 'DoS', 'land': 'DoS', 'neptune': 'DoS', 'pod': 'DoS', 'smurf': 'DoS',
    'teardrop': 'DoS', 'apache2': 'DoS', 'udpstorm': 'DoS', 'processtable': 'DoS',
    'mailbomb': 'DoS',
    # Probe
    'ipsweep': 'Probe', 'nmap': 'Probe', 'portsweep': 'Probe', 'satan': 'Probe',
    'mscan': 'Probe', 'saint': 'Probe',
    # R2L
    'ftp_write': 'R2L', 'guess_passwd': 'R2L', 'imap': 'R2L', 'multihop': 'R2L',
    'phf': 'R2L', 'spy': 'R2L', 'warezclient': 'R2L', 'warezmaster': 'R2L',
    'sendmail': 'R2L', 'named': 'R2L', 'snmpgetattack': 'R2L', 'snmpguess': 'R2L',
    'xlock': 'R2L', 'xsnoop': 'R2L', 'httptunnel': 'R2L',
    # U2R
    'buffer_overflow': 'U2R', 'loadmodule': 'U2R', 'perl': 'U2R', 'rootkit': 'U2R',
    'ps': 'U2R', 'sqlattack': 'U2R', 'xterm': 'U2R',
    # Normal
    'normal': 'Normal',
}


def _read_raw(file_path: Path) -> pd.DataFrame:
    # Use robust encoding fallback because public NSL-KDD files may vary by source.
    for encoding in ('utf-8', 'latin-1', 'cp1252'):
        try:
            return pd.read_csv(file_path, names=RAW_COLUMNS, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(file_path, names=RAW_COLUMNS)


def _basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna().drop_duplicates()
    df = df[df['duration'] >= 0]
    return df


def _normalize_label(raw_label: str) -> str:
    if pd.isna(raw_label):
        return raw_label
    # Some NSL-KDD variants keep trailing dot (e.g., normal.)
    return str(raw_label).strip().rstrip('.')


def _map_labels(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    df = df.copy()
    df['label'] = df['label'].apply(_normalize_label)

    before_counts = df['label'].value_counts().to_dict()
    df['label_group'] = df['label'].map(LABEL_MAP)

    unknown_mask = df['label_group'].isna()
    unknown_counts = df.loc[unknown_mask, 'label'].value_counts().to_dict()

    df = df.loc[~unknown_mask].copy()
    df['label'] = df['label_group'].map(LABEL_GROUPS)
    df.drop(columns=['label_group', 'difficulty_level'], inplace=True)

    stats = {
        'raw_label_counts': before_counts,
        'unknown_label_counts': unknown_counts,
        'known_rows': int((~unknown_mask).sum()),
        'unknown_rows': int(unknown_mask.sum()),
    }
    return df, stats


def _one_hot(df: pd.DataFrame) -> pd.DataFrame:
    return pd.get_dummies(df, columns=['protocol_type', 'service', 'flag'])


def fit_train_preprocessor(
    train_txt_path: str,
    output_train_csv: str,
    artifacts_dir: str,
) -> None:
    train_path = Path(train_txt_path)
    out_csv = Path(output_train_csv)
    artifacts = Path(artifacts_dir)
    artifacts.mkdir(parents=True, exist_ok=True)

    df = _read_raw(train_path)
    df = _basic_clean(df)
    df, stats = _map_labels(df)
    df = _one_hot(df)

    X = df.drop(columns=['label'])
    y = df['label']

    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)

    feature_columns = list(X.columns)
    train_scaled = pd.DataFrame(X_scaled, columns=feature_columns)
    train_scaled['label'] = y.values

    train_scaled.to_csv(out_csv, index=False)

    with open(artifacts / 'feature_columns.json', 'w', encoding='utf-8') as f:
        json.dump(feature_columns, f, ensure_ascii=True, indent=2)

    with open(artifacts / 'label_groups.json', 'w', encoding='utf-8') as f:
        json.dump(LABEL_GROUPS, f, ensure_ascii=True, indent=2)

    with open(artifacts / 'label_map.json', 'w', encoding='utf-8') as f:
        json.dump(LABEL_MAP, f, ensure_ascii=True, indent=2)

    with open(artifacts / 'scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)

    with open(artifacts / 'train_stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=True, indent=2)

    print(f'Train saved: {out_csv}')
    print(f'Artifacts saved: {artifacts}')
    print(f'Known rows: {stats["known_rows"]}, Unknown rows dropped: {stats["unknown_rows"]}')


def transform_test_with_preprocessor(
    test_txt_path: str,
    output_test_csv: str,
    artifacts_dir: str,
) -> None:
    test_path = Path(test_txt_path)
    out_csv = Path(output_test_csv)
    artifacts = Path(artifacts_dir)

    with open(artifacts / 'feature_columns.json', 'r', encoding='utf-8') as f:
        feature_columns = json.load(f)

    with open(artifacts / 'scaler.pkl', 'rb') as f:
        scaler = pickle.load(f)

    df = _read_raw(test_path)
    df = _basic_clean(df)
    df, stats = _map_labels(df)
    df = _one_hot(df)

    X = df.drop(columns=['label'])
    y = df['label']

    missing_cols = sorted(set(feature_columns) - set(X.columns))
    extra_cols = sorted(set(X.columns) - set(feature_columns))

    for col in missing_cols:
        X[col] = 0

    # Drop unseen extra columns in test so model input schema is identical to train.
    if extra_cols:
        X = X.drop(columns=extra_cols)

    X = X[feature_columns]
    X_scaled = scaler.transform(X)

    test_scaled = pd.DataFrame(X_scaled, columns=feature_columns)
    test_scaled['label'] = y.values
    test_scaled.to_csv(out_csv, index=False)

    stats['missing_cols_added'] = missing_cols
    stats['extra_cols_dropped'] = extra_cols

    with open(artifacts / 'test_stats.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=True, indent=2)

    print(f'Test saved: {out_csv}')
    print(f'Known rows: {stats["known_rows"]}, Unknown rows dropped: {stats["unknown_rows"]}')
    print(f'Missing cols added: {len(missing_cols)}, Extra cols dropped: {len(extra_cols)}')


def run_schema_sanity_checks(train_csv: str, test_csv: str) -> None:
    train_df = pd.read_csv(train_csv)
    test_df = pd.read_csv(test_csv)

    train_cols = [c for c in train_df.columns if c != 'label']
    test_cols = [c for c in test_df.columns if c != 'label']

    same_set = set(train_cols) == set(test_cols)
    same_order = train_cols == test_cols

    print(f'Train shape: {train_df.shape}')
    print(f'Test shape: {test_df.shape}')
    print(f'Same feature set: {same_set}')
    print(f'Same feature order: {same_order}')

    if not same_order:
        first_mismatch = next(
            ((i, a, b) for i, (a, b) in enumerate(zip(train_cols, test_cols), start=1) if a != b),
            None,
        )
        if first_mismatch:
            i, a, b = first_mismatch
            print(f'First mismatch at position {i}: train={a}, test={b}')
