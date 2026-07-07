# TỔNG HỢP LÝ THUYẾT SỬ DỤNG TRONG ĐỒ ÁN
### Hệ thống phát hiện xâm nhập mạng lai ghép (Snort + FT-Transformer)

> Bản tổng hợp toàn bộ nền tảng lý thuyết được dùng trong nội dung đồ án hiện tại (Chương 2–5, quyển `Noi_dung_do_an/`). Mỗi mục nêu: **định nghĩa/công thức → vai trò/lý do dùng → dùng ở đâu trong đồ án**. Dùng để ôn tập bảo vệ và tra cứu nhanh.

---

## 0. Bản đồ lý thuyết → nơi sử dụng

| Nhóm | Lý thuyết | Giai đoạn dùng |
|---|---|---|
| A. Dữ liệu & tiền xử lý | Flow-based features (CICFlowMeter), One-hot, MinMaxScaler, PowerTransformer Yeo-Johnson, lọc tương quan | Cả 3 GĐ |
| B. Mô hình lõi | FT-Transformer, Autoencoder, LightGBM, Random Forest, KNN | GĐ1–3 |
| C. Kiến trúc phân tầng | Two-Stage (AE Gate + Stacking), Stacking + Meta-LR, Two-Stage Cascade, Ensemble Voting (Bias–Variance), Asymmetric Voting | GĐ1 (NSL-KDD), GĐ2 (CIC) |
| D. Mất cân bằng lớp | Focal Loss, CB-Focal Loss, SMOTE(-ENN), Weighted Sampling, Label Smoothing, Hard Negative Mining, Boost-Minority Val | GĐ1–3 |
| E. Chuyển giao & thích nghi miền | Covariate Shift, Layer Freezing, Catastrophic Forgetting, Model Surgery | GĐ3 (Testbed) |
| F. Hệ thống lai ghép | Snort (signature-based), pipeline Hybrid, Alert Aggregator | GĐ4 End-to-End |
| G. Chỉ số đánh giá | Macro F1, MCC, Balanced Accuracy | Cả 3 GĐ |

---

## A. Biểu diễn dữ liệu & tiền xử lý

### A.1 Phân tích ở tầng flow (CICFlowMeter)
- **Định nghĩa:** *flow* = chuỗi gói tin cùng 5-tuple (IP nguồn, IP đích, cổng nguồn, cổng đích, giao thức). CICFlowMeter trích **77–80 đặc trưng thống kê** mỗi flow: `Flow_Duration`, số gói fwd/bwd, thống kê độ dài gói (mean/std/min/max), IAT (`Flow_IAT_Mean`, `Fwd_IAT_Std`…), đếm TCP flag (SYN/FIN/RST/PSH/ACK/URG), tốc độ (`Flow_Bytes/s`), active/idle time.
- **Vai trò:** biểu diễn đầu vào cho mọi mô hình ML. Ưu điểm: **hoạt động được với traffic mã hóa (TLS/HTTPS)** không cần giải mã payload.
- **Giới hạn căn bản:** không nắm nội dung payload → không tự phát hiện Infiltration/Heartbleed (thông tin nằm trong payload, không ở thống kê flow).
- **Dùng:** đặc trưng đầu vào tất cả giai đoạn (77 CIC, 80 Testbed V8.5, 122 NSL-KDD sau one-hot).

### A.2 One-hot Encoding + MinMaxScaler (NSL-KDD)
- 3 đặc trưng phân loại (protocol_type: 3, service: 70, flag: 11) → one-hot → **41 raw đặc trưng thành 122 chiều**. 38 đặc trưng số thực chuẩn hoá bằng **MinMaxScaler** về [0,1].
- **Dùng:** tiền xử lý GĐ1.

### A.3 PowerTransformer Yeo-Johnson (CIC & Testbed)
- **Công thức:**
$$\psi_\lambda(x)=\begin{cases}\dfrac{(x+1)^\lambda-1}{\lambda}&\lambda\neq0,\,x\ge0\\ \ln(x+1)&\lambda=0,\,x\ge0\\ \dfrac{-[(-x+1)^{2-\lambda}-1]}{2-\lambda}&\lambda\neq2,\,x<0\\ -\ln(-x+1)&\lambda=2,\,x<0\end{cases}$$
$\lambda$ ước lượng bằng **MLE** để đưa phân phối về xấp xỉ Gaussian.
- **Vào → Ra:** *Vào* = một giá trị đặc trưng thô $x$ (vd `Flow_Bytes/s` lệch mạnh, đuôi dài, có thể âm sau feature-engineering); *Ra* = $\psi_\lambda(x)$ cùng thứ nguyên nhưng phân phối gần Gaussian, tâm ~0. Áp **độc lập từng cột đặc trưng**, mỗi cột một $\lambda$ riêng ước lượng trên tập train.
- **Vì sao đặt ở đây (ngay sau làm sạch, trước FTT):** Feature Tokenizer chiếu tuyến tính $x_j\mathbf{w}_j$ — nếu $x_j$ còn đuôi dài thì vài giá trị cực đại thống trị embedding, lớp thiểu số bị "chôn" trong đuôi Benign. Đưa về Gaussian trước → mỗi đặc trưng đóng góp cân bằng vào token. Phải đặt **trước** mọi mô hình và fit chỉ trên train (tránh leakage), rồi transform cả train/test bằng cùng $\lambda$.
- **Vì sao thay StandardScaler/MinMaxScaler:** nhiều đặc trưng CICFlowMeter có phân phối **power-law đuôi dài** (byte counts, IAT). StandardScaler không đổi hình dạng phân phối; MinMaxScaler không xử lý skewness. Yeo-Johnson làm phân phối gần Gaussian → FTT học hiệu quả hơn, lớp thiểu số không bị "chôn" trong đuôi phân phối Benign.
- **Lưu ý quan trọng:** scaler này gắn chặt với embedding FTT đã học → là gốc rễ vì sao **Re-fit Scaler thất bại** (xem E.1).
- **Dùng:** tiền xử lý GĐ2 (CIC), GĐ3 (V8.5).

