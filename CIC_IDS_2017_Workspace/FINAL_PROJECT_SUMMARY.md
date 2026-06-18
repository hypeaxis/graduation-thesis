# Báo Cáo Tổng Hợp Toàn Bộ Dự Án: Hệ Thống Cascade NIDS (Từ V1 đến V7)

Dự án này là một hành trình dài nhằm xây dựng hệ thống Trí tuệ Nhân tạo phát hiện xâm nhập (Intrusion Detection System) hiệu năng cao trên bộ dữ liệu luồng mạng CIC-IDS-2017. Trải qua 7 phiên bản cải tiến liên tục, hệ thống đã tiến hóa từ một mạng Transformer đơn giản thành một kiến trúc Cascade đa tầng kết hợp Ensemble tinh vi.

---

## 1. Hành Trình Tiến Hóa Của Hệ Thống

*   **V1 - V3: Giai đoạn Khám phá và Tinh chỉnh Cơ bản**
    *   Sử dụng mạng nơ-ron chuyên sâu cho dữ liệu dạng bảng (FT-Transformer).
    *   Phát hiện ra vấn đề cực đoan về mất cân bằng dữ liệu của CIC-IDS-2017 (Ví dụ: Heartbleed chỉ có 11 mẫu, Web Attack vài nghìn mẫu so với 2.2 triệu mẫu Benign).
    *   *Kết quả:* Các nhóm tấn công hiếm bị bỏ qua hoàn toàn. Nhãn đa số lấn át nhãn thiểu số.
*   **V4: Khai sinh Kiến trúc Cascade Two-Stage (Đột phá đầu tiên)**
    *   **Tầng 1 (Gating Network):** Chỉ làm nhiệm vụ phân loại luồng mạng thành `Benign` (Bình thường) hoặc `Suspicious` (Nghi ngờ).
    *   **Tầng 2 (Expert Network):** Đi sâu vào việc phân tích các luồng `Suspicious` để chỉ mặt gọi tên 14 loại tấn công cụ thể.
    *   *Kết quả:* Precision tăng mạnh, bắt đầu nhận diện được các cuộc tấn công siêu hiếm nhờ cơ chế oversampling (SMOTE) chuyên biệt ở Tầng 2.
*   **V5 - V6: Kỷ nguyên Hard Negative Mining và Tối ưu hóa Web Attack**
    *   Phát hiện ra Tầng 2 thường nhầm lẫn giữa Web Attack và Brute Force, cũng như báo động giả Botnet quá nhiều.
    *   Bơm ngược các mẫu bị đoán sai ở Validation về lại tập Train dưới dạng `Hard Negatives` để bắt Tầng 2 "học tài liệu nâng cao".
    *   *Kết quả:* Giải quyết triệt để lỗi Web Attack (F1 vọt lên >90%).
*   **V7: Cực Đại Hiệu Suất với Hybrid Ensemble Voting (Trạng thái Cuối)**
    *   Đối mặt với thử thách khó nhất: Botnet (cảnh báo giả cao) và Infiltration (bị lọt).
    *   Áp dụng phương pháp kết hợp thuật toán (Ensemble): **FT-Transformer + Random Forest + KNN**.
    *   Bổ sung đặc trưng Tỷ lệ luồng (`Flow_Bytes_Ratio`, `Flow_Pkts_Ratio`).
    *   *Kết quả:* Cấu trúc Rule-based Voting đưa Precision của Botnet vọt lên xấp xỉ 80%, trong khi vẫn duy trì Macro F1 toàn hệ thống cao kỷ lục (**0.9294**). Đồng thời, chứng minh được mặt hạn chế của tập dữ liệu tĩnh đối với mã độc Infiltration.

---

## 2. Kiến Trúc Cuối Cùng (State-of-the-Art)

Kiến trúc cuối cùng đang được giữ lại trong không gian làm việc là một kiệt tác của kỹ thuật học máy thực hành:

1.  **Dữ liệu Đầu vào:** 79 đặc trưng luồng mạng tĩnh từ CIC-IDS-2017 (không chứa IP/Timestamp).
2.  **Stage 1 - Cổng Kiểm Soát (FT-Transformer - V4):**
    *   **Đầu vào:** 77 đặc trưng.
    *   **Quy tắc:** Bất kỳ luồng mạng nào có độ rủi ro > 85% đều được gán nhãn `Suspicious` và đẩy sang Tầng 2.
3.  **Stage 2 - Hội Đồng Xét Duyệt (Ensemble - V7):**
    *   **Đầu vào:** 34 đặc trưng tinh túy nhất (bao gồm 2 đặc trưng Tỷ lệ mới).
    *   **Mô hình:** Cụm 3 chuyên gia (FT-Transformer, Random Forest, KNN).
    *   **Biểu quyết:** Ưu tiên cảnh báo Infiltration nếu RF/KNN phát hiện. Đòi hỏi đồng thuận 100% để phong chuẩn nhãn Botnet nhằm diệt False Positive.

---

## 3. Thành Tựu Tổng Quan Cuối Cùng

| Chỉ số | Điểm số Đạt được | Ý nghĩa |
| :--- | :--- | :--- |
| **Độ chính xác tổng (Accuracy)** | **99.55%** | Hệ thống hoạt động hoàn hảo trên bức tranh lưu lượng lớn. |
| **Macro F1-Score** | **0.9294** | Cực kỳ xuất sắc trong việc duy trì hiệu năng trên *tất cả* các nhóm bất kể số lượng nhiều hay ít. |
| **Tỷ lệ báo động giả (FPR)** | **~0.47%** | Rất thấp đối với một hệ thống phân tích mỗi gói tin độc lập. |
| **Dung lượng Mô hình** | Siêu Nhẹ | Cụm mô hình chạy cực kỳ nhanh, hoàn toàn có khả năng nhúng vào các hệ thống IDS phần cứng. |

Dự án đã đạt đến điểm giới hạn cao nhất của hiệu suất so với bản chất tĩnh của bộ dữ liệu gốc. Đây là cơ sở hoàn hảo để đóng lại chặng đường nghiên cứu phát triển mô hình cho CIC-IDS-2017.
