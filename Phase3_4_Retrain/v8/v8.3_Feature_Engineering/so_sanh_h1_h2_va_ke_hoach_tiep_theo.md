# So Sánh V8.3 Hướng 1 vs Hướng 2 — Và Kế Hoạch Cải Thiện Brute Force

**Ngày:** 2026-06-24

---

## 1. So sánh kết quả tổng quan

| Chỉ số | V8.2 Baseline | **Hướng 1** (Run11 SMOTE) | **Hướng 2** (CIC Inject) | Tốt hơn |
|---|:-:|:-:|:-:|:-:|
| Macro F1 | 65.4% | 83.4% | **88.7%** | H2 +5.3% |
| Balanced Accuracy | — | 90.5% | **84.3%** | H1 +6.2% |
| PortScan F1 | 7.5% | **100%** | 99.99% | ≈ ngang |
| Benign F1 | 50.8% | 87% | **92%** | H2 +5% |
| DoS F1 | 91.4% | 93% | **94.1%** | H2 +1.1% |
| Web Attack F1 | 85.2% | 87% | **87%** | ≈ ngang |
| **Brute Force F1** | **91.9%** | **50%** | **70.3%** | **H2 +20.3%** |

**Verdict tổng thể: Hướng 2 tốt hơn ở 4/6 chỉ số chính.**

---

## 2. Phân tích sâu vấn đề Brute Force

### 2.1 Cùng nguồn data — kết quả khác nhau do class weight

Cả 2 hướng đều dùng chung **Run10 Brute Force: 2,984 flows**. Không có hướng nào inject thêm BruteForce mới. Sự khác biệt F1 hoàn toàn đến từ **chiến lược class weight**:

| | Hướng 1 | Hướng 2 |
|---|:-:|:-:|
| Class weight BruteForce | **1.565** (balanced sqrt) | **1.0** (uniform) |
| BruteForce Precision | 0.34 | **1.00** |
| BruteForce Recall | **0.98** | 0.54 |
| BruteForce F1 | 0.50 | **0.70** |

```
H1 — Quá nhạy cảm:
  569 Benign flows → predict là Brute Force (false positive)
  Chỉ 6 Brute Force flows → predict là Benign (false negative)

H2 — Quá thụ động:
  1,368 Brute Force flows → predict là Benign (false negative)
  0 false positive
```

**Không có hướng nào cân bằng được precision/recall cho BruteForce — đây là vấn đề DATA, không phải hyperparameter.**

### 2.2 Tại sao Brute Force khó phân loại?

Run10 BruteForce dùng **hydra** tấn công SSH (port 22) và FTP (port 21). Đặc điểm:
- **Short flows** — hydra timeout nhanh khi bị reject (~0.1–0.5s)
- **Ít packet** — SYN → RST/timeout, không có data transfer
- **Cùng destination port** (22, 21) với Benign SSH login hợp lệ và FTP passive

→ Feature space của BruteForce **overlap lớn** với Benign TCP connections thất bại. Model không có đủ signal để phân biệt.

### 2.3 Vì sao H2 tốt hơn H1 ở BruteForce?

H2 dùng uniform class weight (1.0) nên model **không bị push quá mạnh** về phía BruteForce. Kết quả: precision hoàn hảo (1.00) nhưng recall thấp (54%). H2 tốt hơn vì precision cao hơn quan trọng hơn trong thực tế (false alarm ít hơn).

Tuy nhiên recall 54% vẫn quá thấp — **1,368 BruteForce flows thật bị bỏ qua**.

---

## 3. Nguyên nhân gốc rễ và giải pháp

### Root cause: Thiếu diversity trong BruteForce training data

| | Run10 BruteForce | CIC Tuesday BruteForce |
|---|---|---|
| Số flows | 2,984 | **13,835** |
| Công cụ | hydra | FTP-Patator (7,938) + SSH-Patator (5,897) |
| Môi trường | WSL testbed | Hardware lab (Canonical) |
| Target ports | 22, 21 | 21, 22 |
| Pattern | Uniform (1 tool) | Đa dạng (2 tools, nhiều pattern) |
| Domain | Testbed | CIC — khác distribution |

