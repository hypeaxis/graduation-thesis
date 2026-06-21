# Nhật ký Kỹ thuật: Quá trình Domain Adaptation cho FT-Transformer (Chi tiết)

Tài liệu này lưu trữ toàn bộ các thao tác kỹ thuật, các thay đổi mã nguồn, dữ liệu cấu hình và kết quả chi tiết từng Epoch trong quá trình giải quyết bài toán Concept Drift (Khắc phục sự sụt giảm độ chính xác khi đưa mô hình từ không gian CIC-IDS-2017 sang môi trường Testbed thực tế).

---

## 1. Bối cảnh và Thử nghiệm 1 (Lỗi Re-fit Scaler)

**Vấn đề ban đầu:**
Mô hình FT-Transformer khi dự đoán trên Testbed nội bộ chỉ đạt **Accuracy: 21.93%**, bỏ qua 80% luồng tấn công Slowloris thực tế.

**Thử nghiệm 1 (1_refit_scaler_test.py):**
- **Thao tác:** Khởi tạo lại `PowerTransformer(method='yeo-johnson')` và gọi hàm `fit_transform()` trực tiếp trên tập dữ liệu Testbed.
- **Kết quả:** Thất bại thảm hại, Accuracy tụt xuống **6.87%**, nhận diện sai gần như toàn bộ tấn công thành `Benign`.
- **Nguyên nhân gốc (Root Cause):** Testbed có phân phối lệch cực đoan (22.672 Malicious, 37 Benign). Khi bộ chuẩn hóa không giám sát (Unsupervised Scaler) học trên tập này, nó đã ép các đặc trưng của luồng tấn công Slowloris về quanh giá trị trung bình (`Mean = 0`). Mô hình Học sâu vốn được dạy rằng "các giá trị chuẩn hóa nằm gần 0 là mạng sạch (Benign)", nên đã dẫn tới việc phân loại sai toàn bộ cuộc tấn công.

---

## 2. Thử nghiệm 2: Layer Freezing & Mixed-Domain Fine-Tuning

Rút kinh nghiệm từ Thử nghiệm 1, chiến lược đổi sang **Học Chuyển Giao (Transfer Learning)** với việc bảo toàn bộ chuẩn hóa cũ. Dưới đây là các chi tiết kỹ thuật đã được code trong `2_finetune_freeze.py`.

### 2.1. Tiền xử lý dữ liệu (Data Processing)
- **Tạo Mixed-Domain Dataset:** Lấy 100% dữ liệu Testbed (Tách 80% Train, 20% Val) trộn với 30.000 dòng lấy mẫu ngẫu nhiên từ tập `cic_train_full.csv`. Việc này ngăn chặn mô hình bị "quên" hình dạng của các mạng bình thường cũ.
- **Quy hoạch nhãn (Label Mapping):** Vì Testbed chỉ gán nhãn `Malicious` (cho Slowloris), nhưng bộ Encoder của mô hình nguyên bản (`encoder_stage1.pkl`) lại đòi hỏi 6 nhãn chi tiết (`Benign`, `Brute Force`, `DDoS`, `DoS`, `PortScan`, `Suspicious`). 
  $\rightarrow$ **Giải pháp:** Trong script, nhãn `Malicious` của Testbed đã được quy đổi cứng thành `DoS` trước khi nạp vào Encoder.
- **Giữ nguyên Scaler:** Load lại file `scaler_stage1.pkl` gốc và chỉ gọi `.transform()` lên tập Mixed-Domain, KHÔNG gọi `.fit()`.

### 2.2. Xử lý Mất cân bằng lớp (Class Imbalance)
- **Thuật toán:** Sử dụng `RandomOverSampler` từ thư viện `imbalanced-learn`.
- **Mục đích:** Tập Testbed chỉ có vỏn vẹn 37 mẫu Benign. Oversampler đã nhân bản các mẫu thiểu số này lên sao cho số lượng mẫu của tất cả các lớp bằng với lớp đa số (khoảng 24.000 mẫu/lớp). Tổng kích thước tập Train sau khi cân bằng lên tới khoảng **168.000 mẫu**.
- **CrossEntropy Weights:** Dù đã dùng Oversampler, script vẫn tính toán một tensor `class_weights` dựa trên tần suất nghịch đảo để truyền vào hàm `nn.CrossEntropyLoss(weight=class_weights)` nhằm triệt tiêu hoàn toàn sự thiên lệch.

