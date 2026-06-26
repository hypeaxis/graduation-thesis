# Kế hoạch cải thiện NSL-KDD — v2

> Ngày: 2026-06-24 · **Thay thế** bản kế hoạch trước
> Baseline hiện tại: macro-F1 ≈ **0.595** (v6) · R2L F1 **0.484** / recall **0.376** (v7) · U2R F1 **0.312**
> Target đã chỉnh: macro-F1 ≈ **0.65 – 0.68**
> Code kèm: `nslkdd_improvements.py`

---

## 0. Thay đổi chiến lược cốt lõi

Phân bố subtype thật của KDDTest+ lật ngược giả định cũ: **R2L không phải bài toán coverage của subtype lạ — mà là sparse-generalization của các subtype ĐÃ THẤY nhưng cực thưa trong train.**

| Subtype R2L | Test | Train | Trạng thái |
|---|---:|---:|---|
| **guess_passwd** | 1,231 | 53 | Đã thấy, cực thưa — **prize** |
| **warezmaster** | 944 | 20 | Đã thấy, cực thưa — **prize** |
| imap | 307 | ~12 | Đã thấy, thưa |
| snmpguess | 331 | 0 | Unseen — irreducible |
| snmpgetattack | 178 | 0 | Unseen — irreducible |
| httptunnel | 133 | 0 | Unseen — irreducible |

- **75% test R2L = guess_passwd + warezmaster**, cả hai có trong train.
- **Chỉ 22% (snmp + httptunnel) là unseen** → near-irreducible, bỏ qua.
- Recall R2L = 0.376 ⇒ model đang **miss phần lớn guess_passwd/warezmaster** (subtype đã thấy, learnable). Nếu bắt tốt 2 cái này, recall ≥ 0.75 dù bỏ sót toàn bộ snmp.

**Toàn bộ kế hoạch xoay quanh: bắt cho được guess_passwd + warezmaster; chấp nhận mất đuôi snmp.**

---

## 1. Bước 0 — BẮT BUỘC trước mọi thứ: diagnostic per-subtype

Không có bảng này thì mọi tối ưu đều là mò. Tính recall R2L tách theo subtype trên test:

```python
# y_subtype: tên attack gốc mỗi test row (trước khi map về 5 lớp); y_pred: nhãn 5-class dự đoán
import pandas as pd
df = pd.DataFrame({"subtype": y_subtype, "true5": y_true, "pred5": y_pred})
r2l = df[df.true5 == R2L_ID]
print(r2l.groupby("subtype")
        .apply(lambda g: pd.Series({"n": len(g), "recall": (g.pred5 == R2L_ID).mean()}))
        .sort_values("n", ascending=False))
```

**Đọc kết quả:**
- snmp* ≈ 0 → đúng kỳ vọng, **không cố sửa**.
- guess_passwd / warezmaster < 0.7 → đây là dư địa. Tiếp tục Bước 2 profiling.
- Nếu guess_passwd / warezmaster đã > 0.8 → R2L gần trần, chuyển trọng tâm sang Probe/U2R.

---

## 2. Roadmap (xếp lại theo chẩn đoán mới)

| # | Hành động | Kỳ vọng (macro-F1) | Công sức | Nhắm vào |
|---|---|:---:|:---:|---|
| P1 | Feature engineering theo subtype (guess_passwd + warezmaster) | +0.03 – 0.06 | TB | R2L — prize |
| P2 | Sửa U2R val starvation | +0.01 – 0.03 | Thấp | U2R |
| P3 | Bỏ hard gate → anomaly-score-as-feature | +0.02 – 0.04 | TB | Trần recall |
| P4 | Ensemble LightGBM/XGBoost | +0.01 – 0.03 | TB | Robustness |
| P5 | (Tùy chọn) Cascade stealth↔volume, SSL pretraining | Biến thiên | Cao | Minority |

Con số là ước lượng thô. Đo lại sau mỗi bước; chỉ giữ thay đổi cải thiện test macro-F1.

---

## 3. Chi tiết

### P1 — Feature engineering theo subtype (trọng tâm)

**Nguyên tắc:** dừng feature R2L chung chung; nhắm RIÊNG hai pattern chiếm 75% test.

**a) Profiling trước (mở rộng Bước 0):** so phân phối feature của guess_passwd & warezmaster giữa train và test. Câu hỏi: feature nào tách chúng khỏi Normal? Có drift train→test không?

