# BƯỚC 4 — Chẩn đoán go/no-go (kết quả: PIVOT sang Bước 5)

**Ngày:** 05/07/2026 · Script: [`step4_diagnose.py`](step4_diagnose.py) · Log: `step4_diagnose.log`

Trước khi retrain, kiểm 3 giả thuyết của Bước 4 xem có nhắm đúng nguyên nhân FP DoS (lớp FP chủ đạo, 20.8%) không. **Kết quả: KHÔNG — cả 4 kỹ thuật Bước 4 đều lệch mục tiêu; đúng thuốc là Bước 5.**

Bối cảnh: benign_real 50,721 → **10,561 flow bị nhầm thành DoS** (FP); dos_real 38,403 → 8,760 nhận đúng DoS.

## (A) Clip-test — FP có do "nổ z-score" (ngoại suy) không?

Clip feature ĐÃ scale về [-C,C] rồi predict lại các flow DoS-FP:

| Clip | % DoS-FP → Benign |
|---|---|
| [-10,10] | 0.0% |
| [-5,5] | **0.2%** |
| [-3,3] | 0.5% |

→ **Clip gần như vô tác dụng** (tác dụng phụ: giữ 99.8% DoS-thật). Vậy FP DoS **KHÔNG** do nổ z-score / ngoại suy thang đo → **4.1 log-transform, 4.2 robust scale + clip đều không cứu được DoS.** (Các feature nổ z-score ở Bước 1 như Flow_IAT_Min z=64k là có thật, nhưng KHÔNG phải cái đẩy quyết định sang DoS.)

> Lưu ý: `scaler_77` thực chất là **PowerTransformer** (không phải StandardScaler) — đã nén đuôi nặng sẵn, nên robust scaling thêm cũng ít khác biệt. Khớp với clip-test.

## (B) Separability — feature thô có tách được benign-FP-DoS vs DoS-thật không?

RandomForest (CV 4-fold) trên **80 feature thô**:

| | Kết quả |
|---|---|
| **CV-AUROC** | **1.000 ± 0.000** |

→ Hai lớp **tách HOÀN HẢO** trong không gian đặc trưng thô. Top feature tách: `Total_Length_of_Fwd_Packets`, `Fwd_Packet_Length_Max`, `act_data_pkt_fwd`, `Total_Fwd_Packets`, `PSH/ACK_Flag_Count` (importance trải đều, không phải 1 feature rò rỉ).

**Diễn giải mấu chốt:** thông tin để phân biệt benign thật ↔ DoS thật **đã có đủ** trong feature. Model V8.5 vẫn nhầm vì nó học "benign" từ **CIC lab** (vùng đặc trưng khác hẳn benign Internet thật), nên benign thật rơi vào vùng nó tưởng là DoS. RF tách được 1.0 **vì nó được huấn luyện trên benign THẬT**. → Cần cho model **thấy benign thật lúc train** = **Bước 5**, KHÔNG phải đổi tiền xử lý (Bước 4).

## (C) Short-flow — DoS-thật có siêu ngắn như benign-FP không?

Tổng số gói (Fwd+Bwd):

| Nhóm | median | ≤2 gói | ≤3 gói |
|---|---|---|---|
| benign-FP-DoS | **27** | 5.6% | 14.2% |
| DoS-thật | **4** | 26.3% | 43.6% |

→ Ngược với giả định: **benign-FP-DoS KHÔNG ngắn** (median 27 gói), còn **DoS-thật mới ngắn** (44% ≤3 gói). Lọc/route flow ngắn (**4.3**) sẽ **giết recall DoS** mà gần như không đụng benign-FP → **4.3 phản tác dụng, loại.**

---

## Kết luận Bước 4 & quyết định

| Kỹ thuật Bước 4 | Bằng chứng | Verdict |
|---|---|---|
| 4.1 log-transform | clip/robust vô tác dụng (A) | ❌ không cứu DoS |
| 4.2 robust scale + clip | clip[-5,5] chỉ 0.2% (A); scaler đã là PowerTransformer | ❌ không cứu DoS |
| 4.3 lọc flow ngắn | DoS-thật mới ngắn, benign-FP median 27 gói (C) | ❌ phản tác dụng (giết recall DoS) |
| 4.4 bỏ cổng | đã bác bỏ ở Bước 1 (ablation 0%) | ❌ |

