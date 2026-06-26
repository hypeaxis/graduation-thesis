# Chương 2. Nền tảng lý thuyết

Chương 1 xác định ba giới hạn của các hướng tiếp cận hiện tại và đề xuất hệ thống lai ghép ba giai đoạn. Chương này xây dựng nền tảng lý thuyết cho tất cả các kỹ thuật được sử dụng, theo thứ tự từ đặc trưng đầu vào đến kiến trúc mô hình và chiến lược xử lý mất cân bằng. Phần 2.1 phân tích bài toán IDS dựa trên đặc trưng flow. Phần 2.2 tổng quan nghiên cứu liên quan. Phần 2.3 trình bày kiến trúc FT-Transformer. Phần 2.4 trình bày các kỹ thuật xử lý mất cân bằng. Phần 2.5 trình bày học chuyển giao và thích nghi miền. Phần 2.6 mô tả hệ thống IDS lai ghép.

---

## 2.1 Ngữ cảnh bài toán phát hiện xâm nhập mạng

Phát hiện xâm nhập mạng được hình thức hóa như bài toán phân loại có giám sát trên dữ liệu lưu lượng mạng. Đầu vào là vector đặc trưng thống kê mô tả một *flow* — chuỗi gói tin giữa hai đầu cuối xác định bởi bộ 5-tuple (IP nguồn, IP đích, cổng nguồn, cổng đích, giao thức) trong một khoảng thời gian nhất định. Đầu ra là nhãn lớp: Benign hoặc một trong các loại tấn công.

### 2.1.1 Phân tích ở tầng flow với CICFlowMeter

Công cụ CICFlowMeter trích xuất từ mỗi flow vector 77–80 đặc trưng thống kê:
- Thời lượng flow (`Flow_Duration`)
- Số gói tin theo hai hướng forward/backward (`Fwd_Packets`, `Bwd_Packets`)
- Thống kê độ dài gói tin: trung bình, độ lệch chuẩn, min, max theo hướng
- Thời gian giữa các gói tin (`Flow_IAT_Mean`, `Fwd_IAT_Std`, v.v.)
- Số lượng TCP flag (SYN, FIN, RST, PSH, ACK, URG)
- Tốc độ flow (`Flow_Bytes/s`, `Flow_Packets/s`)
- Active/idle time và cửa sổ TCP

**Ưu điểm:** hoạt động được với traffic mã hóa (TLS/HTTPS), không cần giải mã payload.

**Giới hạn căn bản:** không nắm bắt được nội dung payload — không thể phát hiện Infiltration (tấn công ẩn trong HTTP GET bình thường) hay Heartbleed (khai thác TLS handshake extension). Phân tích chi tiết tại Mục 4.6.

### 2.1.2 Thách thức mất cân bằng không điển hình

Mất cân bằng trong IDS có hai chiều đồng thời:
- **Benign vs Attack:** Benign chiếm 80–90% traffic trong môi trường production
- **Giữa các lớp tấn công:** DoS/DDoS có hàng triệu flow; Infiltration chỉ vài chục flow

**[Hình 2.1: Phân phối lớp trong CIC-IDS-2017 — biểu đồ bar log-scale, Benign ~2,3M, Heartbleed 10]**

Accuracy không phản ánh hiệu năng thực: mô hình dự đoán tất cả là Benign đạt 82,7% accuracy trên CIC nhưng hoàn toàn vô dụng. **Macro F1** (trọng số đều mọi lớp) và **MCC** là các chỉ số phù hợp.

---

## 2.2 Các nghiên cứu liên quan

### 2.2.1 Tiến trình phát triển IDS học máy

**2000–2015:** Decision Tree, Naive Bayes, SVM trên KDD Cup 1999 và NSL-KDD. NSL-KDD loại bỏ 78% bản ghi trùng lặp của KDD Cup gốc và cân bằng lại phân phối, nhưng vẫn là dữ liệu thu thập năm 1998 — thiếu các giao thức và tấn công hiện đại.

