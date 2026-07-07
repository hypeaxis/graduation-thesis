# KẾ HOẠCH — Kiểm toán công thức/lý thuyết + Khôi phục PortScan cho LIVE thật

**Ngày lập:** 08/07/2026 · **Trạng thái:** kế hoạch (CHƯA đụng code) · **Nhánh:** `feat/live-work`

## 0. Động cơ (vì sao có kế hoạch này)

Trong lúc rà Bước 5, phát hiện **lỗ hổng cấu trúc** khiến chỉ số replay-based đẹp nhưng về live thật sẽ tụt — đúng lo ngại của user:

1. **PortScanRule chỉ chạy cho IP kẻ tấn công đã biết trước.**
   - [`server.py:35`](server.py) dựng rule bằng `PortScanRule(settings.attacker_ip, …)`.
   - [`postprocess.py:60`](../ids_replay/postprocess.py) override chỉ khi `src[i] == self.scanner_ip`.
   - [`corpus.py:78,84`](../ids_replay/corpus.py) ground-truth khi đánh giá cũng scope theo `src == attacker_ip`.
   - ⇒ Con số **"PortScanRule bắt 100%"** (commit 8156e98) đo trong replay **đã biết IP tấn công**. Live thật (IP lạ): rule **không kích hoạt** → nếu nhận v8_7, PortScan = **0% thật** (classifier 0% + rule câm).

2. **`port_spread` dùng bucket cố định, không phải cửa sổ trượt.**
   - [`features.py:73`](../ids_replay/features.py): `bucket = ts // window_ms` → bucket 2s cố định. Scan vắt qua ranh bucket bị đếm thiếu cổng; scan chậm (<15 cổng/2s) vô hình.

3. **Các Custom feature nằm trong nhóm covariate shift** (Bước 1) và epsilon xử lý không nhất quán (`.replace(0,1)` vs `+1e-6`) → cần kiểm toán lại.

**Quyết định user (08/07):** hướng khôi phục PortScan = **CẢ HAI** (rule IP-agnostic làm lớp chính + giữ tín hiệu classifier làm backup). Phạm vi lần này = **chỉ lập kế hoạch**.

**Nguyên tắc bất di bất dịch:**
- KHÔNG đổi `replay_config.json` sang v8_7 cho tới khi Pha 3 đạt Go.
- V8.5 giữ nguyên để rollback. Mọi thay đổi model tạo checkpoint MỚI (không ghi đè v8_7).
- Ràng buộc Mục 0: chỉ sửa trong `live_detection/`.
- Tiền xử lý giữ `HybridFeatureScaler` (Bước 4 đã chứng minh đổi scaler có hại).

---

## PHA 1 — Kiểm toán toàn bộ công thức/lý thuyết

**Mục tiêu:** một bảng inventory duy nhất, mỗi công thức kèm: định nghĩa, đơn vị, rủi ro chia-0/nổ, có nằm trong nhóm shift Bước 1 không, kết luận (giữ/sửa/ghi chú luận văn).

**Việc cụ thể (chỉ đọc + viết báo cáo, không sửa code ở Pha 1):**

| # | Công thức / lý thuyết | Vị trí | Điểm cần kiểm |
|---|---|---|---|
| F1 | `Custom_Fwd_Pkt_Rate = Total_Fwd / (Flow_Duration/1e6)` | [features.py:34](../ids_replay/features.py) | đơn vị (gói/giây), `Flow_Duration.replace(0,1)` → flow 0µs thành 1µs (nổ rate) |
| F2 | `Custom_Slow_Index = Flow_Duration / Flow_IAT_Max` | features.py:35 | `.replace(0,1)`; ý nghĩa vật lý khi 1 gói |
| F3 | `Custom_Pkt_Var_Ratio = Pkt_Len_Var / Avg_Pkt_Size` | features.py:36 | cả tử+mẫu `.replace(0,1)` — méo khi giá trị thật <1 |
| F4 | `Custom_IAT_Anomaly = Flow_IAT_Max / Fwd_IAT_Std` | features.py:38 | **shift Bước 1**; `Std=0` (1 gói fwd) → =Flow_IAT_Max (nổ) |
| F5 | `Custom_IAT_CV = Flow_IAT_Std / (Flow_IAT_Mean+1e-6)` | features.py:40 | epsilon `+1e-6` khác kiểu F1-F4 |
| F6 | `Custom_Bwd_Pkt_Ratio = Total_Bwd / (Total_Fwd+1e-6)` | features.py:42 | **shift Bước 1** |
| F7 | `Custom_Pkt_Size_Ratio = Min_Pkt_Len / (Max_Pkt_Len+1e-6)` | features.py:44 | **shift Bước 1** |
| P1 | 5 Port one-hot (Web/RemoteAccess/WellKnown/Registered/Ephemeral) | features.py:28-32 | Bước 1 đã BÁC leakage Port_Is_Web (ablation 0%) — ghi rõ vào luận văn |
| R1 | `port_spread` (Phương án D1) | features.py:69-77 | bucket cố định vs sliding; định nghĩa "cổng duy nhất/nguồn/cửa sổ" |
| R2 | `ConfidenceThresholdRule` T=0.6 (Phương án A) | postprocess.py:24-38 | ngưỡng global vs per-class (Bước 2 nói global-0.6 giết PortScan) |
| C1 | Temperature scaling T=1.481 + ngưỡng/lớp (Bước 2) | [models/v8_5_calibration.json](../models/v8_5_calibration.json) | công thức `softmax(logits/T)`; ECE; **fit trên V8.5, cần fit lại nếu đổi v8_7** |
| C2 | `score = MacroF1(CIC) − FPR(real)` (chọn checkpoint B5) | [v8_7_train_realbenign.py](v8_7_train_realbenign.py) | trọng số 1:1 hợp lý? có nên phạt PortScan-recall? |
| S1 | `HybridFeatureScaler` | [hybrid_feature_scaler.py](../model_defs/hybrid_feature_scaler.py) | công thức từng nhóm feature; vì sao Bước 4 cấm đổi |
| W1 | class-weight sqrt-balanced (fine-tune) | v8_7_train_realbenign.py | công thức trọng số; ảnh hưởng PortScan |

