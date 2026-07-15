# BẢN TỔNG HỢP BẢO VỆ — ĐÚNG 9 MODEL CÓ TRONG QUYỂN

> **Phạm vi:** chỉ các version **thực sự được đưa vào quyển đồ án** (Phụ lục B.1.1 → B.1.9,
> Chương 3, Chương 5). Các version thử nghiệm khác (v8.1–v8.4, v8.6, v8.7, temperature scaling,
> hiệu chỉnh live) **không nằm trong quyển** → không trình bày, chỉ có một ghi chú ngắn ở Phần 9
> để không bị bất ngờ.
>
> **Nguồn:** đọc thẳng **code + checkpoint thật** (load `state_dict`, đọc shape weight, đọc encoder
> pickle). Mọi con số đã xác minh, trừ chỗ đánh dấu ⚠️.
>
> **Khuôn trả lời hội đồng — 3 vế:**
> *"Tham số này giải quyết vấn đề X — to hơn thì bị Y — nhỏ hơn thì bị Z."*
> Người thuộc số sẽ chết ở câu hỏi thứ hai. Người hiểu vấn đề thì không.

---

# PHẦN 0 — ÁNH XẠ: MỤC TRONG QUYỂN ↔ CODE ↔ CHECKPOINT

| Mục quyển | Model | File code thật | Checkpoint | **Đã xác minh** |
|---|---|---|---|---|
| **B.1.1** | NSL-KDD — Autoencoder Gate | `MLAnomalyDetection/AutoencoderTrain.py` | `autoencoder_v2_best.h5` | 122→128→64→32→**16**→32→64→128→122 |
| **B.1.2** | NSL-KDD — FT-Transformer | `train_ft_transformer_nslkdd.py` | `v9_u2r_val_fix_seed42/best_model.pt` | 122 feat, **5 lớp**, 841.732 tham số |
| **B.1.3** | NSL-KDD — LightGBM | `train_lightgbm_ensemble.py` | `v11_lgbm_ensemble_seed42/lgbm_model.txt` | 5 lớp |
| **B.1.4** | NSL-KDD — Meta-LR | `stacking_ensemble.py` | `v12_stacking_seed42/` | input 10 chiều |
| **B.1.5** | CIC — Stage 1 Gating | `phase2_train_v4_stage1.py` | `v4_cascade/stage1/best_stage1_model.pt` | 77 feat, **6 lớp**, 1.087.302 tham số |
| **B.1.6** | CIC — Stage 2 Expert | `phase2_train_v7_stage2_ensemble.py` | `v7_cascade/stage2/best_stage2_ema.pt` | **34** feat, **5 lớp**, 356.165 tham số |
| **B.1.7** | CIC — Random Forest | (cùng file trên) | `best_rf_model.pkl` | 150 cây |
| **B.1.8** | CIC — KNN | (cùng file trên) | `best_knn_model.pkl` | k=16 |
| **B.1.9** | Testbed **V8.5** | `v8/v8.5_Combined/v8_5_train.py` | `v8_5_model.pt` | 80 feat, **5 lớp**, **1.088.005** tham số |
| — | *(không phải model)* Ghép hệ thống | `evaluate_cascade_system_v7.py` | — | Luật voting cascade — **là LUẬT, không có tham số học** |

## 📊 ĐẾM CHO CHUẨN — hội đồng rất hay hỏi "đồ án của em có bao nhiêu mô hình?"

**Trả lời: 9 mô hình** — mỗi cái có **checkpoint/artifact riêng**, đúng bằng số mục B.1.1 → B.1.9.

| Giai đoạn | Số model | Gồm những gì |
|---|---|---|
| **GĐ1 — NSL-KDD** | **4** | Autoencoder Gate · FT-Transformer · LightGBM · Meta-LR |
| **GĐ2 — CIC-IDS-2017** | **4** | Stage 1 FTT · Stage 2 FTT · Random Forest · KNN |
| **GĐ3 — Testbed** | **1** | **V8.5** |
| | **= 9** | |

**Hai cách đếm khác — biết để không bị bắt bẻ:**
- **Đếm theo "khối kiến trúc"** thì ra **7**: gộp Stage 2 (FTT + RF + KNN) thành *một khối ensemble*.
  → Nếu bạn nói "7", phải nói rõ *"7 khối, trong đó khối Expert gồm 3 model bỏ phiếu"*.
- **Đếm theo "model học sâu"** thì chỉ có **4**: FTT NSL-KDD · FTT Stage 1 · FTT Stage 2 · V8.5.
  (AE là mạng nơ-ron nhưng **không giám sát**; LightGBM/RF/KNN/Meta-LR là **machine learning cổ điển**.)

**An toàn nhất khi bị hỏi:**
> *"**Chín mô hình**, chia theo ba giai đoạn: 4 ở NSL-KDD, 4 ở CIC-IDS-2017, 1 ở Testbed.
> Trong đó có **4 mô hình học sâu** (FT-Transformer) — và **chỉ mô hình cuối, V8.5, là hệ thống triển khai thật**.
> Tám cái còn lại là các bước xây dựng và kiểm chứng dẫn tới nó."*

Câu cuối rất quan trọng: nó **chặn trước** câu hỏi *"sao lắm model thế, dùng cái nào?"*.

---

## 🏷️ QUY ƯỚC TÊN — [giai đoạn ↔ dataset ↔ model], phải thống nhất TRƯỚC KHI BẢO VỆ

**Vấn đề (thầy/cô đã cảnh báo):** quyển gọi giai đoạn 2 là **"CIC"** (theo *tên dataset*), nhưng lại gọi
giai đoạn 3 là **"Testbed"** — trong khi **V8.5 KHÔNG được train thuần trên testbed**. Cách gọi lẫn lộn
giữa **tên-theo-dataset** và **tên-theo-giai-đoạn** khiến người nghe không biết CIC nằm ở đâu.

### Bằng chứng: `Combined_V8_5.csv` thật ra là dataset TRỘN (đọc từ `build_dataset_v8_5.py`)

| Lớp | Từ **Testbed** (Run10, tự thu qua WSL2) | Từ **CIC-IDS-2017** | Tổng |
|---|---|---|---|
| Benign | 51.994 | 0 | 51.994 |
| DoS | 19.781 | 0 | 19.781 |
| Web Attack | 24.887 | 2.180 (Thursday) | 27.067 |
| Brute Force | 2.984 (hydra) | **4.999 (Patator)** | 7.983 |
| PortScan | **0** | **5.000 (Friday)** | 5.000 |
| **Tổng** | **~99.646 (89%)** | **~12.179 (11%)** | **111.825** |

**→ V8.5 là model của giai đoạn 3, nhưng dữ liệu train của nó:**
- **PortScan: 100% từ CIC** (testbed không thu được PortScan sạch — đây cũng là gốc rễ vấn đề PortScan ở live).
- **Brute Force: 63% từ CIC** (Patator) + 37% testbed (hydra).
- **Benign, DoS: 100% testbed.**

→ **Gọi V8.5 là "model Testbed thuần" là SAI.** Nó là **model trên dữ liệu TRỘN MIỀN, testbed chiếm đa số**.
🔴 Chú ý: docs cũ có chỗ gọi cả `Combined_V8_5` là **"CIC"** (BUOC5_KETQUA) — **cũng sai theo hướng ngược lại**.

### Bảng quy ước ĐỀ NGHỊ — dùng nhất quán trong slide + quyển

| | **Tên giai đoạn (nên dùng)** | **Dataset thật** | **Model xuất ra** | Chỗ dễ nhầm — nói sao cho đúng |
|---|---|---|---|---|
| **GĐ1** | "NSL-KDD" hoặc "GĐ khả thi" | NSL-KDD (benchmark 1999) | AE Gate, FTT, LightGBM, Meta-LR | *Tên dataset = tên giai đoạn* → không nhầm |
| **GĐ2** | "CIC-IDS-2017" hoặc "GĐ quy mô lớn" | CIC-IDS-2017 (benchmark 2017) | Cascade (S1, S2, RF, KNN) | *Tên dataset = tên giai đoạn* → không nhầm |
| **GĐ3** | **"Testbed thật" / "GĐ triển khai"** — **KHÔNG gọi tắt là 'Testbed thuần'** | **`Combined_V8_5`** = testbed (89%) **+ CIC injected** (11%, cho PortScan & Brute Force) | **V8.5** | ⚠️ *Tên giai đoạn ≠ tên dataset.* Phải nói: *"dữ liệu chủ yếu tự thu, **bổ sung CIC cho 2 lớp testbed không thu đủ**"* |

**Câu chuẩn cho slide GĐ3:**
> *"Giai đoạn 3 huấn luyện trên **dữ liệu testbed tự thu là chính** (Benign, DoS, phần lớn Web Attack/Brute Force),
> **bổ sung dữ liệu CIC-IDS-2017 cho hai lớp mà testbed không thu đủ**: PortScan (toàn bộ) và một phần Brute Force.
> Đó là lý do dataset tên là **`Combined`** — trộn miền có chủ đích. Model kết quả là **V8.5**."*

**Nếu hội đồng hỏi *"sao gọi Testbed mà lại có CIC trong đó?"*:**
> *"Vì testbed WSL2 của em **không tạo được PortScan sạch** (nmap qua NAT cho ra flow SYN đơn không đặc trưng),
> nên em inject 5.000 mẫu PortScan từ CIC để lớp này có đủ dữ liệu học. Em gọi giai đoạn là 'Testbed' theo
> **mục tiêu** (thích nghi môi trường thật), còn dataset là **'Combined'** theo **thành phần** — hai tên cho
> hai thứ khác nhau, và em thống nhất dùng đúng như vậy."*

**Lớp thật (đọc từ `encoder_*.pkl`):**
- Stage 1: `['Benign', 'Brute Force', 'DDoS', 'DoS', 'PortScan', 'Suspicious']` → **6**
- Stage 2: `['Benign', 'Bot', 'Heartbleed', 'Infiltration', 'Web Attack']` → **5**
- V8.5: `['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']` → **5**

## 🔴 5 chỗ QUYỂN ĐANG SAI so với code — sửa trước khi in

| # | Mục | Quyển viết | **Sự thật (verified từ checkpoint)** |
|---|---|---|---|
| 1 | B.1.5 / B.1.6 / Ch.3.3 | Stage 1 **nhị phân**, Stage 2 phân **9 lớp** | Stage 1 = **6 lớp**, Stage 2 = **5 lớp**. Sửa lại thì **lập luận mạnh hơn** — xem Phần 2 |
| 2 | Ch.3.3.4 | Ngưỡng 0,85 *"ưu tiên recall tấn công"* | **NGƯỢC HẲN.** Code ép flow nghi ngờ có `p < 0,85` **về Benign** → nó **giảm false positive** |
| 3 | Ch.3.3.7 + Hình 3.7 | *"Botnet: AND of 3"*, *"Majority Vote cho lớp còn lại"* | **Không có majority vote nào trong code.** FTT làm chủ; RF/KNN chỉ **veto** 2 lớp Bot + Infiltration |
| 4 | B.1.1 / Ch.3.2.2 | AE `122→64→32→16`; ngưỡng = **percentile 95** | AE có **thêm tầng 128**; ngưỡng = **ROC Youden trên tập TRAIN** (percentile 95 là bản **legacy**, không phải bản chạy) |
| 5 | B.1.9 | dropout 0,2 · GELU · AdamW lr=1e-4 · 50 epoch (patience 7) | **dropout 0,15 · GEGLU · layer-wise LR 1e-5/1,5e-5/3e-5 · 15 epoch (patience 5)**. **B.1.9 tự mâu thuẫn với Chương 3.4.5 — Ch.3.4.5 mới đúng** |

**Thêm 2 lệch nhỏ:** B.1.6 ghi `d_ff=256` → thật là **512** (giá trị mặc định ngầm; checkpoint có shape `(1024, 64)` = 2×512 do GEGLU). B.1.7 ghi RF `class_weight='balanced_subsample'` → code là **`'balanced'`**. B.1.8 ghi KNN `weights='distance'` → code là **`'uniform'`** (mặc định).

**Và một con số PHẢI BỎ:** *"1-stage baseline 0,7831"* — ⚠️ **không tìm thấy nguồn gốc trong repo.**
Chuỗi có thật trong docs là **V5 0,6065 → V6 0,9160 → V7 0,9294**. **Đừng nói 0,7831 khi bảo vệ.**

---
---

# PHẦN 1 — GIAI ĐOẠN 1: NSL-KDD (4 model)

> **Câu hỏi của giai đoạn:** *Transformer — vốn sinh ra cho chuỗi ngôn ngữ — có hoạt động được trên
> dữ liệu bảng (tabular) của IDS không?*
>
> **Câu trả lời trung thực trong quyển:** *Có, nhưng **thua LightGBM**. Phải kết hợp mới thắng.*
> **Kết quả cuối GĐ1: Macro F1 = 0,6809** (B.2.1).

## 1.0 Dữ liệu — vì sao 122 đặc trưng

41 cột gốc NSL-KDD. Ba cột chữ được **one-hot encode**:

| Nhóm | Index | Số cột |
|---|---|---|
| Đặc trưng số | 0–37 | 38 |
| `protocol_type` (tcp/udp/icmp) | 38–40 | 3 |
| `service` (http, ftp, smtp…) | 41–110 | **70** |
| `flag` (SF, REJ, S0…) | 111–121 | 11 |
| | | **= 122** |

*(Ranh giới 38/41/111/122 là **hardcode** trong `phase2_ft_transformer.py:132-137`.)*

Nhãn gom 5 nhóm: `Normal, DoS, Probe, R2L, U2R`. **Scaler: MinMaxScaler** (ép về [0,1]).

---

## 1.1 MODEL B.1.1 — AUTOENCODER GATE (Tầng 1)

### Vấn đề nó giải quyết
Classifier chỉ biết các lớp đã học. **Tấn công lạ hoàn toàn thì sao?**
→ Học **nén rồi tái tạo** traffic *bình thường*. Gặp thứ chưa từng thấy → tái tạo dở → **lỗi tái tạo cao** → nghi ngờ.

> **So sánh:** người thủ thư thuộc lòng cách xếp sách của thư viện mình. Đưa cuốn sách quen, họ đặt lại
> đúng chỗ ngay (lỗi thấp). Đưa một vật thể lạ, họ lúng túng (lỗi cao) → chuông reo.

### Kiến trúc THẬT (đọc trực tiếp weight trong `.h5`)

```
122 → 128 → 64 → 32 → [16] → 32 → 64 → 128 → 122
      ── encoder (nén) ──  cổ chai  ── decoder (giải nén) ──
```

🔴 **Quyển ghi `122 → 64 → 32 → 16` — THIẾU HẲN TẦNG 128** ở cả encoder lẫn decoder. Phải sửa.

- Activation: `relu` các tầng giữa, **`sigmoid`** tầng cuối (ép đầu ra về [0,1], khớp MinMaxScaler).
- Loss = **MSE** (xem mục ngay dưới — đây là mảnh quan trọng nhất của model này).
- `optimizer='adam'`, `epochs=100`, `batch_size=256`, `validation_split=0.1`
- `EarlyStopping(monitor='loss', patience=**5**, restore_best_weights=True)` — 🔴 **quyển ghi patience=10**

### ⭐ MSE ở đây là gì — **KHÔNG phải MSE mà bạn quen**

Đây là chỗ dễ nhầm nhất, và là câu hỏi hội đồng rất dễ hỏi.

MSE quen thuộc = sai số giữa **dự đoán** và **nhãn**. Nhưng Autoencoder **không dự đoán nhãn**.
Nó nhận một flow 122 chiều, **nén xuống 16 chiều rồi bung ngược lại 122 chiều**. Đầu ra $\hat{x}$ là
**bản vẽ lại của chính đầu vào** $x$.

→ MSE ở đây là **lỗi tái tạo (reconstruction error)**: **so đầu vào với chính bản sao chép của nó.**

$$\text{MSE}(x) = \frac{1}{122}\sum_{j=1}^{122}\big(x_j - \hat{x}_j\big)^2$$

**Bóc từng mảnh:**
- $x_j$ — giá trị **thật** của đặc trưng thứ $j$ (đã MinMax về [0,1]).
- $\hat{x}_j$ — giá trị mà autoencoder **đoán lại** cho đặc trưng đó, **sau khi đã đi qua cổ chai 16 chiều**.
- **Bình phương** — vừa bỏ dấu (lệch lên hay lệch xuống đều là lệch), vừa **phạt nặng sai lệch lớn**:
  lệch 0,4 bị phạt gấp **4 lần** lệch 0,2, chứ không phải gấp 2.
- **Chia 122** — lấy **trung bình**, để con số không phụ thuộc số đặc trưng → nhờ vậy **một ngưỡng cố định
  mới có ý nghĩa**.

**Trong code:**
```python
mse = np.mean(np.power(X_test - X_test_pred, 2), axis=1)
```
`axis=1` = trung bình **theo hàng** → **mỗi flow ra đúng MỘT con số MSE riêng**.
**Con số đó chính là điểm bất thường (anomaly score) của flow đó.**

#### Ví dụ số (rút gọn còn 3 đặc trưng cho dễ thấy)

| Đặc trưng | $x$ (thật) | $\hat{x}$ (tái tạo) | lệch | bình phương |
|---|---|---|---|---|
| `duration` | 0,10 | 0,12 | +0,02 | 0,0004 |
| `src_bytes` | 0,30 | 0,28 | −0,02 | 0,0004 |
| `count` | 0,50 | **0,90** | **+0,40** | **0,1600** |

$$\text{MSE} = \frac{0{,}0004 + 0{,}0004 + 0{,}1600}{3} = 0{,}0536$$

Hai đặc trưng đầu tái tạo gần như hoàn hảo, nhưng **một đặc trưng lệch 0,4 đã kéo cả điểm số lên**.
Đúng ý đồ: autoencoder **chỉ học traffic bình thường**, nên gặp flow lạ nó sẽ **vẽ trượt ở đúng những chỗ lạ**.

#### 🎯 Cùng MỘT con số, HAI vai trò — nói câu này ở buổi bảo vệ

| Lúc nào | MSE đóng vai gì |
|---|---|
| **Khi TRAIN** | **Hàm mất mát** — model tự chỉnh trọng số để vẽ lại benign cho **giống nhất** (MSE → nhỏ nhất) |
| **Khi CHẠY THẬT** | **Điểm nghi ngờ** — flow nào vẽ lại càng **dở** thì càng **đáng ngờ** (MSE ≥ τ → Suspicious) |

> *"Cùng một công thức, đổi vai trò từ **thứ cần tối thiểu hóa** sang **thứ cần đo**."*

#### Đọc con số ngưỡng τ = 0,008481 cho CÓ NGHĨA

Bản thân 0,008481 nghe rất trừu tượng. **Lấy căn bậc hai để về cùng đơn vị với dữ liệu:**

$$\sqrt{0{,}008481} \approx 0{,}092$$

→ *"Một flow bị coi là đáng ngờ khi **trung bình mỗi đặc trưng bị vẽ trượt hơn ~9,2%** trên thang [0,1]."*

**Trả lời được câu này = hiểu con số, không phải thuộc con số.**

#### ⚠️ Giới hạn của phép lấy trung bình — câu hỏi hội đồng có thể đâm

Vì MSE là **trung bình trên 122 chiều**, một đặc trưng sai nặng sẽ **bị 121 đặc trưng đúng PHA LOÃNG**.

Cụ thể: nếu dữ liệu nằm gọn trong [0,1], sai lệch tối đa của **một** đặc trưng là 1,0, đóng góp:
$$\frac{1^2}{122} = 0{,}0082 \;<\; \tau = 0{,}008481$$

→ **Về nguyên tắc, MỘT đặc trưng đơn lẻ dù sai hết cỡ cũng KHÔNG đủ kéo chuông.** Phải có **ít nhất hai**
đặc trưng lệch nặng.

