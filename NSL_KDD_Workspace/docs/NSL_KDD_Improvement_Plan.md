# Kế hoạch cải thiện mô hình NSL-KDD

> Ngày: 2026-06-24
> Baseline hiện tại: **test macro-F1 ≈ 0.638** trên KDDTest+ (5-class)
> Mục tiêu trung thực: **macro-F1 ≈ 0.69–0.72** (stack đầy đủ các kỹ thuật bên dưới)
> Code kèm theo: `nslkdd_improvements.py` (threshold optimization + feature engineering)

---

## 0. Tóm tắt định hướng

Kế hoạch nhắm vào **đúng ba chỗ đang hỏng**, không phải tinh chỉnh chung chung:

1. **R2L — coverage** (không phải density): precision 0.93 / recall 0.29 ⇒ model học một manifold R2L hẹp từ 995 mẫu train rồi tự tin loại bỏ các subtype lạ chiếm phần lớn trong test.
2. **U2R — precision** (over-predict): recall ổn nhưng precision 0.20–0.35, do bơm 52 → 1000 mẫu (20× synthetic) tạo manifold nhiễu lấn sang lớp khác.
3. **Gate 2-stage — trần recall**: R2L/U2R có reconstruction error *thấp* (trông như normal) nên bị autoencoder route nhầm sang Normal trước khi FT-Transformer kịp nhìn.

> **Lưu ý kỳ vọng:** Đây là benchmark có distribution shift cấu trúc (KDDTest+ chứa ~14–17 loại tấn công không có trong train). 99% macro-F1 không đạt được một cách trung thực; ~0.70 đã là cạnh tranh sòng phẳng với literature. Tiêu chí thành công trong kế hoạch này được đặt theo mức đó.

---

## 1. Chẩn đoán per-class (run tốt nhất hiện tại)

| Lớp | P / R / F1 | Support train → test | Chẩn đoán |
|-----|-----------|----------------------|-----------|
| **R2L** | 0.93 / 0.29 / **0.44** | 995 → 2,885 (16×) | Coverage gap — bottleneck lớn nhất |
| **U2R** | 0.35 / 0.54 / **0.42** | 52 → 67 | Over-predict do SMOTE 20× |
| Probe | 0.62 / 0.70 / 0.66 | 11,656 → 2,421 | Còn dư địa feature scan |
| DoS | 0.93 / 0.82 / 0.87 | 45,927 → 7,458 | Gần đỉnh; ~18% lọt sang Normal |
| Normal | 0.71 / 0.90 / 0.79 | 67,343 → 9,711 | Precision phụ thuộc fix R2L |

**Bằng chứng val không đại diện:** val = 15% iid từ train, chỉ có ~149 R2L / ~8 U2R ⇒ checkpoint selection gần như bỏ rơi 2 lớp thiểu số. Gap val/test của v5 (0.946 / 0.637 = **0.309**) là dấu hiệu mạnh rằng số v5 đang đo trên dữ liệu attack-only (bỏ qua gate), không phải end-to-end.

---

## 2. Roadmap ưu tiên

| # | Kỹ thuật | Tier | Kỳ vọng (macro-F1) | Công sức | Nhắm vào |
|---|----------|:----:|:------------------:|:--------:|----------|
| 1 | Threshold per-class | 1 | +0.02 – 0.05 | Thấp | R2L recall, calibration |
| 2 | Feature hành vi R2L/U2R | 1 | +0.03 – 0.08 | TB | R2L coverage |
| 3 | Anomaly score → feature | 1 | +0.02 – 0.05 | TB | Trần recall (gate) |
| 4 | U2R: giảm SMOTE + focal alpha | 2 | +0.01 – 0.03 | Thấp | U2R precision |
| 5 | Ensemble LightGBM/XGBoost | 2 | +0.01 – 0.03 | TB | Robustness, R2L/U2R |
| 6 | Cascade stealth ↔ volume | 2 | Biến thiên | Cao | Minority recall |
| 7 | SSL pretraining (masked feature) | 3 | Suy đoán | Cao | Generalization |
| 8 | SMOTE-NC thay vanilla SMOTE | 3 | Cận biên | Thấp | Density (đúng cách) |

> Các con số kỳ vọng là **ước lượng thô**, không phải cam kết. Đo lại sau mỗi bước; chỉ giữ thay đổi nào thực sự cải thiện test macro-F1.

---

## 3. Chi tiết từng kỹ thuật

### Tier 1 — làm trước

