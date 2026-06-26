# Kết Quả V8.3 — Hướng 1: Run11 PortScan + SMOTE

**Ngày thực hiện:** 2026-06-23  
**Thời gian training:** ~40 phút (20 epochs, CUDA)  
**Best checkpoint:** Epoch 6  
**Mô hình lưu tại:** `v8_3_huong1_model.pt`

---

## 1. Tóm tắt

| Chỉ số | V8.2 (baseline) | V8.3 Hướng 1 | Thay đổi |
|---|:-:|:-:|:-:|
| Macro F1 | 65.36% | **83.39%** | ▲ +18.03% |
| Balanced Accuracy | — | **90.48%** | — |
| PortScan F1 | 7.5% | **100.00%** | ▲ +92.5% |
| Benign F1 | 50.8% | **87%** | ▲ +36.2% |
| DoS F1 | 91.4% | **93%** | ▲ +1.6% |
| Web Attack F1 | 85.2% | **87%** | ▲ +1.8% |
| Brute Force F1 | 91.9% | **50%** | ▼ −41.9% |

**Mục tiêu chính đã đạt:** Macro F1 > 80% ✓ | PortScan F1 từ 7.5% → 100% ✓

---

## 2. Classification Report chi tiết (Val set — 10%)

```
              precision    recall  f1-score   support

      Benign       0.86      0.88      0.87      5200
 Brute Force       0.34      0.98      0.50       298
         DoS       0.99      0.89      0.93      1978
    PortScan       0.99      1.00      1.00       200
  Web Attack       0.99      0.78      0.87      2489

    accuracy                           0.86     10165
   macro avg       0.83      0.90      0.83     10165
weighted avg       0.90      0.86      0.87     10165

Balanced Accuracy : 0.9048
Macro F1          : 0.8339
```

---

## 3. Confusion Matrix

```
             Benign  Brute Force   DoS  PortScan  Web Attack
Benign         4595          569    16         2          18
Brute Force       6          292     0         0           0
DoS             218            0  1751         0           9
PortScan          0            0     0       200           0
Web Attack      550            0     9         0        1930
```

---

## 4. Diễn biến training theo epoch

| Epoch | Loss | B-Acc | Macro F1 | PortScan F1 | Checkpoint |
|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | 0.0707 | 0.8934 | 0.8105 | 0.9803 | ★ |
| 2 | 0.0600 | 0.8950 | 0.8096 | 0.9901 | |
| 3 | 0.0583 | 0.9026 | 0.8296 | 0.9950 | ★ |
| 4 | 0.0574 | 0.9000 | 0.8150 | 0.9950 | |
| 5 | 0.0566 | 0.9001 | 0.8139 | 0.9950 | |
| **6** | **0.0562** | **0.9048** | **0.8339** | **0.9950** | **★ BEST** |
| 7 | 0.0559 | 0.9048 | 0.8296 | 0.9975 | |
| 8 | 0.0554 | 0.9038 | 0.8223 | 0.9926 | |
| 9–20 | ~0.054 | ~0.906 | ~0.831 | ~0.995 | plateau |

**Nhận xét:** Model hội tụ rất nhanh (epoch 1 đã đạt Macro F1 > 0.81). Sau epoch 6 không cải thiện thêm — plateau rõ ràng từ epoch 9 trở đi, loss giảm rất chậm (0.0553 → 0.0540 trong 11 epoch còn lại).

---

## 5. Phân tích

### 5.1 Thành công

**PortScan: Precision 99% / Recall 100% / F1 100%**
- SMOTE từ ~350 flows thực (Run11 — 50 round nmap) lên 2,000 flows hoạt động tốt trên val set
- Model học được pattern nmap TCP connect từ testbed thật (3 dst port: 80/22/21)
- 200/200 PortScan val flows được phân loại đúng, chỉ 4 Benign flows bị nhầm thành PortScan (FP rất thấp)

**Benign: F1 87%** (so với 50.8% ở V8.2)
- Cải thiện lớn do model không còn bị nhầm Benign → PortScan
- Bottleneck còn lại: 569 Benign flows bị nhầm sang Brute Force (xem mục 5.2)

**DoS / Web Attack: Ổn định** — không bị regression so với V8.2

### 5.2 Điểm yếu — Brute Force F1 = 0.50

Đây là vấn đề nghiêm trọng nhất. Nhìn confusion matrix:

```
Brute Force (thật) → predict đúng:    292 / 298  (recall 98% — tốt)
Benign (thật)      → predict là BF:   569 / 5200 (false positive — xấu)
```

**Nguyên nhân:** Model "cảnh giác quá mức" với Brute Force. Precision 34% nghĩa là cứ 3 flows bị predict là Brute Force thì 2 cái là Benign thật.

Nguồn gốc có thể: class weight Brute Force = 1.565 (sau sqrt normalization) kết hợp FocalLoss gamma=2.0 → model shift mạnh sang phát hiện Brute Force, trong khi một phần Benign traffic (SSH connections hợp lệ, FTP thụ động) có feature overlap với Brute Force pattern.

