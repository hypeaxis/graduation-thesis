# Tổng Hợp Kết Quả Tất Cả Versions — IDS FT-Transformer

**Ngày cập nhật:** 2026-06-24  
**Mục tiêu:** Macro F1 > 90% | BruteForce F1 > 85% | PortScan F1 > 95%

---

## 1. Bảng so sánh tổng quan

| Version | Macro F1 | B-Acc | Benign | BruteForce | DoS | PortScan | Web Attack |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **V8.2** *(baseline)* | 65.4% | — | 50.8% | 91.9% | 91.4% | 7.5% | 85.2% |
| **V8.3 H1** *(Run11+SMOTE)* | 83.4% | 90.5% | 87% | 50% | 93% | **100%** | 87% |
| **V8.3 H2** *(CIC PortScan)* | 88.7% | 84.3% | 92% | 70.3% | 94.1% | **100%** | 87% |
| **V8.4** *(CIC BruteForce)* | 94.95%† | 93.84%† | 93% | 100%† | 94% | **100%** | 87% |
| **V8.5** *(Combined)* | **91.7%** | **91.1%** | **91%** | **86%** | **93%** | **100%** | **88%** |

> † V8.4: val BruteForce = 100% CIC Patator (same-domain) → metric bị inflate, không đáng tin cậy.  
> V8.5: val set mixed domain → metric phản ánh thực tế.

---

## 2. Tiến trình cải thiện BruteForce và PortScan

```
BruteForce F1:
  V8.2  ████████████████████████░░░░░░  91.9%  (baseline — nhưng PortScan rất tệ)
  V8.3H1 █████████████░░░░░░░░░░░░░░░░  50%    (class weight quá cao → FP tăng)
  V8.3H2 ██████████████████░░░░░░░░░░░  70.3%  (uniform weight → recall chỉ 54%)
  V8.4  ████████████████████████████░░  100%†  (CIC-only val → overfit domain)
  V8.5  ██████████████████████░░░░░░░░  86%    ← REAL metric, mixed val

PortScan F1:
  V8.2  ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░  7.5%   (WSL blind spot — không detect được)
  V8.3H1 ████████████████████████████░░  100%   (Run11 SMOTE)
  V8.3H2 ████████████████████████████░░  100%   (CIC PortScan inject)
  V8.4  ████████████████████████████░░  100%   (duy trì)
  V8.5  ████████████████████████████░░  100%   (duy trì)
```

---

## 3. Chi tiết BruteForce qua các versions

| Version | Val BF Source | Support | Precision | Recall | F1 | Ghi chú |
|---|---|:-:|:-:|:-:|:-:|---|
| V8.2 | Run10 hydra | ~300 | — | — | 91.9% | Chưa có PortScan data |
| V8.3 H1 | Run10 hydra | 298 | 0.34 | **0.98** | 50% | Class weight quá cao → FP nhiều |
| V8.3 H2 | Run10 hydra | 298 | **1.00** | 0.54 | 70.3% | Uniform weight → bỏ sót nhiều |
| V8.4 | CIC Patator only | 500 | **1.00** | **1.00** | **100%†** | ⚠️ Same-domain overfit |
| **V8.5** | **Mixed hydra+Patator** | **798** | **0.83** | **0.90** | **86%** | ✅ Đáng tin cậy nhất |

---

## 4. Lịch sử phát triển và bài học

### V8.2 → V8.3 H1: Giải quyết PortScan (WSL blind spot)
- **Vấn đề:** PortScan F1 = 7.5% vì WSL chỉ capture ~7 flows/round
- **Giải pháp:** Run11 — 50 rounds nmap + SMOTE → 2,000 flows
- **Kết quả:** PortScan 7.5% → 100% ✓
- **Trade-off:** BruteForce giảm 91.9% → 50% do class weight 1.565 quá cao

### V8.3 H2: CIC PortScan injection
- **Cải tiến:** CIC-IDS-2017 Friday PortScan (5,000 real flows) thay SMOTE
- **Kết quả:** Macro F1 88.7%, Benign 92%, BruteForce 70.3%
- **Bài học:** Data thật > SMOTE về độ đa dạng; uniform class weight (1.0) tốt hơn overweighting cho BF

