# Báo Cáo Phiên Làm Việc (Session Log)
**Ngày:** 20/06/2026
**Dự án:** Đồ án Tốt nghiệp - Cải thiện mô hình FT-Transformer (Domain Adaptation)

---

## 1. Tóm tắt Mục tiêu Đầu ngày
Giải quyết hiện tượng sụt giảm độ chính xác (Concept Drift) khi mô hình AI phát hiện mã độc (FT-Transformer) chuyển từ môi trường huấn luyện lý tưởng (CIC-IDS-2017) sang môi trường thực tế ảo hóa (Testbed WSL nội bộ chứa mã độc Slowloris). Mục tiêu là nâng Recall của lớp Malicious vốn đang bị rớt thảm hại (từ >99% xuống còn ~21%).

## 2. Các Công Việc Đã Thực Hiện & Kết Quả

### 2.1. Phân tích nguyên nhân & Thử nghiệm Refit Scaler (Exp1)
- **Hành động:** Chạy script `1_refit_scaler_test.py` để kiểm tra việc dùng lại Scaler mới.
- **Phát hiện quan trọng:** Việc chuẩn hóa lại (Re-fit) Scaler trực tiếp trên tập dữ liệu Testbed làm kết quả **tồi tệ hơn** (Accuracy sụt còn 6.87%). Lý do là vì dữ liệu Testbed quá mất cân bằng (Benign cực ít), khiến bộ Scaler ép vùng dữ liệu Malicious về điểm 0 (mean), vô tình trùng với vùng không gian "Benign" mà mô hình đã học.
- **Quyết định:** Bắt buộc giữ nguyên hệ số Scaler gốc của CIC-IDS-2017.

### 2.2. Giai đoạn 1: Fine-tuning & Layer Freezing (Exp2)
- **Hành động:** Code và chạy script `2_finetune_freeze.py`.
- **Kỹ thuật:** 
  - Mix dữ liệu giữa CIC-IDS-2017 và Testbed. Dùng `RandomOverSampler` và hàm mất mát có đánh trọng số (Class Weights) để xử lý chênh lệch lớp.
  - **Layer Freezing:** Đóng băng 77 nút Feature Embedding và 2 khối Attention đầu tiên để "bảo vệ" trí nhớ của AI. Chỉ cho phép mạng học lại ở các lớp cuối.
- **Kết quả:** Đạt thành công xuất sắc.
  - Accuracy: `99.82%`
  - Recall (Malicious): Tăng vọt lên `0.9982`.
  - Không bị hiện tượng Catastrophic Forgetting (Điểm trên tập gốc chỉ giảm `0.55%`).
- **Tác động:** Do đạt chỉ tiêu quá tốt, Giai đoạn 2 (DANN/CORAL) trong Roadmap đã được bỏ qua.

### 2.3. Giai đoạn 3: Feature Engineering & "Phẫu thuật" Mô hình (Exp3)
- **Hành động:** Thiết kế thêm 3 đặc trưng độc lập với phần cứng ảo hóa (`Custom_IAT_CV`, `Custom_Bwd_Pkt_Ratio`, `Custom_Pkt_Size_Ratio`). Cài đặt trong `3_feature_engineering_v2.py`.
- **Kỹ thuật (Model Surgery):** 
  - Vì mô hình gốc chỉ có 77 đầu vào, tiến hành "phẫu thuật" nới rộng thành 80 đầu vào.
  - Copy toàn bộ trọng số của 77 đặc trưng cũ sang cấu trúc mới, chỉ khởi tạo ngẫu nhiên trọng số cho 3 đặc trưng mới.
- **Kết quả (Ablation Study):** Đột phá!
  - Chỉ số MCC (đo lường độ tách bạch trong dữ liệu lệch) tăng từ `0.6825` lên **`0.7333`**.
  - Accuracy đạt **`99.87%`**.

### 2.4. Công cụ Hỗ trợ và Tổng hợp Báo cáo
- Code script `monitor_tasks.sh` để theo dõi tiến trình log Background Terminal theo thời gian thực.
- Code script `4_aggregate_report.py` để quét các file kết quả `.json` và sinh tự động bảng đánh giá.
- Viết file tài liệu `Roadmap_Final_Summary.md` đúc kết lại toàn bộ các phương pháp và bảng số liệu trên để dễ dàng dán vào báo cáo LaTeX.

---

## 3. Các Việc Cần Làm Tiếp Theo (Next Steps)
1. **Thu thập Dữ liệu (Phần việc của Sinh viên):** Tiến hành sinh thêm Traffic Benign (sạch) trên môi trường Testbed WSL để tăng tính thuyết phục cho điểm số Precision. (Giai đoạn 4 của Roadmap).
2. **Viết Đồ án:** Đưa các kỹ thuật "Layer Freezing" và đặc biệt là "Model Surgery" vào quyển Đồ án Tốt nghiệp (các file `.tex`), vì đây là điểm nhấn công nghệ cực kỳ cao.
3. Chạy lại script sinh Báo cáo (`4_aggregate_report.py`) nếu có thêm dữ liệu mới.
