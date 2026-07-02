# Hướng dẫn cải thiện độ chính xác Model trong Live Detection

**Đối tượng đọc:** AI agent làm việc trên codebase (ví dụ Claude Code) + kỹ sư giám sát.
**Ngày:** 02/07/2026 (bản 2 — bổ sung chiến lược thu dữ liệu, xử lý mất cân bằng, và cách đọc chỉ số).
**Bối cảnh:** Đường ống live đã chạy đúng end-to-end (tcpdump → CICFlowMeter V4 → FT-Transformer V8.5 → dashboard). Vấn đề còn lại: trên traffic Internet thật (benign), model báo nhầm **~52% flow benign thành tấn công** với confidence cao (DoS 0.85 / Web Attack 0.88). Đây là **covariate/domain shift ở phía dữ liệu**, KHÔNG phải lỗi lập trình (đã loại trừ: parity 84/84 cột, 0 NaN/inf, model đúng trên train-distribution).

Tài liệu này chia vấn đề thành **các cơ chế cụ thể có thể sửa** và một **playbook theo thứ tự ưu tiên** để agent thực thi tuần tự.

---

## 0. Nguyên tắc bắt buộc cho agent

Đọc kỹ trước khi sửa bất cứ dòng code nào:

> ⛔ **RÀNG BUỘC TỐI THƯỢNG — CHỈ SỬA TRONG `live_detection/`.**
> **TUYỆT ĐỐI KHÔNG được thay đổi code ở bất kỳ phần nào khác của repo** (ví dụ: `Phase3_4_Retrain/`, `CIC_IDS_2017_Workspace/`, `NSL_KDD_Workspace/`, các script train gốc, các workspace...). Với những phần đó chỉ được **ĐỌC / COPY sang `live_detection/`** rồi chỉnh trên bản copy. Không sửa file gốc, không xoá, không đổi tên, không format lại. Cần dùng code train (`Phase3_4_Retrain/v8/v8.5_Combined/v8_5_train.py`) hay dữ liệu ở nơi khác → **copy vào `live_detection/`** (ví dụ `live_detection/training/`, `live_detection/data/analysis/`) rồi làm việc ở đó. Vi phạm nguyên tắc này = phá tài sản đã kiểm chứng của đồ án.

1. **KHÔNG phá nhánh REPLAY.** Mọi thay đổi phải giữ tách bạch REPLAY/LIVE như hiện tại. `LiveFlowSource` không được import corpus.
2. **Giữ parity tuyệt đối.** Mọi phép biến đổi feature (log, scale, clip, drop cột) phải áp dụng **y hệt** ở cả lúc train và lúc suy luận live. Nếu đổi tiền xử lý ở train mà quên đổi ở `FeatureExtractor` (hoặc ngược lại) → hỏng thầm lặng, nguy hiểm hơn bug rõ.
3. **Đo trước — sửa — đo lại.** Không vá mù. Mỗi bước phải có bộ chỉ số trước/sau (xem Mục 3 về đọc chỉ số). Ghi vào bảng ở Mục 6.
4. **Giữ nguyên bộ chỉ số gốc trên CIC-IDS-2017 để báo cáo.** Nếu một thay đổi làm giảm Macro-F1 test gốc quá ~1%, cân nhắc lại — trừ khi việc giảm đó đến từ bỏ feature rò rỉ (đó là kết quả tốt, cần ghi lại).
5. **Không thay model gốc bằng model mới không kiểm chứng.** Mọi checkpoint mới lưu tên có version + ngày; giữ V8.5 nguyên vẹn để rollback.
6. **Commit từng bước riêng biệt** với message rõ ràng để dễ bisect nếu FP tăng bất ngờ.
7. **Tấn công là TẠO chủ động, không "chờ bắt".** Không bao giờ phụ thuộc vào việc tình cờ bắt được tấn công trên mạng thật (xem Mục 2).

---

## 1. Chẩn đoán gốc rễ: 5 cơ chế (không phải 1 khối đen)

