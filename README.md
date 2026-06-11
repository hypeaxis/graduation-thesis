# 🛡️ AI-Powered Network Intrusion Detection System (NIDS)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![React](https://img.shields.io/badge/React-Frontend-61DAFB.svg)

> **Đồ án Tốt nghiệp: Nghiên cứu và Xây dựng Hệ thống Phát hiện Xâm nhập Mạng thông minh dựa trên mô hình Học Sâu thời gian thực.**

---

## 📖 Giới thiệu Tổng quan (Overview)

Hệ thống **AI-Powered NIDS** được thiết kế để giám sát, phân tích lưu lượng mạng và phát hiện các mối đe dọa an ninh mạng nguy hiểm (như *DoS, DDoS, PortScan, Brute-Force, Web Attacks, Slowloris...*) theo thời gian thực. 

Thay vì sử dụng các thuật toán Machine Learning truyền thống (Decision Tree, Random Forest) vốn gặp hạn chế lớn khi xử lý dữ liệu mạng đồ sộ, đồ án này tiên phong ứng dụng kiến trúc **FT-Transformer (Feature Tokenizer Transformer)**. Đây là một trong những kiến trúc mạng học sâu hiện đại nhất dành riêng cho dữ liệu dạng bảng (Tabular Data), mang lại độ chính xác vượt trội đồng thời hạn chế tối đa rủi ro False Positives (Cảnh báo giả).

---

## 🧭 Cấu trúc Dự án (Duality Project Structure)

Dự án này được quy hoạch thành **2 Nhánh nghiên cứu song song**, đại diện cho 2 giai đoạn vòng đời của hệ thống:

### 🌟 Nhánh 1: Sản phẩm Cuối (Final Product) - NSL-KDD
Đây là hệ thống hoàn chỉnh có thể mang đi trình diễn và triển khai. Mô hình AI được tối ưu hóa cực nhẹ trên bộ **122 đặc trưng (features)** của NSL-KDD, kết hợp với giao diện giám sát Cyberpunk.

* **`/IDS_Final_Product/`**: Trái tim của hệ thống thực chiến.
  * `backend/`: Máy chủ API tốc độ cao viết bằng FastAPI. Tích hợp `simulator.py` để đóng giả các đợt tấn công mạng thực tế thông qua việc tự động sinh Log Snort.
  * `frontend/`: Dashboard giám sát mạng Dark Mode. Ứng dụng Zero-Install React qua CDN, biểu diễn các thông số (Total Traffic, Alert Confidence, Threat Type) mượt mà bằng Recharts.
  * `inference/`: Bộ máy chuẩn hóa luồng mạng thời gian thực (`snort_preprocess_122.py`) bằng kỹ thuật Sliding Window (Cửa sổ trượt), và thực thi mô hình PyTorch.
* **`/MLAnomalyDetection/`**: Trung tâm huấn luyện Model (R&D). Chứa các file `train_improved.py`, cấu hình rút trích đặc trưng, xử lý mất cân bằng dữ liệu (SMOTE, ADASYN), và bộ scaler.
* **`Final_Submission_Package.tar.gz`**: Gói nộp đồ án khép kín (Backup).

### 🚀 Nhánh 2: Nghiên cứu Nâng cấp Mở rộng - CIC-IDS-2017
Đây là nhánh thử nghiệm giới hạn công nghệ mới. Mục tiêu là xử lý bộ dữ liệu khổng lồ **CIC-IDS-2017 (2.8 triệu dòng)** và chống lại các cuộc Tấn công chậm (Low-and-Slow Attacks).

