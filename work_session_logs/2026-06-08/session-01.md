# Session Log - 2026-06-08 (session-01)

## Phân tích Dự án Tham khảo và Đề xuất Hướng đi

Trong phiên làm việc này, chúng ta đã tiến hành nghiên cứu 2 dự án liên quan đến NSL-KDD của các tác giả khác để tìm hướng tinh chỉnh mô hình FT-Transformer hiện tại (vốn đang chững lại ở F1 ~0.66 do zero-day attacks).

### 1. Phân tích các dự án tham khảo
- **nsl-kdd-master (Machine Learning truyền thống):** Sử dụng K-Means gom cụm kết hợp Random Forest. Mặc dù báo cáo Detection Rate rất cao, mô hình này bị dính False Alarm Rate (Cảnh báo giả) cực lớn (14-16%), hoàn toàn không phù hợp cho IDS thực tế. Điểm đáng học hỏi duy nhất là họ dùng Feature Selection (Attribute Ratio) để chọn lọc đầu vào.
- **Dự án DNN-main:** Xây dựng mạng Deep Neural Network khổng lồ (2048, 1024, 512 neurons). Kết quả chạy trên tập Test KDD-20 cho thấy F1 Score chỉ đạt `0.595`, **thấp hơn** so với Baseline FT-Transformer của chúng ta. Điều này chứng minh rằng việc cố gắng nhồi thêm layers hay regularization vào Neural Network không giải quyết được zero-day attacks. Chúng ta đã đi đúng hướng khi chọn cơ chế Attention của FT-Transformer.

### 2. Ý tưởng "Chiến lược Two-Stage" (Lưu lại để cân nhắc sau)
Một giải pháp được đề xuất là chia bài toán thành 2 giai đoạn:
- **Stage 1 (Phát hiện bất thường):** Một mô hình Binary Classification chuyên biệt chỉ để phân biệt kết nối là `Normal` hay `Attack`.
- **Stage 2 (Phân loại tấn công):** Nếu Stage 1 xác định là Attack, dữ liệu mới được đẩy qua mô hình thứ 2 để phân loại rạch ròi DoS, Probe, U2R, R2L.

**Lý do tạm gác lại:** Cách này đòi hỏi phải bảo trì và deploy 2 mô hình cùng lúc, làm tăng độ phức tạp của API, tăng độ trễ (latency), và đi ngược lại thiết kế Backend hiện tại (1 mô hình xử lý 122 chiều trả ra 5 nhãn). Do đó, cách này sẽ được giữ lại làm "kế hoạch dự phòng" nếu các phương pháp tối ưu dữ liệu thất bại.

### 3. Mục tiêu Phase 4: Lọc đặc trưng (Feature Selection)
Thay vì đổi kiến trúc mô hình, chúng ta sẽ tối ưu **Dữ liệu đầu vào**:
1. Đánh giá mức độ quan trọng của toàn bộ 122 features (sử dụng Random Forest).
2. Lược bỏ các features mang giá trị nhiễu hoặc không quan trọng (tối đa cắt 20-30%).
3. Huấn luyện lại FT-Transformer V1 trên tệp dữ liệu đã được làm sạch này để giúp mô hình focus vào luật lõi (core rules) chống lại Zero-day attacks.
