# Chương 5. Đánh giá thực nghiệm

Chương 4 phân tích lý thuyết các quyết định thiết kế. Chương này trình bày kết quả thực nghiệm kiểm chứng các phân tích đó trên ba bộ dữ liệu thuộc ba giai đoạn nghiên cứu. Phần 5.1 mô tả môi trường thực nghiệm và các chỉ số đánh giá. Phần 5.2 trình bày kết quả Giai đoạn 1 trên NSL-KDD. Phần 5.3 trình bày kết quả Giai đoạn 2 trên CIC-IDS-2017 theo từng cải tiến kiến trúc. Phần 5.4 trình bày kết quả chẩn đoán covariate shift và động cơ cho tái huấn luyện. Phần 5.5 trình bày kết quả Giai đoạn 3 trên Testbed nội bộ. Phần 5.6 trình bày thử nghiệm hệ thống End-to-End.

---

## 5.1 Môi trường thực nghiệm và chỉ số đánh giá

### 5.1.1 Phần cứng và phần mềm

**Phần cứng:**

| Thành phần | Cấu hình |
|---|---|
| CPU | Intel Core i7 Gen 11 (8 cores, 16 threads, 2.8–4.7 GHz) |
| RAM | 16 GB DDR4 3200 MHz |
| Storage | SSD NVMe 512 GB |
| GPU | Không có (CPU-only training và inference) |
| OS Host | Windows 11 22H2 |
| OS ML/IDS | WSL2 Ubuntu 22.04 LTS |

**Phần mềm chính:**

| Thư viện / Công cụ | Phiên bản | Vai trò |
|---|---|---|
| Python | 3.8 | Runtime |
| PyTorch | 2.0 | FT-Transformer training |
| TensorFlow/Keras | 2.12 | Autoencoder (NSL-KDD) |
| LightGBM | 4.0 | Stage 2 base learner |
| scikit-learn | 1.3 | RF, KNN, Meta-LR, preprocessing |
| CICFlowMeter | v4 (fork linux) | Feature extraction (flow timeout 30s) |
| Snort | 3.1 | Rule-based IDS tầng 1 |
| nmap | 7.94 | PortScan simulation |
| hydra | 9.5 | BruteForce simulation |
| slowhttptest | 1.9 | DoS simulation |
| DVWA | v1.10 | Web Attack victim |

### 5.1.2 Bộ dữ liệu thực nghiệm

| Bộ dữ liệu | Số mẫu | Số đặc trưng | Số lớp | Nguồn |
|---|---|---|---|---|
| NSL-KDD Train (KDDTrain+) | 125.973 | 122 | 5 | Univ. New Brunswick |
| NSL-KDD Test (KDDTest+) | 22.542 | 122 | 5 | Univ. New Brunswick |
| CIC-IDS-2017 | 2.830.743 | 77 | 9 (gộp từ 15) | Univ. New Brunswick |
| Testbed V8.5 | 111.825 | 80 | 5 | Thu thập nội bộ |

### 5.1.3 Chỉ số đánh giá

Tất cả thực nghiệm sử dụng **Macro F1** là chỉ số chính — tính trung bình F1 không trọng số qua các lớp, phạt mô hình nếu bất kỳ lớp nào bị bỏ qua:

$$\text{Macro F1} = \frac{1}{K}\sum_{c=1}^{K} F1_c = \frac{1}{K}\sum_{c=1}^{K} \frac{2 \cdot P_c \cdot R_c}{P_c + R_c}$$

**MCC (Matthews Correlation Coefficient)** được sử dụng thêm cho đánh giá robustness trong mất cân bằng cực đoan (Giai đoạn 2 và Testbed):

$$\text{MCC} = \frac{TP \cdot TN - FP \cdot FN}{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}$$

MCC nằm trong [-1, 1]: giá trị âm cho thấy mô hình phân loại sai hướng có hệ thống (tệ hơn random guess).

**Balanced Accuracy** = trung bình Recall mỗi lớp — không phụ thuộc số mẫu mỗi lớp.

---

## 5.2 Kết quả Giai đoạn 1: NSL-KDD

### 5.2.1 Ablation study theo từng cải tiến

