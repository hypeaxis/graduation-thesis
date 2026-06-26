# Chương 4. Phân tích lý thuyết

Chương 3 trình bày phương pháp đề xuất và các quyết định thiết kế. Chương này phân tích lý thuyết các quyết định quan trọng nhất — những quyết định không hiển nhiên mà thực nghiệm đơn thuần không đủ để giải thích. Phần 4.1 phân tích cơ chế Focal Loss trong điều kiện mất cân bằng cực đoan. Phần 4.2 phân tích tại sao PortScan không thể phân tách trong môi trường WSL2. Phần 4.3 phân tích cơ sở lý thuyết của Hard Negative Mining so với tăng class weight. Phần 4.4 phân tích lý thuyết Ensemble Voting và kiểm soát variance. Phần 4.5 phân tích cơ sở của phương pháp thích nghi miền — tại sao Re-fit Scaler thất bại. Phần 4.6 phân tích giới hạn căn bản của phân tích flow tĩnh với tấn công Infiltration và Botnet.

---

## 4.1 Phân tích Focal Loss trong điều kiện mất cân bằng cực đoan

Để hiểu tại sao Focal Loss vượt trội Cross-Entropy trong bài toán IDS, cần phân tích cơ chế gradient — cụ thể là đóng góp gradient của từng mẫu trong quá trình tối ưu.

### 4.1.1 Phân tích gradient với Cross-Entropy

Xét một batch gồm 1000 mẫu Benign dễ phân loại ($p_t = 0{,}95$) và 10 mẫu BruteForce khó ($p_t = 0{,}4$):

$$\text{Tổng gradient Benign} \propto 1000 \times (-\log 0{,}95) \approx 1000 \times 0{,}051 = 51 \tag{eq:grad-benign}$$

$$\text{Tổng gradient BruteForce} \propto 10 \times (-\log 0{,}4) \approx 10 \times 0{,}916 = 9{,}16 \tag{eq:grad-bf}$$

Dù mỗi mẫu BruteForce mang gradient lớn hơn 18× mỗi mẫu Benign, tổng gradient Benign vẫn áp đảo 5,6:1. Mô hình bị kéo liên tục về phía tối ưu Benign và ít cơ hội học từ mẫu thiểu số.

### 4.1.2 Focal Loss đảo ngược ưu thế gradient

Với Focal Loss ($\gamma=2$), hệ số $(1-p_t)^2$ downweight mạnh mẫu dễ:

$$\text{Tổng gradient Benign (FL)} \propto 1000 \times (1-0{,}95)^2 \times 0{,}051 \approx 0{,}128 \tag{eq:grad-benign-fl}$$

$$\text{Tổng gradient BruteForce (FL)} \propto 10 \times (1-0{,}4)^2 \times 0{,}916 \approx 3{,}30 \tag{eq:grad-bf-fl}$$

Tỷ lệ **đảo ngược**: BruteForce đóng góp gradient lớn hơn Benign 25,8:1.

**Bảng so sánh đóng góp gradient (batch 1000 Benign + 10 BruteForce):**

| Mẫu | $p_t$ | Gradient/mẫu | Hệ số FL | Gradient FL/mẫu | Tổng (×N) CE | Tổng (×N) FL |
|---|---|---|---|---|---|---|
| Benign (1000 mẫu) | 0,95 | 0,051 | 0,0025 | 0,000128 | 51 | 0,128 |
| BruteForce (10 mẫu) | 0,40 | 0,916 | 0,360 | 0,330 | 9,16 | 3,30 |
| **Tỷ lệ BF/Benign** | | 18× | — | 2578× | **1:5,6** | **25,8:1** |

### 4.1.3 Tại sao Focal Loss không giải quyết được PortScan WSL

Focal Loss là giải pháp cho vấn đề **gradient imbalance** — xảy ra khi hai lớp có thể phân tách nhưng một lớp áp đảo gradient. Khi hai lớp không thể phân tách trong không gian đặc trưng (PortScan WSL và Benign nằm trong cùng vùng đặc trưng), Focal Loss không giúp được — không có boundary nào để học tốt hơn bất kể trọng số gradient.

Bằng chứng: PortScan F1 từ 7,5% xuống 6,8% khi thêm Focal Loss $\gamma=2$ (không cải thiện, thậm chí giảm nhẹ). Phân tích chi tiết tại Mục 4.2.

### 4.1.4 Class-Balanced Focal Loss

