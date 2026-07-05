"""
BƯỚC 2 — HIỆU CHỈNH QUYẾT ĐỊNH (calibrate). KHÔNG retrain.

Hai phần (theo playbook Mục 4·Bước 2):
  2.1 Temperature scaling: học 1 nhiệt độ T trên tập calib có nhãn (benign_val + holdout
      tấn công thật) → softmax(logits/T) cho confidence phản ánh đúng độ chắc (giảm ECE).
  2.2 Ngưỡng theo TỪNG LỚP: thay ngưỡng chung 0.6 bằng ngưỡng riêng mỗi lớp; nâng cho
      DoS/Web Attack (2 lớp đang FP). Đây MỚI là đòn bẩy giảm FP (T đơn điệu, không đổi argmax).

Lưu ý trung thực: T-scaling KHÔNG tự giảm FP (chia logit đơn điệu → giữ nguyên argmax và thứ
hạng confidence). Nó chỉ hiệu chỉnh thang đo (ECE). Việc giảm FP đến từ ngưỡng-theo-lớp; nếu
confidence của benign-nhầm-DoS và DoS-thật TRÙNG nhau thì Bước 2 không tách được → cần Bước 4.

Tách fit/eval: fit T + chọn ngưỡng trên CALIB (benign_val + 30% mỗi lớp tấn công), báo cáo
before/after trên EVAL (benign_real + 70% còn lại). benign_val đã giữ riêng từ Bước 0.

Chạy:  python training/step2_calibrate.py     (từ live_detection/)
Xuất:  training/step2_out/  (calibration.json, reliability png, metrics, summary)
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import joblib, numpy as np, pandas as pd, torch

torch.set_num_threads(4)
HERE = Path(__file__).resolve().parent.parent
ANALYSIS = HERE / "data" / "analysis"
OUT = HERE / "training" / "step2_out"; OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "model_defs"))
from ids_replay.features import FeatureExtractor, EXPECTED_FEATURES_80 as FEATS
from hybrid_feature_scaler import HybridFeatureScaler
from phase2_ft_transformer_v2 import FTTransformer

SEED = 42; rng = np.random.default_rng(SEED)
CALIB_FRAC = 0.30                      # % mỗi lớp tấn công dùng để calib (còn lại để eval)
TARGET_TPR = 0.95                      # giữ >=95% recall mỗi lớp tấn công khi chọn ngưỡng
GLOBAL_THR_BEFORE = 0.6                # ngưỡng chung hiện hành (baseline)
ATTACK_FILES = {                        # nhãn model  ->  file thật
    "PortScan": "portscan_real.csv", "DoS": "dos_real.csv",
    "Brute Force": "brute_force_real.csv", "Web Attack": "web_attack_real.csv",
}

def banner(m): print("\n" + "=" * 74 + f"\n{m}\n" + "=" * 74)

# ---- model ----
enc = joblib.load(HERE / "models/v8_5_encoder.pkl")
CLASSES = list(enc.classes_)                       # ['Benign','Brute Force','DoS','PortScan','Web Attack']
BENIGN_I = CLASSES.index("Benign")
scaler = HybridFeatureScaler.load(str(HERE / "models/v8_5_scaler.pkl"))
model = FTTransformer(num_features=80, num_classes=len(CLASSES), d_model=128, num_heads=8,
                      num_layers=4, d_ff=512, dropout=0.15, drop_path_rate=0.15)
model.load_state_dict(torch.load(HERE / "models/v8_5_model.pt", map_location="cpu", weights_only=False))
model.eval()
fe = FeatureExtractor()

def logits_of(csv):
    X = fe.build(pd.read_csv(ANALYSIS / csv, low_memory=False))
    Xs = scaler.transform(X); out = []
    with torch.no_grad():
        for i in range(0, len(Xs), 4096):
            out.append(model(torch.FloatTensor(Xs[i:i+4096])).numpy())
    return np.concatenate(out).astype(np.float64)

# ============================================================================
banner("1. Tính logits cho benign_val / benign_real / 4 lớp tấn công thật")
L = {"benign_val": logits_of("benign_val.csv"), "benign_real": logits_of("benign_real.csv")}
for cls, f in ATTACK_FILES.items():
    L[cls] = logits_of(f)
    print(f"    {cls:<12}: {len(L[cls]):>7,} flow")
print(f"    benign_val {len(L['benign_val']):,} | benign_real {len(L['benign_real']):,}")

# tách calib/eval cho mỗi lớp tấn công
calib_logits, calib_y, eval_atk = [], [], {}
for cls in ATTACK_FILES:
    n = len(L[cls]); idx = rng.permutation(n); k = int(n * CALIB_FRAC)
    ci, ei = idx[:k], idx[k:]
    calib_logits.append(L[cls][ci]); calib_y += [CLASSES.index(cls)] * k
    eval_atk[cls] = L[cls][ei]
# calib benign = benign_val (đã giữ riêng)
calib_logits.append(L["benign_val"]); calib_y += [BENIGN_I] * len(L["benign_val"])
Zc = np.concatenate(calib_logits); yc = np.array(calib_y)
print(f"    Calib set: {len(yc):,} flow ({(yc==BENIGN_I).sum():,} benign + tấn công holdout)")

# ============================================================================
banner("2.1 Fit temperature T (minimize NLL trên calib)")
def ece(probs, y, bins=15):
    conf = probs.max(1); pred = probs.argmax(1); acc = (pred == y).astype(float)
    e = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        m = (conf > lo) & (conf <= hi)
        if m.sum(): e += m.mean() * abs(acc[m].mean() - conf[m].mean())
    return e

def softmax_np(z):
    z = z - z.max(1, keepdims=True); e = np.exp(z); return e / e.sum(1, keepdims=True)

Zc_t = torch.tensor(Zc); yc_t = torch.tensor(yc)
logT = torch.zeros(1, requires_grad=True)          # T = exp(logT) > 0
opt = torch.optim.LBFGS([logT], lr=0.1, max_iter=60)
def closure():
    opt.zero_grad()
    loss = torch.nn.functional.cross_entropy(Zc_t / logT.exp(), yc_t)
    loss.backward(); return loss
opt.step(closure)
T = float(logT.exp().item())
ece_before = ece(softmax_np(Zc), yc); ece_after = ece(softmax_np(Zc / T), yc)
print(f"    T* = {T:.3f}   |  ECE calib: {ece_before:.4f} -> {ece_after:.4f}")

# ============================================================================
banner("2.2 Chọn ngưỡng theo từng lớp (giữ >=95% recall mỗi lớp tấn công)")
# ngưỡng[c] = phân vị (1-TARGET_TPR) của confidence(cal) các flow tấn công thật lớp c
#             ĐƯỢC model dự đoán đúng là c -> 95% flow c thật vượt ngưỡng (giữ recall).
thr = {}
for cls in ATTACK_FILES:
    ci = CLASSES.index(cls)
    n = len(L[cls]); idx = rng.permutation(n); k = int(n * CALIB_FRAC)   # cùng seed -> cùng calib
    p = softmax_np(L[cls][idx[:k]] / T)
    pred_c = p.argmax(1) == ci
    if pred_c.sum() < 20:
        thr[cls] = GLOBAL_THR_BEFORE
        print(f"    {cls:<12}: quá ít flow dự đoán đúng ({pred_c.sum()}) -> giữ {GLOBAL_THR_BEFORE}")
        continue
    conf_true = p[pred_c].max(1)
    t = float(np.quantile(conf_true, 1 - TARGET_TPR))
    thr[cls] = round(max(t, 0.0), 3)
    print(f"    {cls:<12}: ngưỡng={thr[cls]:.3f}  (từ {int(pred_c.sum())} flow c-thật, giữ {TARGET_TPR:.0%} recall)")
thr["Benign"] = 0.0                                # lớp benign không có ngưỡng (là fallback)

# ============================================================================
banner("3. Đánh giá BEFORE/AFTER trên EVAL (benign_real + 70% tấn công holdout)")
def decide(logits, T, thr_map, global_thr=None):
    """logits (n,5) -> nhãn cuối. Nếu global_thr đặt: dùng ngưỡng chung (baseline). Ngược lại per-class."""
    p = softmax_np(logits / T); pred = p.argmax(1); conf = p.max(1)
    out = []
    for i in range(len(pred)):
        c = CLASSES[pred[i]]
        t = global_thr if global_thr is not None else thr_map.get(c, 0.0)
        out.append("Benign" if (c != "Benign" and conf[i] < t) else c)
    return np.array(out)

def metrics(tag, T_use, thr_map, global_thr):
    # FPR trên benign_real
    b = decide(L["benign_real"], T_use, thr_map, global_thr)
    fpr = float((b != "Benign").mean())
    # recall phát hiện tấn công (pred != Benign) trên eval mỗi lớp
    rec = {}
    for cls in ATTACK_FILES:
        d = decide(eval_atk[cls], T_use, thr_map, global_thr)
        rec[cls] = float((d != "Benign").mean())
    macro_tpr = np.mean(list(rec.values()))
    print(f"  [{tag}] FPR benign={fpr*100:5.2f}%  |  TPR: " +
          "  ".join(f"{c[:4]}={rec[c]*100:4.1f}%" for c in ATTACK_FILES) +
          f"  | macroTPR={macro_tpr*100:.1f}%")
    return {"tag": tag, "fpr_benign_pct": round(fpr*100,2),
            "tpr": {c: round(rec[c]*100,2) for c in ATTACK_FILES},
            "macro_tpr_pct": round(macro_tpr*100,2)}

m_raw    = metrics("RAW argmax (T=1, no thr)", 1.0, thr, 0.0)
m_before = metrics(f"BEFORE (T=1, global {GLOBAL_THR_BEFORE})", 1.0, thr, GLOBAL_THR_BEFORE)
m_after  = metrics(f"AFTER  (T={T:.2f}, per-class)", T, thr, None)

# reliability diagram before/after trên eval (gộp benign_real + tấn công eval)
banner("4. Reliability diagram (eval) + lưu tham số")
Ze = [L["benign_real"]] + [eval_atk[c] for c in ATTACK_FILES]
ye = [BENIGN_I]*len(L["benign_real"]) + sum(([CLASSES.index(c)]*len(eval_atk[c]) for c in ATTACK_FILES), [])
Ze = np.concatenate(Ze); ye = np.array(ye)
ece_e_before = ece(softmax_np(Ze), ye); ece_e_after = ece(softmax_np(Ze / T), ye)
print(f"    ECE eval: {ece_e_before:.4f} -> {ece_e_after:.4f}")

import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
def rel_pts(probs, y, bins=15):
    conf = probs.max(1); pred = probs.argmax(1); acc = (pred == y).astype(float)
    xs, ys = [], []
    for b in range(bins):
        lo, hi = b/bins, (b+1)/bins; m = (conf > lo) & (conf <= hi)
        if m.sum(): xs.append(conf[m].mean()); ys.append(acc[m].mean())
    return xs, ys
fig, ax = plt.subplots(figsize=(6,6))
ax.plot([0,1],[0,1],"--",color="gray",label="hoàn hảo")
x0,y0 = rel_pts(softmax_np(Ze), ye); x1,y1 = rel_pts(softmax_np(Ze/T), ye)
ax.plot(x0,y0,"o-",color="#E45756",label=f"before (ECE {ece_e_before:.3f})")
ax.plot(x1,y1,"o-",color="#4C78A8",label=f"after T={T:.2f} (ECE {ece_e_after:.3f})")
ax.set_xlabel("confidence"); ax.set_ylabel("accuracy"); ax.legend(); ax.set_title("Bước 2 — Reliability")
fig.tight_layout(); fig.savefig(OUT/"step2_reliability.png", dpi=110); plt.close(fig)
print(f"[+] {OUT/'step2_reliability.png'}")

calib = {"temperature": round(T,4), "per_class_threshold": thr, "target_tpr": TARGET_TPR,
         "note": "softmax(logits/T); pred tấn công conf<thr[c] -> Benign. Fit trên benign_val+holdout."}
(HERE/"models"/"v8_5_calibration.json").write_text(json.dumps(calib, indent=2, ensure_ascii=False))
summary = {"temperature": T, "ece_calib": [ece_before, ece_after], "ece_eval": [ece_e_before, ece_e_after],
           "thresholds": thr, "metrics": [m_raw, m_before, m_after]}
(OUT/"step2_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
print(f"[+] {HERE/'models'/'v8_5_calibration.json'}\n[+] {OUT/'step2_summary.json'}")
print("\n[✓] BƯỚC 2 phân tích xong.")