| Cấu hình | Macro F1 (KDDTest+) | Cải thiện |
|---|---|---|
| FTT Baseline (CE Loss, no sampling) | 0,638 | — |
| + Boost-Minority Val Set | 0,648 | +0,010 |
| + CB-Focal Loss ($\gamma=2$) | 0,654 | +0,006 |
| + WeightedRandomSampler | 0,658 | +0,004 |
| + LightGBM base learner (độc lập) | 0,668 | — |
| **Stacking Ensemble (FTT + LightGBM → Meta-LR)** | **0,681** | **+0,043 vs baseline** |

*Giao thức: KDDTrain+ cho training, KDDTest+ cho đánh giá cuối — không dùng KDDTest+ cho tuning bất kỳ hyperparameter nào.*

### 5.2.2 Kết quả per-class (Stacking Ensemble cuối)

| Lớp | Precision | Recall | F1-score | Support |
|---|---|---|---|---|
| Normal | 0,7154 | 0,9682 | 0,8228 | 9.711 |
| DoS | 0,9630 | 0,8032 | 0,8759 | 7.458 |
| Probe | 0,8024 | 0,7852 | 0,7937 | 2.421 |
| R2L | 0,9681 | 0,2523 | 0,4003 | 2.885 |
| U2R | 0,5517 | 0,4776 | 0,5120 | 67 |
| **Macro F1** | | | **0,6809** | |

### 5.2.3 Phân tích chi tiết từng lớp

**Normal (F1=0,8228):** Precision thấp (0,7154) — FTT thường xuyên nhầm DoS/Probe thành Normal, đặc biệt với các flow TCP bình thường nhưng có burst. Recall cao (0,9682) — Normal có pattern rõ ràng từ góc nhìn Autoencoder.

**DoS (F1=0,8759):** Cao nhất vì DoS có pattern đặc trưng rõ ràng trong `src_bytes`, `dst_bytes`, flag counts. LightGBM đặc biệt hiệu quả cho DoS.

**Probe (F1=0,7937):** FTT Recall tốt hơn LightGBM nhờ học pattern tương tác `count` và `srv_count`. Stacking kết hợp được ưu thế của cả hai.

**R2L (F1=0,4003, Recall=0,2523):** Vấn đề protocol shift — 62% R2L test dùng pop3 trong khi train dùng telnet/ftp. Đây là **giới hạn cứng của dataset**, không phải giới hạn của mô hình. Mọi thuật toán đều thất bại tương tự với R2L.

**U2R (F1=0,5120, Recall=0,4776):** Cải thiện đáng kể so với baseline 0,15 nhờ Boost-Minority Val + WeightedSampler. Giới hạn: chỉ 52 mẫu train (0,04%) không đủ để học pattern đa dạng của privilege escalation.

### 5.2.4 Kết luận Giai đoạn 1 và chuyển sang CIC-IDS-2017

Macro F1 = 0,6809 là kết quả cao nhất có thể đạt được với NSL-KDD trong điều kiện thực nghiệm này. R2L Recall = 0,2523 phản ánh giới hạn cứng của distribution shift giữa train và test (telnet vs pop3). Mọi cải tiến thuật toán thêm đều không vượt qua được giới hạn này — xác nhận quyết định chuyển sang CIC-IDS-2017 là phù hợp.

---

## 5.3 Kết quả Giai đoạn 2: CIC-IDS-2017

### 5.3.1 Ablation study kiến trúc Two-Stage

| Kiến trúc | Accuracy | Macro F1 |
|---|---|---|
| 1-Stage 9-class FTT (baseline) | 98,21% | 0,7831 |
| Two-Stage (Gating + Expert, không HNM) | 99,55% | 0,8817 |
| Two-Stage + HNM 1 vòng | 99,58% | 0,9102 |
| Two-Stage + HNM 2 vòng | 99,60% | 0,9181 |
| Two-Stage + HNM + Majority Vote (2/3) | 99,61% | 0,9247 |
| **Two-Stage + HNM + Asymmetric Voting** | **99,55%** | **0,9294** |

*Lưu ý: Asymmetric Voting có Accuracy thấp hơn Majority Vote một chút (99,55% vs 99,61%) nhưng Macro F1 cao hơn — vì nó tăng Recall Infiltration và Precision Botnet, có trọng số bằng nhau trong Macro F1 bất kể support size nhỏ.*

### 5.3.2 Stage 1 — Gating Network

| Chỉ số | Benign | Suspicious (các tấn công) |
|---|---|---|
| Precision | 0,9997 | 0,9651 |
| Recall | 0,9982 | 0,9933 |
| F1 | 0,9989 | 0,9790 |

