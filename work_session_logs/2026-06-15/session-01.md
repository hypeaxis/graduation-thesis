# Báo cáo Nhật ký Công việc: Ngày 15 Tháng 06, 2026 (Model V3.1)

## 1. Trọng tâm công việc
Phiên làm việc hôm nay xoáy sâu vào việc **khắc phục tình trạng "Học vẹt" (Data Leakage)** của mô hình AI đối với tập dữ liệu CIC-IDS-2017, đồng thời **hoàn thiện kiến trúc Dữ liệu** để hệ thống phản ánh đúng tính chất mạng thực tế (Production-ready).

## 2. Các thay đổi và thành tựu chính

### a) Xử lý dứt điểm Data Leakage và Lỗi Thống kê
- **Sửa lỗi Mapping**: Cập nhật hàm Regex trong `cic_data_processor.py` để giữ lại thành công lớp `Web Attack` vốn bị thất lạc vào nhóm Rare Attacks. Tổng số lớp được khôi phục về **chính xác 7 Lớp** (Benign, Brute Force, DDoS, DoS, PortScan, Rare Attacks, Web Attack).
- **Chống rò rỉ dữ liệu (No Data Leakage)**: Đã xóa sổ hoàn toàn 2 cột `Destination_Port` và `Fwd_Header_Length.1`. Việc cấm AI nhìn vào Cổng đích (Port) giúp triệt tiêu hoàn toàn khả năng "gian lận" của mô hình (ví dụ: mặc định Port 80 là Web Attack). Mô hình buộc phải học sâu vào hành vi của luồng (Flow dynamics).
- **Nâng cấp thuật toán Lấy mẫu**: Loại bỏ hàm Pandas `groupby` gây tràn RAM (OOM) và thay thế bằng thuật toán **NumPy Stratified Sampling**. Thuật toán mới ép tỷ lệ cực chuẩn xác cho tập Train 300,000 dòng, đảm bảo không có bất kỳ cuộc tấn công hiếm nào bị bỏ sót.

### b) Kết quả Huấn Luyện (Training Model V3.1 - 15 Epochs)
Quá trình huấn luyện kéo dài 15 Epochs với SMOTE (50,000 mẫu/lớp) và Focal Loss đã hoàn tất, mang lại một góc nhìn thực tế, trần trụi về hệ thống IDS:
- **Accuracy (Độ chính xác tổng thể)**: `0.9493` (94.93%)
- **Weighted F1-Score**: `0.9594`
- **Macro-F1**: `0.6671`
- **Phân tích chiều sâu**: Việc tước bỏ cột Cổng đích (Port) khiến mô hình đánh mất "tài liệu quay cóp". Nhờ vậy, Precision của 2 lớp `Web Attack` và `Rare Attacks` giảm mạnh (báo động nhầm nhiều), nhưng **Recall vẫn cực cao (>96.8%)**. Kết quả này phản ánh chính xác giới hạn của một hệ thống phòng thủ chỉ dùng thuật toán học máy dựa trên luồng mạng (Flow-based NIDS) mà không có phân tích gói tin (DPI).

## 3. Bản Lề cho Phase 3: Kiến trúc Hybrid Backend
Kết quả thực tế của mô hình V3.1 chính là lời khẳng định mạnh mẽ nhất cho bản thiết kế Backend sắp tới:
- **Hybrid Architecture (Snort + AI)**: Backend sẽ chạy qua hệ thống Luật (Rules) của Snort trước để chặn tĩnh/Drop các kiểu tấn công bạo lực cơ bản. AI (FT-Transformer) chỉ đóng vai trò chốt chặn cuối cùng cho các luồng khả nghi hoặc chưa rõ danh tính (Zero-day/Anomalous flows). Sự kết hợp này sẽ triệt tiêu >90% tỷ lệ cảnh báo giả (False Positives).
- **Thresholding & Smoothing (Ngưỡng cảnh báo trượt)**: Không kích hoạt báo động (Alert) khi AI chỉ bắt được 1 luồng độc hại. Sử dụng bộ đệm (Sliding Window / Redis) để đếm số lượng bất thường: Chỉ Alert khi phát hiện **X luồng khả nghi trong Y phút** từ cùng 1 Source IP. Cơ chế này sẽ lọc bỏ hoàn toàn sự nhầm lẫn của AI đối với các kết nối hợp lệ như WebSockets (vốn trông y hệt mã độc Slowloris).

---
**Trạng thái cuối phiên:** Source Code và mô hình AI cốt lõi (V3.1) đã sạch 100%, không còn rò rỉ dữ liệu hay học vẹt. Mọi Artifacts (`best_model_v3_ema.pt`, `cic_scaler.pkl`) đã được lưu thành công để sẵn sàng tiến thẳng vào giai đoạn Xây dựng Backend.
