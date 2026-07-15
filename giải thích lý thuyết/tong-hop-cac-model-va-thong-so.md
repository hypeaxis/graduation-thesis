# Tổng hợp các model trong đồ án — và ý nghĩa từng thông số

> Nguyên tắc đọc: đừng học thuộc con số. Với mỗi thông số, hỏi *"nó đang giải quyết vấn đề gì,
> to hơn thì sao, nhỏ hơn thì sao?"* — đó là cách trả lời hội đồng như người hiểu, không phải người thuộc.

Đồ án đi qua 4 nhóm model, mỗi nhóm gắn với một giai đoạn:

| # | Model | Giai đoạn | Dữ liệu | Vai trò |
|---|---|---|---|---|
| 1 | FT-Transformer V1 (122 feat, 4 lớp) | GĐ1 | NSL-KDD | Baseline nền tảng, F1 0.681 |
| 2 | Autoencoder Gate (122→16→122) | GĐ1 | NSL-KDD | Cổng lọc anomaly 2 tầng |
| 3 | Cascade 2 tầng: FTT Gating + FTT/RF/KNN Expert | GĐ2 | CIC-IDS-2017 | Học kiến trúc cascade + ensemble |
| 4 | FT-Transformer V2 — V8.5 (chính thức) / v8_7 (live) | GĐ3→5 | Testbed 80 feat, 5 lớp | **Hệ thống thật** |

(Các model Domain Adaptation trong `Domain_Adaptation_Workspace` đã được quyết định **không** đưa vào
hệ thống — chỉ giữ làm thí nghiệm chẩn đoán covariate shift.)

---

## 1. FT-Transformer V1 — NSL-KDD (GĐ1)

File: `Final/01_NSL_KDD/models/best_model.pt` (~10MB)

```python
FTTransformer(num_features=122, num_classes=4,
              d_model=128, num_heads=8, num_layers=4, d_ff=512, dropout=0.1)
```

- `num_features=122` — NSL-KDD có 41 cột gốc, nhưng các cột phân loại (protocol, service, flag)
  được one-hot encode, tức mỗi giá trị thành một cột 0/1 → nở ra 122 feature đầu vào.
- `num_classes=4` — DoS, Probe, R2L, U2R (gộp theo 4 họ tấn công kinh điển của KDD).
- `d_model=128, num_heads=8, num_layers=4, d_ff=512` — cùng "khung xương" với model cuối
  (xem mục 4 để hiểu sâu từng núm vặn). Giữ nguyên khung qua các giai đoạn là chủ đích:
  so sánh được giữa các dataset mà không lo khác biệt do kiến trúc.
- `dropout=0.1` — V1 chỉ có một lớp phanh chống overfit duy nhất. Chưa có DropPath,
  LayerScale, GEGLU — đó là các nâng cấp của V2 sau này.
- Classifier head V1: `128 → 128 → 4` (V2 sau này bóp còn `128 → 64 → 5` cho gọn).

Vai trò trong luận văn: **tái hiện số liệu nền tảng** (Macro F1 0.681) — chứng minh
FT-Transformer chạy được trên dữ liệu IDS dạng bảng, và làm mốc so sánh. KHÔNG phải hệ thống triển khai.

## 2. Autoencoder Gate — NSL-KDD (GĐ1)

File: `Final/01_NSL_KDD/models/autoencoder_v2_best.h5` (Keras/TensorFlow)

Vấn đề nó giải quyết: classifier chỉ biết 4 lớp đã học. Tấn công **lạ hoàn toàn** thì sao?
Autoencoder (bộ tự mã hóa) học cách **nén rồi tái tạo** traffic bình thường; gặp thứ nó chưa từng thấy,
nó tái tạo dở → lỗi tái tạo cao → nghi ngờ.

Kiến trúc đối xứng hình đồng hồ cát:

```
122 → 128 → 64 → 32 → [16] → 32 → 64 → 128 → 122
      (encoder — nén)  cổ chai  (decoder — giải nén)
```