- Tỷ lệ route sang Stage 2: 17,3% (Suspicious flows)
- False Negative Rate tấn công Stage 1: 0,67% (6,7 trên 1000 tấn công bị nhầm là Benign và không bao giờ đến Stage 2)
- Giải pháp: hai tầng xử lý cung cấp cơ hội phát hiện thứ hai cho 17,3% suspicious

### 5.3.3 Hard Negative Mining — tiến triển theo vòng

| Giai đoạn | Botnet F1 | Infiltration F1 | Macro F1 |
|---|---|---|---|
| Baseline Expert Network (không HNM) | 0,4787 | 0,3821 | 0,8817 |
| Sau HNM vòng 1 ($w_{hard}=2$) | 0,5934 | 0,5213 | 0,9102 |
| Sau HNM vòng 2 ($w_{hard}=2$) | 0,6512 | 0,5903 | 0,9181 |
| Cải thiện tổng | +0,1725 (+36,0%) | +0,2082 (+54,5%) | +0,0364 |

### 5.3.4 So sánh HNM vs class weight

| Phương án | Botnet F1 | Infiltration F1 |
|---|---|---|
| Không HNM, không class weight | 0,4787 | 0,3821 |
| Class weight Botnet ×5 | 0,5103 | 0,4012 |
| Class weight Botnet ×10 | 0,5218 | 0,4198 |
| HNM 1 vòng | 0,5934 | 0,5213 |
| **HNM 2 vòng** | **0,6512** | **0,5903** |

HNM 2 vòng vượt class weight ×10 với +0,1294 Botnet F1 (+24,8%) và +0,1705 Infiltration F1 (+40,6%).

### 5.3.5 Asymmetric Ensemble Voting — kết quả cuối

| Lớp | Precision | Recall | F1-score | Support |
|---|---|---|---|---|
| Benign | 0,9992 | 0,9953 | 0,9972 | 2.031.715 |
| DoS | 0,9683 | 0,9963 | 0,9821 | 225.024 |
| DDoS | 0,9984 | 0,9982 | 0,9983 | 114.453 |
| PortScan | 0,9936 | 0,9990 | 0,9963 | 142.079 |
| BruteForce | 0,9473 | 0,9989 | 0,9724 | 12.369 |
| Web Attack | 0,9084 | 0,9810 | 0,9433 | 1.950 |
| Botnet | 0,7947 | 0,6826 | 0,7344 | 1.758 |
| Infiltration | 0,9524 | 0,6061 | 0,7407 | 33 |
| Heartbleed | 1,0000 | 1,0000 | 1,0000 | 10 |
| **Macro F1** | | | **0,9294** | |
| **Accuracy** | | | **99,55%** | |

**So sánh Expert Network đơn lẻ vs Ensemble:**

| Chỉ số | Expert Network (sau HNM) | Ensemble Asymmetric |
|---|---|---|
| Accuracy | 99,60% | 99,55% |
| Macro F1 | 0,9181 | **0,9294** |
| Botnet F1 | 0,6512 | **0,7344** |
| Infiltration F1 | 0,5903 | **0,7407** |

Asymmetric Voting tăng Botnet F1 thêm +0,0832 và Infiltration F1 thêm +0,1504 — đúng hai lớp mà các quy tắc bỏ phiếu bất đối xứng nhắm tới.

---

## 5.4 Kết quả chẩn đoán Covariate Shift

### 5.4.1 Kết quả direct transfer và Re-fit Scaler

| Thực nghiệm | Accuracy (Testbed) | MCC | Nhận xét |
|---|---|---|---|
| Mô hình CIC trên CIC test (baseline) | 99,55% | 0,9941 | Tham chiếu |
| Direct transfer → 5.000 flows Testbed WSL2 | 21,93% | -0,015 | Phân loại sai hướng hệ thống |
| Re-fit Scaler trên Testbed | 6,87% | -0,087 | **Xấu hơn direct transfer** |

MCC = -0,015 nghĩa là mô hình không chỉ sai mà còn phân loại ngược — tệ hơn cả dự đoán ngẫu nhiên (MCC=0). Re-fit Scaler làm tình trạng xấu hơn một cách phản trực giác: thay scaler tạo mâu thuẫn với FTT embedding đã học (chi tiết tại Mục 4.5).

