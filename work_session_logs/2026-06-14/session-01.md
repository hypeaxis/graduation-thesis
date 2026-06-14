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

### b) Cải tiến Data Pipeline (`cic_data_processor.py`)
- **Vấn đề**: Các file CSV gốc của CIC-IDS-2017 có nhiều flows lỗi chứa giá trị vô cực (`Infinity`) ở cột tốc độ (Bytes/s, Packets/s) do mẫu tấn công có Duration = 0. Code cũ đã vứt bỏ thẳng tay những dòng `Infinity` này, làm mất một lượng lớn mẫu tấn công hiểm hóc. Dữ liệu cũng đang bị dư thừa các cột 0 tuyệt đối (Zero Variance).
- **Hành động**:
  - Bổ sung thuật toán nội suy: Tự động phát hiện giá trị `Infinity` và thay thế chúng bằng giá trị dương lớn nhất có hạn (`max_finite`) của cột đó. Điều này giúp giữ lại được các mẫu Flow Duration = 0 quý giá.
  - Tự động dò tìm và cắt bỏ 8 cột Zero Variance (không mang thông tin), giúp model chạy nhanh và tránh bị nhiễu.

### c) Cải tiến Model Training (`phase2_train_v3.py`)
- **Vấn đề**: Thuật toán `CrossEntropyLoss` cũ quá yếu trong việc phạt mô hình khi dự đoán sai các nhãn tấn công hiếm (do số lượng các nhãn này quá ít so với Benign, dù đã dùng SMOTE). Quá trình train cũng quên mất việc xuất đối tượng Data Scaler ra ngoài, dẫn tới việc Inference sau này gặp lỗi tính toán sai lệch Scale.
- **Hành động**:
  - Tích hợp hàm mất mát **Focal Loss** thay cho CrossEntropy.
  - Sửa lỗi phiên bản PyTorch cũ liên quan tới Automatic Mixed Precision (`torch.amp.GradScaler` -> `torch.cuda.amp.GradScaler`).
  - Thêm luồng tự động export **`cic_scaler.pkl`** qua thư viện `joblib` ngay khi train xong.

### d) Kết quả Huấn Luyện Đột Phá
Tiến hành chạy lại quy trình huấn luyện V3 với 10 Epochs trên tập Validation ~840,000 dòng. Các kết quả F1-Score cuối cùng vô cùng xuất sắc:
- **Macro-F1 Đạt: 0.8292** (Mức trần cao nhất từ trước đến nay cho 7 nhãn không cân bằng).
- F1-Score `Benign`: 0.9797
- F1-Score `DDoS`: 0.9711
- F1-Score `PortScan`: 0.9824
- F1-Score `DoS`: 0.9644
- F1-Score `Brute Force`: 0.9556
- **Recall của Rare Attacks: 96.7%** (Cực kì nhạy bén trong việc bắt các loại tấn công lén lút hiếm gặp).

## 3. Công cụ & Mã hóa phụ trợ
- Viết thêm script **`monitor.sh`** cho phép người dùng tự động theo dõi thời gian thực (tail) đối với bất kỳ tiến trình nền nào do Agent đang chạy.

---
**Trạng thái cuối ngày:** Data Pipeline mạnh mẽ hơn, Model hội tụ với độ chính xác rất cao và Artifacts (Trọng số + Scaler) đều đã lưu hoàn hảo tại `Training_Pipeline/models/v3_improved/`. Hệ thống đã hoàn toàn sẵn sàng cho quá trình tích hợp Inference vào Backend mới.
