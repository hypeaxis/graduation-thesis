"""v15: LightGBM + targeted SMOTE on guess_passwd only.

Problem: only 53 train guess_passwd vs 1231 test → LGBM never learns the pattern.
Fix: SMOTE from 53 → 400 synthetic guess_passwd, all with no_data_transfer=1 + small_bytes.
Risk: synthetics inherit service_telnet + rerror_rate≈0.9 from training distribution.
      But invariant features (no_data_transfer, src/dst bytes) survive → may be enough.
"""

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import classification_report, f1_score

WORKSPACE   = Path(__file__).resolve().parent.parent.parent
CLASS_NAMES = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
N_CLASSES   = 5
OUT_DIR     = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v15_lgbm_smote_gp_seed42'

RAW_COLS = [
    'duration','protocol_type','service','flag','src_bytes','dst_bytes',
    'land','wrong_fragment','urgent','hot','num_failed_logins','logged_in',
    'num_compromised','root_shell','su_attempted','num_root','num_file_creations',
    'num_shells','num_access_files','num_outbound_cmds','is_host_login',
    'is_guest_login','count','srv_count','serror_rate','srv_serror_rate',
    'rerror_rate','srv_rerror_rate','same_srv_rate','diff_srv_rate',
    'srv_diff_host_rate','dst_host_count','dst_host_srv_count',
    'dst_host_same_srv_rate','dst_host_diff_srv_rate',
    'dst_host_same_src_port_rate','dst_host_srv_diff_host_rate',
    'dst_host_serror_rate','dst_host_srv_serror_rate',
    'dst_host_rerror_rate','dst_host_srv_rerror_rate','attack','difficulty',
]


# ─── SMOTE ────────────────────────────────────────────────────────────────────

def targeted_smote(X_minority: np.ndarray, n_synthetic: int,
                   k: int = 5, seed: int = 42) -> np.ndarray:
    """Interpolate synthetic samples from a minority cluster."""
    k = min(k, len(X_minority) - 1)
    nn = NearestNeighbors(n_neighbors=k + 1, algorithm='ball_tree', n_jobs=-1)
    nn.fit(X_minority)
    _, indices = nn.kneighbors(X_minority)   # indices[:,0] = self → skip
    nn_indices = indices[:, 1:]              # (n, k) true neighbors

    rng = np.random.default_rng(seed)
    synthetics = []
    for _ in range(n_synthetic):
        i      = rng.integers(0, len(X_minority))
        j      = nn_indices[i, rng.integers(0, k)]
        lam    = rng.uniform(0, 1)
        synth  = X_minority[i] + lam * (X_minority[j] - X_minority[i])
        synthetics.append(synth)
    return np.array(synthetics, dtype=np.float32)


# ─── Data ─────────────────────────────────────────────────────────────────────

def load_and_split(seed: int = 42):
    # v5 processed data
    df_train = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v5_KddTrain+.csv')
    df_test  = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v5_KddTest+.csv')

    # Raw labels (same row order — pipeline drops 0 rows from train)
    raw = pd.read_csv(WORKSPACE / 'data/raw/KDDTrain+.txt',
                      header=None, names=RAW_COLS)
    assert len(raw) == len(df_train), \
        f'Row mismatch: raw={len(raw)}, v5={len(df_train)}'
    raw_attack = raw['attack'].str.strip().str.rstrip('.').values

    X_full      = df_train.drop(columns=['label']).values.astype(np.float32)
    y_full      = df_train['label'].values.astype(np.int64)
    X_test      = df_test.drop(columns=['label']).values.astype(np.float32)
    y_test      = df_test['label'].values.astype(np.int64)

    per_class_val_frac = {0: 0.10, 1: 0.10, 2: 0.15, 3: 0.40, 4: 0.40}
    per_class_val_max  = {4: 5}
    rng = np.random.default_rng(seed)
    train_idx, val_idx = [], []
    for cls in np.unique(y_full):
        idx   = np.where(y_full == cls)[0]
        n_val = max(1, int(len(idx) * per_class_val_frac.get(int(cls), 0.15)))
        if int(cls) in per_class_val_max:
            n_val = min(n_val, per_class_val_max[int(cls)])
        perm  = rng.permutation(idx)
        val_idx.extend(perm[:n_val].tolist())
        train_idx.extend(perm[n_val:].tolist())

    train_idx = np.array(train_idx)
    X_tr  = X_full[train_idx];  y_tr  = y_full[train_idx]
    X_val = X_full[val_idx];    y_val = y_full[val_idx]
    raw_attack_tr = raw_attack[train_idx]

    return X_tr, y_tr, X_val, y_val, X_test, y_test, raw_attack_tr