**FP DoS không phải vấn đề tiền xử lý — mà là thiếu benign thật trong tập train.** Bằng chứng: benign-FP-DoS và DoS-thật tách hoàn hảo (AUROC 1.0) khi model được thấy benign thật.

---

## Kết quả RETRAIN (negative control — theo yêu cầu kiểm chứng)

Dù chẩn đoán đã dự đoán tiền xử lý không ăn, vẫn retrain thật để có **bằng chứng âm** cho luận văn.

**Cấu hình:** `RobustLogScaler` (log1p 36 feature đuôi nặng → robust median/IQR → clip[-5,5]) thay `HybridFeatureScaler` (PowerTransformer). Fine-tune V8.4 → **v8_6** (30 epoch, early-stop epoch 11, GPU). Code: [`v8_6_train_robust.py`](v8_6_train_robust.py), scaler [`model_defs/robust_log_scaler.py`](../model_defs/robust_log_scaler.py), đánh giá [`step4_eval.py`](step4_eval.py).

**Chất lượng model (CIC val):** Macro-F1 **0.9193** (Benign recall 0.99, DoS recall 0.89) — thấp hơn V8.5 (~0.95) vì fine-tune LR nhỏ chưa thích nghi hết input mới; nhưng trên CIC vẫn tốt (không phải model hỏng).

**FP/TPR trên dữ liệu THẬT (v8_6 vs v8_5):**

| | V8.5 (PowerTransformer) | **V8.6 (robust-log)** | Δ |
|---|---|---|---|
| **FPR benign** | 24.68% | **73.87%** | **+49.19pp** ❌ |
| **DoS-FP** | 20.82% | **38.90%** | **+18.08pp** ❌ |
| WebAttack-FP | 3.67% | 5.44% | +1.77pp |
| DoS TPR | 22.8% | 21.4% | ~ |
| PortScan TPR | 38.6% | 91.0% | +52.4pp (phụ) |
| WebAttack TPR | 89.9% | 84.8% | −5.1pp |

**Kết luận (mạnh hơn dự đoán):** robust-log **không những không cứu FP DoS mà làm FPR tệ hẳn** (24.68% → **73.87%**), DoS-FP gần gấp đôi. Trên CIC val Benign recall 0.99 nhưng benign THẬT bị gắn cờ 73.87% → khoảng cách generalization còn tệ hơn V8.5. Nếu FP do lệch-thang-đo thì robust-scale phải *giúp*; nó làm *hại* → **phủ định dứt khoát giả thuyết tiền xử lý.** (PortScan TPR tăng mạnh là hiệu ứng phụ, không liên quan bài toán FP.)

> Caveat: v8_6 Macro-F1 (0.92) thấp hơn V8.5 (0.95) ~0.03. Nhưng mức FP tăng (+49pp) vượt xa mọi giải thích do chênh 0.03 Macro-F1; hơn nữa Benign recall trên CIC của v8_6 là 0.99 → model KHÔNG dở với benign nói chung, chỉ với benign THẬT → thủ phạm là preprocessing map benign thật vào vùng tấn công, không phải model yếu.

---

## Quyết định cuối Bước 4

Cả **chẩn đoán** (clip 0.2%, AUROC 1.0, benign-FP không ngắn) lẫn **retrain negative control** (FPR 24.68%→73.87%) đều chỉ về một hướng: **FP là vấn đề DỮ LIỆU (thiếu benign thật), không phải tiền xử lý.** → **Bước 5 (fine-tune + thêm benign thật, giữ attack CIC, xử lý mất cân bằng, đánh giá lại CIC test).** Giữ **V8.5 làm model chính** (v8_6 chỉ lưu làm chứng cứ, KHÔNG dùng cho pipeline). Clip[-5,5] vô hại (giữ 99.8% DoS-thật) — có thể giữ như vệ sinh ở Bước 5, không phải đòn bẩy.
