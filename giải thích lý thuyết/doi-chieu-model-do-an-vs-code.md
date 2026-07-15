# Đối chiếu quyển đồ án ↔ code thật — model & siêu tham số

Nguồn đối chiếu:
- Quyển: `Noi_dung_do_an/content per chapter/PhuLucB_Thong_so_mo_hinh.md`, `Chuong3_De_xuat.md`
- Code + **checkpoint thật** (đọc trực tiếp shape của weight, không tin comment)

Mức độ: 🔴 sai bản chất kiến trúc — hội đồng hỏi là lộ · 🟡 lệch số siêu tham số · 🟢 khớp

---

## 1. Kết luận nhanh

Quyển mô tả **6 mô hình**. Code có đủ cả 6, nhưng **thông số trong Phụ lục B lệch khá nhiều so với
checkpoint thật**, và có 5 chỗ lệch tới mức *sai kiến trúc*, không chỉ sai con số.

Nghiêm trọng nhất: **cascade CIC-IDS-2017 trong quyển được mô tả sai hoàn toàn về số lớp.**
Quyển nói Stage 1 nhị phân (2 lớp) và Stage 2 phân 9 lớp. Checkpoint thật nói khác:
Stage 1 có **6 lớp**, Stage 2 có **5 lớp**.

Tin tốt: **thiết kế thật hay hơn thiết kế được mô tả trong quyển** — sửa lại theo code thì phần
biện luận còn mạnh hơn. Xem mục 3.

---

## 2. Bảng tổng: model nào thật sự tồn tại

| # | Model | Quyển mô tả | Code/checkpoint | Trạng thái |
|---|---|---|---|---|
| 1 | NSL-KDD Autoencoder Gate | 122→64→32→16 | **122→128→64→32→16** | 🔴 thiếu 1 tầng |
| 2 | NSL-KDD FT-Transformer | 5 lớp | ship = **4 lớp**; thí nghiệm stacking = 5 lớp | 🔴 hai hệ thống bị gộp làm một |
| 3 | NSL-KDD LightGBM | có | có (`train_lightgbm_ensemble.py`) | 🟡 lệch tham số |
| 4 | NSL-KDD Meta-LR (stacking) | có | có (`stacking_ensemble.py`, kết quả 0,6809) | 🟢 khớp |
| 5 | CIC cascade Stage 1 (FTT) | 2 lớp, 77 feat | **6 lớp**, 77 feat | 🔴 sai số lớp |
| 6 | CIC cascade Stage 2 (FTT + RF + KNN) | 9 lớp, 34 feat, d_ff=256 | **5 lớp**, 34 feat, **d_ff=512** | 🔴 sai số lớp + d_ff |
| 7 | Testbed V8.5 (FTT) | B.1.9 vs Ch.3.4.5 **mâu thuẫn nhau** | 80 feat, 5 lớp, 1.088.005 tham số | 🟡 B.1.9 sai, Ch.3.4.5 đúng |

---

## 3. 🔴 Lỗi bản chất #1 — Cascade CIC thật ra không phải như quyển viết

Đọc thẳng từ checkpoint (`encoder_stage1.pkl`, `encoder_stage2.pkl`, và shape lớp classifier cuối):

```
Stage 1 classes = ['Benign', 'Brute Force', 'DDoS', 'DoS', 'PortScan', 'Suspicious']   → 6 lớp
        classifier.4.weight shape = (6, 64)          ✔ xác nhận 6 đầu ra

Stage 2 classes = ['Benign', 'Bot', 'Heartbleed', 'Infiltration', 'Web Attack']        → 5 lớp
        classifier.4.weight shape = (5, 32)          ✔ xác nhận 5 đầu ra
```

**Quyển nói:** Stage 1 là cổng nhị phân "Benign / Suspicious", Stage 2 phân 9 lớp.

**Thật ra:** Stage 1 **tự phân luôn 4 lớp tấn công đông** (Brute Force, DDoS, DoS, PortScan) và
chỉ đẩy nhãn gom `Suspicious` xuống Stage 2. Stage 2 là **chuyên gia lớp hiếm**: Bot, Heartbleed,
Infiltration, Web Attack (+ Benign để bắt lại khi Stage 1 báo nhầm).

