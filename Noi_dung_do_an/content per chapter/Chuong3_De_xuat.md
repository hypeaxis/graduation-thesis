# Chương 3. Phương pháp đề xuất

Chương 2 cung cấp nền tảng lý thuyết cho FT-Transformer, Focal Loss, Layer Freezing, Model Surgery và hệ thống lai ghép. Chương này trình bày chi tiết phương pháp đề xuất — cách áp dụng các kỹ thuật đó vào ba giai đoạn nghiên cứu tuần tự, mỗi giai đoạn giải quyết một giới hạn cụ thể được phát hiện từ giai đoạn trước. Phần 3.1 tổng quan kiến trúc và luồng tiến hóa ba giai đoạn. Phần 3.2 trình bày Giai đoạn 1 trên NSL-KDD. Phần 3.3 trình bày Giai đoạn 2 trên CIC-IDS-2017. Phần 3.4 trình bày Giai đoạn 3 trên Testbed nội bộ — bắt đầu bằng chẩn đoán covariate shift làm động cơ, sau đó là quy trình thu thập dữ liệu và tái huấn luyện. Phần 3.5 mô tả triển khai hệ thống End-to-End.

---

## 3.1 Tổng quan kiến trúc hệ thống

Hệ thống NIDS được xây dựng qua ba giai đoạn nghiên cứu tuần tự, mỗi giai đoạn được thúc đẩy bởi kết quả định lượng của giai đoạn trước.

**[Hình 3.1: Sơ đồ tổng thể 3 giai đoạn nghiên cứu — mũi tên nhân-quả giữa các giai đoạn; và pipeline End-to-End cuối cùng]**

**Giai đoạn 1** (Mục 3.2) xây dựng mô hình nền tảng trên NSL-KDD: kiến trúc Two-Stage (Autoencoder Gate + Stacking Ensemble), các kỹ thuật xử lý mất cân bằng cốt lõi, pipeline tiền xử lý. Kết thúc bằng phân tích định lượng giới hạn của NSL-KDD — động cơ chuyển sang CIC-IDS-2017.

**Giai đoạn 2** (Mục 3.3) tái thiết kế kiến trúc cho CIC-IDS-2017 với 9 lớp (Benign + 8 nhóm tấn công gộp từ 15 nhãn gốc). Kiến trúc Two-Stage Cascade (Gating Network + Expert Network) và Asymmetric Ensemble Voting được phát triển. Đạt Accuracy 99,55%, Macro F1 = 0,9294.

**Giai đoạn 3** (Mục 3.4) giải quyết covariate shift khi triển khai mô hình CIC sang Testbed WSL2 (sụt giảm từ 99,55% xuống 21,93% Accuracy). Thu thập dữ liệu tấn công thực và tái huấn luyện hoàn toàn mô hình V8.5, đạt Macro F1 = 91,7% trên 5 lớp.

---

## 3.2 Giai đoạn 1: Xây dựng mô hình nền tảng trên NSL-KDD

### 3.2.1 Đặc điểm bộ dữ liệu NSL-KDD và quy trình tiền xử lý

NSL-KDD là bản cải tiến của KDD Cup 1999, loại bỏ 78% bản ghi trùng lặp và cân bằng lại phân phối. Tuy nhiên vẫn là dữ liệu từ năm 1998 — không phản ánh các giao thức và tấn công hiện đại.

**Phân phối dữ liệu:**

| Tập | Tổng mẫu | Normal | DoS | Probe | R2L | U2R |
|---|---|---|---|---|---|---|
| KDDTrain+ | 125.973 | 67.343 (53,5%) | 45.927 (36,5%) | 11.656 (9,3%) | 995 (0,8%) | 52 (0,04%) |
| KDDTest+ | 22.542 | 9.711 (43,1%) | 7.458 (33,1%) | 2.421 (10,7%) | 2.885 (12,8%) | 67 (0,3%) |

*Lưu ý: Phân phối R2L thay đổi rõ rệt giữa train (0,8%) và test (12,8%) — distribution shift cấu trúc không thể giải quyết bằng thuật toán sampling.*

**41 đặc trưng raw:** 38 số thực (duration, byte counts, flag counts, v.v.) và 3 phân loại (protocol\_type, service, flag). Sau one-hot encoding: 122 chiều.

