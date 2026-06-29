"""P4: LightGBM + FT-Transformer ensemble on NSL-KDD 5-class.

Strategy:
  1. Load same v2 data with the SAME boost-minority split as v9 (seed=42)
  2. Train LightGBM with class-aware sample_weight on train split
  3. Soft ensemble: alpha*lgbm_prob + (1-alpha)*ftt_prob
  4. Sweep alpha on val to find best ensemble weight
  5. Evaluate final ensemble on test → report macro-F1 + per-class
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import lightgbm as lgb
from sklearn.metrics import classification_report, f1_score

WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE / 'src' / 'models'))
from phase2_ft_transformer import FTTransformer  # noqa: E402

CLASS_NAMES = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
N_CLASSES = 5


# ─── Data ────────────────────────────────────────────────────────────────────

def load_and_split(seed: int = 42):
    df_train = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v2_KddTrain+.csv')
    df_test  = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v2_KddTest+.csv')

    X_full = df_train.drop(columns=['label']).values.astype(np.float32)
    y_full = df_train['label'].values.astype(np.int64)
    X_test = df_test.drop(columns=['label']).values.astype(np.float32)
    y_test = df_test['label'].values.astype(np.int64)

    # Same split as v9
    per_class_val_frac = {0: 0.10, 1: 0.10, 2: 0.15, 3: 0.40, 4: 0.40}
    per_class_val_max  = {4: 5}
    rng = np.random.default_rng(seed)
    train_idx, val_idx = [], []
    for cls in np.unique(y_full):
        idx = np.where(y_full == cls)[0]
        n_val = max(1, int(len(idx) * per_class_val_frac.get(int(cls), 0.15)))
        if int(cls) in per_class_val_max:
            n_val = min(n_val, per_class_val_max[int(cls)])
        perm = rng.permutation(idx)
        val_idx.extend(perm[:n_val].tolist())
        train_idx.extend(perm[n_val:].tolist())

    X_tr = X_full[train_idx]; y_tr = y_full[train_idx]
    X_val = X_full[val_idx];  y_val = y_full[val_idx]
    return X_tr, y_tr, X_val, y_val, X_test, y_test


# ─── LightGBM ────────────────────────────────────────────────────────────────

def compute_sample_weights(y: np.ndarray) -> np.ndarray:
    """Inverse-frequency weights to handle class imbalance."""
    counts = np.bincount(y, minlength=N_CLASSES).astype(np.float32)
    weights_per_class = 1.0 / np.maximum(counts, 1)
    weights_per_class /= weights_per_class.sum()
    return weights_per_class[y]


def train_lgbm(X_tr, y_tr, X_val, y_val, seed: int = 42):
    sample_weight = compute_sample_weights(y_tr)

    params = {
        'objective': 'multiclass',
        'num_class': N_CLASSES,
        'metric': 'multi_logloss',
        'num_leaves': 127,
        'learning_rate': 0.05,
        'n_estimators': 1000,
        'min_child_samples': 5,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'reg_alpha': 0.1,
        'reg_lambda': 1.0,
        'verbose': -1,
        'random_state': seed,
        'n_jobs': -1,
    }

    model = lgb.LGBMClassifier(**params)
    model.fit(
        X_tr, y_tr,
        sample_weight=sample_weight,
        eval_set=[(X_val, y_val)],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=100),
        ],
    )
    print(f'LightGBM best iteration: {model.best_iteration_}')
    return model


# ─── FT-Transformer inference ─────────────────────────────────────────────────

def ftt_probs(X: np.ndarray, ckpt_path: Path, device: str = 'cpu') -> np.ndarray:
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    model = FTTransformer(num_features=X.shape[1], num_classes=N_CLASSES)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    probs = []
    with torch.no_grad():
        for i in range(0, len(X), 2048):
            logits = model(torch.tensor(X[i:i+2048]))
            probs.append(torch.softmax(logits, dim=1).numpy())
    return np.concatenate(probs)


# ─── Ensemble sweep ───────────────────────────────────────────────────────────

def ensemble_eval(p_lgbm, p_ftt, y_true, alphas=None):
    """Sweep alpha in lgbm*alpha + ftt*(1-alpha); return best alpha + macro-F1."""
    if alphas is None:
        alphas = np.arange(0.0, 1.05, 0.05)
    best_alpha, best_f1 = 0.5, -1.0
    for alpha in alphas:
        p_mix = alpha * p_lgbm + (1 - alpha) * p_ftt
        preds = np.argmax(p_mix, axis=1)
        f1 = f1_score(y_true, preds, average='macro')
        if f1 > best_f1:
            best_f1, best_alpha = f1, alpha
    return best_alpha, best_f1


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    SEED = 42
    V9_CKPT = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v9_u2r_val_fix_seed42/models/best_model.pt'
    OUT_DIR = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v11_lgbm_ensemble_seed42'
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print('=== P4: LightGBM + FT-Transformer Ensemble ===\n')

    print('[1/5] Loading data...')
    X_tr, y_tr, X_val, y_val, X_test, y_test = load_and_split(SEED)
    print(f'  Train={len(y_tr)}  Val={len(y_val)}  Test={len(y_test)}')
    for c in range(N_CLASSES):
        print(f'    {CLASS_NAMES[c]}: train={( y_tr==c).sum()}  val={(y_val==c).sum()}')

    print('\n[2/5] Training LightGBM...')
    lgbm = train_lgbm(X_tr, y_tr, X_val, y_val, SEED)

    print('\n[3/5] LightGBM standalone evaluation...')
    lgbm_val_probs  = lgbm.predict_proba(X_val)
    lgbm_test_probs = lgbm.predict_proba(X_test)
    lgbm_val_f1  = f1_score(y_val,  np.argmax(lgbm_val_probs, 1),  average='macro')
    lgbm_test_f1 = f1_score(y_test, np.argmax(lgbm_test_probs, 1), average='macro')
    print(f'  LightGBM  val  macro-F1 = {lgbm_val_f1:.4f}')
    print(f'  LightGBM  test macro-F1 = {lgbm_test_f1:.4f}')
    print(classification_report(y_test, np.argmax(lgbm_test_probs, 1), target_names=CLASS_NAMES, digits=4))

    print('[4/5] FT-Transformer (v9) probabilities...')
    ftt_val_probs  = ftt_probs(X_val,  V9_CKPT)
    ftt_test_probs = ftt_probs(X_test, V9_CKPT)
    ftt_val_f1  = f1_score(y_val,  np.argmax(ftt_val_probs,  1), average='macro')
    ftt_test_f1 = f1_score(y_test, np.argmax(ftt_test_probs, 1), average='macro')
    print(f'  FTT (v9)  val  macro-F1 = {ftt_val_f1:.4f}')
    print(f'  FTT (v9)  test macro-F1 = {ftt_test_f1:.4f}')

    print('\n[5/5] Ensemble alpha sweep on val...')
    best_alpha, best_val_f1 = ensemble_eval(lgbm_val_probs, ftt_val_probs, y_val)
    print(f'  Best alpha (LightGBM weight) = {best_alpha:.2f}  val macro-F1 = {best_val_f1:.4f}')

    # Final test evaluation at best alpha
    p_test = best_alpha * lgbm_test_probs + (1 - best_alpha) * ftt_test_probs
    y_pred_ensemble = np.argmax(p_test, axis=1)
    ens_test_f1 = f1_score(y_test, y_pred_ensemble, average='macro')
    print(f'\n  Ensemble test macro-F1 = {ens_test_f1:.4f}  (alpha={best_alpha:.2f})')
    print(classification_report(y_test, y_pred_ensemble, target_names=CLASS_NAMES, digits=4))

    # Save results
    result = {
        'lgbm_standalone_test_macro_f1': float(lgbm_test_f1),
        'ftt_v9_test_macro_f1': float(ftt_test_f1),
        'best_ensemble_alpha': float(best_alpha),
        'ensemble_val_macro_f1': float(best_val_f1),
        'ensemble_test_macro_f1': float(ens_test_f1),
    }
    (OUT_DIR / 'ensemble_summary.json').write_text(json.dumps(result, indent=2))

    report_txt = classification_report(y_test, y_pred_ensemble, target_names=CLASS_NAMES, digits=4)
    (OUT_DIR / 'classification_report.txt').write_text(report_txt)

    lgbm.booster_.save_model(str(OUT_DIR / 'lgbm_model.txt'))

    print(f'\nResults saved to {OUT_DIR}')
    print('\n=== SUMMARY ===')
    print(f'  LightGBM alone : test macro-F1 = {lgbm_test_f1:.4f}')
    print(f'  FTT v9 alone   : test macro-F1 = {ftt_test_f1:.4f}')
    print(f'  Ensemble       : test macro-F1 = {ens_test_f1:.4f}  (alpha={best_alpha:.2f})')


if __name__ == '__main__':
    main()