Cứ hình dung: quyển mô tả "phòng khám chỉ hỏi *có bệnh không*, rồi bác sĩ chuyên khoa chẩn đoán tất
cả 9 bệnh". Thực tế là "phòng khám tự xử lý luôn các bệnh phổ biến (cảm, sốt), chỉ đẩy **ca lạ** cho
chuyên khoa hiếm". Đây chính là lý do Stage 2 nhỏ hơn (d=64, 3 tầng, 4 head) — nó chỉ cần giỏi
4 lớp hiếm, không phải 9 lớp.

**Đây là điểm cần sửa gấp** — và khi sửa, lập luận mạnh lên: gradient của Bot/Infiltration/Heartbleed
ở Stage 2 không còn phải cạnh tranh với DoS/DDoS/PortScan (mỗi lớp hàng trăm nghìn flow) nữa,
chỉ cạnh tranh trong nhóm lớp hiếm. Đó là lý do Macro F1 nhảy từ 0,7831 (1-stage) lên 0,9294.

## 4. 🔴 Lỗi bản chất #2 — Ngưỡng 0,85 đang bị giải thích ngược

**Quyển (Ch. 3.3.4):**
> `label = Benign nếu p_Benign ≥ 0,85, ngược lại Suspicious`
> "Ngưỡng bảo thủ ưu tiên recall tấn công hơn giảm workload."

**Code (`evaluate_cascade_system_v7.py:78,120,176`):**
```python
THRESHOLD = 0.85
mask_stage2  = (s1_preds == suspicious_idx) & (s1_probs >= THRESHOLD)   # → xuống Stage 2
mask_low_prob = (s1_preds == suspicious_idx) & (s1_probs < THRESHOLD)
final_preds_chunk[mask_low_prob] = 'Benign'                             # → ÉP VỀ BENIGN
```

Ngữ nghĩa **ngược hẳn**: flow bị Stage 1 nghi ngờ nhưng độ tin cậy < 85% thì **bị vứt thành Benign**,
chứ không phải được đẩy xuống Stage 2 để soi kỹ. Tức ngưỡng này đang **giảm false positive**, chứ
không phải "ưu tiên recall tấn công". Đúng là bảo thủ — nhưng bảo thủ theo hướng *ngược* với điều
quyển đang biện luận.

Phải viết lại một trong hai: hoặc sửa quyển cho khớp code, hoặc sửa code cho khớp ý định thiết kế.

## 5. 🔴 Lỗi bản chất #3 — Luật Asymmetric Voting không giống mô tả

| Quyển (Ch. 3.3.7) | Code (`evaluate_cascade_system_v7.py:191-201`) |
|---|---|
| Infiltration: RF **hoặc** KNN bỏ phiếu → Infiltration | Đúng, **nhưng thêm nhánh**: hoặc FTT nói Infiltration **và** `ft_prob ≥ inf_thresh` |
| Botnet: chỉ khi **cả 3** đồng thuận (AND of 3) | Thực tế: `ft=='Bot'` **và** (RF **hoặc** KNN nói `'Benign'`) → hạ về Benign. Không phải AND của 3 — RF nói `'DoS'` thì Bot vẫn giữ nguyên |
| Lớp còn lại: **Majority Vote 2/3** | **Không có majority vote nào cả.** Lấy thẳng nhãn FTT nếu `ft_prob ≥ 0.65`, dưới ngưỡng → Benign. RF/KNN **không bỏ phiếu** cho các lớp này |

Nói thẳng: ensemble thật là **FTT làm chủ, RF/KNN chỉ đóng vai trò quyền phủ quyết (veto) cho đúng
2 lớp Bot và Infiltration**. Bảng "Majority Vote (2/3) → Macro F1 0,9247" trong B.2.3 cần kiểm tra
lại xem có thật sự chạy hay không, vì code cuối không có nhánh majority.

## 6. 🔴 Lỗi bản chất #4 — Autoencoder thiếu một tầng

Đọc trực tiếp weight trong `autoencoder_v2_best.h5`:

```
dense   (122, 128)     ← tầng quyển KHÔNG ghi
dense_1 (128, 64)
dense_2 (64, 32)
dense_3 (32, 16)       ← bottleneck
dense_4 (16, 32)
dense_5 (32, 64)
dense_6 (64, 128)      ← tầng quyển KHÔNG ghi
dense_7 (128, 122)
```

Kiến trúc thật: **122 → 128 → 64 → 32 → 16 → 32 → 64 → 128 → 122**.
Quyển (B.1.1 và Ch. 3.2.2) ghi 122 → 64 → 32 → 16. Thiếu hẳn tầng 128 ở cả encoder lẫn decoder.

Ngoài ra:
- Quyển: EarlyStopping `patience=10` → code: `patience=5`.
- Quyển: ngưỡng τ chọn ở **percentile 95** của Normal train errors.
  Code `AutoencoderTrain.py`: chọn bằng **ROC Youden** — `optimal_idx = argmax(tpr - fpr)` trên test.
  Hai cách hoàn toàn khác nhau. Giá trị `0,008481` thì khớp, nhưng **lý do sinh ra nó thì quyển kể sai**.

## 7. 🔴 Lỗi bản chất #5 — Hai hệ thống NSL-KDD bị gộp làm một

Quyển (Ch. 3.2.2) kể một câu chuyện: *AE Gate → flow Suspicious → Stacking Ensemble (FTT + LightGBM
+ Meta-LR) phân 4 lớp tấn công*.

Thực tế trong repo là **hai thứ tách rời**:

| | Sản phẩm triển khai (`snort_two_stage_inference.py`) | Thí nghiệm cho ra số 0,6809 (`stacking_ensemble.py`) |
|---|---|---|
| Kiến trúc | AE Gate + FTT **4 lớp** (DoS/Probe/R2L/U2R) | FTT **5 lớp** + LightGBM + Meta-LR, **phẳng, KHÔNG có AE gate** |
| Bằng chứng | `inference_config.json`: `num_classes: 4` | `stacking_ensemble.py:25` `CLASS_NAMES = ['Normal','DoS','Probe','R2L','U2R']` |
| Có LightGBM? | ❌ Không | ✅ Có |

Con số **Macro F1 = 0,6809 ở B.2.1 đến từ cột phải** — mô hình stacking 5 lớp dự đoán thẳng
cả `Normal`, **không đi qua AE Gate**. Nhưng quyển lại trình bày nó như kết quả của pipeline
two-stage có gate. Phải nói rõ: hoặc đây là hai biến thể (và ghi rõ số nào của biến thể nào),
hoặc bỏ AE gate ra khỏi mạch kể của con số 0,6809.

---

## 8. 🟡 Bảng lệch siêu tham số (không sai kiến trúc, nhưng sai số)

### 8.1 NSL-KDD LightGBM (B.1.3)

| Tham số | Quyển | Code thật | Ghi chú |
|---|---|---|---|
| `min_child_samples` | 20 | **5** | Lệch |
| `bagging_freq` | 5 | **không đặt** | ⚠️ Xem dưới |
| `subsample` / bagging_fraction | 0,8 | 0,8 | Khớp *về mặt chữ* |
| `reg_alpha` / `reg_lambda` | không ghi | 0,1 / 1,0 | Quyển thiếu |

⚠️ **Chi tiết kỹ thuật đáng chú ý:** code dùng sklearn API và chỉ đặt `subsample=0.8` mà **không đặt
`subsample_freq`**. Trong LightGBM, bagging chỉ kích hoạt khi `subsample_freq > 0` — nên trên thực tế
`subsample=0.8` **không có tác dụng gì**. Quyển ghi `bagging_freq=5` (giá trị đúng để bagging chạy),
nhưng code không có. Tức quyển đang mô tả một cấu hình *tốt hơn* cấu hình thật sự chạy.

### 8.2 NSL-KDD Meta-LR (B.1.4)
`max_iter`: quyển 1000 → code **2000**. Còn lại (`C=1.0`, `solver=lbfgs`, input 10 chiều) khớp 🟢.

### 8.3 CIC Stage 1 (B.1.5)

