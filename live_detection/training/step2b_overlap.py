"""
BƯỚC 2 (xác nhận) — Confidence của DoS/Web Attack có TÁCH được benign-FP khỏi tấn-công-thật?

Nếu confidence(benign nhầm thành DoS) >= confidence(DoS thật) thì KHÔNG ngưỡng nào lọc được
-> Bước 2 (calibrate + threshold) không cứu được, phải sang Bước 4 (tiền xử lý/retrain).
Đo trên confidence ĐÃ calibrate (chia logits cho T*).

Chạy:  python training/step2b_overlap.py     (từ live_detection/)
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import joblib, numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score

torch.set_num_threads(4)
HERE = Path(__file__).resolve().parent.parent
ANALYSIS = HERE / "data" / "analysis"
OUT = HERE / "training" / "step2_out"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "model_defs"))
from ids_replay.features import FeatureExtractor, EXPECTED_FEATURES_80 as FEATS
from hybrid_feature_scaler import HybridFeatureScaler
from phase2_ft_transformer_v2 import FTTransformer

T = json.loads((HERE/"models"/"v8_5_calibration.json").read_text())["temperature"]
enc = joblib.load(HERE/"models/v8_5_encoder.pkl"); CLASSES = list(enc.classes_)
scaler = HybridFeatureScaler.load(str(HERE/"models/v8_5_scaler.pkl"))
model = FTTransformer(num_features=80, num_classes=len(CLASSES), d_model=128, num_heads=8,
                      num_layers=4, d_ff=512, dropout=0.15, drop_path_rate=0.15)
model.load_state_dict(torch.load(HERE/"models/v8_5_model.pt", map_location="cpu", weights_only=False))
model.eval(); fe = FeatureExtractor()

def probs_of(csv):
    X = fe.build(pd.read_csv(ANALYSIS/csv, low_memory=False)); Xs = scaler.transform(X); out=[]
    with torch.no_grad():
        for i in range(0, len(Xs), 4096):
            out.append(torch.softmax(model(torch.FloatTensor(Xs[i:i+4096]))/T, dim=1).numpy())
    return np.concatenate(out)

pb = probs_of("benign_real.csv")
attacks = {"DoS": probs_of("dos_real.csv"), "Web Attack": probs_of("web_attack_real.csv")}

print(f"[*] Confidence ĐÃ calibrate (T={T:.3f}).  So sánh benign-nhầm-c vs c-thật (đều dự đoán = c)\n")
for cls, pa in attacks.items():
    ci = CLASSES.index(cls)
    # benign bị dự đoán thành c
    bmask = pb.argmax(1) == ci; bconf = pb[bmask, ci]
    # tấn công c thật, được dự đoán đúng c
    amask = pa.argmax(1) == ci; aconf = pa[amask, ci]
    print(f"=== {cls} ===")
    print(f"  benign nhầm->{cls}: {bmask.sum():>6,} flow | conf median={np.median(bconf):.3f} mean={bconf.mean():.3f}")
    print(f"  {cls} thật->{cls} : {amask.sum():>6,} flow | conf median={np.median(aconf):.3f} mean={aconf.mean():.3f}")
    if bmask.sum() and amask.sum():
        y = np.r_[np.zeros(bmask.sum()), np.ones(amask.sum())]
        s = np.r_[bconf, aconf]
        auc = roc_auc_score(y, s)
        print(f"  AUROC(conf tách benign-FP vs {cls}-thật) = {auc:.3f}  "
              f"({'TÁCH ĐƯỢC' if auc>0.7 else 'KHÔNG tách được -> cần Bước 4' if auc<0.6 else 'yếu'})")
        # ngưỡng nào cũng phải: chặn benign (conf<t) nhưng giữ tấn công (conf>=t)
        for t in [0.5, 0.7, 0.85, 0.9]:
            print(f"    thr={t}: benign-FP còn lại {np.mean(bconf>=t)*100:5.1f}% | {cls}-thật giữ {np.mean(aconf>=t)*100:5.1f}%")
    print()
