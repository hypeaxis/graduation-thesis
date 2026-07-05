# BƯỚC 5 — Kết quả fine-tune + benign thật (v8_7)

**Ngày:** 05/07/2026 · **Đúng thuốc theo chẩn đoán Bước 4 (RF AUROC 1.0).**
Scripts: [`split_benign_b5.py`](split_benign_b5.py), [`v8_7_train_realbenign.py`](v8_7_train_realbenign.py), [`step5_eval.py`](step5_eval.py)

## Thiết kế

- **Chia benign thật** (pool 63,401 = benign_real + benign_val, seed 42): **train-mix 40,000 / val 11,700 / test 11,701**. `b5_benign_test` **giữ riêng tuyệt đối** (không train/tune).
- **Train** = Combined_V8_5 (CIC: 51,994 benign + 59,831 attack) **+ 40,000 benign thật** (chỉ vào TRAIN). Val nội bộ = 10% CIC (giữ để đo Macro-F1 CIC, chống forgetting).
- **GIỮ nguyên tiền xử lý V8.5** (`HybridFeatureScaler` — Bước 4 chứng minh đổi scaler làm hại). Chỉ thay **dữ liệu**.
- Fine-tune từ **V8.5** (best), class-weight sqrt-balanced. **Checkpoint theo `score = Macro-F1(CIC) − FPR(benign thật val)`** → tối ưu đúng mục tiêu. Early-stop epoch 11, best = **epoch 5**.

## Quá trình train (FPR giảm đều, attack không đổi)

| epoch | MacroF1(CIC) | FPR(real val) | recall DoS/BF/WA/PS |
|---|---|---|---|
| 1 | 0.878 | 0.62% | 0.89/0.99/0.84/1.00 |
| 3 | 0.879 | 0.35% | 0.89/0.99/0.84/1.00 |
| **5 (best)** | **0.880** | **0.26%** | 0.89/0.99/0.84/1.00 |

→ FPR benign thật lao dốc 0.62%→0.26% qua vài epoch; **attack recall bất động** — không catastrophic forgetting.

## Đánh giá trên `b5_benign_test` (GIỮ RIÊNG — số trung thực)

| | V8.5 (CIC-only) | **V8.7 (+ benign thật)** | Δ |
|---|---|---|---|
| **FPR benign thật** | 24.26% | **0.29%** | **−23.97pp** ✅ |
| **DoS-FP** | 20.46% | **0.25%** | **−20.21pp** ✅ |
| WebAttack-FP | 3.68% | 0.04% | −3.64pp ✅ |
| DoS TPR | 22.8% | 21.2% | −1.6pp (giữ) |
| Brute Force TPR | 99.7% | 100.0% | +0.2pp |
| Web Attack TPR | 89.9% | 86.5% | −3.3pp |
| **PortScan TPR (classifier)** | 38.6% | **0.0%** | −38.6pp ⚠️ |

**Kết luận:** thêm benign thật **giải quyết dứt điểm FP DoS** (20.46%→0.25%) và tổng FPR (24.26%→**0.29%**, giảm ~84 lần) — xác nhận chẩn đoán Bước 4 (benign-FP vs DoS-thật tách AUROC 1.0 khi model thấy benign thật). Không quên tấn công (DoS/BF/WA giữ).

## Đánh đổi & caveat (trung thực)

1. **Classifier PortScan 38.6%→0% — KHÔNG phải mất PortScan (đã kiểm chứng).**
   - Nguyên nhân bản chất: real PortScan = **1 gói SYN đơn** (median 1 gói Fwd) → xét từng-flow *không phân biệt được* với 1 lần mở kết nối benign. Vì thế V8.5 cũng chỉ 38.6%; sau khi học benign thật, các SYN đơn này rơi về Benign (v8_7 gán 76,694/77,218 = 99.3% PortScan → Benign).
   - **PortScan phải bắt bằng mẫu XUYÊN-FLOW**, không phải per-flow. `PortScanRule` (port_spread: 1 nguồn quét ≥15 cổng/2s) làm việc này độc lập classifier.
   - **Kiểm chứng:** giả định classifier gán toàn bộ real PortScan → Benign (xấu nhất), `PortScanRule` vẫn bắt **77,208/77,218 = 100.0%** → PortScan. Vậy **PortScan không mất** ở pipeline đầy đủ.
   - ⚠️ **KHÔNG nên** ép classifier học "SYN đơn = PortScan": sẽ gọi benign single-packet → PortScan → làm SỐNG LẠI FP vừa diệt. → giữ classifier PortScan=0%, để rule lo (đảm bảo `portscan_rule.enabled=true`).
2. **Macro-F1 CIC 0.88** (từ ~0.95): do **587 benign CIC bị gọi nhầm Brute Force** (model dịch biên benign để fit benign THẬT). Đây là đánh đổi domain — model bớt overfit benign-lab, đổi lấy FPR benign-thật ~0. Vì triển khai là traffic thật, đây là đánh đổi ĐÚNG. **F1 lớp tấn công KHÔNG giảm** (DoS 0.93, PS 1.00, WA 0.88 trên CIC) → đạt tiêu chí Done Bước 5.
3. **Caveat phân bố:** benign test cùng nguồn thu với benign train (khác flow, cùng session/endpoint) → 0.29% là ước lượng cho traffic *cùng loại*; traffic benign hoàn toàn mới có thể cao hơn. Vẫn là kết quả thật trên held-out.

## Trạng thái & quyết định cần

- Checkpoint mới: `models/v8_7_model.pt` + `v8_7_scaler.pkl` + `v8_7_encoder.pkl`. **V8.5 giữ nguyên để rollback.**
- **Cần quyết định:** có nhận **v8_7 làm model chính** cho pipeline live không (đổi `replay_config.json` trỏ v8_7)? Sau đó **wire lại calibration (Bước 2)** — fit lại T + ngưỡng trên v8_7 (dùng b5_benign_val + attack), và đảm bảo `PortScanRule` bật để bù PortScan classifier.