CIC Tuesday có **13,835 BruteForce flows** sẵn có, cùng định dạng với CIC PortScan đã dùng thành công trong H2. **Feature mapper đã có sẵn** (`feature_mapper.py`).

---

## 4. Khuyến nghị: Xây dựng V8.4 — Inject CIC BruteForce

### 4.1 Tại sao nên đi hướng này?

| Tiêu chí | Threshold Calibration | Tăng class weight | **Inject CIC BruteForce** |
|---|:-:|:-:|:-:|
| Fix precision thấp | Có | Không | **Có** |
| Fix recall thấp | Không | Có nhưng phá precision | **Có** |
| Rủi ro regression class khác | Thấp | Cao | Trung bình |
| Effort | 1 giờ | 30 phút (re-train) | ~3 giờ |
| Bền vững | Không | Không | **Có** |

Threshold calibration chỉ là band-aid — dịch chuyển threshold sẽ đổi precision/recall nhưng không thể cải thiện **cả hai** cùng lúc khi feature space bị overlap.

### 4.2 Kế hoạch V8.4 cụ thể

**Bước 1 — Map CIC BruteForce (30 phút):**
```python
# Dùng lại feature_mapper.py của H2, chỉ đổi input file và label
# File nguồn: Tuesday-WorkingHours.pcap_ISCX.csv
# Labels cần map: "FTP-Patator" → "Brute Force", "SSH-Patator" → "Brute Force"
# Sample: 5,000 flows (2,500 FTP-Patator + 2,500 SSH-Patator)
```

**Bước 2 — Xây dataset V8.4 (15 phút):**
```
Dataset V8.4 = H2 dataset (loại bỏ Run10 BruteForce 2,984 flows)
             + CIC BruteForce (5,000 flows mapped)
             + CIC PortScan (5,000 flows — giữ nguyên từ H2)
Tổng ước tính: ~104,000 flows

Thay Run10 BF bằng CIC BF vì:
- CIC BF có nhiều pattern hơn (2 tools vs 1 tool)
- Đồng nhất về domain với CIC PortScan đã inject
- 5,000 > 2,984 → model thấy nhiều BF hơn
```

**Bước 3 — Training (40 phút):**
```python
# Base: v8_3_huong2_model.pt (Macro F1 88.7% — tốt nhất hiện tại)
# lr: 2e-5 (thấp hơn H2 vì chỉ cần fine-tune BruteForce)
# Epochs: 25
# Class weights: Uniform (1.0) — giống H2, đã cho precision tốt
# Hoặc: BruteForce weight = 1.2 (tăng nhẹ để cải thiện recall mà không phá precision)
```

**Kỳ vọng kết quả V8.4:**

| Class | H2 (hiện tại) | V8.4 kỳ vọng |
|---|:-:|:-:|
| Macro F1 | 88.7% | **> 88%** |
| BruteForce Precision | 100% | > 85% |
| BruteForce Recall | 54% | **> 75%** |
| BruteForce F1 | 70.3% | **> 80%** |
| PortScan F1 | 99.99% | > 99% |
| Benign F1 | 92% | > 90% |

---

## 5. Tóm tắt quyết định

```
Nên tiếp tục từ: Hướng 2 (H2 model làm base)
Phương pháp:     Inject CIC BruteForce (giống cách H2 inject CIC PortScan)
Mục tiêu:        BruteForce F1 > 80%  |  Macro F1 > 88%
Tên:             V8.4
```

**Lý do không dùng H1 làm base:**
- H1 Brute Force precision chỉ 0.34 — quá nhiều false alarm
- H2 đã có Macro F1 tốt hơn 5.3%, làm base tốt hơn
- H1 PortScan dùng SMOTE (có thể kém đa dạng hơn CIC real data)

---

## 6. Rủi ro V8.4

| Rủi ro | Mức độ | Biện pháp |
|---|:-:|---|
| Domain shift CIC BF → testbed BF pattern khác | Trung bình | Giữ lại 1,000 Run10 BF flows cùng với CIC BF |
| Benign bị mis-classify tăng do CIC BF pattern overlap | Thấp | Benign của CIC và testbed rất khác nhau ở port pattern |
| Regression PortScan / DoS / WebAttack | Thấp | Fine-tune từ H2 với lr thấp |
