# Phân tích Val Set, F1 Metric và Điểm Rò Rỉ — NSL-KDD

> Ngày: 2026-06-24

---

## 1. Val Set Lấy Từ Đâu?

**Val = 15% stratified random split từ KDDTrain+, không phải KDDTest+.**

```python
# src/training/train_ft_transformer_nslkdd.py:182-188
X_train, X_val, y_train, y_val = train_test_split(
    X_train_full, y_train_full,
    test_size=0.15,
    stratify=y_train_full,   # stratify theo train distribution
    random_state=seed,
)
# SMOTE chỉ áp dụng trên train, không bao giờ trên val/test
```

### Distribution Shift: KDDTrain+ vs KDDTest+

| Class | KDDTrain+ | Val (~15%) | KDDTest+ |
|-------|----------:|----------:|---------:|
| Normal | 67,343 (53.5%) | ~10,101 | 9,711 (43.1%) |
| DoS | 45,927 (36.5%) | ~6,889 | 7,458 (33.1%) |
| Probe | 11,656 (9.3%) | ~1,748 | 2,421 (10.7%) |
| **R2L** | **995 (0.8%)** | **~149** | **2,885 (12.8%)** |
| **U2R** | **52 (0.04%)** | **~8** | **67 (0.3%)** |
| **Tổng** | **125,973** | **~18,896** | **22,542** |

**Hệ quả:** Val set chỉ có ~149 mẫu R2L và ~8 mẫu U2R. Checkpoint selection
optimize trên val này thực ra không học được gì có ý nghĩa về 2 class thiểu số đó.
Nhưng khi đánh giá trên KDDTest+, R2L chiếm **12.8%** — gấp **16x** so với trong train.
Đây là nguyên nhân chính khiến val macro-F1 trông cao hơn test macro-F1 thực tế.

---

## 2. Macro hay Weighted F1?

| Nơi dùng | Metric | Code |
|----------|--------|------|
| Epoch monitoring (train/val) | **macro-F1** | `f1_score(..., average='macro')` — line 340 |
| Checkpoint selection | **val macro-F1** | `best_val_macro_f1` |
| Final test report | Cả macro và weighted | `classification_report(...)` |

**Metric chính để so sánh các run: test macro-F1.**

Lý do dùng macro: weighted F1 luôn trông đẹp vì Normal + DoS chiếm đa số.
Macro mới phản ánh thật hiệu năng trên R2L và U2R.

---

## 3. Per-Class F1 Trên KDDTest+ (3 Run Tốt Nhất)

| Class | support | Baseline<br>weighted sampler | SMOTE<br>custom | v5<br>4-class attack |
|-------|--------:|:----------------------------:|:---------------:|:--------------------:|
| Normal | 9,711 | 0.8318 | 0.7939 | — |
| DoS | 7,458 | 0.9058 | 0.8702 | **0.8944** |
| Probe | 2,421 | 0.6722 | 0.6583 | **0.7041** |
| R2L | 2,885 | 0.3613 | 0.4437 | **0.5959** |
| U2R | 67 | 0.2778 | **0.4235** | 0.3525 |
| **macro F1** | | 0.610 | 0.638 | 0.637 |
| **weighted F1** | | 0.777 | 0.759 | 0.789 |
| **accuracy** | | 0.791 | 0.771 | 0.797 |

### Precision / Recall chi tiết (run có macro F1 cao nhất: SMOTE custom)

| Class | Precision | Recall | F1 | Support |
|-------|----------:|-------:|---:|--------:|
| Normal | 0.710 | 0.900 | 0.794 | 9,711 |
| DoS | 0.932 | 0.816 | 0.870 | 7,458 |
| Probe | 0.624 | 0.697 | 0.658 | 2,421 |
| R2L | **0.932** | **0.291** | **0.444** | 2,885 |
| U2R | 0.350 | 0.537 | 0.424 | 67 |
| macro avg | 0.710 | 0.648 | **0.638** | 22,542 |

---

## 4. Phân Tích Điểm Rò Rỉ

