# BƯỚC 1 — Kết quả chẩn đoán covariate shift

**Ngày:** 04/07/2026 · **Không cần retrain.** · Script: [`step1_diagnose.py`](step1_diagnose.py) + [`step1_ablation_extra.py`](step1_ablation_extra.py)
**Artifacts:** [`step1_out/`](step1_out/) (KS ranking, z-score, SHAP, ablation, PNG, `step1_summary.json`).

Mục tiêu (theo playbook Mục 4·Bước 1): biến "domain shift" mơ hồ thành **danh sách feature thủ phạm cụ thể**. Tiêu chí Done: xác định **3–5 feature lệch mạnh nhất** VÀ **3–5 feature đóng góp nhiều nhất cho FP**.

---

## 0. Dữ liệu & phương pháp

| | Nguồn | Số flow | Không gian |
|---|---|---|---|
| **benign_lab** | `Label==Benign` trong tập train `Combined_V8_5.csv` (CIC-IDS-2017) → copy ra `data/analysis/benign_lab.csv` | 51,994 | 80 feature (đã tính sẵn) |
| **benign_real** | `data/analysis/benign_real.csv` (CICFlowMeter thô) → qua **đúng** `FeatureExtractor` của pipeline live | 50,721 | 80 feature |

Parity xác nhận: cả hai 80 feature, **0 NaN / 0 inf**. So sánh trong cùng không gian model thấy lúc suy luận live.

Bốn góc nhìn độc lập, phải **hội tụ** thì kết luận mới chắc:
1. **KS-test** (`ks_2samp`) từng feature → phân bố lệch ở đâu (nguyên nhân *dữ liệu*).
2. **Z-score sau `HybridFeatureScaler`** → feature nào bị đẩy ra vùng ngoại suy (cơ chế *overconfidence*).
3. **SHAP** (`GradientExplainer`) trên **chính flow FP** → feature nào *đẩy quyết định sang lớp tấn công*.
4. **Ablation counterfactual** → ép feature về `median(lab)`, đo **% FP quay lại Benign** (kiểm nhân quả).

---

## 1. Đo lại baseline FP trên 50k benign thật (quan trọng: sửa lại con số cũ)

> Tài liệu cũ ghi "~52% FP" — nhưng đó là ước lượng trên **56 flow** (không tin được). Đo lại trên **50,721 flow**:

| Chỉ số | Giá trị |
|---|---|
| **FPR** | **24.68%** |
| Benign Recall | 75.32% |
| Confidence FP (mean / median) | 0.783 / **0.860** → overconfident |

**FP phân rã theo lớp bị gán nhầm:**

| Lớp nhầm | Số flow | % tổng benign | conf trung bình |
|---|---|---|---|
| **DoS** | 10,561 | **20.82%** | **0.823** |
| Web Attack | 1,863 | 3.67% | 0.575 |
| PortScan | 95 | 0.19% | 0.385 |
| Brute Force | 1 | 0.00% | — |

→ **Vấn đề FP gần như hoàn toàn là DoS với confidence cao (0.82).** Đây là mục tiêu chính của Bước 2 (nâng ngưỡng DoS) và Bước 4.

---

## 2. KS-test — phân bố lệch mạnh nhất (nguyên nhân dữ liệu)

| # | Feature | KS-stat | median lab → real | Diễn giải |
|---|---|---|---|---|
| 1 | **Bwd_IAT_Min** | 0.81 | 253 → 0 | flow real siêu ngắn, gói về gần như tức thời |
| 2 | **Custom_Bwd_Pkt_Ratio** | 0.63 | 0.80 → 1.0 | real cân bằng fwd/bwd hơn |
| 3 | **Custom_IAT_Anomaly** | 0.54 | 2.24 → 22.0 | real cao gấp ~10× |
| 4 | **Down_Up_Ratio** | 0.54 | 0 → 1.0 | **lệch phân loại rõ** (xem histogram) |
| 5 | **FIN_Flag_Count** | 0.52 | 2 → 1 | flag pattern khác |
| … | Fwd/Bwd_IAT_*, Total_Fwd/Bwd_Packets, header lengths | 0.43 | đều nhỏ hơn ở real | **flow real ít gói + IAT nhỏ hơn hẳn lab** |

**Chủ đề xuyên suốt:** traffic Internet thật = **flow rất ngắn** (ít gói, IAT nhỏ) so với flow lab CIC-IDS-2017. Histogram overlay ([`step1_hist_overlay.png`](step1_out/step1_hist_overlay.png)) cho thấy đuôi nặng của IAT ở lab biến mất ở real; `Down_Up_Ratio` và `FIN_Flag_Count` lệch hẳn mode.

---

## 3. Z-score sau scaler — cơ chế "ngoại suy quá tự tin"

Sau khi scale bằng thống kê **lab**, một số feature real rơi ra vùng z-score cực lớn (model chưa từng thấy → đoán bừa tự tin):