**2017–nay:** CIC-IDS-2017 (Sharafaldin et al., 2018) thu thập từ mạng thực với 14 loại tấn công hiện đại, CICFlowMeter 77 đặc trưng. Random Forest và XGBoost đạt Accuracy >99% trên CIC, nhưng hầu hết đánh giá in-distribution (cross-validation trên cùng dataset), không kiểm tra covariate shift khi triển khai.

**FT-Transformer cho tabular data:** Gorishniy et al. (2021) chứng minh FT-Transformer cạnh tranh XGBoost trên 11/15 benchmark tabular — thu hẹp khoảng cách giữa deep learning và mô hình cây.

### 2.2.2 Khoảng trống nghiên cứu

Hầu hết công trình IDS không giải quyết covariate shift do hạ tầng thu thập khác nhau (switch vật lý vs. môi trường ảo hóa). Đây là khoảng trống thực tiễn quan trọng mà đề tài trực tiếp giải quyết.

---

## 2.3 Kiến trúc Feature Tokenizer Transformer (FT-Transformer)

FT-Transformer áp dụng kiến trúc Transformer cho dữ liệu dạng bảng bằng cách xử lý mỗi đặc trưng như một token riêng biệt, cho phép cơ chế Attention học tường minh tương tác giữa các đặc trưng.

**[Hình 2.2: Kiến trúc tổng thể FT-Transformer: Feature Tokenizer → L × Transformer Block → CLS Token → Classification Head → Output]**

### 2.3.1 Cơ chế mã hóa đặc trưng (Feature Tokenizer)

Cho mẫu đầu vào $\mathbf{x} = [x_1, x_2, \ldots, x_k] \in \mathbb{R}^k$, Feature Tokenizer ánh xạ mỗi đặc trưng scalar $x_j$ thành vector nhúng $\mathbf{e}_j \in \mathbb{R}^d$:

$$\mathbf{e}_j = x_j \cdot \mathbf{w}_j + \mathbf{b}_j, \qquad j = 1, 2, \ldots, k \tag{eq:feature-tokenizer}$$

trong đó $\mathbf{w}_j \in \mathbb{R}^d$ và $\mathbf{b}_j \in \mathbb{R}^d$ là tham số **riêng cho từng đặc trưng** — khác MLP dùng chung trọng số. Số tham số Feature Tokenizer: $k \times 2d$.

Token CLS $\mathbf{e}_{[\texttt{CLS}]} \in \mathbb{R}^d$ được thêm vào đầu chuỗi để tổng hợp toàn bộ input. Ma trận token đầy đủ:

$$\mathbf{T} = \begin{bmatrix} \mathbf{e}_{[\texttt{CLS}]} \\ \mathbf{e}_1 \\ \vdots \\ \mathbf{e}_k \end{bmatrix} \in \mathbb{R}^{(k+1) \times d} \tag{eq:token-matrix}$$

**[Hình 2.3: Feature Tokenizer — mỗi x_j được chiếu riêng thành e_j ∈ R^d qua (w_j, b_j) riêng; CLS token thêm vào đầu sequence]**

### 2.3.2 Self-Attention và Transformer Block

**Multi-Head Self-Attention (MHSA)** tính ba ma trận Query, Key, Value:

$$Q = \mathbf{T} W^Q, \quad K = \mathbf{T} W^K, \quad V = \mathbf{T} W^V \tag{eq:qkv}$$

Điểm Attention giữa các token phản ánh mức độ tương tác:

$$\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right) V \tag{eq:attention}$$

Hệ số $1/\sqrt{d_k}$ tránh vanishing gradient khi $d_k$ lớn. Với $h$ đầu Attention song song:

$$\text{MHSA}(\mathbf{T}) = \text{Concat}(\text{head}_1, \ldots, \text{head}_h)\, W^O \tag{eq:mhsa}$$

**Feed-Forward Network (FFN)** áp dụng độc lập trên từng token:

$$\text{FFN}(\mathbf{z}) = \text{GELU}(\mathbf{z} W_1 + \mathbf{b}_1)\, W_2 + \mathbf{b}_2 \tag{eq:ffn}$$