Alpha theo effective number ổn định hơn inverse-frequency khi tỷ lệ lớp chênh lệch >1000:1:

$$\alpha_c = \frac{1 - \beta}{1 - \beta^{n_c}}, \quad \beta = 0{,}9999 \tag{eq:cb-alpha}$$

Khi $n_c$ lớn (Benign, hàng triệu mẫu): $\beta^{n_c} \to 0$, $\alpha_c \to 1-\beta = 0{,}0001$ — rất nhỏ.
Khi $n_c$ nhỏ (Heartbleed, 10 mẫu): $\beta^{10} \approx 0{,}999$, $\alpha_c \to (1-\beta)/(1-\beta) = 1$ — rất lớn.

So với inverse-frequency đơn thuần ($\alpha_c = 1/n_c$): CB-alpha có upper bound tự nhiên tại 1, tránh trọng số cực đoan khi $n_c$ rất nhỏ.

---

## 4.2 Phân tích tính không phân tách của PortScan trong môi trường WSL2

### 4.2.1 Đặc trưng PortScan trên phần cứng thực (CIC-IDS-2017)

Khi nmap quét từ máy tấn công qua switch Gigabit đến victim, CICFlowMeter trên victim capture được hàng trăm flow TCP SYN ngắn đến nhiều cổng khác nhau:

| Đặc trưng | Giá trị đặc trưng PortScan (CIC) | Giá trị Benign HTTP |
|---|---|---|
| `Flow_Duration` | Rất ngắn (< 1ms) | Dài (100ms – vài giây) |
| `Fwd_Pkt_Len_Max` | ~60 bytes (SYN packet) | 100–1500 bytes |
| `Flow_IAT_Mean` | Thấp (nhiều packet song song) | Thay đổi theo nội dung |
| `SYN_flag_count` | Cao | Thấp (1/connection) |
| `FIN_flag_count` | ~0 (SYN bị reject → RST, không FIN) | Có (connection close) |
| Số flow mỗi session | Hàng trăm đến port đích khác nhau | 1–5 flows |

Pattern này **có thể phân tách** từ Benign trong không gian CICFlowMeter — nhiều đặc trưng cùng hướng về phía PortScan.

### 4.2.2 Tại sao NAT phá vỡ đặc trưng PortScan

Khi nmap gửi SYN đến IP Windows host (WSL Mirrored Networking), gói tin đi qua:

```
Kali → WiFi Router → Windows 11 host → Hyper-V Virtual Switch → WSL2 eth0
```

NAT của Windows xử lý gói tin trước khi đến WSL interface. Kết quả:

1. **Consolidation:** nmap gửi 65.536 SYN probes → NAT nhóm thành ~7 flow theo cấu trúc session riêng của Hyper-V
2. **Timing thay đổi:** overhead ảo hóa thêm độ trễ ngẫu nhiên → `Flow_IAT_Mean` không còn thấp đặc trưng
3. **Flow duration tăng:** mỗi "flow" PortScan WSL là một kết nối dài thay vì hàng trăm kết nối ngắn
4. **Byte count tăng:** do consolidation, mỗi flow mang nhiều packet hơn

| Đặc trưng | PortScan CIC | PortScan WSL | Benign HTTP |
|---|---|---|---|
| `Flow_Duration` | < 1ms | **50–500ms** | 100ms – vài giây |
| Số flow/session | Hàng trăm | **~7** | 1–5 |
| `SYN_flag_count` | Cao | Thấp (per-flow) | Thấp |
| Phân biệt với Benign? | **Có** | **Không** | — |

### 4.2.3 Bằng chứng không phân tách

| Cấu hình | PortScan F1 | Kết luận |
|---|---|---|
| FTT, CE Loss, class\_weight=1.0 | 7,5% | Baseline — không học được |
| FTT, Focal Loss $\gamma=2$ | 6,8% | Không cải thiện (không phải vấn đề gradient) |
| FTT, class\_weight PortScan ×5 | 8,1% | Không cải thiện |
| Random Forest, 150 cây | 5,2% | Cùng thất bại |
| KNN, K=5 | 4,9% | Cùng thất bại |
| **FTT, inject CIC Friday PortScan** | **100%** | **Giải pháp dữ liệu** |

Kết quả nhất quán thất bại qua **nhiều thuật toán và inductive bias khác nhau** là bằng chứng mạnh rằng vấn đề nằm ở **dữ liệu thu thập**, không phải mô hình. Khi nhiều thuật toán khác nhau đều thất bại, nguyên nhân gần như chắc chắn là chất lượng hoặc tính đại diện của dữ liệu.

