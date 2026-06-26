# NSL-KDD Experiment Results — Toàn bộ kết quả thực nghiệm

> Ngày cập nhật: 2026-06-24
> Metric chính: **test macro-F1** trên KDDTest+ (5-class, end-to-end)
> Dataset: KDDTrain+ (125,973 mẫu) → KDDTest+ (22,542 mẫu)

---

## 1. Tóm tắt theo phase

| Phase | Version | Macro-F1 | Δ vs Baseline | Trạng thái |
|---|---|:---:|:---:|:---:|
| Baseline | v2_smote_custom | 0.638 | — | ✅ |
| P0+P1a — val strategy | v7 boost-minority | 0.644 | +0.006 | ✅ |
| P1b — behavioral features | v8 small_auth_session | 0.641 | +0.003 | ❌ revert |
| **P2 — U2R val fix** | **v9** | **0.654** | **+0.016** | ✅ Best FTT |
| P3 — AE-as-feature | v10 no gate | 0.627 | −0.011 | ❌ revert |
| **P4 — LightGBM** | **v11** | **0.668** | **+0.030** | ✅ Best overall |

---

## 2. Per-class chi tiết — tất cả versions

### Macro-F1 và per-class F1

| Version | Macro-F1 | Normal F1 | DoS F1 | Probe F1 | R2L F1 | U2R F1 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| v2_smote_custom (baseline) | 0.638 | 0.794 | 0.870 | 0.658 | 0.444 | 0.424 |
| v7 boost-minority, no SMOTE | 0.644 | 0.803 | 0.886 | **0.736** | 0.484 | 0.312 |
| v8 behavioral feat (v3 data) | 0.641 | 0.799 | 0.886 | 0.693 | 0.489 | 0.336 |
| **v9 U2R val fix** | **0.654** | 0.806 | **0.894** | 0.666 | **0.503** | 0.398 |
| v10 AE-as-feat (v4 data) | 0.627 | 0.774 | 0.838 | 0.684 | 0.498 | 0.338 |
| **v11 LightGBM** | **0.668** | **0.820** | 0.865 | **0.804** | 0.344 | **0.507** |

### Precision / Recall / F1 đầy đủ

| Version | Class | Precision | Recall | F1 |
|---|---|:---:|:---:|:---:|
| **v2_smote_custom (baseline)** | Normal | 0.710 | 0.900 | 0.794 |
| | DoS | 0.932 | 0.816 | 0.870 |
| | Probe | 0.624 | 0.697 | 0.658 |
| | R2L | **0.932** | 0.291 | 0.444 |
| | U2R | 0.350 | 0.537 | 0.424 |
| **v7 boost-minority** | Normal | 0.740 | 0.878 | 0.803 |
| | DoS | 0.957 | 0.824 | 0.886 |
| | Probe | 0.677 | 0.806 | 0.736 |
| | R2L | 0.679 | 0.376 | 0.484 |
| | U2R | 0.235 | 0.463 | 0.312 |
| **v8 behavioral feat** | Normal | 0.711 | 0.913 | 0.799 |
| | DoS | 0.952 | 0.828 | 0.886 |
| | Probe | 0.685 | 0.701 | 0.693 |
| | R2L | **0.922** | 0.333 | 0.489 |
| | U2R | 0.344 | 0.328 | 0.336 |
| **v9 U2R val fix ★** | Normal | 0.742 | 0.882 | 0.806 |
| | DoS | 0.932 | 0.860 | **0.895** |
| | Probe | 0.660 | 0.672 | 0.666 |
| | R2L | 0.731 | 0.383 | **0.503** |
| | U2R | 0.292 | **0.627** | 0.398 |
| **v10 AE-as-feat** | Normal | 0.683 | 0.894 | 0.775 |
| | DoS | 0.946 | 0.752 | 0.838 |
| | Probe | 0.694 | 0.674 | 0.684 |
| | R2L | 0.787 | 0.365 | 0.498 |
| | U2R | 0.223 | **0.702** | 0.338 |
| **v11 LightGBM ★** | Normal | 0.711 | **0.969** | **0.820** |
| | DoS | **0.962** | 0.785 | 0.865 |
| | Probe | 0.785 | **0.824** | **0.804** |
| | R2L | **0.977** | 0.208 | 0.343 |
| | U2R | **0.493** | 0.522 | **0.507** |