**Quy trình tiền xử lý:**
1. Label Encoding → one-hot cho 3 đặc trưng phân loại (protocol\_type: 3 giá trị, service: 70 giá trị, flag: 11 giá trị)
2. MinMaxScaler cho 38 đặc trưng số thực
3. SMOTE-ENN cho U2R (52 mẫu → tăng cường) và R2L thiểu số
4. Val Set Boost-Minority: R2L 40% vào val, U2R chỉ 5 mẫu vào val (giữ 47 mẫu cho training)

**Lý do Boost-Minority Val:** nếu U2R chỉ có 5 mẫu trong validation, checkpoint selection không phản ánh đúng hiệu năng U2R — mô hình sẽ được chọn theo Normal/DoS performance. Giữ 47/52 mẫu U2R trong training giải quyết cả hai vấn đề.

### 3.2.2 Kiến trúc Two-Stage: Autoencoder Anomaly Gate và Stacking Ensemble

**Tại sao cần Two-Stage thay vì phân loại đa lớp trực tiếp:**

Nếu phân loại 5 lớp trực tiếp, gradient bị chi phối bởi Normal (53,5%) và DoS (36,5%). U2R với 52 mẫu (0,04%) nhận gradient quá nhỏ để học pattern phân biệt. Two-Stage tách biệt hai bài toán có bản chất khác nhau: phát hiện bất thường (Stage 1) và phân loại chi tiết (Stage 2).

**[Hình 3.2: Kiến trúc Two-Stage NSL-KDD — flow → AE Gate (ngưỡng τ) → Normal thoát khỏi pipeline / Suspicious → Stage 2 Stacking Ensemble → nhãn tấn công]**

---

#### Stage 1 — Autoencoder Anomaly Gate

Autoencoder huấn luyện **chỉ trên Normal flows** theo nguyên lý unsupervised: encoder-decoder học tái tạo lưu lượng bình thường với sai số thấp. Flow tấn công có pattern khác → reconstruction error cao hơn.

**Kiến trúc Autoencoder:**
- Encoder: 122 → 64 → 32 → 16 (ReLU activation)
- Decoder: 16 → 32 → 64 → 122 (ReLU activation)
- Loss: MSE reconstruction trên Normal flows

Sai số tái tạo:

$$\text{MSE}(\mathbf{x}) = \frac{1}{D}\sum_{i=1}^{D}(x_i - \hat{x}_i)^2 \tag{eq:ae-mse}$$

với $D = 122$ chiều. Quyết định phân loại:

$$\text{gate}(\mathbf{x}) = \begin{cases}
\text{Normal} & \text{MSE}(\mathbf{x}) < \tau \\
\text{Suspicious} & \text{MSE}(\mathbf{x}) \geq \tau
\end{cases} \tag{eq:ae-gate}$$

Ngưỡng $\tau = 0{,}008481$ được chọn tại percentile 95 của Normal train errors để tối đa hóa F1 nhị phân trên validation.

**Ưu điểm căn bản của AE Gate:** học "không gian chuẩn" của traffic bình thường mà **không cần nhãn tấn công**. Bất kỳ flow nào bị tái tạo kém là flow bất thường — kể cả tấn công chưa từng thấy trong training. Stage 1 đạt Binary Macro F1 = 0,84 và Precision = 0,93.

---

#### Stage 2 — Stacking Ensemble

Stage 2 nhận Suspicious flows và phân loại thành 4 lớp tấn công (DoS, Probe, R2L, U2R).

**[Hình 3.3: Stacking Ensemble — FTT (122 features) → p_FTT ∈ R^5 | LightGBM → p_LGB ∈ R^5 → Concat [p_FTT; p_LGB] ∈ R^10 → Meta-LR → nhãn cuối]**

**Base learner 1 — FT-Transformer:** $d=128$, 8 heads, 4 lớp Attention, $d_{ff}=512$, dropout=0,1, Focal Loss $\gamma=2$, WeightedRandomSampler. Cơ chế Attention học tương tác giữa `src_bytes`, `rerror_rate` — hiệu quả cho R2L.

**Base learner 2 — LightGBM:** 127 lá, lr=0,05, n_estimators=1000 (early stopping 50), subsample=0,8, inverse-frequency sample weights. Phân vùng đặc trưng cứng qua `logged_in` và `num_compromised` — hiệu quả cho Probe và U2R.