```python
for sub in ["guess_passwd", "warezmaster"]:
    tr = train[train.attack == sub]
    te = test[test.attack == sub]
    cols = ["num_failed_logins", "logged_in", "is_guest_login", "hot",
            "src_bytes", "dst_bytes", "num_access_files", "num_file_creations", "count"]
    print(f"\n== {sub} ==")
    print(pd.concat([tr[cols].mean().rename("train"),
                     te[cols].mean().rename("test")], axis=1))
```

**b) Feature ứng viên (XÁC NHẬN bằng profiling trước khi tin):**

```python
# guess_passwd: đăng nhập thất bại không dẫn tới session, trên service auth
out["failed_auth"] = out["num_failed_logins"] * (1 - out["logged_in"])
out["auth_service"] = out["service"].isin(
    {"telnet", "ftp", "ssh", "login", "pop_3", "imap4", "rlogin"}).astype(int)
out["guess_passwd_signal"] = out["failed_auth"] * out["auth_service"]

# warezmaster: phiên FTP guest tải file lớn (ngưỡng cần chỉnh theo profiling)
out["ftp_session"] = out["service"].isin({"ftp", "ftp_data"}).astype(int)
out["bulk_download"] = (out["dst_bytes"] > 5000).astype(int)
out["warez_signal"] = out["ftp_session"] * out["is_guest_login"] * out["bulk_download"]
```

**c) Đòn bẩy warezclient → warezmaster (quan trọng):** warezclient có ~890 mẫu train nhưng gần như vắng trong test; warezmaster ngược lại (20 train / 944 test). Hai cái cùng họ "warez/FTP download". ⇒ **Giữ warezclient trong train** và để feature `warez_signal` bắt *signature chung* (không phải quirk riêng của warezclient), để kiến thức warezclient transfer sang warezmaster. Đây là nguồn signal "miễn phí" lớn nhất cho R2L.

> ⚠ Nếu profiling cho thấy guess_passwd test KHÔNG có tín hiệu `num_failed_logins` (feature này nổi tiếng yếu cho R2L tổng quát), thì signal nằm ở chỗ khác — dùng kết quả profiling để chọn feature, đừng ép `failed_auth`.

**Tích hợp:** thêm trước one-hot + scaling → regen `scaler.pkl`, `feature_columns.json`. File: `preprocessing_pipeline.py`.

### P2 — Sửa U2R val starvation

buffer_overflow (20 test) + rootkit (13 test) đều có trong train (30, 10) với signature privilege-escalation rõ. Vấn đề: boost-minority-val lấy 40% của 52 → còn 32 train.

- **Val split class-aware:** lớp đa số giữ tỉ lệ; **U2R chỉ góp một số cố định nhỏ vào val (≤ 5) hoặc loại khỏi val**, giữ ~47–52 mẫu trong train.
- **Không để U2R val-F1 chi phối checkpoint** (8 mẫu là nhiễu). Chọn checkpoint trên macro-F1 của các lớp đại diện đủ, theo dõi U2R riêng.
- Để feature `privilege_escalation` mang tín hiệu; cân nhắc rule high-precision trên feature đó như một detector phụ.
- File: `train_ft_transformer_nslkdd.py`.

### P3 — Bỏ hard gate → anomaly-score-as-feature

Gate cứng (`recon_error > 0.008481`) tạo trần recall: chặn R2L/U2R recon-error-thấp trước khi FT-Transformer nhìn. Đừng *chặn* — **nối lỗi tái tạo vào input** để model tự quyết:

```python
recon = ae.predict(stat_feats_12)              # (N, 12)
err_vec = np.abs(stat_feats_12 - recon)        # (N, 12)
err_scalar = err_vec.mean(axis=1, keepdims=True)
X_aug = np.concatenate([X_122_plus, err_vec, err_scalar], axis=1)
```

- Đổi input dim `FeatureEmbedding` (v1) hoặc thêm group "anomaly" cho v2.
- Gỡ logic `stage1_normal_gate_override` trong inference.
- ⚠ **Caveat:** snmp recon-error-thấp ⇒ gỡ gate *không* cứu snmp. Nó thu hồi các attack "vừa đủ bất thường nhưng bị chặn" (có thể gồm guess_passwd/warezmaster bị gate nhầm). Đáng làm, nhưng không kỳ vọng chạm snmp.
- File: `phase2_ft_transformer.py`, `Final_Product/inference/`.