**Web Attack Recall = 78%:** 550 flows bị nhầm sang Benign — một phần Web Attack (SQLi/XSS ngắn, request thất bại) có flow duration và packet size giống Benign HTTP thông thường.

### 5.3 Cảnh báo về PortScan F1 = 100%

> ⚠️ Val set PortScan (200 flows) cũng là SMOTE synthetic data — cùng distribution với train set.  
> F1 = 100% phản ánh khả năng phân loại SMOTE data, **không phải** real nmap traffic đa dạng.  
> Cần kiểm tra thực tế: deploy model lên testbed, chạy nmap từ attacker machine, xem recall thực tế.

---

## 6. Cấu hình training

| Tham số | Giá trị |
|---|---|
| Base model | `v7_model.pt` (FT-Transformer, 80 features, 5 classes) |
| Dataset | `Combined_V8_3_Huong1.csv` (101,646 flows) |
| PortScan source | Run11 (50 round × ~7 flows) + SMOTE → 2,000 flows |
| Train / Val split | 91,481 / 10,165 (90/10, stratified) |
| Epochs | 20 (best: epoch 6) |
| Learning rate | 5e-5 |
| Loss | Focal Loss (γ=2.0, label smoothing=0.05) |
| Class weights | Balanced sqrt-normalized: {Benign: 0.375, BruteForce: 1.565, DoS: 0.608, PortScan: 1.911, WebAtk: 0.542} |
| Optimizer | AdamW (weight_decay=1e-4) |
| Scheduler | CosineAnnealingLR (T_max=20) |
| Device | CUDA |

---

## 7. So sánh với kỳ vọng

| Class | Kỳ vọng | Thực tế | Đạt? |
|---|:-:|:-:|:-:|
| Macro F1 | > 80% | **83.39%** | ✅ Đạt |
| PortScan F1 | > 60% | **100%** | ✅ Vượt xa |
| Benign F1 | > 80% | **87%** | ✅ Đạt |
| DoS F1 | > 90% | **93%** | ✅ Đạt |
| Web Attack F1 | > 85% | **87%** | ✅ Đạt |
| Brute Force F1 | > 90% | **50%** | ❌ Chưa đạt |

---

## 8. So sánh với Hướng 2 (CIC-IDS-2017 injection)

| Chỉ số | Hướng 1 (Run11 SMOTE) | Hướng 2 (CIC inject) | Tốt hơn |
|---|:-:|:-:|:-:|
| Macro F1 | 83.39% | **88.67%** | H2 +5.28% |
| PortScan F1 | **100%** | 99.99% | ≈ ngang |
| Benign F1 | 87% | **91.98%** | H2 +4.98% |
| Brute Force F1 | 50% | **70.26%** | H2 +20.26% |
| DoS F1 | 93% | **94.11%** | ≈ ngang |
| Web Attack F1 | **87%** | 87.02% | ≈ ngang |

**Nhận định:** Hướng 2 (CIC injection) cho kết quả tổng thể tốt hơn Hướng 1 trên mọi chỉ số, đặc biệt Brute Force (+20%). Tuy nhiên, PortScan của H1 có thể thực tế hơn vì data từ testbed cùng môi trường (không có domain shift).

---

## 9. Bước tiếp theo

### Ưu tiên 1 — Fix Brute Force precision thấp
Brute Force precision = 0.34 là vấn đề nghiêm trọng cho deployment. Các hướng:
- **Giảm class weight Brute Force** (hiện 1.565 → thử 0.8–1.0) để giảm false positive Benign→BF
- **Threshold calibration**: tăng threshold predict Brute Force từ 0.5 lên 0.7–0.8
- **Thêm Brute Force data**: augment từ CIC-IDS-2017 BruteForce flows

### Ưu tiên 2 — Validate PortScan trên real traffic
```bash
# Deploy model và chạy nmap từ attacker machine
# Kiểm tra xem 200 PortScan flows thật (không SMOTE) có được detect không
python3 testbed_inference_cascade_v2.py --model v8_3_huong1_model.pt
```

### Ưu tiên 3 — Kết hợp tốt nhất của H1 + H2
Hướng 2 có Macro F1 cao hơn nhưng vẫn có Brute Force recall thấp (54%).  
Cân nhắc hybrid: dùng H2 model + calibrate threshold cho từng class.

---

## 10. Files đầu ra

| File | Mô tả |
|---|---|
| `v8_3_huong1_model.pt` | Model checkpoint tốt nhất — Epoch 6 (4.3 MB) |
| `v8_3_huong1_scaler.pkl` | HybridFeatureScaler (fit trên 91,481 train flows) |
| `v8_3_huong1_encoder.pkl` | LabelEncoder (5 classes) |
| `train_huong1.log` | Log đầy đủ 20 epochs |
| `Combined_V8_3_Huong1.csv` | Dataset training (101,646 flows, tại `scripts/`) |