**Tại sao FTT và LightGBM bổ sung cho nhau:**
- FTT: R2L Recall = 0,383 vs LightGBM R2L Recall = 0,208 (Attention học pattern đa-đặc-trưng R2L tốt hơn)
- LightGBM: Probe F1 và U2R F1 cao hơn (phân nhánh đặc trưng cứng hiệu quả cho lớp nhỏ)
- Hai mô hình sai trên mẫu khác nhau → correlation thấp → ensemble hiệu quả

**Meta-learner — Logistic Regression:**

$$\hat{y} = \text{Meta-LR}\!\left([\,\mathbf{p}_\text{FTT};\;\mathbf{p}_\text{LGBM}\,]\right), \quad \mathbf{p}_\text{FTT},\,\mathbf{p}_\text{LGBM} \in \mathbb{R}^5 \tag{eq:stacking}$$

Đầu vào 10 chiều (xác suất 5 lớp × 2 base learner). Meta-LR được huấn luyện trên out-of-fold predictions để tránh leakage. Meta-LR học khi nào tin FTT hơn và khi nào tin LightGBM hơn.

### 3.2.3 Chiến lược xử lý mất cân bằng NSL-KDD

NSL-KDD có hai dạng mất cân bằng với bản chất khác nhau:

| Dạng | Lớp | Vấn đề | Giải pháp |
|---|---|---|---|
| Thiếu dữ liệu | U2R (52 mẫu) | SMOTE không đủ diversity trong 122 chiều | Boost-Minority Val + WeightedSampling |
| Distribution shift | R2L | 62% test dùng pop3 (không có trong train telnet) | Giới hạn cứng, không giải quyết được bằng sampling |

**Chiến lược tổng hợp:**
1. **Val Set Boost-Minority:** R2L 40% vào val; U2R chỉ 5 mẫu vào val (47 mẫu training)
2. **CB-Focal Loss** với $\alpha_c$ theo effective number: $\beta=0{,}9999$, $\gamma=2$
3. **WeightedRandomSampler** cho FTT: mỗi batch có đại diện của tất cả lớp
4. **Inverse-frequency weights** cho LightGBM: $w_c = N/(K \cdot n_c)$

Kết quả: U2R Recall = 0,4776 (tăng từ 0,15 baseline). R2L Recall = 0,25 — giới hạn cứng do protocol shift pop3/telnet.

### 3.2.4 Tại sao chuyển sang CIC-IDS-2017

| Giới hạn NSL-KDD | Hệ quả |
|---|---|
| Dữ liệu 1998, thiếu tấn công hiện đại | Không có DDoS, Web Attack, Botnet, BruteForce SSH/FTP |
| Chỉ 4 lớp bậc cao | Không đủ chi tiết cho SOC phân biệt DDoS vs DoS |
| R2L protocol shift (pop3 vs telnet) | Giới hạn cứng Macro F1 tại ~0,68 |
| Metric ceiling rõ ràng | Mọi cải tiến thuật toán không vượt được |

CIC-IDS-2017 giải quyết cả hai vấn đề: dữ liệu 2017 với 14 loại tấn công hiện đại và phân loại chi tiết — tạo cơ sở cho Giai đoạn 2.

---

## 3.3 Giai đoạn 2: Two-Stage Cascade NIDS trên CIC-IDS-2017

### 3.3.1 Bộ dữ liệu CIC-IDS-2017 và cấu trúc lớp

CIC-IDS-2017 thu thập trong 5 ngày (25 users, mạng thực) với **15 nhãn gốc**: Benign + 14 loại tấn công. Đề tài gộp thành **9 lớp** cho mô hình:

**Quy tắc gộp nhóm:**
```
BENIGN            → Benign
DoS Hulk
DoS GoldenEye     → DoS (cùng cơ chế: làm cạn kiệt tài nguyên web server)
DoS Slowloris
DoS Slowhttptest
DDoS              → DDoS (phân biệt với DoS: yêu cầu nhiều nguồn)
FTP-Patator       → BruteForce (cùng cơ chế: thử tuần tự credential)
SSH-Patator
PortScan          → PortScan
Web Attack-Brute Force
Web Attack-XSS    → Web Attack (cùng mục tiêu: ứng dụng web)
Web Attack-Sql Injection
Bot               → Botnet
Infiltration      → Infiltration
Heartbleed        → Heartbleed
```

