# Session Log: 2026-06-13 - Session 01

## Goal
Kiểm tra, fix lỗi và hoàn thiện quá trình huấn luyện mô hình FT-Transformer V2 (Enhanced) trên bộ dữ liệu CIC-IDS-2017.

## Actions taken
- Cố gắng khởi chạy `phase2_train_v2.py`.
- Khắc phục lỗi thiếu thư viện (`SMOTE`, `compute_class_weight`) trong `phase2_train_v2.py`.
- Đồng bộ hóa các tham số khởi tạo (từ `n_layers`, `n_heads` thành `num_layers`, `num_heads`, v.v.) giữa file train và file định nghĩa kiến trúc `phase2_ft_transformer_v2.py`.
- Khởi chạy quá trình train trong 10 epochs thông qua môi trường ảo (`.venv`). Cập nhật `monitor_training.sh` để theo dõi luồng log đúng.
- Chờ mô hình hoàn tất 10 epochs và lưu lại trọng số tốt nhất.
- Phân tích và làm rõ vấn đề "High Loss" (do Label Smoothing và Class Weights gây ra), khẳng định giá trị thực tiễn của điểm Macro-F1.

## Files changed/cleaned
- `CIC_IDS_2017_Project/phase2_train_v2.py`: Thêm import, sửa tham số truyền vào hàm khởi tạo.
- `CIC_IDS_2017_Project/monitor_training.sh`: Trỏ lại đường dẫn trích xuất file log.

## Outputs and model status
- **Model Status:** Hoàn tất trọn vẹn 10 Epochs, không bị early stopping. Hội tụ tốt.
- **Kết quả xuất sắc nhất (Best Epoch 10):**
  - Train Macro-F1: 0.9374
  - Validation Macro-F1: 0.8311
  - Val Loss: ~1.318
- Trọng số tốt nhất đã được lưu tự động tại `CIC_IDS_2017_Project/models/v2_enhanced/best_model_v2.pt`.
- Giải quyết thành công *Accuracy Paradox* ở phiên bản model trước đó, chuyển hướng đánh giá toàn vẹn bằng Macro-F1 (0.8311 cho 6 classes không cân bằng).

## Next steps
- Mang trọng số `best_model_v2.pt` đưa vào kiểm thử Inference hoặc tích hợp hệ thống Real-time Simulator ở các Session tiếp theo.