| # | Cơ chế | Triệu chứng khớp | Sửa được không cần data mới? |
|---|---|---|---|
| 1 | **Lệch thang đo + ngoại suy quá tự tin.** Feature dạng tốc độ (`Flow Bytes/s`, `Flow Packets/s`, `IAT`, `Flow Duration`) ở lab có dải khác traffic thật → sau scale thành z-score cực lớn → model đoán bừa với confidence cao. | conf 0.85–0.88 (overconfidence = dấu hiệu extrapolation kinh điển) | ✅ |
| 2 | **Flow siêu ngắn.** Duyệt web sinh nhiều flow 1–3 gói → `Bytes/s`, `Packets/s` chia cho ~0 → giá trị bùng nổ, trông như DoS. | `TLS thường → DoS 0.86` | ✅ |
| 3 | **Lớp Web Attack vốn yếu.** Trong CIC-IDS-2017 lớp này nhỏ, ranh giới tách kém, boundary overfit → HTTP thật rơi vào. | `HTTP thường → Web Attack 0.89` | ✅ |
| 4 | **Feature rò rỉ / spurious.** `Source/Destination Port` hoặc feature gắn thời điểm bắt (attack & benign bắt ở ngày khác nhau trong CIC-IDS-2017) → tương quan giả. | traffic port 80/443 bị hiểu sai | ✅ |
| 5 | **Phân bố benign thật khác lab** (gốc). | FP diện rộng | ❌ (cần data mới) |

**Điểm mấu chốt:** 4/5 cơ chế sửa được **không cần thu dữ liệu mới**. Chỉ (5) cần data.

---

## 2. Chiến lược thu dữ liệu & xử lý mất cân bằng 99:1 (BẮT BUỘC đọc trước khi thu)

Trên mạng thật, tỉ lệ benign:attack ≈ **99:1**. Nếu thu thụ động rồi mong có cả 2 lớp thì gần như **không bao giờ đủ tấn công** để train. Cách xử lý:

### 2.1 Tách rõ hai luồng thu — đừng trộn

| Luồng | Cách thu | Nhãn | Ghi chú |
|---|---|---|---|
| **Benign thật** | Thụ động, phiên dài, đa dạng (duyệt web, streaming, tải file, traffic nền OS) | Gán `Benign` cả mẻ | Dễ, dồi dào |
| **Tấn công thật** | **Chủ động** từ máy thứ hai bắn vào `192.168.1.121`, mỗi loại 1 phiên (nmap portscan, hping3/slowloris DoS, hydra brute-force, web attack) | **Gán theo `ATTACKER_IP` + cửa sổ thời gian** → nhãn sạch | Bạn quyết khối lượng |

Nhãn "theo IP tấn công + thời điểm" **sạch hơn** nhãn CIC-IDS-2017 gốc vì bạn biết chính xác flow nào là tấn công.

### 2.2 Ba nguyên tắc gỡ nút 99:1

1. **Tỉ lệ khi train do BẠN chọn lúc lấy mẫu, KHÔNG bị tỉ lệ lúc bắt quyết định.** Thu benign thoải mái (thụ động), sinh tấn công theo ý muốn (chủ động) → rồi cân bằng bằng sampling/weighting lúc train.
2. **Fine-tune (Bước 5) KHÔNG cần thu lại tấn công.** Giữ nguyên lớp tấn công từ **CIC-IDS-2017**, chỉ **thêm benign thật** vào. Đây là domain adaptation, không phải dựng dataset mới.
3. **99:1 là LÝ DO NÊN làm cổng one-class (Bước 6),** không phải lý do chống lại: one-class chỉ cần lớp benign (đang thừa) → mất cân bằng thành vô nghĩa.

### 2.3 Kỹ thuật xử lý mất cân bằng (đã có sẵn trong repo)

Nếu gộp thành tập có cả 2 lớp để retrain: dùng **class weights / focal loss / SMOTE**. Repo đã có sẵn để tham khảo:
- `Phase3_4_Retrain/archive_v5_focal/` (focal loss)
- `Phase3_4_Retrain/archive_v6_smote/` (SMOTE)
- `Phase3_4_Retrain/archive_v7_run7/` (run7 + SMOTE portscan)

⚠️ Đừng để benign thật áp đảo khiến model quên lớp tấn công (catastrophic forgetting) — luôn đánh giá lại trên CIC-IDS-2017 test sau khi retrain/fine-tune.

---

## 3. Cách đọc chỉ số (QUAN TRỌNG — đừng tin một con số đơn lẻ)