### R2L — Bottleneck lớn nhất (bỏ sót 52–71% sample)

- **Recall = 0.27–0.48** ở mọi run — model không nhận ra R2L ngay cả khi SMOTE tăng precision lên 0.93.
- Khi bỏ class Normal (v5 4-class), R2L recall tăng từ 0.29 lên **0.48** → xác nhận một phần R2L đang bị hiểu nhầm thành Normal trong setup 5-class.
- Root cause: train chỉ có **995 mẫu R2L** nhưng test có **2,885** — không đủ diversity để generalize. R2L trong NSL-KDD bao gồm 15 attack types khác nhau (guess_passwd, ftp_write, snmpgetattack...) với pattern rất khác nhau.

### U2R — Precision thấp (false positive cao)

- Recall ổn (0.45–0.69) nhưng precision rất thấp (0.20–0.35) → model over-predict U2R.
- Train chỉ có **52 mẫu** và val chỉ có **~8 mẫu** → checkpoint selection hoàn toàn không tối ưu được class này.
- SMOTE custom (boost U2R lên 1000 mẫu) cải thiện F1 từ 0.28 → 0.42, nhưng vẫn còn dư địa lớn.

### Val-Test Gap: Val F1 cao ảo

| Run | Val macro-F1 | Test macro-F1 | Gap |
|-----|-------------:|--------------:|----:|
| v2_full_combo_seed42 | 0.685 | 0.613 | **0.072** |
| v2_smote_custom_seed42 | 0.704 | 0.638 | **0.066** |
| v5_two_stage_4class | 0.946 | 0.637 | **0.309** |

Gap 0.07+ (và 0.31 với v5) là bằng chứng rõ ràng val set không đại diện cho test distribution.
Model học "pass val" bằng cách hy sinh R2L recall vì R2L gần như không có trong val.

### Normal-DoS Overlap

- Normal precision thấp hơn recall (0.71 vs 0.90) → một phần traffic attack đang bị gán nhầm là Normal.
- DoS precision cao (0.93) nhưng recall chỉ 0.82 → 18% DoS bị hiểu nhầm — phần lớn sang Normal.

---

## 5. Dư Địa Thật Còn Lại

| Class | F1 hiện tại (best) | Ước tính tiềm năng | Cần làm |
|-------|-------------------:|-------------------:|---------|
| R2L | 0.44–0.60 | ~0.70+ | Val set đại diện hơn; thêm dữ liệu R2L |
| U2R | 0.35–0.42 | ~0.55+ | SMOTE mạnh hơn hoặc few-shot augmentation |
| Probe | 0.66–0.70 | ~0.75 | Cải thiện feature nhận diện scan pattern |
| DoS | 0.87–0.89 | ~0.91 | Gần đỉnh, ít dư địa |
| Normal | 0.79–0.83 | ~0.85 | Phụ thuộc vào R2L fix |

**Nếu chỉ fix R2L recall từ 0.48 → 0.70**, macro F1 ước tính tăng từ ~0.64 lên **~0.72**.

---

## 6. Khuyến Nghị

1. **Thay val set**: Thay vì split 15% từ train (iid), dùng một phần cố định của KDDTest+
   làm val (hoặc stratify val theo test distribution). Điều này sẽ làm checkpoint selection
   phản ánh đúng thực tế.

2. **R2L là ưu tiên số 1**: Tăng cường dữ liệu R2L trong train (SMOTE custom target ≥5,000
   mẫu), hoặc dùng cost-sensitive loss riêng cho R2L với weight cao hơn.

3. **4-class setup đáng xem xét**: Tách Normal detection ra Autoencoder (đã làm ở inference)
   và train FT-Transformer 4-class trên attack-only data cải thiện R2L F1 rõ rệt (0.44→0.60).

4. **Không dùng weighted F1 để compare runs**: Weighted F1 bị chi phối bởi Normal+DoS,
   che giấu sự tụt giảm ở R2L và U2R. Luôn dùng macro F1 làm primary metric.