---

## 4.3 Cơ sở lý thuyết của Hard Negative Mining

### 4.3.1 HNM vs tăng class weight: phân tích điểm khác biệt

**Class weight tăng đồng đều:** đặt $w_{Botnet} = 10$ → mọi mẫu Botnet (kể cả mẫu đã phân loại đúng dễ dàng) được tăng gradient 10×. Mô hình học **phân phối Botnet** tốt hơn nhưng không học **boundary** tốt hơn.

**Hard Negative Mining:** chỉ tăng trọng số cho mẫu đang bị **phân loại sai** — tức là mẫu nằm ở sai phía boundary. Mô hình được buộc phải **tinh chỉnh boundary quyết định** tại chính xác những vùng đang sai.

**[Hình 4.1: So sánh class weight vs HNM — trái: class weight tăng đồng đều gradient tất cả Botnet; phải: HNM chỉ tăng gradient mẫu gần/sai phía boundary]**

### 4.3.2 Liên hệ với AdaBoost và Curriculum Learning

HNM là trường hợp đặc biệt của **Boosting paradigm** (Schapire, 1990):
- AdaBoost: sau mỗi weak learner, tăng trọng số cho mẫu bị phân loại sai để weak learner tiếp theo tập trung vào chúng
- HNM trong đề tài: sau mỗi vòng huấn luyện, thu thập hard negatives (mẫu sai) và tăng trọng số trong vòng tiếp theo

Cũng liên hệ với **Curriculum Learning** (Bengio et al., 2009): học easy samples trước (vòng 1 không HNM), sau đó progressive hard samples (vòng HNM). Hard negatives sau vòng 1 là các mẫu "khó nhất" theo định nghĩa của mô hình đã học.

### 4.3.3 Phân tích định lượng: HNM vs class weight

| Phương án | Botnet F1 | Infiltration F1 |
|---|---|---|
| Không HNM, không class weight | 0,4787 | 0,3821 |
| Class weight Botnet ×5 | 0,5103 | 0,4012 |
| Class weight Botnet ×10 | 0,5218 | 0,4198 |
| HNM 1 vòng ($w_{hard}=2$) | 0,5934 | 0,5213 |
| HNM 2 vòng ($w_{hard}=2$) | **0,6512** | **0,5903** |

HNM 2 vòng vượt trội class weight ×10 với **+13% Botnet F1** và **+17% Infiltration F1**.

### 4.3.4 Giới hạn HNM

HNM hiệu quả khi hai lớp **có thể phân tách** nhưng boundary chưa được học đúng. Với PortScan/Benign WSL — hai lớp không phân tách — HNM không giúp được vì không tồn tại boundary nào để học tốt hơn. Tăng trọng số các mẫu PortScan không phân tách chỉ gây noise cho mô hình.

---

## 4.4 Lý thuyết Ensemble Voting và kiểm soát Variance

### 4.4.1 Phân tích Bias-Variance

Lỗi tổng quát hóa của mô hình phân loại:

$$\mathbb{E}\!\left[(y - f(\mathbf{x}))^2\right] = \underbrace{\left(\mathbb{E}[f(\mathbf{x})] - y\right)^2}_{\text{Bias}^2} + \underbrace{\mathbb{E}\!\left[(f(\mathbf{x}) - \mathbb{E}[f(\mathbf{x})])^2\right]}_{\text{Variance}} + \sigma^2_{\text{noise}} \tag{eq:bias-variance}$$

### 4.4.2 Ensemble giảm Variance

Với $M$ mô hình có cùng phương sai $\sigma^2$ và correlation trung bình $\rho$:

$$\text{Var}(\bar{f}) = \frac{\sigma^2}{M} + \frac{M-1}{M}\, \rho\, \sigma^2 = \frac{\sigma^2}{M}\,\bigl[1 + (M-1)\rho\bigr] \tag{eq:ensemble-variance}$$

**Hai cực đoan:**
- $\rho \to 0$ (hoàn toàn độc lập): $\text{Var}(\bar{f}) \to \sigma^2/M$ — ensemble $M$ lần so với đơn lẻ
- $\rho = 1$ (hoàn toàn tương quan): $\text{Var}(\bar{f}) = \sigma^2$ — ensemble không giúp gì