**Deliverable Pha 1:** `training/AUDIT_CONGTHUC.md` — bảng trên đã điền kết luận, đánh dấu công thức cần sửa (ứng viên: thống nhất epsilon; xem lại `.replace(0,1)`). **Không sửa code ngay** — chỉ liệt kê ứng viên sửa để user duyệt.

**Done Pha 1:** mọi công thức có 1 dòng kết luận "giữ / sửa (nêu cách) / chỉ ghi chú luận văn"; không còn công thức nào "không biết vì sao có".

---

## PHA 2 — Khôi phục PortScan (hướng CẢ HAI)

### 2A. Lớp CHÍNH — Rule IP-agnostic + cửa sổ trượt

**Ý tưởng:** PortScan là mẫu XUYÊN-FLOW (1 nguồn → nhiều cổng). Rule là công cụ đúng, chỉ cần bỏ ràng buộc "biết IP trước" và làm cửa sổ chuẩn hơn.

Thay đổi dự kiến (Pha 2 chỉ ghi rõ, thực thi ở lần sau khi user duyệt):
1. **Bỏ gate `src == scanner_ip`** trong [`PortScanRule.apply`](../ids_replay/postprocess.py): override cho **bất kỳ src** nào có `intensity ≥ min_ports`. `scanner_ip` giữ tùy chọn (mặc định None = mọi nguồn).
2. **`port_spread` → cửa sổ trượt:** với mỗi flow, đếm cổng duy nhất của cùng `src` trong `[t−window, t]` (không phải bucket cố định). Cân nhắc chi phí O(n·k); sắp theo (src, ts) rồi two-pointer.
3. **Giữ tùy chọn loại bỏ chiều phản hồi:** không gắn cờ flow mà `src` là victim trả lời (tránh FP khi server mở nhiều cổng ephemeral).

**Kiểm chứng bắt buộc trước khi nhận (script mới `training/step6_rule_fp.py`):**
- Chạy rule IP-agnostic trên **`b5_benign_test`** (11,701 benign thật, giữ riêng) + benign_real → đo **tỉ lệ benign bị gắn nhầm PortScan**. Ngưỡng chấp nhận: **≤ 0.5%**.
- Chạy trên `portscan_real.csv` với **src coi như IP lạ** (không dùng attacker_ip) → đo recall rule. Kỳ vọng ≥ 95% cho scan nhanh.
- Quét độ nhạy `min_unique_ports ∈ {10,15,20,30}` × `window ∈ {1,2,5}s` → chọn điểm tối FP-benign mà vẫn ≥95% recall scan nhanh. Ghi bảng.

**Rủi ro & phòng ngừa:** benign thật có host mở nhiều cổng (P2P, browser nhiều tab, mDNS) → có thể chạm ngưỡng. Nếu FP-benign >0.5%, xét: (a) nâng ngưỡng cổng, (b) chỉ tính cổng ≤1023/registered, (c) yêu cầu thêm điều kiện "phần lớn flow không có phản hồi" (0 bwd packet).

### 2B. Lớp BACKUP — giữ tín hiệu PortScan trong classifier

**Câu hỏi gating (thí nghiệm quyết định 2B có khả thi không):**
Báo cáo Bước 5 nói "real PortScan = 1 SYN đơn, per-flow không phân biệt được với benign mở kết nối". **Cần kiểm định lại** vì mở-kết-nối benign thường đi tiếp thành phiên có dữ liệu, còn SYN quét thường: cổng đóng → SYN→RST, cổng lọc → SYN không phản hồi. Tức có thể CÓ chữ ký per-flow (RST_Flag_Count, Total_Backward_Packets=0, act_data_pkt_fwd=0, Init_Win_bytes_backward).

