# Báo Cáo Phân Tích Hệ Thống Phát Hiện Xâm Nhập (IDS Testbed)

Tài liệu này tổng hợp chi tiết về kiến trúc mô hình, thuật toán được sử dụng, tập dữ liệu thu thập từ Testbed thực tế, phương pháp tấn công và kết quả đánh giá hiệu năng của hệ thống phân loại đa nhãn (Cascade 9-class).

---

## 1. Kiến Trúc Mô Hình & Thuật Toán (Model Architecture)

Hệ thống IDS hiện tại được thiết kế theo cấu trúc **Cascade 2 Giai Đoạn (Two-Stage Cascade System)**, kết hợp giữa kỹ thuật Học Sâu (Deep Learning) và Học Máy truyền thống (Machine Learning) để tối ưu hóa khả năng phát hiện các luồng mạng bất thường.

### Stage 1: Nhận diện cơ bản (Domain Adaptation Stage 3C)
- **Thuật toán chính:** **FT-Transformer (Feature Tokenizer + Transformer)**. Đây là một biến thể của Transformer được tinh chỉnh đặc biệt cho dữ liệu dạng bảng (Tabular Data).
- **Cấu trúc:** 
  - `num_features`: 80 đặc trưng (bao gồm 77 đặc trưng CICFlowMeter chuẩn và các đặc trưng tùy chỉnh).
  - `d_model`: 128 (kích thước vector nhúng).
  - `num_layers`: 4 lớp Transformer Encoder.
  - `num_heads`: 8 cơ chế Multi-Head Attention.
- **Nhiệm vụ:** Phân loại nhanh các luồng mạng thành `Benign` (Bình thường), các dạng tấn công rõ ràng (như `DoS`), hoặc dán nhãn `Suspicious` (Đáng ngờ) đối với các luồng mạng có dấu hiệu bất thường nhưng chưa đủ thông tin để kết luận.

### Stage 2: Phân tích chuyên sâu (Ensemble Learning)
- **Cơ chế kích hoạt:** Chỉ những luồng bị Stage 1 đánh dấu là `Suspicious` với độ tin cậy cao (Threshold $\ge 0.85$) mới được đưa vào Stage 2 để giảm tải tính toán.
- **Thuật toán (Ensemble):** Sử dụng sự đồng thuận (Voting/Thresholding) giữa 3 mô hình độc lập:
  1. **FT-Transformer (Thu gọn):** `d_model` = 64, 3 layers, 4 heads.
  2. **Random Forest (RF):** Mô hình cây quyết định rừng ngẫu nhiên.
  3. **K-Nearest Neighbors (KNN):** Thuật toán láng giềng gần nhất.
- **Nhiệm vụ:** Phân rã nhãn `Suspicious` thành các loại tấn công tinh vi hơn (ví dụ: `Infiltration`, `Botnet`) bằng cách sử dụng bộ đặc trưng mở rộng (gồm các đặc trưng tĩnh + tỷ lệ gói tin như `Flow_Bytes_Ratio`, `Flow_Pkts_Ratio`).

---

## 2. Kết Quả Thực Nghiệm (Inference Results)

Dưới đây là kết quả đánh giá (Evaluation) của mô hình Cascade trên tập dữ liệu thực tế `run2` vừa thu thập được từ Testbed:

> [!TIP]
> **Tổng quan:** Tổng số mẫu được đánh giá là **49.969 flow**. Độ chính xác trung bình (Weighted F1-Score) đạt **91.48%**. Do không có mẫu nào đạt ngưỡng Suspicious cực cao, toàn bộ kết quả dưới đây là năng lực phản xạ trực tiếp của mạng Transformer Stage 1.

| Nhãn (Class) | Precision | Recall | F1-Score | Support (Số mẫu) |
| :--- | :--- | :--- | :--- | :--- |
| **DoS** | 97.54% | 90.55% | 93.91% | 46.921 |
| **Benign** | 47.04% | 65.08% | 54.61% | 3.018 |
| **Brute Force** | 0.45% | 33.33% | 0.88% | 30 |