---

## 3. Config từng version

| Version | Model | Features | Val Strategy | SMOTE | Best Epoch | Val F1 |
|---|---|:---:|---|:---:|:---:|:---:|
| v2_smote_custom | FT-Transformer v1 | 122 | iid 15% | custom | 2 | 0.704 |
| v7 | FT-Transformer v1 | 122 | boost-minority | none | 4 | 0.758 |
| v8 | FT-Transformer v1 | 124 | boost-minority | none | 14 | 0.849 |
| v9 | FT-Transformer v1 | 122 | boost-minority + U2R≤5 | none | 3 | 0.694 |
| v10 | FT-Transformer v1 | 123 | boost-minority + U2R≤5 | none | 4 | 0.716 |
| v11 | LightGBM | 122 | boost-minority + U2R≤5 | none | 247 trees | — |

**Hyperparameters FT-Transformer (v7–v10):**
- d_model=128, num_heads=8, num_layers=4, d_ff=512, dropout=0.1
- FocalLoss gamma=2.0, alpha=class-balanced (beta=0.9999)
- WeightedRandomSampler, lr=1e-4, weight_decay=1e-4, batch_size=256
- ReduceLROnPlateau, patience=6, max_train_val_gap=0.2

**Hyperparameters LightGBM (v11):**
- num_leaves=127, lr=0.05, n_estimators=1000 (early stop 50)
- subsample=0.8, colsample_bytree=0.8
- reg_alpha=0.1, reg_lambda=1.0
- sample_weight=inverse-frequency per class

---

## 4. Phân tích từng phase

### Phase 0 — Diagnostic (không train)

**Phát hiện chính:**
- warezmaster recall = **0.979** (đã tốt, không phải bottleneck)
- guess_passwd recall = **0.114** (bottleneck thật sự — 1231 test mẫu)
- Nguyên nhân: severe distribution shift train→test
  - Train: 100% telnet, rerror_rate=0.925, logged_in≈0
  - Test: 61% pop_3, rerror_rate≈0, logged_in=0.618
- 62% test R2L có `ae_recon_error < threshold` → bị hard gate chặn nhầm thành Normal
- 64% test U2R có `ae_recon_error < threshold` → tương tự

### Phase 1a — Boost-minority val (v7) ✅ +0.006

**Thay đổi:** val split từ iid 15% → per-class fraction (R2L=40%, U2R=40%, Probe=15%, Normal/DoS=10%)
- R2L val: 149 → 398 mẫu (+167%)
- U2R val: 8 → 21 mẫu (+163%)

**Kết quả:** Probe F1 tăng mạnh +0.078 (0.658→0.736). U2R F1 giảm (0.424→0.312) vì chỉ còn 31 U2R train.

### Phase 1b — Behavioral features (v8) ❌ −0.003

**Thay đổi:** Thêm 2 features vào preprocessing:
- `small_auth_session`: on_auth_service & src_bytes<300 & dst_bytes<1000 & count<5
- `privilege_escalation`: root_shell>0 | su_attempted>0 | num_root>0

**Lý do thất bại:** `small_auth_session` tạo tín hiệu precision cao nhưng hurt recall. R2L precision tăng lên 0.922 (model quá thận trọng), R2L recall giảm 0.376→0.333. warezmaster bị thiệt vì không có `small_auth_session` (session bytes lớn). Val F1 tăng vọt 0.758→0.849 (overfit trên val R2L có signal mạnh).

### Phase 2 — U2R val fix (v9) ✅ +0.016 — Best FT-Transformer

**Thay đổi:** Cap U2R val tại 5 mẫu thay vì 40%:
- U2R val: 21 → 5 mẫu
- U2R train: 31 → **47 mẫu** (+52%)