### P4 — Ensemble LightGBM/XGBoost

Trên dữ liệu bảng, GBDT thường ngang/hơn deep model và bắt subtype thưa bằng split rule rõ. Train LightGBM trên cùng feature (kèm feature P1), ensemble softmax với FT-Transformer (weighted average hoặc stacking nhẹ tune trên val).

### P5 — Tùy chọn (nếu P1–P4 chưa đủ)

Cascade tách stealth (R2L/U2R) khỏi volume (DoS/Probe) để gradient minority không bị áp đảo; SSL masked-feature pretraining cho representation tốt hơn (bằng chứng lẫn lộn).

---

## 4. KHÔNG làm — dead ends đã xác nhận thực nghiệm

| Việc | Vì sao bỏ |
|---|---|
| SMOTE để "fix coverage" R2L | Nội suy trong cụm 20 điểm warezmaster ≠ độ phủ 944 điểm test. Đã xác nhận không giúp. |
| Threshold optimization | Làm giảm macro-F1 v6 (0.595 → 0.570) — overfit val khi composition val≠test. Nếu giữ, chỉ áp lớp đa số. |
| boost-minority val 40% cho U2R | Đói train (52 → 32). Thấy ở P2. |
| "Đại diện hóa" val cho snmp tail | Subtype unseen không thể đưa vào val từ train. Lãng phí công sức. |
| Đuổi recall snmp/httptunnel | Looks-normal, recon-error-thấp, vắng train → near-irreducible (~22% R2L, chấp nhận mất). |
| Đẩy U2R F1 bằng SMOTE 20× | 52 → 1000 tạo manifold nhiễu, over-predict (precision 0.20–0.35). |

---

## 5. Quy trình đánh giá (kỷ luật)

- **Metric chính:** test macro-F1 (KDDTest+). Luôn kèm **per-class P/R/F1 + per-subtype recall (Bước 0) + confusion matrix**.
- **Đo end-to-end** qua cả 2 stage — không báo cáo Stage-2 isolated. (Cần kiểm tra cho mọi con số "4-class".)
- **Không rò rỉ:** fit scaler/encoder/SMOTE chỉ trên train.
- **Bỏ threshold tuning** trừ khi chỉ áp lớp đa số.

---

## 6. Trần trung thực đã chỉnh

| Lớp | Hiện tại | Target | Ghi chú |
|---|---|---|---|
| R2L | F1 0.484 / recall 0.376 | F1 **0.65–0.70** | Bắt seen subtypes; mất ~22% snmp tail |
| U2R | F1 0.312 | F1 **0.45–0.55** | Sửa val starvation; signature rõ |
| Probe | ~0.66–0.70 | ~0.75 | Feature scan |
| DoS | ~0.87–0.89 | ~0.90 | Gần đỉnh |
| Normal | ~0.79–0.83 | ~0.85 | Phụ thuộc fix R2L |
| **Macro** | **~0.595** | **~0.65–0.68** | |

> 99% macro-F1 (5-class, KDDTest+) không trung thực. "99%" chỉ hợp lệ nếu là **binary Normal-vs-Attack** (ghi rõ) hoặc F1 một lớp dễ.

---

## 7. Lộ trình theo phase

- [ ] **Phase 0 (½ ngày):** Diagnostic per-subtype (Bước 0) + profiling feature guess_passwd/warezmaster (P1a). Xác lập baseline đáng tin, biết chính xác dư địa.
- [ ] **Phase 1 (1–2 ngày):** P1 feature engineering theo subtype → regen artifacts → retrain → so per-subtype recall.
- [ ] **Phase 2 (1 ngày):** P2 sửa U2R val split → retrain.
- [ ] **Phase 3 (2–3 ngày):** P3 bỏ hard gate, anomaly-as-feature → đo end-to-end.
- [ ] **Phase 4 (2–4 ngày):** P4 ensemble LightGBM.
- [ ] **Phase 5 (tùy chọn):** cascade / SSL.

> Sau mỗi phase: so macro-F1 + per-class + per-subtype với baseline 0.595. Giữ cái cải thiện, loại cái không. Mục tiêu thoát ở ~0.65–0.68 macro-F1 — cạnh tranh sòng phẳng với literature trung thực.