- **Bottleneck 16** — cổ chai, thông số quan trọng nhất: ép 122 chiều qua khe 16 chiều,
  buộc model chỉ giữ được "bản chất" của traffic bình thường. Cổ chai to quá (ví dụ 100) →
  model copy nguyên đầu vào, mất khả năng phát hiện; nhỏ quá (ví dụ 2) → tái tạo cái gì cũng dở,
  báo động loạn.
- `activation='relu'` các tầng giữa, `sigmoid` tầng cuối — sigmoid ép đầu ra về [0,1],
  khớp với dữ liệu đã scale về [0,1].
- `loss='mse'` — Mean Squared Error, tức bình phương sai lệch giữa đầu vào và bản tái tạo.
  Chính con số này là "điểm bất thường" (anomaly score).
- `optimizer='adam'`, `epochs=100`, `batch_size=256` — cấu hình train tiêu chuẩn.
- **Ngưỡng quyết định lấy từ ROC curve** (điểm tối ưu Youden — chỗ TPR−FPR lớn nhất):
  `mse > threshold → anomaly`. Tức ngưỡng không chọn tay mà chọn bằng dữ liệu.
  ⚠️ **Chính xác theo code bản shipped (`autoencoder_v2_best.h5`):** ngưỡng được chọn bằng Youden ROC
  **trên tập TRAIN** (`KddTrain+`), rồi mới đánh giá trên `KddTest+` — **không rò rỉ dữ liệu test**.
  (Bản legacy v1 dùng percentile 95 — đó mới là thứ quyển đang mô tả, và nó KHÔNG phải bản đang chạy.)

Cứ hình dung: một người thủ thư thuộc lòng cách xếp sách của thư viện mình. Đưa cuốn sách quen,
họ đặt lại đúng chỗ ngay (lỗi thấp); đưa vật thể lạ, họ lúng túng (lỗi cao) → chuông reo.

## 3. Cascade 2 tầng — CIC-IDS-2017 (GĐ2)

Thư mục: `CIC_IDS_2017_Workspace/models/` (stage1 v4 + stage2 v7)

Vấn đề: CIC-IDS-2017 mất cân bằng khủng khiếp — Benign áp đảo, vài lớp tấn công hiếm.
Một model làm hết dễ bị "Benign hóa". Giải pháp: chia hai tầng như bệnh viện —
**phòng khám sàng lọc** trước, ca nghi ngờ mới chuyển **bác sĩ chuyên khoa**.

**Stage 1 — Gating (sàng lọc):**
```python
FTTransformer(num_features=~78, num_classes=coarse,
              d_model=128, num_layers=4, num_heads=8, dropout=0.2, drop_path_rate=0.1)
```
- Nhìn toàn bộ feature CICFlowMeter, phân loại thô (benign / nghi ngờ).
- `dropout=0.2` cao hơn GĐ1 (0.1) — dữ liệu CIC nhiều mẫu lặp, cần phanh mạnh hơn.

**Stage 2 — Expert (chuyên khoa), chỉ xử lý flow bị Stage 1 đánh dấu:**
```python
FTTransformer(num_features=34, num_classes=5,
              d_model=64, num_layers=3, num_heads=4, dropout=0.2, drop_path_rate=0.1)
# d_ff = 512 (mặc định ngầm, KHÔNG phải 256) — 356.165 tham số
```
- `num_features=34` — chỉ dùng 34 feature chọn lọc liên quan đến phân biệt loại tấn công
  (đã xác minh từ `STAGE2_FEATURES` + checkpoint; con số 29 trong bản cũ là SAI).
- `d_model=64, num_layers=3, num_heads=4` — model **nhỏ bằng nửa** Stage 1. Vì sao?
  Bài toán hẹp hơn + dữ liệu vào Stage 2 ít hơn nhiều → model to sẽ học vẹt.
  Nguyên tắc: kích thước model tỉ lệ với lượng dữ liệu và độ rộng bài toán.

