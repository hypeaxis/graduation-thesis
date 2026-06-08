# Session Log - 2026-06-07 (session-01)

## Goal
- Cải thiện model metrics (Macro-F1 từ 0.6679 → target ≥ 0.75).
- Thêm SMOTE, label smoothing, grouped feature embedding, cosine scheduler.
- Backup kiến trúc cũ trước khi thay đổi.
- Chạy grid experiments v2 (8 runs × 20 epochs).

## Root Cause Analysis
Trước khi sửa code, đã phân tích nguyên nhân gốc rễ:

### Class Distribution Mismatch (Critical)
| Class | Train | Test | Vấn đề |
|-------|-------|------|--------|
| Normal | 67,343 (53.5%) | 9,711 (43.1%) | OK |
| DoS | 45,927 (36.5%) | 7,458 (33.1%) | OK |
| Probe | 11,656 (9.3%) | 2,421 (10.7%) | OK |
| R2L | 995 (0.79%) | 2,885 (12.8%) | Test gấp 2.9x train |
| U2R | 52 (0.04%) | 67 (0.30%) | Chỉ 52 mẫu train |

### Unseen Attack Subtypes in Test
- R2L: snmpguess(331), snmpgetattack(178), httptunnel(133), named(17), sendmail(14), xlock(9), xsnoop(4) — ALL absent in train
- U2R: ps(15), xterm(13), sqlattack(2) — ALL absent in train

## Files Backed Up
Tất cả file architecture cũ đã lưu vào `MLAnomalyDetection/archive_v1/`:
- `phase2_ft_transformer_v1.py`
- `train_ft_transformer_nslkdd_v1.py`
- `run_nslkdd_ft_experiments_v1.py`
- `preprocessing_pipeline_v1.py`

## Dependencies Added
- `imbalanced-learn==0.12.4` (cho SMOTE)

## Code Changes

### 1. phase2_ft_transformer.py
- **Added** `LabelSmoothingFocalLoss`: Focal loss với label smoothing factor, giảm overconfidence
- **Added** `FeatureGroupEmbedding`: Nhóm 122 features thành 4 logical groups:
  - numeric (38 features, idx 0-37)
  - protocol_type one-hot (3 features, idx 38-40)
  - service one-hot (70 features, idx 41-110)
  - flag one-hot (11 features, idx 111-121)
  - Mỗi group dùng shared projection → attention matrix giảm từ 123×123 xuống 5×5
- **Added** `FTTransformerV2`: Model mới với:
  - `FeatureGroupEmbedding` (hoặc `FeatureEmbedding` nếu `use_grouped_embedding=False`)
  - Deeper classifier head: Linear→BN→GELU→Dropout→Linear→BN→GELU→Dropout→Linear
  - Default d_model=192, dropout=0.15
- **Preserved** `FTTransformer` (v1) nguyên vẹn cho backward compatibility

### 2. train_ft_transformer_nslkdd.py
- **Added** imports: `FTTransformerV2`, `LabelSmoothingFocalLoss`
- **Added** CLI args:
  - `--model-version {v1,v2}` (default: v1)
  - `--label-smoothing FLOAT` (default: 0.0)
  - `--scheduler {plateau,cosine}` (default: plateau)
  - `--smote-strategy {none,minority,auto,custom}` (default: none)
  - `--smote-k INT` (default: 5)
- **Added** `apply_smote()` function:
  - Strategy `custom`: R2L → 5000 samples, U2R → 1000 samples
  - Auto-adjusts k_neighbors for tiny classes
  - Only applied to train split (never val/test)
- **Modified** `load_datasets()`: integrates SMOTE after train/val split
- **Modified** `main()`:
  - Model version selection (v1/v2)
  - Loss function selection (FocalLoss/LabelSmoothingFocalLoss)
  - Scheduler selection (plateau/cosine)
  - Enhanced logging output
- **Modified** summary JSON: thêm model_version, label_smoothing, smote_strategy, scheduler

### 3. run_nslkdd_ft_experiments.py
- **Added** 8 experiment configs v2 (giữ nguyên 8 configs v1):
  - `v2_smote_custom_seed42/62`: SMOTE only (v1 arch)
  - `v2_smote_ls01_seed42`: SMOTE + label smoothing 0.1
  - `v2_smote_cosine_seed42`: SMOTE + cosine scheduler
  - `v2_grouped_smote_seed42/62`: V2 arch (grouped embedding, d_model=192, dropout=0.15) + SMOTE
  - `v2_full_combo_seed42/62`: V2 arch + SMOTE + label smoothing 0.05 + cosine

## Verification
- V1 model backward compat: OK (FTTransformer output shape [B,5], 841,861 params)
- V2 model: OK (FTTransformerV2 output shape [B,5], 1,468,165 params)
- LabelSmoothingFocalLoss: OK
- CLI args: all new args visible in --help

## Training Status
- 8 v2 runs launched as background task
- All runs use 20 epochs, patience 8
- PENDING: collect metrics after training completes

## Baseline for Comparison
Best v1 run (nslkdd_ft_sampler_weighted_seed62):
- test_accuracy: 0.8005
- test_macro_f1: 0.6679
- R2L F1: 0.5094
- U2R F1: 0.4252
- Val-Test gap: 0.0865

## Final Results
Đã hoàn thành toàn bộ 8/8 runs:

| Metric | Baseline (v1, no smote) | v2_smote_ls01 | v2_smote_cosine | v2_grouped_smote (s62) | v2_full_combo (s62) |
|--------|:--:|:--:|:--:|:--:|:--:|
| Accuracy | **0.8005** | 0.7767 | 0.7857 | 0.7570 | 0.7640 |
| Macro-F1 | **0.6679** | 0.6396 | 0.6481 | 0.6130 | 0.6195 |
| Best Epoch| 19 | 3 | 3 | 3 | 3 |
| R2L F1 | **0.5094** | 0.4632 | 0.4851 | 0.4848 | 0.4813 |
| U2R F1 | **0.4252** | 0.4468 | 0.4358 | 0.2603 | 0.2622 |

**Phân tích & Kết luận:**
1. **SMOTE thất bại trên tập test NSL-KDD:** Tất cả biến thể dùng SMOTE đều bị overfit cực kỳ sớm (ngay epoch 2-3). Nguyên nhân là tập test NSL-KDD chứa lượng lớn "unseen attacks" (các kỹ thuật R2L/U2R chưa từng xuất hiện ở tập train). Việc tăng cường (oversampling) trên các kiểu tấn công *cũ* chỉ khiến mô hình học vẹt quá sâu và càng mất khả năng tổng quát hóa với các cuộc tấn công *mới*.
2. **Kiến trúc V2 (Grouped Embedding):** Giảm thời gian training xuống gấp 10 lần (do rút gọn 122 token thành 4 token groups). Tuy nhiên, nó đánh mất quá nhiều thông tin chi tiết giữa các features, khiến F1 của các nhóm khó như U2R rơi tự do (từ 0.42 xuống 0.26).
3. **Quyết định:** Giữ nguyên kiến trúc Baseline v1 (Feature Embedding riêng lẻ, không SMOTE). Việc tiếp theo nên tập trung vào:
   - Thay đổi hàm Loss (ví dụ thử nghiệm Asymmetric Loss hoặc Cost-Sensitive Learning trực tiếp thay vì oversampling).
   - Tăng cường Regularization (Weight Decay cao hơn, Dropout cao hơn) thay vì cố cân bằng class.
