# BƯỚC 2 — Kết quả hiệu chỉnh quyết định (calibrate)

**Ngày:** 05/07/2026 · **Không retrain.** · Script: [`step2_calibrate.py`](step2_calibrate.py) + [`step2b_overlap.py`](step2b_overlap.py)
**Artifacts:** [`step2_out/`](step2_out/) (reliability png, summary, overlap log) · tham số lưu ở [`models/v8_5_calibration.json`](../models/v8_5_calibration.json)

Mục tiêu (playbook Mục 4·Bước 2): chữa overconfidence để ngưỡng lọc có tác dụng. Tiêu chí Done: reliability gần đường chéo + **FPR giảm** mà **TPR tấn công không tụt**.

> ⚠️ **Lưu ý phương pháp:** temperature scaling chia logits cho 1 hằng số → **đơn điệu, KHÔNG đổi argmax và thứ hạng confidence** → **tự nó không giảm FP**. Nó chỉ hiệu chỉnh thang đo (ECE). Đòn bẩy giảm FP là **ngưỡng-theo-lớp** (2.2), và chỉ hiệu quả nếu confidence tách được benign-FP khỏi tấn-công-thật.

---

## 1. Thiết lập

- **Fit (calib):** `benign_val` (12,680, giữ riêng từ Bước 0) + **30% mỗi lớp tấn công thật** (holdout).
- **Eval (before/after):** `benign_real` (50,721) + **70% tấn công còn lại**. Tách fit/eval sạch.
- Model xuất **logits thô** (`FTTransformer.forward`) → calibrate = `softmax(logits/T)`.

## 2.1 Temperature scaling

| | ECE calib | ECE eval |
|---|---|---|
| before (T=1) | 0.244 | 0.213 |
| **after (T\*=1.481)** | 0.191 | **0.154** |

→ Calibration **cải thiện ~28%** (reliability diagram [`step2_reliability.png`](step2_out/step2_reliability.png) kéo gần đường chéo hơn). Nhưng đường cong vẫn "gãy" ở vùng conf 0.5–0.75 (accuracy thấp) — dấu hiệu **miscalibration phi tuyến** mà 1 tham số T không sửa hết. Vẫn nên giữ T (đúng hơn, vô hại).

## 2.2 Ngưỡng theo từng lớp (giữ ≥95% recall)

Ngưỡng = phân vị 5% của confidence (đã cal) các flow tấn công thật được dự đoán đúng lớp đó:

| Lớp | Ngưỡng | Ghi chú |
|---|---|---|
| PortScan | 0.319 | thấp — dựa thêm `PortScanRule` |
| **DoS** | **0.309** | rất thấp → **DoS thật bị phát hiện với conf THẤP** (dấu hiệu xấu) |
| Brute Force | 0.588 | |
| Web Attack | 0.534 | |

## 3. Đánh giá before/after (EVAL)

| Cấu hình | FPR benign | PortScan | DoS | Brute Force | Web Attack | macro-TPR |
|---|---|---|---|---|---|---|
| RAW (T=1, không ngưỡng) | 24.68% | 40.2% | 23.5% | 99.7% | 90.4% | 63.5% |
| BEFORE (global 0.6 hiện hành) | 20.20% | **0.0%** ⚠️ | 21.0% | 98.9% | 87.0% | 51.7% |
| **AFTER (T=1.48, per-class)** | **21.86%** | **36.5%** | 21.7% | 95.0% | 86.0% | **59.8%** |

**Đọc bảng:**
- Ngưỡng chung **0.6 hiện hành là con dao cùn**: giảm FPR nhưng **giết sạch phát hiện PortScan (→0%)** vì PortScan có conf thấp. Per-class **sửa lỗi này** (0%→36.5%) và giữ macro-TPR cao hơn (59.5 vs 51.7).
- FPR AFTER (21.86%) chỉ giảm ~2.8pp so RAW — **toàn bộ mức giảm đến từ Web Attack**, DoS gần như không đổi.
- ⚠️ Lưu ý: AFTER (21.86%) còn **cao hơn** BEFORE-global-0.6 (20.20%) trên riêng FPR, vì ngưỡng DoS per-class (0.31) thả lỏng hơn 0.6. Per-class **không thắng global-0.6 ở con số FPR đơn thuần** — nó thắng ở chỗ **không giết PortScan** + calibrate đúng. Nhìn 1 mình FPR sẽ hiểu lầm.

## 4. Vì sao FPR không giảm mạnh: phân tích tách được/không (AUROC)

So confidence (đã cal) của **benign-nhầm-c** vs **c-thật** (cùng dự đoán = c):

| Lớp | benign-FP conf (median) | c-thật conf (median) | **AUROC** | Tách được? |
|---|---|---|---|---|
| **DoS** | 0.710 | 0.769 | **0.664** | ❌ **KHÔNG** — trùng nặng |
| **Web Attack** | 0.422 | 0.754 | **0.951** | ✅ **CÓ** — tách sạch |

Tradeoff ngưỡng:

| Ngưỡng | DoS: benign-FP còn / DoS-thật giữ | Web Attack: benign-FP còn / WA-thật giữ |
|---|---|---|
| 0.5 | 87.7% / 91.0% | 38.2% / 96.2% |
| 0.7 | 53.4% / **79.5%** | **8.4%** / 89.1% |

→ **DoS:** muốn bỏ nửa benign-FP (thr 0.7) thì **mất 20% recall DoS** — mà recall DoS vốn đã chỉ ~23%. Confidence gần như **vô dụng** để lọc DoS (AUROC 0.66). Nguyên nhân: benign thật (flow web ngắn) khiến model "thấy giống DoS" với độ tin gần bằng DoS thật — đây là **covariate shift trong không gian đặc trưng**, KHÔNG phải lỗi calibration.
→ **Web Attack:** ngưỡng 0.7 bỏ **92% benign-FP** mà vẫn giữ **89% recall** → **thắng thật sự**.

---

## 5. Kết luận Bước 2

| Hạng mục | Kết quả |
|---|---|
| Temperature T=1.48 | ✅ ECE 0.21→0.15 — giữ lại (calibration hygiene) |
| Sửa lỗi ngưỡng chung 0.6 giết PortScan | ✅ per-class khôi phục PortScan 0%→36.5% |
| **Web Attack FP** | ✅ **lọc được** (AUROC 0.95): thr ~0.6–0.7 bỏ ~70–92% FP, giữ ~89–96% recall |
| **DoS FP (chủ đạo 20.8%)** | ❌ **KHÔNG lọc được bằng calibration** (AUROC 0.66) → **BẮT BUỘC Bước 4** |
| FPR tổng | 24.68% → ~21.8% (chỉ giảm phần Web Attack) |

**Thông điệp cho luận văn:** Bước 2 chứng minh **overconfidence không chỉ là miscalibration** — với DoS, benign-FP tự tin **ngang** tấn công thật (AUROC 0.66), nên không hậu-xử-lý nào (temperature/ngưỡng) cứu được. Đây là **bằng chứng định lượng** cho luận điểm: cần can thiệp **không gian đặc trưng** (Bước 4: robust scale + lọc flow ngắn + xử lý cụm hình-dạng-flow đã xác định ở Bước 1) mới hạ được FP DoS. Web Attack thì hậu-xử-lý là đủ.

**Tham số đã lưu** (`models/v8_5_calibration.json`): `T=1.481`, ngưỡng per-class.

### Quyết định (05/07/2026): CHƯA wire vào pipeline — làm Bước 4 trước

Vì calibration không cứu được DoS FP (đòn bẩy chính), wiring bây giờ chỉ chỉnh được Web Attack + PortScan mà để hành vi live ở trạng thái dở dang. **Chọn giữ nguyên pipeline hiện tại**, chuyển sang **Bước 4** (tiền xử lý chống lệch-thang-đo: 4.2 robust scale + clip, 4.3 lọc flow ngắn — nhắm đúng cụm hình-dạng-flow đã xác định ở Bước 1). Sau khi Bước 4 hạ được DoS FP, sẽ **wire calibrate + ngưỡng-theo-lớp một lần** cho cả DoS lẫn Web Attack (tham số T + threshold đã sẵn ở `calibration.json`, chỉ cần fit lại sau retrain).

---

## 6. Rà soát độ tin cậy (self-review 05/07/2026)

Hai vấn đề phát hiện khi rà soát, đều **không làm đổi kết luận**:

1. **[ĐÃ SỬA] Bug tách calib/eval.** Bản đầu gọi `rng.permutation()` lại ở Mục 2.2 trong khi state `rng` đã tiến → 30% chọn ngưỡng khác 30% calib, ~70% rơi vào eval (rò rỉ nhẹ). Đã sửa (dùng lại đúng calib split) và **chạy lại**: ngưỡng gần như y hệt (Web Attack 0.557→0.534, còn lại đổi ≤0.001; AFTER FPR 21.77→21.86%). Quantile ổn định nên tác động không đáng kể; **kết luận DoS-không-lọc-được không hề dựa vào split này** (AUROC ở `step2b` tính trên toàn bộ dữ liệu).
2. **[CAVEAT] T fit trên tập calib nặng tấn công.** Calib chỉ 24% benign (12,680 / 53,380) trong khi triển khai thật ~99% benign → T=1.48 tối ưu cho prior lệch. Vì T đơn điệu (không đổi quyết định) và ta hoãn wiring, ảnh hưởng nhỏ; **khi wire sau Bước 4 nên fit lại T trên tập đại diện triển khai** (hoặc benign-only) và kiểm ECE lại.

**Kết luận rà soát:** claim cốt lõi (DoS FP không chữa được bằng post-hoc calibration, AUROC 0.66; Web Attack chữa được, AUROC 0.95) **vững** — độc lập với cả 2 vấn đề trên. Con số ngưỡng sẽ được tái tạo sạch khi wire (sau retrain).