#### [1] Tối ưu threshold per-class
- **Vì sao:** R2L precision 0.93 / recall 0.29 — model tự tin nhưng hiếm khi gọi R2L. Tại P=0.93/R=0.29 ⇒ F1=0.44; dịch sang P≈0.70/R≈0.55 ⇒ F1≈0.62, **không train lại**.
- **Cách làm:** thay argmax bằng ngưỡng quyết định riêng từng lớp (`optimize_thresholds` + `predict_with_thresholds` trong `nslkdd_improvements.py`). Cơ chế: chọn lớp có margin `(prob − threshold)` lớn nhất; hạ ngưỡng một lớp ⇒ tăng recall lớp đó.
- **⚠ Kỷ luật:** tune **chỉ trên val**, không bao giờ trên test. Val hiện chỉ có ~149 R2L nên gain cho riêng R2L bị giới hạn tới khi làm Phase 0 (stratify val theo test).
- **File:** áp dụng sau train loop trong `train_ft_transformer_nslkdd.py`; lưu thresholds vào `inference_config.json`.

#### [2] Feature engineering hành vi (R2L/U2R) — fix coverage thật
- **Vì sao:** coverage gap không sửa được bằng resampling. Cần feature mã hóa *hành vi trừu tượng* generalize sang subtype chưa thấy, thay vì nhớ tổ hợp service×protocol của train.
- **Cách làm:** `engineer_behavioral_features()` tạo: `auth_anomaly`, `failed_login_ratio`, `remote_file_activity`, `guest_with_access`, `hot_per_byte`, `low_volume_active`, `privilege_escalation`, `is_sensitive_service`. (num_failed_logins *đơn lẻ* gần như vô dụng cho R2L → luôn dùng dạng kết hợp.)
- **⚠ Tích hợp:** thêm **trước** one-hot + scaling → **regen `scaler.pkl` và `feature_columns.json`** (122 → ~130 features). Đảm bảo numeric block bao gồm các cột mới.
- **⚠ Caveat trung thực:** snmpgetattack/snmpguess (chiếm phần lớn R2L trong test) trông gần như SNMP bình thường — feature này không cứu hết, nhưng họ guess_passwd/warez/ftp sẽ generalize tốt hơn nhiều.
- **File:** `src/data_processing/preprocessing_pipeline.py`.

#### [3] Anomaly score thành feature — bỏ hard gate
- **Vì sao:** gate cứng tạo trần recall (recall end-to-end ≤ recall gate). R2L/U2R recon-error-thấp bị route nhầm sang Normal.
- **Cách làm:** đừng để autoencoder *chặn*. Lấy reconstruction error per-feature + scalar, **nối vào input** FT-Transformer:
  ```python
  recon = ae.predict(stat_feats_12)               # (N, 12)
  err_vec = np.abs(stat_feats_12 - recon)         # (N, 12)
  err_scalar = err_vec.mean(axis=1, keepdims=True)
  X_aug = np.concatenate([X_122, err_vec, err_scalar], axis=1)  # 122 -> 135
  ```
- **⚠ Tích hợp:** đổi input dim của `FeatureEmbedding` (v1) hoặc thêm group thứ 5 "anomaly" cho `FeatureGroupEmbedding` (v2). Cập nhật inference để bỏ logic gate cứng và `stage1_normal_gate_override`.
- **File:** `phase2_ft_transformer.py`, `Final_Product/inference/`.

### Tier 2 — chắc chắn có giá trị

#### [4] U2R: cắt SMOTE quá đà + focal alpha
- **Vì sao:** recall ổn (0.45–0.69), precision 0.20–0.35. Bơm 52 → 1000 (20×) là nguồn false positive.
- **Cách làm:** hạ target SMOTE U2R xuống ~200–300 (hoặc bỏ), tăng focal alpha cho U2R, để feature `privilege_escalation` mang tín hiệu. U2R chỉ 67 mẫu test ⇒ F1 vốn nhiễu; **ổn định** quan trọng hơn đẩy cao.
- **File:** `train_ft_transformer_nslkdd.py` (`--smote-strategy`, alpha của FocalLoss).