Dưới mất cân bằng, **Macro-F1 và Accuracy cân trọng số khác nhau**, và chính **độ lệch giữa chúng là tín hiệu chẩn đoán**:

- **Macro-F1** = trung bình F1 từng lớp, **trọng số bằng nhau** → bỏ qua lớp nào đông.
- **Accuracy** = đếm đúng / tổng → **bị lớp đông (benign) chi phối**.

| Quan hệ quan sát | Ý nghĩa |
|---|---|
| accuracy ≫ macro-F1 | Làm tốt lớp đông, **bỏ lớp hiếm** → cảnh báo imbalance kinh điển (accuracy cao giả tạo) |
| **accuracy ≪ macro-F1** | Làm **tệ trên lớp đông (benign)** nhưng vài lớp nhỏ vẫn ổn nên macro-F1 (trọng số bằng) **che mất** lỗi benign; accuracy mới phơi bày. **Đây đúng là kiểu FP-live hiện tại.** |

**Hệ quả:** phải theo dõi ĐỒNG THỜI, và dùng GAP làm cảnh báo:
- **Accuracy** *và* **Macro-F1** (canh khoảng lệch).
- **Precision/Recall từng lớp** (định vị lớp hỏng).
- Cho đúng bài toán FP: **Benign Recall** và **FPR** (False Positive Rate) là 2 chỉ số **vận hành** quan trọng nhất, vì lỗi nằm ở benign.
- Khi chọn ngưỡng: báo cáo **FPR tại một mức TPR cố định** và/hoặc **PR-AUC** cho lớp tấn công.

> Không có chỉ số "đúng duy nhất". Cả hai kiểu hỏng đều có thể xảy ra dưới 99:1 (đoán tất cả benign → accuracy cao lừa mình; over-flag → accuracy thấp lộ vấn đề nhưng macro-F1 lừa mình). Chỉ khi nhìn cả cụm mới phân biệt được.

---

## 4. Playbook theo thứ tự ưu tiên (đã xác định lại đầy đủ)

Mỗi bước ghi rõ: **Tiền đề** (cần retrain? cần data gì?) → **Mục tiêu → Việc làm → Parity checklist → Kiểm chứng → Tiêu chí Done**.

> **Bản đồ tiền đề nhanh:**
> - Không cần retrain, không cần data train: **Bước 1 (chẩn đoán), Bước 2 (calibrate), Bước 6 (one-class)**.
> - **Cần retrain + cần tập train CIC-IDS-2017 đầy đủ:** **Bước 4 (tiền xử lý), Bước 5 (fine-tune)**.
> - Code train tham khảo: `Phase3_4_Retrain/v8/v8.5_Combined/v8_5_train.py` — **COPY sang `live_detection/training/` rồi sửa trên bản copy** (xem ràng buộc tối thượng ở Mục 0), KHÔNG sửa file gốc.
> - ⚠️ **Chưa xác nhận tập train CIC-IDS-2017 đầy đủ nằm trong repo** → phải định vị/khôi phục trước Bước 4/5.
> - ⚠️ Scaler hiện tại (`models/v8_5_scaler.pkl`) là **`dict` hybrid** (`model_defs/hybrid_feature_scaler.py`), KHÔNG phải sklearn scaler → mọi thay đổi scaling (Bước 4.2) phải đi qua file này, không phải `sklearn.RobustScaler` cắm thẳng.

---

### BƯỚC 0 — Thu dữ liệu thật (2 luồng)  ·  *không cần retrain*

> Mục tiêu: có `benign_real` (dồi dào) và `<attack>_real` (chủ động, nhãn sạch) làm nền cho mọi bước sau.

**Việc làm:**
1. **Benign:** chạy pipeline live trong phiên dài, tạo hoạt động đa dạng (duyệt web, streaming, tải file, để máy chạy nền) → gom CSV từ `data/live/processed/` → `data/analysis/benign_real.csv`. Mục tiêu ≥ vài nghìn flow (56 flow chỉ đủ định hướng, KHÔNG đủ để calibrate/kết luận).
2. **Tấn công:** từ **máy thứ hai** bắn từng loại vào `192.168.1.121`; ghi lại `ATTACKER_IP` + mốc thời gian; lọc flow theo đó → `data/analysis/<attack>_real.csv`, gán nhãn tương ứng.

**Kiểm chứng:** đếm số flow mỗi lớp; kiểm 84/84 cột, 0 NaN/inf trên các file thu.

