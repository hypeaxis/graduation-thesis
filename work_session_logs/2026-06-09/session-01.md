# Phiên làm việc: 09/06/2026 (Tích hợp Two-Stage Backend)

## 1. Mục tiêu
- Sau khi xác nhận sự ưu việt của chiến lược Two-Stage (Autoencoder + FT-Transformer) trong quá trình nghiên cứu, mục tiêu hôm nay là khóa (lock) phương án này cho sản phẩm cuối cùng.
- Tích hợp 2 mô hình vào luồng Inference của Backend.
- Đóng gói toàn bộ mô hình và viết báo cáo tổng kết sản phẩm.

## 2. Hoạt động đã thực hiện
- **Đóng gói Model:** Tạo thư mục `final/model_packages/two_stage_v5`. Copy toàn bộ các tệp cần thiết bao gồm trọng số `autoencoder_v2_best.h5` (Keras), `best_model.pt` (PyTorch) và bộ chuẩn hóa `scaler.pkl`.
- **Viết lại luồng Inference:** Sáng tạo phiên bản mới `snort_ft_transformer_inference_v5.py` cho phép Pipeline thực thi Two-Stage.
  - Tính Lỗi tái tạo (Reconstruction Error) bằng Autoencoder trên tập dữ liệu được tiền xử lý.
  - Sử dụng ngưỡng (Threshold) `0.008481` để phân tách `Normal`.
  - Luân chuyển những mẫu bị nhận diện là tấn công qua FT-Transformer để phân loại thành 4 lớp (`DoS`, `Probe`, `R2L`, `U2R`).
- **Nâng cấp Backend API:** Cập nhật `backend/app/pipeline_service.py` và `backend/app/main.py` để trỏ mặc định về luồng Two-Stage v5. Cài đặt thêm `tensorflow` cho môi trường ảo (venv) của backend.
- **Viết báo cáo tổng kết:** Soạn thảo `FINAL_PRODUCT_REPORT.md` phân tích kỹ lưỡng về kiến trúc và hiệu suất xuất sắc của hệ thống Two-Stage để phục vụ báo cáo đồ án.

## 3. Tổng kết
Kiến trúc AI của đồ án đã hoàn tất và kết nối thành công với Backend API. Hệ thống hiện tại có độ tin cậy cao, khả năng chống nhiễu (anomaly) tuyệt vời nhờ Autoencoder, và sức mạnh phân tách chi tiết cao của Transformer trên các luồng tấn công độc hại. Sẵn sàng cho việc demo bằng Frontend.