**Phân phối 9 lớp sau gộp:**

| Lớp | Số flow | Tỷ lệ |
|---|---|---|
| Benign | 2.359.987 | 83,4% |
| DoS | 252.661 | 8,9% |
| DDoS | 128.025 | 4,5% |
| PortScan | 158.930 | 5,6% |
| BruteForce | 13.835 | 0,5% |
| Web Attack | 2.180 | 0,08% |
| Botnet | 1.956 | 0,07% |
| Infiltration | 36 | 0,001% |
| Heartbleed | 10 | 0,0004% |
| **Tổng** | **2.830.743** | |

*Tỷ lệ Benign:Infiltration = 65.555:1; Benign:Heartbleed = 235.999:1*

**[Hình 3.4: Phân phối 9 lớp CIC-IDS-2017 — bar chart log-scale, thể hiện khoảng cách cực đoan]**

### 3.3.2 Quy trình tiền xử lý và kỹ thuật hóa đặc trưng

**Xử lý chất lượng dữ liệu:**
- Infinity trong `Flow_Bytes/s`, `Flow_Packets/s` (khi duration=0): clip về giá trị lớn nhất hợp lệ
- NaN: loại bỏ (không impute do không biết pattern)

**PowerTransformer Yeo-Johnson:**

$$\psi_\lambda(x) = \begin{cases}
\dfrac{(x+1)^\lambda - 1}{\lambda} & \lambda \neq 0,\; x \geq 0 \\[6pt]
\ln(x + 1) & \lambda = 0,\; x \geq 0 \\[6pt]
\dfrac{-\left[(-x+1)^{2-\lambda} - 1\right]}{2-\lambda} & \lambda \neq 2,\; x < 0 \\[6pt]
-\ln(-x + 1) & \lambda = 2,\; x < 0
\end{cases} \tag{eq:yeo-johnson}$$

Tham số $\lambda$ được ước lượng bằng MLE để tối đa hóa tính xấp xỉ Gaussian.

**Tại sao Yeo-Johnson thay vì StandardScaler hay MinMaxScaler:**
- Nhiều đặc trưng CICFlowMeter có phân phối power-law (byte counts, IAT) với đuôi dài cực đoan
- StandardScaler không thay đổi phân phối — FTT vẫn học trong không gian lệch
- MinMaxScaler đưa về [0,1] nhưng không giải quyết skewness
- Yeo-Johnson đưa phân phối về xấp xỉ Gaussian → FTT học hiệu quả hơn; các lớp thiểu số không bị "chôn vùi" trong đuôi phân phối của Benign

**Lọc tương quan cao:** các đặc trưng với Pearson $r > 0{,}95$ được loại bỏ, giảm từ 77 xuống 34 đặc trưng cho Expert Network. Không lọc cho Gating Network (giữ 77 đặc trưng đầy đủ).

### 3.3.3 Tại sao kiến trúc Two-Stage Cascade

**Vấn đề với 1-Stage trực tiếp:**
Khi FTT phân loại 9 lớp đồng thời, gradient bị dominated bởi Benign (83,4%). Infiltration và Heartbleed nhận gradient quá nhỏ. Kết quả: 1-Stage đạt Accuracy 98,21% nhưng Macro F1 = 0,7831 (thấp hơn 15% so với Two-Stage cascade).

**Logic phân tầng:**
- Stage 1 (Gating): bài toán nhị phân đơn giản hơn — chỉ cần quyết định "có đáng ngờ không?"
- Stage 2 (Expert): chỉ nhận ~17,3% traffic (Suspicious flows) — gradient tập trung phân biệt **giữa các loại tấn công**, không còn phải "cạnh tranh" với 83,4% Benign

**[Hình 3.5: Two-Stage Cascade — traffic → Gating Network → Benign (82,7%) thoát | Suspicious (17,3%) → Expert Network → 9 classes]**

### 3.3.4 Tầng 1: Gating Network

FT-Transformer nhị phân với cấu hình:
- $d=128$, 4 lớp Attention, 8 heads, $d_{ff}=512$, dropout=0,2
- Đầu vào: 77 đặc trưng đầy đủ
- Loss: CB-Focal Loss ($\gamma=2$) + Weighted Sampling