với $d_{ff} = 4d$. **Transformer Block** (Pre-LayerNorm):

$$\mathbf{T}' = \text{LayerNorm}(\mathbf{T} + \text{MHSA}(\mathbf{T})) \tag{eq:block1}$$

$$\mathbf{T}'' = \text{LayerNorm}(\mathbf{T}' + \text{FFN}(\mathbf{T}')) \tag{eq:block2}$$

Sau $L$ tầng, CLS token $\mathbf{e}_{[\texttt{CLS}]}^{(L)}$ đi qua head phân loại:

$$\hat{\mathbf{y}} = \text{softmax}\!\left(\mathbf{e}_{[\texttt{CLS}]}^{(L)}\, W_{cls} + \mathbf{b}_{cls}\right) \tag{eq:cls-head}$$

### 2.3.3 Tại sao chọn FT-Transformer

| Tiêu chí | MLP | Random Forest | XGBoost | **FT-Transformer** |
|---|---|---|---|---|
| Tương tác đặc trưng tường minh | Không | Có (ngầm) | Có (ngầm) | **Có (Attention)** |
| Fine-tuning chọn lọc (Layer Freezing) | Có | Không | Không | **Có** |
| Phù hợp đặc trưng liên tục nhiều | Trung bình | Tốt | Tốt | **Rất tốt** |
| Mở rộng feature (Model Surgery) | Có | Không | Không | **Có** |

**Ba lý do cốt lõi:**
1. Attention học tường minh tương tác đặc trưng — "khi `src_bytes` cao và `rerror_rate` cao đồng thời → R2L attack". MLP học điều này một cách ẩn, kém hiệu quả hơn.
2. Hỗ trợ Layer Freezing khi domain shift sang Testbed WSL (không thể với Random Forest/XGBoost).
3. Hỗ trợ Model Surgery mở rộng $k=77 \to 80$ features bằng cách thêm 3 hàng vào Feature Tokenizer embedding matrix.

### 2.3.4 Cấu hình FT-Transformer trong đề tài

| Mô hình | $d$ | $h$ heads | $L$ layers | $d_{ff}$ | Dropout | Features | Output |
|---|---|---|---|---|---|---|---|
| NSL-KDD Stage 2 | 128 | 8 | 4 | 512 | 0,1 | 122 | 5 lớp |
| CIC Stage 1 (Gating) | 128 | 8 | 4 | 512 | 0,2 | 77 | 2 lớp |
| CIC Stage 2 (Expert) | 64 | 4 | 3 | 256 | 0,2 | 34 | 9 lớp |
| Testbed V8.5 | 128 | 8 | 4 | 512 | 0,2 | 80 | 5 lớp |

*Expert Network dùng cấu hình nhỏ hơn (d=64, L=3) vì chỉ nhận 34 đặc trưng sau lọc tương quan và chỉ xử lý ~17,3% traffic (Suspicious flows từ Gating).*

---

## 2.4 Các kỹ thuật xử lý mất cân bằng dữ liệu

### 2.4.1 Focal Loss

**Cross-Entropy tiêu chuẩn:**

$$\mathcal{L}_{CE}(\mathbf{y}, \hat{\mathbf{y}}) = -\sum_{c=1}^{C} y_c \log \hat{y}_c \tag{eq:ce}$$

Ký hiệu $p_t$ là xác suất dự đoán cho nhãn đúng:

$$p_t = \begin{cases} \hat{y} & y = 1 \\ 1 - \hat{y} & y = 0 \end{cases} \tag{eq:pt}$$

**Vấn đề gradient:** với 1000 mẫu Benign ($p_t=0,95$) và 10 mẫu BruteForce ($p_t=0,4$) trong một batch:
$$\text{Tổng gradient Benign} \propto 1000 \times 0{,}051 = 51 \quad\text{vs}\quad \text{BruteForce} \propto 10 \times 0{,}916 = 9{,}16$$
Benign áp đảo 5:1 dù mỗi BruteForce có gradient lớn hơn 18 lần mỗi Benign.

**Focal Loss** (Lin et al., 2017):

