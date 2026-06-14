# BÁO CÁO TỔNG KẾT SẢN PHẨM: HỆ THỐNG PHÁT HIỆN TẤN CÔNG MẠNG (IDS) TWO-STAGE

## 1. Tổng quan Kiến trúc Hệ thống
Sản phẩm là một hệ thống Phát hiện Xâm nhập (IDS) được xây dựng dựa trên trí tuệ nhân tạo, có nhiệm vụ bắt và phân tích các luồng mạng từ Snort, sau đó phân loại xem luồng mạng đó là bình thường (Normal) hay tấn công (DoS, Probe, R2L, U2R).

Kiến trúc bao gồm:
- **Frontend**: Ứng dụng web hiển thị dashboard, bảng điều khiển và biểu đồ thời gian thực.
- **Backend (FastAPI)**: API xử lý dữ liệu, điều phối tiến trình suy luận và giả lập lưu lượng Snort.
- **AI Inference Engine (Two-Stage)**: Trái tim của hệ thống sử dụng kết hợp 2 mô hình học sâu (Autoencoder và FT-Transformer) thay vì kiến trúc 1-Stage truyền thống.

## 2. Chiến lược Two-Stage Đột Phá
Dữ liệu mạng (NSL-KDD / Snort) thường mất cân bằng nghiêm trọng (Normal và DoS chiếm đại đa số, trong khi R2L và U2R rất hiếm và khó phát hiện). Kiến trúc cũ (1-Stage) khiến mô hình bị "mờ mắt" bởi dữ liệu Normal và dự đoán kém ở các lớp hiếm.

Chúng ta đã áp dụng mô hình **Two-Stage Pipeline** để giải quyết triệt để vấn đề này:

### Stage 1: Autoencoder (Người gác cổng)
- **Thuật toán:** Autoencoder (Unsupervised Learning) được huấn luyện CHỈ trên dữ liệu Normal.
- **Nhiệm vụ:** Hoạt động như một bộ lọc (Anomaly Detector). Tính toán Lỗi Tái tạo (Reconstruction Error - MSE). Nếu lỗi `< 0.008481` (Threshold tối ưu), gói tin lập tức được gắn nhãn `Normal` và kết thúc quá trình. Nếu lỗi `>= 0.008481`, gói tin bị nghi ngờ là Tấn công và được chuyển sang Stage 2.
- **Thành tựu:** Test Macro-F1 đạt **0.84**, Precision đạt **0.93**. Khả năng chống nhiễu cực tốt, bắt được zero-day attacks mà không cần biết nhãn trước đó.

### Stage 2: FT-Transformer (Chuyên gia phân tích)
- **Thuật toán:** FT-Transformer (Supervised Learning).
- **Nhiệm vụ:** Nhận những gói tin đã bị Stage 1 lọc (bỏ qua Normal), tập trung cao độ vào việc phân biệt 4 loại hình tấn công tinh vi: `DoS`, `Probe`, `R2L`, `U2R`.
- **Thành tựu:** Sự cải thiện mang tính đột phá so với Baseline 1-Stage cũ:
  - **R2L F1-Score:** Tăng vọt từ `0.43` lên **`0.5959`** (+16%)
  - **U2R F1-Score:** Tăng vọt từ `0.17` lên **`0.3525`** (+18.2%, tăng gấp đôi)
  - **DoS F1-Score:** Tăng từ `0.82` lên **`0.8944`**

## 3. Cấu trúc Triển khai (Deployment)
Toàn bộ mã nguồn, trọng số (weights), và file cấu hình của hệ thống Two-Stage đã được hợp nhất và đóng gói tại thư mục `final/model_packages/two_stage_v5`.
- **`autoencoder_v2_best.h5`**: Weights của mô hình Keras Autoencoder.
- **`best_model.pt`**: Weights của mô hình PyTorch FT-Transformer (phiên bản 4-class).
- **`scaler.pkl`**: Công cụ chuẩn hóa dữ liệu từ [0, 1] trước khi đưa vào mạng nơ-ron.

Hệ thống Inference hiện tại (`snort_ft_transformer_inference_v5.py`) tải song song 2 Framework (`tensorflow` và `torch`) với hiệu suất cao, xử lý luồng đi từ cảnh báo Snort (alerts) thành ma trận đặc trưng 122 chiều và đưa ra quyết định dự đoán cuối cùng.

## 4. Kết luận
Chiến lược "chia để trị" bằng Autoencoder và FT-Transformer là lựa chọn chính xác và hoàn hảo nhất cho đồ án. Hệ thống không chỉ xử lý vấn đề mất cân bằng nhãn mà còn linh hoạt cho thực tế: Stage 1 có thể phát hiện các phương thức tấn công hoàn toàn mới, trong khi Stage 2 đảm bảo độ chuẩn xác cao cho các phương thức đã biết.
