# Ghi chú viết luận — áp dụng cho toàn bộ đồ án

Tài liệu này tổng hợp các quy tắc từ: template gốc SOICT, `chi-dan-agent-viet-do-an.md`, và rà soát ngôn ngữ 6 chương hiện tại. Đây là nguồn tham chiếu duy nhất khi viết hoặc chỉnh sửa bất kỳ phần nào của đồ án.

---

## 1. TỪ NGỮ BỊ CẤM TUYỆT ĐỐI

### 1.1 Từ phóng đại / cảm xúc (template cấm)
- **Không dùng:** tuyệt vời, xuất sắc, cực kỳ, vô cùng, hết sức, rất (khi không cần thiết), ấn tượng, hứa hẹn, đáng lo ngại, đáng kinh ngạc
- **Không dùng ẩn dụ báo chí:** "chiến trường", "cuộc chiến", "kẻ thù"
- **Không dùng văn nói:** mù quáng, bí bách, chôn vùi (trừ khi trích dẫn)

### 1.2 Từ nối khuôn mẫu (chi-dan mục 10 cấm)
- **Không dùng đầu câu/đoạn:** Hơn nữa, Bên cạnh đó, Nhìn chung, Có thể thấy rằng, Điều đáng chú ý là, Đáng chú ý là, Tóm lại, Đầu tiên…Tiếp theo…Cuối cùng
- **Không dùng kết đoạn/kết chương bằng câu rỗng:** "đóng vai trò quan trọng", "là yếu tố then chốt", "mang lại nhiều lợi ích"

### 1.3 Câu tự bình luận về quá trình viết
- **Không viết:** "Trong phần này tôi sẽ trình bày…", "Đây không phải quá trình thử-sai ngẫu nhiên, mà là…", "Như đã đề cập ở trên…" (dùng tiết chế)

---

## 2. QUY TẮC DÙNG "ĐÁNG KỂ" VÀ CÁC TỪ TĂNG CƯỜNG

| Trường hợp | Quy tắc |
|---|---|
| Có con số cụ thể kèm (ví dụ: "tăng 17,3%") | Không cần thêm "đáng kể" — con số đã nói thay |
| Không có con số — nhận định định tính | Được dùng "đáng kể", nhưng cần giải thích cơ sở |
| "rất cao", "rất thấp", "rất tốt" | Thay bằng con số cụ thể hoặc xoá |

---

## 3. QUY TẮC CÂU VÀ ĐOẠN VĂN

- Mỗi đoạn một ý chính. Câu đầu nêu ý, câu sau dẫn chứng hoặc lập luận.
- Câu sau liên kết với câu trước bằng **nội dung**, không phải bằng từ nối sáo.
- Tối ưu câu: khó thêm hoặc bớt dù chỉ một từ mà không làm thay đổi nghĩa.
- Ưu tiên câu ngắn khi có thể. Tránh câu quá dài với nhiều mệnh đề lồng nhau.
- **Không dùng câu hỏi tu từ** trong văn học thuật.
- Không trộn tiếng Anh với tiếng Việt kiểu "ceiling cứng" — dùng "ngưỡng trên" hoặc "giới hạn trên".

---

## 4. SỐ LIỆU VÀ THUẬT NGỮ KỸ THUẬT — PHẢI DÙNG ĐÚNG

### 4.1 Số lớp phân loại
| Bối cảnh | Số đúng | Ghi chú |
|---|---|---|
| CIC-IDS-2017 raw | 15 nhãn | Benign + 14 loại tấn công đặc thù |
| CIC-IDS-2017 sau gộp nhóm | 9 lớp | Benign + 8 nhóm tấn công |
| Expert Network đầu ra | 9 lớp | Benign (trường hợp Gating báo nhầm) + 8 nhóm |
| Testbed V8.5 | 5 lớp | Benign, BruteForce, DoS, PortScan, WebAttack |
| NSL-KDD Stage 2 đầu ra | 5 lớp | Normal, DoS, Probe, R2L, U2R |

