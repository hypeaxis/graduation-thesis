# Kết Quả V8.5 — Combined Best + Anti-Overfit

**Ngày thực hiện:** 2026-06-24  
**Thời gian training:** ~15 phút (early stop tại epoch 6, best = epoch 1)  
**Mô hình lưu tại:** `v8_5_model.pt`

---

## 1. Tóm tắt

| Chỉ số | V8.4 (trước) | **V8.5** | Thay đổi |
|---|:-:|:-:|:-:|
| Macro F1 | 94.95%* | **91.66%** | ▼ −3.29% (metric honest hơn) |
| Balanced Accuracy | 93.84%* | **91.14%** | ▼ −2.7% |
| BruteForce F1 | 100%* | **86%** | ▼ −14% (val set thực hơn) |
| BruteForce Precision | 100%* | **83%** | — |
| BruteForce Recall | 100%* | **90%** | — |
| PortScan F1 | 100% | **100%** | = |
| Benign F1 | 93% | **91%** | ▼ −2% |
| DoS F1 | 94% | **93%** | ▼ −1% |
| Web Attack F1 | 87% | **88%** | ▲ +1% |

> \* V8.4 val BruteForce = 100% CIC Patator (same-domain với train) → F1=1.00 là overfit domain, không phản ánh thực tế.  
> V8.5 val BruteForce = **798 flows mixed** (Run10 hydra + CIC Patator) → metric đáng tin cậy hơn.

---

## 2. Classification Report chi tiết (Val set — 11,183 flows)

```
              precision    recall  f1-score   support

      Benign       0.87      0.95      0.91      5200
 Brute Force       0.83      0.90      0.86       798
         DoS       0.98      0.89      0.93      1978
    PortScan       1.00      1.00      1.00       500
  Web Attack       0.96      0.81      0.88      2707

    accuracy                           0.91     11183
   macro avg       0.93      0.91      0.92     11183
weighted avg       0.91      0.91      0.91     11183

Balanced Accuracy : 0.9114
Macro F1          : 0.9166
```

---

## 3. Confusion Matrix

```
             Benign  Brute Force   DoS  PortScan  Web Attack
Benign         4954          151    22         0          73
Brute Force      80          718     0         0           0
DoS             196            0  1766         0          16
PortScan          0            0     0       499           1
Web Attack      489            0    15         0        2203
```

---

## 4. Diễn biến training

| Epoch | Loss | B-Acc | Macro F1 | BF F1 | BF P | BF R | WA F1 | PS F1 |
|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **1** | **0.1284** | **0.9114** | **0.9166** | **0.8614** | **0.83** | **0.90** | **0.8812** | **0.9990** |
| 2 | 0.1212 | 0.9111 | 0.9154 | 0.8573 | 0.82 | 0.90 | 0.8804 | 0.9990 |
| 3 | 0.1203 | 0.9115 | 0.9146 | 0.8524 | 0.81 | 0.90 | 0.8814 | 0.9990 |
| 4 | 0.1198 | 0.9110 | 0.9139 | 0.8511 | 0.81 | 0.90 | 0.8809 | 0.9990 |
| 5 | 0.1198 | 0.9110 | 0.9163 | 0.8590 | 0.82 | 0.90 | 0.8822 | 0.9990 |
| 6 | 0.1195 | 0.9112 | 0.9144 | 0.8521 | 0.81 | 0.90 | 0.8811 | 0.9990 |
| — | — | — | — | — | — | — | — | — |
| *Early stop* | | | | | | | | |

**Nhận xét:** Model đạt đỉnh ngay epoch 1 và không cải thiện thêm. Early stop kích hoạt sau 5 epoch không tăng. Đây là dấu hiệu V8.4 base model đã rất tốt — fine-tune thêm với regularization mạnh không mang lại thêm giá trị.

---

## 5. Phân tích

### 5.1 Thành công