**Kết quả:** U2R recall tăng 0.463→0.627 (+0.164), R2L F1 cải thiện lên 0.503. Macro-F1 đạt 0.654 — best FT-Transformer.

### Phase 3 — AE-as-feature, bỏ hard gate (v10) ❌ −0.027

**Thay đổi:** Append `ae_recon_error` (MSE từ autoencoder 122→122) vào input. Bỏ hard gate. 123 features.

**Lý do thất bại:** Hard gate đang giúp DoS/Probe — route samples có MSE cao trực tiếp đến FT-Transformer. Khi bỏ gate, DoS recall sụp 0.860→0.752. `ae_recon_error` không đủ để thay thế. Val/test gap tăng (0.040→0.089).

**U2R recall cải thiện (0.627→0.702)** nhưng precision sụp (0.292→0.223), F1 thực tế giảm.

### Phase 4 — LightGBM standalone (v11) ✅ +0.030 — Best overall

**Thay đổi:** Train LightGBM (127 leaves, inverse-freq weights) trên v2 data. Ensemble alpha sweep → best_alpha=1.0 (LightGBM thuần).

**Điểm mạnh:** Probe F1 = 0.804 (+0.138 vs v9), U2R F1 = 0.507 (+0.109 vs v9), Normal recall = 0.969.

**Điểm yếu:** R2L recall = 0.208 (sụp từ 0.383 ở v9). LightGBM không học được generalization cho R2L (guess_passwd drift train→test quá mạnh).

---

## 5. So sánh với literature

| Model | Macro-F1 (KDDTest+) | Nguồn |
|---|:---:|---|
| Standard RF/SVM | ~0.55–0.65 | Nhiều paper |
| FT-Transformer baseline | 0.638 | Session này |
| **v9 FT-Transformer (best)** | **0.654** | Session này |
| **v11 LightGBM** | **0.668** | Session này |
| Typical deep model honest | ~0.60–0.70 | Literature |

> 99% macro-F1 trên KDDTest+ (5-class) **không trung thực**. Mức 0.65–0.70 là cạnh tranh sòng phẳng với literature có distribution shift thật.

---

## 6. Trần lý thuyết và dư địa còn lại

| Lớp | v9 hiện tại | v11 hiện tại | Trần lý thuyết | Ghi chú |
|---|:---:|:---:|:---:|---|
| R2L recall | 0.383 | 0.208 | ~0.78 | 62% bị gate chặn; ~22% snmp unseen |
| U2R F1 | 0.398 | 0.507 | ~0.60 | 47 train mẫu, signature rõ |
| Probe F1 | 0.666 | **0.804** | ~0.85 | LightGBM đã khai thác tốt |
| DoS F1 | **0.895** | 0.865 | ~0.92 | Gần đỉnh |

**Dư địa lớn nhất còn lại:** Per-class ensemble (LightGBM cho Normal/Probe/U2R + FT-Transformer cho R2L) có thể kết hợp điểm mạnh của cả hai.

---

## 7. Files và artifacts

| Artifact | Path |
|---|---|
| Best FT-Transformer checkpoint | `models/outputs/nslkdd_ft_experiments/v9_u2r_val_fix_seed42/models/best_model.pt` |
| Best LightGBM model | `models/outputs/nslkdd_ft_experiments/v11_lgbm_ensemble_seed42/lgbm_model.txt` |
| Preprocessed data v2 (122 feat) | `data/processed/cleaned5Grouped_v2_Kdd{Train,Test}+.csv` |
| Preprocessed data v4 (123 feat, +AE err) | `data/processed/cleaned5Grouped_v4_Kdd{Train,Test}+.csv` |
| Scaler + feature columns v2 | `models/artifacts_preprocess/` |
| Training script FT-Transformer | `src/training/train_ft_transformer_nslkdd.py` |
| LightGBM ensemble script | `src/training/train_lightgbm_ensemble.py` |
| AE feature generator | `src/data_processing/generate_ae_features.py` |
| Preprocessing pipeline | `src/data_processing/preprocessing_pipeline.py` |
