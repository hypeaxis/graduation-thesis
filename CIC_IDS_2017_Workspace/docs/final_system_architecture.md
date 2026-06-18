# 🌟 Tổng Quan Hệ Thống Phát Hiện Xâm Nhập (Two-Stage Cascade NIDS V4)

Tài liệu này tổng hợp toàn bộ hiện trạng kiến trúc, phương pháp xử lý dữ liệu, siêu tham số và kết quả của mô hình tốt nhất tính đến thời điểm hiện tại.

---

## 1. Kiến Trúc Hệ Thống Hiện Tại (System Architecture)

Hệ thống được thiết kế theo mô hình **Cascade 2 Tầng (Two-Stage)** nhằm giải quyết bài toán mất cân bằng dữ liệu cực đoan trong an toàn thông tin.

*   **Tầng 1 (Stage 1 - General Model):** Đóng vai trò như một "màng lọc thô". Phân tích toàn bộ lưu lượng mạng bằng tất cả 77 đặc trưng. Nhiệm vụ chính là nhận diện các luồng mạng bình thường (Benign) và các tấn công mạng rõ ràng/có khối lượng lớn (DoS, DDoS, PortScan, Brute Force). Những luồng mạng có dấu hiệu bất thường, mập mờ sẽ được gán nhãn là **`Suspicious`** và đẩy xuống Tầng 2.
*   **Tầng 2 (Stage 2 - Expert Model):** Đóng vai trò là "chuyên gia soi chiếu". Nó chỉ tiếp nhận các luồng mạng bị đánh dấu là `Suspicious` từ Tầng 1. Tại đây, nó sử dụng **27 đặc trưng tinh gọn nhất** tập trung vào độ trễ (IAT), kích thước gói tin (Payload Size), bối cảnh cổng (Port Context), và kích thước cửa sổ TCP (TCP Window) để bóc tách các tấn công siêu tinh vi: **`Web Attack`** và **`Rare Attacks`** (Botnet, Infiltration, Heartbleed).

---

## 2. Lõi Thuật Toán AI (Best Model)

Mô hình tốt nhất được sử dụng trong cả 2 Tầng là **FT-Transformer (Feature Tokenizer + Transformer)**. Đây là một kiến trúc tiên tiến chuyên trị dữ liệu dạng bảng (Tabular Data), vượt trội hơn so với MLP truyền thống nhờ cơ chế Attention. Hệ thống còn áp dụng kỹ thuật **EMA (Exponential Moving Average)** để tạo ra một bản sao trọng số mượt mà, giúp tăng tính tổng quát hóa.

### Kết quả Tốt Nhất (Best Metrics)
*   **Stage 1:**
    *   **F1-Score:** `0.8979`
    *   **G-Mean:** `0.9923` (Cực kỳ xuất sắc trong việc phủ quát nhãn).
*   **Stage 2 (Phiên bản 25 Features - Payload Size):**
    *   **F1-Score:** `0.4780`
    *   **G-Mean:** `0.9583`
    *   *Lưu ý:* Kỹ thuật Hard Negative Mining đẩy G-Mean lên 0.963 nhưng làm F1 giảm nhẹ. Phiên bản 25 Features mang lại sự cân bằng F1-Score tốt nhất.

---

## 3. Quy Trình Xử Lý Dữ Liệu (Data Processing Pipeline)

Toàn bộ quá trình xử lý được tự động hóa tại `cic_data_processor_v2.py`:

1.  **Làm sạch (Data Cleaning):** Xóa các cột chứa Infinity, loại bỏ cột rác (Zero Variance), và xóa bỏ cột gây rò rỉ dữ liệu `Fwd_Header_Length.1`.
2.  **Khai phá Đặc trưng (Feature Engineering):**
    *   Tạo 5 đặc trưng ngữ cảnh Cổng mạng: `Port_Is_Web`, `Port_Is_RemoteAccess`, `Port_Is_WellKnown`, `Port_Is_Registered`, `Port_Is_Ephemeral`.
    *   Tạo 4 đặc trưng logic dị thường: `Custom_Fwd_Pkt_Rate`, `Custom_Slow_Index`, `Custom_Pkt_Var_Ratio`, `Custom_IAT_Anomaly`.