> 📥 **Tải Dataset (Khuyến nghị):** Do kích thước thư mục Dataset thô lên tới hơn 800MB, mã nguồn trên GitHub không bao gồm dữ liệu thô. Bạn có thể tải tập dữ liệu CIC-IDS-2017 chính thức tại đây: [Kaggle - Network Intrusion Dataset](https://www.kaggle.com/datasets/chethuhn/network-intrusion-dataset). Sau khi tải, vui lòng giải nén vào thư mục `/CIC_IDS_2017_Project/raw_data/`.

* **`/CIC_IDS_2017_Project/`**: Thư mục cách ly hoàn toàn với nhánh 1.
  * `processed_data/`: Nơi lưu trữ chiến lược **Chunk Splitting**. Dữ liệu được cắt thành 1 khối Train (500k dòng) và 3 khối Test độc lập (775k dòng/khối) bằng Index Shuffling in-place để chống tràn RAM (OOM).
  * `cic_data_processor.py`: Cỗ máy Feature Engineering bổ sung các đặc tính chết người dành riêng cho Slow Attacks (như `Custom_Fwd_Pkt_Rate` và `Custom_Slow_Index`).
  * `phase2_ft_transformer_v2.py`: Bản thiết kế **FT-Transformer V2**. Đột phá công nghệ với `DropPath` (Stochastic Depth), `LayerScale`, và `GEGLU Activation`.
  * `phase2_train_v2.py`: Kịch bản huấn luyện thông minh tích hợp **Dynamic Focal Loss** (Tự động cân bằng class dựa trên tỷ lệ hiếm).

---

## ⚙️ Hướng dẫn Cài đặt & Vận hành (Quick Start)

### Yêu cầu hệ thống (Prerequisites)
- Hệ điều hành: Linux / WSL (Ubuntu 20.04+)
- Python: 3.8 trở lên
- Bộ nhớ: RAM 8GB (Khuyến nghị 16GB nếu muốn chạy nhánh CIC-IDS)
- Cổng mạng khả dụng: 8000 (Cho Backend/Frontend)

### Vận hành Nhánh 1: Giao diện Giám sát (Dashboard)
Hệ thống được thiết kế để "Chạy trong 1 nốt nhạc":

1. Mở Terminal tại thư mục gốc của dự án.
2. Khởi chạy Script đóng gói:
   ```bash
   chmod +x IDS_Final_Product/run.sh
   cd IDS_Final_Product/
   ./run.sh
   ```
3. Mở trình duyệt web và truy cập: **`http://localhost:8000`**
4. Giao diện Cyberpunk sẽ hiện ra. Bạn hãy nhấn nút **`[ Simulate & Detect ]`** góc trên bên phải để giả lập cuộc tấn công mạng và theo dõi các cột biểu đồ phản ứng tức thời!

---

## 🔬 Những Điểm Sáng Kỹ thuật (Technical Innovations)

Đồ án này không chỉ đơn thuần là phân loại dữ liệu, mà giải quyết những bài toán hóc búa nhất của ngành An toàn thông tin:

1. **Từ Log thô sang Ma trận Toán học (Real-time Sliding Window):**
   Thay vì đọc file CSV tĩnh, hệ thống (Nhánh 1) thu thập chuỗi Log Snort (chỉ chứa IP/Port/Time), sau đó dùng thuật toán Cửa sổ trượt (Sliding Window) để tự động tính toán các chỉ số phức tạp (Như số lượng kết nối trong 2 giây qua tới cùng 1 máy chủ). Biến log văn bản thành Tensor 122 chiều trong tích tắc.
2. **Kiến trúc FT-Transformer V2 (Nhánh 2):**
   * **DropPath**: Vứt bỏ ngẫu nhiên các nơ-ron trong quá trình train để chống lại hiện tượng Học vẹt (Overfitting).
   * **LayerScale**: Giữ cho mạng nơ-ron siêu sâu không bị "phát nổ" Gradient.
3. **Dynamic Focal Loss:**
   Xử lý vấn đề Mất cân bằng dữ liệu cực đoan (Imbalanced Data). Có những loại tấn công chiếm 80% dữ liệu, có loại chỉ chiếm 0.1%. Hệ thống sẽ tự động phạt nặng Model nếu đoán sai loại 0.1%, ép Model phải học kỹ từng loại tấn công hiếm.
4. **Trị Tấn công Chậm (Low-and-Slow Defeat):**
   Bổ sung biến `Custom_Slow_Index` dựa trên tỷ lệ Thời gian sống của luồng chia cho IAT Max. Chuyên bắt bớ những luồng mạng "ngâm" kết nối hòng làm sập Server mà không gây ồn ào.

---

## 🛠️ Liên hệ & Tác giả
* **Sinh viên thực hiện**: [Điền tên của bạn vào đây]
* **Mã số sinh viên**: [Điền MSSV]
* **Giáo viên hướng dẫn**: [Điền tên GVHD]
* **Trường/Khoa**: [Điền tên Trường]

*Nếu bạn có bất kỳ câu hỏi nào về kiến trúc Model hoặc cách triển khai, vui lòng xem các file thiết kế chi tiết nằm trong thư mục `/models/` và `/Work_Logs/`.*