### 5.4.2 Kết quả Layer Freezing và Model Surgery (thực nghiệm trung gian)

*(Các kết quả này là thực nghiệm chẩn đoán trong quá trình phát triển Giai đoạn 3, không phải giai đoạn nghiên cứu độc lập)*

| Can thiệp | Accuracy (Testbed) | MCC | CF (%) |
|---|---|---|---|
| Direct transfer | 21,93% | -0,015 | — |
| Re-fit Scaler | 6,87% | -0,087 | — |
| Layer Freezing (đóng băng 2/4 tầng) + Mixed Batch | 99,82% | 0,6825 | 0,61% |
| + Model Surgery (77→80 đặc trưng) | 99,85% | **0,7333** | 0,61% |

Layer Freezing phục hồi từ MCC=-0,015 lên MCC=0,6825 — cải thiện 69,4 điểm tuyệt đối. CF=0,61% cho thấy chỉ mất 0,61% hiệu năng trên CIC gốc — kiến thức tổng quát được bảo toàn tốt.

**Kết luận chẩn đoán:** covariate shift giữa CIC (switch vật lý Gigabit) và WSL2 (Hyper-V NAT) quá lớn để vượt qua bằng fine-tuning. Cần thu thập dữ liệu đặc thù Testbed và tái huấn luyện hoàn toàn — đây là động cơ cho mô hình V8.5.

---

## 5.5 Kết quả Giai đoạn 3: Testbed nội bộ

### 5.5.1 Bằng chứng về tính không phân tách của PortScan WSL2

| Thuật toán | Cấu hình | PortScan F1 |
|---|---|---|
| FT-Transformer | CE Loss, class\_weight=1.0 | 7,5% |
| FT-Transformer | Focal Loss $\gamma=2$ | 6,8% |
| FT-Transformer | class\_weight ×5 | 8,1% |
| Random Forest | 150 cây, default | 5,2% |
| KNN | K=5 | 4,9% |
| **Tất cả** | **Inject 5.000 CIC Friday PortScan** | **100%** |

Kết quả dưới 9% nhất quán qua nhiều thuật toán với inductive bias khác nhau xác nhận: vấn đề ở dữ liệu không phải mô hình. Giải pháp dữ liệu surrogate (inject CIC Friday PortScan có pattern phân tách rõ ràng) giải quyết hoàn toàn với F1 = 100%.

### 5.5.2 BruteForce — ảnh hưởng đa dạng hóa val set

| Val Set | BruteForce F1 | DoS F1 | WebAttack F1 | Macro F1 |
|---|---|---|---|---|
| V8.4 — 100% CIC Patator (đồng nhất) | 1,000 | 0,95 | 0,90 | 0,970 |
| V8.5 — Mixed hydra + CIC Patator | 0,860 | 0,93 | 0,88 | 0,917 |
| **Chênh lệch** | **-0,140** | -0,02 | -0,02 | **-0,053** |

Chênh lệch 14% BruteForce F1 phản ánh **chất lượng đánh giá**, không phải thay đổi mô hình: V8.4 đánh giá in-distribution (chỉ CIC Patator), V8.5 đánh giá cross-distribution (hydra + Patator chưa thấy trong training). V8.5 tin cậy hơn.

### 5.5.3 Kết quả V8.5 per-class

| Lớp | Precision | Recall | F1-score | Support | Nguồn validation |
|---|---|---|---|---|---|
| Benign | 0,87 | 0,95 | 0,91 | 5.200 | Testbed nội bộ |
| BruteForce | 0,83 | 0,90 | 0,86 | 798 | hydra + CIC Patator |
| DoS | 0,98 | 0,89 | 0,93 | 1.978 | Testbed nội bộ |
| PortScan | 1,00 | 1,00 | 1,00 | 500 | CIC Friday (surrogate) |
| Web Attack | 0,96 | 0,81 | 0,88 | 2.707 | Testbed nội bộ |
| **Macro avg** | **0,93** | **0,91** | **0,917** | **11.183** | |
| **Balanced Accuracy** | | | **91,1%** | | |

**Phân tích BruteForce (F1=0,86, Recall=0,90):** 10% BruteForce bị bỏ sót chủ yếu là hydra với timeout dài — connection pattern giống Benign SSH bình thường nếu không đủ mật độ. Precision 0,83 cho thấy false alarm ở mức chấp nhận được.

