# Lịch sử Phiên làm việc: Nâng cấp lên CIC-IDS-2017

Tài liệu này ghi lại toàn bộ quá trình đập đi xây lại hệ thống IDS để tương thích với bộ dữ liệu hiện đại `CIC-IDS-2017` (thay thế cho `NSL-KDD`), bao gồm cả việc thiết kế lại Data Pipeline, kiến trúc Model (FT-Transformer V2) và tích hợp Backend.

## Ngày 12/06/2026: Tối ưu Thời gian Huấn luyện & Chống mất cân bằng dữ liệu
### 1. Tối ưu Hiệu suất Huấn luyện (Performance Optimization)
Ban đầu, cỗ máy GPU GTX 1050 (4GB) dự kiến mất tới **45 tiếng** để train 30 Epochs cho kiến trúc mạng FT-Transformer V2 có 1,088,655 tham số. Chúng ta đã áp dụng 3 kỹ thuật ép xung cực mạnh mà không cần đổi máy:
- **AMP (Automatic Mixed Precision)**: Sử dụng Float16 thay vì Float32, giúp giảm 50% lượng VRAM tiêu thụ và tăng gấp đôi tốc độ tính toán.
- **Tối ưu VRAM Thrashing**: Hạ `batch_size` từ 1024 xuống 256, giúp dữ liệu không bị tràn sang RAM hệ thống.
- **Cắt giảm Data**: Rút ngắn khối `cic_train_chunk.csv` từ 500k xuống 300k dòng.
- **CuDNN Benchmark**: Kích hoạt bộ tìm kiếm thuật toán cuDNN tự động của PyTorch.
👉 **Kết quả:** Thời gian huấn luyện giảm mạnh xuống chỉ còn **15 phút / Epoch**.

### 2. Xử lý Lỗi NaN & Khởi chạy Baseline (10 Epochs)
- **Vấn đề**: Các tham số quá lớn như *Flow Bytes/s* khiến Gradient bị nổ tung, đẩy `Loss = NaN`.
- **Giải pháp**: Nhúng lớp `StandardScaler` vào `phase2_train_v2.py` để chuẩn hóa toàn bộ dữ liệu trước khi nạp vào AI.
- **Thử nghiệm 10 Epochs**:
  - Máy chạy ổn định hoàn hảo. F1-Score leo dần từ `0.0455` (Epoch 1) lên `0.2910` (Epoch 9).
  - Điểm F1 không đạt >90% là do bị ảnh hưởng bởi những nhãn siêu hiếm (chỉ có 1-3 mẫu). Focal Loss ép AI học nhưng không có đủ mẫu thống kê. Khám phá ra **Accuracy Paradox** (Nghịch lý độ chính xác của Model cũ).

### 3. Quy hoạch Label & Khởi tạo Chiến dịch SMOTE
Nhận thấy giới hạn của AI, chúng ta đã can thiệp vào Data:
- Sửa đổi `cic_data_processor.py` để gộp 15 nhãn lắt nhắt thành **6 Nhóm Tấn công Cốt lõi** (Benign, DoS, DDoS, PortScan, Brute Force, Rare Attacks) thông qua hàm `group_labels`.
- Tích hợp **SMOTE** (Synthetic Minority Over-sampling Technique) vào `phase2_train_v2.py` để tự động sinh thêm 10,000 dòng dữ liệu nhân tạo cho các class yếu.
- Thay thế Focal Loss bất ổn bằng **CrossEntropyLoss + Label Smoothing (0.1)** kết hợp `class_weights` tuyến tính.

### Trạng thái
- **Hoàn thành**: Đã chuẩn bị xong File mã nguồn, script theo dõi thời gian thực (`monitor_training.sh`) và các File dữ liệu CSV Chunk.
- **Tiếp theo**: Phát lệnh huấn luyện bản nâng cấp cuối cùng này và tích hợp kết quả vào Real-time Simulator (Session 4).

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
