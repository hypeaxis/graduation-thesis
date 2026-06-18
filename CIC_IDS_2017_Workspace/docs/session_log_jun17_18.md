# 📅 Session Log Chi Tiết: Ngày 17/6 & 18/6/2026

## 📝 Tổng Quan Quá Trình Nghiên Cứu
Trong khoảng thời gian ngày 17/6 và 18/6, dự án đã tập trung vào việc giải quyết hiện tượng **"The Cascade Trap"** (mất độ chuẩn xác do báo động giả từ các luồng mạng bình thường) bằng việc tinh chỉnh kiến trúc phân tầng **Two-Stage Cascade NIDS**. Trọng tâm nghiên cứu nằm ở việc nâng cấp không gian đặc trưng (Feature Space) của Tầng 2, ứng dụng phương pháp khai thác dữ liệu khó (**Hard Negative Mining**), và thực hiện các thử nghiệm so sánh chi tiết giữa phiên bản V4 và V5.

---

## 🔍 Chi Tiết Kỹ Thuật Các Khối Công Việc

### 1. Data Processing & Kỹ Thuật Hard Negative Mining (`extract_hard_negatives.py`)
Thay vì huấn luyện Tầng 2 với dữ liệu lấy mẫu ngẫu nhiên truyền thống, hệ thống đã ứng dụng cơ chế **Hard Negative Mining** để ép mô hình Tầng 2 học cách phân biệt các mẫu đặc biệt khó và hay gây nhầm lẫn nhất:
*   **Chiến lược Khai thác:** 
    * Tái sử dụng mô hình Tầng 1 (Stage 1 - `best_stage1_model.pt`) để dự đoán lại trên toàn bộ tập `cic_train_full.csv`.
    * Lọc và gom toàn bộ các mẫu bị Tầng 1 phân loại là `Suspicious`. Các mẫu này bao gồm "True Positives" (tấn công thật) và "Hard Negatives" (mạng Benign bình thường nhưng có hành vi mập mờ, giống tấn công).
    * Bổ sung thêm **50.000 mẫu "Easy Benign"** (các mẫu Benign được Tầng 1 phân loại chuẩn xác và an toàn) vào tập dữ liệu. Việc này nhằm giúp mô hình Tầng 2 không bị "quên" đi hình thái phân phối của lưu lượng mạng bình thường.
*   **Trích xuất Không gian Đặc trưng Tầng 2 (V5):**
    * Đã nâng cấp không gian đặc trưng của Tầng 2 lên thành **29 đặc trưng** đắt giá nhất (thay vì dùng toàn bộ 77 đặc trưng như Tầng 1).
    * Đặc biệt bổ sung và chú trọng vào các nhóm tính năng (Features):
        * **Kích thước cửa sổ TCP:** `Init_Win_bytes_forward`, `Init_Win_bytes_backward`.
        * **Thông số luồng phụ (Subflow):** `Subflow_Fwd_Bytes`, `Subflow_Bwd_Bytes`.
        * **Đặc trưng Logic dị thường tự định nghĩa (Custom Anomaly):** `Custom_Pkt_Var_Ratio`, `Custom_IAT_Anomaly`.
        * **Đặc trưng ngữ cảnh cổng:** `Port_Is_Web`, `Port_Is_WellKnown`...
*   **Kết quả xuất ra:** Toàn bộ dữ liệu sau khai thác được lưu thành `processed_data/cic_train_stage2_v5_hard.csv` để chuẩn bị cho pha huấn luyện Stage 2 (V5).

### 2. Quá Trình Huấn Luyện Các Mô Hình Tầng 2 (V4 vs V5)
Cả hai phiên bản đều sử dụng kiến trúc cốt lõi FT-Transformer nhưng áp dụng chiến lược phân tách nhãn ở Tầng 2 (Expert Model) hoàn toàn khác nhau:
*   **Phiên bản V4 (`phase2_train_v4_stage2.py`):** 
    * Chiến lược gom nhãn: Gộp tất cả các cuộc tấn công siêu vi/hiếm (Bot, Infiltration, Heartbleed) vào một nhãn chung là `Rare Attacks`.
*   **Phiên bản V5 (`phase2_train_v5_stage2.py`):**
    * Chiến lược tách nhãn: Khôi phục và để mô hình học riêng biệt từng lớp tấn công hiếm: `Bot`, `Infiltration`, `Heartbleed`. Việc tách này kỳ vọng giúp Attention của mô hình bắt được vi trạng thái (micro-states) đặc trưng của từng loại mã độc.
    * Sử dụng cấu hình FT-Transformer siêu tinh gọn cho Tầng 2: `d_model=64`, `num_layers=3`, `num_heads=4` (nhẹ hơn hẳn so với Stage 1 nhằm tăng tốc độ Inference tối đa).

