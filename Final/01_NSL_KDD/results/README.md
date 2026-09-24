# GĐ1 — Kết quả NSL-KDD: file nào là SỐ LIỆU CHÍNH THỨC

> **Số liệu headline của đồ án (Macro F1 = 0,6809):**
> [`nslkdd_ft_experiments/v12_stacking_seed42/meta_lr_report.txt`](nslkdd_ft_experiments/v12_stacking_seed42/meta_lr_report.txt)
> — đây là **Stacking Ensemble (FTT + LightGBM → Meta-LR)**, khớp đúng bảng kết quả Chương 5 (per-class: Normal 0,8228 · DoS 0,8759 · Probe 0,7937 · R2L 0,4003 · U2R 0,5120 · Acc 80,09%).

Các thư mục còn lại là **bước trung gian trong ablation** (đừng nhầm là số cuối):

| Thư mục | Macro F1 | Vai trò (≈ bảng ablation Chương 5) |
|---|:-:|---|
| `v9_u2r_val_fix_seed42/` | 0,6535 | FT-Transformer đơn lẻ (sau Boost-Minority + WeightedSampler) |
| `v11_lgbm_ensemble_seed42/` | 0,6678 | LightGBM base learner độc lập (báo cáo: 0,668) |
| **`v12_stacking_seed42/`** | **0,6809** | **Stacking Ensemble — SỐ CUỐI** |
| `v13_class_aware_gate_seed42/` | 0,6809 | Biến thể class-aware gate (cùng mức) |

> Lưu ý: NSL-KDD là **giai đoạn nền tảng** — giá trị là số liệu này, không phải hệ thống triển khai (hệ thống thật = V8.5, GĐ5).
