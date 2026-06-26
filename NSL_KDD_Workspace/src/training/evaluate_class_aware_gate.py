"""v13: Class-aware AE gate evaluation.

Plan v3, Step 3:
  Hard gate (current): if ae_mse < 0.008481 → force Normal, never reaches FTT
  Class-aware gate:    if ae_mse < threshold AND FTT max(p_R2L, p_U2R) < gate_conf → Normal
                       else → bypass gate, meta-LR decides

Compares 3 scenarios on KDDTest+:
  A. Hard gate  + FTT v9 (production baseline)
  B. Hard gate  + Meta-LR v12 (meta on top of hard gate)
  C. Class-aware gate + Meta-LR v12 (proposed fix)
"""

import json
import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score

WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE / 'src' / 'models'))
from phase2_ft_transformer import FTTransformer  # noqa: E402

CLASS_NAMES     = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
N_CLASSES       = 5
GATE_THRESHOLD  = 0.008481   # AE MSE threshold (fixed, never tune on test)
R2L_IDX, U2R_IDX = 3, 4

V9_CKPT   = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v9_u2r_val_fix_seed42/models/best_model.pt'
V11_MODEL = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v11_lgbm_ensemble_seed42/lgbm_model.txt'
OUT_DIR   = WORKSPACE / 'models/outputs/nslkdd_ft_experiments/v13_class_aware_gate_seed42'


# ─── Data ─────────────────────────────────────────────────────────────────────

def load_and_split(seed: int = 42):
    """Load v2 features + v4 ae_recon_error, apply same boost-minority split."""
    df_v2_train = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v2_KddTrain+.csv')
    df_v2_test  = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v2_KddTest+.csv')
    df_v4_train = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v4_KddTrain+.csv')
    df_v4_test  = pd.read_csv(WORKSPACE / 'data/processed/cleaned5Grouped_v4_KddTest+.csv')

    X_full = df_v2_train.drop(columns=['label']).values.astype(np.float32)
    y_full = df_v2_train['label'].values.astype(np.int64)
    ae_full = df_v4_train['ae_recon_error'].values.astype(np.float32)

    X_test   = df_v2_test.drop(columns=['label']).values.astype(np.float32)
    y_test   = df_v2_test['label'].values.astype(np.int64)
    ae_test  = df_v4_test['ae_recon_error'].values.astype(np.float32)

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

    X_val  = X_full[val_idx];   y_val  = y_full[val_idx];  ae_val  = ae_full[val_idx]
    return X_val, y_val, ae_val, X_test, y_test, ae_test


# ─── Inference ────────────────────────────────────────────────────────────────

def lgbm_probs(X: np.ndarray) -> np.ndarray:
    booster = lgb.Booster(model_file=str(V11_MODEL))
    return booster.predict(X).astype(np.float32)


def ftt_probs(X: np.ndarray) -> np.ndarray:
    ckpt  = torch.load(V9_CKPT, map_location='cpu', weights_only=False)
    model = FTTransformer(num_features=X.shape[1], num_classes=N_CLASSES)
    model.load_state_dict(ckpt['model_state_dict'])
    model.eval()
    parts = []
    with torch.no_grad():
        for i in range(0, len(X), 2048):
            logits = model(torch.tensor(X[i:i+2048]))
            parts.append(torch.softmax(logits, dim=1).numpy())
    return np.concatenate(parts)


# ─── Gate strategies ──────────────────────────────────────────────────────────

def apply_hard_gate(p_ftt: np.ndarray, ae_mse: np.ndarray) -> np.ndarray:
    """Scenario A: if MSE < threshold → Normal, else argmax(ftt_probs)."""
    preds = np.argmax(p_ftt, axis=1).copy()
    gated = ae_mse < GATE_THRESHOLD
    preds[gated] = 0  # force Normal
    return preds


def apply_hard_gate_meta(p_meta: np.ndarray, ae_mse: np.ndarray) -> np.ndarray:
    """Scenario B: if MSE < threshold → Normal, else meta-LR prediction."""
    preds = np.argmax(p_meta, axis=1).copy()
    gated = ae_mse < GATE_THRESHOLD
    preds[gated] = 0
    return preds


def apply_class_aware_gate(p_meta: np.ndarray, p_ftt: np.ndarray,
                            ae_mse: np.ndarray, gate_conf: float) -> np.ndarray:
    """Scenario C: bypass gate for samples where FTT suspects R2L/U2R."""
    preds       = np.argmax(p_meta, axis=1).copy()
    ae_low      = ae_mse < GATE_THRESHOLD                             # gate would fire
    r2l_u2r_conf = np.maximum(p_ftt[:, R2L_IDX], p_ftt[:, U2R_IDX]) # FTT suspicion score
    gate_applies = ae_low & (r2l_u2r_conf < gate_conf)               # gate AND not suspicious
    preds[gate_applies] = 0                                           # force Normal only when safe
    return preds


