# 🚀 Hướng dẫn Huấn luyện Hệ thống NIDS V4 (Two-Stage Cascade)

Tài liệu này là cẩm nang từng bước để bạn có thể mang toàn bộ thư mục `Training_Pipeline` này lên một máy chủ khác (hoặc máy tính có GPU mạnh hơn) và tiến hành huấn luyện từ A-Z một cách chính xác nhất.

---

## 🛠️ 1. Yêu cầu Hệ thống & Môi trường (Prerequisites)

*   **Phần cứng:** 
    *   RAM tối thiểu 16GB (để chạy an toàn tệp dữ liệu).
    *   GPU hỗ trợ CUDA (NVIDIA) tối thiểu 4GB VRAM (khuyến nghị 8GB+).
*   **Phần mềm & Thư viện (Python 3.8+):**
    *   `torch`, `pandas`, `numpy`, `scikit-learn`
    *   `imbalanced-learn` (Cực kỳ quan trọng, bắt buộc phải cài đặt để dùng được `SMOTEENN`).
    *   `tqdm`, `matplotlib`, `seaborn`

**Lệnh cài đặt nhanh trên máy mới:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install pandas numpy scikit-learn imbalanced-learn tqdm matplotlib seaborn joblib
```

---

## 📂 2. Cấu trúc Thư mục Yêu cầu Trước khi Chạy

Hãy chắc chắn rằng trong cùng thư mục với các file Python, bạn đã có thư mục `raw_data/` chứa các file `.csv` gốc của bộ dữ liệu CIC-IDS-2017 (tổng cộng khoảng 2.8 triệu dòng).

```text
Training_Pipeline/
├── raw_data/                 <-- BẮT BUỘC (Chứa các file pcap_ISCX.csv tải từ Kaggle)
├── phase2_ft_transformer_v2.py
├── cic_data_processor_v2.py
├── phase2_train_v4_stage1.py
├── phase2_train_v4_stage2.py
├── cascade_inference.py
└── TRAINING_GUIDE_V4_CASCADE.md
```

---

## 🚀 3. Lộ trình Triển khai (Pipeline Execution)

Bạn hãy thực thi lần lượt 4 lệnh dưới đây theo đúng thứ tự. 

### Bước 1: Tiền xử lý dữ liệu (Feature Engineering & Splitting)
Tiến trình này sẽ đọc toàn bộ dữ liệu thô, biến đổi `Destination_Port` thành các nhóm `Port Category`, thêm các đặc trưng toán học `Custom Features`, chia data thành các mảnh (Chunks) và fit `PowerTransformer`.
*   **Lệnh chạy:**
    ```bash
    python cic_data_processor_v2.py
    ```
*   **Thời gian dự kiến:** ~5-10 phút (phụ thuộc tốc độ ổ cứng và CPU).
*   **Kết quả:** Sẽ tự động tạo ra thư mục `processed_data/` chứa các file `cic_train_stage1.csv`, `cic_train_stage2.csv` và `cic_test_full.csv`.

### Bước 2: Huấn luyện Stage 1 (General Model - 6 Lớp)
Huấn luyện mô hình FT-Transformer để lọc ra 95% luồng dữ liệu mạng thông thường.
*   **Lệnh chạy:**
    ```bash
    python phase2_train_v4_stage1.py
    ```
*   **Thời gian dự kiến:** ~15 phút/Epoch × 15 Epochs = **Khoảng 3 - 4 tiếng**.
*   **Kết quả:** Tạo ra thư mục `models/v4_cascade/stage1/` chứa model `.pt`, scaler và biểu đồ training.

### Bước 3: Huấn luyện Stage 2 (Expert Model - 3 Lớp)
Huấn luyện mô hình FT-Transformer thứ 2 chuyên giải quyết các mẫu "Nghi ngờ" (Suspicious) từ Stage 1 để tìm ra Web Attack và Rare Attacks.
*   **Lệnh chạy:**
    ```bash
    python phase2_train_v4_stage2.py
    ```
*   **Thời gian dự kiến:** Mẫu ít hơn và mạng nhỏ hơn, ~5 phút/Epoch × 25 Epochs = **Khoảng 2 tiếng**.
*   **Kết quả:** Tạo ra thư mục `models/v4_cascade/stage2/` chứa model `.pt`, scaler và biểu đồ training.

### Bước 4: Đánh giá Tổng thể Kiến trúc Phân tầng (Cascade Inference)
Sau khi có cả 2 mô hình, dùng logic định tuyến (Routing) để đánh giá F1-Score cuối cùng trên tập Test hoàn toàn xa lạ.
*   **Lệnh chạy:**
    ```bash
    python cascade_inference.py --evaluate
    ```
*   **Kết quả:** Sẽ in ra màn hình bảng `Classification Report` gộp. Mục tiêu của chúng ta là **Macro-F1 > 90%** tại bước này!

---

## 🎯 4. Tiêu chí Đánh giá (Nghiệm thu Đồ án)

Khi chạy xong Bước 4, hãy chụp lại bảng Classification Report. Nếu hệ thống hiển thị:
- **Macro-F1:** Đạt > 90%.
- **Brute Force (F1):** Đạt > 85%.
- **Web Attack (F1):** Đạt > 80%.

👉 **Bạn đã hoàn thành xuất sắc đồ án!** Các file weight `best_stage1_ema.pt` và `best_stage2_ema.pt` có thể được mang đi tích hợp trực tiếp vào file Backend API của hệ thống giao diện Web Dashboard.
