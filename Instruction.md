Kế hoạch xây dựng sản phẩm

ĐỒ ÁN CUỐI KHOÁ

# Giai đoạn 1: Xây dựng Data Pipeline với Snort

**Mục tiêu:** Bắt gói tin thực tế và tự động hóa quá trình tiền xử lý log từ Snort để tạo ra vector 122 đặc trưng (feature) theo chuẩn NSL-KDD.

- **Thiết lập môi trường nền tảng:** Cấu hình môi trường phát triển đồng bộ sử dụng WSL (Windows Subsystem for Linux) kết hợp với VS Code để thao tác với các công cụ mạng của Linux. Khởi tạo Git repository để quản lý phiên bản nghiêm ngặt.
- **Triển khai & Cấu hình Snort:** Cài đặt Snort trên môi trường Linux. Cấu hình Snort hoạt động ở chế độ _Packet Logger_ để lắng nghe toàn bộ lưu lượng mạng ở tầng thấp và xuất log liên tục dưới định dạng file cấu trúc (CSV/JSON).
- **Feature Extraction (Tiền xử lý Log):** Viết script (Python/Node.js) chạy ngầm để đọc log từ Snort. Script này sẽ nhóm các gói tin thô thành các đặc trưng thống kê trong cửa sổ thời gian 2 giây (ví dụ: count, serror_rate). Output cuối cùng là vector 122 chiều khớp với format đầu vào của mô hình AI.

# Giai đoạn 2: Tối ưu Độ chính xác và Triển khai AI

**Mục tiêu:** Nâng cao độ chính xác cho "bộ não" của hệ thống và đưa mô hình vào môi trường production.

- **Tinh chỉnh Mô hình (Fine-tuning):** Đánh giá lại mô hình Autoencoder (tầng 1) và Transformer (tầng 2). Thực hiện các kỹ thuật xử lý dữ liệu để giảm tỷ lệ báo động giả (False Positive) và tăng khả năng nhận diện các cuộc tấn công tinh vi.
- **Đóng gói Mô hình:** Chuyển đổi mô hình từ PyTorch/TensorFlow sang định dạng ONNX. Quá trình này giúp mô hình nhẹ hơn và suy luận (inference) nhanh hơn rất nhiều.
- **Xây dựng Model API:** Tạo một microservice sử dụng framework FastAPI của Python để load mô hình ONNX. API này nhận dữ liệu 122 chiều từ tầng tiền xử lý log và trả về nhãn phân loại: Normal, DoS, Probe, R2L, U2R.
- **Tối ưu Độ trễ (Latency):** Tối ưu hóa API để đảm bảo thời gian từ lúc gửi vector đặc trưng đến lúc nhận kết quả phân loại chỉ tính bằng milliseconds.

# Giai đoạn 3: Phát triển Backend và Dashboard

- **Mục tiêu:** Xây dựng "thể xác" cho hệ thống, cung cấp giao diện tương tác thời gian thực cho SOC Analyst.
- **Backend Server:** Sử dụng Node.js làm máy chủ trung tâm. Node.js sẽ nhận dữ liệu cảnh báo từ Model API và quản lý các luồng kết nối.
- **Giao tiếp Thời gian thực:** Tích hợp Socket.io hoặc WebSocket vào Node.js để đẩy trực tiếp các cảnh báo (alerts) lên frontend.
- **Phát triển Web Dashboard:** Thiết kế giao diện trực quan bao gồm:
  - Biểu đồ lưu lượng mạng tổng quan.
  - Bảng log cảnh báo hiển thị các kết nối bị đánh dấu là Attack (kèm nhãn phân loại, IP nguồn, thời gian).
  - Phân loại màu sắc theo mức độ nghiêm trọng (Severity), ví dụ: U2R sẽ hiển thị cảnh báo màu đỏ chót.

# Giai đoạn 4: Tích hợp Hệ thống và Giả lập Tấn công

**Mục tiêu:** Nối các mảnh ghép và chứng minh hệ thống hoạt động thực tế dưới áp lực tấn công.

- **System Integration:** Nối liền mạch luồng dữ liệu: Snort -> Script tiền xử lý -> Python (Model API) -> Node.js (Backend) -> Web Dashboard. Đảm bảo hệ thống không bị crash khi lưu lượng tăng cao.
- **Mô phỏng Tấn công (Attack Simulation):** Setup một mạng LAN ảo. Sử dụng các công cụ như hping3, nmap, hoặc Metasploit để bắn các luồng traffic chứa mã độc vào máy đang chạy Snort.
- **Đánh giá Thực chiến:** Quan sát Dashboard để kiểm chứng hệ thống có bắt đúng loại tấn công vừa giả lập hay không. Thực hiện đối chiếu thời gian phản hồi với các hệ thống IDS mã nguồn mở khác như Snort (ở chế độ IDS) hoặc Suricata.

# Giai đoạn 5: Viết Báo cáo và Chuẩn bị Bảo vệ

**Mục tiêu:** Hoàn thiện tài liệu học thuật và chuẩn bị cho buổi bảo vệ trước hội đồng.

- **Hoàn thiện Báo cáo:** Cập nhật các chương lý thuyết. Trình bày sâu vào Chương Kiến trúc Hệ thống, Quy trình tích hợp Snort, và Kết quả giả lập tấn công thực tế.
- **Chuẩn bị Demo Thực tế:** Chuẩn bị kịch bản Live Demo. Đồng thời, quay sẵn một video backup quá trình bật tool tấn công và màn hình Dashboard nhảy cảnh báo để phòng trường hợp mạng gặp sự cố trong ngày bảo vệ