| Tham số | Quyển | Code (`phase2_train_v4_stage1.py`) |
|---|---|---|
| d=128, heads=8, layers=4, dropout=0,2 | ✔ | ✔ 🟢 |
| Số features | 77 | 77 🟢 |
| **Số lớp** | 2 | **6** 🔴 |
| Epochs | 30 (patience 5) | **15** (CosineAnnealingWarmup, warmup=3) |
| Focal γ | 2 | 2 🟢 |
| label_smoothing | không ghi | **0,05** |

### 8.4 CIC Stage 2 (B.1.6)

| Tham số | Quyển | Code thật |
|---|---|---|
| d=64, layers=3, heads=4, dropout=0,2 | ✔ | ✔ 🟢 |
| **d_ff** | 256 | **512** 🔴 |
| Số features | 34 | 34 🟢 (`stage2_features.json`) |
| **Số lớp** | 9 | **5** 🔴 |
| Learning rate | 5e-5 | **1e-4** |
| Epochs | 50 (patience 7) | **20** |
| Focal γ | 1,5 | 1,5 🟢 |
| label_smoothing | không ghi | **0,05** |

Về `d_ff=512`: code gọi `FTTransformer(..., d_model=64, num_layers=3, num_heads=4, ...)` mà
**không truyền `d_ff`** → nhận giá trị mặc định `d_ff=512` của class. Kiểm chứng từ checkpoint:
`transformer_blocks.0.ffn.0.weight` có shape `(1024, 64)` — vì GEGLU cần `d_ff × 2 = 1024` →
`d_ff = 512`, và `ffn.3.weight = (64, 512)` xác nhận lần nữa. Đây là **hardcode ngầm qua giá trị
mặc định** — một cái bẫy điển hình: người viết nghĩ mình dùng 256, thực tế chạy 512.

### 8.5 CIC Random Forest (B.1.7)

| Tham số | Quyển | Code |
|---|---|---|
| n_estimators / max_depth / max_features | 150 / 25 / 20 | ✔ 🟢 |
| `min_samples_split` | 5 | **không đặt** (mặc định 2) |
| `min_samples_leaf` | 2 | **không đặt** (mặc định 1) |
| `class_weight` | `balanced_subsample` | **`balanced`** |

`balanced` vs `balanced_subsample` khác nhau thật: `balanced` tính trọng số **một lần trên toàn bộ
tập train**; `balanced_subsample` tính lại trọng số **trên mẫu bootstrap của từng cây**. Với lớp cực
hiếm (Heartbleed 10 mẫu), `balanced_subsample` mới là lựa chọn đúng — vì nhiều cây bootstrap sẽ không
có mẫu Heartbleed nào cả. Quyển ghi cái đúng, code chạy cái kia.

### 8.6 CIC KNN (B.1.8)

| Tham số | Quyển | Code |
|---|---|---|
| K | 16 | 16 🟢 |
| `weights` | `distance` | **`uniform`** (mặc định) 🔴 |
| `algorithm` | `ball_tree` | **`auto`** (mặc định) |
| `leaf_size` | 30 | không đặt |

Code chỉ có: `KNeighborsClassifier(n_neighbors=16, n_jobs=-1)`.
Chương 3.3.6 còn viết *"KNN (K=16, distance-weighted)"* — **không đúng**, code là uniform:
16 láng giềng bỏ phiếu ngang nhau, không phân biệt gần hay xa.

### 8.7 Testbed V8.5 — quyển **tự mâu thuẫn với chính nó**

| Tham số | Phụ lục B.1.9 | Chương 3.4.5 | **Code `v8_5_train.py`** |
|---|---|---|---|
| Dropout | 0,2 | 0,15 | **0,15** → Ch.3.4.5 đúng |
| drop_path | không ghi | không ghi | **0,15** → cả hai thiếu |
| Learning rate | AdamW lr=1e-4 | layer-wise 1e-5 / 1,5e-5 / 3e-5 | **layer-wise** → Ch.3.4.5 đúng |
| Epochs | 50 (patience 7) | patience 5 | **15** (patience **5**) → Ch.3.4.5 gần đúng |
| Label smoothing | không ghi | 0,10 | **0,10** |
| Weight decay | không ghi | 2e-4 | **2e-4** |
| Class weights | không ghi | √(N/(K·n_c)), clip [0,5;2,0] | **đúng y hệt** 🟢 |
| Activation | GELU | — | **GEGLU** (khác GELU!) |