**Tiêu chí Done:** có ≥ vài nghìn benign thật + ít nhất 1–2 loại tấn công thật có nhãn sạch. Tách sẵn một phần benign làm **validation giữ riêng** (cho Bước 2).

---

### BƯỚC 1 — Chẩn đoán  ·  *không cần retrain*

> Mục tiêu: biến "domain shift" mơ hồ thành danh sách 3–5 feature thủ phạm cụ thể. Đây cũng là material cho chương phân tích của đồ án.

**Việc làm:**
1. Load benign CIC-IDS-2017 (từ train) → `benign_lab.csv`; dùng `benign_real.csv` từ Bước 0.
2. So sánh phân bố **từng feature**: KS-test (`scipy.stats.ks_2samp`) → xếp hạng theo KS-statistic giảm dần; vẽ histogram overlay ~10 feature nghi ngờ nhất (`Flow Bytes/s`, `Flow Packets/s`, `Flow IAT Mean`, `Flow Duration`, `Fwd/Bwd Packet Length Mean/Std`, các `*Flag Count`).
3. Chạy **SHAP** (hoặc feature importance) trên **chính các flow FP** (benign thật bị gọi là DoS/Web Attack): xem feature nào đẩy quyết định sang lớp tấn công.

**Kiểm chứng:** bảng xếp hạng KS-statistic + bảng SHAP top-feature cho FP.

**Tiêu chí Done:** xác định 3–5 feature lệch mạnh nhất VÀ 3–5 feature đóng góp nhiều nhất cho FP. Các bước sau tập trung đúng vào các feature này.

---

### BƯỚC 2 — Hiệu chỉnh quyết định (calibrate)  ·  *KHÔNG cần retrain — quick win ROI cao nhất*

> Mục tiêu: chữa overconfidence để ngưỡng lọc thật sự có tác dụng. Làm được ngay trong `live_detection/` với model V8.5 hiện có + validation benign giữ riêng (Bước 0).

**2.1 Temperature scaling (post-hoc)**
- Học 1 tham số nhiệt độ `T` trên validation benign, chia logits cho `T` trước softmax → confidence phản ánh đúng độ chắc.
- Lưu `T` cạnh model; áp trong `Classifier.predict` (cùng chỗ cho cả replay + live để parity).

**2.2 Ngưỡng theo từng lớp**
- Thay `conf_threshold=0.6` chung bằng ngưỡng riêng mỗi lớp trong `ConfidenceThresholdRule`.
- Nâng ngưỡng cho **DoS** và **Web Attack** (2 lớp đang FP); giữ bình thường cho lớp khác.

**Kiểm chứng:** reliability diagram (confidence vs accuracy) trước/sau; **Benign Recall / FPR** trên benign thật; TPR trên tấn công thật (Bước 3).

**Tiêu chí Done:** confidence được calibrate (reliability diagram gần đường chéo); **FPR giảm rõ** mà **TPR tấn công không tụt** (kiểm chéo Bước 3).

---

### BƯỚC 3 — Kiểm chứng phát hiện tấn công  ·  *song song, xuyên suốt — ĐỪNG BỎ*

> FP thấp vô nghĩa nếu bỏ sót tấn công. Chạy sau MỖI thay đổi giảm-FP.

**Việc làm:**
- Từ **máy thứ hai trong LAN**, chạy portscan/DoS vào `192.168.1.121`.
- Đặt `attacker_ip` trong `replay_config.json` = IP máy tấn công để `PortScanRule` kích hoạt.
- Ghi **cả TP-rate lẫn FP-rate** — hai con số phải đi cùng nhau trong bảng Mục 6.

**Lưu ý mạng (WSL mirrored):** self-scan (quét chính `192.168.1.121` từ cùng máy) đi qua **loopback, không qua eth0** → không bắt được; **phải bắn từ máy khác**. Traffic giữa 2 máy khác trong LAN cần SPAN/port-mirroring.

---

### BƯỚC 4 — Tiền xử lý + retrain  ·  *CẦN retrain + CẦN tập train CIC-IDS-2017 đầy đủ*

