# Kế hoạch Cải thiện Model — Mục tiêu F1 > 90%

## 1. Chẩn đoán Hiện trạng

### Dữ liệu
| Tập | Vai trò | Tổng mẫu | Labels |
|-----|---------|:--------:|--------|
| **run5** | Train + Validation | 111,426 | Benign (18440), DoS (91645), PortScan (442), Brute Force (628), Web Attack (271) |
| **run6** | Test (KHÔNG ĐƯỢC CHẠM khi tune) | 93,547 | Benign (58868), DoS (28743), PortScan (2633), Brute Force (1449), Web Attack (1854) |

### Model hiện tại: `v4_hybrid_model.pt`
- 80 features, 6 classes encoder: `['Benign', 'Brute Force', 'DDoS', 'DoS', 'PortScan', 'Suspicious']`
- Malicious Recall ~97%, Benign Recall ~22%

---

## 2. Các vấn đề cốt lõi và Cách giải quyết triệt để

### Vấn đề 1: Label Mismatch (Sai lệch nhãn)
**Tình trạng:** Encoder hiện tại chứa `DDoS` và `Suspicious` (không có trong Testbed) nhưng lại **thiếu `Web Attack`** (có 1854 mẫu trong `run6`). Hậu quả là 1854 mẫu này bị vứt bỏ khi đánh giá, làm kết quả F1 bị sai lệch hoàn toàn.
**Cách giải quyết:**
Xây dựng lại bộ `LabelEncoder` mới chỉ chứa đúng 5 class thực tế của Testbed: `['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']`.
- Tác dụng: Mô hình sẽ có lớp đầu ra (Output Layer) là 5 node. 100% dữ liệu Testbed sẽ được mô hình học và đánh giá một cách công bằng. Không còn mẫu nào bị vứt bỏ, giúp F1 phản ánh chính xác thực tế.

### Vấn đề 2: Bias về Attack và Benign FPR cực cao
**Tình trạng:** Model v4 có Benign Recall chỉ ~22% (78% traffic lành tính bị đánh nhầm thành tấn công). Lý do là tập `run5` quá thiên lệch về DoS (~91k DoS vs ~18k Benign). Chỉ dùng Threshold calibration sẽ không đủ sức kéo F1 > 90% (cao nhất chỉ đạt ~87.5%).
**Cách giải quyết:**
Bắt buộc phải tiến hành **Finetune nhẹ (10 epoch)** trên tập `run5` với Combo 3 công cụ sau:
1. **Dùng Focal Loss:** Sử dụng lại code Focal Loss (γ=2.0, α=0.25) từ `phase2_train (1).py`. Focal Loss sẽ tự động giảm trọng số của các mẫu "dễ" (như DoS) và tập trung phạt cực nặng vào các mẫu "khó" (các luồng Benign hay bị nhận diện nhầm).
2. **Bơm Class Weight cho Benign:** Nhân trọng số phạt của class `Benign` lên gấp 3 đến 5 lần trong hàm Loss. Nếu mô hình đoán sai 1 luồng Benign, nó sẽ bị phạt nặng gấp 5 lần so với đoán sai DoS. Mô hình sẽ tự khắc cẩn thận hơn khi kết luận Attack.
3. **Label Smoothing (0.05):** Không cho phép mô hình tự tin 100% (ví dụ output ra `[0, 0, 1.0, 0, 0]`). Bắt mô hình dự đoán ra `[0.01, 0.01, 0.96, 0.01, 0.01]`. Việc này giúp phân phối xác suất mềm mại hơn, làm bước Threshold Calibration sau đó phát huy tác dụng tối đa.

---

## 3. Kế hoạch thực hiện (3 bước)

### Bước 1 — Sửa Encoder + Retrain với Focal Loss (trên run5)

**Mục đích:** Tạo model mới với encoder đúng 5 classes của Testbed, loss function tối ưu.

Tạo script `4c_retrain_focal_v5.py`:
1. Sử dụng **Encoder mới:** 5 classes.
2. Áp dụng **FocalLoss(γ=2.0, α=0.25)**, kết hợp **Class weight cho Benign** (gấp 3-5x) và **Label smoothing = 0.05**.
3. **Model Surgery:** Giữ nguyên kỹ thuật freeze 77 embeddings + 2 transformer blocks đầu.
4. **Base model:** Vẫn dùng `finetuned_stage3c_hybrid.pt` làm khởi điểm (giữ tri thức cũ).
5. **Train 10 epoch** trên run5 (80/20 train/val split, seed=42).
6. **Output:** `models/v5_focal_model.pt` + `models/v5_encoder.pkl`.

### Bước 2 — Threshold Calibration (trên validation split của run5)

**Mục đích:** Tìm ngưỡng tối ưu để cân bằng Recall(Attack) vs FPR.

Tạo script `5d_threshold_calibration.py`:
1. Load model `v5_focal_model.pt` (từ Bước 1).
2. Inference trên **validation split của run5**.
3. Lấy softmax probabilities cho class Benign: `P(Benign)`.
4. Sweep ngưỡng `t` từ 0.50 đến 0.99 (step=0.01):
   - Nếu `P(Benign) ≥ t` → gán Benign.
   - Ngược lại → giữ nguyên multi-class prediction.
5. Tính Macro F1, tìm điểm tối ưu với ràng buộc FPR < 10%.
6. Lưu `optimal_threshold.json`.

**QUAN TRỌNG:** Bước này chạy 100% trên run5. KHÔNG CHẠM run6.

### Bước 3 — Đánh giá chính thức trên Test Set (run6)

**Mục đích:** Lấy con số F1 cuối cùng để báo cáo trong luận văn.

Tạo script `5e_final_evaluation_run6.py`:
1. Load model `v5_focal_model.pt` + `optimal_threshold.json`.
2. Inference trên **toàn bộ run6** (93,547 mẫu, đầy đủ 5 classes).
3. Áp ngưỡng: nếu `P(Benign) ≥ threshold` → Benign, else giữ nguyên.
4. In Classification Report đầy đủ 5 classes và Confusion Matrix.

**Đây là CON SỐ DUY NHẤT được báo cáo.**

## 4. Files sẽ tạo

| File | Mô tả |
|------|--------|
| `Phase3_4_Retrain/src/4c_retrain_focal_v5.py` | [NEW] Retrain với Focal Loss + encoder 5 classes |
| `Phase3_4_Retrain/src/5d_threshold_calibration.py` | [NEW] Sweep ngưỡng trên run5 validation |
| `Phase3_4_Retrain/src/5e_final_evaluation_run6.py` | [NEW] Đánh giá chính thức trên run6 |
| `Phase3_4_Retrain/models/v5_focal_model.pt` | [NEW] Model output |
| `Phase3_4_Retrain/models/v5_encoder.pkl` | [NEW] Encoder 5 classes |
| `Phase3_4_Retrain/models/optimal_threshold.json` | [NEW] Ngưỡng tối ưu |