**Stage 2 ensemble — thêm 2 model cổ điển đấu cùng FTT:**
```python
RandomForestClassifier(n_estimators=150, max_depth=25, max_features=20, class_weight='balanced')
KNeighborsClassifier(n_neighbors=16)
```
- Random Forest — rừng ngẫu nhiên: `n_estimators=150` = 150 cây quyết định bỏ phiếu;
  `max_depth=25` = mỗi cây hỏi tối đa 25 tầng câu hỏi (sâu hơn → nhớ cả nhiễu);
  `max_features=20` = mỗi lần rẽ nhánh chỉ được nhìn 20 feature ngẫu nhiên — ép các cây
  *khác nhau*, vì 150 cây giống hệt nhau thì bỏ phiếu vô nghĩa;
  `class_weight='balanced'` = lớp hiếm được nhân trọng số to lên, tránh bị lớp đông đè.
- KNN — láng giềng gần nhất: `n_neighbors=16` = nhìn 16 flow giống nhất trong tập train
  rồi theo đa số. k nhỏ (1–3) → nhạy nhiễu; k to (100) → bị lớp đông nuốt; 16 là điểm cân bằng tìm được.
- Ghi chú file `best_stage1_ema.pt`: EMA — Exponential Moving Average, tức bản "trung bình trượt"
  của weight qua các bước train. Weight cuối cùng hay rung lắc theo batch chót; bản EMA mượt hơn,
  thường generalize tốt hơn một chút.

Bài học GĐ2 mang sang GĐ3: kiến trúc cascade + kinh nghiệm chống mất cân bằng —
nhưng hệ thống cuối chọn 1 model đa lớp + Snort rule thay vì cascade 2 model.

## 4. FT-Transformer V2 — V8.5 / v8_7, hệ thống thật (GĐ3→5)

File: `Phase3_4_Retrain/v8/v8.5_Combined/v8_5_model.pt` (chính thức trong luận văn, Macro F1 91.7%)
và `live_detection/models/v8_7_model.pt` (bản live, FP 24.26% → 0.29%). Cùng kiến trúc, ~1.09M tham số.

```python
FTTransformer(num_features=80, num_classes=5,
              d_model=128, num_heads=8, num_layers=4,
              d_ff=512, dropout=0.15, drop_path_rate=0.15)
```

### Nhóm kích thước

- `num_features=80` — 80 feature thống kê của flow từ testbed → 80 token + 1 token `[CLS]`.
- `num_classes=5` — Benign, Brute Force, DoS, PortScan, Web Attack.
- `d_model=128` — mỗi feature được thổi thành vector 128 chiều. Là "độ rộng bàn làm việc":
  nhỏ hơn → thiếu chỗ biểu diễn sắc thái; to hơn → thừa tham số so với lượng dữ liệu → overfit.
- `num_heads=8` — 8 phiên thảo luận attention song song, mỗi phiên 128/8 = 16 chiều;
  mỗi đầu chuyên soi một kiểu tương tác (cặp tốc độ–kích thước gói, nhóm cờ TCP...).
- `num_layers=4` — 4 tầng: tầng đầu học tương tác đơn giản giữa cặp feature,
  tầng sau học tương tác-của-tương-tác. 4 là điểm cân bằng cho tabular (paper gốc dùng 3–6).
- `d_ff=512` — FFN nở 128→512→128 sau attention; quy ước chuẩn d_ff = 4×d_model.
  Attention lo "trao đổi giữa các feature", FFN lo "tiêu hóa" thông tin vừa nhận.

### Nhóm phanh chống overfit (nâng cấp V2 so với V1)

- `dropout=0.15` — tắt ngẫu nhiên 15% neuron mỗi bước train.
- `drop_path_rate=0.15` — DropPath (Stochastic Depth): thỉnh thoảng tắt **nguyên một tầng**,
  cho dữ liệu đi tắt qua residual; tỉ lệ tăng dần theo độ sâu (tầng 1 ≈ 0, tầng 4 ≈ 0.15).