**Quyết định phân loại với ngưỡng bảo thủ:**
$$\text{label} = \begin{cases}
\text{Benign} & \hat{p}_{Benign} \geq 0{,}85 \\
\text{Suspicious} & \hat{p}_{Benign} < 0{,}85
\end{cases}$$

**Lý do ngưỡng 85% (không phải 50%):** ngưỡng bảo thủ ưu tiên recall tấn công hơn giảm workload. Bỏ sót một Infiltration ở Stage 1 → vĩnh viễn không phát hiện được. Workload thêm cho Stage 2 (17% thay vì ít hơn) là chi phí chấp nhận được.

### 3.3.5 Tầng 2: Expert Network và Hard Negative Mining

Expert Network nhận Suspicious flows và phân loại thành 9 lớp (Benign giữ lại cho trường hợp Gating báo nhầm):
- $d=64$, 3 lớp Attention, 4 heads, $d_{ff}=256$, dropout=0,2
- Đầu vào: 34 đặc trưng (sau lọc tương quan cao)
- Loss: CB-Focal Loss ($\gamma=1{,}5$)

**Kết quả ban đầu (không HNM):**
- Botnet F1 = 0,4787 → Nguyên nhân: FTT nhầm Benign long-idle connection thành Botnet C2 heartbeat (FP cao)
- Infiltration F1 = 0,3821 → Nguyên nhân: FTT bỏ sót Infiltration bị phân loại sai thành Benign SSH/HTTP (FN cao)

**Hard Negative Mining (HNM) — 2 vòng:**

**[Hình 3.6: Vòng lặp HNM — huấn luyện → inference trên val → thu thập hard negatives (mẫu sai) → thêm vào train với w_hard=2.0 → huấn luyện lại]**

Sau mỗi vòng huấn luyện, thu thập mẫu bị phân loại sai trên tập validation (hard negatives). Thêm vào train với trọng số $w_{hard} = 2{,}0$:

$$\mathcal{L}_{HNM} = \sum_{i \notin \text{hard}} \mathcal{L}_{FL}(x_i) + w_{hard} \sum_{i \in \text{hard}} \mathcal{L}_{FL}(x_i)$$

| Giai đoạn | Botnet F1 | Infiltration F1 |
|---|---|---|
| Không HNM | 0,4787 | 0,3821 |
| Sau HNM vòng 1 | 0,5934 | 0,5213 |
| Sau HNM vòng 2 | **0,6512** | **0,5903** |

**Tại sao HNM hiệu quả hơn tăng class weight:** class weight tác động đồng đều lên toàn bộ lớp — kể cả mẫu đã phân loại đúng. HNM tập trung vào **vùng biên quyết định**: chỉ mẫu đang bị phân loại sai được tăng cường → mô hình học biên giới tốt hơn thay vì học phân phối lớp.

Bằng chứng: class weight ×10 cho Botnet → F1 = 0,5103; HNM 2 vòng → F1 = 0,6512 (+14% tuyệt đối so với weight).

### 3.3.6 Từ Expert Network đơn lẻ đến Asymmetric Ensemble Voting

**Phân tích confusion matrix sau HNM:**
- **Botnet:** FP cao — FTT thường xuyên nhầm Benign long-idle thành Botnet C2 heartbeat. RF và KNN ít bị lỗi này nhờ inductive bias khác.
- **Infiltration:** FN cao — FTT bỏ sót Infiltration vì flow riêng lẻ giống Benign SSH. RF với bootstrap sampling và KNN với lân cận cục bộ xử lý lớp hiếm tốt hơn.

**Tại sao ba mô hình sai trên mẫu khác nhau ($\rho$ thấp):**
- FTT: học phi tuyến qua Attention — sai trên mẫu có tương tác đặc trưng phức tạp không nhất quán
- RF (150 cây, max_depth=25, class_weight=balanced\_subsample): mắc sai trên mẫu gần biên quyết định phức tạp cao chiều
- KNN (K=16, distance-weighted): mắc sai trên mẫu trong vùng thưa (thiểu số xa training points)

Khi $\rho$ thấp: $\text{Var}(\bar{f}) = \frac{\sigma^2}{M}[1 + (M-1)\rho] \approx \frac{\sigma^2}{M}$ → ensemble giảm variance hiệu quả.

