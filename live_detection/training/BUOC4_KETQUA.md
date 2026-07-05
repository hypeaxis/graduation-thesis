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

**FP DoS không phải vấn đề tiền xử lý — mà là thiếu benign thật trong tập train.** Bằng chứng: benign-FP-DoS và DoS-thật tách hoàn hảo (AUROC 1.0) khi model được thấy benign thật. → **PIVOT sang Bước 5 (fine-tune V8.5 + thêm benign thật, giữ nguyên lớp tấn công CIC).** Xử lý mất cân bằng theo Mục 2.3; đánh giá lại trên CIC test để tránh catastrophic forgetting.

Clip[-5,5] tuy không cứu DoS nhưng **vô hại** (giữ 99.8% DoS-thật) và dọn các z-score nổ — có thể gộp vào tiền xử lý của Bước 5 như bước vệ sinh, không phải đòn bẩy chính.