> Mục tiêu: kéo FP xuống mạnh bằng tiền xử lý chống lệch-thang-đo. Làm 4 việc, đo FP sau mỗi việc để biết việc nào hiệu quả nhất.
> **Tiền đề:** định vị/khôi phục tập train trước; **COPY** code train (`Phase3_4_Retrain/v8/v8.5_Combined/v8_5_train.py`) + dữ liệu cần thiết **sang `live_detection/`** rồi làm trên bản copy (Mục 0); lưu checkpoint mới có version+ngày, giữ V8.5 để rollback.

**4.1 Log-transform feature đuôi nặng** — `log1p` cho byte-count/duration/rate/IAT (theo danh sách từ Bước 1).
**4.2 Robust scaling + clipping** — dùng median/IQR thay standard scale; clip z-score `[-5, 5]`. ⚠️ Sửa qua `model_defs/hybrid_feature_scaler.py` (scaler là dict hybrid), KHÔNG cắm thẳng `sklearn.RobustScaler`.
**4.3 Lọc/đánh dấu flow siêu ngắn** — flow `< 2–3 gói` (hoặc duration dưới ngưỡng): route sang "benign/undetermined" thay vì đưa vào classifier (chặn DoS-giả, cơ chế 2).
**4.4 Bỏ feature rò rỉ** — retrain **không có** `Source/Destination Port` + feature gắn thời điểm bắt. Kỳ vọng: F1 CIC-IDS-2017 gần như không đổi nhưng FP live giảm → **bằng chứng spurious correlation** cho báo cáo.

**Parity checklist (chạy sau MỖI thay đổi 4.x):**
- `FeatureExtractor` live áp **đúng** phép biến đổi như train.
- Refit scaler → **lưu bản mới** → **server nạp bản mới** (đừng để live dùng scaler cũ).
- Kiểm "84/84 (hoặc N/N sau khi drop) cột, 0 NaN, 0 inf, cùng thứ tự cột" ở cả train và live.

**Kiểm chứng:** chạy lại benign thật + tấn công thật sau mỗi thay đổi; ghi FPR/Benign-Recall/TPR + Macro-F1 CIC-IDS-2017.

**Tiêu chí Done:** FP benign thật giảm rõ rệt (định hướng < 20%, càng thấp càng tốt) mà Macro-F1 CIC-IDS-2017 vẫn ≥ ~0.96 và TPR tấn công không tụt.

---

### BƯỚC 5 — Fine-tune bằng benign thật  ·  *CẦN retrain; KHÔNG cần thu lại tấn công*

> Mục tiêu: chữa trực tiếp cơ chế (5). Giữ lớp tấn công từ CIC-IDS-2017, thêm benign thật.

**Việc làm:**
- Trộn `benign_real` (Bước 0) vào tập train (hoặc fine-tune từ V8.5), **giữ nguyên attack CIC-IDS-2017**.
- Xử lý mất cân bằng theo Mục 2.3 (class weight / focal / SMOTE — đã có trong repo).
- Cân bằng lớp để không quên tấn công.

**Tiêu chí Done:** FP benign thật hội tụ về mức chấp nhận được; **F1 lớp tấn công không suy giảm** (đánh giá lại CIC-IDS-2017 test).

---

### BƯỚC 6 — Kiến trúc "cổng bất thường" (one-class)  ·  *không cần retrain FT-Transformer; tùy chọn — điểm cộng phương pháp*

> Mục tiêu: đóng góp phương pháp; đánh trực tiếp open-set/covariate shift; hợp bản chất 99:1 (chỉ cần benign).

**Việc làm:**
- Train **one-class** (Isolation Forest / autoencoder) **chỉ trên benign thật** làm cổng lọc.
- Quyết định kết hợp: chỉ báo tấn công khi **cả hai** đồng ý — (1) classifier V8.5 nói "attack" VÀ (2) cổng one-class nói "bất thường so với benign địa phương".
- Benign thật (dù classifier nhầm) bị cổng chặn vì *giống benign địa phương* → FP giảm.

**Tiêu chí Done:** FP giảm rõ nhờ cổng; trình bày được cơ chế trong chương kết luận.

---

## 5. Cạm bẫy thường gặp (agent chú ý)

