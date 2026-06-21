# Tổng hợp Kết quả Thực thi Lộ trình (Roadmap) Khắc phục Concept Drift cho FT-Transformer

Tài liệu này tổng hợp lại toàn bộ quá trình, phương pháp và kết quả thực nghiệm theo Lộ trình (Roadmap) nhằm khắc phục hiện tượng Concept Drift khi đem mô hình FT-Transformer (đã huấn luyện trên tập CIC-IDS-2017) sang chạy thực tế trên môi trường Testbed (Slowloris WSL).

---

## Bối cảnh ban đầu (Baseline)
- **Mô hình gốc:** FT-Transformer (4 layers, 8 heads, 128 d_model), độ chính xác trên tập CIC-IDS-2017 đạt `>99%`.
- **Vấn đề:** Khi mang sang Testbed nội bộ (chỉ gồm 37 mẫu Benign và 22,672 mẫu Malicious), mô hình gần như bị "mù".
  - Accuracy: `21.93%`
  - Recall (Malicious): `0.218`
  - MCC: `-0.015`
- **Chẩn đoán:** Bị "Covariate Shift" cực nặng do khác biệt về hạ tầng mạng (WSL/NAT) so với mạng vật lý thực (CIC-2017), khiến không gian đặc trưng của gói tin bị dịch chuyển.

---

## Thử nghiệm 1: Khởi tạo lại bộ chuẩn hóa (Re-fit Scaler)
- **Phương pháp:** Thử dùng lại thuật toán `PowerTransformer` nhưng Fit trực tiếp trên dữ liệu Testbed thay vì dùng tham số cũ của CIC-IDS-2017.
- **Kết quả:** Thất bại thảm hại.
  - Accuracy: Tụt xuống `6.87%`.
  - Recall (Malicious): Tụt xuống `0.0673`.
- **Nguyên nhân:** Dữ liệu Testbed mất cân bằng cực đoan (Benign quá ít). Việc Re-fit Scaler đã làm tâm phân phối (mean=0) bị kéo lệch hẳn về phía lớp Malicious. Vô tình, vùng không gian này lại trùng với vùng mà mô hình gốc học là "Benign".
- **Kết luận:** BẮT BUỘC phải giữ nguyên Scaler gốc (fit trên CIC-IDS-2017) cho toàn bộ các đặc trưng cũ.

---

## Giai đoạn 1: Fine-tuning với Layer Freezing (Đóng băng lớp)
- **Phương pháp:**
  - Trộn dữ liệu Testbed với một tập mẫu nhỏ (~30,000 dòng) từ CIC-IDS-2017 để tạo tập **Mixed-Domain**.
  - Dùng thuật toán `RandomOverSampler` kết hợp Class Weights để xử lý mất cân bằng lớp cực đoan trên Testbed.
  - Đóng băng (Freeze) toàn bộ Layer Đầu vào (Feature Embeddings) và 2 khối Attention Block đầu tiên để bảo vệ kiến thức gốc.
  - Chỉ cho phép mô hình học (Unfreeze) ở 2 khối Attention cuối và Classification Head.
- **Kết quả:** Thành công vang dội.
  - Accuracy: `99.82%`
  - Recall (Malicious): `0.9982`
  - MCC: `0.6825`
  - Catastrophic Forgetting (Độ sụt giảm trên tập CIC-2017 gốc): Cực nhỏ, chỉ giảm `-0.55%`.

---

## Giai đoạn 2: Domain Alignment (CORAL/DANN)
- **Tình trạng:** **ĐÃ BỎ QUA**.
- **Lý do:** Giai đoạn 1 đã vượt xa mọi Tiêu chí Hoàn thành (DoD) đề ra trong Roadmap (Recall Malicious yêu cầu > 0.218, thực tế đạt 0.9982). Không cần thiết phải làm phức tạp thêm bằng thuật toán căn chỉnh Domain cấp độ Embedding.

---

## Giai đoạn 3: Feature Engineering v2 & Phẫu thuật Mô hình (Model Surgery)
- **Phương pháp:**
  - Nhận thấy mô hình có thể vẫn phụ thuộc vào giá trị thời gian tuyệt đối của máy ảo, tiến hành bổ sung 3 đặc trưng mang tính "tỷ lệ/nội tại" để chống nhiễu:
    1. `Custom_IAT_CV` (Hệ số biến thiên của IAT = Std / Mean).
    2. `Custom_Bwd_Pkt_Ratio` (Tỷ lệ gói tin phản hồi).
    3. `Custom_Pkt_Size_Ratio` (Tỷ lệ kích thước Min/Max).
  - Tận dụng kiến trúc Token của FT-Transformer, thực hiện **Model Surgery (Cấy ghép mô hình)**: Nới rộng đầu vào từ 77 lên 80 Features. Chép đè (Load State Dict) trọng số của 77 mạng Linear Embedding cũ, và chỉ khởi tạo ngẫu nhiên để học 3 Embedding mới.
  - Bộ Scaler dùng cơ chế Hybrid: 77 Đặc trưng cũ dùng Scaler cũ, 3 Đặc trưng mới dùng Scaler mới.
- **Kết quả:** Vượt lên một tầm cao mới (Ablation Study thành công).
  - Accuracy: Tăng lên `99.87%`.
  - Recall (Malicious): Đạt `0.9987`.
  - **MCC (Chỉ số quan trọng nhất cho dữ liệu lệch):** Tăng vọt từ `0.6825` lên **`0.7333`**.
  - Catastrophic Forgetting: Vẫn an toàn ở mức `-0.61%`.
- **Kết luận:** Bộ đặc trưng mới kết hợp Model Surgery đã giúp không gian phân loại rành mạch hơn rất nhiều.

---

## Giai đoạn 4: Mở rộng dữ liệu Testbed
- **Tình trạng:** **ĐANG CHỜ XỬ LÝ (PENDING)**.
- **Lý do:** Bộ dữ liệu Testbed hiện tại chỉ có đúng 37 mẫu Benign, khiến chỉ số Precision và Recall (Benign) có độ tin cậy thấp (Confidence Interval lớn). Cần người dùng tự bật Tool chặn/thu thập thêm hàng trăm mẫu Traffic sạch trên máy ảo WSL trước khi chốt hạ con số vào quyển Đồ án cuối.

---

## 5. Bảng Tổng hợp Kết quả Cuối cùng

Đây là bảng tóm tắt mọi thông số qua các thử nghiệm (Có thể dùng trực tiếp để đưa vào báo cáo LaTeX).

| Thử nghiệm | Phương pháp Scaler | Chiến lược Fine-Tuning | Độ chính xác (Acc) | Balanced Acc | MCC | Recall (Benign) | Recall (Malicious) | Quên kiến thức cũ (Δ Acc) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Baseline (Gốc)** | Dùng nguyên Scaler CIC-2017 | Không Fine-tune | 21.93% | 60.90% | -0.0150 | 100.00% | 21.80% | -0.00% |
| **Exp1** | Re-fit Scaler hoàn toàn mới | Chỉ đổi Scaler, không train | 6.87% | 52.01% | 0.0065 | 97.30% | 6.73% | Không xét |
| **Exp2 (Giai đoạn 1)**| Dùng nguyên Scaler CIC-2017 | Layer Freezing (Chỉ train lớp cuối) | 99.82% | 99.91% | 0.6825 | 100.00% | 99.82% | -0.55% |
| **Exp3 (Giai đoạn 3)**| Lai ghép (Cũ + Mới) | Cấy ghép mô hình (+3 Features) | **99.87%** | **99.93%** | **0.7333** | **100.00%** | **99.87%** | -0.61% |
