"""
BƯỚC 4 (chẩn đoán go/no-go) — Trước khi retrain, kiểm 3 giả thuyết:

(A) CLIP-TEST: FP có phải do "nổ z-score" (ngoại suy ngoài vùng train) không?
    Clip feature ĐÃ scale về [-5,5] rồi predict lại các flow DoS-FP -> bao nhiêu về Benign?
    Nhiều -> 4.2 (robust scale + clip) sẽ ăn. Ít -> FP không do scale, cần Bước 5 (benign thật).

(B) SEPARABILITY: real-benign-nhầm-DoS vs DoS-thật có tách được trong FEATURE SPACE THÔ không?
    CV-AUROC của RandomForest. Cao -> thông tin CÓ trong feature (retrain/khác model cứu được).
    Thấp -> hai lớp chồng thật -> tiền xử lý trên CIC-only khó cứu.

(C) SHORT-FLOW: DoS-thật có siêu ngắn như benign-FP không? Nếu có -> lọc flow ngắn (4.3)
    sẽ GIẾT luôn recall DoS -> phải thận trọng.

Chạy:  python training/step4_diagnose.py     (từ live_detection/)
"""
from __future__ import annotations
import sys
from pathlib import Path
import joblib, numpy as np, pandas as pd, torch
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

torch.set_num_threads(4)
HERE = Path(__file__).resolve().parent.parent
ANALYSIS = HERE / "data" / "analysis"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "model_defs"))
from ids_replay.features import FeatureExtractor, EXPECTED_FEATURES_80 as FEATS
from hybrid_feature_scaler import HybridFeatureScaler
from phase2_ft_transformer_v2 import FTTransformer

enc = joblib.load(HERE/"models/v8_5_encoder.pkl"); CLASSES = list(enc.classes_)
scaler = HybridFeatureScaler.load(str(HERE/"models/v8_5_scaler.pkl"))
model = FTTransformer(num_features=80, num_classes=len(CLASSES), d_model=128, num_heads=8,
                      num_layers=4, d_ff=512, dropout=0.15, drop_path_rate=0.15)
model.load_state_dict(torch.load(HERE/"models/v8_5_model.pt", map_location="cpu", weights_only=False))
model.eval(); fe = FeatureExtractor()

def feats(csv):
    return fe.build(pd.read_csv(ANALYSIS/csv, low_memory=False))
def predict_from_scaled(Xs):
    out=[]
    with torch.no_grad():
        for i in range(0,len(Xs),4096):
            out.append(model(torch.FloatTensor(Xs[i:i+4096])).argmax(1).numpy())
    return enc.inverse_transform(np.concatenate(out))

Xb = feats("benign_real.csv"); Xd = feats("dos_real.csv")
pred_b = predict_from_scaled(scaler.transform(Xb))
pred_d = predict_from_scaled(scaler.transform(Xd))
b_isDoS = pred_b == "DoS"                          # benign bị nhầm thành DoS (FP)
d_isDoS = pred_d == "DoS"                          # DoS thật được nhận đúng (TP)
print(f"[*] benign_real {len(Xb):,}: DoS-FP = {b_isDoS.sum():,}")
print(f"[*] dos_real    {len(Xd):,}: DoS đúng = {d_isDoS.sum():,}\n")

# ---------- (A) CLIP-TEST ----------
print("="*70); print("(A) CLIP-TEST: clip feature đã scale về [-C,C] rồi predict lại DoS-FP")
Xb_fp = Xb[b_isDoS]
base = "DoS"
for C in [10, 5, 3]:
    Xs = np.clip(scaler.transform(Xb_fp), -C, C)
    rec = float((predict_from_scaled(Xs) == "Benign").mean())
    print(f"    clip[-{C},{C}]: {rec*100:5.1f}% DoS-FP -> Benign")
# cũng đo tác dụng phụ lên DoS-thật (clip có giết TP không?)
Xd_tp = Xd[d_isDoS]
for C in [5]:
    Xs = np.clip(scaler.transform(Xd_tp), -C, C)
    keep = float((predict_from_scaled(Xs) == "DoS").mean())
    print(f"    [tác dụng phụ] clip[-{C},{C}] trên DoS-thật: giữ {keep*100:.1f}% vẫn = DoS")

# ---------- (B) SEPARABILITY (raw feature space) ----------
print("\n"+"="*70); print("(B) SEPARABILITY: RF CV-AUROC tách benign-FP-DoS vs DoS-thật (feature THÔ)")
Xpos = Xd[d_isDoS]; Xneg = Xb[b_isDoS]
n = min(len(Xpos), len(Xneg), 8000)
rng = np.random.default_rng(42)
Xp = Xpos[rng.choice(len(Xpos), n, replace=False)]
Xn = Xneg[rng.choice(len(Xneg), n, replace=False)]
X = np.vstack([Xp, Xn]); y = np.r_[np.ones(n), np.zeros(n)]
rf = RandomForestClassifier(n_estimators=120, max_depth=12, n_jobs=4, random_state=42)
auc = cross_val_score(rf, X, y, cv=4, scoring="roc_auc", n_jobs=4)
print(f"    n={n}/lớp | CV-AUROC = {auc.mean():.3f} ± {auc.std():.3f}")
print(f"    -> {'TÁCH ĐƯỢC trong feature thô (retrain/tiền xử lý có cửa)' if auc.mean()>0.85 else 'CHỒNG NHAU (feature thô không tách -> cần benign thật/Bước 5)' if auc.mean()<0.7 else 'trung bình'}")
# feature quan trọng nhất để tách
rf.fit(X, y)
imp = pd.Series(rf.feature_importances_, index=FEATS).sort_values(ascending=False)
print("    Top feature tách benign-FP vs DoS-thật:")
for f, v in imp.head(8).items(): print(f"      {f:<28} {v:.3f}")

# ---------- (C) SHORT-FLOW overlap ----------
print("\n"+"="*70); print("(C) SHORT-FLOW: phân bố tổng số gói (Fwd+Bwd)")
def npkt(X): return X[:, FEATS.index("Total_Fwd_Packets")] + X[:, FEATS.index("Total_Backward_Packets")]
for name, Xarr, mask in [("benign-FP-DoS", Xb, b_isDoS), ("DoS-thật", Xd, d_isDoS)]:
    p = npkt(Xarr[mask])
    print(f"    {name:<14}: median={np.median(p):.0f} | ≤2 gói={np.mean(p<=2)*100:4.1f}% | ≤3 gói={np.mean(p<=3)*100:4.1f}%")
print("\n[i] Nếu DoS-thật cũng phần lớn ≤3 gói -> lọc flow ngắn (4.3) sẽ giết recall DoS.")