#### [5] Ensemble LightGBM/XGBoost
- **Vì sao:** trên dữ liệu bảng, GBDT thường ngang hoặc hơn deep model; bắt R2L/U2R bằng split rule rõ ràng tốt hơn.
- **Cách làm:** train LightGBM trên cùng feature (kèm feature mới #2), ensemble softmax với FT-Transformer (weighted average hoặc stacking nhẹ trên val).
- **File:** module mới + combiner trong inference.

#### [6] Cascade phân tầng "stealth ↔ volume"
- **Vì sao:** 5-class phẳng để Normal/DoS áp đảo gradient của R2L/U2R.
- **Cách làm:** tầng 1 Normal/Attack (learned); tầng 2 tách high-volume (DoS/Probe) ↔ stealth (R2L/U2R); nhánh stealth chuyên biệt với feature R2L riêng, tối ưu recall thiểu số độc lập.

### Tier 3 — nếu còn thời gian
- **[7] SSL pretraining:** masked feature modeling trên toàn KDDTrain+ trước khi fine-tune. Có thể cải thiện representation cho attack lạ; bằng chứng còn lẫn lộn.
- **[8] SMOTE-NC:** nếu vẫn oversampling, dùng SMOTE-NC (xử lý đúng cột categorical) *trước* khi encode. Đừng SMOTE vanilla trên 122-dim one-hot (nội suy cột one-hot tạo giá trị phân số vô nghĩa).

---

## 4. Bản đồ tích hợp (files bị đụng)

| File | Thay đổi |
|------|----------|
| `preprocessing_pipeline.py` | Thêm `engineer_behavioral_features` trước encode/scale; regen `scaler.pkl`, `feature_columns.json` |
| `phase2_ft_transformer.py` | Đổi input dim cho anomaly features (#3); (tùy chọn) SSL head (#7) |
| `train_ft_transformer_nslkdd.py` | Threshold opt (#1); U2R SMOTE target + alpha (#4) |
| `Final_Product/inference/` | Bỏ hard gate → soft feature (#3); áp tuned thresholds; report **end-to-end** |
| (mới) `lightgbm_model.py` + combiner | Ensemble (#5) |
| `inference_config.json` | Lưu per-class thresholds; gỡ ngưỡng gate cứng |

---

## 5. Quy trình đánh giá (kỷ luật bắt buộc)

- **Metric chính:** test macro-F1 trên KDDTest+. Luôn kèm **per-class P/R/F1 + confusion matrix**. Không dùng weighted-F1 để so sánh run.
- **Đo end-to-end:** chạy qua **cả 2 stage**, không báo cáo Stage-2 isolated. (Đây là điều cần kiểm tra cho con số v5 0.60.)
- **Không rò rỉ:** fit scaler / encoder / SMOTE **chỉ trên train**. Tune threshold **chỉ trên val**.
- **Val đại diện hơn:** stratify val-from-train theo tỷ lệ class của test (sửa lệch *tỷ lệ* để checkpoint ngừng bỏ rơi R2L). Lệch *coverage* là bất khả kháng. Nếu bắt buộc dùng slice test làm val, **khóa riêng một slice test khác** chỉ dùng một lần cho báo cáo cuối.

---

## 6. Lộ trình thực thi theo phase

- [ ] **Phase 0 — Vệ sinh đánh giá (½ ngày).** Stratify val theo test; kiểm tra không rò rỉ; dựng báo cáo per-class end-to-end qua cả 2 stage; khóa clean test slice. → *Thiết lập baseline 0.638 đáng tin.*
- [ ] **Phase 1 — Quick wins (1–2 ngày).** [1] Threshold opt → đo lại. [2] Feature hành vi → regen artifacts, retrain → đo lại.
- [ ] **Phase 2 — Gỡ trần (2–3 ngày).** [3] Anomaly-score-as-feature (bỏ hard gate). [4] U2R SMOTE fix. → đo end-to-end.
- [ ] **Phase 3 — Ensemble (2–4 ngày).** [5] LightGBM + combiner trên val → đo lại.
- [ ] **Phase 4 — Tùy chọn.** [6] Cascade, [7] SSL.

> Sau **mỗi** phase: so test macro-F1 + per-class với baseline 0.638. Giữ thay đổi cải thiện, loại bỏ thay đổi không.

---

## Phụ lục — Tiêu chí thành công trung thực

| Kết quả | Trạng thái |
|---------|-----------|
| Macro-F1 ~0.65–0.72 trên KDDTest+ (5-class, end-to-end) | ✅ Mục tiêu thực tế |
| R2L F1 0.44 → ~0.60+ | ✅ Khả thi (stretch) |
| U2R F1 ổn định ~0.50+ với precision khá hơn | ✅ Khả thi |
| 99% macro-F1 (5-class, KDDTest+) | ❌ Không trung thực — dấu hiệu rò rỉ |
| "99%" cho báo cáo | Chỉ trung thực nếu là **binary Normal-vs-Attack** (ghi rõ) hoặc F1 một lớp dễ |
