# Lịch sử Phiên làm việc: Nâng cấp lên CIC-IDS-2017

Tài liệu này ghi lại toàn bộ quá trình đập đi xây lại hệ thống IDS để tương thích với bộ dữ liệu hiện đại `CIC-IDS-2017` (thay thế cho `NSL-KDD`), bao gồm cả việc thiết kế lại Data Pipeline, kiến trúc Model (FT-Transformer V2) và tích hợp Backend.

---

## Session 1: Tiền xử lý dữ liệu và Chunking
**Trạng thái: Hoàn tất (✅)**

### 1. Phân tích Model Cũ
- Quét mô hình `best_model (1).pt` do user cung cấp.
- **Kết quả**: Xác nhận đây là một mạng FT-Transformer chất lượng cao dành cho CIC-IDS-2017 (đầu vào 77 features, đầu ra 15 classes), đạt Validation F1 = `0.964`. 

### 2. Thiết kế Script Tiền xử lý (`cic_data_processor.py`)
Viết một Pipeline Python hoàn toàn mới để xử lý 2.8 triệu dòng dữ liệu mạng.
- **Bổ sung Custom Features**: Tạo riêng 2 features toán học để khắc chế "Tấn công chậm" (Slow attacks như Slowloris, Slowhttptest):
  - `Custom_Fwd_Pkt_Rate`: Tốc độ gói tin gửi đi.
  - `Custom_Slow_Index`: Tỷ lệ giữa tổng thời gian luồng và thời gian trễ tối đa giữa 2 gói tin (Flow_Duration / IAT_Max).
- Kích thước ma trận đầu vào thay đổi từ 77 lên **81 features**. Do đó, phải xây dựng model V2 để tương thích, không dùng lại model cũ.

### 3. Khắc phục lỗi tràn RAM (OOM)
- Dataset có dung lượng gần 1GB. Pandas bị sập (Exit Code 137) khi cố dùng `train_test_split` trên RAM 4GB.
- **Giải pháp**: Ứng dụng kỹ thuật "Index Shuffling" in-place. Xáo trộn vị trí dòng ngẫu nhiên và dùng `iloc` cắt trực tiếp từng khoảng index, sau đó giải phóng bộ nhớ.

### 4. Chiến lược Phân mảnh (Chunk Splitting)
Hệ thống đã xẻ 2.8 triệu dòng dữ liệu ra thành 4 cụm hoàn toàn không trùng lặp:
1. `cic_train_chunk.csv` (500,000 dòng): Dùng làm tài nguyên cốt lõi để Model học thuật.
2. `cic_test_chunk_1.csv` (775,958 dòng): Tập Validation để kiểm chứng trong quá trình train.
3. `cic_test_chunk_2.csv` (775,958 dòng): Tập Test dự phòng.
4. `cic_test_chunk_3.csv` (775,960 dòng): Tập Test dự phòng độc lập cuối cùng.

**Kết luận Session 1**: Nền tảng dữ liệu đã vững chắc tuyệt đối. Sẵn sàng cho việc tạo mới Model.