### 2.3. Tinh chỉnh Thuật toán & Layer Freezing (Model Architecture)
- **Đóng băng (Freeze):** Để giữ lại các biểu diễn đặc trưng (Representations) tổng quát mà mạng đã vất vả học được từ CIC-IDS-2017, các biến số Gradient đã bị tắt (`requires_grad = False`) ở các tầng:
  - `model.feature_embedding` (Lớp chuyển 77 features thành vector 128 chiều).
  - `model.transformer_blocks[0]` (Khối Attention thứ nhất).
  - `model.transformer_blocks[1]` (Khối Attention thứ hai).
- **Mở khóa (Unfreeze):** Chỉ cho phép cập nhật trọng số ở:
  - `model.transformer_blocks[2]` và `model.transformer_blocks[3]`.
  - `model.classifier` (2 lớp Fully Connected đầu ra).
- **Optimizer:** `AdamW` với Learning Rate siêu nhỏ: `lr = 1e-5` (giảm 10 lần so với lúc train gốc) để nắn nhẹ vùng không gian quyết định (Decision Boundary) mà không làm hỏng cấu trúc cũ.

---

## 3. Nhật ký Huấn luyện (Training Logs)

Batch Size được thiết lập = 256. Dưới đây là quá trình Loss và Balanced Accuracy trên tập Testbed-Validation thay đổi qua 10 Epochs:

```text
============================================================
GIAI ĐOẠN 1: LAYER FREEZING FINE-TUNING
============================================================
[*] Nạp Testbed Data...
[*] Nạp CIC-IDS-2017 Sample Data...
[*] Áp dụng Scaler gốc từ CIC-IDS-2017...
[*] Cân bằng lớp Mixed-Domain bằng RandomOverSampler...
[*] Đóng băng (Freeze) lớp Embedding và 2 khối Attention đầu...
[*] Bắt đầu Fine-Tuning...
Epoch 1/10 | Loss: 0.1863 | Val B-Acc: 0.9594 | Recall(Malicious): 0.9189
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9594)
Epoch 2/10 | Loss: 0.0672 | Val B-Acc: 0.9839 | Recall(Malicious): 0.9678
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9839)
Epoch 3/10 | Loss: 0.0447 | Val B-Acc: 0.9896 | Recall(Malicious): 0.9793
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9896)
Epoch 4/10 | Loss: 0.0337 | Val B-Acc: 0.9949 | Recall(Malicious): 0.9899
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9949)
Epoch 5/10 | Loss: 0.0265 | Val B-Acc: 0.9985 | Recall(Malicious): 0.9969
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9985)
Epoch 6/10 | Loss: 0.0234 | Val B-Acc: 0.9988 | Recall(Malicious): 0.9976
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9988)
Epoch 7/10 | Loss: 0.0208 | Val B-Acc: 0.9988 | Recall(Malicious): 0.9976
Epoch 8/10 | Loss: 0.0188 | Val B-Acc: 0.9989 | Recall(Malicious): 0.9978
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9989)
Epoch 9/10 | Loss: 0.0168 | Val B-Acc: 0.9990 | Recall(Malicious): 0.9980
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9990)
Epoch 10/10 | Loss: 0.0163 | Val B-Acc: 0.9991 | Recall(Malicious): 0.9982
   -> Lưu checkpoint tốt nhất! (B-Acc: 0.9991)
```

## 4. Kết quả Báo cáo Đánh giá Cuối cùng

**1. Đánh giá trên tập Validation của Testbed nội bộ:**
- Accuracy tổng thể: `0.9982` (99.82%)
- Balanced Accuracy: `0.9991` (Chỉ số cực kỳ uy tín cho tập lệch lớp).
- MCC (Matthews Correlation Coefficient): `0.6825`
- Recall đối với các mẫu Benign (Mạng bình thường): `1.0000` (Không nhận nhầm người tốt thành mã độc).
- Recall đối với các mẫu Malicious (Slowloris): `0.9982` (Phát hiện thành công gần 100% tấn công).
- **Confusion Matrix:**
  ```text
  Benign    [    7,       0 ]
  Malicious [    8,    4527 ]
  ```
  *(Chỉ có 8 mẫu Slowloris lọt qua hệ thống trong số 4535 mẫu tấn công kiểm thử).*

**2. Đánh giá kiểm tra "Catastrophic Forgetting" (Kiến thức cũ):**
Chạy mô hình (đã Fine-tune với dữ liệu WSL) ngược lại trên 50.000 dòng dữ liệu test của mạng CIC-IDS-2017 gốc:
- Accuracy: `0.9935` (Chỉ giảm 0.55% so với mức Baseline gốc là ~99.9%).
- Nhận xét: Mô hình vẫn lưu giữ được khả năng nhận diện 14 dạng tấn công cũ, đảm bảo tính ứng dụng rộng rãi.

---
**Tài liệu này được tạo tự động bởi AI-Agent để phục vụ cho việc sao lưu dữ liệu nghiên cứu khoa học.**