### 3.3.7 Thiết kế Asymmetric Ensemble Voting

**[Hình 3.7: Asymmetric Voting — FTT vote + RF vote + KNN vote → Luật Infiltration (OR of RF,KNN) | Luật Botnet (AND of 3) | Majority Vote (cho lớp còn lại)]**

**Quy tắc thông thường (Majority Voting):** nhãn được bầu bởi ít nhất 2/3 mô hình.

**Hai quy tắc bất đối xứng:**

1. **Ưu tiên Infiltration:** nếu RF hoặc KNN bỏ phiếu Infiltration → kết quả là Infiltration (bất kể FTT). Lý do: Infiltration chiếm 0,001% dữ liệu; bỏ sót Infiltration nghiêm trọng hơn nhiều so với false alarm. Trao đổi: tăng Recall đổi lấy giảm Precision.

2. **Đồng thuận Botnet:** kết quả là Botnet **chỉ khi** cả ba mô hình đều bỏ phiếu Botnet. Lý do: FTT thường xuyên nhầm Benign thành Botnet (FP cao gây alert fatigue). Trao đổi: tăng Precision đổi lấy giảm Recall.

**Kết quả so sánh phương án Voting:**

| Phương án | Botnet F1 | Infiltration F1 | Macro F1 |
|---|---|---|---|
| FTT đơn lẻ (sau HNM) | 0,6512 | 0,5903 | 0,9181 |
| Majority Vote (2/3) | 0,7089 | 0,6843 | 0,9247 |
| **Asymmetric Voting** | **0,7344** | **0,7407** | **0,9294** |

---

## 3.4 Giai đoạn 3: Tái huấn luyện mô hình trên Testbed nội bộ

### 3.4.1 Chẩn đoán Covariate Shift — Động cơ cho Giai đoạn 3

Trước khi triển khai lên Testbed thực, thực nghiệm chuyển giao trực tiếp được thực hiện để định lượng mức độ covariate shift.

**Thực nghiệm chuyển giao:**

| Thực nghiệm | Accuracy | MCC | Nhận xét |
|---|---|---|---|
| Mô hình CIC trên CIC test set | 99,55% | 0,9941 | Baseline |
| Direct transfer → 5.000 flows Testbed WSL2 | 21,93% | -0,015 | Tệ hơn dự đoán ngẫu nhiên |
| Re-fit PowerTransformer trên Testbed | 6,87% | -0,087 | **Xấu hơn direct transfer** |

MCC = -0,015 cho thấy mô hình không chỉ hoạt động kém mà còn phân loại **sai hướng có hệ thống**. Re-fit Scaler làm tình trạng xấu hơn: mô hình đã học embedding gắn với khoảng giá trị CIC-scaler; thay scaler mới tạo mâu thuẫn nội bộ → Accuracy xuống 6,87%.

**Nguyên nhân covariate shift:**
- Switch Gigabit vật lý (CIC) vs card mạng ảo Hyper-V (WSL): overhead ảo hóa thay đổi packet size và timing
- NAT của Windows thêm độ trễ, thay đổi ACK timing → ảnh hưởng trực tiếp IAT features và flag counts
- PowerTransformer fit trên CIC phân phối → ánh xạ sai khi áp dụng lên Testbed phân phối

**Kết luận:** không thể tái sử dụng mô hình CIC bằng bất kỳ kỹ thuật fine-tuning nào vì phân phối đặc trưng thay đổi hoàn toàn. Cần thu thập dữ liệu Testbed đủ đa dạng và tái huấn luyện hoàn toàn.

*(Lưu ý: các kết quả DA chi tiết — Layer Freezing MCC=0,6825, Model Surgery MCC=0,7333 — là các thực nghiệm trung gian trong quá trình chẩn đoán, không phải giai đoạn nghiên cứu độc lập)*

### 3.4.2 Môi trường Testbed và thu thập dữ liệu

**Cấu hình hai máy:**
- **Máy victim** (Windows 11 + WSL2 Ubuntu 22.04, IP 192.168.1.x): WSL2 Mirrored Networking — traffic LAN đến trực tiếp WSL interface, không qua NAT hoàn toàn. Cài đặt: Apache2 + DVWA (cổng 80), OpenSSH (cổng 22), vsftpd (cổng 21), Snort 3, CICFlowMeter.
- **Máy tấn công** (Kali Linux laptop, cùng WiFi): nmap, hydra, slowhttptest, hping3, curl scripts.

