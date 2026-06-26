# Chương 1. Giới thiệu đề tài

Phát hiện xâm nhập mạng là bài toán phân loại lưu lượng mạng thành Benign và các loại tấn công trong thời gian thực. Tần suất và thiệt hại của tấn công mạng tăng liên tục — theo báo cáo IBM 2023, chi phí trung bình một vụ vi phạm dữ liệu đạt 4,45 triệu USD và thời gian phát hiện trung bình là 204 ngày. Chương này đặt vấn đề và phân tích tại sao các hướng tiếp cận hiện hành chưa giải quyết triệt để bài toán này, từ đó dẫn đến định hướng giải pháp của đồ án. Phần 1.1 mô tả bài toán và ba thách thức cốt lõi. Phần 1.2 phân tích giới hạn của IDS dựa trên chữ ký, IDS thống kê và IDS học máy truyền thống. Phần 1.3 trình bày mục tiêu và kiến trúc giải pháp lai ghép qua ba giai đoạn nghiên cứu. Phần 1.4 liệt kê bốn đóng góp chính. Phần 1.5 mô tả bố cục các chương còn lại.

---

## 1.1 Bài toán phát hiện xâm nhập mạng và ba thách thức cốt lõi

### 1.1.1 Định nghĩa bài toán

Hệ thống phát hiện xâm nhập mạng (NIDS — Network Intrusion Detection System) phân tích lưu lượng mạng và phân loại mỗi flow thành một trong các lớp: Benign (lưu lượng bình thường) hoặc một trong các nhóm tấn công (DoS, DDoS, BruteForce, PortScan, Web Attack, Botnet, Infiltration, v.v.).

**Flow mạng** là tập hợp các gói tin TCP/UDP có cùng 5-tuple (IP nguồn, IP đích, cổng nguồn, cổng đích, giao thức) trong một phiên giao tiếp. Từ mỗi flow, CICFlowMeter trích xuất 77–80 đặc trưng thống kê: byte counts, packet size statistics, inter-arrival times, TCP flag counts, flow duration.

**Yêu cầu:** phát hiện trong thời gian thực (latency < 1 phút mỗi flow), False Alarm Rate thấp (SOC không thể xử lý hàng nghìn false alarm mỗi ngày), và Recall cao đối với tấn công nghiêm trọng (bỏ sót Infiltration hay Botnet có hậu quả rất lớn).

**[Hình 1.1: Vòng đời tấn công mạng — từ Reconnaissance (PortScan) đến Exploitation (Web Attack, BruteForce) đến Exfiltration (Infiltration, Botnet C2)]**

### 1.1.2 Ba thách thức cốt lõi

**Thách thức 1 — Mất cân bằng lớp cực đoan:**
Trong lưu lượng mạng thực tế, Benign chiếm 83–99% và nhiều loại tấn công nghiêm trọng nhất (Infiltration, Heartbleed) chiếm dưới 0,01%. Tỷ lệ Benign:Infiltration có thể lên đến 65.000:1. Mô hình phân loại đa lớp thông thường bị dominated bởi Benign và không học được pattern tấn công thiểu số.

**Thách thức 2 — Covariate shift giữa môi trường train và deploy:**
Các benchmark dataset (NSL-KDD năm 1998, CIC-IDS-2017 trên switch vật lý Gigabit) có phân phối đặc trưng khác với môi trường triển khai thực (card mạng ảo Hyper-V, NAT Windows). Mô hình huấn luyện trên CIC-IDS-2017 đạt Accuracy 99,55% nhưng chỉ đạt 21,93% khi áp dụng trực tiếp lên Testbed WSL2 — sụt giảm 77,62%.

**Thách thức 3 — Giới hạn của bất kỳ hướng tiếp cận đơn lẻ nào:**
Rule-based IDS (Snort) phát hiện nhanh nhưng bỏ sót tấn công chưa có chữ ký. ML-based IDS phát hiện pattern thống kê nhưng cần thời gian tích lũy flow và bỏ sót các tấn công có flow statistics giống Benign. Không hướng tiếp cận nào đơn lẻ đủ để phủ toàn bộ vector tấn công.

---

## 1.2 Phân tích giới hạn các hướng tiếp cận hiện hành

### 1.2.1 IDS dựa trên chữ ký (Signature-based)