def tune_gate_conf(p_meta_val, p_ftt_val, ae_val, y_val) -> float:
    """Grid-search gate_conf on val to maximize macro-F1."""
    best_conf, best_f1 = 0.0, -1.0
    for conf in np.arange(0.0, 0.55, 0.05):
        preds = apply_class_aware_gate(p_meta_val, p_ftt_val, ae_val, conf)
        f1 = f1_score(y_val, preds, average='macro', zero_division=0)
        if f1 > best_f1:
            best_f1, best_conf = f1, conf
    return float(best_conf)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print('=== v13: Class-aware AE Gate Evaluation ===\n')

    print('[1/5] Loading data + AE reconstruction errors...')
    X_val, y_val, ae_val, X_test, y_test, ae_test = load_and_split(seed=42)
    print(f'  Val={len(y_val)}  Test={len(y_test)}')
    gate_rate_val  = (ae_val  < GATE_THRESHOLD).mean()
    gate_rate_test = (ae_test < GATE_THRESHOLD).mean()
    print(f'  Gate fires (MSE < {GATE_THRESHOLD}): val={gate_rate_val:.3f}  test={gate_rate_test:.3f}')
    for c in range(N_CLASSES):
        mask = y_test == c
        if mask.sum() > 0:
            blocked = (ae_test[mask] < GATE_THRESHOLD).mean()
            print(f'    {CLASS_NAMES[c]}: {mask.sum()} test samples, {blocked*100:.1f}% blocked by hard gate')

    print('\n[2/5] Computing model probabilities...')
    p_lgbm_val  = lgbm_probs(X_val);   p_lgbm_test  = lgbm_probs(X_test)
    p_ftt_val   = ftt_probs(X_val);    p_ftt_test   = ftt_probs(X_test)

    print('\n[3/5] Fitting meta-LR on val (same as v12)...')
    X_meta_val  = np.hstack([p_lgbm_val,  p_ftt_val])
    X_meta_test = np.hstack([p_lgbm_test, p_ftt_test])
    meta = LogisticRegression(solver='lbfgs', C=1.0, max_iter=2000,
                               class_weight='balanced', random_state=42)
    meta.fit(X_meta_val, y_val)
    p_meta_val  = meta.predict_proba(X_meta_val)
    p_meta_test = meta.predict_proba(X_meta_test)

    print('\n[4/5] Tuning gate_conf on val (not test)...')
    best_gate_conf = tune_gate_conf(p_meta_val, p_ftt_val, ae_val, y_val)
    print(f'  Best gate_conf (val) = {best_gate_conf:.2f}')

    print('\n[5/5] Evaluating three scenarios on TEST...')

    # Scenario A: Hard gate + FTT v9
    preds_A = apply_hard_gate(p_ftt_test, ae_test)
    f1_A    = f1_score(y_test, preds_A, average='macro')

    # Scenario B: Hard gate + Meta-LR
    preds_B = apply_hard_gate_meta(p_meta_test, ae_test)
    f1_B    = f1_score(y_test, preds_B, average='macro')

    # Scenario C: Class-aware gate + Meta-LR (best conf from val)
    preds_C = apply_class_aware_gate(p_meta_test, p_ftt_test, ae_test, best_gate_conf)
    f1_C    = f1_score(y_test, preds_C, average='macro')

    # Baseline: no gate at all (meta-LR v12)
    preds_base = np.argmax(p_meta_test, axis=1)
    f1_base    = f1_score(y_test, preds_base, average='macro')

    print(f'\n  [Baseline] Meta-LR v12 (no gate)              : {f1_base:.4f}')
    print(f'  [A] Hard gate  + FTT v9  (production current)  : {f1_A:.4f}')
    print(f'  [B] Hard gate  + Meta-LR (v12 + gate)          : {f1_B:.4f}')
    print(f'  [C] Class-aware gate + Meta-LR (gate_conf={best_gate_conf:.2f}): {f1_C:.4f}')

    print('\n--- Classification report [C] ---')
    print(classification_report(y_test, preds_C, target_names=CLASS_NAMES, digits=4))

    # Gate bypass stats for C
    ae_low = ae_test < GATE_THRESHOLD
    r2l_u2r_conf = np.maximum(p_ftt_test[:, R2L_IDX], p_ftt_test[:, U2R_IDX])
    bypassed = ae_low & (r2l_u2r_conf >= best_gate_conf)
    hard_gated = ae_low & (r2l_u2r_conf < best_gate_conf)
    print(f'Gate stats on test:')
    print(f'  MSE < threshold total       : {ae_low.sum()} ({ae_low.mean()*100:.1f}%)')
    print(f'  → Hard-gated to Normal      : {hard_gated.sum()} ({hard_gated.mean()*100:.1f}%)')
    print(f'  → Bypassed (FTT suspicious) : {bypassed.sum()} ({bypassed.mean()*100:.1f}%)')

    # Per-class gate bypass breakdown
    for c in [R2L_IDX, U2R_IDX]:
        mask = y_test == c
        rescued = bypassed[mask].sum()
        total_blocked = ae_low[mask].sum()
        print(f'  {CLASS_NAMES[c]}: {total_blocked} blocked, {rescued} rescued by class-aware gate')

    results = {
        'no_gate_meta_lr_v12':           float(f1_base),
        'A_hard_gate_ftt_v9':            float(f1_A),
        'B_hard_gate_meta_lr':           float(f1_B),
        'C_class_aware_gate_meta_lr':    float(f1_C),
        'gate_conf_tuned_on_val':        float(best_gate_conf),
    }
    (OUT_DIR / 'results.json').write_text(json.dumps(results, indent=2))
    (OUT_DIR / 'report_C.txt').write_text(
        classification_report(y_test, preds_C, target_names=CLASS_NAMES, digits=4)
    )

    print(f'\nResults saved → {OUT_DIR}')
    print('\n=== SUMMARY ===')
    print(f'  Meta-LR v12 (no gate)       : {f1_base:.4f}  ← reference')
    print(f'  A. Hard gate + FTT          : {f1_A:.4f}')
    print(f'  B. Hard gate + Meta-LR      : {f1_B:.4f}')
    print(f'  C. Class-aware + Meta-LR    : {f1_C:.4f}  ({f1_C-f1_base:+.4f} vs no-gate)')


if __name__ == '__main__':
    main()
