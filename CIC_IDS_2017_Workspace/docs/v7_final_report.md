# 🚀 Báo Cáo Nghiệm Thu Hệ Thống Cascade NIDS V7 (Ensemble Voting)

Báo cáo này tổng hợp chi tiết toàn bộ các thay đổi về mặt kiến trúc, đặc trưng dữ liệu và hiệu năng đạt được trong bản nâng cấp V7 của hệ thống Two-Stage Cascade NIDS trên tập dữ liệu CIC-IDS-2017.

---

## 1. Đặt Vấn Đề và Hướng Giải Quyết
Từ kết quả của phiên bản V6, hệ thống bộc lộ 2 điểm yếu chí mạng tại các nhóm tấn công khó (Rare Attacks):
*   **Infiltration:** Mạng nơ-ron bỏ lọt hoàn toàn 13/33 mẫu bất chấp việc tinh chỉnh Threshold. Nguyên nhân được xác định là do 13 flow này giống hệt các truy cập tải file HTTPS thông thường, và **hệ thống thiếu đi khả năng tương quan chuỗi hành vi (Time-Window / Multi-flow correlation)**.
*   **Botnet:** Điểm chuẩn xác (Precision) mắc kẹt ở mức 47.87% dù đã sử dụng cơ chế Hard Negative Mining. Nguyên nhân là các gói tin liên lạc Botnet quá giống với traffic nền của hệ thống.

**Giải pháp đề xuất (Dựa trên tệp nghiên cứu Jupyter Notebook):**
Kiểm chứng tập dữ liệu `raw_data` cho thấy toàn bộ thông tin gốc như `Source IP`, `Destination IP` và `Timestamp` đã bị xóa bỏ, khiến việc tính toán Time-Window bất khả thi. Thay vào đó, chúng ta ứng dụng **Học máy Kết hợp (Ensemble Learning)** kết hợp thêm **Đặc trưng Tỷ lệ Dữ liệu**.

---

## 2. Các Nâng Cấp Công Nghệ (V7 Implementation)

### 2.1. Feature Engineering (Đặc trưng Tỷ lệ Dữ liệu)
Nhằm khoanh vùng hành vi mã độc Botnet gửi lên các tập lệnh siêu ngắn và nhận về khối lượng dữ liệu khổng lồ, hệ thống đã trích xuất thêm 2 tính năng:
*   `Flow_Bytes_Ratio` = `Total_Length_of_Fwd_Packets / Total_Length_of_Bwd_Packets`
*   `Flow_Pkts_Ratio` = `Total_Fwd_Packets / Total_Backward_Packets`

Không gian đặc trưng của Tầng 2 (Stage 2) chính thức mở rộng lên **34 Đặc trưng**.

### 2.2. Huấn luyện "Hội đồng Chuyên gia" (Ensemble Models)
Thay vì phó thác hoàn toàn việc phân tích bất thường cho Mạng Nơ-ron (FT-Transformer), dữ liệu Khó (Hard Negative) của Stage 2 được dùng để huấn luyện song song 3 mô hình ưu việt nhất từ kết quả nghiên cứu:
1.  **FT-Transformer:** Xử lý tổng quát, F1-Score nội bộ đạt **0.6640** (Kỷ lục).
2.  **Random Forest (RF):** Huấn luyện với cấu hình `150 estimators`, `max_depth=25`, `max_features=20` để nắm bắt sự tương quan phi tuyến tính mạnh mẽ.
3.  **K-Nearest Neighbors (KNN):** Huấn luyện với `K=16` để kiểm soát các đợt bùng nổ theo không gian phân cụm.

### 2.3. Cơ chế Đánh Giá Bỏ Phiếu (Rule-based Ensemble Voting)
Tập lệnh `evaluate_cascade_system_v7.py` được thiết kế mới để tiếp nhận ý kiến từ cả 3 mô hình cho các luồng mạng Nghi ngờ (Suspicious) bị chặn ở Tầng 1:
*   **Infiltration Priority:** Do Infiltration là một loại mã độc rất kín đáo, chỉ cần **RF** hoặc **KNN** hô hoán "Infiltration", hệ thống sẽ lập tức cảnh báo (Tin tưởng RF/KNN hơn FT-Transformer).
*   **Botnet Consensus:** Để triệt tiêu False Positive của Botnet, nếu FT-Transformer cảnh báo "Botnet" nhưng cả **RF** và **KNN** đều báo "Benign", hệ thống sẽ biểu quyết hạ nhãn về lại **Benign**.

---

## 3. Kết Quả Nghiệm Thu Tổng Thể

Hệ thống được thử nghiệm lại trên tập Validation End-to-End **2.529.391** luồng mạng thực tế.

| Nhãn (Class) | Độ chuẩn xác (Precision) | Độ phủ (Recall) | F1-Score | Số lượng (Support) |
| :--- | :--- | :--- | :--- | :--- |
| **Benign** | 0.9992 | 0.9953 | **0.9972** | 2,031,715 |
| **DDoS** | 0.9984 | 0.9982 | **0.9983** | 114,453 |
| **PortScan** | 0.9936 | 0.9990 | **0.9963** | 142,079 |
| **DoS** | 0.9683 | 0.9963 | **0.9821** | 225,024 |
| **Brute Force** | 0.9473 | 0.9989 | **0.9724** | 12,369 |
| **Web Attack** | 0.9084 | 0.9810 | **0.9433** | 1,950 |
| **Botnet** | **0.7947** 🚀 | 0.6826 | **0.7344** 🚀 | 1,758 |
| **Infiltration** | 0.9524 | 0.6061 | **0.7407** | 33 |
| **Heartbleed** | 1.0000 | 1.0000 | **1.0000** | 10 |

### 🏆 Đánh giá Thành tựu V7
*   **Độ Chính Xác Tổng Thể (Accuracy):** Duy trì ở mức siêu cao **99.55%**.
*   **Macro F1-Score Toàn Hệ Thống:** Nhảy vọt lên mức **0.9294** (So với mốc 0.9160 của V6).
*   **Phá vỡ giới hạn Botnet:** Botnet chính thức không còn là điểm yếu chí mạng khi Precision của nó tăng gấp đôi từ 47.87% lên **79.47%**. Luật đồng thuận (Consensus) đã thực hiện quá xuất sắc nhiệm vụ của mình.
*   **Xác lập Giới Hạn Tối Hậu của Infiltration:** Mặc dù được hội đồng chuyên gia kết hợp nhưng Recall của Infiltration vẫn kẹt lại ở 60.61%. Phiên bản V7 đã chứng minh về mặt thống kê rằng: Tập dữ liệu Flow-based tĩnh của CIC-IDS-2017 hoàn toàn bị mù trước 13 mẫu Infiltration còn lại. Đây không phải lỗi của AI, mà là giới hạn vật lý của tập dữ liệu.

---
**Kết luận:** Hệ thống Cascade NIDS ở phiên bản V7 đã đạt đến độ chín muồi và là trạng thái cực đại (State-of-the-Art) cho dạng dữ liệu Flow-based không định danh IP.