**Kết luận quan trọng: để ensemble hiệu quả, các mô hình thành phần phải sai trên những mẫu khác nhau ($\rho$ thấp).**

### 4.4.3 Tại sao FTT + RF + KNN có $\rho$ thấp

| Mô hình | Inductive Bias | Sai trên mẫu nào |
|---|---|---|
| FT-Transformer | Học tương tác đặc trưng qua Attention — global | Mẫu có tương tác đặc trưng phức tạp không nhất quán trong training |
| Random Forest (150 cây, max_depth=25) | Phân vùng không gian đặc trưng — cục bộ | Mẫu gần biên quyết định phức tạp trong không gian cao chiều |
| KNN (K=16, distance-weighted) | Lân cận cục bộ — lazy learning | Mẫu trong vùng thưa, xa training points |

Ba inductive bias khác nhau → sai trên các tập mẫu khác nhau → correlation thấp → ensemble giảm variance hiệu quả.

### 4.4.4 Asymmetric Voting: khi chi phí FP ≠ FN

**Majority Voting (2/3):** tối ưu khi chi phí FP và FN bằng nhau cho tất cả lớp.

**Asymmetric Voting** phản ánh chi phí khác nhau giữa các lớp:

| Lớp | Vấn đề | Chi phí FP | Chi phí FN | Quy tắc |
|---|---|---|---|---|
| Infiltration | FTT underpredicts (FN cao) | Trung bình (false alarm) | Rất cao (bỏ sót data breach) | OR(RF, KNN) → Infiltration |
| Botnet | FTT overpredicts (FP cao) | Cao (alert fatigue) | Trung bình (một sự cố) | AND(FTT, RF, KNN) → Botnet |
| Các lớp khác | Cân bằng | — | — | Majority (2/3) |

**Lý do Infiltration Priority Rule:** Infiltration chiếm 0,001% dữ liệu và bỏ sót một sự cố Infiltration thường dẫn đến data exfiltration không phát hiện trong nhiều tháng. Chi phí FN rất cao → tăng Recall đổi lấy giảm Precision là đánh đổi hợp lý.

**Lý do Botnet Consensus Rule:** FTT sau HNM có FP cao với Botnet (nhiều Benign long-idle bị nhầm). Alert fatigue — đội ngũ SOC nhận hàng trăm false alarm mỗi ngày bắt đầu bỏ qua cả cảnh báo thật. Yêu cầu đồng thuận 3/3 giảm FP mạnh, đổi lấy giảm Recall vừa phải.

---

## 4.5 Cơ sở của phương pháp thích nghi miền

*(Mục này cung cấp nền tảng lý thuyết giải thích kết quả chẩn đoán covariate shift trong Giai đoạn 3)*

### 4.5.1 Tại sao Re-fit Scaler thất bại

Mô hình FTT bao gồm hai thành phần học được từ CIC:
1. **PowerTransformer** $f_{CIC}$: ánh xạ $X_{raw} \to X_{scaled}$ với phân phối CIC
2. **FTT embedding** $g_{CIC}$: ánh xạ $X_{scaled} \to H_{latent}$, được học với đầu vào có phân phối $f_{CIC}(X_{CIC})$

Khi thay $f_{CIC}$ bằng $f_{Testbed}$ (Re-fit Scaler trên Testbed):
- $X_{scaled}^{new} = f_{Testbed}(X_{raw}^{Testbed})$ có phân phối khác $f_{CIC}(X_{raw}^{CIC})$
- Nhưng $g_{CIC}$ vẫn được học để xử lý phân phối cũ → **mâu thuẫn nội bộ**
- Token embedding của FTT đã học "giá trị $x_j$ trong khoảng [a,b] theo scaler CIC có ý nghĩa Z" → khi scaler thay đổi, khoảng giá trị tương ứng với ý nghĩa đó dịch chuyển, nhưng embedding không biết

Kết quả: Accuracy từ 21,93% (direct transfer) giảm xuống 6,87% (Re-fit Scaler) — **xác nhận thực nghiệm** cho phân tích lý thuyết này.

**Nguyên tắc:** khi fine-tune mô hình cho miền mới, scaler phải được thay đổi **cùng lúc** với ít nhất một phần tham số mô hình — không thể thay đổi một trong hai một cách độc lập.

### 4.5.2 Tại sao Layer Freezing hiệu quả