3.  **Lấy mẫu phân tầng (Stratified Sampling):** Giữ lại toàn bộ dữ liệu hiếm, trích xuất ngẫu nhiên khoảng 300,000 mẫu để làm tập Huấn luyện (Train), 2.5 triệu mẫu còn lại làm tập Đánh giá (Validation).
4.  **Tối ưu tốc độ chấm điểm (Val Downsampling):** Rút gọn 20% các nhãn phổ biến trên tập Validation (nhưng giữ nguyên 100% nhãn hiếm) giúp thời gian Validate giảm từ 40 phút xuống còn 2 phút.
5.  **Cân bằng tập Huấn luyện (SMOTE-ENN):** Sử dụng thuật toán SMOTE để sinh thêm dữ liệu và ENN để xóa bỏ nhiễu, đảm bảo mỗi nhãn trong lúc Train có tối thiểu `30,000` mẫu.
6.  **Chuẩn hóa (Scaling):** Sử dụng `PowerTransformer (Yeo-Johnson)` để đưa phân phối dữ liệu về gần với dạng phân phối chuẩn Gaussian, giúp Transformer học tốt hơn.

---

## 4. Các Thông Số Tới Thời Điểm Hiện Tại (Hyperparameters)

| Thông số | Stage 1 | Stage 2 |
| :--- | :--- | :--- |
| **Số lượng Đặc trưng (Features)** | 77 | 27 (+ TCP Window) |
| **Chiều nhúng (d_model)** | 128 | 64 |
| **Số tầng Attention (num_layers)**| 4 | 3 |
| **Số lượng đầu (num_heads)** | 8 | 4 |
| **Dropout / Drop Path Rate** | 0.2 / 0.1 | 0.2 / 0.1 |
| **Batch Size** | 256 | 256 |
| **Số Epochs** | 15 | 25 |
| **Learning Rate (AdamW)** | 1e-4 | 1e-4 |
| **Weight Decay** | 1e-4 | 1e-4 |
| **Learning Rate Scheduler** | Cosine Annealing Warmup (3 epochs) | Cosine Annealing Warmup (3 epochs) |
| **Hàm mất mát (Loss Function)** | Focal Loss (Gamma=2.0) + Label Smoothing (0.05) | Focal Loss (Gamma=2.0) + Label Smoothing (0.05) |
| **Trọng số lớp (Class Weights)** | Tự động cân bằng, nhân 3 (`x3`) cho nhóm `Suspicious` | Hard Negative Mining + Class Weights |
| **Chế độ tính toán** | AMP (Tăng tốc xử lý dấu phẩy động) | AMP |

## 5. Cơ chế Khóa Ngưỡng Chuyển Tầng (Probability Thresholding)

*   **Ngưỡng (Threshold):** `85%`
*   **Quy tắc:** Khi Stage 1 dự đoán là `Suspicious`, nó phải tính toán xác suất. Nếu xác suất `>= 85%`, nó mới được chuyển cho Stage 2 xử lý. Nếu `< 85%`, luồng bị ép gán thành `Benign`. Kỹ thuật này triệt tiêu hoàn toàn làn sóng False Positive (báo động giả) của hệ thống.

---

## 6. Kiến Trúc Phòng Thủ Chiều Sâu (Defense-in-depth): Tích hợp AI và Snort

Trong thực tế quản trị hệ thống thông tin, hệ thống AI không đứng đơn độc mà hoạt động như một lớp lọc thông minh, kết hợp cùng các công cụ bảo mật tiêu chuẩn (như Snort, Suricata) để tối đa hóa độ tin cậy.

*   **Xử lý nhãn Botnet:** AI đặc biệt giỏi trong việc phát hiện sự bất thường về nhịp độ kết nối (Anomaly IAT Variance). Khi Tầng 2 dự đoán một luồng mạng là `Bot`, để xác nhận 100% đó là mã độc (ví dụ Ares Botnet) mà không báo động giả, quy trình chuẩn yêu cầu AI đẩy cảnh báo này sang **Snort**.
*   **Quy trình Xác nhận kép (Double Verification):** Snort sẽ lập tức đối chiếu địa chỉ IP hoặc nội dung bản tin DNS của luồng bị tình nghi với các danh sách đen (Blacklist) đã biết. 
*   Sự kết hợp giữa **phát hiện hành vi dị thường (AI)** và **xác thực bằng chữ ký/luật tĩnh (Snort)** giúp loại bỏ hoàn toàn các luồng Benign chạy ngầm có nhịp điệu tương đồng (như NTP sync, Windows Update), đảm bảo tỷ lệ False Positive của Botnet tiệm cận 0.