**[Hình 3.8: Sơ đồ Testbed — Kali Linux [tấn công] --LAN--> Router/Switch --WiFi--> Windows 11 host [WSL2 Ubuntu victim]; CICFlowMeter thu thập trên WSL interface]**

**5 lớp thu thập được:**

| Lớp | Tool | Đặc điểm |
|---|---|---|
| Benign | Browse thực tế, YouTube, GitHub | Traffic sinh hoạt tự nhiên nhiều phiên |
| BruteForce | hydra SSH/FTP, nhiều thread | TCP connections liên tiếp thất bại |
| DoS | slowhttptest, hping3 | Làm cạn tài nguyên HTTP server |
| PortScan | nmap (surrogate CIC Friday) | Xem mục 3.4.3 |
| WebAttack | curl SQLi, XSS vào DVWA | HTTP GET/POST với payload tấn công |

**4 lớp không thu thập được và lý do:**

| Lớp | Lý do không thu thập |
|---|---|
| DDoS | Cần nhiều máy tấn công phối hợp đồng thời |
| Botnet | Cần hạ tầng C2 thực và triển khai malware |
| Infiltration | Cần kịch bản đa bước với máy trung gian bị xâm phạm |
| Heartbleed | Cần OpenSSL phiên bản cụ thể cũ; chỉ 10 mẫu trong CIC không đủ để huấn luyện |

### 3.4.3 Bài toán PortScan: dữ liệu surrogate

**Vấn đề:** nmap từ Kali qua WiFi + Windows NAT → WSL interface chỉ capture được ~7 flow mỗi round scan (vs hàng trăm flow trên switch vật lý). Flow PortScan WSL trông như Benign TCP health check trong không gian CICFlowMeter.

**Bằng chứng không phân tách:**

| Cấu hình thuật toán | PortScan F1 |
|---|---|
| FTT, CE Loss, no class weight | 7,5% |
| FTT, Focal Loss $\gamma=2$ | 6,8% |
| FTT, class\_weight PortScan ×5 | 8,1% |
| Random Forest, 150 cây | 5,2% |
| KNN, K=5 | 4,9% |

Kết quả nhất quán thất bại qua nhiều thuật toán → vấn đề nằm ở **dữ liệu**, không phải mô hình.

**Giải pháp dữ liệu surrogate:** inject 5.000 flow CIC Friday PortScan (thu thập trên switch vật lý thực) vào tập train. Flow CIC PortScan có pattern rõ ràng: SYN flag cao, duration ngắn đồng nhất, byte count gần bằng 0.

**Kết quả:** PortScan F1 từ 7,5% → 100% và duy trì ổn định qua mọi phiên bản tiếp theo.

### 3.4.4 Bài toán BruteForce: đa dạng hóa tập kiểm định

**Vấn đề đồng nhất miền:** V8.4 train trên hydra + CIC Patator, val set 100% CIC Patator (do stratified split). BruteForce F1 = 100% — đánh giá in-distribution, không phản ánh generalization.

**Giải pháp:** xây dựng val set đa dạng miền: 400 hydra flows + 398 Patator flows = 798 flows BruteForce.

| Val Set | BruteForce F1 | Macro F1 | Tin cậy |
|---|---|---|---|
| V8.4: 100% CIC Patator | 1,000 | 94,95% | Thấp (in-distribution) |
| V8.5: Mixed hydra + Patator | 0,860 | 91,7% | Cao (domain-diverse) |

Chênh lệch 14% tuyệt đối phản ánh thay đổi tập kiểm định, không phải thay đổi mô hình. V8.5 đáng tin cậy hơn vì kiểm tra khả năng generalize sang tool BruteForce chưa thấy.

**3 đặc trưng bổ sung cho môi trường NAT:**

| Đặc trưng | Công thức | Lý do |
|---|---|---|
| `IAT_CV` | $\sigma_{IAT} / \mu_{IAT}$ | Đo tính đều đặn timing; phân biệt periodic C2 với Benign |
| `Bwd_Pkt_Ratio` | $N_{bwd} / N_{total}$ | Phân biệt one-way (PortScan, DoS) với two-way (Benign) |
| `Pkt_Size_Ratio` | $\overline{L}_{bwd} / \overline{L}_{fwd}$ | Phân biệt download-heavy vs upload-heavy vs DoS |