**Phân tích ma trận nhầm lẫn (Confusion Matrix):**
- **DoS:** Mô hình phát hiện cực kỳ xuất sắc và chính xác 42.485 mẫu tấn công từ chối dịch vụ (chiếm tỷ lệ nhận diện đúng 90.5%).
- **Benign:** Nhận diện đúng 1.964 luồng bình thường. Tuy nhiên, có 1.054 luồng bình thường bị nhận diện nhầm thành DoS (False Positives). Nguyên nhân chủ yếu do traffic nền bị xen lẫn vào các khung thời gian (time window) khi tấn công Hulk DoS bắn phá mãnh liệt, gây nhiễu đặc trưng luồng.
- **PortScan / Web Attack:** Script tự động đánh nhãn `dataset_builder.py` đã ưu tiên dán nhãn luồng là `DoS` khi có sự chồng lấn thời gian xảy ra, do đó các mẫu `PortScan` tạm thời bị gộp chung vào lớp DoS trong tập đánh giá.

---

## 3. Nội Dung Tập Dữ Liệu Được Sử Dụng (Dataset)

Tập dữ liệu kiểm thử (Custom IDS Testbed) được xây dựng trực tiếp tại môi trường mạng nội bộ (LAN) với cấu trúc như sau:

- **Nguồn dữ liệu:**
  1. **CICFlowMeter (`attack_run2.pcap_Flow.csv`):** Chứa hơn 61.500 luồng mạng (flows) thô được trích xuất từ file định dạng PCAP.
  2. **Snort IDS (`alert_run2`):** Ghi nhận ~34.000 cảnh báo an ninh nội bộ, đóng vai trò làm Ground Truth (Nhãn chuẩn).

- **Tiền xử lý (Data Engineering):**
  - **Trích xuất đặc trưng mới:** Sinh thêm các đặc trưng Custom (như `Custom_Fwd_Pkt_Rate`, tỷ lệ byte, thống kê Port...).
  - **Gán nhãn bằng Time-Window:** Áp dụng thuật toán **Binary Search** so khớp thời gian (Time ± 120s) giữa Flow mạng và Cảnh báo Snort để dán nhãn tự động.
  - **Làm sạch & Chuẩn hóa:** Loại bỏ các giá trị nhiễu (`Infinity`, `NaN`), xóa bỏ các cột định danh mạng (`IP`, `Port`) để chống Overfitting, và chuẩn hóa giá trị về thang đo 0-1 bằng `MinMaxScaler`.

---

## 4. Cách Tập Tấn Công Được Thực Hiện (Attack Methodology)

Việc thu thập dữ liệu diễn ra theo mô hình **Attacker (Máy 1) $\rightarrow$ Victim (Máy 2)**. Kịch bản được thực thi hoàn toàn tự động hóa thông qua mã nguồn `auto_attack.py` với 7 kỹ thuật chính:

> [!IMPORTANT]
> **Công cụ & Payload Tấn Công:**
> 1. **PortScan:** Sử dụng `nmap -sT -T4 -p 1-1000` để quét qua hàng ngàn cổng TCP, sinh ra lượng lớn gói tin cờ SYN/ACK.
> 2. **SSH Brute Force:** Dùng công cụ `hydra` kết hợp từ điển `rockyou.txt` dội bom liên tục thông tin đăng nhập vào cổng 22.
> 3. **FTP Brute Force:** Tương tự SSH, `hydra` tấn công dò mật khẩu vào cổng 21 (FTP).
> 4. **Web Brute Force:** `hydra` gửi hàng loạt request `HTTP GET` trực tiếp vào trang `login.php` của máy chủ DVWA (Damn Vulnerable Web App).
> 5. **SQL Injection:** Khai thác lỗ hổng cơ sở dữ liệu tự động hóa qua `sqlmap` bằng cách chèn Payload SQL vào thanh URL hoặc Header.
> 6. **DoS Slowloris:** Duy trì hàng ngàn kết nối rác HTTP chậm rãi (`slowloris -p 80 -s 200`) để rút cạn tài nguyên Server (Connection Exhaustion).
> 7. **DoS Hulk:** Kích hoạt script Python `hulk.py` thực hiện HTTP Flood, tạo ra hàng ngàn truy vấn Web với tham số ngẫu nhiên ngụy tạo khiến máy chủ sập nguồn.