| Feature | % flow real \|z\|>5 | real max \|z\| | lab max \|z\| | Ghi chú |
|---|---|---|---|---|
| **Custom_Pkt_Size_Ratio** | 13.78% | 6.60 | **0.15** | custom feature: lab bó chặt, real nổ hẳn |
| **Flow_IAT_Min** | 0.18% | **64,717** | 2.63 | outlier scale thảm khốc |
| **Flow_Bytes_s** | 0.01% | 15.41 | 0.05 | rate feature nổ (cơ chế #2: chia ~0) |
| **FIN_Flag_Count** | 59.90% | 5.84 | 5.84 | 60% flow real ở rìa |
| **RST_Flag_Count** | 37.36% | 73.56 | 73.56 | flag pattern lệch |
| Custom_IAT_CV | 0.07% | 9.09 | 7.02 | |

→ Xác nhận **cơ chế #1** (lệch thang đo → z-score nổ) và **#2** (flow siêu ngắn → rate bùng nổ). Đặc biệt `Custom_Pkt_Size_Ratio` và `Flow_IAT_Min` là ứng viên số 1 cho **robust scaling + clipping (Bước 4.2)**.

---

## 4. SHAP trên flow FP — feature đẩy quyết định sang lớp tấn công

Giải thích 300 flow FP (nền 100 benign), lấy attribution theo **đúng lớp tấn công model gán** ([`step1_shap_fp.png`](step1_out/step1_shap_fp.png)):

| # | Feature | mean\|SHAP\| | hướng | Diễn giải |
|---|---|---|---|---|
| 1 | **Port_Is_Web** | 0.83 | **+ (đẩy sang tấn công)** | **feature cổng → nghi leakage/spurious (cơ chế #4)** |
| 2 | **min_seg_size_forward** | 0.70 | + | kích thước segment nhỏ |
| 3 | Fwd_Packet_Length_Max | 0.46 | + | |
| 4 | Avg_Bwd_Segment_Size | 0.40 | + | |
| 5 | **RST_Flag_Count** | 0.36 | + | trùng với z-score |
| 6 | Total_Length_of_Fwd_Packets | 0.32 | + | |

**Phát hiện then chốt:** `Port_Is_Web` là yếu tố **#1** đẩy benign→tấn công. Đúng như cơ chế #4 dự đoán: traffic web (80/443) → `Port_Is_Web=1` → model học tương quan giả "web = tấn công" (vì trong CIC-IDS-2017 các đợt Web Attack đi qua cổng 80). → **Bằng chứng mạnh cho Bước 4.4 (bỏ feature cổng rò rỉ).**

---

## 5. Ablation counterfactual — kiểm nhân quả

**5a. Đơn lẻ (từ nghi phạm KS/z-score)** — ép về median lab, % FP về Benign:

| Feature | % FP hồi phục |
|---|---|
| **Down_Up_Ratio** | **11.88%** |
| RST_Flag_Count | 2.10% |
| Fwd_IAT_Mean | 1.37% |
| Bwd_IAT_Min | 1.12% |
| Custom_Bwd_Pkt_Ratio | 0.92% |

**5b. Nhắm nhóm SHAP + reset theo NHÓM** (`step1_ablation_extra.py`):

> ⏳ **CHƯA CHẠY XONG — chạy tiếp sau.** Script đã sẵn sàng (đã giới hạn `torch.set_num_threads(4)`
> + lấy mẫu `FP_SAMPLE=4000` để tránh treo CPU). Base predict đã xác nhận **FP 12,520 / 24.68%**
> (khớp script chính). Còn lại 14 lượt ablation nhóm — chạy:
> ```
> python training/step1_ablation_extra.py     # từ live_detection/
> ```
> Sẽ đo: `Port_Is_Web` đơn lẻ (kiểm chứng SHAP #1), nhóm `Port_Is_*` (5 cổng), nhóm `SHAP-top6`,
> và `SHAP-top6 + Down_Up_Ratio` → % FP hồi phục. Kết quả ghi `step1_out/step1_ablation_extra.csv`,
> điền bảng vào đây.

→ Không có 1 feature "viên đạn bạc" đơn lẻ — FP là **shift đồng thời của cả cụm**. Điều này ủng hộ hướng **calibrate (Bước 2) + robust scaling toàn cục (Bước 4.2)** thay vì chỉ vá 1 feature; đồng thời `Port_Is_Web`/nhóm cổng là mục tiêu **bỏ leakage (Bước 4.4)**.

---

## 6. Kết luận Bước 1 (đạt tiêu chí Done)

**3–5 feature LỆCH phân bố mạnh nhất (KS):**
`Bwd_IAT_Min` · `Custom_Bwd_Pkt_Ratio` · `Custom_IAT_Anomaly` · `Down_Up_Ratio` · `FIN_Flag_Count`

**3–5 feature ĐẨY FP sang tấn công mạnh nhất (SHAP):**
`Port_Is_Web` · `min_seg_size_forward` · `Fwd_Packet_Length_Max` · `Avg_Bwd_Segment_Size` · `RST_Flag_Count`

**Feature CỐT LÕI (xuất hiện ≥2/3 bảng top-10 KS/z-score/SHAP):**
`Total_Length_of_Fwd_Packets` · `Fwd_IAT_Mean` · `FIN_Flag_Count` · `RST_Flag_Count`

### Ánh xạ sang cơ chế & bước sửa tiếp theo

| Cơ chế (Mục 1 playbook) | Bằng chứng Bước 1 | Bước sửa |
|---|---|---|
| #1 lệch thang đo → z-score nổ | Custom_Pkt_Size_Ratio, Flow_IAT_Min, Flow_Bytes_s | **4.2** robust scale + clip |
| #2 flow siêu ngắn → rate bùng nổ | KS: IAT/packet-count đều nhỏ; Flow_Bytes_s nổ | **4.3** lọc/đánh dấu flow ngắn |
| #4 feature cổng rò rỉ | **SHAP: Port_Is_Web #1** | **4.4** bỏ Port_Is_* rò rỉ |
| overconfidence (0.82 DoS) | conf FP median 0.86 | **2** temperature + ngưỡng/lớp DoS |

**Khuyến nghị thứ tự:** Bước 2 (calibrate — quick win, đánh trực tiếp DoS conf 0.82) → Bước 4.4 (bỏ Port_Is_Web leakage) → Bước 4.2 (robust scale cho Custom_Pkt_Size_Ratio/Flow_IAT_Min).
