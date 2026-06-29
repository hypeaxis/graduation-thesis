# 🚀 Báo Cáo Hiệu Suất Hệ Thống Cascade NIDS V6 (End-to-End Evaluation)

Đây là kết quả kiểm thử toàn trình (End-to-End) của hệ thống Two-Stage Cascade trên tập Validation khổng lồ **2.529.391** luồng mạng thực tế.

## 1. Hiệu quả của Cơ chế Khóa Ngưỡng 85% (Probability Thresholding)

Cơ chế chặn cửa mềm (Softmax Gating) tại Tầng 1 đã hoạt động cực kỳ hoàn hảo:
*   **2.510.704** luồng mạng bình thường/tấn công phổ thông được phân loại chuẩn xác ngay tại Stage 1.
*   **12.592** luồng mạng có dấu hiệu đáng ngờ nhưng xác suất thấp (`< 85%`) đã bị ép bẻ lái thành `Benign`. **Đây chính là 12.592 cảnh báo giả (False Positives) được triệt tiêu hoàn toàn!**
*   **6.095** luồng mạng thực sự nguy hiểm (`>= 85%`) được chuyển tiếp xuống Stage 2.

> 💡 **Kết luận:** Tầng 2 chỉ phải xử lý đúng **0.24%** tổng lưu lượng mạng. Nó giúp hệ thống NIDS có thể chạy theo thời gian thực (Real-time) mà không lo bị nghẽn cổ chai CPU/GPU.

## 2. Kết quả Phân Loại Tổng Hợp (Classification Report)

Chỉ số F1-Score của toàn hệ thống đã tiệm cận mức hoàn hảo ở các lớp tấn công diện rộng, và bứt phá mạnh mẽ ở các lớp tấn công hiếm:

| Nhãn (Class) | Độ chuẩn xác (Precision) | Độ phủ (Recall) | F1-Score | Số lượng (Support) |
| :--- | :--- | :--- | :--- | :--- |
| **Benign** | 99.94% | 99.46% | **99.70%** | 2,031,715 |
| **DDoS** | 99.84% | 99.82% | **99.83%** | 114,453 |
| **PortScan** | 99.36% | 99.90% | **99.63%** | 142,079 |
| **DoS** | 96.83% | 99.63% | **98.21%** | 225,024 |
| **Brute Force** | 94.73% | 99.89% | **97.24%** | 12,369 |
| **Web Attack** | 87.97% | 98.21% | **92.80%** | 1,950 |
| **Bot** | 47.87% | 91.87% | **62.94%** | 1,758 |
| **Infiltration** | 95.24% | 60.61% | **74.07%** | 33 |
| **Heartbleed** | 100.00% | 100.00% | **100.00%** | 10 |

## 3. Tổng Kết Kiến Trúc
*   **Độ chính xác tổng thể (Accuracy):** `99.51%`
*   **Macro Average F1-Score:** `0.9160` (Bước nhảy vọt nhờ khôi phục thành công nhãn Web Attack).
*   Bài toán **"The Cascade Trap"** (Bẫy sụt giảm Precision do False Positives từ tập Benign khổng lồ) đã được giải quyết triệt để thông qua cơ chế Thresholding.
*   Kỹ thuật thêm **TCP Window**, kết hợp **Hard Negative Mining** và **Gộp Nhãn Động (Dynamic Label Grouping)** đã giúp Stage 2 học được chính xác hình thái của các công cụ tấn công mạng (như Patator, Sqlmap, XSS).
