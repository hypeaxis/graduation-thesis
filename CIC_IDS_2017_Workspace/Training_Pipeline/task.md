# Lộ trình Nâng cấp CIC-IDS-2017

## Session 1: Data Engineering & Foundation
- [x] Khởi tạo thư mục dự án `CIC_IDS_2017_Project/`.
- [x] Phát triển script `cic_data_processor.py` chống tràn RAM.
- [x] Chạy script phân mảnh: Cắt 500k dòng Train, và 3 cụm Test hoàn toàn riêng biệt.
- [x] Xác thực kích thước ma trận đầu ra là 81 features (đã tính luôn features cho tấn công chậm).

## Session 2: Model Architecture V2
- [x] Đổi tên file Preview thành `phase2_ft_transformer_v2.py`.
- [x] Lập trình chi tiết các class lõi (Bỏ các `NotImplementedError`).
- [x] Tích hợp LayerScale.
- [x] Tích hợp DropPath.
- [x] Thay thế GELU bằng GEGLU.

## Session 3: Model Training & Evaluation
- [ ] Lập trình `phase2_train_v2.py`.
- [ ] Cài đặt thuật toán Dynamic Focal Loss (Alpha tự động).
- [ ] Chạy huấn luyện trên `cic_train_chunk.csv`.
- [ ] In kết quả đánh giá trên `cic_test_chunk_1.csv`.

## Session 4: Real-time Integration
- [ ] Xây dựng bộ giả lập CIC-IDS-2017 Simulator trên Backend.
- [ ] Cập nhật Router và Inference Engine dùng model V2 (81 features).
- [ ] Nghiệm thu giao diện Dashboard cuối cùng.
