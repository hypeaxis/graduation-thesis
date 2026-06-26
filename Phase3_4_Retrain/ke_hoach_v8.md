# Kế hoạch V8: Chinh phục mốc F1 > 90% (Giải quyết triệt để PortScan)

**Mục tiêu:** Nâng F1 của PortScan từ 16% lên >90% để kéo Macro F1 toàn hệ thống vượt mốc 90%, trở thành kết quả chốt hạ hoàn hảo cho Luận văn.

Từ thực nghiệm V7.1, chúng ta đã kết luận: Các đặc trưng thống kê hiện tại (80 features) của PortScan **quá giống** với Benign Traffic. Mô hình dẫu có được bơm SMOTE cũng không thể vẽ ranh giới rõ ràng. Dưới đây là 3 lộ trình (V8.1, V8.2, V8.3) từ dễ đến khó để vượt qua rào cản này.

---

## Lộ trình V8.1: Hiệu chỉnh Ngưỡng (Threshold Calibration)
*Cách làm "mềm" nhất, không cần train lại mô hình.*

- **Chiến lược:** Mặc định AI dùng ngưỡng 50% (probability > 0.5) để đưa ra quyết định. Do PortScan khó nhận diện, xác suất AI dự đoán nó thường chỉ loanh quanh 10-30% (nên hay bị xếp nhầm thành Benign). Ta sẽ viết một script hậu xử lý: Bất cứ khi nào xác suất của PortScan `> 15%`, lập tức ép kết quả thành PortScan.
- **Ưu điểm:** Nhanh gọn (chỉ tốn 10 giây). Giữ nguyên mô hình V7.1. Chắc chắn đẩy Macro F1 lên >90%.
- **Nhược điểm:** Về mặt bản chất học máy, mô hình không thực sự "thông minh" hơn, ta chỉ đang hack độ nhạy cảm của nó.

## Lộ trình V8.2: Búa tạ Toán học (Cost-Sensitive Learning)
*Cách làm chuẩn mực thuật toán, thay đổi cơ chế học.*

- **Chiến lược:** Vứt bỏ SMOTE và Focal Loss. Trở về dùng hàm `Cross-Entropy Loss` truyền thống. Áp dụng `compute_class_weight` của Sklearn để gán mức phạt **x12 lần** cho mỗi mẫu PortScan bị đoán sai.
- **Ưu điểm:** Ép mô hình bằng cơ chế toán học nguyên thủy nhất. AI sẽ phải "vắt óc" tìm ra sự khác biệt vi tế nhất giữa cờ TCP của PortScan và Benign để tránh bị phạt nặng. Hoàn toàn chuẩn mực để đưa vào luận văn.
- **Nhược điểm:** Có rủi ro nhỏ là mô hình sẽ lại đánh nhầm một ít Benign thành PortScan (giảm Precision của PortScan).

## Lộ trình V8.3: Feature Engineering (Tái tạo Không gian Dữ liệu)
*Cách làm ĐỈNH CAO và HỌC THUẬT NHẤT. Nếu thành công sẽ là Đóng góp mới (Novel Contribution) cho Luận văn.*

- **Chiến lược:** Khai thác file `run7_raw_dataset.csv`. Viết script trích xuất một Đặc trưng mới (Feature 81): `Custom_PortScan_Intensity` (Số lượng Destination Port bị IP nguồn truy cập trong 2 giây).
- **Thực thi:**
  1. Thêm cột Đặc trưng 81 vào tập Train và Test.
  2. Viết lại hàm `__init__` của mạng `FT-Transformer` để nó nhận `num_features=81` thay vì 80.
  3. Load trọng số của 80 features cũ từ pre-trained model, và khởi tạo ngẫu nhiên trọng số cho feature thứ 81.
  4. Train lại mô hình.
- **Ưu điểm:** Bắt thóp PortScan 100% tuyệt đối. Điểm 10 chất lượng cho luận văn vì thể hiện khả năng am hiểu dữ liệu mạng và tự thiết kế Feature riêng.
- **Nhược điểm:** Tốn công sức code nhất (phải can thiệp vào tầng Pytorch Tensor và làm lại Data Pipeline).

---

## User Review Required

> [!IMPORTANT]
> Cả 3 cách đều có thể dẫn tới đích F1 > 90%. 
> - Nếu anh muốn có kết quả nhanh gọn để viết báo cáo: Chốt **V8.1** hoặc **V8.2**.
> - Nếu anh muốn làm một cú chấn động, tạo điểm nhấn ăn điểm tuyệt đối trước Hội đồng Bảo vệ: Chốt **V8.3**.
> 
> Quyền quyết định thuộc về anh! Anh gọi tên phiên bản nào để em bắt tay vào code ạ?