**Đây không hẳn là lỗi** — nó là **đặc tính chống nhiễu có chủ đích**: một đặc trưng dị thường lẻ thì
chưa đủ để kết luận.

**Nếu bị hỏi *"tấn công chỉ làm méo đúng một đặc trưng thì sao?"*:**
> *"Autoencoder gate sẽ **bỏ sót** — và đó chính là lý do nó chỉ là **tầng lọc THÔ**. Phía sau còn
> classifier, và ở giai đoạn cuối còn Snort. **Không tầng nào một mình đủ cả** — đó là toàn bộ lý do
> hệ thống phải lai."*

**Lưu ý chính xác:** MinMaxScaler được fit trên `KddTrain+`, nên trên `KddTest+` có thể xuất hiện giá trị
**vượt ngoài [0,1]** (giá trị lớn hơn mọi thứ từng thấy khi train). Khi đó sai lệch của một đặc trưng
**có thể lớn hơn 1** → chính cơ chế này góp phần làm MSE của các flow tấn công lạ **vọt lên**.

### Bottleneck = 16 — thông số quan trọng nhất

| | Hậu quả |
|---|---|
| **To quá** (vd 100) | Model chỉ việc **copy nguyên đầu vào** → tái tạo cái gì cũng tốt → **mất hoàn toàn khả năng phát hiện** |
| **Nhỏ quá** (vd 2) | Tái tạo cái gì cũng dở, kể cả benign → **báo động loạn** |
| **16/122 ≈ nén 7,6 lần** | Đủ chật để ép model chỉ giữ được "bản chất" của traffic bình thường |

### Quy trình chọn ngưỡng τ — **phải nói đúng, đây là chỗ dễ bị bắt lỗi**

1. `MinMaxScaler` fit trên `KddTrain+`.
2. Train autoencoder **CHỈ trên các mẫu Normal** của `KddTrain+`.
3. Tính MSE trên **toàn bộ `KddTrain+`** (cả Normal lẫn Attack).
4. Chọn ngưỡng bằng **ROC Youden trên chính tập train đó**:
   $$\tau^{*} = \arg\max_{\tau}\ \big(TPR(\tau) - FPR(\tau)\big)$$
5. **Đánh giá** trên `KddTest+` — tập test thật, chưa từng đụng vào.

→ **KHÔNG rò rỉ dữ liệu test.** Ngưỡng sinh từ train, đo trên test. **Đây là phương pháp ĐÚNG.**

**Chỉ số Youden J** = $TPR - FPR$: điểm trên đường ROC **xa đường chéo ngẫu nhiên nhất**.
Nói nôm na: *"chỗ bắt được nhiều tấn công nhất trong khi báo nhầm ít nhất."*

🔴 **Quyển ghi "percentile 95 của Normal train errors"** — đó là bản **legacy v1**, không phải bản đang chạy.
Giá trị **τ = 0,008481** thì khớp, **nhưng lý do sinh ra nó thì quyển kể sai.**

### Tham số fix cứng
`autoencoder_threshold = 0,008481` (trong `inference_config.json`) — **giá trị đông cứng từ một lần chạy ROC**.
Nó gắn chặt với scaler và tập train lúc đó → **đổi dữ liệu là phải fit lại.**

---

## 1.2 MODEL B.1.2 — FT-TRANSFORMER (V1)

> **Phần này chỉ trình bày ĐÚNG những lựa chọn có trong quyển (B.1.2).**
> Những lựa chọn **chỉ tồn tại trong code** (sampler, SMOTE, mixup, multi-seed, ngưỡng gap…)
> **KHÔNG nằm trong quyển** → được tách hẳn xuống **mục 1.2-PL** ở cuối, chỉ dùng khi hội đồng mở code hỏi.
> **Đừng chủ động nhắc chúng.**

### Cấu hình theo quyển (B.1.2) — **học thuộc đúng bảng này**

| Tham số | Giá trị (quyển) | **Nó giải quyết vấn đề gì — to hơn thì sao, nhỏ hơn thì sao** |
|---|---|---|
| Số features đầu vào | **122** | 41 cột gốc, one-hot 3 cột chữ → 38 + 3 + 70 + 11 = 122 |
| Số lớp đầu ra | **5** (Normal, DoS, Probe, R2L, U2R) | |
| `d_model` | **128** | "Độ rộng bàn làm việc" — mỗi đặc trưng được thổi thành vector 128 chiều. **Nhỏ hơn** → thiếu chỗ biểu diễn sắc thái tương tác; **to hơn** → thừa tham số so với lượng dữ liệu → overfit |
| `n_heads` | **8** | 8 phiên thảo luận attention song song, mỗi phiên $128/8 = 16$ chiều. **Ít đầu** → chỉ soi được một kiểu tương tác; **nhiều đầu** → mỗi đầu quá hẹp (16 chiều đã khá mỏng) |
| `n_layers` | **4** | Tầng đầu học tương tác **cặp** đặc trưng; tầng sau học **tương-tác-của-tương-tác**. **Nông hơn** → không bắt được quan hệ bậc cao; **sâu hơn** → khó train, thừa với dữ liệu bảng (paper gốc dùng 3–6) |
| `d_ff` | **512** | FFN nở $128 \to 512 \to 128$. Quy ước chuẩn $d_{ff} = 4 \times d_{model}$. Attention lo *"trao đổi giữa các đặc trưng"*, FFN lo *"tiêu hóa"* thông tin vừa nhận |
| `Dropout` | **0,1** | **V1 chỉ có MỘT lớp phanh chống overfit duy nhất** (V2 ở GĐ2/GĐ3 sẽ thêm DropPath, LayerScale, label smoothing). **Cao hơn** → model học chậm, underfit trên dữ liệu nhỏ; **thấp hơn** → overfit |
| `Activation` | **GELU** | Mượt hơn ReLU (không gãy khúc tại 0) → gradient ổn định hơn |
| `Normalization` | **Pre-LN** | LayerNorm đặt **TRƯỚC** attention (`x + attn(norm(x))`), không phải sau như Transformer gốc. **Nhờ Pre-LN mà train sâu ổn định KHÔNG cần warmup** |
| `Loss` | **Focal Loss (γ = 2)** | Dồn sức học mẫu khó — xem mục (f) |
| `Optimizer` | **AdamW** (lr = 1e-4, weight_decay = 1e-5) | AdamW tách weight decay khỏi gradient → regularization đúng nghĩa |
| `Scheduler` | **CosineAnnealingLR** | LR giảm theo hình cosine: **đầu bước dài tiến nhanh, cuối bước ngắn đáp nhẹ vào đáy loss** |
| `Epochs` | **50** (Early Stopping patience = 5) | |
| `Batch size` | **256** | **Nhỏ hơn** → gradient nhiễu, train chậm; **to hơn** → gradient mượt nhưng dễ kẹt ở điểm yên ngựa |

Kiến trúc tương ứng:
```python
FTTransformer(num_features=122, num_classes=5,
              d_model=128, num_heads=8, num_layers=4, d_ff=512, dropout=0.1)
# 841.732 tham số | classifier: Linear(128,128) → GELU → Dropout → Linear(128,5)
```

### Lý thuyết bên trong — cách hoạt động

#### (a) Feature Tokenizer — "mỗi đặc trưng là một từ" ⭐ **mảnh quan trọng nhất cả đồ án**

```python
self.feature_projections = nn.ModuleList([nn.Linear(1, d_model) for _ in range(122)])
```

Mỗi đặc trưng $x_j$ (một con số) được chiếu thành vector 128 chiều **bằng một Linear RIÊNG của nó**:
$$t_j = \mathbf{w}_j \cdot x_j + \mathbf{b}_j \in \mathbb{R}^{128}$$

- 122 đặc trưng → 122 token + 1 token `[CLS]` học được → chuỗi dài 123.
- **Vì sao mỗi đặc trưng một Linear riêng, không dùng chung?** Vì `duration=100` và `src_bytes=100` là
  **hai chuyện hoàn toàn khác nhau**. Dùng chung ma trận thì con số 100 bị mã hóa giống hệt nhau.
  Mỗi đặc trưng cần "ngôn ngữ" riêng.
- **Hệ quả sống còn — nói câu này ở buổi bảo vệ:** vì embedding là **122 hàng độc lập**, sang giai đoạn 3
  muốn thêm 3 đặc trưng chỉ cần **ghép thêm 3 hàng** → đó là **Model Surgery**.
  **Nếu chọn MLP thường (một Linear chung trộn hết đặc trưng ngay tầng đầu) thì Model Surgery BẤT KHẢ THI.**

#### (b) Multi-Head Self-Attention — "các đặc trưng nói chuyện với nhau"

$$\text{Attention}(Q,K,V)=\text{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right)V$$

Bóc từng mảnh:
- $Q$ (query) — *"tôi đang tìm thông tin gì?"* · $K$ (key) — *"tôi chứa thông tin gì?"*
- $QK^{\top}$ — điểm số **đặc trưng $i$ liên quan đặc trưng $j$ bao nhiêu**. Đây chính là thứ mà cây quyết
  định phải chẻ nhánh nhiều lần mới học được, còn attention học **trực tiếp trong một phép nhân ma trận**.
- $\sqrt{d_k}$ — chia để chống "điểm số phình to". Với $d_k = 128/8 = 16$, tích vô hướng 16 chiều có phương
  sai ~16 → không chia thì softmax **bão hòa**, gradient chết.

  **Ví dụ số:** $q\cdot k = 40$, các cặp khác ≈ 0.
  Không chia: $\text{softmax}(40,0,0)\approx(1{,}0\ ;\ 0\ ;\ 0)$ — cứng ngắc, **gradient ≈ 0**.
  Chia $\sqrt{16}=4$: $\text{softmax}(10,0,0)$ — vẫn nhọn nhưng **còn gradient để học**.
- `num_heads=8` → 8 phiên thảo luận song song, mỗi phiên 16 chiều. Một đầu chuyên soi cặp
  (tốc độ gói ↔ kích thước gói), đầu khác soi nhóm cờ TCP.

#### (c) Pre-LN residual
```python
x = x + dropout(attention(norm1(x)))    # LayerNorm TRƯỚC attention
x = x + dropout(ffn(norm2(x)))
```
Đây là **Pre-LN**, không phải Post-LN của Transformer gốc → train sâu ổn định mà không cần warmup.
Residual (`x + ...`) = đường tắt cho gradient chảy ngược, chống vanishing gradient.

#### (d) FFN `128 → 512 → 128`, activation **GELU**
Attention lo *"trao đổi giữa các đặc trưng"*; FFN lo *"tiêu hóa"* thông tin vừa trao đổi.
`d_ff = 4 × d_model` là quy ước chuẩn từ paper Transformer gốc.

#### (e) Token `[CLS]` — "thư ký cuộc họp" ⭐

**Vấn đề nó giải quyết:** sau 4 tầng attention, ta có **122 vector** (mỗi đặc trưng một vector 128 chiều).
Nhưng classifier chỉ cần **MỘT** vector để ra quyết định. **Ép 122 vector thành 1 — bằng cách nào?**

**Cách làm:** thêm **một token thứ 123** vào đầu chuỗi — nhưng token này **không tương ứng với đặc trưng nào cả**.
Nó là một **vector rỗng, học được** (`nn.Parameter`), khởi tạo ngẫu nhiên nhỏ ($\mathcal{N}(0; 0{,}02^2)$).

```python
self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))   # vector 128 chiều, HỌC ĐƯỢC
...
tokens = torch.stack([proj_j(x[:, j]) for j in range(122)])  # 122 token đặc trưng
return torch.cat([cls_token, tokens], dim=1)                 # → chuỗi dài 123
```

Sau đó chuỗi 123 token đi qua 4 tầng Transformer. Vì self-attention cho **mọi token nhìn thấy mọi token**,
token `[CLS]` được phép **"hỏi" cả 122 đặc trưng** ở mỗi tầng. Cuối cùng lấy **đúng vector đầu tiên**:

```python
x = self.final_norm(x)
return x[:, 0, :]          # ← chỉ lấy CLS, vứt 122 token còn lại
```

> **So sánh đời thường:** 122 đặc trưng là **122 người dự họp**, mỗi người biết một mảnh thông tin.
> `[CLS]` là **người thư ký** — **không mang thông tin gì lúc đầu** (vector rỗng), ngồi nghe suốt 4 vòng thảo
> luận, ghi lại **những gì đáng ghi**. Cuối buổi, sếp (classifier) **chỉ đọc biên bản của thư ký**,
> không hỏi lại từng người.

**Vì sao thư ký phải BẮT ĐẦU TỪ RỖNG?** Vì nếu nó mang sẵn nội dung, biên bản sẽ bị **thiên lệch** bởi định
kiến có sẵn thay vì bởi những gì thực sự được nói. Bắt đầu từ vector ~0 → **mọi thứ nó có đều là thứ nó
nghe được**, và trọng số "nghe ai nhiều hơn" là thứ nó **tự học trong quá trình train**.

##### Vì sao không dùng mean-pooling (lấy trung bình 122 token)?

| | Cách hoạt động | Vấn đề |
|---|---|---|
| **Mean-pooling** | $\frac{1}{122}\sum_j t_j$ | Coi **mọi đặc trưng quan trọng NGANG NHAU** và **cố định**. Nhưng với flow DoS thì `Flow_Duration` quan trọng, với PortScan thì `SYN_Flag_Count` quan trọng — **trọng số phải THAY ĐỔI theo từng flow** |
| **`[CLS]`** | Học trọng số qua attention | Trọng số **phụ thuộc chính flow đang xét** ($Q$ của CLS nhân với $K$ của từng đặc trưng) → **linh hoạt theo ngữ cảnh** |

**Ví dụ số:** giả sử 3 đặc trưng, sau attention token `[CLS]` tính ra trọng số
$\text{softmax}(q_{CLS} \cdot k_j)$:

| Flow | duration | src_bytes | SYN_count | CLS nghe ai |
|---|---|---|---|---|
| DoS (kéo dài bất thường) | **0,70** | 0,20 | 0,10 | Nghe **duration** là chính |
| PortScan (SYN dồn dập) | 0,05 | 0,15 | **0,80** | Nghe **SYN_count** là chính |

Mean-pooling sẽ **luôn** cho $(0{,}33 ; 0{,}33 ; 0{,}33)$ ở cả hai dòng — **mù trước sự khác biệt**.

##### Vì sao không lấy đại một token đặc trưng nào đó làm đại diện?
Vì token của `duration` **vẫn mang thiên hướng là "duration"** — nó bị neo vào đặc trưng gốc của mình.
`[CLS]` **không thuộc về đặc trưng nào**, nên nó **tự do** trở thành bất cứ bản tóm tắt nào có ích nhất.

##### Chốt một câu cho hội đồng
> *"`[CLS]` là một token **rỗng, học được**, không ứng với đặc trưng nào. Nhờ self-attention, nó **hỏi** cả 122
> đặc trưng và **tự học trọng số nên nghe ai nhiều hơn — theo TỪNG flow**. Đó là điều mean-pooling không làm
> được, vì mean cố định trọng số bằng nhau cho mọi mẫu."*

#### (f) Focal Loss (γ = 2) — **đúng như quyển ghi**

$$FL(p_t) = -\alpha_t\,(1-p_t)^{\gamma}\,\log(p_t), \qquad \gamma = 2{,}0$$

- $p_t$ — xác suất model gán cho **lớp đúng**. $p_t$ cao = model đã làm tốt mẫu này.
- $(1-p_t)^{\gamma}$ — **hệ số điều chỉnh**: mẫu càng dễ thì hệ số càng nhỏ → **đóng góp vào loss càng ít**.
- $\gamma$ — **nút vặn**. $\gamma = 0$ quay về Cross-Entropy thường.

**Ví dụ số:** mẫu dễ $p_t = 0{,}9$ → hệ số $(1-0{,}9)^2 = 0{,}01$; mẫu khó $p_t = 0{,}3$ → $(1-0{,}3)^2 = 0{,}49$.
→ **Mẫu khó được quan tâm gấp 49 lần mẫu dễ.**

**Vì sao cần nó ở đây?** NSL-KDD mất cân bằng nặng: Normal/DoS hàng chục nghìn mẫu, **U2R chỉ vài chục**.
Với Cross-Entropy thường, hàng vạn mẫu Normal dễ sẽ **át toàn bộ gradient**, model chỉ việc đoán "Normal"
là đã có loss thấp. Focal Loss **hạ trọng số của những mẫu dễ đó xuống**, buộc model phải nhìn vào U2R.

**To/nhỏ thì sao:** $\gamma$ **cao hơn** (3–5) → dồn quá mạnh vào mẫu khó, model **bỏ bê mẫu dễ** và mất ổn định;
$\gamma$ **thấp hơn** (0–1) → gần như Cross-Entropy, lớp hiếm lại bị đè.

---

## 📎 1.2-PL — PHỤ LỤC: những lựa chọn **CHỈ CÓ TRONG CODE**, không nằm trong quyển

> ⚠️ **KHÔNG chủ động trình bày phần này.** Nó chỉ dùng khi hội đồng **mở code ra hỏi**.
> Nêu ra mà không bị hỏi = tự mời họ đào vào chỗ quyển chưa viết.

### (A) Số lớp: quyển nói 5, sản phẩm triển khai lại là 4

Trong repo có **hai hệ thống NSL-KDD tách rời**:

| | Sản phẩm triển khai (`snort_two_stage_inference.py`) | **Thí nghiệm cho ra số 0,6809** (`stacking_ensemble.py`) |
|---|---|---|
| Kiến trúc | AE Gate + FTT **4 lớp** (DoS/Probe/R2L/U2R) | FTT **5 lớp** + LightGBM + Meta-LR — **phẳng, KHÔNG có AE Gate** |
| Bằng chứng | `inference_config.json`: `num_classes: 4` | `stacking_ensemble.py:25`: `CLASS_NAMES = ['Normal','DoS','Probe','R2L','U2R']` |

**Con số Macro F1 = 0,6809 ở B.2.1 đến từ cột PHẢI** — model stacking **5 lớp**, dự đoán thẳng cả `Normal`,
**KHÔNG đi qua AE Gate**. Nhưng quyển đang trình bày nó như kết quả của pipeline two-stage **có gate**.

**Nếu bị hỏi:** *"Số 0,6809 là của **biến thể Stacking 5 lớp**. AE Gate là **một biến thể triển khai khác**
(gate nhị phân + 4 lớp tấn công). Em trình bày tách bạch hai thứ."*
→ Nếu gộp làm một, hội đồng chỉ cần mở `inference_config.json` là thấy `num_classes: 4`.

### (B) Các cơ chế trong code mà quyển không ghi

| Cơ chế (chỉ có trong code) | Là gì |
|---|---|
| `focal-alpha = class-balanced` | $\alpha_t$ **không phải** $1/n_c$ thô, mà là **Effective Number** (Cui et al. 2019): $E_n = \dfrac{1-\beta^{\,n_c}}{1-\beta}$, $\alpha_c \propto \dfrac{1-\beta}{E_{n_c}}$. **Trực giác:** 1000 mẫu DoS **không** đáng giá gấp 1000 lần 1 mẫu U2R, vì các mẫu DoS **chồng lấn nhau** rất nhiều |
| `sampler = weighted` | `WeightedRandomSampler` — lấy mẫu theo $1/n_c$ khi tạo batch |
| `smote-strategy = custom` (k=5) | SMOTE sinh mẫu thiểu số bằng **nội suy** giữa một mẫu và láng giềng. **Chỉ trên train, không bao giờ trên val/test** |
| `mixup-alpha` | Trộn tuyến tính 2 mẫu + 2 nhãn |
| **Gap-based early stopping** | `--max-train-val-gap 0.12`, `--gap-patience 3` → dừng khi `train_f1 − val_f1 > 0,12` trong 3 epoch liên tiếp. **Chống overfit trực tiếp bằng khoảng cách train–val**, không chỉ dựa vào val loss |
| `seed = 42 / 52 / 62` | Chạy **nhiều seed** — điểm cộng về tính tái lập, **nên đưa vào quyển** |
| Epochs thực chạy | Runner ghi đè: **20 epoch, patience 6** — 🔴 quyển ghi **50 / patience 5** |

