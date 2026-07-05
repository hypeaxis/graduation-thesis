"""
BƯỚC 5 (đánh giá) — v8_7 (fine-tune + benign thật) vs V8.5, đo trên dữ liệu THẬT.

QUAN TRỌNG: FPR đo trên **b5_benign_test** (11,701 flow benign thật GIỮ RIÊNG, KHÔNG dùng
lúc train/tune) -> ước lượng trung thực. KHÔNG đo trên benign_real (đã có 40k vào train v8_7).

Chạy:  python training/step5_eval.py     (từ live_detection/)
"""
from __future__ import annotations
import sys
from pathlib import Path
import joblib, numpy as np, pandas as pd, torch

torch.set_num_threads(4)
HERE = Path(__file__).resolve().parent.parent
ANALYSIS = HERE / "data" / "analysis"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "model_defs"))
from ids_replay.features import FeatureExtractor
from hybrid_feature_scaler import HybridFeatureScaler
from phase2_ft_transformer_v2 import FTTransformer

ATTACK_FILES = {"PortScan": "portscan_real.csv", "DoS": "dos_real.csv",
                "Brute Force": "brute_force_real.csv", "Web Attack": "web_attack_real.csv"}
fe = FeatureExtractor()

def load(model_pt, scaler_pkl, enc_pkl):
    enc = joblib.load(enc_pkl)
    sc = HybridFeatureScaler.load(str(scaler_pkl))
    m = FTTransformer(num_features=80, num_classes=len(enc.classes_), d_model=128, num_heads=8,
                      num_layers=4, d_ff=512, dropout=0.15, drop_path_rate=0.15)
    m.load_state_dict(torch.load(model_pt, map_location="cpu", weights_only=False)); m.eval()
    return m, sc, enc

def predict(m, sc, enc, X):
    Xs = sc.transform(X); out=[]
    with torch.no_grad():
        for i in range(0, len(Xs), 4096):
            out.append(m(torch.FloatTensor(Xs[i:i+4096])).argmax(1).numpy())
    return enc.inverse_transform(np.concatenate(out))

def evaluate(tag, m, sc, enc, cache):
    pb = predict(m, sc, enc, cache["test"])
    fpr = float((pb != "Benign").mean())
    dos_fp = float((pb == "DoS").mean()); wa_fp = float((pb == "Web Attack").mean())
    rec = {c: float((predict(m, sc, enc, cache[c]) == c).mean()) for c in ATTACK_FILES}
    print(f"\n### {tag}")
    print(f"  FPR (b5_benign_test giữ riêng) = {fpr*100:5.2f}%  (DoS-FP {dos_fp*100:.2f}% | WA-FP {wa_fp*100:.2f}%)")
    print("  TPR: " + "  ".join(f"{c}={rec[c]*100:.1f}%" for c in ATTACK_FILES))
    return {"fpr": fpr*100, "dos_fp": dos_fp*100, "wa_fp": wa_fp*100, "tpr": {c: rec[c]*100 for c in ATTACK_FILES}}

def main():
    print("[*] Trích feature (test benign thật giữ riêng + 4 lớp tấn công)...")
    cache = {"test": fe.build(pd.read_csv(ANALYSIS/"b5_benign_test.csv", low_memory=False))}
    for c, f in ATTACK_FILES.items():
        cache[c] = fe.build(pd.read_csv(ANALYSIS/f, low_memory=False))

    r5 = evaluate("V8.5 (CIC-only) — baseline", *load(HERE/"models/v8_5_model.pt",
                  HERE/"models/v8_5_scaler.pkl", HERE/"models/v8_5_encoder.pkl"), cache)
    r7 = evaluate("V8.7 (fine-tune + benign thật) — Bước 5", *load(HERE/"models/v8_7_model.pt",
                  HERE/"models/v8_7_scaler.pkl", HERE/"models/v8_7_encoder.pkl"), cache)

    print("\n" + "="*62)
    print("KẾT LUẬN Bước 5 (FPR trên benign thật GIỮ RIÊNG):")
    print(f"  FPR:    V8.5 {r5['fpr']:.2f}%  ->  V8.7 {r7['fpr']:.2f}%   (Δ {r7['fpr']-r5['fpr']:+.2f}pp)")
    print(f"  DoS-FP: V8.5 {r5['dos_fp']:.2f}%  ->  V8.7 {r7['dos_fp']:.2f}%   (Δ {r7['dos_fp']-r5['dos_fp']:+.2f}pp)")
    print(f"  TPR tấn công (v8.5 -> v8.7):")
    for c in ATTACK_FILES:
        print(f"    {c:<12}: {r5['tpr'][c]:5.1f}% -> {r7['tpr'][c]:5.1f}%  (Δ {r7['tpr'][c]-r5['tpr'][c]:+.1f}pp)")

if __name__ == "__main__":
    main()