Các tầng Attention thấp học **biểu diễn tổng quát** bất biến theo môi trường thu thập:
- Tầng 1-2: "duration ngắn + byte count thấp → flow ngắn", "SYN flag cao → scan"
- Tầng 3-4: học phân biệt Botnet heartbeat vs Benign idle — đặc thù phân phối CIC

Khi đóng băng tầng 1-2 và chỉ cập nhật tầng 3-4 + classification head:
- Tầng 1-2 giữ lại kiến thức tổng quát (không cần re-learn từ ít dữ liệu Testbed)
- Tầng 3-4 học lại biểu diễn đặc thù Testbed với scaler mới
- Catastrophic Forgetting $CF = 0{,}61\%$ — cân bằng plasticity và stability đạt được

---

## 4.6 Giới hạn của dữ liệu flow-based tĩnh: Infiltration và Botnet

### 4.6.1 Bản chất tấn công Infiltration

Infiltration trong CIC-IDS-2017 là tấn công leo thang đặc quyền qua ứng dụng (Dropbox, iexplore). Các flow cá nhân CICFlowMeter bắt được là HTTP/HTTPS requests bình thường — đặc trưng flow không phân biệt được so với Benign web browsing.

**Giới hạn căn bản:** CICFlowMeter trích xuất thống kê từ 5-tuple. Infiltration không có dấu hiệu ở tầng này — thông tin tấn công nằm trong **payload** (file download bất thường, privilege escalation API call) mà flow statistics không nắm bắt được.

Pattern bất thường của Infiltration chỉ lộ ra khi quan sát **chuỗi flow theo thời gian**:
- Tần suất kết nối đến server bên ngoài tăng bất thường
- DNS query đến domain chưa từng thấy
- Upload data bất thường vào đêm khuya

Đây là vấn đề **phân tích chuỗi thời gian** (temporal analysis) — không phải phân loại điểm dữ liệu đơn lẻ. Mô hình phân loại flow đơn lẻ (FTT, RF, KNN) về nguyên lý không thể nắm bắt thông tin ngữ cảnh này.

### 4.6.2 Bản chất tấn công Botnet C2

Botnet C2 communication có pattern periodic heartbeat ở tần suất thấp — mỗi flow C2 riêng lẻ trông như Benign DNS/HTTP. Pattern bất thường (periodic với interval cố định, DNS đến domain bất thường) chỉ rõ khi quan sát nhiều flow liên tiếp theo thời gian.

Lý do Botnet F1 dù cải thiện đáng kể (0,4787 → 0,7344 nhờ HNM + Ensemble) vẫn là một trong những lớp thấp nhất: giới hạn tương tự Infiltration, cộng thêm sự đa dạng cao của các biến thể Botnet C2 trong CIC.

### 4.6.3 Hệ quả và hướng giải quyết

| Giới hạn | Tấn công bị ảnh hưởng | Hướng giải quyết |
|---|---|---|
| Flow đơn lẻ không đủ context | Infiltration, Botnet | Session aggregation (nhiều flow → 1 vector dài) |
| Không có payload analysis | Infiltration, Web Attack | DPI tích hợp + multi-modal (flow + payload encoder) |
| Không phân tích temporal | Infiltration, Botnet | Graph-based temporal analysis, LSTM trên flow sequence |

Các hướng này nằm ngoài phạm vi đề tài hiện tại nhưng là mở rộng tự nhiên tiếp theo.

---

## Kết chương

Chương này phân tích lý thuyết sáu quyết định thiết kế. Focal Loss với CB-alpha phù hợp hơn Cross-Entropy khi tỷ lệ lớp chênh lệch >1000:1, nhưng không giải quyết được vấn đề không phân tách. PortScan không thể phân tách trong WSL2 vì NAT thay đổi cơ bản phân phối đặc trưng flow — giới hạn không thể vượt qua bằng điều chỉnh thuật toán, chỉ giải quyết được bằng dữ liệu surrogate. Hard Negative Mining cải thiện boundary learning tốt hơn tăng class weight đơn thuần: +13% Botnet F1 so với class weight ×10. Ensemble hoạt động vì FTT + RF + KNN có inductive bias khác nhau tạo correlation thấp. Re-fit Scaler thất bại vì tạo mâu thuẫn giữa scaler mới và embedding cũ — cần cập nhật đồng thời. Infiltration và Botnet bị giới hạn cơ bản bởi flow-level analysis — cải thiện thực sự đòi hỏi temporal analysis hoặc DPI. Chương 5 trình bày kết quả thực nghiệm kiểm chứng tất cả các phân tích lý thuyết này.