**Nếu hội đồng hỏi *"sao code khác quyển?"*:** *"Quyển ghi cấu hình **mặc định của script**; runner thí nghiệm
ghi đè một số giá trị. Em ghi nhận sai sót và sẽ đồng bộ lại Phụ lục B theo cấu hình **thực chạy**."*

---

## 1.3 MODEL B.1.3 — LIGHTGBM

```python
params = {
    'objective': 'multiclass', 'num_class': 5, 'metric': 'multi_logloss',
    'num_leaves': 127, 'learning_rate': 0.05, 'n_estimators': 1000,
    'min_child_samples': 5,                    # 🔴 quyển ghi 20
    'subsample': 0.8, 'colsample_bytree': 0.8,
    'reg_alpha': 0.1, 'reg_lambda': 1.0,       # 🔴 quyển thiếu
    'random_state': 42, 'n_jobs': -1,
}
# early_stopping(stopping_rounds=50)
# sample_weight = inverse-frequency (1/n_c, chuẩn hóa)
```

| Tham số | Ý nghĩa — to/nhỏ thì sao |
|---|---|
| `num_leaves=127` | LightGBM mọc **leaf-wise** (chọn lá có lỗi cao nhất để chẻ), khác XGBoost mọc level-wise. 127 lá ≈ độ sâu 7 nếu cây cân. To hơn → nhớ cả nhiễu |
| `learning_rate=0.05` | Mỗi cây chỉ sửa 5% sai số còn lại → đi chậm mà chắc; bù lại cần nhiều cây |
| `n_estimators=1000` + early stop 50 | Tối đa 1000 cây, dừng khi 50 vòng không cải thiện val logloss |
| `min_child_samples=5` | Một lá phải có ≥ 5 mẫu. **Rất thấp — CỐ Ý**, để lớp U2R (vài chục mẫu) còn có lá riêng. Cao hơn (20 như quyển ghi) → **U2R bị nuốt** |
| `reg_alpha=0.1` (L1) / `reg_lambda=1.0` (L2) | Phạt trọng số lá, chống overfit |

### ⚠️ CÁI BẪY PHẢI BIẾT TRƯỚC
`subsample=0.8` được đặt **nhưng KHÔNG đặt `subsample_freq`**. Trong LightGBM, **bagging chỉ kích hoạt khi
`subsample_freq > 0`** → trên thực tế **`subsample=0.8` KHÔNG có tác dụng gì**. Model đang train trên 100%
dữ liệu mỗi cây. (Quyển ghi `bagging_freq=5` — tức quyển đang mô tả một cấu hình **tốt hơn** cấu hình thật chạy.)

**Nếu bị hỏi:** *"Đây là lỗi cấu hình em đã tự phát hiện khi rà soát. Nó **không làm sai kết quả** — chỉ là
mất một cơ chế regularization. Quyển cần ghi đúng cấu hình **thực chạy**."*

---

## 1.4 MODEL B.1.4 — META-LOGISTIC REGRESSION (Stacking)

### ⭐ Vì sao phải Stacking — **có bằng chứng số, đây là điểm mạnh nhất của GĐ1**

Đọc `v11_lgbm_ensemble_seed42/ensemble_summary.json`:
```json
{ "lgbm_standalone_test_macro_f1": 0.6678,
  "ftt_v9_test_macro_f1":          0.6535,
  "best_ensemble_alpha":           1.0,        ← !!!
  "ensemble_test_macro_f1":        0.6678 }
```

**Đọc con số này cho đúng:** thử soft-voting $\alpha \cdot p_{LGBM} + (1-\alpha)\cdot p_{FTT}$, quét $\alpha$ từ 0→1
→ **$\alpha$ tối ưu = 1,0**, tức **vứt bỏ hoàn toàn FT-Transformer**.
**Trung bình có trọng số THẤT BẠI** — nó không tìm được cách kết hợp nào tốt hơn LightGBM đơn lẻ.

→ **Chính thất bại này biện minh cho Stacking.** Trung bình tuyến tính quá thô. Cần một **meta-learner
biết HỌC cách kết hợp**, chứ không phải một hằng số $\alpha$.

### Meta-learner

```python
X_meta = hstack([p_lgbm (5 chiều), p_ftt (5 chiều)])       # → 10 chiều
meta = LogisticRegression(solver='lbfgs', C=1.0,
                          max_iter=2000,                    # 🔴 quyển ghi 1000
                          class_weight='balanced', random_state=42)
meta.fit(X_meta_val, y_val)         # fit trên VAL → đánh giá trên TEST
```

### Kết quả thật (`v12_stacking_seed42/results.json`)

| Model | Macro F1 (KddTest+) |
|---|---|
| LightGBM đơn lẻ | 0,6678 |
| FT-Transformer đơn lẻ | 0,6535 |
| **Meta-LR stacking** | **0,6809** |
| Meta-LR + tinh chỉnh ngưỡng | 0,6809 *(không tăng thêm)* |

**Nói gì:**
> *"FT-Transformer đơn lẻ **THUA** LightGBM trên NSL-KDD — em báo cáo trung thực điều đó. Cây quyết định
> vẫn rất mạnh trên dữ liệu bảng nhỏ. Nhưng hai model **SAI KHÁC NHAU**: LightGBM giỏi ranh giới sắc,
> Transformer giỏi tương tác mượt. Meta-LR học được **nghe ai lúc nào** → 0,6809, cao hơn cả hai.
> Đây là lý do em **giữ cả hai** thay vì chọn một."*

### ⚠️ ĐIỂM YẾU PHẢI TỰ NÓI TRƯỚC
Tập val chia theo tỉ lệ riêng từng lớp, nhưng **U2R bị chặn cứng ở 5 mẫu**
(`per_class_val_max = {4: 5}`). Meta-LR được fit trên tập val đó → **nó học lớp U2R từ đúng 5 mẫu.**

> *"Đây là giới hạn của NSL-KDD: U2R chỉ có vài chục mẫu trong toàn bộ tập train. Em chặn ở 5 mẫu val để
> không rút cạn tập train của lớp hiếm nhất. Hệ quả là F1 của U2R có phương sai rất lớn — và đó **chính là
> lý do Macro F1 giai đoạn 1 chỉ đạt 0,68**. Nó cũng là một lý do em chuyển sang CIC-IDS-2017."*

**Trung thực thứ hai:** tinh chỉnh ngưỡng per-class bằng Nelder-Mead **không mang lại gì**
(ngưỡng hội tụ về 0 cho cả 5 lớp, F1 y hệt 0,6809). **Đừng khoe nó như một đóng góp.**

---

## 1.5 GIAI ĐOẠN 1 — NÊN NÓI GÌ

**Ba câu trên slide:**
1. *"Giai đoạn 1 trả lời câu hỏi khả thi: Transformer có ăn được dữ liệu bảng không."*
2. *"Trung thực: **có, nhưng thua LightGBM** (0,6535 vs 0,6678). Soft-voting **thất bại** ($\alpha^*=1{,}0$ —
   tức vứt bỏ Transformer). Chỉ **Stacking** mới thắng cả hai: **0,6809**."*
3. *"Nhưng thứ giá trị nhất giai đoạn 1 bàn giao **không phải con số** — mà là **quyết định kiến trúc**:
   Feature Tokenizer với embedding-per-feature. Đó là thứ 2 giai đoạn sau cho phép **Model Surgery**."*

**Câu hỏi sẽ bị hỏi:**

| Hỏi | Trả lời |
|---|---|
| *"F1 0,68 thấp thế sao vẫn dùng?"* | *"0,68 là **Macro** F1 — nó phạt rất nặng lớp hiếm (U2R vài chục mẫu). Accuracy ~99%. Và GĐ1 **không phải hệ thống triển khai**, nó là bước chứng minh khả thi."* |
| *"Sao không dùng luôn LightGBM cho hệ cuối?"* | *"Vì **cây không làm được Model Surgery**. Sang testbed cần thêm 3 đặc trưng NAT — với cây phải train lại từ đầu, mà testbed lúc đó chỉ có ~37 flow benign."* |
| *"AE Gate có bắt được zero-day thật không?"* | *"Em **không** có bằng chứng zero-day thật. Nó bắt được **anomaly** — flow có lỗi tái tạo cao. Em báo cáo AUC trên NSL-KDD test, **không tuyên bố** khả năng zero-day."* |
| **"MSE ở đây là gì?"** | *"**Không phải** sai số giữa dự đoán và nhãn. Là **lỗi tái tạo**: so đầu vào 122 chiều với **bản vẽ lại của chính nó** sau khi qua cổ chai 16 chiều. Trung bình bình phương lệch trên 122 đặc trưng, **mỗi flow ra một con số** — và đó chính là **điểm bất thường**."* |
| *"τ = 0,008481 ở đâu ra? Nó nghĩa là gì?"* | *"ROC Youden — điểm $TPR-FPR$ lớn nhất — tính trên tập **train**, rồi đánh giá trên KddTest+. Về ý nghĩa: $\sqrt{0{,}008481}\approx 0{,}092$ → **flow đáng ngờ khi trung bình mỗi đặc trưng bị vẽ trượt hơn ~9,2%** trên thang [0,1]."* |
| *"Số 0,6809 là của pipeline nào?"* | *"Của **biến thể Stacking 5 lớp**, không đi qua AE Gate. Em trình bày tách bạch."* |

---
---

# PHẦN 2 — GIAI ĐOẠN 2: CIC-IDS-2017 CASCADE (4 model)

> **Câu hỏi:** *Kiến trúc này chịu nổi **quy mô lớn** (2,53 triệu flow) và **mất cân bằng cực đoan**
> (Benign ~80%, **Heartbleed 10 mẫu**) không?*
>
> **Kết quả trong quyển: Accuracy 99,55% · Macro F1 = 0,9294** (9 lớp).

## 2.0 FT-Transformer **V2** — kiến trúc nâng cấp (dùng chung cho GĐ2 và GĐ3)

> **Đây là kiến trúc của cả 3 model FT-Transformer còn lại trong đồ án** (Stage 1, Stage 2, V8.5).
> Hiểu kỹ mục này = trả lời được mọi câu hỏi kiến trúc của GĐ2 và GĐ3.

### Vì sao phải nâng cấp? — **đặt vấn đề trước, đừng liệt kê tính năng**

V1 (NSL-KDD) chạy trên **~125.000 flow**. V2 phải chạy trên **2,5 triệu flow, 9 lớp, mất cân bằng cực đoan**
(Benign 2 triệu ↔ Heartbleed **10 mẫu**). Bài toán đổi bản chất theo **hai hướng ngược nhau**:

| Sức ép mới | Hệ quả | V1 có chống được không? |
|---|---|---|
| **Dữ liệu to hơn 20 lần, nhiều mẫu lặp** | Model dễ **học vẹt** (overfit) | ❌ V1 chỉ có **một** lớp phanh: `dropout` |
| **Mạng phải đủ sâu để phân 9 lớp** | Tầng sâu → **train bất ổn**, gradient rung lắc | ❌ V1 không có cơ chế ổn định nào |
| **Lớp hiếm cần biểu diễn tinh vi** | FFN phải **lọc** được thông tin, không chỉ nén-nở | ❌ FFN của V1 là ReLU/GELU thuần, "cho qua tất" |

→ V2 thêm **3 cơ chế** trả lời đúng 3 sức ép trên (+ 1 thay đổi ở classifier head).
**Khung xương giữ nguyên** (`d_model=128`, `heads=8`, `layers=4`, `d_ff=512`) — **cố ý**, để so sánh được giữa
các giai đoạn.

### Bảng đối chiếu V1 ↔ V2 — **học thuộc bảng này**

| | **V1 (GĐ1 — NSL-KDD)** | **V2 (GĐ2 + GĐ3)** | Giải quyết sức ép nào |
|---|---|---|---|
| Chống overfit | `dropout` (1 lớp) | `dropout` + **DropPath** + (label smoothing ở tầng loss) | Dữ liệu to, nhiều mẫu lặp |
| Ổn định train | *(không có)* | **LayerScale** (init 1e-4) | Mạng sâu, gradient rung lắc |
| FFN | `Linear → GELU → Linear` | **`Linear → GEGLU → Linear`** (có cổng) | Lọc thông tin cho lớp hiếm |
| Classifier head | `Linear(d,d) → GELU → Drop → Linear(d,C)` | **`LayerNorm(d) → Linear(d, d/2) → GELU → Drop → Linear(d/2, C)`** | Gọn hơn, chuẩn hóa trước khi phân lớp |
| Attention | 3 Linear rời (`w_q`, `w_k`, `w_v`) | **1 Linear gộp** (`qkv`) | *(chỉ tối ưu tốc độ, không đổi toán học)* |
| Feature Tokenizer | ✅ giữ nguyên | ✅ **giữ nguyên** | ⭐ Nhờ vậy mới làm được **Model Surgery** ở GĐ3 |
| Pre-LN residual | ✅ giữ nguyên | ✅ giữ nguyên | |

**Câu chốt:** *"V2 không đổi **khung xương**, chỉ **thêm ba lớp phanh và một cơ chế lọc**.
Giữ nguyên khung là **có chủ đích** — đó là biến kiểm soát để so sánh giữa các giai đoạn."*

---

### Một khối Transformer V2 trông như thế nào (đọc từ trên xuống)

```python
def forward(self, x):
    x = x + self.drop_path1( self.ls1 * self.attn(self.norm1(x)) )   # nhánh Attention
    x = x + self.drop_path2( self.ls2 * self.ffn (self.norm2(x)) )   # nhánh FFN
    return x
```

Đọc **từ trong ra ngoài** một dòng:

| Thứ tự | Thành phần | Vai trò |
|---|---|---|
| 1 | `norm1(x)` | **Pre-LN** — chuẩn hóa TRƯỚC khi tính (giữ từ V1) |
| 2 | `attn(...)` | Các đặc trưng "nói chuyện" với nhau |
| 3 | `self.ls1 * ...` | **LayerScale** — vặn nhỏ đóng góp của khối này |
| 4 | `drop_path1(...)` | **DropPath** — thỉnh thoảng **xóa sạch** cả khối |
| 5 | `x + ...` | **Residual** — đường tắt, luôn còn nguyên `x` để đi tiếp |

**Điểm mấu chốt về thiết kế:** cả **LayerScale** và **DropPath** đều **chỉ tác động lên NHÁNH PHỤ**,
không đụng vào đường residual `x`. Nghĩa là **dù nhân nhỏ đi (LayerScale) hay xóa sạch (DropPath), tín hiệu
gốc vẫn chảy qua nguyên vẹn** → model không bao giờ bị "đứt mạch".

---

### (a) DropPath (Stochastic Depth) — "cho cả một TẦNG nghỉ"

```python
dpr = [x.item() for x in torch.linspace(0, drop_path_rate, num_layers)]
# num_layers=4, drop_path_rate=0.1 → dpr = [0.000, 0.033, 0.067, 0.100]
```

**Khác Dropout ở đâu?**

| | Tắt cái gì | Hình dung |
|---|---|---|
| **Dropout** | **Neuron lẻ** (15% số neuron trong một tầng) | Trong một phòng ban, **vài nhân viên** nghỉ phép |
| **DropPath** | **CẢ MỘT TẦNG** (với xác suất $p$, cả khối biến mất) | **Cả phòng ban** nghỉ, công việc **đi tắt** sang phòng sau |

Công thức thật (mỗi **mẫu** trong batch được quyết định riêng):
$$
\text{DropPath}(h) =
\begin{cases}
0 & \text{với xác suất } p \quad \text{(xóa sạch nhánh phụ)}\\[4pt]
\dfrac{h}{1-p} & \text{với xác suất } 1-p \quad \text{(giữ, nhưng KHUẾCH ĐẠI)}
\end{cases}
$$

**Vì sao phải chia cho $1-p$?** Để **kỳ vọng đầu ra không đổi** giữa lúc train và lúc chạy thật.
**Ví dụ số** với $p = 0{,}1$: 90% số lần nhánh được giữ và nhân $1/0{,}9 = 1{,}111$; 10% số lần bị xóa (= 0).
Kỳ vọng $= 0{,}9 \times 1{,}111 \times h + 0{,}1 \times 0 = h$ ✔ — **đúng bằng giá trị khi không có DropPath**.
Nhờ vậy lúc `eval()` chỉ cần **tắt DropPath đi**, không phải hiệu chỉnh gì.

**Vì sao tỉ lệ TĂNG DẦN theo độ sâu (0 → 0,1)?**
- **Tầng 1 ($p = 0$, không bao giờ tắt):** nó học **biểu diễn nền tảng** — mọi tầng sau đều xây trên nó.
  Tắt tầng 1 = **rút móng nhà**.
- **Tầng 4 ($p = 0{,}1$, hay bị tắt nhất):** nó học **tinh chỉnh cuối** — thứ **dễ overfit nhất**,
  và cũng là thứ **bỏ đi cũng không sập**.

> **So sánh:** thỉnh thoảng cho một phòng ban nghỉ, buộc các phòng còn lại **tự xoay xở** → **không phòng nào
> được phép trở thành điểm phụ thuộc duy nhất**. Nhưng **phòng kế toán gốc (tầng 1) thì không bao giờ được nghỉ**.

**To/nhỏ thì sao:** `drop_path_rate` **cao hơn** (0,3–0,5) → mạng quá "rỗng", underfit, hội tụ chậm;
**bằng 0** → mất hoàn toàn cơ chế này, quay về V1.

---

### (b) LayerScale — "vặn volume từ 0 lên"

```python
self.ls1 = nn.Parameter(torch.ones(d_model) * 1e-4)   # 128 số, HỌC ĐƯỢC
x = x + drop_path1(self.ls1 * self.attn(self.norm1(x)))
```

$$x \leftarrow x + \boldsymbol{\gamma} \odot \text{Attn}(\text{LN}(x)), \qquad \boldsymbol{\gamma} \text{ khởi tạo } = 10^{-4}$$

- $\boldsymbol{\gamma}$ là **một vector 128 chiều** (mỗi chiều một hệ số riêng), **học được**.
- Khởi tạo **1e-4** — cực nhỏ.

**Vấn đề nó giải quyết:** lúc mới khởi tạo, trọng số ngẫu nhiên → đầu ra của mỗi khối là **rác**.
Cộng 4 khối rác vào nhau qua residual → tín hiệu bị **nhiễu loạn ngay từ bước 1**, gradient rung lắc dữ dội.

**LayerScale giải bằng cách:** nhân đầu ra khối với $10^{-4}$ → **đóng góp gần như bằng 0**
→ lúc khởi đầu model **≈ hàm đồng nhất (identity)**: $x \leftarrow x + 0{,}0001 \times \text{rác} \approx x$.
Rồi **model tự học tăng $\boldsymbol{\gamma}$ lên** ở đúng những khối nó thấy hữu ích.

**Ví dụ số:** đầu ra Attention có độ lớn ~1,0. Nhân $10^{-4}$ → đóng góp **0,0001** so với $x$ có độ lớn ~1,0
→ **thay đổi 0,01%**. Sau vài trăm bước train, nếu khối đó hữu ích, $\gamma$ có thể leo lên 0,1–1,0.

> **So sánh:** người mới vào đội thì **quan sát trước, phát biểu sau**. Ai chứng minh được mình có ích
> thì **dần dần được nói to hơn**.