- **LayerScale** (khởi tạo 1e-4) — mỗi tầng lúc đầu chỉ đóng góp một lượng tí hon rồi tự học
  tăng dần, như vặn volume từ 0 lên từ từ → train ổn định.
- **GEGLU** thay ReLU trong FFN — activation có "cổng": nửa tính nội dung, nửa quyết định cho qua bao nhiêu.
- Classifier head: `[CLS]` → 128 → 64 → 5.

### Thông số train V8.5 (model chính thức)

- `FocalLoss(gamma=2.0, weight=class_weight_balanced, label_smoothing=0.10)` —
  γ=2: mẫu dễ (p=0.9) bị giảm trọng số còn (1−0.9)²=0.01, mẫu khó (p=0.3) giữ (1−0.3)²=0.49 —
  dồn sức học mẫu khó gấp ~50 lần; label smoothing 0.10 làm mềm nhãn cứng để model bớt tự tin mù quáng.
- `AdamW(weight_decay=2e-4)` + `CosineAnnealingLR(T_max=15)` — LR giảm dần hình cosine:
  đầu bước dài tiến nhanh, cuối bước ngắn đáp nhẹ vào đáy loss.
- `EPOCHS=15, batch_size=256`, early stopping — V8.4 hội tụ ở epoch 3 nên 15 là dư.
- Dataset: mix testbed (hydra, nmap) + CIC (Patator, PortScan) — bài học lớn nhất của v8:
  **val set đa dạng domain thì metric mới thật** (V8.4 đạt 94.95% nhưng inflate vì val toàn CIC).

### Thông số fine-tune v8_7 (bản live)

Khác biệt cốt lõi: **layer-wise learning rate** — tu sửa nhà tốt sẵn, không đập móng:

- backbone (embedding + tầng 1–2): `lr = 1e-5` (gần đóng băng)
- tầng giữa (3–4): `lr = 1.5e-5`
- classifier head: `lr = 3e-5` (chỉnh mạnh nhất, gấp 3 backbone)

Cộng thêm: train tối đa 25 epoch, early stop patience 6, và mỗi epoch đo **FPR trên tập benign
THẬT held-out** (không train trên nó) — tiêu chí dừng gắn thẳng với "ngoài đời có báo động nhầm không".

---

## Tóm lại — bức tranh một dòng cho từng model

- **NSL-KDD FTT V1**: chứng minh khái niệm, mốc so sánh F1 0.681 — khung 128/8/4/512, chỉ có dropout.
- **Autoencoder Gate**: đồng hồ cát 122→16→122, điểm bất thường = MSE tái tạo, ngưỡng chọn bằng ROC.
- **CIC cascade**: sàng lọc (FTT to) → chuyên khoa (FTT nhỏ 64/4/3 + RF 150 cây + KNN k=16) —
  bài học "model nhỏ cho bài toán hẹp" và ensemble.
- **V8.5 / v8_7 (hệ thống thật)**: FTT V2 80→5, thêm 5 lớp phanh (dropout, DropPath, LayerScale,
  label smoothing, weight decay), Focal Loss γ=2, fine-tune layer-wise LR, dừng theo FPR benign thật.

## Ứng dụng khi bảo vệ

Khi hội đồng chỉ vào bất kỳ thông số nào, trả lời theo khuôn 3 vế:
**"nó giải quyết vấn đề X — to hơn thì bị Y — nhỏ hơn thì bị Z."**
Ví dụ: bottleneck 16 của autoencoder (to → copy nguyên đầu vào, nhỏ → báo động loạn);
k=16 của KNN (nhỏ → nhạy nhiễu, to → lớp đông nuốt lớp hiếm); d_model=128 (nhỏ → thiếu chỗ
biểu diễn tương tác, to → overfit với lượng dữ liệu hiện có).
