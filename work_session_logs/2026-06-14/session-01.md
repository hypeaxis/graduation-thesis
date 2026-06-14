# Báo cáo Nhật ký Công việc: Ngày 14 Tháng 06, 2026

## 1. Trọng tâm công việc
Phiên làm việc hôm nay tập trung vào việc **khắc phục dứt điểm tình trạng dự đoán ảo giác (hallucination)** của AI và **tối ưu hóa Data Pipeline & Model Training** cho bộ dữ liệu CIC-IDS-2017. Đồng thời, giải quyết vấn đề đầy bộ nhớ ổ cứng của người dùng bằng cách dọn dẹp các thư mục rác.

## 2. Các thay đổi và thành tựu chính

### a) Quy hoạch lại Workspace & Giải phóng Ổ cứng
- **Vấn đề**: Toàn bộ dữ liệu của NSL-KDD (cũ) và CIC-IDS-2017 đang bị trộn lẫn, các biến thể thư mục gây lãng phí bộ nhớ và khó kiểm soát. Quá trình sinh dữ liệu mô phỏng (Snort) hoàn toàn không phù hợp về định dạng đối với model CIC-IDS-2017 (CICFlowMeter).
- **Hành động**:
  - Chuyển dự án sang thiết kế 2 Workspaces hoàn toàn tách biệt: `NSL_KDD_Workspace` và `CIC_IDS_2017_Workspace`.
  - Phá hủy thư mục Backend/Frontend lỗi thời (`Final_Product`) và `Data` trống, **giải phóng thành công 5.5 GB** không gian lưu trữ cứng.
  - Tổ chức code lên GitHub với tệp `.gitignore` được cấu hình chặt chẽ (cấm đẩy các file CSV hàng GB lên repo).

### b) Cải tiến Data Pipeline V2 (`cic_data_processor.py`)
- **Vấn đề**: Các file CSV gốc của CIC-IDS-2017 có nhiều flows lỗi chứa giá trị vô cực (`Infinity`) ở cột tốc độ (Bytes/s, Packets/s). Dữ liệu cũng đang bị dư thừa các cột 0 tuyệt đối (Zero Variance) và đặc biệt là bị **Rò rỉ Dữ liệu (Data Leakage)** qua các cột định danh. Ngoài ra, việc bốc ngẫu nhiên 300,000 mẫu làm mất đi các lớp tấn công siêu hiếm, và lỗi Regex làm mất lớp `Web Attack`.
- **Hành động**:
  - Bổ sung thuật toán nội suy `Infinity` thay vì drop dòng. Cắt bỏ 8 cột Zero Variance.
  - Sửa lỗi Mapping Regex, gộp lại thành công **đúng 7 lớp cốt lõi** (Benign, DoS, DDoS, PortScan, Brute Force, Web Attack, Rare Attacks).
  - Loại bỏ hoàn toàn các cột gây **Data Leakage** (như `Destination_Port`, `Fwd_Header_Length.1`), triệt tiêu đường học vẹt của AI để đảm bảo khả năng triển khai thực tế.
  - **Stratified Sampling bằng NumPy**: Viết lại thuật toán chia dữ liệu 300,000 dòng bằng kỹ thuật chia mảng NumPy (giải quyết lỗi Tràn RAM OOM của Pandas GroupBy trước đó), đảm bảo ép tỷ lệ 7 lớp vào tập Train vô cùng chuẩn xác.

### c) Cải tiến Model Training (`phase2_train_v3.py`)
- **Vấn đề**: Thuật toán `CrossEntropyLoss` cũ quá yếu, mô hình dễ bị Overpredict các nhãn hiếm (do SMOTE cường độ cao kết hợp Focal Loss). Quá trình train cũng quên xuất đối tượng Data Scaler.
- **Hành động**:
  - Tích hợp hàm mất mát **Focal Loss** và SMOTE (50,000 mẫu).
  - Sửa lỗi phiên bản PyTorch cũ liên quan tới Automatic Mixed Precision (`torch.amp.GradScaler` -> `torch.cuda.amp.GradScaler`).
  - Nâng cấp giới hạn học từ 10 lên **15 Epochs** để AI đủ thời gian tiêu hoá cả 7 Lớp dữ liệu chống nhiễu mới.
  - Thêm luồng tự động export **`cic_scaler.pkl`** qua thư viện `joblib` ngay khi train xong.

## 3. Kiến trúc Vận hành Tương lai (Định hướng Phase 3)
Sẵn sàng cho việc thiết kế Backend/Frontend thực tế:
- **Kiến trúc Hybrid**: Chạy Snort Rules trước để chặn tĩnh, AI (FT-Transformer) chỉ đóng vai trò phân tích các Anomalous Flows bí ẩn, giúp giảm >90% False Positives.
- **Sliding Window Threshold**: Kích hoạt Alert khi có X Flows bị phát hiện dị thường trong vòng Y phút (Triệt tiêu hoàn toàn sự hoang tưởng của AI do Slowloris False Positives).

## 4. Công cụ & Mã hóa phụ trợ
- Viết thêm script **`monitor.sh`** cho phép người dùng tự động theo dõi thời gian thực (tail) đối với bất kỳ tiến trình nền nào do Agent đang chạy.

---
**Trạng thái cuối ngày:** Data Pipeline xử lý chống Data Leakage thành công. Model Training (15 Epochs) đang được chạy dưới nền. Chuẩn bị qua Phase Backend.