**Bonus — vì sao mỗi chiều một hệ số riêng (vector 128) chứ không phải một số?**
Vì một khối có thể **rất hữu ích cho vài chiều biểu diễn** và **vô dụng cho các chiều khác**.
Vector cho phép model **bật/tắt từng chiều độc lập**.

**Liên hệ với GĐ3:** LayerScale + Pre-LN chính là lý do **V8.5 bỏ được warmup** — hai cơ chế này đã lo phần
"bảo vệ giai đoạn đầu" mà warmup vốn lo.

---

### (c) GEGLU — "activation CÓ CỔNG" (thay GELU thuần)

```python
self.ffn = nn.Sequential(
    nn.Linear(d_model, d_ff * 2),      # ← 128 → 1024  (NHÂN ĐÔI!)
    GEGLU(),                            # chunk làm 2 nửa → 1024 → 512
    nn.Dropout(dropout),
    nn.Linear(d_ff, d_model)            # ← 512 → 128
)

class GEGLU(nn.Module):
    def forward(self, x):
        x, gate = x.chunk(2, dim=-1)    # cắt 1024 thành 2 × 512
        return x * F.gelu(gate)         # nội dung × cổng
```

$$\text{GEGLU}(x) = \underbrace{x_1}_{\text{NỘI DUNG}} \odot \underbrace{\text{GELU}(x_2)}_{\text{CỔNG} \in (\approx 0,\ \infty)}, \qquad [x_1, x_2] = \text{chunk}(Wx)$$

**Khác GELU thuần ở đâu?**

| | Cách hoạt động |
|---|---|
| **GELU thuần** | Tính ra một giá trị rồi **cho qua** (chỉ bị bóp méo phi tuyến). **Mọi thông tin đều đi tiếp** |
| **GEGLU** | Tính **HAI** thứ: một nửa là **nội dung**, một nửa là **cổng quyết định cho qua bao nhiêu**. **Nhân với nhau** |

**Ví dụ số** cho một chiều:

| Trường hợp | $x_1$ (nội dung) | $x_2$ (cổng) | $\text{GELU}(x_2)$ | Kết quả $x_1 \odot \text{GELU}(x_2)$ |
|---|---|---|---|---|
| Cổng **mở** | 3,0 | +2,0 | ≈ 1,95 | **5,85** → thông tin đi tiếp, còn được khuếch đại |
| Cổng **đóng** | 3,0 | −3,0 | ≈ −0,004 | **≈ −0,01** → **thông tin bị chặn gần như hoàn toàn** |

→ **Cùng một nội dung 3,0**, nhưng model **tự quyết định** cho qua hay chặn, **tùy theo ngữ cảnh của flow đó**.

> **So sánh:** GELU là **cái phễu** — đổ gì cũng chảy xuống (chỉ chảy nhanh/chậm khác nhau).
> GEGLU là **cái van có người trực** — người đó **nhìn nội dung rồi mới quyết định mở van bao nhiêu**.

**Vì sao cần cho bài toán này?** Với 9 lớp mất cân bằng, model phải học **lọc**: đặc trưng nào liên quan
Heartbleed thì cho qua khi đang xét flow đó, **chặn** khi đang xét flow Benign. GELU thuần không có cơ chế
chặn — nó cho qua tất, chỉ khác nhau về độ lớn.

**⚠️ Đây là lý do `Linear(d_model, d_ff * 2)`:** phải sinh ra **gấp đôi** ($2 \times 512 = 1024$) để cắt làm hai nửa.
**Cái giá phải trả:** tầng Linear đầu của FFN **to gấp đôi** → tham số nhiều hơn. Đó là đánh đổi có ý thức.

🔴 **Quyển B.1.9 ghi `Activation = GELU` → SAI. Code là GEGLU.** Hai thứ **khác nhau về bản chất**,
không phải khác tên gọi.

---

### (d) Classifier head V2 — gọn hơn V1

```python
# V1:  Linear(128, 128) → GELU → Dropout → Linear(128, C)
# V2:  LayerNorm(128) → Linear(128, 64) → GELU → Dropout → Linear(64, C)
```
- **Thêm `LayerNorm` ở đầu** — chuẩn hóa vector `[CLS]` trước khi phân lớp → ổn định hơn.
- **Bóp $128 \to 64$** thay vì giữ $128 \to 128$ → **ít tham số hơn**, giảm overfit ở tầng cuối
  (nơi dễ học vẹt nhất).
- **Đây chính là chỗ để đọc số lớp từ checkpoint:** `classifier.4.weight` có shape `(C, 64)`.
  Nhờ nó mà xác minh được **Stage 1 = 6 lớp** `(6, 64)`, **Stage 2 = 5 lớp** `(5, 32)` (vì Stage 2 có $d=64 \to 32$).

---

### ⚠️ CÁI BẪY `d_ff` — phải biết trước khi bị hỏi

Cả Stage 1 và Stage 2 gọi `FTTransformer(...)` mà **KHÔNG truyền `d_ff`** → nhận **giá trị mặc định 512** của class.

🔴 Quyển B.1.6 ghi Stage 2 `d_ff = 256` → **SAI**.

**Kiểm chứng từ checkpoint** (không cần tin comment):
```
transformer_blocks.0.ffn.0.weight  shape = (1024, 64)
                                            ↑
                     1024 = 2 × d_ff  (GEGLU nhân đôi)  ⟹  d_ff = 512  ✔
transformer_blocks.0.ffn.3.weight  shape = (64, 512)    ⟹  xác nhận lần 2  ✔
```

→ **Hardcode NGẦM qua giá trị mặc định** — cái bẫy điển hình:
**người viết nghĩ mình dùng 256, thực tế chạy 512.**

**Nếu bị hỏi:** *"Em đã đối chiếu lại với checkpoint: shape thật là (1024, 64), tức $d_{ff} = 512$ chứ không
phải 256 như Phụ lục ghi. Nguyên nhân là code **không truyền `d_ff`** nên nhận giá trị mặc định. Em sẽ sửa
Phụ lục theo cấu hình **thực chạy**."*

---

## 2.1 MODEL B.1.5 — STAGE 1: GATING NETWORK

```python
FTTransformer(num_features=77, num_classes=6,
              d_model=128, num_layers=4, num_heads=8,
              dropout=0.2, drop_path_rate=0.1)     # d_ff = 512 (mặc định)
# 1.087.302 tham số
```
**6 lớp:** `Benign, Brute Force, DDoS, DoS, PortScan, Suspicious`

### 🔴 ĐIỀU QUYỂN ĐANG KỂ SAI — VÀ SỰ THẬT HAY HƠN

**Quyển:** *"Stage 1 là cổng nhị phân Benign/Suspicious, Stage 2 phân 9 lớp."*

**Sự thật:** Stage 1 **TỰ PHÂN LUÔN 4 LỚP TẤN CÔNG ĐÔNG** (Brute Force, DDoS, DoS, PortScan) và
**chỉ đẩy nhãn gom `Suspicious`** xuống Stage 2. Stage 2 là **chuyên gia LỚP HIẾM**
(Bot, Heartbleed, Infiltration, Web Attack — + Benign để bắt lại khi Stage 1 báo nhầm).

> **So sánh:** quyển mô tả *"phòng khám chỉ hỏi CÓ BỆNH KHÔNG, rồi bác sĩ chuyên khoa chẩn đoán tất cả 9 bệnh."*
> Thực tế là *"phòng khám **tự chữa luôn các bệnh phổ biến** (cảm, sốt), **chỉ đẩy ca lạ** cho chuyên khoa hiếm."*

**Sửa lại thì LẬP LUẬN MẠNH HƠN:** gradient của Bot/Infiltration/Heartbleed ở Stage 2 **không còn phải cạnh
tranh** với DoS/DDoS/PortScan (mỗi lớp hàng trăm nghìn flow) — chúng chỉ cạnh tranh **trong nhóm lớp hiếm**.
**Đó là toàn bộ lý do cascade hoạt động.**
Và đó cũng là lý do **Stage 2 NHỎ hơn** (d=64, 3 tầng, 4 head): bài toán hẹp hơn + dữ liệu ít hơn
→ **model to sẽ học vẹt**.

### Tiền xử lý Stage 1

#### (a) SMOTE-ENN với Borderline-SMOTE — **lý thuyết ĐANG DÙNG, quyển CHƯA NÊU**

```python
strategy = {label: max(30000, count) for label, count in label_counts.items()}
strategy[label_counts.idxmax()] = label_counts.max()          # lớp đông nhất giữ nguyên
smote_enn = SMOTEENN(smote=BorderlineSMOTE(sampling_strategy=strategy,
                                            random_state=42, k_neighbors=5),
                     random_state=42)
```

Ba mảnh:
1. **Borderline-SMOTE** — khác SMOTE thường: **chỉ sinh mẫu mới ở VÙNG BIÊN GIỚI** (những mẫu thiểu số có
   nhiều láng giềng thuộc lớp khác). **Lý do:** mẫu nằm sâu trong vùng an toàn thì sinh thêm cũng vô ích —
   model đã phân đúng rồi. **Biên giới mới là chỗ model sai.**
2. **`max(30000, count)`** — nâng **mọi lớp** lên tối thiểu **30.000** mẫu. To hơn → nhiều mẫu nhân tạo,
   dễ overfit vào nhiễu SMOTE; nhỏ hơn → lớp hiếm vẫn bị đè.
3. **ENN (Edited Nearest Neighbours)** — bước **dọn dẹp SAU khi sinh**: xóa những mẫu mà **đa số láng giềng
   thuộc lớp khác**.

> **So sánh đời thường:** SMOTE là **trồng thêm cây**; Borderline = chỉ trồng **dọc hàng rào** (chỗ tranh chấp);
> ENN = **nhổ bỏ** những cây mọc lấn sang vườn nhà hàng xóm.

#### (b) PowerTransformer Yeo-Johnson (thay MinMax của GĐ1)

### Công thức ĐẦY ĐỦ — **4 nhánh, không phải 2**

$$
\psi(y,\lambda)=
\begin{cases}
\dfrac{(y+1)^{\lambda}-1}{\lambda} & \lambda \ne 0,\ \ y \ge 0 \\[10pt]
\ln(y+1) & \lambda = 0,\ \ y \ge 0 \\[10pt]
-\,\dfrac{(1-y)^{\,2-\lambda}-1}{2-\lambda} & \lambda \ne 2,\ \ y < 0 \\[10pt]
-\ln(1-y) & \lambda = 2,\ \ y < 0
\end{cases}
$$

**Đọc bảng này cho đúng — nó chia theo HAI trục:**

| | $\lambda$ **thường** | $\lambda$ **ở giá trị suy biến** |
|---|---|---|
| **$y \ge 0$** (nhánh dương) | $\dfrac{(y+1)^{\lambda}-1}{\lambda}$ | $\lambda = 0$ → $\ln(y+1)$ |
| **$y < 0$** (nhánh âm) | $-\dfrac{(1-y)^{2-\lambda}-1}{2-\lambda}$ | $\lambda = 2$ → $-\ln(1-y)$ |

Bóc từng mảnh:
- **$y+1$ và $1-y$** — phép **dịch để tránh số ≤ 0** trước khi lũy thừa. Nhánh dương dịch lên 1
  ($y \ge 0 \Rightarrow y+1 \ge 1$); nhánh âm **lật dấu rồi dịch** ($y < 0 \Rightarrow 1-y > 1$).
  → **Cả hai nhánh đều đưa cơ số về $\ge 1$**, nên lũy thừa luôn hợp lệ.
- **Dấu trừ ở nhánh âm** — để hàm **đơn điệu tăng liên tục** khi đi qua $y = 0$. Không có dấu trừ thì
  đồ thị bị **gãy và lật ngược** ở gốc.
- **$2-\lambda$ ở nhánh âm** (thay vì $\lambda$) — chọn khéo để hàm **trơn tại $y = 0$**
  (đạo hàm hai phía khớp nhau). Đây là toàn bộ "phép thuật" của Yeo & Johnson (2000).
- **Hai nhánh $\ln$** — là **giới hạn** khi mẫu số tiến về 0, xử lý trường hợp chia-cho-0
  ($\lambda \to 0$ ở nhánh dương, $\lambda \to 2$ ở nhánh âm).

**Chỉ có MỘT tham số $\lambda$ duy nhất cho cả 4 nhánh** — nó được **ước lượng từ dữ liệu bằng
maximum likelihood**, riêng cho **từng cột đặc trưng**.

### ⚠️ Vì sao 2 nhánh âm KHÔNG phải chi tiết thừa — **dữ liệu của đồ án CÓ số âm thật**

Nếu chỉ có nhánh $y \ge 0$ thì Yeo-Johnson **chính là Box-Cox dịch 1 đơn vị** — chẳng có gì mới.
**Toàn bộ lý do Yeo-Johnson tồn tại là 2 nhánh âm.**

Và trong đồ án này chúng **được dùng thật**. Kiểm tra trên 200.000 dòng của `Combined_V8_5.csv`:

| Cột | Giá trị nhỏ nhất | Số dòng âm |
|---|---|---|
| `Init_Win_bytes_backward` | **−1** | **494** |
| `Flow_IAT_Min` | **−1** | 4 |

*(`−1` là quy ước của CICFlowMeter cho "không quan sát được initial window size" — một quirk nổi tiếng của bộ trích xuất này.)*

→ **Nếu dùng Box-Cox hay log, hai cột này sẽ báo lỗi hoặc phải bịa giá trị thay thế.**
Yeo-Johnson **xử lý được nguyên bản**, không cần đụng vào dữ liệu.

**Đây là câu trả lời hoàn chỉnh cho "sao không dùng log?"** — không chỉ là lý thuyết suông,
mà có **bằng chứng ngay trong dữ liệu của mình**.

### Vấn đề nó giải quyết

- Đặc trưng mạng **lệch phải cực mạnh** (đuôi dài): `Flow_Bytes_s` chạy từ 0 đến **hàng trăm triệu**.
- **MinMax với đuôi dài là thảm họa:** một outlier duy nhất định nghĩa cả `max` → **toàn bộ phần còn lại
  bị nén về gần 0**, model không phân biệt nổi.
- Yeo-Johnson **học $\lambda$ từ dữ liệu** để **bẻ thẳng phân phối** về gần chuẩn.
  `standardize=True` → sau đó **z-score hóa** (trừ mean, chia std).

**Đọc $\lambda$ cho có nghĩa:**

| $\lambda$ | Hiệu ứng | Hợp với |
|---|---|---|
| $\lambda \approx 0$ | Gần như **lấy log** — **nén đuôi phải rất mạnh** | Đặc trưng lệch phải cực đoan (`Flow_Bytes_s`) |
| $\lambda \approx 1$ | Gần như **không đổi gì** (biến đổi tuyến tính) | Đặc trưng vốn đã gần chuẩn |
| $\lambda > 1$ | **Kéo giãn** đuôi phải | Đặc trưng lệch **trái** |

> **So sánh đời thường:** ảnh chụp ngược sáng có vùng cháy trắng và vùng tối đen. **Yeo-Johnson là nút
> chỉnh gamma** — nó **kéo giãn vùng tối và nén vùng sáng** để nhìn ra chi tiết ở cả hai đầu.
> $\lambda$ chính là **độ mạnh của nút vặn đó**, và **máy tự dò lấy** thay vì người chỉnh tay.

⚠️ Scaler được **fit trên dữ liệu ĐÃ resample** (có cả mẫu SMOTE nhân tạo). Nếu bị hỏi:
*"$\lambda$ được ước lượng trên phân phối sau cân bằng — đó là **phân phối mà model thực sự nhìn thấy khi train**."*

### Siêu tham số Stage 1

| Tham số | Giá trị | Giải thích |
|---|---|---|
| `dropout` | **0,2** | Cao hơn GĐ1 (0,1) — CIC nhiều mẫu lặp + có SMOTE → cần phanh mạnh hơn |
| `drop_path_rate` | **0,1** | Tăng dần 0 → 0,1 theo 4 tầng |
| Loss | `Focal(γ=**2.0**, label_smoothing=**0.05**, weight=balanced)` | 🔴 quyển không ghi label_smoothing |
| Optimizer | `AdamW(lr=1e-4, weight_decay=1e-4)` | |
| Scheduler | `CosineAnnealingWarmup(warmup=**3**, total=15, min_lr=1e-6)` | **Warmup 3 epoch:** trọng số lúc đầu ngẫu nhiên → LR lớn ngay bước 1 sẽ đẩy model đi lung tung. Warmup tăng LR tuyến tính từ 0 |
| **EMA** | `decay=0.999` | $\theta_{EMA}\leftarrow 0{,}999\,\theta_{EMA} + 0{,}001\,\theta$. Weight cuối hay rung lắc theo batch chót; bản EMA **mượt hơn, generalize tốt hơn** |
| Grad clip | **1,0** | Một batch dị thường không làm nổ weight |
| AMP | `torch.cuda.amp` | Mixed precision float16 → nhanh ~2×, tiết kiệm VRAM |
| Epochs | **15** | 🔴 quyển ghi 30 |
| Chọn checkpoint | `max(val_f1, ema_val_f1)` | Lấy bản tốt hơn giữa model thường và model EMA |
| Metric phụ | **G-mean** $=\left(\prod_c \text{recall}_c\right)^{1/C}$ | Trung bình **NHÂN** của recall. Khác Macro F1: chỉ cần **MỘT** lớp có recall = 0 thì **G-mean = 0 ngay**. Rất khắt khe với lớp hiếm |

### 🔴 ĐIỂM YẾU LỚN NHẤT CỦA GĐ2 — PHẢI TỰ NÓI TRƯỚC

```python
TRAIN_CSV = 'processed_data/cic_train_stage1.csv'
VAL_CSV   = 'processed_data/cic_test_full.csv'      # ← TẬP TEST!
```

**Tập validation dùng để CHỌN checkpoint chính là tập test dùng để BÁO CÁO 0,9294.**
→ Model được **chọn** dựa trên chính tập mà nó được **chấm điểm**. Đây là **model-selection leak** —
con số 0,9294 **là cận trên, lạc quan hơn thực tế**.

**Cách trả lời (đừng chối, đừng vòng vo):**
> *"Đúng, đây là một hạn chế về phương pháp mà em **tự phát hiện khi rà soát lại code**: ở giai đoạn 2,
> tập val để chọn checkpoint trùng với tập test báo cáo. Nghĩa là **0,9294 là cận trên**.
> Em ghi rõ điều này thay vì che đi.*
>
> *Điều quan trọng: bài học đó **đã được sửa ở giai đoạn 3** — V8.5 dùng val tách riêng bằng
> `train_test_split(test_size=0.1, stratify=y)`, và **val được đa dạng hóa miền có chủ đích**
> (xem B.2.7: V8.4 val toàn CIC → 94,95% **inflate**; V8.5 val đa dạng miền → 91,7% **thật hơn**).
> Đó là một phần của quá trình trưởng thành trong đồ án này."*

Câu trả lời này **biến điểm yếu thành điểm mạnh**.

---

## 2.2 MODEL B.1.6 — STAGE 2: EXPERT NETWORK

```python
FTTransformer(num_features=34, num_classes=5,      # 🔴 quyển: 9 lớp, d_ff=256
              d_model=64, num_layers=3, num_heads=4,
              dropout=0.2, drop_path_rate=0.1)     # d_ff = 512 (mặc định)
# 356.165 tham số — nhỏ bằng 1/3 Stage 1
```
**5 lớp:** `Benign, Bot, Heartbleed, Infiltration, Web Attack`

**Vì sao model NHỎ hơn?** Bài toán hẹp hơn (4 lớp hiếm thay vì 6) + dữ liệu vào Stage 2 ít hơn nhiều
→ model to sẽ học vẹt.
**Nguyên tắc: kích thước model tỉ lệ với lượng dữ liệu và độ rộng bài toán.**