Snort, Suricata: phát hiện tấn công đã biết bằng cách khớp pattern trong payload hoặc header gói tin. Latency thấp (microsecond per packet).

**Giới hạn:** không phát hiện được tấn công zero-day hoặc tấn công không có signature. Tấn công DoS slowhttptest tạo HTTP request hoàn toàn hợp lệ — không khớp signature nào — nhưng có pattern thống kê bất thường ở tầng flow.

### 1.2.2 IDS dựa trên phân tích thống kê truyền thống

Random Forest, SVM trên đặc trưng flow thống kê. Không cần viết rule thủ công, có thể phát hiện tấn công chưa thấy.

**Giới hạn với mất cân bằng:** Random Forest với class\_weight="balanced" đạt F1 thấp trên Infiltration (<0,5 trong thực nghiệm) vì bootstrap sampling không đảm bảo đủ đại diện cho lớp <0,01%. Giới hạn với covariate shift: RF fit trên CIC không thể tái sử dụng cho Testbed vì phân vùng không gian đặc trưng bị vô hiệu hóa khi phân phối thay đổi.

### 1.2.3 IDS dựa trên Deep Learning (MLP, CNN, LSTM)

MLP đa lớp học biểu diễn phi tuyến phức tạp hơn RF. CNN và LSTM học pattern temporal. Tuy nhiên, tất cả đều gặp cùng vấn đề gradient imbalance với lớp thiểu số.

**FT-Transformer (Gorishniy et al., 2021):** cơ chế Attention trong Feature Tokenizer cho phép học tương tác **giữa các đặc trưng** — thay vì xử lý đặc trưng độc lập như MLP. Điều này đặc biệt có giá trị cho NIDS: tấn công Infiltration không phân biệt được từ một đặc trưng đơn lẻ mà chỉ bộc lộ qua tổ hợp (connection destination bất thường + upload data cao + thời điểm khuya đêm). FTT phù hợp hơn MLP/RF cho dữ liệu tabular có tương tác đặc trưng phức tạp.

---

## 1.3 Mục tiêu và kiến trúc giải pháp

### 1.3.1 Mục tiêu đồ án

Xây dựng và đánh giá hệ thống NIDS lai ghép (Snort + FT-Transformer) có khả năng:
1. Phân loại đa lớp với Macro F1 > 0,9 trên bộ dữ liệu benchmark CIC-IDS-2017 (9 lớp)
2. Đạt Macro F1 > 0,9 trên Testbed thực với dữ liệu tấn công thu thập thực trong môi trường WSL2
3. Phát hiện bổ sung qua tích hợp Snort (rule-based) và FTT (ML-based) trong thử nghiệm End-to-End

### 1.3.2 Ba giai đoạn nghiên cứu

**[Hình 1.2: Sơ đồ ba giai đoạn — NSL-KDD → CIC-IDS-2017 → Testbed, mũi tên thể hiện nhân-quả giữa kết quả giai đoạn trước và vấn đề giai đoạn sau]**

**Giai đoạn 1 — Mô hình nền tảng trên NSL-KDD:**
Xây dựng kiến trúc Two-Stage (Autoencoder Anomaly Gate + Stacking Ensemble FTT+LightGBM→Meta-LR). Phát triển chiến lược xử lý mất cân bằng: CB-Focal Loss, Boost-Minority Val Set, WeightedRandomSampler. Kết quả: Macro F1 = 0,6809, xác nhận giới hạn ceiling của NSL-KDD do protocol shift.

**Giai đoạn 2 — Two-Stage Cascade NIDS trên CIC-IDS-2017:**
Tái thiết kế kiến trúc cho 9 lớp (Benign + 8 nhóm tấn công gộp từ 15 nhãn gốc). Phát triển Two-Stage Cascade (Gating FTT nhị phân + Expert FTT đa lớp), Hard Negative Mining 2 vòng, và Asymmetric Ensemble Voting với hai quy tắc bất đối xứng. Kết quả: Macro F1 = 0,9294.

**Giai đoạn 3 — Tái huấn luyện trên Testbed nội bộ:**
Chẩn đoán covariate shift (21,93% Accuracy direct transfer, MCC=-0,015). Thu thập dữ liệu tấn công thực từ máy Kali Linux trong mạng LAN, xây dựng dataset V8.5 (111.825 flows, 5 lớp). Sử dụng dữ liệu surrogate CIC PortScan cho lớp không thu thập được trong WSL2. Tái huấn luyện hoàn toàn FTT V8.5. Kết quả: Macro F1 = 91,7% trên val set đa dạng miền.