### A.4 Lọc tương quan cao (correlation filtering)
- Loại đặc trưng có **Pearson $r>0{,}95$** → giảm **77 → 34 đặc trưng** cho Expert Network. Gating Network giữ đủ 77.
- **Vai trò:** giảm dư thừa, giúp mạng nhỏ (Expert d=64) học ổn định trên phần traffic khó.

---

## B. Mô hình lõi

### B.1 FT-Transformer (Feature Tokenizer Transformer) — mô hình trung tâm
Áp dụng Transformer cho **dữ liệu bảng**: mỗi đặc trưng là một token → Attention học **tường minh tương tác giữa các đặc trưng**.

**(1) Feature Tokenizer** — chiếu mỗi scalar $x_j$ thành vector nhúng riêng:
$$\mathbf{e}_j = x_j\cdot\mathbf{w}_j+\mathbf{b}_j,\quad j=1..k$$
$(\mathbf{w}_j,\mathbf{b}_j)$ **riêng từng đặc trưng** (khác MLP dùng chung trọng số). Thêm **CLS token** để tổng hợp toàn input → ma trận token $\mathbf{T}\in\mathbb{R}^{(k+1)\times d}$.

- **Vào → Ra:** *Vào* = vector đặc trưng đã chuẩn hoá $\mathbf{x}=[x_1..x_k]\in\mathbb{R}^k$ (1 flow); *Ra* = $\mathbf{T}\in\mathbb{R}^{(k+1)\times d}$ — biến **mỗi số vô hướng thành 1 vector $d$ chiều** (token). $k$ = số đặc trưng, $d$ = kích thước embedding (128/64).
- **Vì sao đặt ở đây (lớp đầu tiên của mạng):** Attention cần "chuỗi token" để tính tương tác cặp; nhưng dữ liệu bảng vốn là các số rời rạc, không có token sẵn như câu chữ. Feature Tokenizer chính là bước **biến bảng thành chuỗi** để Transformer dùng được. Dùng $(\mathbf{w}_j,\mathbf{b}_j)$ riêng vì mỗi đặc trưng có thang/ý nghĩa khác nhau (byte count ≠ flag count). CLS token thêm vào để cuối mạng có 1 vector duy nhất đại diện cả flow cho việc phân loại.

**(2) Multi-Head Self-Attention (MHSA):**
$$Q=\mathbf{T}W^Q,\;K=\mathbf{T}W^K,\;V=\mathbf{T}W^V$$
$$\text{Attention}(Q,K,V)=\text{softmax}\!\Big(\tfrac{QK^\top}{\sqrt{d_k}}\Big)V$$
Hệ số $1/\sqrt{d_k}$ chống vanishing gradient; $h$ head song song rồi Concat qua $W^O$.

- **Vào → Ra:** *Vào* = ma trận token $\mathbf{T}\in\mathbb{R}^{(k+1)\times d}$; *Ra* = ma trận cùng kích thước, mỗi token đã được **cập nhật bằng tổng có trọng số của các token khác**. $QK^\top$ = ma trận điểm tương tác giữa **mọi cặp đặc trưng** (kích thước $(k{+}1)\times(k{+}1)$); softmax biến mỗi hàng thành trọng số $\ge0$, tổng 1; nhân $V$ = trộn thông tin theo trọng số đó.
- **Vì sao đặt ở đây (lõi mỗi Transformer block):** đây chính là bước **học tương tác đặc trưng tường minh** — điều làm FTT vượt MLP. Ví dụ token `src_bytes` "chú ý" mạnh tới token `rerror_rate` → mạng nắm được luật "hai cái cùng cao → R2L". Chia $\sqrt{d_k}$ vì khi $d_k$ lớn, tích vô hướng $QK^\top$ có phương sai lớn → softmax bão hoà, gradient ~0; chia lại đưa về thang ổn định. Nhiều head để học **nhiều kiểu quan hệ song song** (1 head bắt quan hệ timing, head khác bắt quan hệ kích thước gói).