### 34 đặc trưng chọn lọc (`STAGE2_FEATURES` — đã đếm)
5 cờ cổng (`Port_Is_*`) · 6 đặc trưng IAT · 8 kích thước gói · 5 header/segment · 4 window/subflow ·
6 cờ TCP + tỉ lệ tự chế (gồm `Custom_Pkt_Var_Ratio`, `Custom_IAT_Anomaly`, `Flow_Bytes_Ratio`, `Flow_Pkts_Ratio`).

→ 2 đặc trưng tỉ lệ **được tính tại chỗ**, không có sẵn trong CSV:
`Flow_Bytes_Ratio = Total_Length_of_Fwd_Packets / Total_Length_of_Bwd_Packets` (thay 0 bằng 1 để tránh chia 0).

### Hard Negative Mining — ✅ **quyển ĐÃ có (Ch. 3.3.5, 5.3.3)**
Train CSV là `cic_train_stage2_v7_hard.csv`, sinh bởi `extract_hard_negatives_v7.py`.

**Ý tưởng:** Stage 2 chỉ nhìn thấy những flow mà Stage 1 gán `Suspicious`. Nếu train nó trên dữ liệu ngẫu nhiên
thì **nó học sai phân phối**. Phải train nó trên **đúng những mẫu Benign KHÓ** — những mẫu mà Stage 1 đã nhầm
thành Suspicious. Đó là "hard negative".

> **So sánh:** bác sĩ chuyên khoa **không cần luyện trên người khỏe mạnh rõ ràng** — họ cần luyện trên
> **những ca mà phòng khám tuyến dưới không dám kết luận**.

**Bằng chứng trong quyển (Ch. 3.3.5):** class weight ×10 cho Botnet → F1 = 0,5103;
**HNM 2 vòng → F1 = 0,6512** (+14 điểm tuyệt đối). → **HNM thắng class weight.** Đây là số rất mạnh, phải dùng.

### Cái hack cho Heartbleed (10 mẫu!)
```python
if count < 6:      # SMOTE cần ≥ 6 mẫu (k_neighbors=5 + chính nó)
    # nhân bản (duplicate) mẫu cho đủ 6
```
**Trung thực:** với lớp chỉ có vài mẫu, code **nhân bản** cho đủ 6 rồi mới SMOTE được.

**Nếu bị hỏi về Heartbleed F1 = 1,0000:** *"Heartbleed có **10 mẫu** trong tập test. F1 = 1,0 trên 10 mẫu
**không phải bằng chứng mạnh** — em báo cáo nó nhưng **không dựa vào nó** để kết luận."*

### Trọng số lớp — thủ thuật thực dụng
```python
c_weights = compute_class_weight('balanced', ...)      # w_c = N / (K · n_c)
for cls in ['Web Attack', 'Infiltration', 'Heartbleed']:
    c_weights[idx] *= 1.5                              # ← nhân thêm 1,5×
```
Sau khi cân bằng chuẩn, **nhân thêm 1,5×** cho 3 lớp khó nhất. **Phải nói rõ đây là heuristic.**

### Siêu tham số Stage 2 — khác Stage 1 ở đâu

| Tham số | Stage 1 | **Stage 2** | Vì sao khác |
|---|---|---|---|
| Focal `gamma` | 2,0 | **1,5** | Sau SMOTE + trọng số ×1,5, dữ liệu **đã cân bằng hơn** → không cần dồn sức vào mẫu khó mạnh như vậy nữa. **γ quá cao trên dữ liệu đã cân bằng → model bỏ bê mẫu dễ** |
| `NUM_EPOCHS` | 15 | **20** | Bài toán lớp hiếm khó hội tụ hơn |
| SMOTE | **Borderline**-SMOTE | **SMOTE thường** | Với lớp cực hiếm, khái niệm "biên giới" gần như vô nghĩa |
| `label_smoothing` / `lr` / `wd` / warmup / EMA / clip | 0,05 / 1e-4 / 1e-4 / 3 / 0,999 / 1,0 | **giống hệt** | |
| Checkpoint dùng khi inference | `best_stage1_model.pt` (**không EMA**) | `best_stage2_ema.pt` (**EMA**) | ⚠️ **Bất đối xứng** — nếu bị hỏi: *"Em chọn bản nào có val F1 cao hơn ở từng tầng."* |

---

## 2.3 MODEL B.1.7 + B.1.8 — RANDOM FOREST + KNN

Cả hai **train trên CÙNG dữ liệu đã SMOTE + đã scale** như FTT Stage 2.

```python
RandomForestClassifier(n_estimators=150, max_features=20, max_depth=25,
                       class_weight='balanced',        # 🔴 quyển: 'balanced_subsample'
                       random_state=42, n_jobs=-1)
KNeighborsClassifier(n_neighbors=16, n_jobs=-1)        # 🔴 weights='uniform' (mặc định)
```

| Tham số | Ý nghĩa — to/nhỏ thì sao |
|---|---|
| `n_estimators=150` | 150 cây bỏ phiếu. Ít hơn → phương sai cao; nhiều hơn → chậm, lợi ích bão hòa |
| `max_depth=25` | Mỗi cây hỏi tối đa 25 tầng câu hỏi. Sâu hơn → nhớ cả nhiễu |
| **`max_features=20`** | **Quan trọng nhất:** mỗi lần rẽ nhánh chỉ được nhìn **20/34** đặc trưng ngẫu nhiên → **ÉP CÁC CÂY KHÁC NHAU**. 150 cây giống hệt nhau thì bỏ phiếu vô nghĩa. **Đây chính là chữ "Random" trong Random Forest** |
| `n_neighbors=16` | Nhìn 16 flow giống nhất rồi theo đa số. k nhỏ (1–3) → **nhạy nhiễu**; k to (100) → **lớp đông nuốt lớp hiếm**; 16 là điểm cân bằng |

### 🔴 Hai lệch phải sửa trong quyển

**RF `class_weight`:** `balanced` vs `balanced_subsample` **khác nhau thật sự**:
- `balanced` → tính trọng số **một lần trên toàn bộ tập train**.
- `balanced_subsample` → tính lại trọng số **trên mẫu bootstrap của TỪNG CÂY**.

Với lớp cực hiếm (Heartbleed 10 mẫu), **nhiều cây bootstrap sẽ KHÔNG có mẫu Heartbleed nào cả**
→ `balanced_subsample` mới là lựa chọn đúng. **Quyển ghi cái đúng, code chạy cái kia.**

**KNN `weights`:** Chương 3.3.6 viết *"KNN (K=16, distance-weighted)"* — **KHÔNG ĐÚNG**.
Code chỉ có `KNeighborsClassifier(n_neighbors=16, n_jobs=-1)` → **`uniform`**:
16 láng giềng bỏ phiếu **ngang nhau**, không phân biệt gần hay xa.

---

## 2.4 GHÉP HỆ THỐNG — LUẬT CASCADE THẬT (`evaluate_cascade_system_v7.py`)

### Đường đi của một flow
```
                          ┌── s1_pred ≠ Suspicious ──────────────► lấy luôn nhãn Stage 1
   flow ──► Stage 1 ──────┤
                          └── s1_pred = Suspicious ──┬── p < 0,85 ──► ÉP VỀ BENIGN
                                                     └── p ≥ 0,85 ──► xuống Stage 2
```

### 🔴 Ngưỡng 0,85 đang bị quyển GIẢI THÍCH NGƯỢC

**Quyển (Ch. 3.3.4):** *"Ngưỡng bảo thủ **ưu tiên recall tấn công** hơn giảm workload."*

**Code:**
```python
mask_low_prob = (s1_preds == suspicious_idx) & (s1_probs < THRESHOLD)
final_preds_chunk[mask_low_prob] = 'Benign'          # ← VỨT THÀNH BENIGN
```
Flow bị Stage 1 nghi ngờ **nhưng độ tin cậy < 85%** thì **bị vứt thành Benign**, chứ **không** được đẩy
xuống Stage 2 soi kỹ. → Ngưỡng này **GIẢM FALSE POSITIVE**, hoàn toàn **ngược** với điều quyển biện luận.

**Cách nói đúng:** *"Ngưỡng 0,85 là **van giảm báo động giả**: chỉ những flow mà Stage 1 **thật sự tin**
là đáng ngờ (≥ 85%) mới được chuyển xuống chuyên khoa. Nghi ngờ yếu thì bỏ qua — **đánh đổi recall lấy
precision, có chủ đích**."*

### Luật Asymmetric Voting trong Stage 2 (nguyên văn logic)

```python
if   ft == 'Benign':                                        → Benign         # (0) FTT phủ quyết
elif rf=='Infiltration' or knn=='Infiltration'
     or (ft=='Infiltration' and ft_prob >= inf_thresh):     → Infiltration   # (1) OR — ưu tiên tối đa
elif ft=='Bot' and (rf=='Benign' or knn=='Benign'):         → Benign         # (2) veto Bot
elif ft_prob >= 0.65:                                       → ft             # (3) soft threshold
else:                                                        → Benign         # (4) mặc định
```

**Đọc cho đúng — ensemble thật KHÔNG PHẢI majority vote:**
- **FTT làm chủ.** RF/KNN chỉ có **quyền PHỦ QUYẾT (veto)** cho đúng **2 lớp**:
  - **Infiltration** — veto *thuận*: chỉ cần **1 trong 2** nói Infiltration là gán ngay (OR).
  - **Bot** — veto *nghịch*: nếu **1 trong 2** nói Benign thì **hạ Bot xuống Benign**.
    (🔴 Quyển ghi *"AND of 3"* — **sai**: nếu RF nói `'DoS'` thì Bot **vẫn giữ nguyên**.)
- **Các lớp còn lại: RF/KNN KHÔNG bỏ phiếu.** Lấy thẳng nhãn FTT nếu `ft_prob ≥ 0,65`, dưới ngưỡng → Benign.
- 🔴 **KHÔNG có nhánh majority vote nào trong code.** Bảng *"Majority Vote (2/3) → Macro F1 0,9247"* ở B.2.3
  **cần kiểm tra lại xem có thật sự chạy không.**

**Vì sao luật BẤT ĐỐI XỨNG?** Vì **chi phí sai của hai lớp khác nhau**:
- **Infiltration** — cực hiếm (33 mẫu test), **bỏ sót là thảm họa** → hạ ngưỡng tối đa, ai nói cũng nghe.
- **Bot** — hay báo nhầm → siết lại, cần đồng thuận mới tin.
> **So sánh:** với bệnh ung thư hiếm, chỉ cần **MỘT** bác sĩ nghi ngờ là phải sinh thiết.
> Với cảm cúm thì cần **cả nhóm** đồng ý mới cho nghỉ làm.

### 🎯 PHÁT HIỆN MỚI — trả lời được câu hỏi đang bỏ ngỏ về ngưỡng Infiltration

Code quét 3 ngưỡng `[0,65 · 0,68 · 0,70]` và xuất 3 report. **Đọc cả 3 file:**
```
final_v7_report_thresh_0.65.txt  →  macro avg  0.9514  0.9175  0.9294
final_v7_report_thresh_0.68.txt  →  macro avg  0.9514  0.9175  0.9294
final_v7_report_thresh_0.70.txt  →  macro avg  0.9514  0.9175  0.9294
```
**GIỐNG HỆT NHAU.**

→ Ngưỡng Infiltration **không ảnh hưởng gì đến kết quả**, vì nhánh `rf=='Infiltration' or knn=='Infiltration'`
đã quyết định xong **trước khi** nhánh `ft_prob >= inf_thresh` kịp có tiếng nói.

**Nói gì:** *"Em quét 3 ngưỡng, **cả ba cho kết quả y hệt** → con số 0,9294 **không phụ thuộc vào lựa chọn
ngưỡng này**. Trên thực tế, quyết định Infiltration đến từ RF/KNN chứ không từ FT-Transformer."*
→ **Tốt hơn** việc phải "chốt một ngưỡng".

---

## 2.5 KẾT QUẢ THẬT GĐ2 (2.529.391 flow — B.2.4)

| Lớp | Precision | Recall | **F1** | Support |
|---|---|---|---|---|
| Benign | 0,9992 | 0,9953 | 0,9972 | 2.031.715 |
| **Bot** | 0,7947 | **0,6826** | **0,7344** | 1.758 |
| Brute Force | 0,9473 | 0,9989 | 0,9724 | 12.369 |
| DDoS | 0,9984 | 0,9982 | 0,9983 | 114.453 |
| DoS | 0,9683 | 0,9963 | 0,9821 | 225.024 |
| Heartbleed | 1,0000 | 1,0000 | 1,0000 | **10** ⚠️ |
| **Infiltration** | 0,9524 | **0,6061** | **0,7407** | **33** ⚠️ |
| PortScan | 0,9936 | 0,9990 | 0,9963 | 142.079 |
| Web Attack | 0,9084 | 0,9810 | 0,9433 | 1.950 |
| **Macro avg** | **0,9514** | **0,9175** | **0,9294** | |
| Accuracy | | | **0,9955** | |

**Đọc bảng này cho đúng:**
- **Macro F1 0,9294 bị kéo xuống bởi ĐÚNG 2 lớp:** Bot (0,73) và Infiltration (0,74). **Bảy lớp còn lại ≥ 0,94.**
- **Infiltration recall chỉ 0,61** (bắt 20/33) — **giới hạn của DỮ LIỆU, không phải của model**: Infiltration
  trong CIC-IDS-2017 là mã độc chạy **sau khi đã vào máy** — hành vi của nó ở tầng flow gần như **giống traffic
  bình thường**. **Thông tin đó không có trong feature CICFlowMeter.**
- **Heartbleed F1 = 1,0 trên 10 mẫu** — báo cáo, nhưng **không dùng làm bằng chứng**.

## 2.6 GIAI ĐOẠN 2 — NÊN NÓI GÌ

| Hỏi | Trả lời |
|---|---|
| *"Vì sao Stage 2 nhỏ hơn Stage 1?"* | *"Bài toán hẹp hơn + dữ liệu vào ít hơn nhiều. **Kích thước model phải tỉ lệ với lượng dữ liệu**, nếu không sẽ học vẹt."* |
| *"Ensemble của em là majority vote?"* | **KHÔNG.** *"FTT làm chủ; RF/KNN chỉ có **quyền phủ quyết** cho 2 lớp Bot và Infiltration. Đây là **Asymmetric Voting** — vì **chi phí sai của hai lớp là khác nhau**."* |
| *"Ngưỡng Infiltration chọn bao nhiêu?"* | *"Em quét 0,65 / 0,68 / 0,70 và **cả ba cho kết quả y hệt** → kết quả không phụ thuộc ngưỡng này."* |
| *"Vì sao Infiltration recall chỉ 61%?"* | *"**Giới hạn của dữ liệu**, không phải model: hành vi sau xâm nhập ở tầng flow **giống traffic bình thường**."* |
| *"Val set của anh là gì?"* | ⚠️ **Nói thật** — xem mục 2.1, "ĐIỂM YẾU LỚN NHẤT". |
| *"γ của Focal Loss?"* | *"**Stage 1: 2,0. Stage 2: 1,5.** Khác nhau **có chủ đích**: Stage 2 đã cân bằng dữ liệu bằng SMOTE + trọng số ×1,5 rồi, γ cao nữa sẽ làm model **bỏ bê mẫu dễ**."* |
| *"HNM có hơn class weight không?"* | *"**Có, đo được:** class weight ×10 cho Botnet → F1 0,5103; **HNM 2 vòng → 0,6512**. Hơn **14 điểm tuyệt đối**."* |

---
---

# PHẦN 3 — CHẨN ĐOÁN COVARIATE SHIFT (Chương 5.4 — thực nghiệm trung gian)

> ⚠️ **Đây là THỰC NGHIỆM CHẨN ĐOÁN, không phải sản phẩm.** Quyển đã ghi đúng như vậy (Ch. 5.4.2).
> **Đừng trình bày nó như hệ thống.** Nhưng phải kể — vì nó là **lý do V8.5 tồn tại**.

## 3.1 Bước A — Direct transfer: SỤP ĐỔ

| | CIC (miền gốc) | Testbed (miền đích) |
|---|---|---|
| Accuracy | 99,55% | **21,93%** |
| MCC | 0,9941 | **−0,015** |

$$\text{MCC} = \frac{TP \cdot TN - FP \cdot FN}{\sqrt{(TP+FP)(TP+FN)(TN+FP)(TN+FN)}}$$

**MCC âm nghĩa là gì?** MCC chạy từ −1 đến 1; **0 = đoán bừa**.
**MCC = −0,015 tức model dự đoán TỆ HƠN CẢ TUNG ĐỒNG XU** — nó không chỉ sai, nó **sai có hệ thống**.

**Nguyên nhân — Covariate Shift:**
$$P_{source}(\mathbf{x}) \ne P_{target}(\mathbf{x}) \quad\text{trong khi}\quad P(y \mid \mathbf{x}) \text{ không đổi}$$
- CIC thu trên **switch Gigabit vật lý**. Testbed chạy trên **WSL2 / Hyper-V NAT**.
- Overhead ảo hóa đổi packet size & timing; NAT Windows đổi ACK timing → **phá hủy IAT và flag counts**.
- PowerTransformer đã fit $\lambda$ trên phân phối CIC → áp lên Testbed cho ra giá trị vô nghĩa.

### 🌐 MÔI TRƯỜNG THU ẢNH HƯỞNG THẾ NÀO — và câu hỏi "thay đổi cổng?"

Đây là câu hỏi thầy/cô đã cảnh báo. Phải tách **hai cơ chế cổng** khác nhau, vì cách trả lời khác hẳn.

#### Trước tiên: 5 cờ cổng được tính từ đâu (đọc `ids_replay/features.py:26-32`)

```python
p = df['Destination_Port'].astype(int)     # ← CỔNG ĐÍCH (cổng DỊCH VỤ), không phải cổng nguồn
df['Port_Is_Web']          = p.isin([80, 443, 8080, 8443, 8888]).astype(int)
df['Port_Is_RemoteAccess'] = p.isin([21, 22, 23, 2222, 3389]).astype(int)
df['Port_Is_WellKnown']    = (p <= 1023).astype(int)
df['Port_Is_Registered']   = ((p > 1023) & (p <= 49151)).astype(int)
df['Port_Is_Ephemeral']    = (p > 49151).astype(int)
```

**Điểm mấu chốt phải nhớ: cả 5 cờ tính từ `Destination_Port` (cổng DỊCH VỤ), KHÔNG phải cổng nguồn.**
Đây là một quyết định thiết kế **tốt** — và nó quyết định câu trả lời cho cả hai cơ chế dưới đây.

#### Cơ chế 1 — NAT đổi *cổng NGUỒN* (source port remapping)

**NAT làm gì:** khi flow từ máy trong mạng đi qua NAT của Windows/Hyper-V ra ngoài, NAT **thay cổng nguồn**
(ví dụ `51200 → 60918`) để quản lý bảng dịch địa chỉ. **Cổng đích (dịch vụ) giữ nguyên.**

**Ảnh hưởng lên feature:**
- **KHÔNG trực tiếp phá 5 cờ `Port_Is_*`** — vì chúng dùng **cổng đích**, mà NAT không đổi cổng đích.
  → **Đây là lý do dùng cổng đích là lựa chọn khôn ngoan: cờ cổng MIỄN NHIỄM với NAT source remapping.**
- **Nhưng NAT phá thứ khác:** việc chèn một tầng dịch địa chỉ làm đổi **timing** (thêm độ trễ xử lý),
  **ACK pattern**, và **initial window size** (mỗi đầu NAT có thể thương lượng lại TCP window).
  → **Chính những đặc trưng này mới là thứ bị phá**, không phải cổng.

**Bằng chứng số (từ KS-test, `step1_summary.json`)** — top đặc trưng lệch lab↔thật **toàn là timing & window**:

| Đặc trưng lệch nhất | KS | Loại |
|---|---|---|
| `Bwd_IAT_Min` | **0,811** | **timing** |
| `Custom_IAT_Anomaly` | 0,545 | **timing** |
| `Init_Win_bytes_backward` | 0,446 | **TCP window (NAT thương lượng lại)** |
| `Fwd_IAT_Max / Mean / Total` | ~0,43 | **timing** |

→ **KHÔNG có cờ `Port_Is_*` nào trong nhóm lệch mạnh nhất.** Cổng **không phải** thủ phạm covariate shift.
NAT gây hại qua **đồng hồ (IAT) và cửa sổ TCP (window)**, đúng như dự đoán.

#### Cơ chế 2 — Dịch vụ chạy ở *cổng KHÁC* giữa hai môi trường

Đây mới là cơ chế **cổng thật sự có thể gây hại** — và nó **không liên quan NAT**, mà liên quan **cách dựng lab**.

**Vấn đề:** CIC bắt SSH ở cổng chuẩn **22**, web ở **80/443**. Nhưng trong testbed tự dựng, người ta hay chạy
dịch vụ ở **cổng phi chuẩn** cho tiện (SSH ở `2222`, web dev ở `8080`/`8000`, RDP ở cổng lạ…).

**Hậu quả nếu không xử lý:** cùng một tấn công SSH brute-force, nhưng
- CIC: cổng đích 22 → `Port_Is_RemoteAccess = 1`
- Testbed: cổng đích 2222 → nếu 2222 **không có trong danh sách** → `Port_Is_RemoteAccess = 0`,
  `Port_Is_Registered = 1` → **one-hot cổng LẬT hoàn toàn** → model thấy một "loại dịch vụ" khác hẳn.

**Cách đồ án đã xử lý — nhìn kỹ danh sách cổng, nó KHÔNG phải danh sách chuẩn:**
```python
Port_Is_Web         = {80, 443, 8080, 8443, 8888}   # ← 8080/8443/8888: cổng web PHI CHUẨN của lab
Port_Is_RemoteAccess= {21, 22, 23, 2222, 3389}      # ← 2222: cổng SSH PHI CHUẨN của lab
```
→ **`2222`, `8080`, `8443`, `8888` được thêm tay vào** chính là để **bù cho việc testbed chạy dịch vụ ở cổng
phi chuẩn**. Đây là bằng chứng đội làm **đã lường trước** cơ chế 2 và vá bằng cách **mở rộng danh sách cổng**
để một-hot khớp giữa hai miền.

#### 🎯 Và một cú twist đắt giá — cổng HÓA RA KHÔNG phải nguyên nhân FP (bài học SHAP ≠ ablation)

SHAP xếp **`Port_Is_Web` là đặc trưng #1** đẩy các flow benign thật thành "tấn công" → **nghi nó là thủ phạm**.
Nhưng **ablation** (bỏ hẳn `Port_Is_Web` rồi đo lại FP) cho thấy: nó gây **0% tác động** lên báo giả.

→ **Cổng trông có vẻ quan trọng (SHAP) nhưng KHÔNG gây ra lỗi (ablation).** Thủ phạm thật vẫn là **timing**.
Đây chính là bài học **"quan trọng ≠ nguyên nhân"** (xem mục 5.2 GĐ5).

#### Chốt câu trả lời cho hội đồng

> *"Môi trường thu ảnh hưởng theo **hai đường cổng**. Một, **NAT đổi cổng NGUỒN** — nhưng em tính 5 cờ cổng
> từ **cổng ĐÍCH (dịch vụ)**, nên chúng **miễn nhiễm** với NAT; cái NAT thật sự phá là **timing và TCP window**,
> và KS-test xác nhận đúng như vậy. Hai, **dịch vụ testbed chạy ở cổng phi chuẩn** (SSH 2222, web 8080) —
> cái này em xử lý bằng cách **thêm các cổng đó vào danh sách one-hot** để khớp giữa hai miền. Và điều thú vị:
> SHAP tưởng cổng là thủ phạm báo giả, nhưng ablation chứng minh cổng gây **0%** — thủ phạm thật là timing."*

## 3.2 Bước B — Thử cách RẺ NHẤT: re-fit scaler → **CÒN TỆ HƠN** (21,93% → **6,87%**)

**⭐ Đây là KẾT QUẢ ÂM quan trọng nhất của cả đồ án. Phải nói — nó chứng minh bạn hiểu bản chất.**

**Vì sao re-fit scaler lại làm mọi thứ tệ hơn?**
FT-Transformer gồm scaler $f_{CIC}$ và embedding $g_{CIC}$ — chúng **học CÙNG NHAU**. Embedding
`feature_embeddings[j]` đã học rằng *"z-score 2,0 của đặc trưng j nghĩa là bất thường"* — **theo thang đo của
$f_{CIC}$**. Thay riêng scaler → **cùng một con số vật lý giờ ánh xạ sang z-score khác** → embedding **hiểu sai
toàn bộ**.

> **So sánh:** như đổi đơn vị đo từ **inch sang cm** nhưng **quên báo cho người thợ**. Anh ta vẫn cưa theo con số
> ghi trên bản vẽ — và mọi thứ hỏng **nặng hơn** là nếu cứ để nguyên.

**⭐ NGUYÊN TẮC RÚT RA (câu này rất "ăn" ở hội đồng):**
> **Scaler và tham số model phải đổi ĐỒNG THỜI. Đổi riêng một cái là tạo mâu thuẫn nội bộ.**

## 3.3 Bước C — Layer Freezing: MCC −0,015 → **0,6825**

$$\theta_{fine}^{*}=\arg\min_{\theta_{fine}}\ \mathcal{L}\big(f_{\theta_{freeze},\,\theta_{fine}}(\mathbf{x}_{target}),\ y_{target}\big)$$

