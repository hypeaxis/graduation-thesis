"""
BƯỚC 4 (đánh giá) — Đo FPR benign thật + TPR tấn công với model v8_6 (robust-log) so V8.5.

Mục tiêu: kiểm chứng negative result — tiền xử lý robust-log KHÔNG hạ được FP DoS.
So sánh trực tiếp v8_5 (PowerTransformer) vs v8_6 (RobustLogScaler) trên CÙNG dữ liệu thật.

Chạy:  python training/step4_eval.py     (từ live_detection/)
"""
from __future__ import annotations
import sys
from pathlib import Path
import joblib, numpy as np, pandas as pd, torch

torch.set_num_threads(4)
HERE = Path(__file__).resolve().parent.parent
ANALYSIS = HERE / "data" / "analysis"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "model_defs"))
from ids_replay.features import FeatureExtractor, EXPECTED_FEATURES_80 as FEATS
from hybrid_feature_scaler import HybridFeatureScaler
from robust_log_scaler import RobustLogScaler
from phase2_ft_transformer_v2 import FTTransformer

ATTACK_FILES = {"PortScan": "portscan_real.csv", "DoS": "dos_real.csv",
                "Brute Force": "brute_force_real.csv", "Web Attack": "web_attack_real.csv"}
fe = FeatureExtractor()

def load_model(model_pt, enc_pkl):
    enc = joblib.load(enc_pkl)
    m = FTTransformer(num_features=80, num_classes=len(enc.classes_), d_model=128, num_heads=8,
                      num_layers=4, d_ff=512, dropout=0.15, drop_path_rate=0.15)
    m.load_state_dict(torch.load(model_pt, map_location="cpu", weights_only=False)); m.eval()
    return m, enc

def predict(m, scaler, enc, X):
    Xs = scaler.transform(X); out=[]
    with torch.no_grad():
        for i in range(0, len(Xs), 4096):
            out.append(m(torch.FloatTensor(Xs[i:i+4096])).argmax(1).numpy())
    return enc.inverse_transform(np.concatenate(out))

def evaluate(tag, m, scaler, enc, feats_cache):
    Xb = feats_cache["benign_real"]
    pb = predict(m, scaler, enc, Xb)
    fpr = float((pb != "Benign").mean())
    dos_fp = float((pb == "DoS").mean())
    wa_fp = float((pb == "Web Attack").mean())
    rec = {}
    for cls, f in ATTACK_FILES.items():
        d = predict(m, scaler, enc, feats_cache[cls])
        rec[cls] = float((d == cls).mean())          # recall lớp đúng
    print(f"\n### {tag}")
    print(f"  FPR benign = {fpr*100:5.2f}%  (DoS-FP {dos_fp*100:.2f}% | WebAttack-FP {wa_fp*100:.2f}%)")
    print("  TPR: " + "  ".join(f"{c}={rec[c]*100:.1f}%" for c in ATTACK_FILES))
    return {"fpr": fpr*100, "dos_fp": dos_fp*100, "wa_fp": wa_fp*100,
            "tpr": {c: rec[c]*100 for c in ATTACK_FILES}}

def main():
    print("[*] Trích feature (dùng chung cho cả 2 model)...")
    cache = {"benign_real": fe.build(pd.read_csv(ANALYSIS/"benign_real.csv", low_memory=False))}
    for cls, f in ATTACK_FILES.items():
        cache[cls] = fe.build(pd.read_csv(ANALYSIS/f, low_memory=False))

    # V8.5 (PowerTransformer hybrid)
    m5, e5 = load_model(HERE/"models/v8_5_model.pt", HERE/"models/v8_5_encoder.pkl")
    s5 = HybridFeatureScaler.load(str(HERE/"models/v8_5_scaler.pkl"))
    r5 = evaluate("V8.5 (PowerTransformer) — baseline", m5, s5, e5, cache)

    # V8.6 (RobustLogScaler)
    m6, e6 = load_model(HERE/"models/v8_6_model.pt", HERE/"models/v8_6_encoder.pkl")
    s6 = RobustLogScaler.load(str(HERE/"models/v8_6_robust_scaler.pkl"))
    r6 = evaluate("V8.6 (RobustLog: log+robust+clip) — Bước 4", m6, s6, e6, cache)

    print("\n" + "="*60)
    print("KẾT LUẬN Bước 4 (negative control):")
    print(f"  FPR:    V8.5 {r5['fpr']:.2f}%  ->  V8.6 {r6['fpr']:.2f}%   (Δ {r6['fpr']-r5['fpr']:+.2f}pp)")
    print(f"  DoS-FP: V8.5 {r5['dos_fp']:.2f}%  ->  V8.6 {r6['dos_fp']:.2f}%   (Δ {r6['dos_fp']-r5['dos_fp']:+.2f}pp)")
    verdict = "XÁC NHẬN negative: robust-log KHÔNG hạ FP DoS" if abs(r6['dos_fp']-r5['dos_fp']) < 5 \
              else "BẤT NGỜ: robust-log CÓ đổi FP DoS đáng kể -> xem lại"
    print(f"  -> {verdict}")

if __name__ == "__main__":
    main()