**Thí nghiệm (`training/step6_ps_separability.py`):**
- RF/Logistic 5-fold trên **real PortScan vs real benign** (feature thô 80). Đo **CV-AUROC**.
  - Nếu **AUROC cao (≥0.9):** CÓ chữ ký phân biệt ⇒ 2B khả thi. Lấy top-feature (SHAP/importance) làm bằng chứng, và **đính chính** khẳng định "không phân biệt được" của Bước 5.
  - Nếu **AUROC thấp (~0.5–0.7):** đúng là không tách được per-flow ⇒ **bỏ 2B**, chỉ dựa 2A, ghi rõ lý do (không cố ép classifier → tránh làm sống lại FP benign).

**Nếu 2B khả thi → train `v8_8` (fine-tune tiếp từ v8_7):**
- Thêm một phần **real PortScan có chữ ký rõ** (cổng đóng/lọc: có RST hoặc 0 bwd) vào TRAIN với nhãn PortScan; **giữ nguyên 40k benign thật** để không sống lại FP.
- Checkpoint theo `score` mở rộng: `MacroF1(CIC) − FPR(real) + λ·PortScan_recall(real)` — λ nhỏ, quét {0.1, 0.2}.
- **Ràng buộc chấp nhận v8_8:** `FPR benign thật ≤ 1%` (không tệ hơn v8_7 quá 0.7pp) **VÀ** PortScan-recall-classifier > 0 có ý nghĩa (mục tiêu ≥15%). Nếu FPR bật lên >1% → **loại v8_8, giữ v8_7 + chỉ 2A**.

**Lưu ý:** 2B là "đai an toàn thứ hai", KHÔNG được đánh đổi FPR (thành quả cốt lõi Bước 5). Rule 2A vẫn là lớp chính.

---

## PHA 3 — Tái đánh giá end-to-end theo thiết lập LIVE thật

**Mục tiêu:** đo cả pipeline (classifier + rule) trong điều kiện **KHÔNG biết trước IP tấn công**, để số phản ánh live thật — không lặp lại lỗi replay biết-IP.

**Script mới `training/step6_live_eval.py`:**
- Chạy `FeatureExtractor → Classifier → RulePipeline(IP-agnostic)` trên từng file real (portscan/dos/bruteforce/webattack) + `b5_benign_test`.
- **Không** gate ground-truth theo attacker_ip; nhãn theo file nguồn.
- So sánh 3 cấu hình: **V8.5+rule cũ** (baseline hiện tại) · **v8_7+rule IP-agnostic** · **v8_8+rule IP-agnostic** (nếu có).
- Đo mỗi lớp: recall qua-pipeline; benign: FPR tổng + phân rã theo lớp.

**Tiêu chí Go/No-Go để đổi `replay_config` sang v8_7/v8_8:**
| Chỉ tiêu | Ngưỡng Go |
|---|---|
| FPR benign thật (pipeline) | ≤ 1% |
| PortScan recall (pipeline, IP lạ) | ≥ 90% (nhờ 2A) |
| DoS / BruteForce / WebAttack recall | không tụt >5pp so với hiện trạng |
| Macro-F1 CIC (chống forgetting) | ≥ 0.85 |

Chỉ khi **tất cả** đạt Go mới đổi model chính + **fit lại calibration Bước 2** (T + ngưỡng/lớp trên v8_7/v8_8 với b5_benign_val + attack), rồi cập nhật `replay_config.json`.

---

## Thứ tự thực thi (khi user cho phép chuyển từ "kế hoạch" sang "làm")

1. **Pha 1** (audit, chỉ đọc) → `AUDIT_CONGTHUC.md`. *(rẻ, làm trước, không rủi ro)*
2. **Pha 2B-gating** (`step6_ps_separability.py`) → biết có làm classifier backup không. *(quyết định nhánh)*
3. **Pha 2A** (rule IP-agnostic + sliding + `step6_rule_fp.py`). *(lõi khôi phục PortScan)*
4. **Pha 2B** train v8_8 *(chỉ nếu gating khả thi)*.
5. **Pha 3** (`step6_live_eval.py`) → bảng Go/No-Go.
6. Nếu Go: fit calibration + đổi `replay_config` + cập nhật memory tiến trình.

## Definition of Done (cả kế hoạch)
- [ ] Mọi công thức có kết luận giữ/sửa (Pha 1).
- [ ] Rule IP-agnostic có bằng chứng FP-benign ≤0.5% và recall scan ≥95% ở thiết lập IP lạ (Pha 2A).
- [ ] Trả lời dứt điểm: classifier CÓ/KHÔNG giữ được PortScan (Pha 2B gating), kèm số AUROC.
- [ ] Bảng Go/No-Go live-realistic cho V8.5 / v8_7 / v8_8 (Pha 3).
- [ ] Không chỉ số nào tụt khi chuyển replay→live (điều kiện tiên quyết đổi model chính).

## Liên quan
- Báo cáo trước: [BUOC1](BUOC1_KETQUA.md) · [BUOC2](BUOC2_KETQUA.md) · [BUOC4](BUOC4_KETQUA.md) · [BUOC5](BUOC5_KETQUA.md)
- Memory: `live-detection-model-improvement-progress`, `project_live_work_branch`.