- **Parity trôi thầm lặng:** đổi tiền xử lý một bên mà quên bên kia. Sau mỗi thay đổi feature, chạy lại parity checklist (Bước 4).
- **Refit scaler nhưng quên save/nạp bản mới ở server** → live dùng scaler cũ. Nhớ scaler là **dict hybrid**.
- **Clip/log làm mất tín hiệu tấn công thật:** kiểm ở Bước 3 rằng tấn công vẫn bị bắt sau khi nén feature.
- **Fine-tune gây catastrophic forgetting:** giữ tỉ lệ lớp hợp lý, đánh giá lại trên CIC-IDS-2017 test.
- **Đo FP/tin chỉ số trên quá ít flow:** 56 flow chỉ đủ định hướng. Thu đủ benign thật (Bước 0) để con số đáng tin.
- **Tin một chỉ số đơn lẻ:** luôn đọc cụm accuracy + macro-F1 + per-class recall + FPR (Mục 3).

---

## 6. Bảng theo dõi kết quả (agent cập nhật sau mỗi bước)

| Bước | Thay đổi | FPR / Benign-Recall (benign thật) | Accuracy | Macro-F1 CIC-IDS-2017 | TP-rate tấn công thật | Ghi chú |
|---|---|---|---|---|---|---|
| Gốc | (chưa sửa) | ~52% FP | thấp | 0.978 | chưa đo | overconfidence 0.85–0.88 |
| 0 | Thu dữ liệu | — | — | — | — | #benign=..., #attack=... |
| 1 | Chẩn đoán | — | — | — | — | top feature lệch: ... |
| 2 | calibrate + ngưỡng/lớp | | | | | không retrain |
| 3 | (kiểm chứng tấn công) | | | | | chạy sau mỗi bước |
| 4.1 | log-transform | | | | | retrain |
| 4.2 | robust scale + clip | | | | | qua hybrid_feature_scaler |
| 4.3 | lọc flow ngắn | | | | | |
| 4.4 | bỏ feature rò rỉ | | | | | bằng chứng spurious? |
| 5 | fine-tune benign thật | | | | | giữ attack CIC |
| 6 | cổng one-class | | | | | tùy chọn |

---

## 7. Định hướng viết báo cáo (từ hạn chế → đóng góp)

Đừng chỉ nói "domain shift, hạn chế". Trình bày thành **chuỗi có kiểm chứng**:
1. **Parity công cụ đã đạt** (khâu trích đặc trưng, 84/84 cột) **≠ khớp phân bố** (khâu dữ liệu).
2. **Chứng minh bằng Bước 1** feature nào lệch (KS-test + SHAP trên FP).
3. **Đo lại theo cụm chỉ số sau mỗi can thiệp** (bảng Mục 6) — nhấn mạnh GAP accuracy↔macro-F1 và FPR/Benign-Recall (Mục 3).
4. Nếu Bước 4.4 giữ được F1 mà giảm FP → nêu như phát hiện về **spurious correlation** trong CIC-IDS-2017.

Một bảng "FPR trước/sau từng can thiệp" biến hạn chế thành **đóng góp phân tích thực sự**. Giữ Macro-F1 0.978 (trên CIC-IDS-2017) trong phần kết quả, kèm mục riêng "Hạn chế covariate shift trên môi trường live thật" trong chương kết luận.

---

## 8. Thứ tự thực thi khuyến nghị (tóm tắt cho agent)

```
1. BƯỚC 0  Thu dữ liệu thật (2 luồng: benign thụ động + tấn công chủ động)   ← làm trước
2. BƯỚC 1  Chẩn đoán (KS-test + SHAP trên FP)
3. BƯỚC 2  Calibrate (temperature + ngưỡng/lớp)        ← quick win, KHÔNG retrain
4. BƯỚC 3  Kiểm chứng tấn công thật từ máy khác        ← xen kẽ, đừng bỏ
5. BƯỚC 4  Tiền xử lý + retrain (log→robust→lọc→bỏ leak)   ← cần tập train
6. BƯỚC 5  Fine-tune benign thật                       ← cần tập train
7. BƯỚC 6  Cổng one-class                              ← tùy chọn, điểm cộng
```

Ưu tiên đòn bẩy **không cần retrain trước**: **Bước 0 → 1 → 2** trả về nhiều nhất với công ít nhất và không cần tập train. Bước 4–5 (retrain) cho kết quả bền vững hơn nhưng cần định vị tập train CIC-IDS-2017 + tốn công; Bước 6 là điểm cộng phương pháp cho đồ án.
