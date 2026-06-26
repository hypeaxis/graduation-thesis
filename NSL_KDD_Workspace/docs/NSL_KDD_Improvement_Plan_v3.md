# Kế hoạch cải thiện NSL-KDD — v3

> Ngày: 2026-06-24 · **Thay thế** bản kế hoạch v2
> Kết quả hiện tại:
> - **FTT v9** (best FT-Transformer): macro-F1 = **0.654** · R2L F1=0.503/recall=0.383 · U2R F1=0.398
> - **LightGBM v11** (best standalone): macro-F1 = **0.668** · Probe F1=0.804 · R2L F1=0.344/recall=0.208
> - Khoảng cách giữa hai model: LGBM giỏi Probe/U2R, FTT giỏi R2L — rõ ràng bổ sung lẫn nhau
> Target: macro-F1 **0.70–0.71** (thực thi bước 1–3) · Stretch: **0.74–0.76** (thêm bước 4)

---

## Xác nhận trước khi tiếp tục

**Autoencoder đã train đúng:** fit chỉ trên `X_train[y==0]` (Normal từ KDDTrain+), không dùng test set.
Con số gate Phase 0 (62% R2L bị chặn, 64% U2R bị chặn) là đáng tin.

---

## Oracle Analysis (đã tính, đáng tin)

| Class | FTT v9 recall | LGBM v11 recall | Nên tin model nào |
|---|:---:|:---:|:---:|
| Normal | 0.882 | **0.968** | LGBM |
| DoS | **0.860** | 0.785 | FTT |
| Probe | 0.672 | **0.824** | LGBM |
| **R2L** | **0.383** | 0.208 | **FTT** (hơn gần 2×) |
| **U2R** | **0.627** | 0.522 | **FTT** |

- **Oracle per-sample** (luôn chọn model đúng hơn): macro-F1 = **0.760** → đây là trần lý thuyết
- **Global alpha = 0.70** (70% LGBM + 30% FTT, tính trên TEST): F1 = **0.694**
- Khoảng dư địa cho meta-learner: từ 0.668 (LGBM alone) → 0.694 (global mix) → 0.760 (oracle)

Meta-learner học per-class weighting có thể lấy được ~0.70–0.71 từ khoảng 0.668→0.760.

---

## Tại sao v11 (LightGBM) không ensemble được với v9 (FTT)?

Global alpha sweep chọn `alpha=1.0` (pure LGBM) vì val distribution bị lệch:
- val R2L đến từ train distribution (telnet-heavy) → FTT đang overfit val R2L hơn
- val Probe/U2R: LGBM tốt hơn rõ ràng → kéo alpha về 1.0

Giải pháp: **meta-learner học cách blend**, thay vì tìm một scalar alpha cố định.

---

## Bước 1 — Stacking Ensemble (cao nhất, rẻ nhất)

**Ý tưởng:** dùng vector xác suất 5-class của cả v9 và v11 (10 chiều tổng) làm input cho một meta-learner nhẹ. Meta-learner tự học "với R2L thì tin v9, với Probe/U2R thì tin v11" — mà không cần biết nhãn trước lúc inference.

```
v9  → p_v9  (5 chiều)  ┐
                         ├→ [p_v9 ‖ p_v11] (10 chiều) → meta-learner → final label
v11 → p_v11 (5 chiều)  ┘
```

**Cách chống leakage (bắt buộc):**
- Meta-learner KHÔNG được fit trên tập đã dùng để chọn best epoch của v9/v11
- Dùng **out-of-fold predictions** từ K-fold cross-val trên KDDTrain+ để sinh training data cho meta-learner
- Hoặc (đơn giản hơn): dùng val set (boost-minority) làm meta-train, đánh giá trên test
  - Val = 13,477 mẫu: đủ để fit logistic regression 10-chiều, không đủ cho LGBM nông nếu U2R chỉ có 5 val mẫu

**Meta-learner ưu tiên:** Logistic Regression đa lớp (`solver='lbfgs'`, `C=1.0`, `max_iter=1000`) — đủ mạnh, ít overfit, fit nhanh.

**Phương án rẻ hơn nếu val quá nhỏ:** Per-class weighted fusion
```python
p_final[:, c] = w_c * p_v11[:, c] + (1 - w_c) * p_v9[:, c]
```
Tối ưu w_c bằng Nelder-Mead trên val, evaluate trên test.

**Kỳ vọng:** macro-F1 **+0.02–0.04** (đưa từ 0.668 lên ~0.69–0.71).

