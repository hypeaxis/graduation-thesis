"""
BƯỚC 1 (bổ sung) — Ablation nhắm đúng nhóm feature SHAP + reset theo NHÓM.

Lý do: ablation trong step1_diagnose.py lấy nghi phạm chủ yếu từ KS/z-score nên bỏ sót
'Port_Is_Web' — feature SHAP xếp #1 đẩy FP sang tấn công (nghi leakage/spurious, cơ chế #4).
Script này ép các feature SHAP-top (và vài NHÓM) về median(lab) rồi đo % FP quay lại Benign.

Chạy:  python training/step1_ablation_extra.py     (từ live_detection/)
"""
from __future__ import annotations
import sys
from pathlib import Path
import joblib, numpy as np, pandas as pd, torch

torch.set_num_threads(4)          # tránh oversubscribe thread -> thrash chậm trên CPU
FP_SAMPLE = 4000                  # lấy mẫu FP đại diện cho ablation (đủ ổn định %)
rng = np.random.default_rng(42)

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "training" / "step1_out"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "model_defs"))
from ids_replay.features import FeatureExtractor, EXPECTED_FEATURES_80 as FEATS
from hybrid_feature_scaler import HybridFeatureScaler
from phase2_ft_transformer_v2 import FTTransformer

# --- data ---
X_lab = pd.read_csv(HERE / "data/analysis/benign_lab.csv")[FEATS].values.astype(np.float32)
X_lab = np.nan_to_num(X_lab)
X_real = FeatureExtractor().build(pd.read_csv(HERE / "data/analysis/benign_real.csv", low_memory=False))
lab_med = np.median(X_lab, axis=0)

# --- model ---
enc = joblib.load(HERE / "models/v8_5_encoder.pkl")
scaler = HybridFeatureScaler.load(str(HERE / "models/v8_5_scaler.pkl"))
model = FTTransformer(num_features=80, num_classes=len(enc.classes_), d_model=128,
                      num_heads=8, num_layers=4, d_ff=512, dropout=0.15, drop_path_rate=0.15)
model.load_state_dict(torch.load(HERE / "models/v8_5_model.pt", map_location="cpu", weights_only=False))
model.eval()

def predict(X):
    Xs = scaler.transform(X); out = []
    with torch.no_grad():
        for i in range(0, len(Xs), 4096):
            out.append(model(torch.FloatTensor(Xs[i:i+4096])).argmax(1).numpy())
    return enc.inverse_transform(np.concatenate(out))

base = predict(X_real)
is_fp = base != "Benign"
fp_idx = np.where(is_fp)[0]
print(f"[*] real-benign {len(base):,} | FP {len(fp_idx):,} ({is_fp.mean()*100:.2f}%)")
print(f"    FP theo lớp: {pd.Series(base[is_fp]).value_counts().to_dict()}")
if len(fp_idx) > FP_SAMPLE:                       # lấy mẫu để ablation chạy nhanh
    fp_idx = rng.choice(fp_idx, size=FP_SAMPLE, replace=False)
Xfp = X_real[fp_idx].copy()
print(f"[*] Ablation trên mẫu {len(Xfp):,} flow FP")

def recover(cols):
    """ép các cột `cols` về median(lab) trên tập FP -> % quay lại Benign."""
    Xm = Xfp.copy()
    for c in cols:
        Xm[:, FEATS.index(c)] = lab_med[FEATS.index(c)]
    return float((predict(Xm) == "Benign").mean()) * 100

PORT = ['Port_Is_Web', 'Port_Is_RemoteAccess', 'Port_Is_WellKnown', 'Port_Is_Registered', 'Port_Is_Ephemeral']
SHAP_TOP = ['Port_Is_Web', 'min_seg_size_forward', 'Fwd_Packet_Length_Max',
            'Avg_Bwd_Segment_Size', 'RST_Flag_Count', 'Total_Length_of_Fwd_Packets']

rows = []
# đơn lẻ — các feature SHAP-top (đặc biệt Port_Is_Web)
for c in SHAP_TOP + ['Down_Up_Ratio']:
    rows.append({"target": c, "type": "single", "fp_recovered_pct": round(recover([c]), 2)})
# nhóm
rows.append({"target": "ALL Port_Is_* (5)", "type": "group", "fp_recovered_pct": round(recover(PORT), 2)})
rows.append({"target": "SHAP-top6", "type": "group", "fp_recovered_pct": round(recover(SHAP_TOP), 2)})
rows.append({"target": "SHAP-top6 + Down_Up_Ratio", "type": "group",
             "fp_recovered_pct": round(recover(SHAP_TOP + ['Down_Up_Ratio']), 2)})

df = pd.DataFrame(rows).sort_values("fp_recovered_pct", ascending=False)
df.to_csv(OUT / "step1_ablation_extra.csv", index=False)
print("\n[*] Ablation bổ sung (ép -> median lab, % FP quay lại Benign):")
print(df.to_string(index=False))
print(f"\n[+] {OUT/'step1_ablation_extra.csv'}")