**(3) Feed-Forward + Transformer Block (Pre-LayerNorm):**
$$\text{FFN}(\mathbf{z})=\text{GELU}(\mathbf{z}W_1+\mathbf{b}_1)W_2+\mathbf{b}_2,\quad d_{ff}=4d$$
$$\mathbf{T}'=\text{LN}(\mathbf{T}+\text{MHSA}(\mathbf{T})),\quad \mathbf{T}''=\text{LN}(\mathbf{T}'+\text{FFN}(\mathbf{T}'))$$
Sau $L$ tầng, **CLS token** qua head phân loại softmax.

- **Vào → Ra (FFN):** *Vào/Ra* = một token $\mathbf{z}\in\mathbb{R}^d$ → $\mathbb{R}^d$, áp **độc lập từng token**. FFN nở rộng ra $d_{ff}=4d$ rồi thu lại → thêm **phi tuyến** (GELU) cho biến đổi trong từng token, sau khi MHSA đã trộn thông tin *giữa* các token.
- **Vào → Ra (Block):** *Vào/Ra* = $\mathbf{T}\to\mathbf{T}''$ cùng kích thước → **xếp chồng $L$ block** được, mỗi block tinh chỉnh thêm. **Residual** $(\mathbf{T}+\dots)$ giữ đường gradient thẳng chống suy biến ở mạng sâu; **LayerNorm** ổn định thang giá trị mỗi token.
- **Vào → Ra (CLS head):** *Vào* = **chỉ** vector CLS ở tầng cuối $\mathbf{e}_{[CLS]}^{(L)}\in\mathbb{R}^d$ (đã gom thông tin toàn flow qua Attention); *Ra* = phân phối xác suất $\hat{\mathbf{y}}\in\mathbb{R}^{C}$ ($C$ lớp).
- **Vì sao dùng CLS thay vì gộp tất cả token:** CLS được thiết kế để "hút" thông tin từ mọi đặc trưng qua các tầng Attention, nên 1 vector này đủ đại diện cả flow → head phân loại gọn, số tham số nhỏ, tránh phải pooling thủ công $k$ token.

- **Ba lý do chọn FTT (thay MLP/RF/XGBoost):**
  1. **Attention học tương tác đặc trưng tường minh** — vd "src_bytes cao + rerror_rate cao → R2L", "destination lạ + upload cao + khuya → Infiltration". MLP học ngầm, kém hơn.
  2. Hỗ trợ **Layer Freezing** khi domain shift (RF/XGBoost không làm được).
  3. Hỗ trợ **Model Surgery** mở rộng đặc trưng $77\to80$.
- **Cấu hình trong đồ án:**

| Mô hình | d | heads | L | d_ff | dropout | features | output |
|---|---|---|---|---|---|---|---|
| NSL-KDD Stage 2 | 128 | 8 | 4 | 512 | 0,1 | 122 | 5 lớp |
| CIC Gating | 128 | 8 | 4 | 512 | 0,2 | 77 | 2 lớp |
| CIC Expert | 64 | 4 | 3 | 256 | 0,2 | 34 | 9 lớp |
| Testbed V8.5 | 128 | 8 | 4 | 512 | 0,2 | 80 | 5 lớp |

### B.2 Autoencoder Anomaly Gate (GĐ1, Stage 1)
- **Nguyên lý unsupervised:** huấn luyện **chỉ trên Normal flows**; encoder–decoder học tái tạo lưu lượng bình thường với sai số thấp. Flow tấn công → reconstruction error cao.
- **Kiến trúc:** Encoder 122→64→32→16, Decoder 16→32→64→122 (ReLU), loss MSE.
$$\text{MSE}(\mathbf{x})=\tfrac{1}{D}\sum_{i=1}^{D}(x_i-\hat x_i)^2,\quad
\text{gate}(\mathbf{x})=\begin{cases}\text{Normal}&\text{MSE}<\tau\\\text{Suspicious}&\text{MSE}\ge\tau\end{cases}$$
Ngưỡng $\tau=0{,}008481$ (percentile 95 của Normal train errors).

- **Vào → Ra:** *Vào* = flow $\mathbf{x}\in\mathbb{R}^{122}$; *Ra trung gian* = $\hat{\mathbf{x}}$ (bản tái tạo) → **1 số vô hướng** MSE (mức "lạ"); *Ra cuối* = nhãn nhị phân {Normal, Suspicious}. $D=122$ = số chiều; $\tau$ = ngưỡng cắt.
- **Vì sao dùng MSE + ngưỡng ở vị trí Stage 1:** cần một **cổng lọc rẻ, chặn phần lớn Benign** trước khi chạy mô hình đa lớp đắt hơn. AE học "hình dạng" của Normal nên MSE đo trực tiếp độ lệch khỏi chuẩn — không cần nhãn tấn công, do đó **bắt được cả tấn công chưa từng thấy** (khác classifier phải học từng lớp). Chọn $\tau$ ở percentile 95 = chấp nhận ~5% Normal bị đẩy sang Stage 2 để đổi lấy recall tấn công cao (đặt cổng "rộng" có chủ đích).
- **Ưu điểm:** phát hiện cả tấn công **chưa từng thấy** vì chỉ cần biết "không gian chuẩn". Stage 1 đạt Binary Macro F1 = 0,84, Precision = 0,93.

### B.3 LightGBM (base learner GĐ1)
- Gradient Boosting trên cây; 127 lá, lr=0,05, n_estimators=1000 (early stopping 50), inverse-frequency weights. **Phân vùng đặc trưng cứng** (`logged_in`, `num_compromised`) → hiệu quả cho Probe, U2R.
- **Vai trò:** bổ sung FTT trong Stacking — sai trên mẫu khác FTT ($\rho$ thấp).

### B.4 Random Forest & KNN (thành viên Ensemble GĐ2)
- **RF** (150 cây, max_depth=25, class_weight=balanced_subsample): phân vùng không gian đặc trưng cục bộ; sai ở mẫu gần biên phức tạp cao chiều.
- **KNN** (K=16, distance-weighted): lazy learning theo lân cận; sai ở vùng thưa (thiểu số xa training points).
- **Vai trò:** ba inductive bias khác nhau (FTT/RF/KNN) → correlation thấp → ensemble giảm variance (xem C.4).

---

## C. Kiến trúc phân tầng & tổ hợp mô hình

### C.1 Two-Stage NSL-KDD (AE Gate + Stacking)
- **Vì sao 2 tầng thay vì phân loại 5 lớp trực tiếp:** gradient bị Normal (53,5%) + DoS (36,5%) chi phối; U2R (0,04%) không đủ gradient. Tách **phát hiện bất thường** (Stage 1 AE) khỏi **phân loại chi tiết** (Stage 2 Stacking).

### C.2 Stacking Ensemble + Meta-Learner (GĐ1, Stage 2)
- Hai base learner → nối xác suất → meta-learner học "khi nào tin ai":
$$\hat y=\text{Meta-LR}\big([\mathbf{p}_\text{FTT};\mathbf{p}_\text{LGBM}]\big),\quad \mathbf{p}\in\mathbb{R}^5\;(\text{đầu vào }10\text{ chiều})$$

- **Vào → Ra:** *Vào* = **xác suất dự đoán** của 2 base learner nối lại $[\mathbf{p}_\text{FTT};\mathbf{p}_\text{LGBM}]\in\mathbb{R}^{10}$ (không phải đặc trưng gốc); *Ra* = nhãn 1 trong 5 lớp. Meta-LR = hồi quy logistic học **trọng số cho từng ô xác suất**.
- **Vì sao đặt ở đây (tầng trên cùng của Stacking):** hai base learner mạnh ở lớp khác nhau (FTT giỏi R2L, LightGBM giỏi Probe/U2R). Thay vì trung bình cứng, Meta-LR **học có điều kiện "khi nào tin ai"** từ chính xác suất chúng đưa ra. Phải train trên **out-of-fold predictions** (dự đoán trên phần dữ liệu base learner chưa thấy) — nếu train trên cùng dữ liệu base learner đã fit thì xác suất quá lạc quan → Meta-LR học sai (leakage).
- **Meta-LR** train trên **out-of-fold predictions** để tránh leakage.
- **Bổ sung:** FTT R2L Recall 0,383 > LightGBM 0,208 (Attention học pattern đa đặc trưng); LightGBM tốt hơn ở Probe/U2R (phân nhánh cứng). → Macro F1 0,681.

### C.3 Two-Stage Cascade NIDS (GĐ2, CIC)
- **Vì sao:** 1-Stage 9 lớp bị Benign (83,4%) chi phối → Acc 98,21% nhưng Macro F1 chỉ 0,7831.
- **Stage 1 — Gating Network** (FTT nhị phân, ngưỡng bảo thủ):
$$\text{label}=\begin{cases}\text{Benign}&\hat p_{Benign}\ge0{,}85\\\text{Suspicious}&\hat p_{Benign}<0{,}85\end{cases}$$

- **Vào → Ra:** *Vào* = xác suất Benign $\hat p_{Benign}\in[0,1]$ do Gating FTT xuất ra; *Ra* = quyết định định tuyến {Benign→thoát, Suspicious→Stage 2}. Ngưỡng dịch từ 0,5 lên **0,85** = **thắt chặt điều kiện được coi là Benign**.
- **Vì sao đặt ngưỡng ở đây, và vì sao 0,85:** đây là điểm **đánh đổi Recall↔workload** của cả cascade. Chỉ những flow rất tự tin là Benign ($\ge85\%$) mới được thả; mọi cái còn ngờ vực đẩy sang Expert. Bỏ sót 1 tấn công ở cổng này là **mất vĩnh viễn** (Stage 2 không bao giờ thấy nó), nên ưu tiên recall — chấp nhận ~17,3% traffic sang Stage 2. Đặt ngưỡng tại tầng cổng (không tại Expert) để lỗi được "bắt sớm" và rẻ.
Ngưỡng **0,85** (không phải 0,5): ưu tiên **recall tấn công** — bỏ sót ở Stage 1 là mất vĩnh viễn; đổi lại workload Stage 2 ~17,3%. Lọc ~82,7% Benign.
- **Stage 2 — Expert Network** (FTT d=64, 34 đặc trưng): chỉ xử lý Suspicious → gradient tập trung phân biệt **giữa các loại tấn công**.

### C.4 Lý thuyết Ensemble & kiểm soát Variance
- **Phân rã Bias–Variance:**
$$\mathbb{E}[(y-f)^2]=\text{Bias}^2+\text{Variance}+\sigma^2_{noise}$$
- **Ensemble $M$ mô hình** (phương sai $\sigma^2$, tương quan trung bình $\rho$):
$$\text{Var}(\bar f)=\frac{\sigma^2}{M}\big[1+(M-1)\rho\big]$$

- **Vào → Ra:** *Vào* = số mô hình $M$, phương sai mỗi mô hình $\sigma^2$, tương quan lỗi trung bình $\rho\in[0,1]$; *Ra* = phương sai của **dự đoán trung bình** $\bar f$. Đây là công thức **giải thích/định hướng thiết kế**, không phải bước tính trong pipeline runtime.
- **Vì sao trích ở đây:** để **chứng minh vì sao chọn FTT+RF+KNN** thay vì 3 mạng cùng loại. Công thức cho thấy lợi ích ensemble bị chặn bởi $\rho$: nếu 3 mô hình sai giống nhau ($\rho\to1$) thì $\text{Var}(\bar f)\to\sigma^2$ — vô ích. Ba inductive bias khác nhau ép $\rho$ nhỏ → số hạng $(M{-}1)\rho$ nhỏ → variance giảm gần $\sigma^2/M$. Đây là căn cứ lý thuyết cho quyết định ở C.5.
$\rho\to0$: giảm variance $M$ lần; $\rho=1$: vô ích. **Kết luận:** ensemble chỉ hiệu quả khi các mô hình **sai trên mẫu khác nhau** — đúng với FTT+RF+KNN.

### C.5 Asymmetric Ensemble Voting (GĐ2)
Khi **chi phí FP ≠ FN** giữa các lớp, thay Majority Vote bằng luật bất đối xứng:

| Lớp | Vấn đề FTT | Quy tắc | Đánh đổi |
|---|---|---|---|
| Infiltration | FN cao (bỏ sót) | **OR(RF, KNN)** → Infiltration | ↑Recall, ↓Precision |
| Botnet | FP cao (báo nhầm) | **AND(FTT, RF, KNN)** → Botnet | ↑Precision, ↓Recall |
| Còn lại | cân bằng | Majority 2/3 | — |
- **Lý do:** bỏ sót Infiltration (0,001%) → data breach nhiều tháng → ưu tiên Recall; FTT nhầm Botnet nhiều → **alert fatigue** cho SOC → yêu cầu đồng thuận 3/3.
- **Kết quả:** Infiltration F1 0,5903→0,7407; Botnet F1 0,6512→0,7344; Macro F1 → **0,9294**.

---

## D. Kỹ thuật xử lý mất cân bằng lớp

### D.1 Focal Loss & Class-Balanced Focal Loss (cốt lõi)
- **Vấn đề gradient (CE):** batch 1000 Benign ($p_t=0{,}95$) + 10 BruteForce ($p_t=0{,}4$): tổng gradient Benign ≈ 51 vs BruteForce ≈ 9,16 → Benign áp đảo **5,6:1** dù mỗi mẫu BF mạnh hơn 18×.
- **Focal Loss** (Lin 2017): downweight mẫu dễ bằng $(1-p_t)^\gamma$:
$$\mathcal{L}_{FL}(p_t)=-\alpha_t(1-p_t)^\gamma\log(p_t)$$

- **Vào → Ra:** *Vào* = $p_t$ = xác suất mô hình gán cho **nhãn đúng** của mẫu (1 số $\in[0,1]$), $\alpha_t$ = trọng số theo lớp, $\gamma$ = độ tập trung; *Ra* = **giá trị loss của 1 mẫu**. Hệ số điều biến $(1-p_t)^\gamma$: mẫu dễ ($p_t$ cao) → gần 0; mẫu khó ($p_t$ thấp) → gần 1.
- **Vì sao đặt ở đây (thay Cross-Entropy làm hàm mục tiêu):** trong batch, Benign đông nên **tổng** gradient của chúng át lớp hiếm dù mỗi Benign đã dễ. Nhân $(1-p_t)^\gamma$ **tắt bớt đóng góp của mẫu đã học tốt**, dồn gradient vào mẫu khó (thường là tấn công hiếm) → đảo ngược tỷ lệ. Dùng đúng chỗ tính loss vì đây là nơi duy nhất tác động được lên hướng cập nhật gradient. **Lưu ý phạm vi:** chỉ chữa *mất cân bằng gradient*, không chữa *không phân tách* (PortScan WSL) — vì khi không có boundary, đổi trọng số loss vô nghĩa.
- **CB-Focal Loss** (Cui 2019) — alpha theo *effective number*:
$$\alpha_c=\frac{1-\beta}{1-\beta^{n_c}},\quad \beta=0{,}9999$$

- **Vào → Ra:** *Vào* = số mẫu lớp $c$ là $n_c$; *Ra* = trọng số lớp $\alpha_c$ đưa vào $\alpha_t$ của Focal Loss. Mẫu số $1-\beta^{n_c}$ = "effective number" — số mẫu *thực sự đóng góp thông tin* (mẫu trùng lặp gần như không thêm gì).
- **Vì sao dùng thay $1/n_c$ tại đây:** với lớp cực hiếm (Heartbleed 10 mẫu), $1/n_c$ cho trọng số khổng lồ → mô hình overfit vài mẫu đó và mất ổn định. CB-alpha có **trần tự nhiên = 1** (khi $n_c$ nhỏ), tăng mượt theo độ hiếm → an toàn khi tỷ lệ lớp chênh >1000:1. Tính **một lần trước train** từ phân phối lớp, rồi cắm vào $\alpha_t$ của công thức Focal.
- **Giới hạn quan trọng:** Focal Loss chỉ giải quyết **gradient imbalance** (hai lớp *phân tách được*). **Không giúp** khi hai lớp *không phân tách* (PortScan WSL): F1 7,5%→6,8% khi thêm Focal.
- **Dùng:** GĐ1 (γ=2), Gating (γ=2), Expert (γ=1,5), V8.5.

### D.2 SMOTE / SMOTE-ENN
$$\mathbf{x}_{new}=\mathbf{x}_i+\lambda(\mathbf{x}_{k_r}-\mathbf{x}_i),\quad \lambda\sim U(0,1)$$
Nội suy tuyến tính với láng giềng cùng lớp; **ENN** loại mẫu nhiễu gần biên.

- **Vào → Ra:** *Vào* = một mẫu lớp hiếm $\mathbf{x}_i$ và một láng giềng cùng lớp $\mathbf{x}_{k_r}$ (chọn ngẫu nhiên trong $K$-NN); $\lambda$ = tỉ lệ nội suy; *Ra* = **mẫu tổng hợp mới** nằm trên đoạn thẳng nối hai mẫu. Chạy **offline trên tập train** trước khi huấn luyện, làm tăng số mẫu lớp hiếm.
- **Vì sao đặt ở đây (tăng cường dữ liệu, không phải đổi loss):** khác Focal (đổi *trọng số* mẫu sẵn có), SMOTE **tạo thêm mẫu** để lấp vùng thưa của lớp hiếm → giúp mô hình cây/KNN có mật độ để học. Đặt ở bước tiền xử lý train (sau scaler) vì nội suy phải thực hiện trong không gian đặc trưng đã chuẩn hoá.
- **Giới hạn:** U2R 52 mẫu trong 122 chiều → mẫu tổng hợp gần như bản sao, không tăng diversity thực. Dùng thận trọng ở GĐ1.

### D.3 Weighted Random Sampling
$$w_i=\frac{N}{K\cdot n_c}\quad(\text{biến thể V8.5: } w_i=\sqrt{\tfrac{N}{K\,n_c}},\ \text{clip }[0{,}5;2{,}0])$$
Mỗi batch có đại diện mọi lớp. Biến thể căn bậc hai + clip tránh trọng số cực đoan. Dùng cho FTT các GĐ.

- **Vào → Ra:** *Vào* = tổng số mẫu $N$, số lớp $K$, số mẫu lớp của mẫu $i$ là $n_c$; *Ra* = **xác suất được chọn** $w_i$ của mẫu $i$ khi lấy mẫu tạo batch (lớp hiếm → $w_i$ lớn → hay được chọn hơn).
- **Vì sao đặt ở tầng sampler (không phải loss):** giải mất cân bằng ở **đầu vào** — đảm bảo mỗi mini-batch có đủ đại diện mọi lớp để gradient không "trắng" lớp hiếm. Bổ trợ Focal (giải ở đầu ra loss): dùng đồng thời cả hai. Biến thể $\sqrt{\cdot}$ + clip $[0{,}5;2]$ ở V8.5 để **không oversample quá mức** gây lặp mẫu và overfit lớp hiếm.

### D.4 Label Smoothing
$$y_c^{smooth}=(1-\varepsilon)y_c+\frac{\varepsilon}{C}$$
$\varepsilon=0{,}10$ ở V8.5 giảm overfitting. **Không** dùng cho CIC Expert (hại Heartbleed 10 mẫu).

- **Vào → Ra:** *Vào* = nhãn one-hot cứng $y_c\in\{0,1\}$; *Ra* = nhãn "mềm" — lớp đúng còn $1-\varepsilon+\varepsilon/C$, các lớp khác được $\varepsilon/C$ (thay vì 0). $C$ = số lớp, $\varepsilon$ = mức làm mềm.
- **Vì sao đặt ở đây (biến đổi nhãn mục tiêu trước khi tính loss):** nhãn cứng ép mô hình đẩy logit lớp đúng ra vô cực → **quá tự tin, overfit**. Làm mềm nhãn giữ khoảng cách logit hữu hạn → hiệu chỉnh xác suất tốt hơn, tổng quát hoá tốt hơn với V8.5 (dữ liệu Testbed nhỏ). **Tắt** ở CIC Expert vì với Heartbleed 10 mẫu, chia đều $\varepsilon/C$ làm loãng tín hiệu vốn đã ít.

### D.5 Hard Negative Mining (HNM) — đóng góp phương pháp
- **Ý tưởng:** sau mỗi vòng, thu **mẫu bị phân loại sai** (hard negatives), thêm vào train với trọng số $w_{hard}=2{,}0$, lặp 2 vòng:
$$\mathcal{L}_{HNM}=\sum_{i\notin hard}\mathcal{L}_{FL}(x_i)+w_{hard}\sum_{i\in hard}\mathcal{L}_{FL}(x_i)$$

- **Vào → Ra:** *Vào* = loss Focal của từng mẫu, chia hai nhóm: mẫu thường và **tập hard** (mẫu bị phân loại sai ở vòng trước, thu từ inference trên validation); *Ra* = tổng loss có **nhân đôi trọng số** phần hard. $w_{hard}=2{,}0$. Là **vòng lặp**: train → tìm mẫu sai → gán nhãn hard → train lại (2 vòng).
- **Vì sao đặt ở đây (điều chỉnh loss theo *mẫu*, không theo *lớp*):** confusion matrix cho thấy lỗi tập trung ở **vùng biên** giữa vài lớp (Botnet↔Benign, Infiltration↔Benign). Nhân trọng số đúng những mẫu sai đó → gradient dồn vào **tinh chỉnh biên quyết định** tại nơi đang sai, thay vì kéo đều cả lớp như class weight. Chỉ áp ở Expert Network (nơi phân biệt các lớp khó), sau khi đã có mô hình vòng 1 để biết "mẫu nào khó".
- **Khác class weight:** class weight tăng gradient **toàn bộ** lớp (kể cả mẫu đã đúng) → học *phân phối* lớp. HNM chỉ tăng mẫu **sai phía boundary** → học *biên quyết định*.
- **Nền tảng lý thuyết:** trường hợp đặc biệt của **Boosting** (AdaBoost, Schapire 1990) + liên hệ **Curriculum Learning** (Bengio 2009: dễ trước, khó sau).
- **Kết quả:** Botnet F1 0,4787→0,6512 (+36%), Infiltration 0,3821→0,5903 (+54,5%) — **vượt class weight ×10** (+13% / +17% tuyệt đối).
- **Giới hạn:** vô dụng khi hai lớp không phân tách (không tồn tại boundary tốt hơn) → chỉ gây noise.

### D.6 Boost-Minority Validation Set
- Đưa nhiều mẫu lớp hiếm vào **validation** để checkpoint selection phản ánh đúng hiệu năng lớp hiếm (R2L 40% vào val; U2R chỉ 5/52 vào val, giữ 47 cho train). Tránh chọn model theo Normal/DoS.

---

## E. Học chuyển giao & thích nghi miền (GĐ3)

### E.1 Covariate Shift
- **Định nghĩa:** $P_{source}(\mathbf{x})\neq P_{target}(\mathbf{x})$ trong khi $P(y\mid\mathbf{x})$ lý thuyết không đổi.
- **Trong đồ án:** CIC (switch Gigabit vật lý) vs Testbed WSL2 (Hyper-V NAT). Direct transfer: **Acc 99,55%→21,93%, MCC 0,9941→−0,015** (sai ngược, tệ hơn random).
- **Nguyên nhân:** overhead ảo hoá đổi packet size/timing; NAT Windows đổi ACK timing → ảnh hưởng IAT & flag counts; PowerTransformer fit trên CIC lệch với Testbed.
- **Vì sao Re-fit Scaler còn tệ hơn (21,93%→6,87%):** FTT gồm scaler $f_{CIC}$ + embedding $g_{CIC}$ học *cùng nhau*. Thay riêng scaler tạo **mâu thuẫn nội bộ** (embedding hiểu khoảng giá trị theo scaler cũ). **Nguyên tắc:** scaler và (một phần) tham số mô hình phải đổi **đồng thời**.

### E.2 Layer Freezing Fine-tuning
$$\theta_{fine}^{*}=\arg\min_{\theta_{fine}}\mathcal{L}\big(f_{\theta_{freeze},\theta_{fine}}(\mathbf{x}_{target}),y_{target}\big)$$

- **Vào → Ra:** *Vào* = mô hình đã học trên CIC với tham số chia hai: $\theta_{freeze}$ (tầng thấp, **giữ nguyên**) và $\theta_{fine}$ (tầng cao, **cho cập nhật**), cùng ít dữ liệu đích $\mathbf{x}_{target}$; *Ra* = bộ tham số tầng cao tối ưu $\theta_{fine}^{*}$ thích nghi miền mới. Chỉ tối ưu theo $\theta_{fine}$ (dưới dấu $\arg\min$).
- **Vì sao đặt ở đây (khi chuyển miền với ít dữ liệu):** dữ liệu Testbed quá ít để train lại cả mạng mà không overfit. Đóng băng tầng thấp giữ **kiến thức tổng quát** (đã đúng ở mọi miền), chỉ học lại phần **đặc thù miền** ở tầng cao → cần ít dữ liệu, ít quên. Đây là bước nằm **giữa** direct-transfer (thất bại) và retrain-hoàn-toàn (tốn dữ liệu).
- **Lý do phân tầng:** tầng Attention thấp học biểu diễn **tổng quát** (duration ngắn + byte thấp → PortScan); tầng cao học phân biệt **đặc thù miền**. Đóng băng tầng thấp (2/4) giữ kiến thức tổng quát, cập nhật tầng cao thích nghi miền mới.
- Phục hồi MCC −0,015 → 0,6825 (+69,4 điểm).

### E.3 Catastrophic Forgetting (CF)
$$CF=\frac{\text{Acc}_{source,before}-\text{Acc}_{source,after}}{\text{Acc}_{source,before}}\times100\%$$
Đóng băng 2/4 tầng đạt **CF = 0,61%** (giữ 99,39% hiệu năng CIC) — cân bằng plasticity/stability.

- **Vào → Ra:** *Vào* = accuracy trên **miền gốc CIC** đo *trước* và *sau* khi fine-tune sang Testbed; *Ra* = **% hiệu năng cũ bị mất**. CF thấp = quên ít.
- **Vì sao cần chỉ số này ở đây:** fine-tune sang miền mới có rủi ro "học miền mới nhưng quên miền cũ" (catastrophic forgetting). CF **định lượng cái giá** đó, để xác nhận Layer Freezing đạt được thích nghi *mà không* hi sinh năng lực trên CIC — bằng chứng cho lựa chọn đóng băng 2/4 tầng.

### E.4 Model Surgery (mở rộng đặc trưng)
- Ghép thêm $\Delta$ hàng vào ma trận embedding của Feature Tokenizer:
$$\mathbf{W}^{emb}_{new}=\begin{bmatrix}\mathbf{W}^{emb}_{old}\in\mathbb{R}^{k\times d}\\ \mathbf{W}^{emb}_{newrows}\in\mathbb{R}^{\Delta\times d}\end{bmatrix}$$
$\Delta$ hàng mới khởi tạo $\mathcal{N}(0,0{,}01)$, học trong fine-tune; $k$ hàng cũ **transplant giữ nguyên**.

- **Vào → Ra:** *Vào* = ma trận embedding cũ $\mathbf{W}^{emb}_{old}$ (ứng với $k=77$ đặc trưng) + $\Delta=3$ hàng mới; *Ra* = ma trận mở rộng cho $k{+}\Delta=80$ đặc trưng. Mỗi **hàng** = tham số $(\mathbf{w}_j,\mathbf{b}_j)$ token hoá một đặc trưng.
- **Vì sao làm ở đây (thay vì train mạng mới từ đầu):** khi thêm 3 đặc trưng đặc thù NAT, nếu train lại từ đầu sẽ **vứt toàn bộ kiến thức CIC**. Model Surgery **ghép thêm hàng** cho đặc trưng mới trong khi giữ nguyên 77 hàng cũ (transplant) → tận dụng lại mọi thứ đã học, chỉ học phần mới. Khởi tạo hàng mới rất nhỏ $\mathcal{N}(0,0{,}01)$ để lúc đầu chúng ~không ảnh hưởng, tránh sốc mô hình; rồi để fine-tune học dần. Tương thích FTT vì kiến trúc token-per-feature cho phép nối hàng độc lập (RF/XGBoost không có cấu trúc này).
- **Dùng:** $77\to80$ (thêm 3 đặc trưng đặc thù NAT: IAT_CV, Bwd_Pkt_Ratio, Pkt_Size_Ratio). Sau Layer Freezing: MCC 0,6825→0,7333.

> **Ghi chú:** Layer Freezing/Model Surgery là **thực nghiệm chẩn đoán trung gian** trong GĐ3; kết luận cuối là covariate shift quá lớn → **thu dữ liệu thật + retrain hoàn toàn V8.5**.

---

## F. Hệ thống IDS lai ghép (Snort + FT-Transformer)

### F.1 Snort — IDS dựa trên dấu hiệu (signature-based)
- Khớp pattern trong **payload/header gói tin**; latency **microsecond**; rất tốt cho tấn công đã biết.
- **Giới hạn:** không phát hiện zero-day/không có luật; không hoạt động với traffic mã hoá.

### F.2 So sánh & tính bổ sung Snort ↔ FTT

| Tiêu chí | Snort (rule) | FT-Transformer (ML) |
|---|---|---|
| Tầng phân tích | Packet (payload+header) | Flow (thống kê 5-tuple) |
| Độ trễ | Microsecond | Vài giây (near-realtime) |
| Tấn công chưa có luật | Không | Có |
| Traffic mã hoá | Không | Có |
| Nhạy covariate shift | Không | Có |

- **Bổ sung điển hình:** Snort bắt XSS/SQLi (payload) mà FTT bỏ sót; FTT bắt DoS slow-connection (duration/IAT bất thường) mà Snort bỏ sót; FTT bắt BruteForce SSH (nhiều kết nối thất bại).

### F.3 Pipeline End-to-End & Alert Aggregator
- Traffic → interface → **SONG SONG:** (1) Snort packet-level real-time; (2) tcpdump pcap → CICFlowMeter → PowerTransformer → FTT → ML alert. **Alert Aggregator** hợp nhất: cùng session ở cả hai nguồn → *confirmed alert*, tăng ưu tiên.

---

## G. Chỉ số đánh giá

### G.1 Macro F1 (chỉ số chính)
$$\text{Macro F1}=\frac{1}{K}\sum_{c=1}^{K}\frac{2P_cR_c}{P_c+R_c}$$
Trung bình F1 **không trọng số** → phạt nếu bất kỳ lớp nào bị bỏ qua. Lý do dùng: Accuracy bị Benign (82,7%) chi phối — model đoán toàn Benign vẫn đạt 82,7% Acc nhưng vô dụng.

- **Vào → Ra:** *Vào* = Precision $P_c$ và Recall $R_c$ của **từng lớp** (từ confusion matrix); *Ra* = 1 số $\in[0,1]$. Lấy F1 mỗi lớp rồi **trung bình đều** ($1/K$) — mọi lớp trọng số như nhau bất kể số mẫu.
- **Vì sao chọn làm chỉ số chính:** trọng số đều nghĩa là lớp Infiltration (33 mẫu) "nặng" ngang Benign (2 triệu mẫu) → mô hình buộc phải làm tốt **cả lớp hiếm**. Đúng mục tiêu bài toán IDS (bỏ sót tấn công hiếm là thảm hoạ). Đối lập Micro-F1/Accuracy vốn bị lớp đa số nuốt.

### G.2 MCC (Matthews Correlation Coefficient)
$$\text{MCC}=\frac{TP\cdot TN-FP\cdot FN}{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}$$
Nằm trong [−1,1]; **giá trị âm = phân loại sai hướng có hệ thống** (tệ hơn random). Dùng đánh giá robustness khi mất cân bằng cực đoan (chẩn đoán covariate shift: MCC=−0,015).

- **Vào → Ra:** *Vào* = cả 4 ô của confusion matrix (TP, TN, FP, FN); *Ra* = 1 hệ số tương quan $\in[-1,1]$ (+1 hoàn hảo, 0 = random, −1 = sai ngược hoàn toàn). Khác Accuracy/F1, MCC **dùng cả 4 ô** nên không bị đánh lừa khi một lớp áp đảo.
- **Vì sao dùng thêm ở chẩn đoán covariate shift:** khi direct-transfer, Accuracy 21,93% nghe "còn đỡ" nhưng MCC = **−0,015** phơi bày sự thật: mô hình phân loại **sai có hệ thống**, tệ hơn đoán bừa. Một số duy nhất tóm tắt được điều đó → công cụ lý tưởng để định lượng mức độ hỏng khi đổi miền.

### G.3 Balanced Accuracy
Trung bình **Recall mỗi lớp** — không phụ thuộc số mẫu mỗi lớp. V8.5: 91,1%.

---

## H. Bảng tra công thức nhanh

| # | Công thức | Thuộc |
|---|---|---|
| 1 | $\mathbf{e}_j=x_j\mathbf{w}_j+\mathbf{b}_j$ | Feature Tokenizer (B.1) |
| 2 | $\text{softmax}(QK^\top/\sqrt{d_k})V$ | Self-Attention (B.1) |
| 3 | $\text{MSE}=\frac1D\sum(x_i-\hat x_i)^2$ | Autoencoder Gate (B.2) |
| 4 | $\mathcal{L}_{FL}=-\alpha_t(1-p_t)^\gamma\log p_t$ | Focal Loss (D.1) |
| 5 | $\alpha_c=(1-\beta)/(1-\beta^{n_c})$ | CB-alpha (D.1) |
| 6 | $\mathbf{x}_{new}=\mathbf{x}_i+\lambda(\mathbf{x}_{k_r}-\mathbf{x}_i)$ | SMOTE (D.2) |
| 7 | $\mathcal{L}_{HNM}=\sum\mathcal{L}+w_{hard}\sum_{hard}\mathcal{L}$ | HNM (D.5) |
| 8 | $\text{Var}(\bar f)=\frac{\sigma^2}{M}[1+(M-1)\rho]$ | Ensemble variance (C.4) |
| 9 | $CF=\frac{\text{Acc}_{before}-\text{Acc}_{after}}{\text{Acc}_{before}}\times100\%$ | Catastrophic Forgetting (E.3) |
| 10 | $\psi_\lambda(x)$ Yeo-Johnson | PowerTransformer (A.3) |
| 11 | Macro F1, MCC | Chỉ số (G) |

---

## I. Từ viết tắt

| Viết tắt | Nghĩa |
|---|---|
| NIDS | Network Intrusion Detection System |
| FTT | FT-Transformer (Feature Tokenizer Transformer) |
| MHSA | Multi-Head Self-Attention |
| FFN / LN | Feed-Forward Network / LayerNorm |
| AE | Autoencoder |
| CB-Focal | Class-Balanced Focal Loss |
| SMOTE(-ENN) | Synthetic Minority Over-sampling (+ Edited Nearest Neighbours) |
| HNM | Hard Negative Mining |
| RF / KNN | Random Forest / K-Nearest Neighbors |
| Meta-LR | Meta Logistic Regression |
| MCC | Matthews Correlation Coefficient |
| CF | Catastrophic Forgetting |
| IAT | Inter-Arrival Time |
| NAT | Network Address Translation |
| WSL2 | Windows Subsystem for Linux 2 |
| SOC | Security Operations Center |

---

## J. Mạch liên kết lý thuyết (để trả lời "vì sao dùng")

1. **Dữ liệu flow (A.1)** cho phép làm việc với traffic mã hoá nhưng mất payload → sinh ra giới hạn với Infiltration/Botnet (F, và hạn chế Chương 6).
2. **FT-Transformer (B.1)** được chọn không chỉ vì độ chính xác mà vì **cho phép Layer Freezing + Model Surgery (E)** — điều RF/XGBoost không làm được.
3. **Mất cân bằng (D)** giải bằng chuỗi kỹ thuật *bổ sung*: Focal/CB-Focal cho gradient, Weighted Sampling cho batch, HNM cho boundary — mỗi cái giải một khía cạnh khác nhau; HNM ≠ class weight (D.5).
4. **Phân tầng (C)** để gradient lớp hiếm không bị Benign nuốt; **Ensemble (C.4–C.5)** để giảm variance và điều chỉnh theo chi phí FP/FN thực tế.
5. **Thích nghi miền (E)** là hệ quả tất yếu khi mang model lab ra môi trường thật — và bằng chứng Re-fit Scaler thất bại (E.1) là phát hiện lý thuyết đáng chú ý nhất.
6. **Lai ghép Snort+FTT (F)** vì mỗi tầng có điểm mù mà tầng kia bù được — không hướng đơn lẻ nào đủ.
