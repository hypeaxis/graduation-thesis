# -*- coding: utf-8 -*-
"""Sơ đồ liên kết lý thuyết — Hybrid NIDS (Snort + FT-Transformer).
Xuất fig_theory_linkage.pdf + .png theo style bộ hình đồ án."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os, sys

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "savefig.dpi": 220, "savefig.bbox": "tight", "savefig.pad_inches": 0.08,
})

C = {
    "chal": "#334155", "A": "#0e7490", "B": "#1d4ed8", "C": "#7c3aed",
    "D": "#ea580c", "E": "#15803d", "F": "#be123c", "G": "#475569",
}

fig, ax = plt.subplots(figsize=(16.8, 10.6))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

# căn cột dùng chung
CX = {"L": 20, "M": 50, "R": 80}


def box(cx, cy, w, h, lines, color, fc=None, fs=8.4, tc="white"):
    fc = fc or color
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.25,rounding_size=1.1",
        linewidth=1.1, edgecolor=color, facecolor=fc, alpha=0.97, zorder=3))
    if isinstance(lines, str):
        lines = [lines]
    n = len(lines)
    for i, ln in enumerate(lines):
        yy = cy + h / 2 - (h / (n + 1)) * (i + 1)
        ax.text(cx, yy, ln, ha="center", va="center", color=tc,
                fontsize=(fs + 0.7 if i == 0 else fs),
                fontweight=("bold" if i == 0 else "normal"), zorder=4)


def arrow(x1, y1, x2, y2, color="#1e293b", style="-|>", lw=1.6, ls="solid", rad=0.0):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle=style, mutation_scale=14,
        linewidth=lw, color=color, linestyle=ls, zorder=2,
        connectionstyle=f"arc3,rad={rad}"))


# ── Tiêu đề + chú giải ──────────────────────────────────────────────────────
ax.text(50, 98.2, "SƠ ĐỒ LIÊN KẾT LÝ THUYẾT — Hệ thống NIDS lai ghép (Snort + FT-Transformer)",
        ha="center", va="center", fontsize=14.5, fontweight="bold", color="#0f172a")
ax.text(50, 94.8, "Ba thách thức → ba nhóm giải pháp lý thuyết, cùng vận hành trên một pipeline dữ liệu chung",
        ha="center", va="center", fontsize=9.8, color="#475569", style="italic")

leg = [("A · Dữ liệu & tiền xử lý", C["A"]), ("B · Mô hình lõi", C["B"]),
       ("C · Phân tầng & tổ hợp", C["C"]), ("D · Mất cân bằng", C["D"]),
       ("E · Thích nghi miền", C["E"]), ("F · Lai ghép", C["F"]), ("G · Chỉ số", C["G"])]
lx = 3.0
for txt, col in leg:
    ax.add_patch(FancyBboxPatch((lx, 91.0), 1.6, 1.6, boxstyle="round,pad=0.1",
                                facecolor=col, edgecolor="none", zorder=3))
    ax.text(lx + 2.0, 91.8, txt, ha="left", va="center", fontsize=7.5, color="#334155")
    lx += len(txt) * 0.52 + 4.0

# ── Hàng thách thức (căn 20/50/80) ──────────────────────────────────────────
cy_ch = 86.5
box(CX["L"], cy_ch, 29, 7.4,
    ["THÁCH THỨC 1 — Mất cân bằng lớp cực đoan",
     "Benign 83–99% ; Infiltration <0,01%", "tỉ lệ tới 65.000 : 1"], C["chal"], fs=8.1)
box(CX["M"], cy_ch, 29, 7.4,
    ["THÁCH THỨC 2 — Covariate shift", "khi mang mô hình lab ra môi trường thật",
     "Acc 99,55% → 21,93% ; MCC → −0,015"], C["chal"], fs=8.1)
box(CX["R"], cy_ch, 29, 7.4,
    ["THÁCH THỨC 3 — Giới hạn một tầng đơn lẻ",
     "Snort mù zero-day / DoS-slow", "ML mù payload ngắn (XSS)"], C["chal"], fs=8.1)

# ── Pipeline dữ liệu chung ──────────────────────────────────────────────────
ax.text(50, 81.4, "PIPELINE DỮ LIỆU CHUNG", ha="center", va="center",
        fontsize=8.4, fontweight="bold", color="#334155")
# thách thức → pipeline
for cx in CX.values():
    arrow(cx, cy_ch - 3.9, cx, 80.2, color="#94a3b8", lw=1.2, ls=(0, (4, 3)))

sy = 76.3
sp = [
    (7.5, 12, ["Lưu lượng", "mạng"], C["G"]),
    (25.5, 21, ["Đặc trưng flow", "CICFlowMeter (A.1)", "77–80 đặc trưng/flow"], C["A"]),
    (46.5, 17, ["Chuẩn hoá", "Yeo-Johnson (A.3)", "→ ~Gaussian"], C["A"]),
    (68.0, 18, ["FT-Transformer (B.1)", "Tokenizer→Attention→CLS", "học tương tác đặc trưng"], C["B"]),
    (89.0, 14, ["Phân loại", "+ Cảnh báo"], C["G"]),
]
for cx, w, lines, col in sp:
    box(cx, sy, w, 7.4, lines, col, fs=7.8)
for i in range(len(sp) - 1):
    arrow(sp[i][0] + sp[i][1] / 2, sy, sp[i + 1][0] - sp[i + 1][1] / 2, sy, lw=2.0)

# ── Ba cột giải pháp ────────────────────────────────────────────────────────
top = 65.5
box(CX["L"], top, 28, 5.8, ["NHÓM C + D · Phân tầng & mất cân bằng"], C["C"], fs=8.0)
box(CX["M"], top, 28, 5.8, ["NHÓM E · Thích nghi miền (Testbed)"], C["E"], fs=8.0)
box(CX["R"], top, 28, 5.8, ["NHÓM F · Lai ghép hai tầng"], C["F"], fs=8.0)

# pipeline → header (mũi tên dọc gọn)
for cx, col in ((CX["L"], C["C"]), (CX["M"], C["E"]), (CX["R"], C["F"])):
    arrow(cx, sy - 3.9, cx, top + 3.0, color=col, lw=1.5)
# enabler đặc biệt: FTT cho phép nhóm E
arrow(68.0, sy - 3.9, 62, 71.6, color=C["E"], lw=1.4, rad=-0.2)
ax.text(60.5, 70.6, "FTT cho phép Layer Freezing\n& Model Surgery (RF/XGBoost không có)",
        ha="center", va="center", fontsize=6.8, color=C["E"], style="italic")


def stack(cx, items):
    n = len(items)
    y0, y1, h = 58.0, 13.0, 7.2
    ys = [y0 - (y0 - y1) * i / (n - 1) for i in range(n)]
    for (lines, col), yy in zip(items, ys):
        box(cx, yy, 28, h, lines, col, fs=7.6)
    for i in range(n - 1):
        arrow(cx, ys[i] - h / 2, cx, ys[i + 1] + h / 2, lw=1.4)
    return ys[-1] - h / 2


stack(CX["L"], [
    (["AE Anomaly Gate (B.2)", "lọc Benign, bắt cả tấn công lạ"], C["B"]),
    (["Two-Stage Cascade (C.3)", "Gating 0,85 → Expert (lớp hiếm)"], C["C"]),
    (["CB-Focal (D.1) + Weighted Sampling (D.3)", "cân bằng gradient lớp hiếm"], C["D"]),
    (["Hard Negative Mining ×2 (D.5)", "tinh chỉnh biên quyết định"], C["D"]),
    (["Stacking Meta-LR (C.2) + Ensemble (C.4)", "→ Asymmetric Voting (C.5)"], C["C"]),
])
stack(CX["M"], [
    (["Chẩn đoán Covariate shift (E.1)", "Re-fit Scaler còn tệ hơn: 21,9→6,9%"], C["E"]),
    (["Layer Freezing (E.2)", "đóng băng tầng thấp, học tầng cao"], C["E"]),
    (["Model Surgery 77→80 (E.4)", "ghép 3 đặc trưng NAT, giữ kiến thức cũ"], C["E"]),
    (["Catastrophic Forgetting (E.3)", "CF = 0,61% — quên rất ít"], C["G"]),
    (["Thu dữ liệu thật + Retrain V8.5", "giải pháp cuối cho shift quá lớn"], C["E"]),
])
stack(CX["R"], [
    (["Snort — dựa trên dấu hiệu (F.1)", "packet-level, bắt payload đã biết"], C["F"]),
    (["FT-Transformer — học máy (B.1)", "flow-level, bắt hành vi chưa có luật"], C["B"]),
    (["Tính bổ sung hai tầng", "DoS-slow: chỉ ML · XSS ngắn: chỉ Snort"], C["F"]),
    (["Alert Aggregator (F.3)", "hợp nhất → confirmed alert"], C["F"]),
    (["Không tấn công nào", "bị bỏ sót bởi CẢ hai tầng"], C["F"]),
])

# ── Băng chỉ số (G) ─────────────────────────────────────────────────────────
gy = 6.0
box(50, gy, 90, 5.6,
    ["ĐÁNH GIÁ (NHÓM G):   Macro F1 — chỉ số chính, đều mọi lớp    •    "
     "MCC — bắt phân loại sai hướng (chẩn đoán shift)    •    Balanced Accuracy"],
    C["G"], fs=8.2)
for cx in CX.values():
    arrow(cx, 9.4, cx, gy + 2.9, color="#94a3b8", lw=1.2)

out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(out_dir, exist_ok=True)
for ext in ("pdf", "png"):
    p = os.path.join(out_dir, f"fig_theory_linkage.{ext}")
    fig.savefig(p); print("saved", p)