**Tại sao 15 → 9:** 4 biến thể DoS gộp thành DoS; FTP-Patator + SSH-Patator → BruteForce; 3 biến thể Web Attack → Web Attack.

**Tại sao 9 → 5 (Testbed):** DDoS cần nhiều máy tấn công; Botnet cần hạ tầng C2 thực; Infiltration cần kịch bản đa bước với máy chủ trung gian bị xâm phạm; Heartbleed chỉ có 10 mẫu trong CIC và cần OpenSSL cũ.

### 4.2 Cấu hình mô hình — PHẢI DÙNG ĐÚNG

**CIC Stage 1 — Gating Network:**
- FT-Transformer: d=128, 4 lớp Attention, 8 đầu, dropout=0.2
- 77 đặc trưng đầu vào, nhị phân (Benign/Suspicious), ngưỡng 85%

**CIC Stage 2 — Expert Network FTT:**
- FT-Transformer: d=64, 3 lớp Attention, 4 đầu, dropout=0.2
- 34 đặc trưng (sau lọc tương quan cao)
- 9 lớp đầu ra

**NSL-KDD Stage 2 — Stacking Ensemble:**
- FT-Transformer: d=128, 8 đầu, 4 lớp, d_ff=512, dropout=0.1, FocalLoss γ=2
- LightGBM: 127 lá, lr=0.05, n_estimators=1000
- Meta-LR: đầu vào 10 chiều (5 xác suất × 2 mô hình)

**CIC Ensemble thành phần:**
- RF: 150 cây, max_depth=25, max_features=20, class_weight=balanced_subsample
- KNN: K=16

### 4.3 Kết quả số liệu — KHÔNG ĐƯỢC THAY ĐỔI

| Mô hình | Metric | Giá trị |
|---|---|---|
| NSL-KDD E2E | Macro F1 | 0.6809 |
| NSL-KDD E2E | Accuracy | 80.09% |
| NSL-KDD Stage 1 | Binary Macro-F1 | 0.84 |
| NSL-KDD Stage 1 | Threshold τ | 0.008481 |
| CIC Two-Stage | Accuracy | 99.55% |
| CIC Two-Stage | Macro F1 | 0.9294 |
| CIC Botnet sau HNM (trước ensemble) | F1 | 0.6512 |
| CIC Botnet cuối | F1 | 0.7344 |
| CIC Infiltration sau HNM | F1 | 0.5903 |
| CIC Infiltration cuối | F1 | 0.7407 |
| Domain: Baseline CIC → Testbed | Accuracy | 21.93%, MCC = -0.015 |
| Domain: exp1 Re-fit Scaler | Accuracy | 6.87% (tệ hơn) |
| Domain: exp2 Layer Freezing | Accuracy | 99.82%, MCC = 0.6825, CF = 0.61% |
| Domain: exp3 Model Surgery | Accuracy | 99.87%, MCC = 0.7333 |
| Testbed V8.5 | Macro F1 | 91.7% |
| Testbed V8.5 BruteForce | P/R/F1 | 83%/90%/86% |

### 4.4 Thuật ngữ nhất quán

| Khái niệm | Cách viết chuẩn trong đồ án |
|---|---|
| Mô hình NSL-KDD tốt nhất | Stacking Ensemble (FT-Transformer + LightGBM → Meta-LR) |
| Stage 1 CIC | Gating Network |
| Stage 2 CIC | Expert Network |
| Phiên bản Testbed cuối | V8.5 (không ghi tên model) |
| Phát hiện bất thường (theo title đề tài) | Anomaly-based detection / phát hiện bất thường hành vi |
| Phân phối đặc trưng khác biệt giữa môi trường | Covariate shift |
| Quên kiến thức cũ khi fine-tune | Catastrophic Forgetting (CF) |

---

## 5. CẤU TRÚC MỖI CHƯƠNG (BẮT BUỘC THEO TEMPLATE)