→ **Phụ lục B.1.9 phải viết lại theo Chương 3.4.5.** Hai chỗ trong cùng một quyển đang nói hai
cấu hình khác nhau cho cùng một model — hội đồng chỉ cần lật hai trang là thấy.

---

## 9. Các tham số HARDCODE không hề có trong quyển — và ý nghĩa của chúng

Đây là phần nguy hiểm nhất khi bảo vệ: những con số này **đang chạy trong hệ thống** nhưng
**không được giải thích ở đâu cả**. Nếu hội đồng mở code ra và hỏi "0,985 này ở đâu ra?" thì phải
trả lời được. Với mỗi con số, khuôn trả lời là: *giải quyết vấn đề gì — to hơn thì sao — nhỏ hơn thì sao*.

### 9.1 Trong `Final/01_NSL_KDD/models/inference_config.json` + `snort_two_stage_inference.py`

| Hằng số | Giá trị | Nó làm gì / to-nhỏ thì sao |
|---|---|---|
| `AUTOENCODER_THRESHOLD` | **0,008481** | Ngưỡng MSE tái tạo. MSE ≥ τ → Suspicious. Cao hơn → bỏ sót tấn công (FN tăng); thấp hơn → mọi flow đều đáng ngờ (FP tăng). Đây là **giá trị đông cứng từ một lần chạy ROC**, nên nó gắn chặt với scaler và tập train lúc đó — đổi dữ liệu là phải fit lại. |
| `threshold_calibration_quantile` | **0,99** | Khi chạy live, hiệu chỉnh lại ngưỡng bằng phân vị 99 của MSE trên chính traffic đang chạy — tức "coi 1% flow lỗi nặng nhất là bất thường". Đây là cơ chế tự thích nghi với môi trường mới. ⚠️ **Nhưng hàm `calibrate` trong code lại có `quantile: float = 0.98` làm mặc định** — hai giá trị 0,98 và 0,99 tồn tại song song, cần thống nhất. |
| `high_confidence_threshold` | **0,95** | Chỉ những dự đoán ≥ 95% mới được đánh dấu "tin cậy cao" khi hiển thị/aggregate. Là ngưỡng trình bày, không đổi nhãn. |
| `stage1_normal_gate_override_threshold` | **0,985** | Nếu AE Gate cho **> 98,5%** số flow là Normal, hệ thống coi đó là dấu hiệu gate đang "ngủ" (bị traffic lạ làm lệch) → kích hoạt cơ chế ghi đè. Nói nôm na: *"nếu bạn bảo mọi thứ đều bình thường một cách đáng ngờ, thì chính bạn mới đáng ngờ."* |
| `dominant_label_warning_threshold` | **0,9** | Cảnh báo vận hành: nếu > 90% flow rơi vào cùng một nhãn → nghi mô hình bị sập về một lớp (mode collapse) hoặc scaler sai. Không đổi kết quả, chỉ bật cờ cảnh báo. |
| `slow_attack_score_override_threshold` | **0,65** | Điểm nghi ngờ tấn công chậm; ≥ 0,65 → gắn cờ. Xem công thức bên dưới. |
| `slow_attack_ratio_override_threshold` | **0,35** | Nếu **> 35% flow trong lô** bị gắn cờ slow-attack, ghi đè kết luận của AE Gate. Lý do tồn tại: tấn công chậm (slowloris) *cố tình* trông giống traffic bình thường ở cấp flow — chỉ lộ ra khi nhìn **tỉ lệ trên cả lô**. |
| `slow_attack_override_min_rows` | **4** | Chốt an toàn: cần ít nhất 4 flow mới cho phép ghi đè. Chống việc 1–2 flow lẻ kích hoạt override (2 trên 3 flow = 67% > 35%, nhưng vô nghĩa về thống kê). |

**Công thức `slow_attack_score`** (`snort_preprocess_122.py:236-242`) — đây là **feature engineering
thủ công hoàn toàn không có trong quyển**:

