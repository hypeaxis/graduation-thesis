from typing import Optional
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

BALANCE_RANDOM_STATE = 42

LABEL_GROUPS = {
    'Normal': 0,
    'DoS': 1,
    'Probe': 2,
    'R2L': 3,
    'U2R': 4,
}

LABEL_MAP = {
    'back': 'DoS', 'land': 'DoS', 'neptune': 'DoS', 'pod': 'DoS', 'smurf': 'DoS',
    'teardrop': 'DoS', 'apache2': 'DoS', 'udpstorm': 'DoS', 'processtable': 'DoS',
    'mailbomb': 'DoS',
    'ipsweep': 'Probe', 'nmap': 'Probe', 'portsweep': 'Probe', 'satan': 'Probe',
    'mscan': 'Probe', 'saint': 'Probe',
    'ftp_write': 'R2L', 'guess_passwd': 'R2L', 'imap': 'R2L', 'multihop': 'R2L',
    'phf': 'R2L', 'spy': 'R2L', 'warezclient': 'R2L', 'warezmaster': 'R2L',
    'sendmail': 'R2L', 'named': 'R2L', 'snmpgetattack': 'R2L', 'snmpguess': 'R2L',
    'xlock': 'R2L', 'xsnoop': 'R2L', 'httptunnel': 'R2L',
    'buffer_overflow': 'U2R', 'loadmodule': 'U2R', 'perl': 'U2R', 'rootkit': 'U2R',
    'ps': 'U2R', 'sqlattack': 'U2R', 'xterm': 'U2R',
    'normal': 'Normal',
}


def _label_counts_by_name(labels: pd.Series) -> Dict[str, int]:
    inverse_label_groups = {index: name for name, index in LABEL_GROUPS.items()}
    label_counts = labels.value_counts().to_dict()
    return {
        inverse_label_groups[index]: int(label_counts.get(index, 0))
        for index in sorted(inverse_label_groups)
    }


def _build_balance_targets(class_counts: pd.Series) -> Dict[int, int]:
    targets = {}
    for label_value, count in class_counts.items():
        count = int(count)
        if count >= 20000:
            target_count = count
        elif count >= 5000:
            target_count = max(count, 20000)
        elif count >= 500:
            target_count = max(count, 8000)
        else:
            target_count = max(count, 1000)
        targets[int(label_value)] = int(target_count)
    return targets


def _read_raw(file_path: Path) -> pd.DataFrame:
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


def _build_vocab(series: pd.Series) -> Dict[str, int]:
    values = sorted(str(value).strip() for value in series.astype(str).unique())
    return {'__UNK__': 0, **{value: index for index, value in enumerate(values, start=1)}}


def _encode_categories(df: pd.DataFrame, vocabularies: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    encoded = df.copy()
    for column, vocabulary in vocabularies.items():
        encoded[column] = [vocabulary.get(str(value).strip(), 0) for value in encoded[column].astype(str)]
    return encoded


def _prepare_dataframe(df: pd.DataFrame, scaler: Optional[MinMaxScaler], vocabularies: Optional[Dict[str, Dict[str, int]]]):
    df = _basic_clean(df)
    df, stats = _map_labels(df)

    if vocabularies is None:
        vocabularies = {column: _build_vocab(df[column]) for column in CATEGORICAL_COLUMNS}

    encoded = _encode_categories(df, vocabularies)

    numeric_df = encoded[NUMERIC_COLUMNS].copy()
    if scaler is None:
        scaler = MinMaxScaler()
        numeric_df.loc[:, :] = scaler.fit_transform(numeric_df)
    else:
        numeric_df.loc[:, :] = scaler.transform(numeric_df)

    final_df = pd.concat([numeric_df, encoded[CATEGORICAL_COLUMNS], encoded[['label']]], axis=1)
    return final_df, stats, scaler, vocabularies


def _balance_training_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, object]]:
    class_counts = df['label'].value_counts().sort_index()
    target_counts = _build_balance_targets(class_counts)
    balanced_parts = []

    for label_value, group_df in df.groupby('label', sort=True):
        target_count = target_counts[int(label_value)]
        balanced_parts.append(
            group_df.sample(
                n=target_count,
                replace=len(group_df) < target_count,
                random_state=BALANCE_RANDOM_STATE,
            )
        )

    balanced_df = pd.concat(balanced_parts, axis=0)
    balanced_df = balanced_df.sample(frac=1.0, random_state=BALANCE_RANDOM_STATE).reset_index(drop=True)

    balance_stats = {
        'balance_method': 'tiered_random_oversample',
        'rows_before_balance': int(len(df)),
        'rows_after_balance': int(len(balanced_df)),
        'balance_target_rules': {
            'count_gte_20000': 'keep_original_count',
            '5000_to_19999': 'raise_to_20000',
            '500_to_4999': 'raise_to_8000',
            'count_lt_500': 'raise_to_1000',
        },
        'target_counts_by_label': {
            name: int(target_counts[index])
            for name, index in LABEL_GROUPS.items()
        },
        'label_counts_before_balance': _label_counts_by_name(df['label']),
        'label_counts_after_balance': _label_counts_by_name(balanced_df['label']),
    }
    return balanced_df, balance_stats