$$\mathcal{L}_{FL}(p_t) = -\alpha_t\, (1 - p_t)^\gamma \log(p_t) \tag{eq:focal-loss}$$

Với $\gamma=2$, khi $p_t=0,95$: hệ số $(1-0,95)^2 = 0,0025$ → gradient Benign giảm 400 lần; BruteForce ($p_t=0,4$): hệ số $0,36$ → giảm ít. Tỷ lệ BruteForce/Benign đảo ngược thành 2578:1 so với 18:1 của CE.

**Class-Balanced Focal Loss** (Cui et al., 2019):

$$\alpha_c = \frac{1 - \beta}{1 - \beta^{n_c}}, \quad \beta = 0{,}9999 \tag{eq:cb-alpha}$$

Ổn định hơn inverse-frequency đơn thuần khi tần suất lớp chênh lệch >1000:1.

### 2.4.2 SMOTE

SMOTE (Chawla et al., 2002) tạo mẫu tổng hợp bằng nội suy tuyến tính:

$$\mathbf{x}_{new} = \mathbf{x}_i + \lambda\, (\mathbf{x}_{k_r} - \mathbf{x}_i), \qquad \lambda \sim \text{Uniform}(0, 1) \tag{eq:smote}$$

$\mathbf{x}_{k_r}$ là láng giềng ngẫu nhiên trong $K$-NN của $\mathbf{x}_i$ thuộc cùng lớp. **SMOTE-ENN** thêm bước ENN loại bỏ mẫu nhiễu gần biên giới.

**Giới hạn:** U2R với 52 mẫu trong không gian 122 chiều — các mẫu tổng hợp chủ yếu là bản sao gần, không tăng được diversity thực sự.

### 2.4.3 Weighted Random Sampling

$$w_i = \frac{N}{K \cdot n_c} \tag{eq:class-weight}$$

Biến thể làm mượt và clip về $[w_{min}, w_{max}]$ dùng trong V8.5:

$$w_i = \sqrt{\frac{N}{K \cdot n_c}}, \quad \text{clip về } [0{,}5;\; 2{,}0] \tag{eq:smooth-weight}$$

### 2.4.4 Label Smoothing

$$y_c^{smooth} = (1 - \varepsilon)\, y_c + \frac{\varepsilon}{C} \tag{eq:label-smooth}$$

Dùng $\varepsilon = 0{,}10$ trong V8.5 để giảm overfitting. Không dùng cho CIC Expert Network (ảnh hưởng xấu với Heartbleed chỉ có 10 mẫu).

---

## 2.5 Học chuyển giao và thích nghi miền

### 2.5.1 Covariate Shift

$$P_{source}(\mathbf{x}) \neq P_{target}(\mathbf{x}), \quad P(y \mid \mathbf{x}) \text{ về lý thuyết không đổi}$$

CIC thu thập trên switch Gigabit tạo $P_{source}$; Testbed WSL với Hyper-V NAT tạo $P_{target}$ khác biệt. MCC từ $-0{,}015$ khi apply trực tiếp xác nhận covariate shift nghiêm trọng.

**Nguyên nhân cụ thể:**
- Switch vật lý Gigabit xử lý frame đầy đủ; card mạng ảo Hyper-V có overhead ảo hóa thay đổi packet size và timing
- NAT của Windows thêm độ trễ, thay đổi ACK timing → ảnh hưởng IAT và flag counts
- PowerTransformer parameters fit trên phân phối CIC không phù hợp với phân phối Testbed

### 2.5.2 Layer Freezing Fine-tuning

Đóng băng tham số tầng thấp $\theta_{freeze}$, chỉ cập nhật tầng cao $\theta_{fine}$:

$$\theta_{fine}^{*} = \arg\min_{\theta_{fine}}\; \mathcal{L}\!\left(f_{\theta_{freeze},\, \theta_{fine}}(\mathbf{x}_{target}),\; y_{target}\right) \tag{eq:layer-freeze}$$

**Lý do phân tầng:** tầng Attention thấp học quan hệ tổng quát (duration ngắn → low byte count → PortScan); tầng cao học phân biệt đặc thù miền. Đóng băng tầng thấp giữ kiến thức tổng quát, cập nhật tầng cao để thích nghi.

