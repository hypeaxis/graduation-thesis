# Log Session: Giai đoạn 3, 4, và 5 (Tái thiết Pipeline, Retrain và Đánh giá chuẩn)
**Thời gian thực hiện:** Ngày 21-22 tháng 06 năm 2026

## 1. Tóm tắt Mục Tiêu
Theo Roadmap, Session này tập trung giải quyết triệt để vấn đề rò rỉ dữ liệu (Data Leakage) và độ tin cậy của mô hình bằng cách:
1. Chuẩn hóa quy trình tiền xử lý bằng việc đóng gói Scaler (Giai đoạn 3).
2. Huấn luyện lại mô hình (Retrain) thông qua Model Surgery trên tập `run5` (Giai đoạn 4).
3. Đánh giá minh bạch mô hình bằng bộ dữ liệu thực chiến `run6` (Giai đoạn 5).

## 2. Chi Tiết Thực Hiện

### Giai đoạn 3: Chuẩn hóa & Đóng gói Preprocessing Pipeline
- **Cấu trúc thư mục mới:** Khởi tạo thư mục `Phase3_4_Retrain/` để cô lập mã nguồn và dữ liệu. Di chuyển `Cleaned_Labeled_Dataset_run5.csv` (Train Set) và `Cleaned_Labeled_Dataset_run6.csv` (Test Set) vào `Phase3_4_Retrain/data/`.
- **`hybrid_feature_scaler.py`:** Tạo Class `HybridFeatureScaler` duy nhất quản lý 2 luồng chuẩn hóa.
  - Cố định (Freeze) `scaler_77_original` từ CIC-IDS-2017 (không fit lại).
  - Khởi tạo và chỉ fit `scaler_3_new` (PowerTransformer) cho 3 feature tùy chỉnh.
  - Cả 2 scaler được đóng gói vào chung một file `v4_hybrid_pipeline.pkl`.
- **`check_distribution_drift.py`:** Cài đặt hàm cảnh báo Data Drift tự động. Đo lường phân phối (Mean, Std) của 3 custom features lúc fit và cảnh báo nếu Z-Score của batch test lệch ngưỡng `3.0`.

### Giai đoạn 4: Re-fit & Re-train trên dữ liệu đã làm sạch
- **Kịch bản:** Sử dụng tập `Cleaned_Labeled_Dataset_run5.csv` kết hợp với tập con CIC-IDS-2017 (tổng 119k mẫu Mix Train Data).
- **Thực thi `4_refit_retrain_v2.py`:**
  - Áp dụng `HybridFeatureScaler` lên Mixed Data, fit scaler 3 custom feature.
  - Tải Base Model (`finetuned_stage3c_hybrid.pt`).
  - **Model Surgery:** Freeze Embedding của 77 feature cũ và 2 layer đầu tiên của Transformer block. Unfreeze layer Classifier và Embedding của 3 feature mới.
  - **Class Weighting:** Gán trọng số nghịch đảo với tần suất xuất hiện của các nhãn để bù đắp lớp thiểu số (Brute Force có rất ít mẫu).
  - Train trong 15 Epochs. Loss giảm đều từ `0.4661` xuống `0.1335`.
  - Kết quả xuất ra Model mới: `v4_hybrid_model.pt`.

### Giai đoạn 5: Đánh giá Chuẩn trên Test Set (run 6)
- Tập `run6` có độ khó cực cao vì tỷ lệ **Benign chiếm tới 63%** (58.868 mẫu) và hoàn toàn tách biệt so với `run5`.
- **Thực thi `5_standard_evaluation.py`**:
  - Load Test Set `run6`, đưa qua `check_distribution_drift.py` -> Kết quả: **Không có Data Drift**.
  - Đưa qua `v4_hybrid_pipeline.pkl` và `v4_hybrid_model.pt`.

## 3. Phân tích Kết quả Cuối cùng
Kết quả xuất ra tại log của script `5_standard_evaluation.py`:
- **Accuracy:** 0.4387
- **Balanced Accuracy:** 0.6156
- **MCC:** 0.4158

**Confusion Matrix (Tuyệt đối):**
```
                  Pred_Benign  Pred_Brute Force  Pred_DoS  Pred_PortScan
True_Benign             10162             28947      4884          14875
True_Brute Force            2              1447         0              0
True_DoS                  100                 0     27762            881
True_PortScan              10              1622       144            857
```

**Đánh giá Insight:**
1. **Model Surgery thành công ở phương diện thiểu số:** Recall của Brute Force đạt mức **99.86%** (1447/1449) và DoS đạt **96.59%**. Hệ thống đã thoát khỏi cảnh bị mù màu với các lớp thiểu số như ở các session đầu.
2. **Hậu quả của Class Weighting và Single Model:** Tuy bắt được gần 100% tấn công thiểu số, Model Multi-class đã đánh đổi hoàn toàn nhóm Traffic Bình thường (Benign) để có được Recall cao đó. Cụ thể, hơn **43.000 mẫu Benign** đã bị Model nhìn nhầm thành Brute Force (28.947) và PortScan (14.875).
3. **Mở đường cho Cascade Architecture:** Lượng False Positives khổng lồ này khẳng định luận điểm chủ chốt của đồ án: Một mạng Multi-class đơn lẻ, học dựa trên Flow-Statistics tĩnh, là không đủ khả năng để vừa giữ False Positives thấp, vừa không bỏ sót lớp thiểu số. Chúng ta **bắt buộc phải sử dụng** mô hình Cascade (2 Stage: Stage 1 làm nhiệm vụ hớt bọt/Anomaly Detection để ngăn chặn False Positive cho Benign, sau đó mới đưa lớp Malicious cho Stage 2 phân loại chi tiết).
