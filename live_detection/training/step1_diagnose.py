"""
BƯỚC 1 — CHẨN ĐOÁN COVARIATE SHIFT (không cần retrain).

Mục tiêu (theo HUONG_DAN_CAI_THIEN_MODEL_LIVE.md, Mục 4 · Bước 1):
    Biến "domain shift" mơ hồ thành DANH SÁCH 3–5 FEATURE THỦ PHẠM cụ thể,
    bằng 2 góc nhìn độc lập nhưng phải hội tụ:
      (A) Phân bố feature lệch ở đâu?  -> KS-test lab-benign vs real-benign.
      (B) Feature nào ĐẨY quyết định sang lớp tấn công trên chính flow FP? -> SHAP.

Ràng buộc Mục 0: CHỈ đọc/copy dữ liệu ngoài repo vào live_detection/, không sửa gốc.
    - benign_lab  = các dòng Label==Benign trong tập TRAIN của model (Combined_V8_5.csv)
                    -> copy ra data/analysis/benign_lab.csv (đã sẵn 80 feature).
    - benign_real = data/analysis/benign_real.csv (cột CICFlowMeter thô)
                    -> đưa qua ĐÚNG FeatureExtractor của pipeline live để về 80 feature
                       (parity: cùng phép biến đổi model đang thấy lúc suy luận live).

Chạy:  python training/step1_diagnose.py         (từ thư mục live_detection/)
Xuất:  training/step1_out/  (KS ranking, z-score scaled, SHAP FP, ablation, PNG, summary)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from scipy.stats import ks_2samp

# ----------------------------------------------------------------------------
# Đường dẫn — self-contained trong live_detection/, chỉ ĐỌC Combined_V8_5 ở ngoài.
# ----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent.parent               # = live_detection/
REPO = HERE.parent                                          # = Graduation-Thesis/
ANALYSIS = HERE / "data" / "analysis"
OUT = HERE / "training" / "step1_out"
OUT.mkdir(parents=True, exist_ok=True)

BENIGN_REAL = ANALYSIS / "benign_real.csv"
BENIGN_LAB = ANALYSIS / "benign_lab.csv"                    # sẽ tạo nếu chưa có
COMBINED_V8_5 = REPO / "Phase3_4_Retrain" / "v8" / "v8.5_Combined" / "Combined_V8_5.csv"

MODEL_PT = HERE / "models" / "v8_5_model.pt"
SCALER_PKL = HERE / "models" / "v8_5_scaler.pkl"
ENCODER_PKL = HERE / "models" / "v8_5_encoder.pkl"

sys.path.insert(0, str(HERE))                # để 'from ids_replay.features import ...'
sys.path.insert(0, str(HERE / "model_defs"))  # để 'from hybrid_feature_scaler import ...'
from ids_replay.features import FeatureExtractor, EXPECTED_FEATURES_80   # noqa: E402
from hybrid_feature_scaler import HybridFeatureScaler                    # noqa: E402
from phase2_ft_transformer_v2 import FTTransformer                       # noqa: E402

FEATS = EXPECTED_FEATURES_80
N_HIST = 12          # số feature vẽ histogram overlay
SHAP_BG = 100        # số mẫu nền (background) cho SHAP
SHAP_FP = 300        # số flow FP tối đa để giải thích (giữ chạy vài phút trên CPU)
SHAP_NSAMPLES = 100  # số lần lấy mẫu expected-gradients / flow
SEED = 42
rng = np.random.default_rng(SEED)


def banner(msg: str):
    print("\n" + "=" * 74 + f"\n{msg}\n" + "=" * 74)


# ============================================================================
# 0. Chuẩn bị benign_lab (copy Label==Benign từ tập train vào live_detection/)
# ============================================================================
def prepare_benign_lab() -> pd.DataFrame:
    if BENIGN_LAB.exists():
        print(f"[=] benign_lab đã có sẵn: {BENIGN_LAB.name}")
        return pd.read_csv(BENIGN_LAB)
    banner("0. Copy benign lab (CIC-IDS-2017) từ Combined_V8_5.csv -> live_detection/")
    if not COMBINED_V8_5.exists():
        sys.exit(f"[!] Không thấy tập train {COMBINED_V8_5}. Cần định vị lại trước Bước 1.")
    frames = []
    for ch in pd.read_csv(COMBINED_V8_5, chunksize=100_000):
        frames.append(ch[ch["Label"] == "Benign"])
    lab = pd.concat(frames, ignore_index=True)
    lab.to_csv(BENIGN_LAB, index=False)
    print(f"[+] Trích {len(lab):,} flow Benign (lab) -> {BENIGN_LAB}")
    return lab


# ============================================================================
# 1. Dựng 2 ma trận trong CÙNG không gian 80 feature
# ============================================================================
def build_matrices():
    banner("1. Dựng ma trận 80 feature: lab (đã có sẵn) vs real (qua FeatureExtractor)")
    lab_df = prepare_benign_lab()
    X_lab = lab_df[FEATS].values.astype(np.float32)
    X_lab = np.nan_to_num(X_lab, nan=0.0, posinf=0.0, neginf=0.0)

    real_df = pd.read_csv(BENIGN_REAL, low_memory=False)
    X_real = FeatureExtractor().build(real_df)     # ĐÚNG pipeline live (parity)

    print(f"    lab-benign : {X_lab.shape[0]:>7,} flow x {X_lab.shape[1]} feat")
    print(f"    real-benign: {X_real.shape[0]:>7,} flow x {X_real.shape[1]} feat")
    print(f"    parity: NaN/inf lab={np.isnan(X_lab).sum()}/{np.isinf(X_lab).sum()}"
          f"  real={np.isnan(X_real).sum()}/{np.isinf(X_real).sum()}")
    return X_lab, X_real


# ============================================================================
# 2. KS-test từng feature -> xếp hạng độ lệch phân bố
# ============================================================================
def ks_ranking(X_lab, X_real) -> pd.DataFrame:
    banner("2. KS-test lab vs real cho từng feature (xếp theo KS-statistic giảm dần)")
    rows = []
    for j, name in enumerate(FEATS):
        a, b = X_lab[:, j], X_real[:, j]
        st = ks_2samp(a, b)
        rows.append({
            "feature": name,
            "ks_stat": round(float(st.statistic), 4),
            "p_value": float(st.pvalue),
            "lab_median": round(float(np.median(a)), 4),
            "real_median": round(float(np.median(b)), 4),
            "lab_p99": round(float(np.percentile(a, 99)), 4),
            "real_p99": round(float(np.percentile(b, 99)), 4),
        })
    df = pd.DataFrame(rows).sort_values("ks_stat", ascending=False).reset_index(drop=True)
    df.to_csv(OUT / "step1_ks_ranking.csv", index=False)
    print(df.head(15).to_string(index=False))
    print(f"\n[+] Bảng đầy đủ 80 feature -> {OUT/'step1_ks_ranking.csv'}")
    return df


# ============================================================================
# 3. Histogram overlay cho top-N feature lệch nhất
# ============================================================================
def plot_histograms(X_lab, X_real, ks_df):
    banner(f"3. Histogram overlay {N_HIST} feature lệch nhất -> PNG")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    top = ks_df.head(N_HIST)["feature"].tolist()
    ncol, nrow = 3, (N_HIST + 2) // 3
    fig, axes = plt.subplots(nrow, ncol, figsize=(15, 3.2 * nrow))
    for ax, name in zip(axes.ravel(), top):
        j = FEATS.index(name)
        a, b = X_lab[:, j], X_real[:, j]
        lo, hi = np.percentile(np.concatenate([a, b]), [1, 99])   # cắt đuôi để nhìn được
        if hi <= lo:
            hi = lo + 1.0
        bins = np.linspace(lo, hi, 50)
        ax.hist(a, bins=bins, density=True, alpha=0.55, label="lab (CIC)", color="#4C78A8")
        ax.hist(b, bins=bins, density=True, alpha=0.55, label="real (live)", color="#E45756")
        ks = ks_df.loc[ks_df.feature == name, "ks_stat"].iloc[0]
        ax.set_title(f"{name}\nKS={ks}", fontsize=9)
        ax.legend(fontsize=7)
    for ax in axes.ravel()[len(top):]:
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "step1_hist_overlay.png", dpi=110)
    plt.close(fig)
    print(f"[+] {OUT/'step1_hist_overlay.png'}")


# ============================================================================
# 4. Kiểm tra "nổ z-score" ở không gian SAU scaler (cơ chế 1: ngoại suy quá tự tin)
# ============================================================================
def zscore_extrapolation(X_lab, X_real, scaler) -> pd.DataFrame:
    banner("4. Sau HybridFeatureScaler: feature nào bị đẩy ra z-score cực lớn (real)?")
    Zr = scaler.transform(X_real)
    Zl = scaler.transform(X_lab)
    rows = []
    for j, name in enumerate(FEATS):
        zr = Zr[:, j]
        rows.append({
            "feature": name,
            "real_max_absz": round(float(np.max(np.abs(zr))), 2),
            "real_pct_gt5": round(float(np.mean(np.abs(zr) > 5) * 100), 2),
            "real_pct_gt10": round(float(np.mean(np.abs(zr) > 10) * 100), 2),
            "lab_max_absz": round(float(np.max(np.abs(Zl[:, j]))), 2),
        })
    df = pd.DataFrame(rows).sort_values("real_pct_gt5", ascending=False).reset_index(drop=True)
    df.to_csv(OUT / "step1_scaled_zscore.csv", index=False)
    print("    (top theo % flow real có |z|>5 — dấu hiệu ngoại suy ngoài vùng train)")
    print(df.head(15).to_string(index=False))
    print(f"\n[+] {OUT/'step1_scaled_zscore.csv'}")
    return df


# ============================================================================
# 5. Chạy model trên real-benign -> định vị các flow FP + thống kê confidence
# ============================================================================
def load_model():
    encoder = joblib.load(ENCODER_PKL)
    scaler = HybridFeatureScaler.load(str(SCALER_PKL))
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_heads=8, num_layers=4, d_ff=512,
                          dropout=0.15, drop_path_rate=0.15)
    model.load_state_dict(torch.load(MODEL_PT, map_location="cpu", weights_only=False))
    model.eval()
    return model, scaler, encoder


def predict(model, scaler, encoder, X):
    Xs = scaler.transform(X)
    labels, confs = [], []
    with torch.no_grad():
        for i in range(0, len(Xs), 2048):
            probs = torch.softmax(model(torch.FloatTensor(Xs[i:i + 2048])), dim=1)
            c, idx = probs.max(dim=1)
            labels.append(idx.numpy()); confs.append(c.numpy())
    labels = encoder.inverse_transform(np.concatenate(labels))
    return labels, np.concatenate(confs), Xs


def find_fp(model, scaler, encoder, X_real):
    banner("5. Model V8.5 trên real-benign: tỉ lệ FP + confidence + phân rã theo lớp")
    labels, confs, Xs = predict(model, scaler, encoder, X_real)
    is_fp = labels != "Benign"
    fpr = float(is_fp.mean())
    print(f"    Tổng real-benign : {len(labels):,} flow")
    print(f"    Benign Recall    : {(~is_fp).mean()*100:.2f}%   |   FPR: {fpr*100:.2f}%")
    print(f"    Confidence (FP)  : mean={confs[is_fp].mean():.3f}  "
          f"median={np.median(confs[is_fp]):.3f}  (overconfidence nếu >0.8)")
    print("\n    FP phân rã theo lớp bị gán nhầm:")
    vc = pd.Series(labels[is_fp]).value_counts()
    for cls, n in vc.items():
        m = (labels == cls)
        print(f"      {cls:<12}: {n:>6,} flow  ({n/len(labels)*100:5.2f}% tổng)  "
              f"conf mean={confs[m].mean():.3f}")
    summary = {
        "n_real_benign": int(len(labels)),
        "fpr_pct": round(fpr * 100, 2),
        "benign_recall_pct": round((~is_fp).mean() * 100, 2),
        "fp_conf_mean": round(float(confs[is_fp].mean()), 3),
        "fp_breakdown": {k: int(v) for k, v in vc.items()},
    }
    return is_fp, labels, Xs, summary


# ============================================================================
# 6. SHAP trên các flow FP -> feature nào đẩy quyết định sang lớp tấn công
# ============================================================================
def shap_on_fp(model, encoder, Xs, is_fp, labels) -> pd.DataFrame:
    banner("6. SHAP (GradientExplainer) trên flow FP: feature đẩy sang lớp tấn công")
    import shap

    fp_idx = np.where(is_fp)[0]
    if len(fp_idx) == 0:
        print("    (Không có FP — bỏ qua SHAP.)")
        return pd.DataFrame()
    fp_sample = rng.choice(fp_idx, size=min(SHAP_FP, len(fp_idx)), replace=False)
    # nền = mẫu benign đã scale (tất cả benign_real làm phông "bình thường")
    bg_idx = rng.choice(len(Xs), size=min(SHAP_BG, len(Xs)), replace=False)
    background = torch.FloatTensor(Xs[bg_idx])
    X_explain = torch.FloatTensor(Xs[fp_sample])

    explainer = shap.GradientExplainer(model, background)
    # ranked_outputs=1: CHỈ giải thích lớp có logit cao nhất (=lớp model gán) -> rẻ x5,
    # đúng thứ ta cần (feature đẩy sang lớp tấn công đã dự đoán).
    sv, idx_out = explainer.shap_values(X_explain, ranked_outputs=1, nsamples=SHAP_NSAMPLES)
    contrib = np.asarray(sv[0], dtype=np.float64)         # (n_fp, 80) theo lớp top-1

    mean_abs = np.mean(np.abs(contrib), axis=0)          # độ lớn ảnh hưởng
    mean_signed = np.mean(contrib, axis=0)               # hướng (+ = đẩy sang tấn công)
    df = pd.DataFrame({
        "feature": FEATS,
        "shap_mean_abs": np.round(mean_abs, 5),
        "shap_mean_signed": np.round(mean_signed, 5),
    }).sort_values("shap_mean_abs", ascending=False).reset_index(drop=True)
    df.to_csv(OUT / "step1_shap_fp.csv", index=False)
    print(f"    Giải thích {len(fp_sample)} flow FP (nền {len(bg_idx)}).  Top đẩy quyết định:")
    print(df.head(15).to_string(index=False))
    print(f"\n[+] {OUT/'step1_shap_fp.csv'}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    top = df.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = ["#E45756" if s > 0 else "#4C78A8" for s in top["shap_mean_signed"]]
    ax.barh(top["feature"], top["shap_mean_abs"], color=colors)
    ax.set_xlabel("mean(|SHAP|) toward predicted attack class")
    ax.set_title("Bước 1 — Feature đẩy FP sang lớp tấn công (đỏ=đẩy tăng)")
    fig.tight_layout()
    fig.savefig(OUT / "step1_shap_fp.png", dpi=110)
    plt.close(fig)
    print(f"[+] {OUT/'step1_shap_fp.png'}")
    return df


# ============================================================================
# 7. Ablation "smoking gun": ép feature nghi phạm về median lab -> bao nhiêu FP hồi phục?
# ============================================================================
def ablation_recovery(model, scaler, encoder, X_real, X_lab, is_fp, suspects) -> pd.DataFrame:
    banner("7. Ablation: ép từng feature nghi phạm -> median(lab) -> % FP quay lại Benign")
    fp_idx = np.where(is_fp)[0]
    Xfp = X_real[fp_idx].copy()
    lab_med = np.median(X_lab, axis=0)
    rows = []
    for name in suspects:
        j = FEATS.index(name)
        Xmod = Xfp.copy()
        Xmod[:, j] = lab_med[j]
        lbl, _, _ = predict(model, scaler, encoder, Xmod)
        rec = float(np.mean(lbl == "Benign"))
        rows.append({"feature": name, "fp_recovered_to_benign_pct": round(rec * 100, 2)})
    df = pd.DataFrame(rows).sort_values("fp_recovered_to_benign_pct", ascending=False)
    df.to_csv(OUT / "step1_ablation.csv", index=False)
    print("    (feature nào 1 mình kéo nhiều FP về Benign = thủ phạm mạnh nhất)")
    print(df.to_string(index=False))
    print(f"\n[+] {OUT/'step1_ablation.csv'}")
    return df


# ============================================================================
def main():
    banner("BƯỚC 1 — CHẨN ĐOÁN COVARIATE SHIFT (KS-test + SHAP trên FP)")
    X_lab, X_real = build_matrices()
    ks_df = ks_ranking(X_lab, X_real)
    plot_histograms(X_lab, X_real, ks_df)

    model, scaler, encoder = load_model()
    z_df = zscore_extrapolation(X_lab, X_real, scaler)
    is_fp, labels, Xs, fp_summary = find_fp(model, scaler, encoder, X_real)
    shap_df = shap_on_fp(model, encoder, Xs, is_fp, labels)

    # nghi phạm = hợp của top-KS, top-zscore, top-SHAP
    suspects = []
    for src in (ks_df["feature"].head(8), z_df["feature"].head(8),
                shap_df["feature"].head(8) if len(shap_df) else pd.Series([], dtype=str)):
        for f in src:
            if f not in suspects:
                suspects.append(f)
    abl_df = ablation_recovery(model, scaler, encoder, X_real, X_lab, is_fp, suspects[:12])

    # ---- tổng hợp: giao của 3 góc nhìn = thủ phạm cốt lõi ----
    banner("TỔNG HỢP — thủ phạm cốt lõi (giao của KS + z-score + SHAP)")
    top_ks = set(ks_df["feature"].head(10))
    top_z = set(z_df["feature"].head(10))
    top_shap = set(shap_df["feature"].head(10)) if len(shap_df) else set()
    core = [f for f in FEATS if (f in top_ks) + (f in top_z) + (f in top_shap) >= 2]
    print("    Feature xuất hiện trong >=2/3 bảng top-10:")
    for f in core:
        tags = [t for t, s in [("KS", top_ks), ("Zscore", top_z), ("SHAP", top_shap)] if f in s]
        print(f"      - {f:<28} [{', '.join(tags)}]")

    summary = {
        "fp_diagnosis": fp_summary,
        "top_ks": ks_df.head(10).to_dict("records"),
        "top_zscore": z_df.head(10).to_dict("records"),
        "top_shap": shap_df.head(10).to_dict("records") if len(shap_df) else [],
        "ablation": abl_df.to_dict("records"),
        "core_culprits": core,
    }
    (OUT / "step1_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\n[+] Tổng hợp -> {OUT/'step1_summary.json'}")
    print("\n[✓] BƯỚC 1 hoàn tất. Artifacts trong training/step1_out/.")


if __name__ == "__main__":
    main()