### V8.4: CIC BruteForce injection
- **Vấn đề:** H2 BruteForce recall chỉ 54% — bỏ sót quá nhiều
- **Giải pháp:** Thay Run10 hydra (2,984) bằng CIC FTP+SSH Patator (4,999)
- **Kết quả:** Macro F1 94.95%, BF F1 100% trên val
- **Bài học:** ⚠️ Val set = 100% CIC Patator → không test được hydra generalization

### V8.5: Combined + Anti-Overfit
- **Vấn đề:** V8.4 val set không có hydra → F1 bị inflate
- **Giải pháp:** Mix Run10 hydra (2,984) + CIC Patator (4,999) = 7,983 BF flows
- **Kết quả:** BF P=83%/R=90%/F1=86% — metric đáng tin cậy nhất
- **Bài học:** Val set diversity quan trọng hơn val set "dễ" → metric cao hơn nhưng không thật

---

## 5. Phân tích bottleneck còn lại (V8.5)

### Web Attack Recall = 81% (489 flows miss → Benign)
- **Pattern miss:** SQLi ngắn thất bại, XSS curl một request, HTTP error nhanh
- **Overlap với Benign:** Flow duration ngắn + ít packet + HTTP port → giống Benign HTTP thường
- **Tỉ lệ miss:** V8.2=14.8%, H2=21.7%, V8.4=19.2%, V8.5=18.1% → cải thiện rất chậm
- **Giải pháp tiềm năng:** Thêm CIC Thursday Infiltration hoặc dùng ensemble với rule-based WebAttack detector

### Benign FP = 224 flows bị mis-classify (151→BF + 73→WA)
- **Nguyên nhân:** SSH/FTP connections ngắn bị nhầm BruteForce; HTTP error responses bị nhầm WebAttack
- **Mức độ:** 224/5200 = 4.3% false alarm rate — chấp nhận được cho production IDS

---

## 6. Khuyến nghị cho luận văn

### Model nên dùng
**V8.5** là lựa chọn chính thức:
- Metric đáng tin cậy (mixed-domain val set)
- BruteForce P=83%/R=90% là con số có thể defend được trong báo cáo
- WebAttack 88% và PortScan 100% đã đạt threshold tốt

**V8.4** nên đề cập là "upper bound / best-case scenario":
- Macro F1 94.95% khi test trong điều kiện ideal (same-domain)
- Cần ghi rõ caveat về val set homogeneity

### Điểm cần nhấn mạnh
1. **Hành trình giải quyết PortScan WSL blind spot** — từ 7.5% → 100% qua 3 bước (Run11 → SMOTE → CIC real data)
2. **Tầm quan trọng của domain diversity trong val set** — V8.4 vs V8.5 là ví dụ điển hình
3. **Trade-off Precision/Recall cho BruteForce** — H1/H2/V8.4/V8.5 mỗi version chọn điểm khác nhau trên đường PR curve

---

## 7. Bảng files và models

| Version | Model file | Macro F1 | Dùng cho |
|---|---|:-:|---|
| V8.2 | `archive_v5_focal/` | 65.4% | Baseline reference |
| V8.3 H1 | `huong1_tang_scan_rounds/v8_3_huong1_model.pt` | 83.4% | Minh họa SMOTE approach |
| V8.3 H2 | `huong2_inject_cic_portscan/v8_3_huong2_model.pt` | 88.7% | CIC injection milestone |
| V8.4 | `v8.4_BruteForce_Fix/v8_4_model.pt` | 94.95%† | Best-case scenario |
| **V8.5** | **`v8.5_Combined/v8_5_model.pt`** | **91.7%** | **Model chính thức** |

---

## 8. Kết luận

Quá trình từ V8.2 → V8.5 giải quyết được 2 vấn đề cốt lõi của hệ thống IDS trên WSL testbed:

1. **PortScan detection** (7.5% → 100%): WSL không capture được nmap flows trực tiếp → inject CIC real hardware data làm surrogate. Bài học: khi môi trường lab có hardware limitation, external dataset injection là viable solution.

2. **BruteForce F1 ổn định** (dao động 50–91% → 86% reliable): Khó khăn chính là sự overlap feature giữa hydra BruteForce (SSH/FTP authentication timeout) và Benign traffic. Mixed dataset (testbed + CIC Patator) cho kết quả cân bằng nhất ở P=83%/R=90%.

**Điểm yếu chưa giải quyết:** Web Attack recall 81% — các WebAttack payload ngắn/thất bại có flow features gần với Benign HTTP, cần approach khác (rule-based hybrid hoặc payload inspection).
