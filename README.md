# 🛡️ AI-Powered Network Intrusion Detection System (NIDS)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![React](https://img.shields.io/badge/React-Frontend-61DAFB.svg)

> **Đồ án Tốt nghiệp: Nghiên cứu và Xây dựng Hệ thống Phát hiện Xâm nhập Mạng thông minh dựa trên mô hình Học Sâu thời gian thực.**

---

## 📖 Giới thiệu Tổng quan (Overview)

Hệ thống **AI-Powered NIDS** được thiết kế để giám sát, phân tích lưu lượng mạng và phát hiện các mối đe dọa an ninh mạng nguy hiểm (như *DoS, DDoS, PortScan, Brute-Force, Web Attacks, Infiltration, Botnet...*) theo thời gian thực. 

Thay vì sử dụng các thuật toán Machine Learning truyền thống vốn gặp hạn chế lớn khi xử lý dữ liệu mạng phân tán, đồ án này tiên phong ứng dụng kiến trúc **FT-Transformer (Feature Tokenizer Transformer)** kết hợp với mô hình **Cascade Ensemble**. Đây là một trong những hệ thống học sâu và học máy lai hiện đại nhất, mang lại độ chính xác cực đoan (>99%) đồng thời hạn chế tối đa rủi ro False Positives (Cảnh báo giả).

---

## 🧭 Cấu trúc Dự án (Duality Project Structure)

Dự án này được quy hoạch chặt chẽ theo tiêu chuẩn Khoa học Dữ liệu (Data Science Project Structure), chia làm **2 Workspace** song song đại diện cho 2 bộ dữ liệu và 2 giai đoạn vòng đời của hệ thống:

### 🌟 1. Nhánh Triển khai Thực tế: `NSL_KDD_Workspace`
Đây là hệ thống hoàn chỉnh có thể mang đi trình diễn và triển khai thực chiến. Mô hình AI được tối ưu hóa cực nhẹ trên bộ dữ liệu kinh điển NSL-KDD, kết hợp với giao diện giám sát Cyberpunk.

*   **`Final_Product/`**: Trái tim của hệ thống thực chiến.
    *   `backend/`: Máy chủ API tốc độ cao viết bằng FastAPI. Tích hợp hệ thống giả lập cuộc tấn công mạng thực tế thông qua việc tự động sinh Log Snort.
    *   `frontend/`: Dashboard giám sát mạng Dark Mode viết bằng React. Hiển thị thông số (Total Traffic, Alert Confidence, Threat Type) mượt mà bằng Recharts.
    *   `inference/`: Bộ máy chuẩn hóa luồng mạng thời gian thực bằng kỹ thuật Cửa sổ trượt (Sliding Window), và thực thi dự đoán bằng PyTorch.
*   **`src/`**: Mã nguồn lõi dùng để tiền xử lý đặc trưng và huấn luyện mô hình FT-Transformer cho NSL-KDD.
*   **`data/`** & **`models/`**: Nơi chứa dữ liệu và trọng số mô hình đã được huấn luyện.

### 🚀 2. Nhánh Nghiên cứu Nâng cao: `CIC_IDS_2017_Workspace`
Đây là nhánh thử nghiệm công nghệ tột đỉnh. Bài toán đặt ra là phải đối phó với bộ dữ liệu khổng lồ **CIC-IDS-2017 (2.8 triệu dòng)**, cực đoan về độ mất cân bằng và phức tạp trong việc nhận diện Botnet cũng như Infiltration.

*   **`src/`**: Khối não của dự án.
    *   `data_processing/`: Cỗ máy Feature Engineering bổ sung các đặc tính chết người như Tỷ lệ Luồng (Flow Ratio).
    *   `models/`: Bản thiết kế **FT-Transformer V2** tiên tiến. Đột phá với `DropPath` (Stochastic Depth) và `LayerScale`.
    *   `training/`: Kịch bản huấn luyện hệ thống **Hybrid Ensemble V7** (FT-Transformer kết hợp Random Forest và KNN qua cơ chế Voting khắt khe).
*   **`docs/`**: Toàn bộ báo cáo phân tích hiệu năng mô hình, lịch sử phát triển kiến trúc Cascade, và chứng minh toán học.
*   **`archive/`**: Bảo tàng lưu trữ các phiên bản tiền nhiệm (V2 -> V6) để phục vụ việc tra cứu và so sánh.

---

## ⚙️ Hướng dẫn Cài đặt & Vận hành (Quick Start)

### Yêu cầu hệ thống (Prerequisites)
- Hệ điều hành: Linux / WSL (Ubuntu 20.04+)
- Python: 3.8 trở lên
- Bộ nhớ: RAM 8GB (Khuyến nghị 16GB nếu muốn chạy nhánh CIC-IDS)
- Cổng mạng khả dụng: 8000 (Cho Backend/Frontend)

### Vận hành Ứng dụng Giao diện Giám sát (Nhánh NSL-KDD)
Hệ thống được thiết kế để "Chạy trong 1 nốt nhạc":

1. Mở Terminal tại thư mục gốc của dự án.
2. Khởi chạy Script đóng gói:
   ```bash
   chmod +x NSL_KDD_Workspace/Final_Product/run.sh
   cd NSL_KDD_Workspace/Final_Product/
   ./run.sh
   ```
3. Mở trình duyệt web và truy cập: **`http://localhost:8000`**
4. Giao diện Cyberpunk sẽ hiện ra. Bạn hãy nhấn nút **`[ Simulate & Detect ]`** góc trên bên phải để giả lập cuộc tấn công mạng và theo dõi phản ứng tức thời của AI!

---

## 🔬 Những Điểm Sáng Kỹ thuật (Technical Innovations)

Đồ án này giải quyết những bài toán hóc búa nhất của ngành An toàn thông tin:

1. **Kiến trúc Two-Stage Cascade:**
   Hệ thống không đoán nhãn ngay, mà chia làm Tầng 1 (Gating) để chặn phần lớn luồng bình thường, chỉ những luồng khả nghi mới bị đẩy xuống Tầng 2 (Expert) phân tích chuyên sâu. Tối ưu cực đại tốc độ và hạ thấp cảnh báo giả.
2. **Từ Log thô sang Ma trận (Real-time Sliding Window):**
   Biến đổi luồng Log Snort thành Tensor mạng tức thời qua cơ chế trượt cửa sổ thời gian (Sliding Window).
3. **Hard Negative Mining & Hybrid Ensemble:**
   Sử dụng kỹ thuật thu thập lại các dự đoán sai của AI để huấn luyện nâng cao. Dùng cơ chế Hội đồng biểu quyết đa thuật toán (Voting) để dập tắt triệt để rủi ro nhận diện nhầm Web Attack và Botnet.

---

## 🛠️ Liên hệ & Tác giả
* **Sinh viên thực hiện**: [Điền tên của bạn vào đây]
* **Mã số sinh viên**: [Điền MSSV]
* **Giáo viên hướng dẫn**: [Điền tên GVHD]
* **Trường/Khoa**: [Điền tên Trường]
