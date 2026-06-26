"""v12: Stacking ensemble — LR meta-learner on 10-dim probability vectors.

Plan v3, Step 1 + Step 2:
  Input : val/test probs from LGBM v11 (5-dim) + FTT v9 (5-dim) = 10-dim
  Meta  : Logistic Regression fit on val → predict on test
  Thresh: per-class threshold tuning on val meta-probs → apply on test
"""

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from scipy.optimize import minimize
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score

WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE / 'src' / 'models'))
from phase2_ft_transformer import FTTransformer  # noqa: E402

CLASS_NAMES = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
N_CLASSES   = 5

V9_CKPT   = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v9_u2r_val_fix_seed42/models/best_model.pt'
V11_MODEL = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v11_lgbm_ensemble_seed42/lgbm_model.txt'
OUT_DIR   = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v12_stacking_seed42'


# ─── Data ─────────────────────────────────────────────────────────────────────

def load_and_split(seed: int = 42):
    df_train = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v2_KddTrain+.csv')
    df_test  = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v2_KddTest+.csv')

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
        perm = rng.permutation(idx)
        val_idx.extend(perm[:n_val].tolist())
        train_idx.extend(perm[n_val:].tolist())

    X_val = X_full[val_idx];  y_val = y_full[val_idx]
    X_test = X_test;          y_test = y_test
    return X_val, y_val, X_test, y_test


# ─── Model inference ──────────────────────────────────────────────────────────

def lgbm_probs(X: np.ndarray) -> np.ndarray:
    booster = lgb.Booster(model_file=str(V11_MODEL))
    raw = booster.predict(X)          # shape (n, 5)
    return raw.astype(np.float32)


def ftt_probs(X: np.ndarray, device: str = 'cpu') -> np.ndarray:
    ckpt  = torch.load(V9_CKPT, map_location=device, weights_only=False)
    model = FTTransformer(num_features=X.shape[1], num_classes=N_CLASSES)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    parts = []
    with torch.no_grad():
        for i in range(0, len(X), 2048):
            logits = model(torch.tensor(X[i:i+2048]))
            parts.append(torch.softmax(logits, dim=1).numpy())
    return np.concatenate(parts)


# ─── Threshold tuning ─────────────────────────────────────────────────────────