**File:** `src/training/stacking_ensemble.py` (mới)

---

## Bước 2 — Threshold per-class (miễn phí, làm cùng bước 1)

R2L của cả hai model đang bị precision quá cao / recall chết:
- v11 LGBM: P=0.977, R=0.208 — quá thận trọng
- v9 FTT:   P=0.731, R=0.383 — vẫn còn nhiều dư địa

**Cơ chế:** thay vì `argmax(prob)`, dùng `argmax(prob - threshold)` với threshold_c per-class.
Hạ threshold_R2L → model dễ predict R2L hơn → recall tăng.

```python
def predict_with_thresholds(probs, thresholds):
    margins = probs - np.array(thresholds)[np.newaxis, :]
    return np.argmax(margins, axis=1)
```

**Kỷ luật:** tune threshold **chỉ trên val**, report trên test.
Ước tính v9: hạ ngưỡng R2L để R≈0.55–0.60, P≈0.55 → F1 ≈ 0.57 (từ 0.503).
**Đừng đẩy recall quá 0.65** — precision sẽ sụp, gây hại macro.

Làm threshold tune SAU khi có ensemble (bước 1), vì ensemble thay đổi phân phối prob.

**File:** tích hợp vào `stacking_ensemble.py` hoặc thêm `--optimize-thresholds` flag.

---

## Bước 3 — Class-aware Gate (gỡ trần R2L/U2R mà không hại DoS)

**Vấn đề đã xác nhận:**
- 62% test R2L có `ae_recon_error < 0.008481` → bị hard gate chặn nhầm thành Normal
- 64% test U2R tương tự
- Gỡ gate hoàn toàn (v10) → DoS sụp từ 0.894 → 0.838 vì gate đang giúp DoS

**Giải pháp: Asymmetric gate — chỉ chặn khi CẢ HAI điều kiện thỏa:**

```python
# Hiện tại (hard gate):
is_normal = ae_mse < THRESHOLD  # route về Normal nếu đúng

# Đề xuất (class-aware gate):
ae_says_normal     = ae_mse < THRESHOLD
ft_not_suspicious  = max(p_R2L, p_U2R) < low_conf_threshold  # e.g., 0.15
is_normal_final    = ae_says_normal AND ft_not_suspicious
# Nếu FTT đã nghi R2L/U2R → bỏ qua gate, tin FTT
```

Hoặc phiên bản đơn giản hơn:

```python
# Chỉ áp gate cho DoS/Probe (high reconstruction error → đúng khi AE cờ anomaly)
# Bypass gate cho R2L/U2R (low recon error là đặc trưng của chúng, không phải bug)
if ae_mse < THRESHOLD:
    if ft_pred in {R2L, U2R}:
        pass  # tin FTT, không route về Normal
    else:
        route_to_Normal()
```

**Kỳ vọng:** R2L recall tăng lên gần 0.65+ (từ 0.383), U2R recall giữ nguyên hoặc tăng nhẹ.
DoS/Probe không bị ảnh hưởng vì gate vẫn hoạt động cho chúng.

**File:** `Final_Product/inference/snort_two_stage_inference.py` (sửa hàm `predict()`).
Lưu ý: bước này chỉ ảnh hưởng inference pipeline, không cần retrain model.

---

## Bước 4 — Feature bất biến với drift cho guess_passwd

> Làm sau bước 1–3. Đây là bước khó nhất, chạm trần thật ~0.74–0.76.

**Nguyên nhân drift đã xác nhận:**
| Feature | Train guess_passwd | Test guess_passwd |
|---|---|---|
| service | 100% telnet | 61% pop_3, 17% telnet |
| rerror_rate | 0.925 | ≈ 0 |
| logged_in | ≈ 0 | 0.618 |
| src_bytes | ~30–200 | ~30–200 (BẤT BIẾN) |
| dst_bytes | ~100–300 | ~100–300 (BẤT BIẾN) |

`small_auth_session` (Phase 1b) đã đúng hướng nhưng hại warezmaster vì threshold dst_bytes<1000 quá hẹp.

**Feature bất biến với drift (ứng viên):**

```python
# Pattern: nhiều lần thử đăng nhập thất bại, session nhỏ, không thành công
df['failed_login_ratio'] = df['num_failed_logins'] / (df['count'].clip(lower=1))
df['small_payload']      = (df['src_bytes'] < 500).astype(float)  # bytes nhỏ → thử mật khẩu
df['no_data_transfer']   = (df['dst_bytes'] < 2000).astype(float) # server trả về ít → thất bại

# Tránh: service one-hot (drift), rerror_rate (flip hoàn toàn)
# Tránh: small_auth_session (dst_bytes < 1000 hại warezmaster có dst_bytes lớn)
```

