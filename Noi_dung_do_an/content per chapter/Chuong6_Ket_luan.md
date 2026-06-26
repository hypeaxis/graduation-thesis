# Chương 6. Kết luận

Chương 5 trình bày kết quả thực nghiệm qua ba giai đoạn và kiểm chứng các phân tích lý thuyết. Chương này tổng kết những gì đồ án đã đạt được, chỉ ra các hạn chế còn tồn tại, và đề xuất hướng phát triển có căn cứ trong các hạn chế đó. Phần 6.1 đối chiếu kết quả với mục tiêu ban đầu và tóm tắt bốn đóng góp. Phần 6.2 liệt kê các hạn chế cụ thể với phân tích nguyên nhân. Phần 6.3 đề xuất bốn hướng phát triển tiếp theo.

---

## 6.1 Kết quả đạt được

### 6.1.1 Đối chiếu với mục tiêu

| Mục tiêu ban đầu | Kết quả đạt được |
|---|---|
| Macro F1 > 0,9 trên CIC-IDS-2017 | **0,9294** — đạt |
| Macro F1 > 0,9 trên Testbed thực | **0,917** — đạt |
| Tích hợp Snort + ML trong End-to-End | Đạt — pipeline chạy song song WSL2 |
| Phát hiện bổ sung giữa hai tầng | Đạt — DoS/XSS xác nhận bổ sung |

### 6.1.2 Tóm tắt kết quả định lượng

**Giai đoạn 1 — NSL-KDD:** Stacking Ensemble (FTT + LightGBM → Meta-LR) đạt Macro F1 = 0,6809, cải thiện 4,3% so với FTT baseline. U2R F1 = 0,5120 (tăng từ 0,15 baseline). R2L Recall = 0,2523 — giới hạn cứng do protocol shift pop3/telnet không thể vượt qua bằng thuật toán.

**Giai đoạn 2 — CIC-IDS-2017:** Two-Stage Cascade với Asymmetric Ensemble Voting đạt Macro F1 = 0,9294 và Accuracy = 99,55%. Infiltration F1 = 0,7407 và Botnet F1 = 0,7344. Từng cải tiến có đóng góp định lượng: Two-Stage (+0,099), HNM 2 vòng (+0,036), Asymmetric Voting (+0,011 so với Majority Vote).

**Giai đoạn 3 — Testbed V8.5:** Macro F1 = 91,7%, Balanced Accuracy = 91,1%, MCC = 0,891 trên val set đa dạng miền. PortScan F1 = 100% với dữ liệu surrogate. BruteForce F1 = 86% (Recall = 80%) trên mixed hydra + CIC Patator.

### 6.1.3 Bốn đóng góp

1. **Kiến trúc Two-Stage Cascade với Asymmetric Ensemble Voting:** phân tầng phát hiện (binary gate + expert classifier) kết hợp với voting bất đối xứng theo chi phí FP/FN khác nhau của từng lớp. Macro F1 = 0,9294 trên 9 lớp CIC-IDS-2017.

2. **Hard Negative Mining 2 vòng cho lớp tấn công hiếm:** tăng tập trung gradient vào biên quyết định thay vì tăng class weight đồng đều. Botnet F1 +36%, Infiltration F1 +54,5% — vượt trội class weight ×10 với +24,8% và +40,6%.

3. **Chẩn đoán covariate shift định lượng và xây dựng Testbed thực:** xác định Re-fit Scaler làm tình hình xấu hơn (21,93%→6,87%); xác định PortScan không phân tách trong NAT; thiết kế val set đa dạng miền; đạt Macro F1 = 91,7%.

4. **Hệ thống Hybrid IDS End-to-End trên phần cứng phổ thông:** pipeline Snort + CICFlowMeter + FTT V8.5 chạy hoàn chỉnh trên Intel i7 + 16GB RAM, không GPU; xác nhận tính bổ sung hai tầng phát hiện trong thử nghiệm thực.

---

## 6.2 Hạn chế

### 6.2.1 Hạn chế về phạm vi tấn công

**Thiếu 4 lớp trong Testbed:** DDoS (cần nhiều máy phối hợp), Botnet C2 (cần hạ tầng malware), Infiltration (cần kịch bản đa bước), Heartbleed (cần OpenSSL cụ thể và chỉ 10 mẫu trong CIC). Mô hình V8.5 chỉ đạt được trên 5 lớp, không phải 9 lớp như mô hình CIC.

**Ảnh hưởng:** hệ thống không phát hiện được DDoS, Botnet, Infiltration bằng tầng ML trong môi trường Testbed. Tầng Snort có thể bổ sung một phần nhưng không đầy đủ.

### 6.2.2 Hạn chế của phương pháp flow-based