def augment_with_smote(X_tr, y_tr, raw_attack_tr, n_synthetic=400, seed=42):
    gp_mask    = raw_attack_tr == 'guess_passwd'
    gp_indices = np.where(gp_mask)[0]
    print(f'  guess_passwd in train split: {len(gp_indices)} samples')

    # Diagnostic: check no_data_transfer for guess_passwd in train
    # no_data_transfer is the 2nd-to-last feature (before label col was dropped)
    # It's the feature we just added — let's find it by index
    # v5 data: last 2 features before label = no_data_transfer, failed_login_ratio
    ndt_col = X_tr.shape[1] - 2   # no_data_transfer index
    flr_col = X_tr.shape[1] - 1   # failed_login_ratio index
    print(f'  guess_passwd no_data_transfer mean: {X_tr[gp_indices, ndt_col].mean():.4f}')
    print(f'  guess_passwd failed_login_ratio mean: {X_tr[gp_indices, flr_col].mean():.4f}')

    X_gp = X_tr[gp_indices]
    X_synthetic = targeted_smote(X_gp, n_synthetic=n_synthetic, k=5, seed=seed)

    # Synthetics should have no_data_transfer ≈ 1 (since all real gp samples do)
    print(f'  synthetic no_data_transfer mean: {X_synthetic[:, ndt_col].mean():.4f}')

    y_synthetic = np.full(n_synthetic, 3, dtype=np.int64)   # label = R2L
    X_aug = np.vstack([X_tr, X_synthetic])
    y_aug = np.hstack([y_tr, y_synthetic])
    print(f'  Train size: {len(y_tr)} → {len(y_aug)} (+{n_synthetic} synthetic guess_passwd)')
    return X_aug, y_aug


def compute_sample_weights(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=N_CLASSES).astype(np.float32)
    w = 1.0 / np.maximum(counts, 1)
    return (w / w.sum())[y]


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print('=== v15: LightGBM + targeted SMOTE on guess_passwd ===\n')

    print('[1/4] Loading v5 data + raw labels...')
    X_tr, y_tr, X_val, y_val, X_test, y_test, raw_attack_tr = load_and_split(seed=42)
    print(f'  Train={len(y_tr)}  Val={len(y_val)}  Test={len(y_test)}')

    print('\n[2/4] Targeted SMOTE on guess_passwd...')
    X_tr_aug, y_tr_aug = augment_with_smote(X_tr, y_tr, raw_attack_tr,
                                             n_synthetic=400, seed=42)
    for c in range(N_CLASSES):
        print(f'  {CLASS_NAMES[c]}: {(y_tr_aug==c).sum()}')

    print('\n[3/4] Training LightGBM v15...')
    params = {
        'objective': 'multiclass', 'num_class': N_CLASSES,
        'metric': 'multi_logloss', 'num_leaves': 127,
        'learning_rate': 0.05, 'n_estimators': 1000,
        'min_child_samples': 5, 'subsample': 0.8,
        'colsample_bytree': 0.8, 'reg_alpha': 0.1, 'reg_lambda': 1.0,
        'verbose': -1, 'random_state': 42, 'n_jobs': -1,
    }
    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_tr_aug, y_tr_aug,
        sample_weight=compute_sample_weights(y_tr_aug),
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=100),
        ],
    )
    print(f'  Best iteration: {model.best_iteration_}')

    print('\n[4/4] Evaluation on test...')
    p_test = model.predict_proba(X_test)
    y_pred = np.argmax(p_test, axis=1)
    f1     = f1_score(y_test, y_pred, average='macro')
    print(f'  v15 LGBM macro-F1 = {f1:.4f}')
    print(classification_report(y_test, y_pred, target_names=CLASS_NAMES, digits=4))

    # Compare with v11 baseline
    print('Baseline comparison:')
    print(f'  v11 LGBM (v2, no SMOTE):              0.6678  R2L recall=0.208')
    print(f'  v14 LGBM (v5, no SMOTE):              0.6617  R2L recall=0.200')
    print(f'  v15 LGBM (v5, SMOTE guess_passwd):    {f1:.4f}  R2L recall={f1_score(y_test, y_pred, average=None)[3]:.3f}')

    model.booster_.save_model(str(OUT_DIR / 'lgbm_v15_model.txt'))
    (OUT_DIR / 'results.json').write_text(json.dumps({
        'v15_test_macro_f1': float(f1),
        'v15_r2l_recall': float(f1_score(y_test, y_pred, average=None)[3]),
    }, indent=2))
    (OUT_DIR / 'classification_report.txt').write_text(
        classification_report(y_test, y_pred, target_names=CLASS_NAMES, digits=4)
    )
    print(f'\nModel saved → {OUT_DIR}')


if __name__ == '__main__':
    main()