- Đóng băng **2/4 tầng thấp** + toàn bộ 77 embedding cũ; chỉ cho tầng cao học.
- **Lý do phân tầng:** tầng attention **THẤP** học biểu diễn **tổng quát** (*"duration ngắn + byte thấp →
  giống PortScan"*) — đúng ở **mọi miền**. Tầng **CAO** học phân biệt **đặc thù miền**.
  → **Đóng băng tầng thấp = giữ kiến thức tổng quát.**

### ⚙️ CODE ĐÓNG BĂNG THẾ NÀO — và VÌ SAO nó làm được (câu hỏi kỹ thuật, phải trả lời được)

Code thật (`4_refit_retrain_v2.py:189-203`):
```python
# (1) đóng băng 77 embedding cũ
for i in range(77):
    for p in model.feature_embedding.feature_embeddings[i].parameters():
        p.requires_grad = False
# (2) đóng băng 2 khối Transformer đầu
for p in model.transformer_blocks[0].parameters(): p.requires_grad = False
for p in model.transformer_blocks[1].parameters(): p.requires_grad = False
# (3) MỞ KHÓA 3 embedding mới
for i in range(77, 80):
    for p in model.feature_embedding.feature_embeddings[i].parameters():
        p.requires_grad = True

# (4) optimizer CHỈ nhận tham số còn requires_grad=True
optimizer = torch.optim.AdamW(
    filter(lambda p: p.requires_grad, model.parameters()), lr=1e-5, weight_decay=1e-4)
```

**Cơ chế đóng băng là HAI ổ khóa độc lập** — hiểu tách bạch hai cái này là trả lời được mọi câu hỏi:

| Ổ khóa | Dòng | Nó chặn cái gì |
|---|---|---|
| **Khóa 1 — `requires_grad = False`** | (1)(2) | Autograd **không tính, không lưu** gradient cho tham số đó. Sau `loss.backward()`, `p.grad` của nó **vẫn là `None`** |
| **Khóa 2 — `filter(...)` khi tạo optimizer** | (4) | Optimizer **không hề nhận** các tham số đóng băng vào danh sách cập nhật → `optimizer.step()` **không có tham chiếu tới chúng** → không thể đụng vào |

**Vì sao cần CẢ HAI (belt-and-suspenders)?**
Khóa 1 một mình **gần đủ** — `step()` bỏ qua tham số có `grad = None`. **Nhưng AdamW có `weight_decay`**, và
weight decay được cộng vào bước cập nhật **độc lập với gradient** → nếu tham số đóng băng vẫn nằm trong optimizer,
weight decay **vẫn co nhỏ trọng số của nó mỗi bước** (dù grad = None). Khóa 2 (`filter`) mới **triệt để** loại
chúng ra, đảm bảo trọng số đóng băng **đứng yên tuyệt đối**.

### 🔑 VÌ SAO code CÓ THỂ đóng băng ở mức từng-đặc-trưng — mấu chốt nằm ở KIẾN TRÚC

Chú ý dòng (1): nó lặp `feature_embeddings[i]` để đóng băng **đúng 77 cái đầu**, chừa 3 cái cuối.
**Chỉ làm được điều này vì Feature Tokenizer là một `nn.ModuleList` gồm các `nn.Linear` RỜI NHAU:**

```python
self.feature_embeddings = nn.ModuleList([nn.Linear(1, d_model) for _ in range(80)])
#                          ↑ 80 module ĐỘC LẬP → mỗi cái có Parameter riêng, địa chỉ riêng
```

→ Có thể **trỏ tay vào từng cái** và bật/tắt `requires_grad` riêng lẻ.

**Nếu dùng MLP thường** (một `nn.Linear(80, d)` chung), 80 đặc trưng **dính chung MỘT ma trận trọng số** →
**không có cách nào** đóng băng 77 cột mà chừa 3 cột: chúng là **cùng một tham số**.
→ **Đây lại là lúc quyết định kiến trúc ở GĐ1 trả cổ tức** (giống Model Surgery).

### 🎯 ĐIỂM TINH TẾ NHẤT — đóng băng block 0,1 nhưng 3 embedding mới VẪN học được

Đây là chỗ dễ hiểu sai, và là câu hỏi "gài" mà hội đồng giỏi hay hỏi:

> *"Block 0 và 1 nằm NGAY SAU embedding (theo chiều forward). Anh đóng băng chúng. Vậy gradient làm sao
> chảy ngược qua chúng để tới 3 embedding mới mà anh muốn train?"*

**Trả lời:** `requires_grad = False` **KHÔNG chặn gradient chảy XUYÊN QUA** một tầng. Nó chỉ ngăn việc
**lưu gradient cho trọng số của chính tầng đó**. Phải phân biệt hai loại gradient:

| Loại gradient | Frozen block 0 có tính không? |
|---|---|
| $\partial L / \partial W_{block0}$ (theo **trọng số** của block 0) | **KHÔNG** — vì $W_{block0}$ có `requires_grad=False`. Đây là cái ta muốn đóng băng |
| $\partial L / \partial (\text{đầu vào của block 0})$ (theo **hoạt hóa** đi vào) | **CÓ** — luôn được tính, vì đây là mắt xích của chain rule để tới các tầng trước |

Chuỗi lan truyền ngược:
```
loss → classifier → block3 → block2 → block1(frozen) → block0(frozen) → embeddings[77:80]
        (học)        (học)    (học)    trọng số ĐỨNG YÊN   trọng số ĐỨNG YÊN   (HỌC ✔)
                                       nhưng tín hiệu VẪN CHẢY QUA →→→→→→→→→→→→→→→→→→
```

→ Gradient **đi ngang qua** block 1 và block 0 (không đọng lại làm đổi trọng số của chúng) rồi **tới được**
3 embedding mới → chúng **vẫn cập nhật bình thường**. **Đóng băng một tầng = "cho tín hiệu đi nhờ qua",
không phải "xây tường chặn".**

> **So sánh:** block 0,1 như **đường cao tốc đã trải nhựa xong** — xe (gradient) vẫn chạy qua để tới đích
> phía sau, nhưng **mặt đường không bị đào lên sửa lại**.

- Optimizer: `AdamW(..., lr=1e-5, weight_decay=1e-4)` — **LR cực nhỏ 1e-5** vì đang **tu sửa** phần chưa đóng băng,
  không xây mới. (Ở đây là **CrossEntropyLoss có class weight**, không phải Focal — khác với V8.5 sau này.)

**Catastrophic Forgetting (CF)** — đo cái giá phải trả:
$$CF = \frac{\text{Acc}_{source,\,before} - \text{Acc}_{source,\,after}}{\text{Acc}_{source,\,before}} \times 100\%$$
Đóng băng 2/4 tầng → **CF = 0,61%** (giữ 99,39% năng lực trên CIC).
→ Cân bằng **plasticity** (học cái mới) và **stability** (giữ cái cũ).

### ⚠️ CAVEAT SỐNG CÒN VỀ MCC 0,6825 — **PHẢI TỰ NÓI TRƯỚC**

Confusion matrix gốc (`Domain_Adaptation_Technical_Log.md`):
```
              dự đoán Benign | dự đoán Malicious
Benign     [        7        |        0        ]     ← CHỈ 7 MẪU BENIGN
Malicious  [        8        |     4527        ]
```

**Tập validation đó chỉ có 7 flow Benign.** MCC 0,6825 tính trên 7 mẫu là **con số có phương sai khổng lồ** —
thêm/bớt 1 mẫu là MCC nhảy vọt. **Nếu hội đồng lật ra thấy: xong.**

**Tự nói trước:**
> *"MCC 0,6825 ở bước này được đo trên tập validation testbed lúc đó **chỉ có 7 flow benign** — em ghi rõ vì
> con số này **không đủ tin cậy về mặt thống kê**. Nó chỉ có ý nghĩa **định tính**: chứng minh Layer Freezing kéo
> model từ 'tệ hơn đoán bừa' về 'có tín hiệu'.*
>
> ***Chính vì tập benign quá nhỏ** mà em kết luận phải **đi thu dữ liệu thật quy mô lớn và retrain hoàn toàn** —
> và đó chính là V8.5."*

→ Câu này **biến một điểm chết thành mạch lập luận** cho quyết định tiếp theo.

## 3.4 Bước D — Model Surgery: 77 → 80 đặc trưng, MCC **0,6825 → 0,7333**

$$
\mathbf{W}^{emb}_{new}=
\begin{bmatrix}
\mathbf{W}^{emb}_{old}\in\mathbb{R}^{77\times d} & \text{(cấy ghép nguyên — transplant)}\\
\mathbf{W}^{emb}_{newrows}\in\mathbb{R}^{3\times d} & \text{(khởi tạo mới, học trong fine-tune)}
\end{bmatrix}
$$

**3 đặc trưng mới đặc thù NAT** (đúng như B.1.9 ghi):
`Custom_IAT_CV`, `Custom_Bwd_Pkt_Ratio`, `Custom_Pkt_Size_Ratio`.

```python
for i in range(77):        param.requires_grad = False    # 77 embedding cũ: ĐÓNG BĂNG
for i in range(77, 80):    param.requires_grad = True     # 3 embedding mới: CHO HỌC
# + đóng băng transformer_blocks[0], [1]
```

> **So sánh:** **ghép thêm 3 ngăn kéo** vào một cái tủ — đồ trong các ngăn cũ vẫn y nguyên, chỉ có 3 ngăn mới
> còn trống chờ sắp đồ.

**⭐ Vì sao FT-Transformer làm được mà RF/XGBoost thì không?**
Vì kiến trúc **token-per-feature** cho phép **nối thêm HÀNG độc lập** vào ma trận embedding.
Cây quyết định **không có ma trận embedding để nối**.
→ **ĐÂY LÀ LÚC QUYẾT ĐỊNH KIẾN TRÚC Ở GĐ1 TRẢ CỔ TỨC.**

⚠️ **Lệch nhỏ:** quyển ghi 3 hàng mới khởi tạo $\mathcal{N}(0; 0{,}01)$; code thực tế dùng **init mặc định của
`nn.Linear(1, d)`** (xavier_uniform cho weight, 0 cho bias). Tinh thần giống nhau (hàng mới bắt đầu **trung tính**,
không phá phần cũ), nhưng **con số cụ thể khác** → sửa quyển cho khớp.

**Vì sao hàng mới phải "trung tính" lúc đầu?** Nếu 3 hàng mới mang tín hiệu quá mạnh ngay từ đầu, chúng sẽ
**bơm nhiễu** vào model đã ổn định → **phá kiến thức cũ**. Trung tính → 3 đặc trưng mới ban đầu **gần như vô hình**,
rồi **lớn dần** khi model thấy chúng hữu ích.

## 3.5 Bước E — Kết luận
> *"Covariate shift quá lớn để chữa bằng kỹ thuật thích nghi. Phải **đi thu dữ liệu thật** và **retrain hoàn toàn**."*
→ **Sinh ra V8.5.**

---
---

# PHẦN 4 — GIAI ĐOẠN 3: V8.5 (model của hệ thống thật)

```python
FTTransformer(num_features=80, num_classes=5,
              d_model=128, num_heads=8, num_layers=4,
              d_ff=512, dropout=0.15, drop_path_rate=0.15)
# → 1.088.005 tham số (verified)
# Lớp: ['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']
```
**Kết quả trong quyển: Macro F1 = 91,7%** trên 5 lớp mô phỏng được (B.2.6).

## 4.1 Vì sao đúng 80 đặc trưng — **bằng chứng số học cho dòng chảy trọng số GĐ2 → GĐ3**

| Nhóm | Số lượng | Ví dụ |
|---|---|---|
| CICFlowMeter gốc | 68 | `Flow_Duration`, `Flow_IAT_Mean`, `SYN_Flag_Count`, `Init_Win_bytes_forward`… |
| Cờ cổng (one-hot thủ công) | 5 | `Port_Is_Web`, `Port_Is_RemoteAccess`, `Port_Is_WellKnown`, `Port_Is_Registered`, `Port_Is_Ephemeral` |
| Tự chế (kế thừa từ GĐ2) | 4 | `Custom_Fwd_Pkt_Rate`, `Custom_Slow_Index`, `Custom_Pkt_Var_Ratio`, `Custom_IAT_Anomaly` |
| **Tự chế (Model Surgery)** | **3** | **`Custom_IAT_CV`, `Custom_Bwd_Pkt_Ratio`, `Custom_Pkt_Size_Ratio`** |

→ 68 + 5 + 4 = **77** — **đúng bằng số đặc trưng của Stage 1 GĐ2** ✔ → **+ 3 = 80**.

**Đây là bằng chứng số học cho thấy V8.5 KẾ THỪA TRỌNG SỐ từ GĐ2**, không train lại từ đầu.

## 4.2 HybridFeatureScaler — "phẫu thuật ở tầng tiền xử lý"

```python
scaler = HybridFeatureScaler(scaler_77_path='.../final_cic_ids_2017/scaler_stage1.pkl')
scaler.fit_custom_scaler(X_train[:, 77:])         # chỉ fit PowerTransformer cho 3 cột mới
X_scaled = hstack([ scaler_77.transform(X[:, :77]),     # ← ĐÔNG CỨNG từ CIC
                    scaler_3.transform(X[:, 77:]) ])    # ← fit mới
```

**⭐ Đây là hệ quả TRỰC TIẾP của bài học Bước B (re-fit scaler thất bại).**
- 77 cột cũ **giữ nguyên scaler của CIC** — vì embedding của chúng đã học theo thang đo đó, **đổi là hỏng**.
- Chỉ 3 cột mới được fit scaler mới — vì embedding của chúng **cũng mới**, chưa học gì.

→ **Scaler và model đổi ĐỒNG THỜI, đúng nguyên tắc rút ra ở Bước B.**
**Nói được câu này là ăn điểm.**

## 4.3 Siêu tham số V8.5 — **B.1.9 hiện đang SAI, đây là bản đúng**

| Tham số | 🔴 B.1.9 ghi | ✅ **Code thật** | Vì sao |
|---|---|---|---|
| Base model | *(không ghi)* | **`v8_4_model.pt`** — `model.load_state_dict(state)` | **KHÔNG random init.** Đây là **fine-tune**, không phải train từ đầu |
| Learning rate | AdamW lr=1e-4 | **Layer-wise: 1e-5 / 1,5e-5 / 3e-5** | Xem dưới |
| Dropout | 0,2 | **0,15** | |
| DropPath | *(không ghi)* | **0,15** | |
| Activation | GELU | **GEGLU** | Khác nhau thật sự |
| Epochs / patience | 50 / 7 | **15 / 5** | V8.4 hội tụ ở epoch 3 → 15 là dư |
| Label smoothing | *(không ghi)* | **0,10** | Cao hơn GĐ2 (0,05) |
| Weight decay | *(không ghi)* | **2e-4** | Gấp đôi GĐ2 (1e-4) |
| Class weights | *(không ghi)* | **√(balanced) → clip[0,5; 2,0] → /mean** | Xem dưới |
| Loss | CB-Focal (γ=2) | `Focal(γ=2.0, weight=cw, label_smoothing=0.10)` ✔ | Khớp |
| Batch / grad clip | 256 ✔ / — | 256 / **1,0** | |
| Split | *(không ghi)* | `train_test_split(test_size=0.1, stratify=y, random_state=42)` | |

**→ Phụ lục B.1.9 PHẢI VIẾT LẠI theo Chương 3.4.5 + code.**
Hai chỗ trong cùng một quyển đang nói hai cấu hình khác nhau cho cùng một model —
**hội đồng chỉ cần lật hai trang là thấy.**

## 4.4 ⭐ Layer-wise Learning Rate (Discriminative Fine-tuning) — lý thuyết cốt lõi GĐ3

```python
backbone (feature_embedding + transformer_blocks[0,1]) : lr = 1e-5      # gần như đóng băng
mid      (transformer_blocks[2,3] + norm)              : lr = 1.5e-5
head     (classifier)                                   : lr = 3e-5      # chỉnh mạnh nhất, gấp 3×
```

**Trực giác:** tầng thấp học thứ **tổng quát** (đúng ở mọi miền) → **đụng vào là phá**.
Tầng cao học thứ **đặc thù nhiệm vụ** → **cần chỉnh mạnh** cho miền mới.

> **So sánh:** tu sửa một căn nhà tốt sẵn — **móng và tường chịu lực gần như không đụng** (1e-5),
> **nội thất sửa mạnh** (3e-5). **Không ai đập móng để đổi màu tường.**

**Đây là "Layer Freezing phiên bản MỀM":** thay vì `requires_grad=False` (LR = 0 tuyệt đối), ta cho LR
**rất nhỏ** — tầng thấp **vẫn được chỉnh vi mô** để thích nghi, nhưng **không thể trôi xa**.

## 4.5 🎯 Vì sao GĐ3 BỎ Warmup và BỎ EMA? (câu hỏi GHI ĐIỂM)

> *"**Warmup sinh ra để bảo vệ giai đoạn trọng số NGẪU NHIÊN**: lúc mới khởi tạo, trọng số vô nghĩa,
> learning rate lớn ngay bước 1 sẽ đẩy model đi lung tung.*
>
> ***Giai đoạn 3 KHÔNG có trọng số ngẫu nhiên*** *— nó bắt đầu từ một model đã tốt. **Không có gì để bảo vệ**
> → warmup vô nghĩa, thậm chí **có hại** (làm chậm quá trình bám vào miền mới).*
>
> *EMA cũng vậy: nó làm mượt **dao động** của train-from-scratch. Fine-tune với LR 1e-5 **gần như không dao động** —
> EMA chỉ tốn bộ nhớ.*
>
> *Nguyên tắc: **dùng đúng công cụ cho đúng tình huống, thay vì bê nguyên cấu hình cũ.**"*

## 4.6 Class weight — công thức 4 bước **có lịch sử**

```python
cw = compute_class_weight('balanced', ...)   # w_c = N / (K · n_c)
cw = np.sqrt(cw)                             # (1) làm dịu
cw = np.clip(cw, 0.5, 2.0)                   # (2) chặn hai đầu
cw = cw / cw.mean()                          # (3) chuẩn hóa về mean = 1
```

- **(1) Căn bậc hai** — trọng số balanced thuần cho lớp cực hiếm ra giá trị khổng lồ (lớp chiếm 0,1% → $w=200$).
  $\sqrt{200}=14{,}1$: **vẫn ưu tiên, nhưng không để một lớp bé xíu lái toàn bộ gradient.**
- **(2) Clip [0,5 ; 2,0]** — **bài học từ V8.3:** class weight 1,565 quá cao → **Brute Force F1 sập từ 91,9%
  xuống 50%** vì FP tăng vọt. **Con số này CÓ LỊCH SỬ — hãy kể nó, đừng chỉ đọc con số.**
- **(3) Chuẩn hóa mean = 1** — giữ độ lớn tổng của loss ổn định, để **learning rate không bị đổi nghĩa ngầm**
  khi số lớp thay đổi.

## 4.7 ⭐ Bài học VAL SET — B.2.7, phải nói (đây là đóng góp phương pháp thật)

| | Val set | Macro F1 |
|---|---|---|
| **V8.4** | **đồng nhất** (toàn CIC) | **94,95%** ← **INFLATE** |
| **V8.5** | **đa dạng miền** (mix testbed + CIC) | **91,7%** ← **THẬT HƠN** |

> *"V8.4 đạt 94,95% nhưng con số đó **lạc quan giả** vì val set toàn CIC — cùng phân phối với train.
> Khi em **đa dạng hóa val set** (trộn testbed thật + CIC), Macro F1 tụt về 91,7%. **Con số thấp hơn nhưng
> TRUNG THỰC hơn.***
>
> ***Bài học: val set đa dạng miền thì metric mới thật.** Một model 'tốt hơn' trên val đồng nhất có thể
> **tệ hơn** ngoài đời."*

→ Đây chính là **câu trả lời chuẩn bị sẵn** cho *"vì sao GĐ3 (91,7%) thấp hơn GĐ2 (92,9%)?"*:
**hai con số không so sánh được** (khác dataset, khác số lớp), và **91,7% được đo trên val khắt khe hơn nhiều**.

## 4.8 GIAI ĐOẠN 3 — NÊN NÓI GÌ

| Hỏi | Trả lời |
|---|---|
| *"V8.5 train từ đầu à?"* | **"KHÔNG."** *"`model.load_state_dict(v8_4)` — nạp trọng số có sẵn, rồi fine-tune với layer-wise LR 1e-5/1,5e-5/3e-5. Đây là **transfer learning**, và nó chỉ tồn tại được **nhờ** giai đoạn 2."* |
| *"Sao F1 GĐ3 (91,7%) thấp hơn GĐ2 (92,9%)?"* | *"**Hai con số không so sánh được** — khác dataset, khác số lớp (9 vs 5). Và 91,7% được đo trên **val đa dạng miền**, khắt khe hơn nhiều so với val đồng nhất (V8.4 val toàn CIC cho 94,95% — inflate)."* |
| *"Sao không train thẳng trên testbed cho xong?"* | *"Testbed lúc đó chỉ có **~37 flow benign**. Model có **1,09 triệu tham số**. Train 1,09 triệu tham số trên vài chục flow = **học vẹt**. Model cần biết trước 'flow tấn công trông thế nào' — kiến thức đó đến từ **2,5 triệu flow CIC ở giai đoạn 2**."* |
| *"Vì sao 3 đặc trưng mới?"* | *"Vì môi trường NAT làm lệch IAT và tỉ lệ gói chiều ngược. `IAT_CV` đo độ biến thiên IAT, `Bwd_Pkt_Ratio` và `Pkt_Size_Ratio` đo bất đối xứng hai chiều — đúng những thứ NAT làm méo."* |
| *"Dropout của V8.5 là bao nhiêu?"* | **"0,15"** *(KHÔNG phải 0,2 như B.1.9 — B.1.9 đang sai, Chương 3.4.5 mới đúng)* |

---
---

# PHẦN 4B — MLP vs TRANSFORMER & HAI HÌNH THỨC HUẤN LUYỆN

> Hai câu hỏi này **hay bị hỏi** và **hay bị lẫn vào nhau**. Chúng là **HAI TRỤC ĐỘC LẬP**:
> - **Trục kiến trúc:** dùng **MLP** hay **Transformer**? (chọn *hình dạng* model)
> - **Trục huấn luyện:** **train từ đầu** hay **fine-tune**? (chọn *cách* dạy model)
> Trả lời tách bạch hai trục là dấu hiệu hiểu sâu.

## 4B.1 — MLP vs Transformer: khác nhau ở BẢN CHẤT nào

Đừng trả lời "Transformer mạnh hơn" — đó là câu của người thuộc. Khác biệt nằm ở **cách xử lý đặc trưng**.

### Bảng đối chiếu chi tiết

| Tiêu chí | **MLP thường** | **FT-Transformer (đồ án dùng)** |
|---|---|---|
| **Tầng đầu vào** | **Một** `Linear(80, d)` — nhân **cả vector 80 chiều** với một ma trận $80 \times d$ | **80** `Linear(1, d)` **riêng** — mỗi đặc trưng nhân với ma trận $1 \times d$ **của riêng nó** |
| **Đầu vào biến thành gì** | **Một** vector $d$ chiều (đã trộn hết) | **80 token**, mỗi token $d$ chiều + 1 token `[CLS]` → chuỗi 81 |
| **"Danh tính" của đặc trưng** | **Mất ngay tầng 1** — sau khi cộng gộp, không còn biết chiều nào là `duration`, chiều nào là `src_bytes` | **Giữ nguyên xuyên suốt** — token thứ $j$ luôn là đặc trưng $j$ |
| **Học tương tác đặc trưng** | **Gián tiếp** — phải chồng nhiều tầng, tương tác "ngấm" dần qua trọng số | **Trực tiếp** — attention tính $QK^\top$, **một phép nhân ra ngay** cặp đặc trưng nào liên quan |
| **Tương tác phụ thuộc mẫu?** | Không — trọng số **cố định** sau train, mọi mẫu trộn như nhau | **Có** — attention weight **đổi theo từng flow** ($Q,K$ phụ thuộc đầu vào) |
| **Đọc/giải thích được?** | ❌ Trộn rồi thì mất dấu, không rút ra "đặc trưng nào soi đặc trưng nào" | ✅ **Ma trận attention** đọc được: token nào chú ý token nào |
| **➕ Thêm/bớt đặc trưng** | ❌ **Phải train lại từ đầu** — ma trận $80{\times}d$ đổi thành $83{\times}d$, **toàn bộ trọng số vô nghĩa** | ✅ **Ghép thêm 3 token** ($\to$ 83 module), **giữ nguyên 80 cái cũ** — **Model Surgery** |
| **🧊 Đóng băng chọn lọc** | ❌ Không thể — 80 đặc trưng **chung một ma trận**, một tham số | ✅ Đóng băng **77 module cũ**, chỉ học **3 module mới** — mỗi đặc trưng một `nn.Linear` rời |
| **Chi phí tính toán** | **Rẻ** — vài phép nhân ma trận | **Đắt hơn** — attention là $O(N^2)$ theo số token ($N{=}81$) |
| **Số tham số (ước lượng)** | Ít hơn (không có Q/K/V) | Nhiều hơn (~1,09M cho V8.5) — cái giá của attention |
| **Mạnh trên dữ liệu bảng?** | Khá, nhưng thường **thua cây** (LightGBM/XGBoost) | Cạnh tranh; **cũng thua LightGBM trên bảng NHỎ** (xem dưới) |
| **Xử lý đặc trưng phân loại** | Cần one-hot bên ngoài rồi trộn chung | Mỗi giá trị/đặc trưng thành token riêng — tự nhiên hơn |
| **Trong đồ án** | Chỉ dùng làm **baseline so sánh** (GĐ1) | **Xương sống** của 4/9 model, kể cả hệ thống cuối V8.5 |

### 🔬 Cụ thể hóa bằng số — chỗ khác biệt SỐNG CÒN nằm ở tầng đầu vào

Giả sử hai đặc trưng đều có giá trị **100**: `duration = 100` (giây) và `src_bytes = 100` (byte).
Chúng **cùng con số nhưng khác hẳn ý nghĩa**. Xem tầng đầu vào của hai kiến trúc xử lý ra sao:

**MLP —** một ma trận $W \in \mathbb{R}^{80 \times d}$ nhân với **cả vector**:
$$h = W^\top x = \underbrace{w_{\text{duration}} \cdot 100}_{\text{cột duration}} + \underbrace{w_{\text{src\_bytes}} \cdot 100}_{\text{cột src\_bytes}} + \dots \text{(cộng gộp 80 cột)}$$
→ Kết quả là **một vector đã cộng dồn**. Đóng góp của `duration` và `src_bytes` **đã hòa vào nhau** —
tầng sau **không còn cách nào tách** "phần nào của $h$ đến từ duration". **Danh tính đặc trưng bốc hơi.**

**FT-Transformer —** mỗi đặc trưng đi qua `Linear(1, d)` **riêng**:
$$t_{\text{duration}} = w_{\text{dur}} \cdot 100 + b_{\text{dur}}, \qquad t_{\text{src\_bytes}} = w_{\text{sb}} \cdot 100 + b_{\text{sb}}$$
→ **Hai token TÁCH BIỆT**, mỗi cái mang "ngôn ngữ" riêng của đặc trưng đó. Cùng số 100 nhưng
$t_{\text{duration}} \ne t_{\text{src\_bytes}}$ vì $w_{\text{dur}} \ne w_{\text{sb}}$. **Danh tính được giữ.**

> **Đây là toàn bộ lý do** Model Surgery và Layer Freezing khả thi: bạn chỉ **đóng băng/ghép** được thứ mà bạn
> vẫn còn **địa chỉ riêng** để trỏ tới. MLP trộn hết vào một cục — không còn địa chỉ nào để trỏ.

**Câu chốt — nói đúng câu này:**
> *"Khác biệt cốt lõi không phải 'mạnh/yếu', mà là **MLP trộn hết đặc trưng ngay tầng đầu**, còn FT-Transformer
> **giữ mỗi đặc trưng thành một token độc lập**. Chính sự độc lập đó cho phép hai thứ mà MLP không làm được:
> **Model Surgery** (ghép thêm đặc trưng mà không train lại) và **Layer Freezing chọn lọc** (đóng băng
> 77 đặc trưng, chỉ học 3 cái mới). Với đồ án phải **thích nghi miền bằng ít dữ liệu**, hai khả năng đó là
> sống còn."*

**Nhưng phải TRUNG THỰC — Transformer KHÔNG luôn thắng:**
> *"Trên NSL-KDD (dữ liệu bảng nhỏ), **LightGBM THẮNG FT-Transformer** (0,6678 vs 0,6535). Cây quyết định
> vẫn rất mạnh trên bảng. Em không chọn Transformer vì nó 'mạnh hơn' — em chọn vì nó có **khả năng phẫu thuật
> kiến trúc** mà cây và MLP đều không có. Đó là lý do em **kết hợp** (ensemble) ở GĐ1-2 thay vì loại bỏ cây."*

## 4B.2 — Hai hình thức huấn luyện: TRAIN TỪ ĐẦU vs FINE-TUNE

| | **Train from scratch (train từ đầu)** | **Fine-tune (tinh chỉnh)** |
|---|---|---|
| Trọng số ban đầu | **Ngẫu nhiên** | **Nạp từ model đã có** (`load_state_dict`) |
| Dùng khi nào | Chưa có model nào, hoặc **không gian đặc trưng đổi hoàn toàn** | Đã có model tốt trên miền gần, **muốn giữ kiến thức cũ** |
| Learning rate | Lớn (1e-4) + **cần warmup** bảo vệ giai đoạn ngẫu nhiên | Rất nhỏ (1e-5) + **bỏ warmup** (không có trọng số ngẫu nhiên để bảo vệ) |
| Rủi ro | Cần **nhiều dữ liệu**, không thì học vẹt | **Catastrophic forgetting** (quên miền cũ) nếu LR quá lớn |
| Trong đồ án | **GĐ1, GĐ2** | **GĐ3 (V8.5)** |

### Mỗi giai đoạn dùng hình thức nào — và VÌ SAO

| Giai đoạn | Hình thức | Vì sao **buộc** phải vậy |
|---|---|---|
| **GĐ1 (NSL-KDD)** | Train từ đầu | Chưa có model nào trước đó |
| **GĐ2 (CIC)** | Train từ đầu | **Không gian đặc trưng đổi hoàn toàn**: 122 one-hot (NSL) → 77 CICFlowMeter. **Không thể** nạp trọng số của model 122 chiều vào model 77 chiều — shape không khớp, ý nghĩa cột cũng khác |
| **GĐ3 (V8.5)** | **Fine-tune** | 77 đặc trưng CIC **giữ nguyên** + thêm 3 → **nạp được** trọng số GĐ2. Testbed **quá ít dữ liệu** (~37 flow benign lúc đầu) để train từ đầu 1,09 triệu tham số → **buộc** phải fine-tune |

**→ Đây chính là mấu chốt của nhận xét "3 giai đoạn không khác nhau":**
Ba giai đoạn **KHÔNG phải ba lần train lại cùng một model**. Chỉ **HAI lần đầu train từ đầu** (và buộc phải
tách rời vì không gian đặc trưng không tương thích). **Giai đoạn 3 là fine-tune** — nạp trọng số GĐ2, ghép
đặc trưng, tinh chỉnh nhẹ. **Đó là transfer learning, không phải huấn luyện lại.**

### Câu hỏi gộp cả hai trục (hội đồng hay hỏi kiểu này)

| Hỏi | Trả lời |
|---|---|
| *"Sao GĐ2 không fine-tune từ GĐ1 cho đỡ tốn?"* | *"Vì **không gian đặc trưng khác hẳn**: NSL-KDD 122 chiều one-hot, CIC 77 chiều số thực. Nạp trọng số của cái này vào cái kia là **vô nghĩa** — như đưa chìa khóa nhà cho người ở thành phố khác. Fine-tune chỉ áp dụng được khi hai miền **cùng bộ đặc trưng** — đó là GĐ2 → GĐ3."* |
| *"Sao GĐ3 không train từ đầu cho sạch?"* | *"Testbed chỉ có **~37 flow benign** lúc đầu. Train 1,09 triệu tham số trên vài chục flow = **học vẹt**. Kiến thức 'flow tấn công trông thế nào' phải đến từ **2,5 triệu flow CIC** ở GĐ2 — nên em **fine-tune** để giữ lại nó."* |
| *"Sao không dùng MLP cho gọn?"* | *"Vì MLP **trộn hết đặc trưng ngay tầng đầu** → mất khả năng **Model Surgery** và **Layer Freezing chọn lọc**. Mà cả hai đúng là thứ cứu GĐ3 khi phải thích nghi miền bằng ít dữ liệu."* |

---
---

# PHẦN 5 — BẢNG ĐỐI CHIẾU 3 GIAI ĐOẠN (in ra, học thuộc)

| | **GĐ1 — NSL-KDD** | **GĐ2 — CIC-IDS-2017** | **GĐ3 — V8.5** |
|---|---|---|---|
| **Câu hỏi** | Transformer ăn được dữ liệu bảng không? | Chịu nổi quy mô + mất cân bằng không? | Sống được với traffic THẬT không? |
| **Kẻ thù** | Chính giả thuyết | **Imbalance** (Heartbleed 10 mẫu) | **Covariate shift** (lab ≠ thật) |
| **Khởi tạo trọng số** | ngẫu nhiên | ngẫu nhiên | **nạp V8.4 → fine-tune** |
| **Nhận trọng số từ GĐ trước?** | — | **KHÔNG** (122 one-hot ≠ 77 CICFlowMeter) | **CÓ** (Model Surgery 77→80) |
| **Số đặc trưng** | 122 (one-hot) | 77 (S1) / 34 (S2) | **80** (77 kế thừa + 3 mới) |
| **Số lớp** | 5 (stacking) / 4 (bản deploy) | 6 (S1) + 5 (S2) → **9** cuối | 5 |
| **Kiến trúc** | FTT **V1** (chỉ dropout) | FTT **V2** (+DropPath +LayerScale +GEGLU) | FTT **V2** (như GĐ2) |
| **Scaler** | MinMaxScaler | **PowerTransformer Yeo-Johnson** | **HybridFeatureScaler** (77 đông cứng + 3 fit mới) |
| **Cân bằng dữ liệu** | SMOTE + WeightedSampler + Focal α class-balanced | **Borderline-SMOTE + ENN** (min 30k) + class weight ×1,5 + **HNM** | **√(balanced) + clip[0,5; 2,0]** |
| **Loss** | Focal γ=2,0, LS=0 | Focal **γ=2,0** (S1) / **γ=1,5** (S2), LS=0,05 | Focal **γ=2,0**, LS=**0,10** |
| **Dropout / DropPath** | 0,1 / — | 0,2 / 0,1 | **0,15 / 0,15** |
| **Optimizer** | AdamW lr=1e-4 | AdamW lr=1e-4, wd=1e-4 | AdamW **layer-wise** 1e-5/1,5e-5/3e-5, wd=**2e-4** |
| **Scheduler** | Plateau | **Warmup(3) + Cosine** | Cosine, **BỎ warmup** |
| **EMA** | không | **có (0,999)** | **BỎ** |
| **Epochs** | 20 (patience 6) | 15 (S1) / 20 (S2) | 15 (patience 5) |
| **Kiến trúc hệ thống** | AE Gate + Stacking (LGBM + FTT + Meta-LR) | **Cascade 2 tầng** + RF/KNN veto | **1 model phẳng** + Snort |
| **Val set** | tách riêng (U2R chỉ 5 mẫu ⚠️) | ⚠️ **val = test** | tách riêng, **đa dạng miền** ✅ |
| **Kết quả** | Macro F1 **0,6809** | Macro F1 **0,9294** (9 lớp) | Macro F1 **91,7%** (5 lớp) |
| **Bàn giao gì** | **Kiến trúc** (Feature Tokenizer) | **Trọng số backbone 77 đặc trưng** | Hệ thống thật |

## ⚠️ CẢNH BÁO KHI TRÌNH BÀY

**KHÔNG xếp 3 con số F1 (0,68 / 0,93 / 0,92) lên cùng một trục.** Chúng khác dataset, khác số lớp (5/9/5)
→ **không so sánh được**, và trông như **"tụt lùi" ở GĐ3**.

**Thay bằng cặp số NỘI BỘ của từng giai đoạn** (trước/sau khi áp vũ khí mới):

| Giai đoạn | Cặp số chứng minh vũ khí có tác dụng |
|---|---|
| **GĐ1** | FTT 0,6535 · LGBM 0,6678 · soft-voting **thất bại** (α*=1,0) → **Stacking 0,6809** |
| **GĐ2** | FTT đơn lẻ sau HNM 0,6512 (Bot) → **Asymmetric Voting 0,7344** · Macro F1 **0,9294** |
| **GĐ2 (HNM)** | class weight ×10 → Bot F1 0,5103 → **HNM 2 vòng → 0,6512** |
| **GĐ3** | direct transfer MCC **−0,015** → freezing **0,6825** → surgery **0,7333** |
| **GĐ3 (val)** | V8.4 val đồng nhất **94,95%** (inflate) → V8.5 val đa dạng **91,7%** (thật) |

---
---

# PHẦN 6 — LÝ THUYẾT: đã nêu / CHƯA nêu / đã loại

## 6.1 ✅ Đã dùng VÀ đã nêu trong quyển

| Lý thuyết | GĐ | Công thức lõi | Câu chốt một dòng |
|---|---|---|---|
| **Feature Tokenizer** | 1,2,3 | $t_j = \mathbf{w}_j x_j + \mathbf{b}_j$ | Mỗi đặc trưng một Linear riêng → **mới làm được Model Surgery** |
| **Multi-Head Self-Attention** | 1,2,3 | $\text{softmax}(QK^\top/\sqrt{d_k})V$ | Học tương tác cặp-đặc-trưng **trực tiếp** |
| **CLS token** | 1,2,3 | $x[:,0,:]$ | "Thư ký cuộc họp" — **HỌC** cách tổng hợp, khác mean-pooling |
| **Autoencoder / lỗi tái tạo** | 1 | $\text{MSE}(x,\hat{x})$ | Cổ chai 16 chiều ép model học "bản chất" benign |
| **Focal Loss (CB-Focal)** | 1,2,3 | $-\alpha_t(1-p_t)^\gamma\log p_t$ | γ=2: **mẫu khó được quan tâm gấp 49× mẫu dễ** |
| **Stacking** | 1 | Meta-LR trên 10 chiều xác suất | **Soft-voting THẤT BẠI (α*=1,0)** → phải stacking |
| **Cascade 2 tầng** | 2 | — | **Lớp đông ở tầng 1, lớp hiếm ở tầng 2** → gradient không bị đè |
| **Hard Negative Mining** | 2 | — | class weight ×10 → 0,5103; **HNM → 0,6512** |
| **Asymmetric Ensemble Voting** | 2 | — | **Chi phí sai khác nhau → luật khác nhau** |
| **Random Forest / KNN** | 2 | — | `max_features=20` **là chữ "Random"**; k=16 |
| **Yeo-Johnson** | 2,3 | **4 nhánh** (2 cho $y\ge0$, 2 cho $y<0$), 1 tham số $\lambda$ ước lượng bằng MLE | Bẻ thẳng đuôi dài; **xử lý được cả 0 và số âm** (khác log/Box-Cox) — và dữ liệu **có số âm thật**: `Init_Win_bytes_backward = −1` |
| **Covariate Shift** | 3 | $P_s(x)\ne P_t(x)$ | Acc 99,55% → 21,93%; **MCC → −0,015** |
| **Layer Freezing** | 3 | $\arg\min_{\theta_{fine}}$ | Tầng thấp = tổng quát (giữ); tầng cao = đặc thù miền (học lại) |
| **Catastrophic Forgetting** | 3 | $CF=\Delta\text{Acc}_{src}/\text{Acc}_{src}$ | Đóng băng 2/4 tầng → **CF = 0,61%** |
| **Model Surgery** | 3 | $W_{new}=[W_{old}; W_{newrows}]$ | Ghép 3 ngăn kéo mới, giữ nguyên 77 ngăn cũ |
| **Label Smoothing** | 2,3 | $y=(1-\varepsilon)y_{oh}+\varepsilon/C$ | ε: 0,05 (GĐ2) → 0,10 (GĐ3) |

## 6.2 🔴 ĐANG DÙNG NHƯNG **CHƯA NÊU** — nên bổ sung vào quyển

**Nhóm nguy hiểm: đang chạy trong code, sinh ra kết quả, nhưng KHÔNG có trong quyển.**
Hội đồng mở code ra hỏi là không trả lời được.

| Lý thuyết | Ở đâu | Vì sao phải nêu |
|---|---|---|
| **Borderline-SMOTE** | GĐ2 S1 | Khác SMOTE thường — **chỉ sinh mẫu ở VÙNG BIÊN GIỚI**, nơi model thực sự sai |
| **ENN (Edited Nearest Neighbours)** | GĐ2 S1+S2 | Bước **dọn dẹp SAU SMOTE**: xóa mẫu sinh nhầm vào vùng lớp khác |
| **`max(30000, count)`** | GĐ2 | Nâng mọi lớp lên ≥ 30k — **con số fix cứng chưa được biện minh ở đâu** |
| **Duplicate-to-6 hack** | GĐ2 S2 | Heartbleed 10 mẫu → SMOTE cần ≥ 6 → **nhân bản** |
| **EMA (0,999)** | GĐ2 | $\theta_{EMA}\leftarrow 0{,}999\theta_{EMA}+0{,}001\theta$. **Stage 2 inference dùng EMA, Stage 1 dùng bản thường** — bất đối xứng |
| **Effective Number (class-balanced α)** | GĐ1 | $E_n=(1-\beta^n)/(1-\beta)$ — **không phải $1/n$ thô** |
| **Warmup LR (3 epoch)** | GĐ2 | Bảo vệ giai đoạn trọng số ngẫu nhiên. **GĐ3 BỎ vì không còn trọng số ngẫu nhiên** — điểm ghi điểm |
| **Layer-wise LR (Discriminative FT)** | GĐ3 | 1e-5 / 1,5e-5 / 3e-5 — **"Layer Freezing phiên bản mềm"** |
| **DropPath / Stochastic Depth** | GĐ2,3 | Tắt **cả một tầng**, tỉ lệ **tăng dần theo độ sâu** |
| **LayerScale (1e-4)** | GĐ2,3 | Mỗi tầng bắt đầu **~vô hình**, tự học tăng dần |
| **GEGLU** | GĐ2,3 | $x_1\odot\text{GELU}(x_2)$ — activation **có cổng**. **Là lý do `d_ff*2`**. (B.1.9 đang ghi nhầm là GELU) |
| **Gradient Clipping (1,0)** | GĐ2,3 | Một batch dị thường không làm nổ weight |
| **AMP (Mixed Precision)** | GĐ2 | float16 → nhanh ~2× |
| **G-mean** | GĐ2 | $(\prod_c\text{recall}_c)^{1/C}$ — **một lớp recall = 0 thì G-mean = 0 NGAY** |
| **Youden's J** | GĐ1 | $\arg\max(TPR-FPR)$ — cách chọn ngưỡng AE (quyển đang ghi nhầm là percentile 95) |
| **MCC** | GĐ3 | Chỉ số cho tập lệch lớp; **âm = tệ hơn đoán bừa** |
| **Gap-based early stopping** | GĐ1 | Dừng khi `train_f1 − val_f1 > 0,12` |
| **√ + clip class weight** | GĐ3 | Bài học từ V8.3 (BF F1 sập 91,9% → 50%) |

## 6.3 ✅ Đã cân nhắc và **LOẠI BỎ** — nên nêu (chứng minh có suy nghĩ, không phải chọn bừa)

| Phương án | Vì sao loại |
|---|---|
| **MLP thường** (một Linear chung) | Trộn hết đặc trưng ngay tầng đầu → **không còn "token của đặc trưng j"** → Attention **không có gì để so sánh**; và **mất luôn khả năng Model Surgery** |
| **Cây làm model chính** | Rất mạnh trên bảng — thực tế **LightGBM THẮNG FTT ở GĐ1**. Nhưng cây học tương tác bằng **chẻ nhánh liên tiếp**, kém khi tương tác liên tục & mượt; và **không làm được Model Surgery**. → **Không loại bỏ mà KẾT HỢP** (ensemble ở GĐ1 và GĐ2) |
| **StandardScaler (z-score)** | Giả định phân phối gần chuẩn. Đặc trưng mạng **lệch phải cực mạnh** → z-score không sửa được độ lệch |
| **MinMaxScaler cho CIC** | Một outlier duy nhất định nghĩa cả `max` → phần còn lại **nén về ~0** |
| **Một model phẳng 9 lớp** | Phải học 2 nhiệm vụ khó dưới 1 hàm mất mát + chịu mất cân bằng toàn cục. **Đây là baseline mà cascade đánh bại** |
| **Adversarial DA (DANN)** | Cần **nhiều dữ liệu miền đích** + train đối kháng khó ổn định. Thời điểm GĐ3 testbed chỉ có **~37 flow benign** |
| **Re-fit scaler** (giữ nguyên model) | **Đã thử: 21,93% → 6,87%.** Scaler và model **phải đổi đồng thời** |
| **Autoencoder làm cổng cho hệ cuối** | Ngưỡng lỗi tái tạo **cực nhạy với domain shift** — mà shift **chính là vấn đề lớn nhất** của đồ án |

---
---

# PHẦN 7 — THAM SỐ FIX CỨNG (trong phạm vi quyển)

| Giá trị | Ở đâu | Nghĩa — to/nhỏ thì sao |
|---|---|---|
| **0,008481** | AE threshold (`inference_config.json`) | MSE ≥ τ → Suspicious. **Đông cứng từ một lần chạy ROC Youden trên train** → đổi dữ liệu là phải fit lại |
| **16** | AE bottleneck | To → copy nguyên đầu vào (mất khả năng phát hiện); nhỏ → báo động loạn |
| **38 / 41 / 111 / 122** | `DEFAULT_FEATURE_GROUPS` | Ranh giới one-hot NSL-KDD (numeric / protocol / service / flag) |
| **5** | `per_class_val_max = {4: 5}` | ⚠️ **Val chỉ có 5 mẫu U2R** — Meta-LR học lớp U2R từ 5 mẫu |
| **30000** | SMOTE strategy GĐ2 | `max(30000, count)` cho mọi lớp. To hơn → overfit nhiễu SMOTE; nhỏ hơn → lớp hiếm vẫn bị đè |
| **6** | Duplicate hack GĐ2 S2 | SMOTE cần ≥ 6 mẫu → **nhân bản Heartbleed** cho đủ |
| **1,5×** | Class weight GĐ2 S2 | Nhân thêm cho Web Attack / Infiltration / Heartbleed. **Heuristic** |
| **0,999** | EMA decay GĐ2 | |
| **1,0** | Grad clip (GĐ2, GĐ3) | Chặn norm gradient |
| **0,85** | `THRESHOLD` cascade | ⚠️ **GIẢM FP** (không phải "ưu tiên recall" như quyển viết). Cao hơn → ít flow xuống Stage 2, bỏ sót nhiều; thấp hơn → Stage 2 quá tải, FP tăng |
| **0,65** | Soft threshold FTT Stage 2 | **Van giảm FP ẩn — quyển hoàn toàn không nhắc.** Ảnh hưởng trực tiếp recall mọi lớp hiếm |
| **[0,65 · 0,68 · 0,70]** | `infiltration_thresholds` | **Cả 3 cho kết quả Y HỆT** → không ảnh hưởng kết quả |
| **[0,5 ; 2,0]** | Class weight clip V8.5 | **Bài học từ V8.3**: weight 1,565 → **BF F1 sập 91,9% → 50%** |
| **1e-5 / 1,5e-5 / 3e-5** | Layer-wise LR V8.5 | backbone / mid / head. Backbone cao hơn → **phá kiến thức CIC**; head thấp hơn → **không thích nghi được miền mới** |
| **1e-4** | LayerScale init | Mỗi tầng bắt đầu ~vô hình |
| **2e-4** | Weight decay V8.5 | Gấp đôi GĐ2 |

---
---

# PHẦN 8 — 6 ĐIỂM YẾU TỰ BIẾT (nói TRƯỚC khi bị hỏi)

> **Nguyên tắc vàng:** một điểm yếu **bạn tự nêu** = bằng chứng bạn hiểu sâu.
> Cùng điểm yếu đó **bị hội đồng moi ra** = bằng chứng bạn không kiểm soát được đồ án của mình.

| # | Điểm yếu | Câu trả lời chuẩn bị sẵn |
|---|---|---|
| 1 | **GĐ2: val = test** (chọn checkpoint trên chính tập báo cáo) | *"0,9294 là **cận trên**. Em tự phát hiện khi rà soát. **GĐ3 đã sửa**: val tách riêng và **đa dạng hóa miền** — chính vì thế V8.5 báo 91,7% chứ không phải 94,95% inflate của V8.4."* |
| 2 | **MCC 0,6825 đo trên 7 mẫu benign** | *"Không đủ tin cậy thống kê, chỉ có ý nghĩa **định tính**. **Chính vì tập benign quá nhỏ** mà em quyết định thu dữ liệu thật và **retrain hoàn toàn** → V8.5."* |
| 3 | **Meta-LR fit trên val có 5 mẫu U2R** | *"Giới hạn của NSL-KDD. Đây **chính là lý do** Macro F1 GĐ1 chỉ 0,68, và là một lý do chuyển sang CIC-IDS-2017."* |
| 4 | **Heartbleed F1=1,0 trên 10 mẫu · Infiltration 33 mẫu** | *"Em báo cáo nhưng **không dựa vào** chúng để kết luận. Infiltration recall 61% là **giới hạn của dữ liệu**: hành vi sau xâm nhập không lộ ra ở tầng flow."* |
| 5 | **B.1.9 mâu thuẫn với Chương 3.4.5** | **Sửa TRƯỚC KHI IN.** Nếu không kịp: *"Phụ lục B.1.9 có sai sót biên tập; cấu hình đúng là Chương 3.4.5 — dropout 0,15, layer-wise LR, 15 epoch."* |
| 6 | **Quyển kể sai cascade (6/5 lớp) và ngưỡng 0,85** | **Sửa TRƯỚC KHI IN.** Sửa lại thì **lập luận mạnh hơn** — xem Phần 2. |

### Bonus — 2 lỗi cấu hình tự phát hiện (nêu ra là ghi điểm "biết code của mình")
- **LightGBM `subsample=0.8` KHÔNG hoạt động** vì thiếu `subsample_freq` → **bagging chưa từng chạy**.
- **`d_ff=512` là giá trị mặc định NGẦM**, không phải 256 như B.1.6 ghi. Kiểm chứng từ shape checkpoint `(1024, 64)`.

---

# PHẦN 9 — GHI CHÚ: những gì NGOÀI phạm vi quyển

Repo còn có **v8.6, v8.7, temperature scaling, ngưỡng per-class, hệ replay/live** —
**KHÔNG có trong quyển**, nên **không trình bày**. Nhưng cần biết 2 điều để không bị bất ngờ:

1. **Hệ demo live đang chạy đúng V8.5** (`replay_config.json` → `models/v8_5_model.pt`) → **nhất quán với quyển** ✅
2. Nếu hội đồng hỏi *"hệ thống có báo động giả nhiều không khi chạy thật?"* → trả lời trung thực:
   *"Trên traffic benign thật thu được, V8.5 có tỉ lệ báo động giả đáng kể. Em đã có **hướng xử lý đã kiểm chứng**
   — bổ sung benign thật vào tập huấn luyện và fine-tune — nhưng đó là **công việc sau phạm vi quyển**,
   em ghi vào phần hướng phát triển."*
   → **Đừng nêu số nếu không hỏi. Nêu số ngoài quyển = mời hội đồng đào sâu vào thứ chưa viết.**

---

# PHẦN 10 — 5 CÂU CHỐT PHẢI THUỘC

1. **"Ba giai đoạn không phải ba lần train lại."** Chỉ **hai** lần đầu train từ đầu (và **buộc phải tách rời**
   vì 122 one-hot ≠ 77 CICFlowMeter). **Giai đoạn 3 NẠP trọng số giai đoạn 2**, ghép thêm 3 đặc trưng bằng
   Model Surgery, fine-tune layer-wise LR.

2. **"Giống nhau là BIẾN KIỂM SOÁT, không phải sự lặp lại."** Giữ nguyên khung `128/8/4/512` để mọi chênh lệch
   kết quả **quy được về dữ liệu và miền**, không phải về kiến trúc.

3. **"Quyết định kiến trúc ở GĐ1 mới là thứ cứu GĐ3."** Feature Tokenizer (mỗi đặc trưng một Linear riêng)
   → **Model Surgery khả thi**. Nếu chọn MLP hay cây thì **bế tắc**.

4. **"Scaler và model phải đổi ĐỒNG THỜI."** Re-fit riêng scaler làm accuracy tụt tiếp **21,93% → 6,87%**.
   **HybridFeatureScaler chính là hiện thực của bài học này.**

5. **"Val set đa dạng miền thì metric mới thật."** V8.4 val đồng nhất → 94,95% (**inflate**);
   V8.5 val đa dạng → 91,7% (**thật**). **Con số thấp hơn nhưng trung thực hơn.**