```python
slow_attack_score = 0.35 * interval_component      # khoảng cách giữa 2 flow / 3.0 giây, chặn ở 1
                  + 0.25 * persistence_component   # số kết nối tới cùng đích trong 60s / 15, chặn ở 1
                  + 0.20 * spread_component        # số cổng đích khác nhau trong 60s / 20, chặn ở 1
                  + 0.20 * burst_component         # 1 − (số flow cùng host / 20)  → thưởng cho "chậm"
slow_attack_flag = 1 if (slow_attack_score >= 0.65 and src_conn_count_60s >= 8) else 0
```

Bóc từng mảnh:
- `interval_component` — flow cách nhau càng lâu (chuẩn hóa theo mốc **3 giây**) thì điểm càng cao.
  Tấn công chậm cố tình giãn nhịp để né rule.
- `persistence_component` — nhưng "chậm" mà **dai** mới đáng ngờ: đếm kết nối tới cùng đích trong 60s,
  chuẩn hóa theo mốc **15** kết nối.
- `spread_component` — quét nhiều cổng khác nhau (mốc **20** cổng) → giống trinh sát.
- `burst_component` — **trừ điểm nếu dồn dập**: chia cho mốc **20** flow cùng host rồi lấy `1 −`.
  Đây là mảnh làm cho score này *chuyên trị tấn công chậm* chứ không phải flood.
- Trọng số 0,35 / 0,25 / 0,20 / 0,20 và các mốc 3s / 15 / 20 / 20 đều là **số do người chọn tay**,
  không phải học từ dữ liệu. Phải trung thực nói điều này nếu bị hỏi: đây là heuristic vận hành,
  được tinh chỉnh bằng quan sát, không phải kết quả tối ưu hóa.
- Điều kiện `src_conn_count_60s >= 8` — chốt chặn: dù điểm cao đến đâu, một nguồn chỉ mở < 8 kết nối
  trong 60 giây thì không thể là tấn công chậm có ý đồ.

### 9.2 Trong cascade CIC (`evaluate_cascade_system_v7.py`)

| Hằng số | Giá trị | Ý nghĩa |
|---|---|---|
| `THRESHOLD` | **0,85** | Ngưỡng route xuống Stage 2 (xem mục 4 — ngữ nghĩa đang bị quyển kể ngược). |
| `infiltration_thresholds` | **[0,65 · 0,68 · 0,70]** | Không phải một ngưỡng — là **một dải được quét** rồi xuất 3 report (`final_v7_report_thresh_*.txt`). Quyển không nói đã chọn giá trị nào để báo cáo con số cuối 0,9294. **Phải chốt và ghi rõ.** |
| soft threshold FTT | **0,65** | Trong Stage 2: nếu FTT tự tin < 65% → ép nhãn về Benign. Đây là **van giảm false positive** ẩn, quyển hoàn toàn không nhắc. Nó ảnh hưởng trực tiếp tới recall của mọi lớp hiếm. |

### 9.3 Trong hệ live (`live_detection/`)

| Hằng số | Giá trị | Ý nghĩa |
|---|---|---|
| `temperature` (calibration) | **1,4811** | Temperature scaling: `softmax(logits / T)`. T > 1 → **làm mềm** phân phối, kéo độ tự tin xuống cho khớp độ chính xác thật. T = 1,48 nghĩa là model gốc đang **quá tự tin**. T < 1 sẽ làm nó tự tin hơn nữa (sai hướng). |
| `per_class_threshold` | PortScan 0,319 · DoS 0,308 · Brute Force 0,588 · Web Attack 0,534 · Benign 0,0 | Ngưỡng riêng từng lớp: dự đoán tấn công mà độ tin cậy dưới ngưỡng của lớp đó → hạ về Benign. Ngưỡng **thấp** (PortScan 0,32) = dễ dàng chấp nhận báo động → ưu tiên recall. Ngưỡng **cao** (Brute Force 0,59) = khó tính hơn → lớp này hay báo nhầm nên siết lại. Benign = 0 vì không cần ngưỡng để nói "bình thường". |
| `target_tpr` | **0,95** | Tiêu chí sinh ra bộ ngưỡng trên: chọn ngưỡng thấp nhất sao cho vẫn giữ **95% recall** trên tập fit. Tức "chấp nhận bỏ sót tối đa 5%, còn lại tối ưu hóa để giảm FP". |
| `PortScanRule.window_sec` | **2,0** | Rule bù cho model: một IP chạm ≥ N cổng khác nhau trong cửa sổ 2 giây → PortScan. Cửa sổ rộng hơn → bắt được scan chậm nhưng dễ nhầm traffic bình thường nhiều cổng. |
| `PortScanRule.min_unique_ports` | **15** | Ngưỡng số cổng. Thấp hơn (ví dụ 5) → trình duyệt mở nhiều tab cũng bị báo; cao hơn (50) → scan nhẹ (`nmap --top-ports 20`) lọt lưới. |
| grad clip | **1,0** | Trong train: chặn norm gradient ở 1,0, tránh một batch dị thường làm nổ weight. |