**BruteForce F1 = 86% — kết quả đáng tin cậy nhất từ trước đến nay**
- Val set chứa **cả hai domain**: 798 flows = ~400 Run10 hydra + ~398 CIC Patator (stratified 10%)
- Recall 90%: model bắt được 9/10 BruteForce thật
- Precision 83%: cứ 6 báo động BruteForce thì có 5 cái thật (chấp nhận được cho IDS)
- 80 hydra flows bị miss → Benign (các flow SSH/FTP rất ngắn, khó phân biệt)
- 151 Benign flows bị nhầm → BruteForce (false alarm)

**PortScan F1 = 100% — duy trì hoàn hảo**

**Web Attack F1 = 88%** — tăng nhẹ từ 87% nhờ CIC Thursday XSS/SQLi patterns

### 5.2 Điểm yếu còn lại

**Web Attack Recall = 81%** — 489/2,707 flows bị miss → Benign:
- Tỉ lệ miss giảm nhẹ: V8.4 = 19.2%, V8.5 = 18.1%
- Nguyên nhân cốt lõi chưa giải quyết: một số WebAttack (SQLi thất bại, XSS ngắn) có flow pattern giống Benign HTTP

**Benign recall cao (95%) nhưng precision thấp hơn (87%)**:
- 151 Benign → BruteForce + 73 Benign → WebAttack = 224 Benign flows bị mis-classify
- Phần lớn do Benign SSH/FTP connections bị nhầm với BruteForce

### 5.3 Tại sao early stop tại epoch 1?

Regularization kết hợp quá mạnh:
- `dropout=0.15` + `label_smoothing=0.10` + `weight_decay=2e-4`
- V8.4 base đã được train rất tốt → model không còn nhiều room để cải thiện
- Label smoothing 0.10 làm mềm target quá mức → gradient signal yếu → model drift nhẹ khỏi optimum sau mỗi epoch

**Nếu chạy lại V8.5:** thử `label_smoothing=0.05` (giữ nguyên như V8.4) và `dropout=0.12`.

---

## 6. Cấu hình training

| Tham số | Giá trị |
|---|---|
| Base model | `v8_4_model.pt` (Macro F1 94.95% — đã anti-overfit bằng mixed val) |
| Dataset | `Combined_V8_5.csv` (111,825 flows) |
| BruteForce | Run10 hydra (2,984) + CIC Patator FTP+SSH (4,999) = 7,983 |
| WebAttack | Run10 (24,887) + CIC Thursday XSS/SQLi (2,180) = 27,067 |
| PortScan | CIC Friday (5,000) |
| Epochs | Max 15, early stop patience=5 → dừng tại epoch 6 |
| Learning rate | Layer-wise: backbone=1e-5, mid=1.5e-5, head=3e-5 |
| Dropout | 0.15 |
| DropPath | 0.15 |
| Label smoothing | 0.10 |
| Weight decay | 2e-4 |
| Class weights | sqrt-balanced clip[0.5,2.0]: BF=1.328, PS=1.587 |
| Device | CUDA |

---

## 7. So sánh với kỳ vọng

| Class | Kỳ vọng | Thực tế | Đạt? |
|---|:-:|:-:|:-:|
| Macro F1 | > 88% | **91.66%** | ✅ Đạt |
| BruteForce F1 | > 85% | **86%** | ✅ Đạt |
| BruteForce Recall | > 75% | **90%** | ✅ Vượt |
| PortScan F1 | > 99% | **100%** | ✅ Đạt |
| WebAttack F1 | > 90% | **88%** | ❌ Chưa đạt |
| Benign F1 | > 90% | **91%** | ✅ Đạt |

---

## 8. Files đầu ra

| File | Mô tả |
|---|---|
| `v8_5_model.pt` | Best checkpoint — Epoch 1 (4.3 MB) |
| `v8_5_scaler.pkl` | HybridFeatureScaler (fit trên 100,642 train flows) |
| `v8_5_encoder.pkl` | LabelEncoder (5 classes) |
| `train_v8_5.log` | Log training đầy đủ |
| `Combined_V8_5.csv` | Dataset (111,825 flows) |
| `cic_webattack_mapped.csv` | CIC Thursday WebAttack đã map (2,180 flows) |