### 3.4.5 Mô hình cuối V8.5: thiết kế và huấn luyện

**Thành phần dataset V8.5 (111.825 flows):**

| Lớp | Nguồn | Số flows | Tỷ lệ |
|---|---|---|---|
| Benign | Testbed nội bộ (nhiều phiên) | 51.975 | 46,5% |
| DoS | Testbed nội bộ | 19.800 | 17,7% |
| Web Attack | Run10 + CIC Thursday XSS/SQLi | 27.067 | 24,2% |
| BruteForce | Run10 hydra + CIC Patator | 7.983 | 7,1% |
| PortScan | CIC Friday (surrogate) | 5.000 | 4,5% |
| **Tổng** | | **111.825** | |

**Cấu hình huấn luyện V8.5:**

| Tham số | Giá trị |
|---|---|
| Kiến trúc | FTT: d=128, 8 heads, 4 layers, d_ff=512 |
| Learning rate | Theo lớp: backbone 1e-5, mid 1,5e-5, head 3e-5 |
| Dropout | 0,15 |
| Label smoothing | 0,10 |
| Weight decay | 2e-4 |
| Class weights | $\sqrt{N/(K \cdot n_c)}$, clip [0,5; 2,0] |
| Early stopping | Patience=5, dừng tại epoch 6 |

**[Hình 3.9: Learning curves V8.5 — train loss và val Macro F1 theo epoch; best checkpoint tại epoch 1]**

---

## 3.5 Triển khai Hybrid IDS End-to-End

### 3.5.1 Pipeline tích hợp

**[Hình 3.10: Pipeline End-to-End — Traffic → eth0 interface → Snort (packet-level, real-time alert log) || tcpdump pcap → CICFlowMeter → PowerTransformer V8.5 → FTT V8.5 → ML alert log → Alert Aggregator]**

Ba thành phần chạy song song:
- **Snort 3:** lắng nghe interface WSL, tạo cảnh báo ngay khi phát hiện luật khớp (microsecond). Community Rules + Emerging Threats Open.
- **CICFlowMeter:** capture PCAP liên tục, tổng hợp flow sau khi hoàn chỉnh (RST/FIN hoặc timeout 30s), trích xuất 80 đặc trưng → CSV.
- **FTT Inference Engine:** đọc CSV mới, apply PowerTransformer V8.5, phân loại với mô hình V8.5 → nhãn lớp + confidence score → ML alert log.

**Alert Aggregator:** hợp nhất hai nguồn cảnh báo. Cùng một session trong cả hai → confirmed alert, mức ưu tiên tăng.

### 3.5.2 Môi trường giả lập tấn công

**Script tự động hóa tấn công (Kali):**

```bash
# DoS
slowhttptest -c 1000 -H -i 10 -r 200 -t GET -u http://192.168.1.x/dvwa/

# BruteForce SSH
hydra -l admin -P /usr/share/wordlists/rockyou.txt 192.168.1.x ssh

# PortScan
nmap -sS -p 1-65535 --min-rate 1000 192.168.1.x

# WebAttack SQLi
curl "http://192.168.1.x/dvwa/vulnerabilities/sqli/?id=1' OR '1'='1"
```

---

## Kết chương

Chương này trình bày phương pháp đề xuất qua ba giai đoạn với mỗi giai đoạn xuất phát từ kết quả định lượng của giai đoạn trước. Giai đoạn 1 trên NSL-KDD thiết lập kiến trúc Two-Stage (AE Gate + Stacking Ensemble) và xác nhận giới hạn trên của dataset 1998. Giai đoạn 2 trên CIC-IDS-2017 phát triển Two-Stage Cascade với Asymmetric Ensemble Voting cho 9 lớp (gộp từ 15 nhãn gốc), đạt Macro F1 = 0,9294. Giai đoạn 3 trên Testbed giải quyết covariate shift bằng thu thập dữ liệu thực và tái huấn luyện hoàn toàn, đạt Macro F1 = 91,7% trên 5 lớp có thể mô phỏng. Chương 4 tiếp theo phân tích lý thuyết bốn quyết định thiết kế quan trọng nhất của các giai đoạn này.
