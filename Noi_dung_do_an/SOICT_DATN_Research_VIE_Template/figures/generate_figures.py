"""
Generate all thesis figures for Hybrid NIDS thesis.
Run: python3 generate_figures.py
Output: PDF files in the same directory.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# ── consistent style ──────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 150,
    'savefig.dpi': 200,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
})

BLUE   = '#2563EB'
GREEN  = '#16A34A'
ORANGE = '#EA580C'
RED    = '#DC2626'
PURPLE = '#7C3AED'
GRAY   = '#6B7280'
LIGHT  = '#DBEAFE'


# ── 1. NSL-KDD ablation bar chart ─────────────────────────────────────────────
def fig_nslkdd_ablation():
    models = ['FTT\nbaseline', 'FTT +\nBoost-Val', 'LightGBM\nđơn lẻ', 'Stacking\nEnsemble']
    scores = [0.638, 0.654, 0.668, 0.681]
    colors = [LIGHT, LIGHT, LIGHT, BLUE]
    edge   = [BLUE]*4

    fig, ax = plt.subplots(figsize=(6, 3.8))
    bars = ax.bar(models, scores, color=colors, edgecolor=edge, linewidth=1.4, width=0.55)
    bars[-1].set_edgecolor(BLUE)

    for bar, val in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
                f'{val:.3f}', ha='center', va='bottom', fontsize=10,
                fontweight='bold' if val == max(scores) else 'normal')

    ax.set_ylim(0.60, 0.72)
    ax.set_ylabel('Macro F1 (5 lớp, KDDTest+)')
    ax.set_title('So sánh kiến trúc trên NSL-KDD (đánh giá đầu-cuối)')
    ax.axhline(0.681, color=BLUE, linestyle='--', linewidth=0.8, alpha=0.5)
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_nslkdd_ablation.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_nslkdd_ablation.png'))
    plt.close(fig)
    print('✓ fig_nslkdd_ablation')


# ── 2. NSL-KDD per-class F1 ───────────────────────────────────────────────────
def fig_nslkdd_perclass():
    classes = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
    precision = [0.7154, 0.9630, 0.8024, 0.9681, 0.5517]
    recall    = [0.9682, 0.8032, 0.7852, 0.2523, 0.4776]
    f1        = [0.8228, 0.8759, 0.7937, 0.4003, 0.5120]

    x = np.arange(len(classes))
    w = 0.26
    fig, ax = plt.subplots(figsize=(7, 4))

    ax.bar(x - w, precision, w, label='Precision', color='#93C5FD', edgecolor='#1D4ED8')
    ax.bar(x,     recall,    w, label='Recall',    color='#6EE7B7', edgecolor='#065F46')
    ax.bar(x + w, f1,        w, label='F1-score',  color=BLUE,      edgecolor='#1D4ED8')

    ax.set_xticks(x)
    ax.set_xticklabels(classes)
    ax.set_ylim(0, 1.10)
    ax.set_ylabel('Score')
    ax.set_title('Kết quả phân loại đầu-cuối trên KDDTest+ (Stacking Ensemble)')
    ax.legend(loc='upper right')
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # annotate R2L recall
    ax.annotate('R2L Recall\n= 0.25\n(giới hạn\ndữ liệu)',
                xy=(3 - w*0.05, 0.2523), xytext=(3.6, 0.45),
                arrowprops=dict(arrowstyle='->', color=RED),
                color=RED, fontsize=8.5)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_nslkdd_perclass.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_nslkdd_perclass.png'))
    plt.close(fig)
    print('✓ fig_nslkdd_perclass')


# ── 3. CIC-IDS-2017 class imbalance ──────────────────────────────────────────
def fig_cic_imbalance():
    labels = ['Benign', 'DoS\nHulk', 'DoS\nGoldenEye', 'DoS\nSlowloris', 'DoS\nSlowhttptest',
              'DDoS', 'PortScan', 'Brute\nForce', 'Web\nAttack', 'Bot', 'Infiltration', 'Heartbleed']
    # approximate percentages from 2.83M flows
    pcts = [82.70, 5.11, 2.33, 0.82, 0.60, 4.69, 2.27, 0.53, 0.47, 0.07, 0.03, 0.003]
    colors_bar = [GREEN if p > 5 else (ORANGE if p > 0.5 else RED) for p in pcts]
    colors_bar[0] = GRAY

    fig, ax = plt.subplots(figsize=(9, 4))
    x = np.arange(len(labels))
    bars = ax.bar(x, pcts, color=colors_bar, edgecolor='white', linewidth=0.5)

    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel('Tỉ lệ (%, thang log)')
    ax.set_title('Phân phối lớp trong CIC-IDS-2017 (~2,83 triệu flow)')
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # annotate ratios
    ax.annotate('82,7%', xy=(0, 82.7), xytext=(0.5, 70),
                fontsize=9, color=GRAY, fontweight='bold')
    ax.annotate('Benign:Infiltration\n= 2.750 : 1', xy=(10, 0.03), xytext=(7, 0.008),
                arrowprops=dict(arrowstyle='->', color=RED),
                fontsize=8, color=RED)

    patches = [
        mpatches.Patch(color=GRAY,   label='Benign (82,7%)'),
        mpatches.Patch(color=GREEN,  label='Tấn công > 5%'),
        mpatches.Patch(color=ORANGE, label='Tấn công 0,5–5%'),
        mpatches.Patch(color=RED,    label='Tấn công < 0,5%'),
    ]
    ax.legend(handles=patches, loc='upper right', fontsize=9)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_cic_imbalance.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_cic_imbalance.png'))
    plt.close(fig)
    print('✓ fig_cic_imbalance')


# ── 4. HNM ablation ───────────────────────────────────────────────────────────
def fig_hnm_ablation():
    stages  = ['Baseline\n(trước HNM)', 'Sau 2 vòng\nHNM']
    botnet  = [0.4787, 0.6512]
    infilt  = [0.3821, 0.5903]

    x = np.arange(len(stages))
    w = 0.30
    fig, ax = plt.subplots(figsize=(5.5, 4))

    b1 = ax.bar(x - w/2, botnet, w, label='Botnet F1',      color='#FCA5A5', edgecolor=RED,    linewidth=1.3)
    b2 = ax.bar(x + w/2, infilt, w, label='Infiltration F1', color='#93C5FD', edgecolor=BLUE,   linewidth=1.3)

    for bar, val in zip(list(b1)+list(b2), botnet+infilt):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.008,
                f'{val:.4f}', ha='center', va='bottom', fontsize=9)

    # delta annotations
    ax.annotate('', xy=(1 - w/2, 0.6512), xytext=(0 - w/2, 0.4787),
                arrowprops=dict(arrowstyle='->', color=RED, lw=1.5))
    ax.annotate('', xy=(1 + w/2, 0.5903), xytext=(0 + w/2, 0.3821),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=1.5))
    ax.text(0.32, 0.62, '+36,0%', color=RED,  fontsize=9, fontweight='bold')
    ax.text(0.68, 0.54, '+54,5%', color=BLUE, fontsize=9, fontweight='bold')

    ax.set_xticks(x)
    ax.set_xticklabels(stages)
    ax.set_ylim(0, 0.80)
    ax.set_ylabel('F1-score')
    ax.set_title('Đóng góp của Hard Negative Mining\n(2 vòng, nhân bản 10×)')
    ax.legend()
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_hnm_ablation.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_hnm_ablation.png'))
    plt.close(fig)
    print('✓ fig_hnm_ablation')


# ── 5. Ensemble ablation ──────────────────────────────────────────────────────
def fig_ensemble_compare():
    metrics = ['Botnet F1', 'Infiltration F1']
    before  = [0.6512, 0.5903]   # after HNM, before ensemble
    after   = [0.7344, 0.7407]   # final ensemble

    x = np.arange(len(metrics))
    w = 0.32
    fig, ax = plt.subplots(figsize=(5.5, 4))

    b1 = ax.bar(x - w/2, before, w, label='Expert Network (sau HNM)', color='#FDE68A', edgecolor=ORANGE, linewidth=1.3)
    b2 = ax.bar(x + w/2, after,  w, label='Asymmetric Ensemble cuối',  color=BLUE,      edgecolor='#1D4ED8', linewidth=1.3)

    for bar, val in zip(list(b1)+list(b2), before+after):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.008,
                f'{val:.4f}', ha='center', va='bottom', fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=11)
    ax.set_ylim(0, 0.90)
    ax.set_ylabel('F1-score')
    ax.set_title('Đóng góp của Asymmetric Ensemble Voting\n(FTT + RF + KNN)')
    ax.legend(loc='lower right')
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3)
    ax.set_axisbelow(True)

    # delta labels
    ax.text(0.22, 0.72, '+0,0832', color=BLUE, fontsize=9, fontweight='bold')
    ax.text(1.22, 0.72, '+0,1504', color=BLUE, fontsize=9, fontweight='bold')

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_ensemble_compare.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_ensemble_compare.png'))
    plt.close(fig)
    print('✓ fig_ensemble_compare')


# ── 6. Domain adaptation comparison ──────────────────────────────────────────
def fig_da_comparison():
    methods   = ['Direct\nTransfer', 'Re-fit\nScaler', 'Layer\nFreezing', 'Model\nSurgery']
    accuracy  = [21.93, 6.87, 99.82, 99.87]
    mcc       = [-0.015, 0.006, 0.6825, 0.7333]

    x = np.arange(len(methods))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))
    colors_acc = [RED, RED, GREEN, GREEN]
    colors_mcc = [RED, GRAY, ORANGE, BLUE]

    bars1 = ax1.bar(x, accuracy, color=colors_acc, edgecolor='white', linewidth=0.8, width=0.55)
    for bar, val in zip(bars1, accuracy):
        ax1.text(bar.get_x()+bar.get_width()/2,
                 bar.get_height() + (1.5 if val > 5 else 0.3),
                 f'{val:.2f}%', ha='center', va='bottom', fontsize=9.5,
                 fontweight='bold' if val > 50 else 'normal')
    ax1.set_xticks(x); ax1.set_xticklabels(methods)
    ax1.set_ylabel('Accuracy (Testbed WSL2, %)')
    ax1.set_title('Accuracy qua các can thiệp')
    ax1.set_ylim(-5, 115)
    ax1.spines[['top','right']].set_visible(False)
    ax1.yaxis.grid(True, alpha=0.3); ax1.set_axisbelow(True)

    bars2 = ax2.bar(x, mcc, color=colors_mcc, edgecolor='white', linewidth=0.8, width=0.55)
    ax2.axhline(0, color='black', linewidth=0.8, linestyle='-')
    for bar, val in zip(bars2, mcc):
        offset = 0.02 if val >= 0 else -0.06
        ax2.text(bar.get_x()+bar.get_width()/2, val + offset,
                 f'{val:+.4f}', ha='center', va='bottom', fontsize=9,
                 fontweight='bold' if abs(val) > 0.5 else 'normal')
    ax2.set_xticks(x); ax2.set_xticklabels(methods)
    ax2.set_ylabel('MCC (Matthews Correlation Coefficient)')
    ax2.set_title('MCC qua các can thiệp')
    ax2.set_ylim(-0.15, 0.85)
    ax2.spines[['top','right']].set_visible(False)
    ax2.yaxis.grid(True, alpha=0.3); ax2.set_axisbelow(True)

    fig.suptitle('Chuỗi can thiệp Domain Adaptation: CIC → Testbed WSL2', fontsize=12, fontweight='bold')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_da_comparison.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_da_comparison.png'))
    plt.close(fig)
    print('✓ fig_da_comparison')


# ── 7. PortScan inseparability ────────────────────────────────────────────────
def fig_portscan_inseparable():
    algos  = ['FTT\n(CE)', 'FTT\n(Focal)', 'FTT\n(CW×5)', 'RF\n(150 cây)', 'KNN\n(K=5)', 'Tất cả\n(+CIC surr.)']
    scores = [7.5, 6.8, 8.1, 5.2, 4.9, 100.0]
    colors = [RED]*5 + [GREEN]

    fig, ax = plt.subplots(figsize=(7, 3.8))
    bars = ax.bar(algos, scores, color=colors, edgecolor='white', linewidth=0.5, width=0.6)
    for bar, val in zip(bars, scores):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height() + 0.8,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10,
                fontweight='bold' if val == 100 else 'normal')

    ax.set_ylabel('PortScan F1 (%)')
    ax.set_title('PortScan F1 theo thuật toán — WSL/NAT vs. dữ liệu surrogate\n'
                 '(kết quả < 9% trên mọi thuật toán ⟹ vấn đề dữ liệu, không phải mô hình)')
    ax.set_ylim(0, 115)
    ax.axhline(100, color=GREEN, linestyle='--', linewidth=0.8, alpha=0.6)
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3); ax.set_axisbelow(True)

    ax.annotate('Inject CIC\nFriday data\n(hardware)', xy=(5, 100), xytext=(4.1, 80),
                arrowprops=dict(arrowstyle='->', color=GREEN),
                fontsize=9, color=GREEN, fontweight='bold')

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_portscan_inseparable.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_portscan_inseparable.png'))
    plt.close(fig)
    print('✓ fig_portscan_inseparable')


# ── 8. V8.5 per-class F1 ─────────────────────────────────────────────────────
def fig_v85_perclass():
    classes = ['Benign', 'BruteForce', 'DoS', 'PortScan', 'Web Attack']
    f1      = [0.91, 0.86, 0.93, 1.00, 0.88]
    colors  = [GRAY, ORANGE, BLUE, GREEN, PURPLE]

    fig, ax = plt.subplots(figsize=(6.5, 4))
    bars = ax.bar(classes, f1, color=colors, edgecolor='white', linewidth=0.5, width=0.55)
    for bar, val in zip(bars, f1):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.005,
                f'{val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    ax.axhline(0.917, color='black', linestyle='--', linewidth=1.0, label='Macro F1 = 0,917')
    ax.set_ylim(0.70, 1.08)
    ax.set_ylabel('F1-score')
    ax.set_title('V8.5 — Kết quả per-class trên tập validation đa dạng miền\n(11.183 flows, 5 lớp)')
    ax.legend(loc='lower right')
    ax.spines[['top','right']].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3); ax.set_axisbelow(True)

    # BruteForce annotation
    ax.annotate('Recall = 90%\n(hydra + CIC Patator)', xy=(1, 0.86),
                xytext=(1.8, 0.79),
                arrowprops=dict(arrowstyle='->', color=ORANGE),
                fontsize=8.5, color=ORANGE)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'fig_v85_perclass.pdf'))
    fig.savefig(os.path.join(OUT, 'fig_v85_perclass.png'))
    plt.close(fig)
    print('✓ fig_v85_perclass')


if __name__ == '__main__':
    fig_nslkdd_ablation()
    fig_nslkdd_perclass()
    fig_cic_imbalance()
    fig_hnm_ablation()
    fig_ensemble_compare()
    fig_da_comparison()
    fig_portscan_inseparable()
    fig_v85_perclass()
    print('\nAll figures saved to:', OUT)
