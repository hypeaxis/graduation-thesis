"""v14: LightGBM retrained on v5 data (drift-invariant features).

Same hyperparams as v11 (num_leaves=127, lr=0.05, n_estimators=1000, early_stop=50).
New input: v5 data = v2 base + no_data_transfer + failed_login_ratio (124 features).
"""

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score

WORKSPACE = Path(__file__).resolve().parent.parent.parent
CLASS_NAMES = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
N_CLASSES   = 5
OUT_DIR     = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v14_lgbm_v5_seed42'


def load_and_split(seed: int = 42):
    df_train = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v5_KddTrain+.csv')
    df_test  = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v5_KddTest+.csv')

    X_full = df_train.drop(columns=['label']).values.astype(np.float32)
    y_full = df_train['label'].values.astype(np.int64)
    X_test = df_test.drop(columns=['label']).values.astype(np.float32)
    y_test = df_test['label'].values.astype(np.int64)

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

    return (X_full[train_idx], y_full[train_idx],
            X_full[val_idx],   y_full[val_idx],
            X_test,            y_test)


def compute_sample_weights(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=N_CLASSES).astype(np.float32)
    w = 1.0 / np.maximum(counts, 1)
    return (w / w.sum())[y]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print('=== v14: LightGBM on v5 data (drift-invariant features) ===\n')

    print('[1/3] Loading v5 data...')
    X_tr, y_tr, X_val, y_val, X_test, y_test = load_and_split(seed=42)
    print(f'  Train={len(y_tr)}  Val={len(y_val)}  Test={len(y_test)}')
    print(f'  Input features: {X_tr.shape[1]}')
    for c in range(N_CLASSES):
        print(f'    {CLASS_NAMES[c]}: train={(y_tr==c).sum()}  val={(y_val==c).sum()}')

    print('\n[2/3] Training LightGBM v14...')
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
        X_tr, y_tr,
        sample_weight=compute_sample_weights(y_tr),
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=100),
        ],
    )
    print(f'  Best iteration: {model.best_iteration_}')

    print('\n[3/3] Evaluation on test...')
    p_test = model.predict_proba(X_test)
    y_pred = np.argmax(p_test, axis=1)
    f1     = f1_score(y_test, y_pred, average='macro')
    print(f'  v14 LGBM test macro-F1 = {f1:.4f}')
    print(classification_report(y_test, y_pred, target_names=CLASS_NAMES, digits=4))

    # Feature importance for new features
    feat_imp = dict(zip(
        ['no_data_transfer', 'failed_login_ratio'],
        [model.feature_importances_[-2], model.feature_importances_[-1]]
    ))
    print(f'  Feature importance (new v5 features): {feat_imp}')

    model.booster_.save_model(str(OUT_DIR / 'lgbm_v14_model.txt'))
    result = {'v14_lgbm_v5_test_macro_f1': float(f1)}
    (OUT_DIR / 'results.json').write_text(json.dumps(result, indent=2))
    (OUT_DIR / 'classification_report.txt').write_text(
        classification_report(y_test, y_pred, target_names=CLASS_NAMES, digits=4)
    )
    print(f'\nModel saved → {OUT_DIR}')


if __name__ == '__main__':
    main()
