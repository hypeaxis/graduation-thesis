# 🛡️ AI-Powered & Hybrid Network Intrusion Detection System (NIDS)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![React](https://img.shields.io/badge/React-Frontend-61DAFB.svg)
![Snort](https://img.shields.io/badge/Snort-IDS-CD2027.svg)

> **Đồ án Tốt nghiệp: Nghiên cứu và Xây dựng Hệ thống Phát hiện Xâm nhập Mạng thông minh dựa trên mô hình Học Sâu thời gian thực và Kiến trúc Hybrid IDS.**

---

## 📖 Giới thiệu Tổng quan (Overview)

Hệ thống **AI-Powered Hybrid NIDS** được thiết kế để giám sát, phân tích lưu lượng mạng và phát hiện các mối đe dọa an ninh mạng nguy hiểm (như *DoS, DDoS, PortScan, Brute-Force, Web Attacks, Infiltration, Botnet...*) theo thời gian thực. 

Điểm đột phá của dự án là sự kết hợp giữa **Luật tĩnh (Signature-based IDS qua Snort)** và **Học sâu (Anomaly-based qua Machine Learning/Deep Learning)**. Thay vì chỉ sử dụng các thuật toán truyền thống, hệ thống ứng dụng kiến trúc **FT-Transformer (Feature Tokenizer Transformer)** kết hợp với mô hình **Cascade/Hybrid Ensemble**. Qua đó, mang lại độ chính xác cực đại (>99%) đồng thời hạn chế tối đa rủi ro False Positives (Cảnh báo giả) trong môi trường mạng thực tế.

---

## 🧭 Cấu trúc Dự án (Tri-Core Project Structure)

Dự án được quy hoạch chặt chẽ theo từng giai đoạn và mục tiêu cụ thể, chia làm **3 Workspace** đại diện cho 2 bộ dữ liệu nghiên cứu và 1 môi trường thực chiến:

### 🌟 1. Nhánh Nghiên cứu Nền tảng: `NSL_KDD_Workspace`
Hệ thống thử nghiệm ban đầu nhằm chứng minh tính khả thi của mô hình AI. Mô hình được huấn luyện trên bộ dữ liệu kinh điển NSL-KDD.
*   **`Final_Product/`**: 
    *   `backend/`: Máy chủ API mô phỏng luồng log mạng.
    *   `frontend/`: Dashboard giám sát mạng Dark Mode hiển thị trực quan thông số bằng React & Recharts.
    *   `inference/`: Bộ máy chuẩn hóa luồng mạng thời gian thực (Sliding Window).
*   **`src/`, `data/`, `models/`**: Mã nguồn tiền xử lý và huấn luyện FT-Transformer cho NSL-KDD.

### 🚀 2. Nhánh Nghiên cứu Nâng cao: `CIC_IDS_2017_Workspace`
Thử nghiệm các công nghệ học sâu tột đỉnh. Giải quyết bài toán với dữ liệu khổng lồ **CIC-IDS-2017 (2.8 triệu dòng)**, đối phó với mức độ mất cân bằng dữ liệu cực đoan của Infiltration và Botnet.
*   **`src/data_processing/`**: Cỗ máy Feature Engineering trích xuất các đặc trưng quan trọng (Tỷ lệ Luồng - Flow Ratio, v.v.).
*   **`src/models/`**: Bản thiết kế **FT-Transformer V2** tiên tiến, đột phá với `DropPath` (Stochastic Depth) và `LayerScale`.
*   **`src/training/`**: Kịch bản huấn luyện hệ thống **Hybrid Ensemble** (kết hợp FT-Transformer, Random Forest, KNN qua cơ chế Voting).
*   **`docs/` & `archive/`**: Tài liệu phân tích hiệu năng và bảo tàng lưu trữ các phiên bản kiến trúc.

### ⚔️ 3. Nhánh Triển khai Thực chiến (Testbed): `Custom_IDS_Testbed`
Đây là môi trường **Hybrid IDS** hoạt động thực tế trên hạ tầng **WSL (Windows Subsystem for Linux)**. Tích hợp toàn trình (End-to-End Pipeline) từ việc bắt gói tin vật lý đến hiển thị cảnh báo lên Dashboard.
*   **Tích hợp Snort & CICFlowMeter**: Bắt luồng mạng theo thời gian thực, kết hợp cảnh báo luật tĩnh (Snort) và trích xuất 78+ đặc trưng dòng chảy mạng (CICFlowMeter).
*   **Data Pipeline Thực tế**: Kịch bản tự động hóa luồng dữ liệu thô sang vector đặc trưng, đẩy vào FastAPI/Node.js backend.
*   **Xuyên Máy Tính**: Môi trường giả lập Attacker (Laptop 1) tấn công Victim (Laptop 2 chạy WSL Mirrored Network).
*   **Thư mục chính**: `configs/`, `scripts/`, `docs/` chứa tài liệu cấu trúc và file khởi chạy kiểm thử thực tế.

---

## 🔬 Những Điểm Sáng Kỹ thuật (Technical Innovations)

Đồ án này giải quyết những bài toán hóc búa nhất của ngành An toàn thông tin:

1. **Kiến trúc Hybrid IDS (Signature + Anomaly):**
   Kết hợp sự chính xác tuyệt đối của Snort (luật đã biết) với khả năng nhận diện các cuộc tấn công Zero-day của Machine Learning/Deep Learning.
2. **Cơ Chế Two-Stage Cascade & Hybrid Ensemble:**
   Phân luồng Gating (Tầng 1) chặn lưu lượng bình thường, Tầng 2 (Expert) dùng cơ chế Hội đồng biểu quyết (Voting) giữa Transformer và các thuật toán Tree-based để khử False Positives với các dạng tấn công phức tạp.
3. **Từ Log thô sang Vector (Real-time Pipeline):**
   Xây dựng hệ thống tự động bắt gói tin, trích xuất đặc trưng (Feature Extraction) bằng CICFlowMeter/Snort và truyền tải mượt mà qua luồng inference tính bằng milliseconds.
4. **Mạng Giả lập Tấn công WSL (Mirrored Network):**
   Đột phá trong việc giả lập tấn công mạng LAN xuyên thiết bị thực tế nhờ cấu hình Mirrored Networking trên Windows 11 và WSL.

---

## ⚙️ Hướng dẫn Cài đặt & Vận hành (Quick Start)

### Yêu cầu hệ thống (Prerequisites)
- Hệ điều hành: Linux / WSL 2 (Ubuntu 20.04/22.04), Windows 11 (cho nhánh Testbed)
- Python: 3.8+ & Node.js
- Bộ nhớ: RAM 8GB (Khuyến nghị 16GB cho CIC-IDS-2017 & Testbed)

### Truy cập chi tiết từng nhánh
Do mỗi không gian làm việc (Workspace) có môi trường chạy đặc thù, vui lòng tham khảo tài liệu chi tiết tại từng nhánh:
1. **[Nhánh NSL-KDD (Final Product Demo)](./NSL_KDD_Workspace/Final_Product/README.md)** *(Chạy mô phỏng sẵn có)*
2. **[Nhánh Nghiên cứu CIC-IDS-2017](./CIC_IDS_2017_Workspace/README.md)** *(Huấn luyện AI chuyên sâu)*
3. **[Nhánh Thực chiến IDS Testbed](./Custom_IDS_Testbed/docs/hybrid_ids_architecture.md)** *(Hướng dẫn cấu hình WSL & Snort)*

---

## 🛠️ Liên hệ & Tác giả
* **Sinh viên thực hiện**: [Điền tên của bạn vào đây]
* **Mã số sinh viên**: [Điền MSSV]
* **Giáo viên hướng dẫn**: [Điền tên GVHD]
* **Trường/Khoa**: [Điền tên Trường]