---

## 1.4 Bốn đóng góp chính

**Đóng góp 1 — Kiến trúc Two-Stage Cascade với Asymmetric Ensemble Voting:**
Gating Network FTT nhị phân (d=128, 4 lớp Attention, 8 heads, ngưỡng 0,85) lọc 82,7% traffic Benign trước khi Expert Network xử lý 9 lớp. Asymmetric Voting (Infiltration Priority Rule + Botnet Consensus Rule) tăng Infiltration F1 từ 0,5903 lên 0,7407 và Botnet F1 từ 0,6512 lên 0,7344 so với Expert Network đơn lẻ sau HNM. Macro F1 = 0,9294 trên CIC-IDS-2017.

**Đóng góp 2 — Hard Negative Mining 2 vòng cho lớp tấn công hiếm:**
Phương pháp thu thập mẫu bị phân loại sai sau mỗi vòng huấn luyện và tái huấn luyện với trọng số $w_{hard}=2{,}0$. Cải thiện Botnet F1: 0,4787→0,6512 (+36%) và Infiltration F1: 0,3821→0,5903 (+54,5%) — vượt trội so với tăng class weight đơn thuần (+24,8% và +40,6% cao hơn class weight ×10).

**Đóng góp 3 — Chẩn đoán định lượng covariate shift và xây dựng Testbed thực:**
Định lượng mức độ covariate shift: CIC→Testbed WSL2: Accuracy 99,55%→21,93%, MCC 0,9941→-0,015; Re-fit Scaler: 21,93%→6,87% (xấu hơn). Thiết kế và thu thập dataset V8.5 với 111.825 flows trong môi trường mạng LAN thực; xác định và giải quyết vấn đề PortScan không phân tách trong môi trường NAT bằng dữ liệu surrogate; đánh giá robustness với val set đa dạng miền (BruteForce: hydra + CIC Patator). Mô hình V8.5 đạt Macro F1 = 91,7%.

**Đóng góp 4 — Hệ thống Hybrid IDS End-to-End tích hợp Snort + FTT:**
Triển khai pipeline hoàn chỉnh Snort 3 + CICFlowMeter + FTT V8.5 chạy song song trên WSL2 Ubuntu 22.04 trong môi trường phần cứng phổ thông (Intel i7 Gen 11, 16GB RAM, không GPU). Thực nghiệm End-to-End trên 5 loại tấn công xác nhận tính bổ sung hai tầng: DoS slowhttptest chỉ được phát hiện bởi ML; XSS payload ngắn chỉ được phát hiện bởi Snort; không loại tấn công nào bị bỏ sót hoàn toàn bởi cả hai.

---

## 1.5 Bố cục đồ án

| Chương | Nội dung |
|---|---|
| **Chương 2** | Cơ sở lý thuyết: FT-Transformer, Focal Loss, Layer Freezing, Snort, kiến trúc Hybrid IDS |
| **Chương 3** | Phương pháp đề xuất: chi tiết ba giai đoạn, tất cả kiến trúc và thuật toán |
| **Chương 4** | Phân tích lý thuyết: giải thích tại sao từng quyết định thiết kế là phù hợp |
| **Chương 5** | Đánh giá thực nghiệm: kết quả định lượng và kiểm chứng |
| **Chương 6** | Kết luận và hướng phát triển |
| **Phụ lục A** | Cấu hình môi trường thực nghiệm chi tiết |
| **Phụ lục B** | Bảng siêu tham số đầy đủ của tất cả mô hình |

---

## Kết chương

Chương này phân tích ba thách thức cốt lõi của NIDS (mất cân bằng lớp, covariate shift, giới hạn một tầng), phân tích giới hạn các hướng tiếp cận hiện có, và đề xuất giải pháp lai ghép Snort + FT-Transformer thông qua ba giai đoạn nghiên cứu tuần tự. Bốn đóng góp chính được xác định với kết quả số liệu cụ thể. Chương 2 trình bày nền tảng lý thuyết cho tất cả kỹ thuật được sử dụng.