### 9.4 Class weight V8.5 — hardcode có lý lẽ, nên đưa vào quyển

```python
cw = compute_class_weight('balanced', ...)     # w_c = N / (K · n_c)
cw = np.sqrt(cw)                               # làm dịu
cw = np.clip(cw, 0.5, 2.0)                     # chặn hai đầu
cw = cw / cw.mean()                            # chuẩn hóa
```
- **√** — trọng số balanced thuần cho lớp cực hiếm giá trị khổng lồ (lớp chiếm 0,1% → w = 200).
  Căn bậc hai kéo 200 → 14,1: vẫn ưu tiên, nhưng không để một lớp bé xíu lái toàn bộ gradient.
- **clip [0,5; 2,0]** — chặn cứng: không lớp nào được coi trọng quá 2 lần hay bị coi nhẹ quá nửa
  so với mức trung bình. Đây là bài học rút ra từ V8.3 H1 (class weight 1,565 quá cao → BruteForce
  F1 sập từ 91,9% xuống 50% vì FP tăng vọt).
- **chuẩn hóa về mean = 1** — giữ độ lớn tổng của loss ổn định, để learning rate không bị đổi nghĩa.

---

## 10. Việc cần làm (ưu tiên giảm dần)

1. 🔴 **Sửa B.1.5 / B.1.6 / Ch.3.3**: Stage 1 = 6 lớp (Benign + 4 tấn công đông + Suspicious),
   Stage 2 = 5 lớp (Benign + 4 lớp hiếm). Viết lại lập luận cascade theo hướng "head classes ở tầng 1,
   rare classes ở tầng 2" — mạnh hơn bản hiện tại.
2. 🔴 **Sửa Ch.3.3.4**: ngưỡng 0,85 đang giảm FP, không phải tăng recall.
3. 🔴 **Sửa Ch.3.3.7**: mô tả đúng luật ensemble (FTT chủ đạo + RF/KNN veto cho Bot/Infiltration;
   không có majority vote; có soft threshold 0,65).
4. 🔴 **Sửa B.1.1 / Ch.3.2.2**: Autoencoder có tầng 128; ngưỡng τ chọn bằng ROC Youden, không phải percentile 95.
5. 🔴 **Tách bạch hai hệ thống NSL-KDD** — nói rõ số 0,6809 đến từ stacking 5 lớp (không qua gate).
6. 🟡 **Viết lại B.1.9** theo Chương 3.4.5 + code (dropout 0,15, drop_path 0,15, layer-wise LR, 15 epoch).
7. 🟡 **Sửa B.1.7 / B.1.8**: RF `class_weight='balanced'` (không phải balanced_subsample, không có
   min_samples_*); KNN `weights='uniform'` (không phải distance).
8. 🟡 **Sửa B.1.3**: LightGBM `min_child_samples=5`; nói rõ có `reg_alpha=0,1`, `reg_lambda=1,0`;
   và bagging thực tế **không hoạt động** vì thiếu `subsample_freq`.
9. 🟢 **Bổ sung một mục "Tham số vận hành"** vào Phụ lục B, gom toàn bộ mục 9 ở trên —
   để không bị hỏi bất ngờ về 0,985 / 0,65 / 1,4811 / 15 cổng.