Mỗi chương **phải có**:
- **Tổng quan đầu chương** (văn bản Normal, không in đậm/nghiêng): liên kết với chương trước, nêu lý do có mặt của chương này, giới thiệu các mục sẽ trình bày.
- **Kết chương** (văn bản Normal, không in đậm/nghiêng): tóm tắt nội dung đã trình bày, kết luận chính, câu nối sang chương tiếp theo.

Kết chương **không được** viết giống Tổng quan. Không dùng gạch đầu dòng trong hai phần này.

---

## 6. CÁC LỖI ĐÃ SỬA — KHÔNG LÀM LẠI

| Lỗi | Đã sửa tại |
|---|---|
| Benign count tab:v85-dataset: 56.600 → **51.994** (đếm trực tiếp từ `Combined_V8_5.csv`; DoS = **19.781**) | Ch3 |
| **0,4787 KHÔNG phải Botnet F1** — đó là *Precision* của Bot ở V6; F1 khi đó đã là **0,6294**. Chuỗi đúng: HNM (nội bộ Tầng 2) 0,5103 → 0,6512; Ensemble (đầu-cuối) 0,6294 → 0,7344 | Ch1, Ch3, Ch4, Ch5, Ch6, tóm tắt |
| **0,3821 không có nguồn.** Infiltration F1 ở V6 **đã là 0,7407** — ensemble không làm thay đổi lớp này | Ch3, Ch5, Ch6 |
| **0,7831 / 0,8817 / 0,9102 / 0,9181 / 0,9247 không có nguồn sơ cấp** — thay bằng chuỗi có báo cáo: V5 0,6065 → V6 0,9160 → V7 0,9294 | Ch5, Phụ lục B |
| Benign CIC: 82,7% → **80,32%**; Infiltration 0,03% → **0,0013%**; tỉ lệ Benign:Infiltration 2.750:1 → **~63.100:1** | Ch3, Ch5 |
| Tổng CIC 2.830.743 → **2.829.385** (sau tiền xử lý) | Ch5 |
| Learning rate tầng mid: 1,5e-5 → **2e-5** (`train_v8_5.log`) | Ch3, Phụ lục B |
| PortScan F1 100% → **99,90%** (499/500) | Ch3, Ch5, Ch6 |
| Tập đánh giá domain adaptation: "5.000 flow" → **4.542 flow**, và đây là đánh giá **nhị phân** với chỉ 7 mẫu Benign | Ch5, Phụ lục B |
| `Custom_Bwd_Pkt_Ratio` = Bwd/**Fwd** (không phải /Total); `Custom_Pkt_Size_Ratio` = **min/max** packet | Phụ lục B |
| 0,6809 **không** đi qua Autoencoder Gate — đó là Stacking phẳng 5 lớp | Ch3, Ch5 |
| PortScan table: RF=8.2%/KNN=8.7% → RF=5.2%/KNN=4.9% | Ch5 |
| CIC FTT Tầng 2: L=3 → L=4 (đây là Tầng 1; Tầng 2 dùng L=3, d=64); `d_ff` 256 → **512** (giá trị mặc định ngầm) | Ch2, Phụ lục B |
| E2E Benign false alarm: "Không có" → mô tả đúng Precision=83% | Ch5 |

> **Quy ước tên gọi đã chốt:** mô hình cuối gọi là **FT-IDS** (không dùng "V8.5" trong phần chính); hai tầng cascade gọi là **Tầng 1 / Tầng 2**; đồ án có **ba** giai đoạn, trong đó Giai đoạn 3 gồm hai phần. Bảng ánh xạ sang định danh nội bộ nằm ở đầu Phụ lục B.

## 7. CÁC LỖI CẦN SỬA — CHƯA THỰC HIỆN

*Rà lại ngày 19/07/2026: các mục 1–10 của danh sách cũ đã hoàn tất — không còn chỗ nào ghi "14 lớp" trong `Chuong/*.tex`, và `Bia.tex` đã điền đủ tên đề tài, sinh viên, GVHD, khoa/trường. Chỉ còn lại một việc:*

| # | Vị trí | Việc còn lại |
|---|---|---|
| 1 | Tất cả chương | Thiếu đoạn Tổng quan đầu chương và Kết chương cuối chương (xem quy tắc ở Mục 5 — hai phần này không được viết giống nhau, không dùng gạch đầu dòng) |

---

## 8. CÁC LỖI NGÔN NGỮ CẦN SỬA (theo thứ tự ưu tiên)

| # | Chương/Dòng | Văn bản hiện tại | Sửa thành |
|---|---|---|---|
| 1 | Ch3/84 | "Hơn nữa, 62% test R2L..." | Xoá "Hơn nữa,"; viết lại câu nối tự nhiên |
| 2 | Ch3/123 | "cực kỳ mất cân bằng" | "mất cân bằng nghiêm trọng" |
| 3 | Ch6/12 | "Đáng chú ý là Botnet F1..." | Xoá "Đáng chú ý là", viết thẳng vào |
| 4 | Ch5/293 | "Kết quả đáng chú ý nhất là BruteForce F1 = 86%" | "BruteForce F1 = 86% (Recall = 90%)..." |
| 5 | Ch1/7 | "Điều đáng lo ngại hơn là thời gian phát hiện..." | "Thời gian phát hiện trung bình kéo dài 204 ngày —" |
| 6 | Ch1/26 | "mở ra hướng cân bằng hứa hẹn" | "mở ra hướng tiếp cận khác:" |
| 7 | Ch1/26 | "phần lớn kết quả ấn tượng này" | "phần lớn kết quả này" |
| 8 | Ch1/7 | "không gian mạng trở thành chiến trường" | "tần suất và mức độ thiệt hại của tấn công mạng tăng liên tục" |
| 9 | Ch1/16 | "hoàn toàn mù quáng trước biến thể mới" | "không phát hiện được biến thể chưa có luật" |
| 10 | Ch2/224 | "đặc biệt mù quáng với các tấn công khai thác hành vi" | "không phát hiện được các tấn công khai thác hành vi" |
| 11 | Ch5/114 | "ceiling cứng không thể vượt qua" | "giới hạn trên không thể vượt qua bằng cải tiến thuật toán đơn thuần" |
| 12 | Ch3/7 | "Đây không phải quá trình thử-sai ngẫu nhiên, mà là chuỗi quyết định có cơ sở" | Xoá câu này |
| 13 | Ch5/108 | "giảm tải đáng kể cho Stage 2" | "giảm tải cho Stage 2" (hoặc thêm con số) |
| 14 | Ch5/130 | "học hiệu quả hơn đáng kể" | Thêm con số so sánh hoặc bỏ "đáng kể" |

---

## 9. QUYẾT ĐỊNH CẤU TRÚC: GIÁNG CẤP DOMAIN ADAPTATION (chốt 2026-06)

Giữ **Testbed Retraining V8.5** làm hệ thống chính. Domain Adaptation (DA) chỉ **"nói tới, không nói sâu"**: xuất hiện như đoạn cầu nối giải thích vì sao phải tái huấn luyện, không còn là một giai đoạn nghiên cứu độc lập.

### 9.1 Nguyên tắc "DA nhẹ"

| Giữ (mức nhẹ) | Bỏ |
|---|---|
| Chẩn đoán covariate shift: CIC 99,55% → **21,93%** trên Testbed (MCC −0,015) | Bảng MCC exp2/exp3 (0,6825 → 0,7333) |
| Re-fit Scaler thất bại → **6,87%** (lý do: không đổi scaler độc lập với mô hình) | Mô tả chi tiết Layer Freezing, Mixed-Domain Batch |
| 1 câu nhắc đã thử fine-tuning sơ bộ nhưng hạn chế dữ liệu (1 loại tấn công, 37 Benign) → chuyển hướng | Catastrophic Forgetting 0,61% |
| Giải thích 3 đặc trưng (IAT_CV, Bwd_Pkt_Ratio, Pkt_Size_Ratio) — vì V8.5 dùng 80 chiều | Mục con riêng cho Model Surgery |

### 9.2 Đóng góp: 5 → 4

Gộp 3 đặc trưng kỹ thuật vào đóng góp về Testbed. Bỏ đóng góp #2 cũ ("Phương pháp thích nghi miền" dạng standalone). Danh sách đóng góp còn **4**.

### 9.3 Đánh số lại giai đoạn: 4 → 3

- **Giai đoạn 1:** NSL-KDD (mô hình nền tảng)
- **Giai đoạn 2:** CIC-IDS-2017 Two-Stage Cascade
- **Giai đoạn 3:** Testbed Retraining V8.5 — mở đầu bằng chẩn đoán covariate shift (gộp phần DA cũ vào đây)

(Giai đoạn 4 cũ → Giai đoạn 3 mới. Giai đoạn 3 DA cũ bị giáng cấp thành đoạn mở đầu.)

### 9.4 Các vị trí phải sửa

| # | Vị trí | Việc cần làm |
|---|---|---|
| 1 | Ch1 dòng 41 | "Giai đoạn 3" (Layer Freezing + Model Surgery) → gộp vào GĐ Testbed, giữ phần chẩn đoán 21,93% |
| 2 | Ch1 dòng 55 | Đóng góp #2 "thích nghi miền" → bỏ; gộp 3 đặc trưng vào đóng góp Testbed |
| 3 | Ch3 mục 3.4 (dòng 188–241) | Rút gọn: giữ 3.4.1 + 3.4.2 làm động cơ; cắt 3.4.3 (Layer Freezing); 3.4.4 → "thiết kế 3 đặc trưng cho V8.5" |
| 4 | Ch5 mục 5.4 (dòng 190–233) | Giữ đoạn 197 + 201 (số liệu thất bại); bỏ bảng kết quả dòng 217–231 |
| 5 | Ch6 dòng 14 và 25 | Bỏ "Domain Adaptation (Giai đoạn 3)" khỏi kết luận chính |
| 6 | Toàn bộ | Đánh số lại 4 giai đoạn → 3 giai đoạn |

### 9.5 Cập nhật cho mục 4.3

Các dòng MCC exp2/exp3 trong bảng 4.3 (0,6825; 0,7333; exp1 6,87% Re-fit; exp2/exp3 Layer Freezing/Model Surgery) **không còn xuất hiện trong narrative luận văn** — chỉ lưu trong ghi chú để tham chiếu lịch sử. Hai số **21,93%** và **6,87%** vẫn dùng làm động cơ.

### 9.6 Bản nháp chuẩn cho mục 5.4 (độ sâu tham chiếu — đã duyệt)

> Mô hình CIC-IDS-2017 đạt Accuracy 99,55% trên tập kiểm tra cùng miền, nhưng khi áp dụng trực tiếp lên 5.000 flow thu thập từ Testbed WSL, Accuracy giảm còn 21,93% và MCC = −0,015 — tệ hơn dự đoán ngẫu nhiên. Nguyên nhân là covariate shift: hạ tầng card mạng ảo Hyper-V và NAT của Windows tạo phân phối đặc trưng CICFlowMeter khác biệt so với switch vật lý Gigabit của môi trường CIC. Thử fit lại PowerTransformer trên dữ liệu Testbed không khắc phục được mà còn làm Accuracy giảm tiếp còn 6,87%, do mô hình đã học biểu diễn nội bộ gắn với khoảng giá trị của scaler cũ. Một thử nghiệm fine-tuning sơ bộ cho thấy có thể phục hồi hiệu năng, nhưng phạm vi giới hạn ở một loại tấn công với 37 mẫu Benign khiến kết quả thiếu độ tin cậy thống kê. Hai quan sát này dẫn tới quyết định thu thập dữ liệu Testbed đa dạng loại tấn công và tái huấn luyện mô hình hoàn toàn trên phân phối đích.