**Infiltration và Botnet:** như phân tích tại Mục 4.6, flow đơn lẻ không mang đủ thông tin để phân biệt. Infiltration F1 = 0,7407 là kết quả tốt nhất có thể đạt được với phân tích flow-based trên CIC — không phải vì kiến trúc kém mà vì giới hạn căn bản của phương pháp.

**Web Attack (F1=0,8767 CIC, 0,88 Testbed):** XSS và SQLi payload ngắn tạo flow statistics giống Benign HTTP POST. Tầng Snort bù đắp phần này.

**Độ trễ phát hiện ML:** DoS slowhttptest cần đợi 30 giây (CICFlowMeter timeout) trước khi phát hiện được. Tấn công đã gây hậu quả trong 30 giây đó.

### 6.2.3 Hạn chế về quy mô thực nghiệm

**Môi trường đơn:** thực nghiệm Testbed thực hiện trên một cặp máy trong mạng LAN gia đình. Kết quả có thể khác trong môi trường doanh nghiệp với nhiều người dùng, nhiều dịch vụ, tải cao hơn.

**PortScan surrogate:** PortScan F1 = 100% đạt được nhờ dữ liệu surrogate CIC Friday (phần cứng vật lý thực), không phải dữ liệu thu thập trong chính môi trường WSL2. Kết quả này không thể tổng quát hóa sang WSL2 thực tế với nmap thông thường.

### 6.2.4 Hạn chế về giải thích mô hình

FT-Transformer là mô hình hộp đen — không giải thích được tại sao một flow cụ thể bị phân loại là Botnet. Trong môi trường SOC thực tế, analyst cần biết lý do cảnh báo để quyết định response. Thiếu khả năng explainability là trở ngại cho triển khai thực tiễn.

---

## 6.3 Hướng phát triển

### 6.3.1 Temporal Analysis cho Botnet và Infiltration

Thay vì phân loại flow đơn lẻ, xây dựng session-level feature: gộp nhiều flow liên tiếp từ cùng 5-tuple thành vector dài, học pattern temporal bằng LSTM hoặc Temporal Transformer. Lý thuyết: pattern Botnet C2 periodic heartbeat và Infiltration multi-step chỉ lộ ra khi quan sát nhiều flow liên tiếp — temporal model có khả năng nắm bắt đặc điểm này.

Thách thức: xác định ranh giới session, xử lý session dài hàng giờ trong thời gian thực, lưu trữ state giữa các packet captures.

### 6.3.2 Web Attack Temporal Analysis

Web Attack XSS/SQLi thất bại trông giống Benign HTTP POST. Nhưng trong một cuộc tấn công thực, kẻ tấn công thực hiện nhiều lần thử với payload khác nhau trước khi thành công — pattern "nhiều HTTP POST bất thường liên tiếp đến cùng endpoint" phân biệt được với Benign browsing. Temporal analysis trên chuỗi HTTP flow có thể cải thiện Web Attack Recall đáng kể.

### 6.3.3 Automated Feature Engineering cho Testbed đa dạng

V8.5 bổ sung 3 đặc trưng thủ công (IAT\_CV, Bwd\_Pkt\_Ratio, Pkt\_Size\_Ratio) dựa trên hiểu biết về môi trường NAT. Hướng tiếp cận tự động hơn: sử dụng gradient-based feature importance của FTT để tự động phát hiện đặc trưng nào quan trọng cho môi trường Testbed nhưng không có trong 77 đặc trưng CICFlowMeter gốc.

### 6.3.4 Federated Learning cho Multi-site Privacy-Preserving NIDS

Môi trường doanh nghiệp thực tế bao gồm nhiều site (trụ sở, chi nhánh, cloud) với chính sách không chia sẻ traffic giữa site. Federated Learning cho phép nhiều site cùng cải thiện mô hình chung mà không chia sẻ dữ liệu: mỗi site huấn luyện local, chỉ chia sẻ gradient cập nhật, server tổng hợp thành mô hình global. Kết hợp với phương pháp xử lý covariate shift trong đề tài (Layer Freezing + Model Surgery), có thể xây dựng NIDS thích nghi với mỗi môi trường mạng trong khi vẫn học từ dữ liệu toàn cầu.

---

## Kết chương

Đồ án đạt cả ba mục tiêu đặt ra: Macro F1 = 0,9294 trên CIC-IDS-2017, Macro F1 = 91,7% trên Testbed thực, và hệ thống Hybrid IDS End-to-End hoạt động được trên phần cứng phổ thông. Bốn đóng góp chính có tính năng động định lượng rõ ràng và kiểm chứng thực nghiệm. Các hạn chế được xác định cụ thể: phạm vi tấn công Testbed bị giới hạn bởi điều kiện thực nghiệm, giới hạn căn bản của flow-based analysis với Infiltration/Botnet, và thiếu explainability. Bốn hướng phát triển được đề xuất xuất phát trực tiếp từ các hạn chế này và có căn cứ kỹ thuật rõ ràng.