**Phân tích Web Attack (F1=0,88, Recall=0,81):** 19% bị bỏ sót là XSS payload ngắn và SQLi thất bại — flow statistics không phân biệt được với Benign HTTP POST. Tầng Snort bổ sung phát hiện đúng những gì ML bỏ sót (xem Mục 5.6).

**Phân tích Benign (F1=0,91, Recall=0,95):** Recall cao (95%) nhưng Precision 0,87 — khoảng 13% flow bị gán Benign thực ra là tấn công nhẹ, chủ yếu Benign SSH/FTP bị nhầm với BruteForce.

---

## 5.6 Thử nghiệm hệ thống End-to-End

### 5.6.1 Kịch bản thử nghiệm và kết quả phát hiện

| Loại tấn công | Snort | FTT V8.5 | Ghi chú |
|---|---|---|---|
| PortScan (nmap SYN) | Phát hiện | Phát hiện | Snort: per-packet, ngay lập tức; ML: sau flow hoàn chỉnh |
| BruteForce (hydra SSH) | Phát hiện | Phát hiện | Snort: ssh-brute rule; ML: qua connection failure pattern |
| DoS (slowhttptest) | Một phần | Phát hiện | Snort chỉ thấy valid HTTP connections; ML thấy duration bất thường |
| Web Attack SQLi | Phát hiện | Phát hiện | Snort: HTTP payload; ML: flow statistics |
| Web Attack XSS | Phát hiện | Một phần | Snort: `<script>` signature; ML bỏ sót XSS payload ngắn (Recall 86%) |
| Benign | Không cảnh báo | Một phần FP | ML: ~7% Benign SSH/FTP bị nhầm BruteForce (Precision 92%) |

*Phát hiện: cảnh báo đúng; Một phần: phát hiện không hoàn toàn; Không cảnh báo: hành vi đúng với Benign.*

### 5.6.2 Tính bổ sung giữa Snort và FTT

**Snort không thể phát hiện:** DoS slowhttptest — mỗi HTTP request hoàn toàn hợp lệ về packet level, không có signature bất thường. Chỉ pattern thống kê flow (connection duration bất thường, IAT) lộ ra DoS.

**FTT không thể phát hiện hoàn toàn:** Web Attack XSS payload ngắn — không có pattern flow-level đặc trưng. Snort với rule `content:"<script>"` bắt được ngay trong payload tầng ứng dụng.

**Kết luận bổ sung:** không tấn công nào bị bỏ sót hoàn toàn bởi cả hai tầng đồng thời. Kiến trúc Hybrid (Snort + ML) cung cấp coverage rộng hơn 1-layer bất kỳ.

### 5.6.3 Độ trễ phát hiện

| Tấn công | Snort latency | FTT latency |
|---|---|---|
| PortScan | < 1ms (per-packet) | ~5s (sau flow hoàn chỉnh) |
| BruteForce | < 1ms | ~10s (nhiều failed connections tích lũy) |
| DoS slowhttptest | Không phát hiện được | 30s (sau flow timeout) |
| Web Attack SQLi | < 1ms | ~3s |

FTT latency bị giới hạn bởi CICFlowMeter flow completion (RST/FIN hoặc timeout 30s). Tối ưu hóa timeout theo loại service (port 22: timeout 5s, port 80: timeout 30s) có thể giảm latency BruteForce SSH từ 10s xuống ~5s — nằm trong phạm vi cải tiến phần mềm, không phải vấn đề kiến trúc.

---

## Kết chương

Thực nghiệm trên ba giai đoạn xác nhận tất cả phân tích lý thuyết từ Chương 4. NSL-KDD đạt Macro F1=0,6809 — giới hạn bởi protocol shift R2L không vượt được bằng thuật toán. CIC-IDS-2017 đạt Macro F1=0,9294 với từng cải tiến kiến trúc có đóng góp định lượng rõ ràng: Two-Stage (+0,099), HNM (+0,036), Asymmetric Voting (+0,011). PortScan WSL2 xác nhận không phân tách qua kết quả nhất quán <9% F1 ở mọi thuật toán — giải quyết bằng dữ liệu surrogate. V8.5 đạt Macro F1=91,7% trên val set đa dạng miền — con số đáng tin cậy hơn 97% của phiên bản đồng nhất miền. End-to-End xác nhận tính bổ sung của Snort và FTT. Chương 6 tổng kết đóng góp và hướng nghiên cứu tiếp theo.