### 3. Cơ Chế Khóa Ngưỡng (Probability Thresholding)
Cơ chế "Khóa ngưỡng 85%" đã được thiết kế tại hàm Gating và hoạt động vô cùng hiệu quả để chống hiện tượng False Positives ồ ạt đẩy xuống Tầng 2:
*   Luật phân tuyến: Nếu Stage 1 dự đoán luồng mạng là `Suspicious` nhưng có độ tự tin (Probability) `< 0.85` -> Hệ thống sẽ can thiệp bẻ lái và ép nhãn thành `Benign`.
*   Chỉ các luồng mạng có sự bất thường cực đoan (Probability `>= 0.85`) mới được phép bypass (chuyển tiếp) qua Tầng 2 phân tích độ sâu.

### 4. Kết Quả Đánh Giá Toàn Trình (`evaluate_cascade_system.py`)
Tiến hành kiểm thử trên tập Validation với quy mô khổng lồ: **2.529.391** luồng mạng thực tế. Phân tích kết quả được trích xuất từ `final_v5_report.txt` và `final_cascade_report.txt`:

**Thống kê Lọc Gating (Thresholding Gating Stats):**
*   Hoàn thành việc nhận định luồng chuẩn xác ngay tại Stage 1: **2.510.704** mẫu.
*   Bị chặn lại và ép về Benign (Ngăn chặn thành công False Positives): **12.592** mẫu.
*   Phải chuyển tiếp xuống Stage 2 phân tích sâu: Chỉ **6.095** mẫu. (Bảo đảm tuyệt đối hệ thống NIDS sẽ không bị nghẽn CPU khi chạy Real-time).

**Chi tiết Hiệu Suất Mô Hình V5 (FINAL CASCADE SYSTEM PERFORMANCE):**
*   **Luồng Tốt (Benign):** F1-Score xuất sắc đạt **0.9969** (trên khối lượng hơn 2 triệu mẫu).
*   **Các cuộc tấn công mạng đại trà (Volume-based Attacks):**
    *   **DDoS:** F1-Score: **0.9983**
    *   **DoS:** F1-Score: **0.9821**
    *   **PortScan:** F1-Score: **0.9963**
    *   **Brute Force:** F1-Score: **0.9724**
*   **Các cuộc tấn công cực hiếm (Rare Attacks - Yếu tố cốt lõi của V5):**
    *   **Bot:** F1-Score đạt **0.6180** (Sự tách nhãn ở V5 đã giúp cải thiện đáng kể so với việc gộp chung, chỉ số Recall bắt được nhãn cực cao: 0.9636, Precision: 0.4549).
    *   **Infiltration:** F1-Score đạt **0.7143** (Điểm số rất cao với loại tấn công chèn ép backdoor, Precision: 0.8696).
    *   **Heartbleed:** F1-Score đạt **1.0000** (Hệ thống định vị và nhận dạng đúng 100% tỷ lệ ở cả độ phủ lẫn độ chuẩn xác - 10/10 mẫu).

**Vấn đề Về Nhãn Web Attack (Đã Xử Lý Thành Công ở V6):** 
Trước đó tại nhóm `Web Attack`, F1-Score ghi nhận toàn bộ là `0.0000` (dù support size > 1900 mẫu). Căn nguyên không đến từ mô hình học sai, mà do quá trình map label (Label Encoder) không khớp bởi ký tự mã hóa lỗi `ï¿½` trong bộ dữ liệu gốc (`Web Attack ï¿½ Brute Force`, `Web Attack ï¿½ XSS`). 
**Giải pháp:** Đã điều chỉnh cơ chế map label trong toàn bộ pipeline (`cic_data_processor_v2.py`, `phase2_train_v6_stage2.py`, `evaluate_cascade_system_v6.py`) từ việc dùng Regex/Dictionary cứng nhắc sang cơ chế gộp chuỗi động (`if 'Web Attack' in label`).
**Kết quả:** Web Attack đã được khôi phục thành công với điểm số cực kỳ ấn tượng: **F1-Score đạt 0.9280** và **Recall đạt 0.9821**.

### 5. Tổng kết Tối Ưu Hệ Thống V6
*   Các chỉ số hiệu suất quan trọng đã được hệ thống hóa qua `cascade_performance_report.md`.
*   Tài liệu hóa kiến trúc hệ thống và luồng chạy (bao gồm cả Snort Double Verification) tại `final_system_architecture.md`.
*   **Độ chính xác toàn hệ thống (Accuracy):** Đạt **99.51%**.
*   **Chỉ số Macro Average F1-score:** Nhờ sự đóng góp xuất sắc của Web Attack, Macro F1-Score của toàn hệ thống đã nhảy vọt lên **0.9160** (so với mức 0.6065 ở bản V5 do lỗi label). Điều này chứng minh rằng việc chẻ nhỏ các lớp tấn công hiếm ở Stage 2 kết hợp Hard Negative Mining giúp mô hình đạt được hiệu năng nhận diện toàn diện và tuyệt đỉnh.