def predict_with_thresholds(probs: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """argmax(prob - threshold) per sample."""
    return np.argmax(probs - thresholds[np.newaxis, :], axis=1)


def tune_thresholds(probs_val: np.ndarray, y_val: np.ndarray) -> np.ndarray:
    """Nelder-Mead on val to maximize macro-F1."""
    def neg_f1(t):
        preds = predict_with_thresholds(probs_val, np.array(t))
        return -f1_score(y_val, preds, average='macro', zero_division=0)

    x0     = np.zeros(N_CLASSES)
    result = minimize(neg_f1, x0, method='Nelder-Mead',
                      options={'maxiter': 5000, 'xatol': 1e-4, 'fatol': 1e-4})
    return np.array(result.x)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print('=== v12: Stacking Ensemble (LR meta-learner) ===\n')

    print('[1/5] Loading data...')
    X_val, y_val, X_test, y_test = load_and_split(seed=42)
    print(f'  Val={len(y_val)}  Test={len(y_test)}')
    for c in range(N_CLASSES):
        print(f'    {CLASS_NAMES[c]}: val={(y_val==c).sum()}')

    print('\n[2/5] Getting model probabilities...')
    p_lgbm_val  = lgbm_probs(X_val)
    p_lgbm_test = lgbm_probs(X_test)
    p_ftt_val   = ftt_probs(X_val)
    p_ftt_test  = ftt_probs(X_test)

    # Quick sanity: standalone F1 on test
    f1_lgbm = f1_score(y_test, np.argmax(p_lgbm_test, 1), average='macro')
    f1_ftt  = f1_score(y_test, np.argmax(p_ftt_test,  1), average='macro')
    print(f'  LGBM v11 test macro-F1 = {f1_lgbm:.4f}')
    print(f'  FTT  v9  test macro-F1 = {f1_ftt:.4f}')

    # Stack: [p_lgbm || p_ftt]
    X_meta_val  = np.hstack([p_lgbm_val,  p_ftt_val])   # (n_val,  10)
    X_meta_test = np.hstack([p_lgbm_test, p_ftt_test])  # (n_test, 10)

    print('\n[3/5] Fitting LR meta-learner on val...')
    meta = LogisticRegression(
        solver='lbfgs', C=1.0, max_iter=2000,
        class_weight='balanced', random_state=42
    )
    meta.fit(X_meta_val, y_val)

    # Meta-learner predictions + probabilities
    meta_val_probs  = meta.predict_proba(X_meta_val)
    meta_test_probs = meta.predict_proba(X_meta_test)

    f1_meta_val  = f1_score(y_val,  np.argmax(meta_val_probs,  1), average='macro')
    f1_meta_test = f1_score(y_test, np.argmax(meta_test_probs, 1), average='macro')
    print(f'  Meta-LR  val  macro-F1 = {f1_meta_val:.4f}')
    print(f'  Meta-LR  test macro-F1 = {f1_meta_test:.4f}')
    print(classification_report(y_test, np.argmax(meta_test_probs, 1),
                                 target_names=CLASS_NAMES, digits=4))

    print('[4/5] Per-class threshold tuning on val...')
    thresholds = tune_thresholds(meta_val_probs, y_val)
    print(f'  Tuned thresholds: {dict(zip(CLASS_NAMES, thresholds.round(4)))}')

    y_thresh_val  = predict_with_thresholds(meta_val_probs,  thresholds)
    y_thresh_test = predict_with_thresholds(meta_test_probs, thresholds)
    f1_thresh_val  = f1_score(y_val,  y_thresh_val,  average='macro')
    f1_thresh_test = f1_score(y_test, y_thresh_test, average='macro')
    print(f'  Meta+Thresh  val  macro-F1 = {f1_thresh_val:.4f}')
    print(f'  Meta+Thresh  test macro-F1 = {f1_thresh_test:.4f}')
    print(classification_report(y_test, y_thresh_test, target_names=CLASS_NAMES, digits=4))

    print('[5/5] Saving results...')
    results = {
        'lgbm_v11_test_f1':    float(f1_lgbm),
        'ftt_v9_test_f1':      float(f1_ftt),
        'meta_lr_test_f1':     float(f1_meta_test),
        'meta_thresh_test_f1': float(f1_thresh_test),
        'thresholds':          {CLASS_NAMES[i]: float(thresholds[i]) for i in range(N_CLASSES)},
    }
    (OUT_DIR / 'results.json').write_text(json.dumps(results, indent=2))
    (OUT_DIR / 'meta_lr_report.txt').write_text(
        classification_report(y_test, np.argmax(meta_test_probs, 1),
                               target_names=CLASS_NAMES, digits=4)
    )
    (OUT_DIR / 'meta_thresh_report.txt').write_text(
        classification_report(y_test, y_thresh_test, target_names=CLASS_NAMES, digits=4)
    )

    print(f'\nResults saved → {OUT_DIR}')
    print('\n=== SUMMARY ===')
    print(f'  LGBM v11 alone    : {f1_lgbm:.4f}')
    print(f'  FTT  v9  alone    : {f1_ftt:.4f}')
    print(f'  Meta-LR stacking  : {f1_meta_test:.4f}  ({f1_meta_test-f1_lgbm:+.4f} vs LGBM)')
    print(f'  Meta-LR + Thresh  : {f1_thresh_test:.4f}  ({f1_thresh_test-f1_lgbm:+.4f} vs LGBM)')


if __name__ == '__main__':
    main()
