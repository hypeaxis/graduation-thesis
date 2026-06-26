# Báo cáo Phân tích V8.1 (Threshold Calibration)

## 1. Mục tiêu
Sử dụng mô hình V7.1 (SMOTE PortScan + Focal Loss) và tiến hành hạ ngưỡng (Threshold) phán đoán của PortScan để tăng tỷ lệ Recall cho PortScan mà không cần phải huấn luyện lại mô hình.

## 2. Kết quả Thực nghiệm

| Ngưỡng PortScan (Threshold) | Macro F1 Toàn cục | PortScan Recall | PortScan Precision | PortScan F1 | Đánh giá |
|-----------------------------|-------------------|-----------------|--------------------|-------------|----------|
| **Mặc định (Argmax - 0.5)** | 74.87%            | 19.16%          | 14.19%             | 16.31%      | Cân bằng nhất, nhưng PortScan vẫn thấp. |
| **Ngưỡng 0.3**              | 71.84%            | 54.85%          | 6.47%              | 11.57%      | Bắt đầu đánh nhầm nhiều Benign. |
| **Ngưỡng 0.2**              | 65.16%            | 87.67%          | 3.81%              | 7.30%       | Recall cao nhưng Precision sập thảm hại. |
| **Ngưỡng 0.15**             | 63.10%            | 92.51%          | 3.49%              | 6.72%       | Đánh nhầm hàng ngàn gói tin Benign. |
| **Ngưỡng 0.1**              | 60.76%            | 97.36%          | 3.24%              | 6.28%       | Gần như bắt được 100% PortScan nhưng phá hủy hoàn toàn Benign. |

## 3. Phân tích & Kết luận
- **Hiện tượng:** Khi hạ ngưỡng bắt PortScan xuống (ví dụ 0.2), mô hình đã thành công trong việc gom được 87.6% lượng PortScan thực tế. Tuy nhiên, nó cũng vơ vét luôn hàng nghìn gói tin Benign vào lưới PortScan, khiến độ chính xác (Precision) tụt xuống mức 3.8%.
- **Nguyên nhân gốc rễ:** Trong không gian dữ liệu 80 chiều (được trích xuất từ CICFlowMeter), ranh giới đặc trưng của `PortScan` và các tín hiệu chạy ngầm `Benign` bị **chồng lấp (overlap) gần như hoàn toàn**.
- **Kết luận:** Kỹ thuật Threshold Calibration **KHÔNG THỂ** giải quyết được bài toán này. Việc hạ ngưỡng chỉ mang tính chất hack (đánh đổi Benign lấy PortScan) chứ không làm mô hình thông minh hơn.
- **Hướng đi tiếp theo:** Bắt buộc phải sử dụng **V8.2 (Cost-Sensitive Learning / Class Weights)** để ép mô hình học sự phân biệt tinh vi bằng toán học, hoặc **V8.3 (Feature Engineering)** để thêm đặc trưng không gian thời gian (số port truy cập / giây) nhằm bóc tách hoàn toàn PortScan khỏi Benign.