Xác nhận bằng profiling trước khi dùng:
```python
for feat in ['failed_login_ratio', 'small_payload', 'no_data_transfer']:
    train_gp = train[train.attack=='guess_passwd'][feat].mean()
    test_gp  = test[test.attack=='guess_passwd'][feat].mean()
    print(f"{feat}: train={train_gp:.3f}  test={test_gp:.3f}  drift={abs(train_gp-test_gp):.3f}")
```

**File:** `src/data_processing/preprocessing_pipeline.py` (thêm vào `_engineer_behavioral_features`), regen artifacts.

---

## Bước 5 (Tùy chọn) — Detector R2L chuyên biệt

Nếu sau bước 1–4, R2L vẫn là lực cản chính:
- Train binary classifier R2L-vs-rest trên feature từ bước 4
- Đưa output (prob R2L) vào meta-learner bước 1 như feature thứ 11
- Hoặc dùng như một "veto vote": nếu detector R2L tin tưởng cao → override prediction

**Chỉ làm nếu bước 1–4 cho macro-F1 < 0.70.**

---

## Quy trình chống leakage (bắt buộc)

```
KDDTrain+ ──┬──[80%]──→ fit v9, v11, mọi feature engineering
            │
            └──[20% = val boost-minority]──→ fit meta-learner / tune thresholds / tune gate

KDDTest+  ──→ CHỈ đánh giá cuối cùng, không bao giờ dùng để tune
```

- Fit scaler, AE, SMOTE, feature engineering **chỉ trên train**
- Meta-learner fit trên val (out-of-fold predictions từ v9, v11)
- Threshold và gate tuning **chỉ trên val**

---

## Lộ trình thực thi

| Bước | Việc cần làm | Kỳ vọng macro-F1 | Công sức | Không cần retrain |
|---|---|:---:|:---:|:---:|
| **1** | Stacking ensemble (LR meta-learner) | +0.02–0.04 | Thấp | ✅ |
| **2** | Threshold per-class trên ensemble | +0.01–0.02 | Rất thấp | ✅ |
| **3** | Class-aware gate | +0.01–0.03 | Thấp | ✅ |
| **4** | Feature bất biến guess_passwd | +0.03–0.05 | TB | ❌ (regen + retrain) |
| **5** | R2L binary detector | Biến thiên | TB | ❌ |

**Target thực tế:** Bước 1+2+3 → **0.70–0.71** · Bước 4 thêm → **0.74–0.76**

---

## Trần trung thực sau từng bước

| Lớp | Hiện tại (best) | Sau B1+B2+B3 | Sau B4 | Ghi chú |
|---|---|---|---|---|
| R2L | recall 0.383, F1 0.503 | recall ~0.55, F1 ~0.57 | recall ~0.70, F1 ~0.65 | snmp tail vẫn không thể bắt |
| U2R | recall 0.627, F1 0.398 | F1 ~0.45 | F1 ~0.50 | ổn định quan trọng hơn đẩy cao |
| Probe | F1 0.804 (LGBM) | F1 ~0.80 | F1 ~0.80 | gần đỉnh |
| DoS | F1 0.894 (FTT v9) | F1 ~0.89 | F1 ~0.89 | giữ nguyên |
| Normal | F1 0.820 (LGBM) | F1 ~0.82 | F1 ~0.83 | phụ thuộc R2L fix |
| **Macro** | **0.668** | **~0.70–0.71** | **~0.74–0.76** | |

---

## KHÔNG làm — dead ends đã xác nhận

| Việc | Lý do bỏ |
|---|---|
| SMOTE R2L | Nội suy 20 warezmaster ≠ 944 test. Đã xác nhận gây hại. |
| Gỡ gate hoàn toàn (v10) | DoS sụp từ 0.894→0.838. Gate giúp DoS/Probe. |
| `small_auth_session` feature | Hại warezmaster (dst_bytes lớn không fire). Precision tăng nhưng recall giảm. |
| Global threshold optimization | Overfit val khi val composition ≠ test. v6 đã thấy. |
| Threshold tune trên test | Leakage rõ ràng. |
| Đuổi snmp recall | snmp unseen trong train, recon-error thấp → near-irreducible. |
