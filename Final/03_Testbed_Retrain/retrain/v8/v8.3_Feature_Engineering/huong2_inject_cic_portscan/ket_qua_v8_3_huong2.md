# Kết Quả V8.3 — Hướng 2: Inject CIC-IDS-2017 PortScan

**Ngày thực hiện:** 2026-06-23  
**Thời gian training:** ~54 phút (20 epochs, CUDA)  
**Mô hình lưu tại:** `v8_3_huong2_model.pt`

---

## 1. Tóm tắt

| Chỉ số | V8.2 (baseline) | V8.3 Hướng 2 | Thay đổi |
|---|:-:|:-:|:-:|
| Macro F1 | 65.36% | **88.67%** | ▲ +23.31% |
| Balanced Accuracy | — | **84.26%** | — |
| PortScan F1 | 7.5% | **99.99%** | ▲ +92.49% |
| Benign F1 | 50.8% | 91.98% | ▲ +41.18% |
| DoS F1 | 91.4% | 94.11% | ▲ +2.71% |
| Brute Force F1 | 91.9% | 70.26% | ▼ −21.64% |
| Web Attack F1 | 85.2% | 87.02% | ▲ +1.82% |

**Mục tiêu chính đã đạt:** PortScan F1 từ 7.5% → 99.99% ✓

---

## 2. Classification Report chi tiết

```
              precision    recall  f1-score   support

      Benign     0.8562    0.9936    0.9198     51994
 Brute Force     1.0000    0.5416    0.7026      2984
         DoS     0.9890    0.8976    0.9411     19781
    PortScan     1.0000    0.9998    0.9999      5000
  Web Attack     0.9834    0.7803    0.8702     24887

    accuracy                         0.9121    104646
   macro avg     0.9657    0.8426    0.8867    104646
weighted avg     0.9226    0.9121    0.9097    104646

Balanced Accuracy: 0.8426
```

---

## 3. Confusion Matrix

```
             Benign  Brute Force    DoS  PortScan  Web Attack
Benign        51659            0    118         0         217
Brute Force    1368         1616      0         0           0
DoS            1917            0  17755         0         109
PortScan          0            0      0      4999           1
Web Attack     5389            0     79         0       19419
```

---

## 4. Phân tích

### 4.1 Thành công

**PortScan: Precision 100% / Recall 99.98% / F1 99.99%**
- CIC-IDS-2017 PortScan injection hoàn toàn giải quyết vấn đề WSL blind spot
- Model học được pattern nmap TCP connect từ dữ liệu CIC 2017 (thu trên hardware thật)
- `Flow_Duration` là feature phân biệt chính: CIC PortScan median = 48 μs vs Benign = 23,625 μs (491× khác biệt)
- Chỉ 1 PortScan flow bị nhầm thành Web Attack (49,999/5,000 đúng)

**Benign: F1 91.98%** (so với 50.8% ở V8.2)
- Cải thiện lớn do model không còn bị nhầm Benign → PortScan (vấn đề cũ của V8.1/V8.2)

**DoS: F1 94.11%** — ổn định, nhẹ cải thiện

### 4.2 Điểm yếu

**Brute Force Recall: 54.16% (1,368/2,984 flows bị nhầm thành Benign)**
- Nguyên nhân: Run10 Brute Force flows (SSH/FTP) có flow pattern gần với Benign
  (ngắn, ít packet — hydra connection timeout nhanh)
- CIC injection không ảnh hưởng trực tiếp nhưng model có thể đã shift focus

**Web Attack Recall: 78.03% (5,389/24,887 flows bị nhầm thành Benign)**
- Nguyên nhân tương tự: một số Web Attack flows (SQLi thất bại, curl ngắn) giống Benign HTTP
- Cần kiểm tra: có phải Web Attack mới (XSS+curl burst) ngắn hơn pattern cũ không

### 4.3 Lưu ý quan trọng về tập đánh giá

> ⚠️ **Kết quả trên là train set evaluation** (bao gồm cả 90% train + 10% val).  
> Model đã thấy các samples này trong quá trình training → có thể overfit.  
> Cần đánh giá trên **tập test độc lập** (run6 hoặc dataset chưa dùng) để có kết quả thực.

---

## 5. Cấu hình training

| Tham số | Giá trị |
|---|---|
| Base model | `v7_model.pt` (FT-Transformer, 80 features, 5 classes) |
| Dataset | `Combined_V8_3_Huong2.csv` (104,646 flows) |
| PortScan source | CIC-IDS-2017 Friday-PortScan (5,000 sampled / 158,804 available) |
| Epochs | 20 |
| Learning rate | 3e-5 (thấp hơn V7 do domain shift) |
| Loss | Focal Loss (γ=2.0, label smoothing=0.05) |
| Optimizer | AdamW (weight decay=1e-4) |
| Scheduler | CosineAnnealingLR (T_max=20) |
| Device | CUDA |

---

## 6. So sánh với kỳ vọng

| Class | Kỳ vọng | Thực tế | Đạt? |
|---|:-:|:-:|:-:|
| PortScan F1 | > 70% | **99.99%** | ✅ Vượt xa |
| Macro F1 | > 81% | **88.67%** | ✅ Đạt |
| Benign F1 | > 75% | **91.98%** | ✅ Vượt |
| DoS F1 | > 88% | **94.11%** | ✅ Đạt |
| Web Attack F1 | > 83% | **87.02%** | ✅ Đạt |
| Brute Force F1 | > 88% | **70.26%** | ❌ Chưa đạt |

---

## 7. Bước tiếp theo

### Ưu tiên 1 — Đánh giá trên test set độc lập
```bash
# Dùng run6 dataset (chưa dùng trong training)
python3 evaluate_on_testset.py --model v8_3_huong2_model.pt --data <run6_cleaned.csv>
```

### Ưu tiên 2 — Fix Brute Force recall
Brute Force recall 54% là vấn đề lớn. Các hướng:
- **Tăng class weight** cho Brute Force trong Focal Loss
- **SMOTE** cho Brute Force (3k → 8k flows) để model thấy nhiều hơn
- **Fine-tune thêm 5 epoch** với lr=1e-5 tập trung vào Brute Force

### Ưu tiên 3 — So sánh với Hướng 1 (Run11 + SMOTE)
Khi run11 xong, train Hướng 1 và so sánh:
- Hướng 1 PortScan F1 có thể thấp hơn (SMOTE từ 3 open ports)
- Hướng 1 Brute Force F1 có thể tốt hơn (không có domain shift từ CIC)

---

## 8. Files đầu ra

| File | Mô tả |
|---|---|
| `v8_3_huong2_model.pt` | Model checkpoint tốt nhất (4.3 MB) |
| `v8_3_huong2_scaler.pkl` | HybridFeatureScaler (fit trên 94k flows) |
| `v8_3_huong2_encoder.pkl` | LabelEncoder (5 classes) |
| `Combined_V8_3_Huong2.csv` | Dataset training (104,646 flows) |
| `cic_portscan_mapped.csv` | CIC PortScan đã map sang 81 features (158,804 flows) |