def fit_train_preprocessor_41emb(train_txt_path: str, output_train_csv: str, artifacts_dir: str) -> None:
    train_path = Path(train_txt_path)
    out_csv = Path(output_train_csv)
    artifacts = Path(artifacts_dir)
    artifacts.mkdir(parents=True, exist_ok=True)

    df = _read_raw(train_path)
    processed_df, stats, scaler, vocabularies = _prepare_dataframe(df, scaler=None, vocabularies=None)
    processed_df, balance_stats = _balance_training_dataframe(processed_df)
    stats.update(balance_stats)
    processed_df.to_csv(out_csv, index=False)

    with open(artifacts / 'numeric_columns.json', 'w', encoding='utf-8') as file:
        json.dump(NUMERIC_COLUMNS, file, ensure_ascii=True, indent=2)
    with open(artifacts / 'categorical_columns.json', 'w', encoding='utf-8') as file:
        json.dump(CATEGORICAL_COLUMNS, file, ensure_ascii=True, indent=2)
    with open(artifacts / 'categorical_vocabularies.json', 'w', encoding='utf-8') as file:
        json.dump(vocabularies, file, ensure_ascii=True, indent=2)
    with open(artifacts / 'label_groups.json', 'w', encoding='utf-8') as file:
        json.dump(LABEL_GROUPS, file, ensure_ascii=True, indent=2)
    with open(artifacts / 'label_map.json', 'w', encoding='utf-8') as file:
        json.dump(LABEL_MAP, file, ensure_ascii=True, indent=2)
    with open(artifacts / 'numeric_scaler.pkl', 'wb') as file:
        pickle.dump(scaler, file)
    with open(artifacts / 'train_stats.json', 'w', encoding='utf-8') as file:
        json.dump(stats, file, ensure_ascii=True, indent=2)

    print(f'Train saved: {out_csv}')
    print(f'Artifacts saved: {artifacts}')
    print(f'Known rows: {stats["known_rows"]}, Unknown rows dropped: {stats["unknown_rows"]}')
    print(f'Balanced rows: {stats["rows_before_balance"]} -> {stats["rows_after_balance"]}')


def transform_test_with_preprocessor_41emb(test_txt_path: str, output_test_csv: str, artifacts_dir: str) -> None:
    test_path = Path(test_txt_path)
    out_csv = Path(output_test_csv)
    artifacts = Path(artifacts_dir)

    with open(artifacts / 'categorical_vocabularies.json', 'r', encoding='utf-8') as file:
        vocabularies = json.load(file)
    with open(artifacts / 'numeric_scaler.pkl', 'rb') as file:
        scaler = pickle.load(file)

    df = _read_raw(test_path)
    processed_df, stats, _, _ = _prepare_dataframe(df, scaler=scaler, vocabularies=vocabularies)
    processed_df.to_csv(out_csv, index=False)

    with open(artifacts / 'test_stats.json', 'w', encoding='utf-8') as file:
        json.dump(stats, file, ensure_ascii=True, indent=2)

    print(f'Test saved: {out_csv}')
    print(f'Known rows: {stats["known_rows"]}, Unknown rows dropped: {stats["unknown_rows"]}')


def run_schema_sanity_checks_41emb(train_csv: str, test_csv: str) -> None:
    train_df = pd.read_csv(train_csv)
    test_df = pd.read_csv(test_csv)

    train_cols = [column for column in train_df.columns if column != 'label']
    test_cols = [column for column in test_df.columns if column != 'label']

    print(f'Train shape: {train_df.shape}')
    print(f'Test shape: {test_df.shape}')
    print(f'Same feature order: {train_cols == test_cols}')
    print(f'Numeric feature count: {len(NUMERIC_COLUMNS)}')
    print(f'Categorical feature count: {len(CATEGORICAL_COLUMNS)}')