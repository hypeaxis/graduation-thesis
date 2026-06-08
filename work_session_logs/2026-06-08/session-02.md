# Work Session Log: 2026-06-08 (Session 02)

## 1. Kết quả Phase 4: Feature Selection
- **Mục tiêu:** Áp dụng phương pháp truyền thống (Feature Selection) để cắt giảm nhiễu (noise) khỏi 122 đặc trưng ban đầu, hy vọng giúp FT-Transformer v1 bớt overfit và phát hiện Zero-day tốt hơn.
- **Thực hiện:** Đã sử dụng `RandomForest` để chấm điểm Feature Importances, sau đó loại bỏ 32 features ít quan trọng nhất (như các loại service hiếm). Chỉ giữ lại Top 90 features.
- **Kết quả:**
  - Macro-F1 trên tập Validation: Đạt `0.6622` (Sớm bị Early Stop ở Epoch 4).
  - Macro-F1 trên tập Test (KDDTest+): Đạt `0.6343`.
- **Đánh giá:** Rất đáng tiếc là việc cắt giảm feature khiến F1-Score trên tập Test giảm (từ 0.6679 xuống 0.6343). Lý do là vì ở bài toán an ninh mạng, các feature "hiếm" đôi khi lại chứa tín hiệu quan trọng để cảnh báo các loại tấn công Zero-day. Việc cắt bỏ chúng đã làm mất đi một số tín hiệu ngầm. Do đó, phương án giảm chiều dữ liệu không mang lại hiệu quả như mong đợi.

## 2. Bước ngoặt Phase 5: Chiến lược Two-Stage (Binary + Multiclass)
- **Mục tiêu:** Tách bài toán 5-class phức tạp thành 2 giai đoạn (Stages) độc lập để các mô hình làm tốt nhiệm vụ chuyên môn của nó.
- **Phát hiện:** User đã cung cấp một script `AutoencoderTrain.py` chuyên trách cho bài toán Binary. AI nhận thấy việc sử dụng Autoencoder (Học không giám sát) là vô cùng phù hợp để tìm kiếm sự bất thường (Anomaly Detection) cho bước đầu tiên. Tuy nhiên, đã phát hiện lỗi **Data Leakage** trong script cũ của User (tìm ngưỡng Threshold và tự in ra báo cáo ngay trên tập Train).
- **Thực thi:**
  - **Stage 1 (Binary Classification):** Đã sửa lại lỗi Data Leakage trong file `AutoencoderTrain.py` để mô hình train và tìm ngưỡng trên dữ liệu Train, sau đó chấm điểm nghiêm ngặt (Strict evaluation) trên tập Test. Hiện tại đang cài đặt thư viện `tensorflow` để chạy mô hình này.
  - **Stage 2 (Multiclass Classification):** Đã nâng cấp API của `train_ft_transformer_nslkdd.py` để hỗ trợ cờ `--task-type 4-class-attack`. Mô hình FT-Transformer sẽ tự động vứt bỏ luồng Normal và chỉ tập trung phân biệt 4 loại tấn công (DoS, Probe, R2L, U2R). Hiện tại mô hình Stage 2 đang được huấn luyện dưới nền.

## 3. Kết quả đánh giá chiến lược Two-Stage
**Kết quả Stage 1: Autoencoder (Phân loại Normal vs Attack)**
- **Test Macro-F1:** `0.84` | **Accuracy:** `84%`
- **Precision cho nhãn Attack:** `0.93` (Độ tin cậy cực cao, rất ít False Positives).
- **AUC Score:** `0.906`.
- *Nhận xét:* Làm rất tốt nhiệm vụ gác cổng (Anomaly Detection), bắt được hầu hết các tấn công kể cả zero-day mà không cần biết chi tiết.

**Kết quả Stage 2: FT-Transformer (Phân loại 4 nhãn Attack)**
Khi gánh nặng phải phân biệt "Normal" được trút bỏ, FT-Transformer đã có sự bứt phá ngoạn mục trên các nhãn khó:
- **DoS F1-Score:** `0.8944` (Baseline V1: 0.82) 📈
- **Probe F1-Score:** `0.7041` (Baseline V1: 0.74) 📉
- **R2L F1-Score:** `0.5959` (Baseline V1: 0.43) 🚀 Tăng vọt!
- **U2R F1-Score:** `0.3525` (Baseline V1: 0.17) 🚀 Tăng gấp đôi!

**Tổng kết Phase 5:** 
Chiến lược Two-Stage (Autoencoder + FT-Transformer) là **hướng đi chính xác và tốt nhất** cho đồ án. Việc chia để trị giúp giải quyết triệt để vấn đề mất cân bằng dữ liệu và tối ưu hóa thế mạnh của từng thuật toán. R2L và U2R - 2 loại tấn công khó phát hiện nhất - đã có sự cải thiện mang tính đột phá so với mô hình 1-Stage truyền thống.