Đánh giá Catastrophic Forgetting:

$$CF = \frac{\text{Acc}_{source,\, before} - \text{Acc}_{source,\, after}}{\text{Acc}_{source,\, before}} \times 100\% \tag{eq:cf}$$

Chiến lược đóng băng 2/4 tầng đạt $CF = 0{,}61\%$ (giữ 99,39% hiệu năng CIC).

### 2.5.3 Model Surgery

Mở rộng Feature Tokenizer $k \to k + \Delta$ features:

$$\mathbf{W}^{emb}_{new} = \begin{bmatrix} \mathbf{W}^{emb}_{old} \in \mathbb{R}^{k \times d} \\ \mathbf{W}^{emb}_{new rows} \in \mathbb{R}^{\Delta \times d} \end{bmatrix} \in \mathbb{R}^{(k+\Delta) \times d}$$

$\Delta$ hàng mới khởi tạo $\mathcal{N}(0, 0{,}01)$, được học trong fine-tuning. $k$ hàng cũ giữ nguyên (transplant). Tất cả tham số còn lại không thay đổi.

Trong đề tài: $77 \to 80$ features với 3 đặc trưng bổ sung đặc thù NAT (IAT\_CV, Bwd\_Pkt\_Ratio, Pkt\_Size\_Ratio). Model Surgery sau Layer Freezing tăng MCC từ $0{,}6825$ lên $0{,}7333$.

---

## 2.6 Hệ thống IDS lai ghép: Snort và FT-Transformer

### 2.6.1 So sánh hai hướng tiếp cận

| Tiêu chí | Snort (rule-based) | FT-Transformer (ML-based) |
|---|---|---|
| Tầng phân tích | Packet (payload + header) | Flow (thống kê 5-tuple) |
| Độ trễ | Microsecond (real-time) | Vài giây (near-realtime) |
| Phát hiện tấn công đã biết | Rất tốt | Tốt |
| Phát hiện tấn công chưa có luật | Không | Có |
| Hoạt động với traffic mã hóa | Không | Có |
| Nhạy cảm với covariate shift | Không | Có |

### 2.6.2 Tại sao kết hợp thay vì chọn một

Hai phương pháp bổ sung cho nhau:
- **Snort bắt XSS/SQLi** qua payload HTTP body; FTT bỏ sót vì flow statistics giống Benign HTTP
- **FTT bắt DoS slow-connection** qua flow duration và IAT bất thường; Snort bỏ sót nếu không có rule cho slow-rate DoS cụ thể
- **FTT bắt BruteForce SSH** qua số TCP connections thất bại; Snort bỏ sót nếu tool không có signature

### 2.6.3 Kiến trúc pipeline End-to-End

**[Hình 2.4: Traffic → interface → SONG SONG: (1) Snort packet-level real-time; (2) tcpdump pcap → CICFlowMeter → PowerTransformer → FTT → ML alert → Alert Aggregator → Dashboard]**

Hai thành phần chạy song song và độc lập. Alert Aggregator hợp nhất cảnh báo: cùng một session trong cả hai nguồn → confirmed alert, mức ưu tiên tăng.

---

## Kết chương

Chương này cung cấp nền tảng lý thuyết cho ba giai đoạn nghiên cứu. FT-Transformer được chọn vì cơ chế Attention học tường minh tương tác đặc trưng và hỗ trợ Layer Freezing và Model Surgery — hai kỹ thuật không thể áp dụng với Random Forest hay XGBoost. Focal Loss với CB-alpha giải quyết gradient imbalance khi tỷ lệ lớp chênh lệch >1000:1. Layer Freezing kiểm soát Catastrophic Forgetting khi thích nghi miền. Snort và FTT hoạt động ở hai tầng độc lập và bổ sung nhau, tạo cơ sở cho hệ thống lai ghép End-to-End. Chương 3 áp dụng tất cả kỹ thuật này vào ba giai đoạn nghiên cứu cụ thể.
