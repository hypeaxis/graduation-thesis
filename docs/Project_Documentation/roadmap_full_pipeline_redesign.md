# Roadmap Toàn Diện: Tái Thiết Pipeline IDS
## (Attack Simulation → Labeling → Scaler/Preprocessing → Training → Evaluation)

> Tài liệu tổng hợp toàn bộ phát hiện từ các thử nghiệm trước, sắp xếp lại thành lộ trình end-to-end có thứ tự ưu tiên rõ ràng. Mỗi giai đoạn có: Mục tiêu, Input cần, Các bước, Output, DoD (Definition of Done). Agent/người thực hiện PHẢI tuân thủ đúng thứ tự — một số giai đoạn block (chặn) giai đoạn sau, một số có thể chạy song song (ghi rõ trong sơ đồ phụ thuộc).

---

## 0. Tóm tắt các phát hiện đã xác nhận (căn cứ để xây roadmap này)

| # | Phát hiện | Nguồn |
|---|---|---|
| 1 | Re-fit scaler unsupervised trực tiếp trên target domain mất cân bằng cực đoan → recenter sai, kéo Recall sập | Thử nghiệm 1 |
| 2 | Slowloris vốn "low-and-slow", đã gần cụm Benign sẵn trên feature thô → cộng hưởng với lỗi #1 | Thử nghiệm 1 |
| 3 | Model Surgery (freeze 77 feature gốc, train 3 feature mới) là hướng đúng, nhưng scaler 3 feature mới PHẢI fit trên Mixed Train Data, không fit trên tập đang evaluate | Stage 3 |
| 4 | Hybrid Pipeline hiện tại (2 PowerTransformer tách biệt cho 77 + 3 feature) là thiết kế đúng về mặt train-time, NHƯNG báo cáo run2 mô tả "MinMaxScaler" → cần xác minh inference pipeline có khớp train pipeline không | Báo cáo run2 |
| 5 | Ground truth dựa vào Snort (IDS khác) là rủi ro phương pháp luận — lỗi của Snort in thẳng vào nhãn "chuẩn" | Báo cáo run2 |
| 6 | Gán nhãn theo time-window ±120s + rule "ưu tiên DoS khi chồng lấn" làm PortScan bị nuốt vào DoS, Benign bị gán nhầm DoS | Báo cáo run2 |
| 7 | Cascade Stage 2 chưa từng kích hoạt (0 mẫu đạt ngưỡng Suspicious 0.85) — nghi ngờ model overconfident dưới domain shift | Báo cáo run2 |
| 8 | Brute Force (n=30) và các lớp support thấp cho số liệu nhiễu, không đáng tin cậy thống kê | Báo cáo run2 |
| 9 | DoS Hulk và Web Brute Force có thể trùng lặp đặc trưng flow-level (cùng dạng HTTP flood) | Báo cáo run2 |
| 10 | Benign chỉ chiếm ~6% dữ liệu thu thập — không đủ để đo False Positive Rate đáng tin cậy | Báo cáo run2 |

---

## 1. Nguyên tắc bắt buộc xuyên suốt toàn bộ roadmap

1. **Không bao giờ fit/re-fit bất kỳ scaler nào trên tập dữ liệu đang dùng để evaluate.** Scaler chỉ fit trên Train/Mixed-Train set, lưu lại, dùng cố định cho mọi lần inference sau đó.
2. **77 feature gốc: embedding + PowerTransformer giữ đông cứng (frozen) vĩnh viễn**, không re-fit, không train lại — đây là tài sản tri thức từ CIC-IDS-2017 cần bảo toàn.
3. **3 feature mới (và mọi feature thêm sau này): luôn fit scaler riêng trên Mixed Train Data**, version hóa cùng checkpoint.
4. **Ground truth ưu tiên từ attack orchestrator (timestamp tự ghi), Snort chỉ dùng làm tín hiệu đối chiếu phụ**, không phải nguồn nhãn chính.
5. **Mọi checkpoint phải đi kèm 1 bundle duy nhất, không tách rời:** `model.pt` + `scaler_77.joblib` + `scaler_3custom.joblib` + `feature_schema.json` + `training_config.json`, đặt cùng thư mục, đặt tên theo version (vd: `v3_hybrid_run2fix/`).
6. **Mọi đánh giá bắt buộc báo cáo:** Confusion Matrix tuyệt đối, Macro F1 (không chỉ Weighted F1), MCC, Balanced Accuracy, kèm cảnh báo rõ với lớp có support < 100 mẫu.

---

## Sơ đồ phụ thuộc giữa các giai đoạn

```
Giai đoạn 0 (Xác minh inference pipeline)  ──BLOCKING──▶  mọi giai đoạn khác
                                                              │
        ┌─────────────────────────────────────────────────────┤
        ▼                                                     ▼
Giai đoạn 1 (Redesign Attack Simulation)         Giai đoạn 2 (Redesign Labeling)
   [có thể làm song song với GĐ2]                  [phụ thuộc log từ GĐ1 nếu thu data mới]
        │                                                     │
        └─────────────────────┬───────────────────────────────┘
                               ▼
                  Giai đoạn 3 (Chuẩn hóa Scaler/Preprocessing Pipeline)
                               │
                               ▼
                  Giai đoạn 4 (Re-fit & Re-train theo dữ liệu mới)
                               │
                               ▼
                  Giai đoạn 5 (Chuẩn hóa lại Evaluation Methodology)
                               │
                               ▼
                  Giai đoạn 6 (Tổng hợp so sánh toàn bộ version)
```

---

## GIAI ĐOẠN 0 — Xác minh Inference Pipeline hiện tại (BLOCKING, làm trước tiên)

### Mục tiêu
Xác nhận dứt điểm: script đã tạo ra bảng kết quả run2 có thực sự dùng đúng Hybrid Pipeline (2 PowerTransformer đã `joblib.dump` từ lúc train), hay vô tình dùng MinMaxScaler như mô tả trong báo cáo.

### Input cần (Agent phải hỏi nếu thiếu)
- [ ] Toàn bộ đoạn code từ lúc đọc `attack_run2.pcap_Flow.csv` cho đến lúc gọi `model.forward()`/`model.predict()`.
- [ ] Đường dẫn 2 file scaler đã lưu (`scaler_77.joblib`, `scaler_3custom.joblib` hoặc tên tương đương) và xác nhận chúng có tồn tại, có được load đúng hay không.

### Các bước
1. Review code, đánh dấu chính xác bước transform nào được áp dụng cho 80 feature trước khi vào model.
2. Viết script `0_verify_inference_pipeline.py`: lấy 5-10 sample bất kỳ từ run2, chạy qua đúng pipeline train-time (load 2 scaler đã lưu) và so sánh trực tiếp với output của script inference hiện tại (đầu ra trước khi vào model, không phải kết quả cuối). Hai luồng phải cho **giá trị giống hệt nhau** (sai số < 1e-6).
3. Nếu MinMaxScaler thực sự được dùng ở một bước nào đó (vd: chuẩn hóa sơ bộ trước khi sinh `Custom_*` feature) — xác định rõ nó có ảnh hưởng đến input cuối cùng vào model hay chỉ là bước trung gian độc lập.

### Output kỳ vọng
- `0_verify_inference_pipeline.py` + log kết quả PASS/FAIL.
- Nếu FAIL: bản vá pipeline inference + chạy lại toàn bộ đánh giá run2 với pipeline đã sửa, cập nhật lại bảng kết quả trong báo cáo trước khi dùng cho bất kỳ kết luận nào.

### DoD
- Có bằng chứng (log so khớp số học) rằng pipeline inference khớp 100% với pipeline train. Không giai đoạn nào bên dưới được bắt đầu trước khi mục này PASS.

---

## GIAI ĐOẠN 1 — Redesign Attack Simulation (`auto_attack.py`)

### Mục tiêu
Tạo dữ liệu tấn công đa dạng, có ground truth chính xác tự thân, đạt chuẩn để dùng cho pentest và huấn luyện mô hình tổng quát hóa tốt.

### Các bước
1. **Ground truth tự ghi log:** mỗi phiên tấn công ghi ra 1 dòng CSV `attack_type, src_ip, dst_ip, dst_port, start_time_ms, end_time_ms, params` — độ chính xác mili-giây, lấy timestamp ngay tại điểm script gửi request đầu tiên/cuối cùng.
2. **Đa dạng hóa tham số mỗi kỹ thuật**, không chạy 1 config cố định:
   - PortScan: biến thiên tốc độ scan (`-T2` đến `-T5`), dải cổng, kiểu scan (`-sT`, `-sS`, `-sV`).
   - Brute Force (SSH/FTP/Web): biến thiên số thread hydra (slow vs fast brute force), độ dài wordlist.
   - Slowloris: biến thiên số connection (`-s`), tốc độ giữ kết nối.
   - Hulk: biến thiên request rate, số worker.
   - SQLi (sqlmap): biến thiên kỹ thuật (`--technique=B,U,S,T`), tốc độ request.
3. **Tăng mạnh tỷ trọng Benign:** viết `background_traffic_generator.py` chạy độc lập, song song, không trùng lịch với attack script — mô phỏng duyệt web, SSH hợp lệ, file transfer, traffic idle. Mục tiêu tối thiểu: Benign chiếm ≥ 25-30% tổng dữ liệu thu được.
4. **Multiple attacker-victim pairs**, lịch chạy ngẫu nhiên hóa (random scheduling) thay vì 1 kịch bản tuyến tính cố định.
5. **Tách thời gian giữa các loại attack khác nhau** (không cho 2 kỹ thuật chạy chồng lấn ngẫu nhiên, trừ khi đó là mục đích thử nghiệm riêng về "multi-stage attack overlap" — nếu làm, phải gán nhãn multi-label rõ ràng, không ép về 1 nhãn).

### Output kỳ vọng
- `auto_attack_v2.py`, `background_traffic_generator.py`
- `ground_truth_log_runN.csv` cho mỗi lần thu thập

### DoD
- Tỷ lệ Benign/Malicious trong dữ liệu mới đạt tối thiểu 25/75 (so với ~6/94 hiện tại).
- Mỗi loại tấn công có ít nhất 3 biến thể tham số khác nhau trong tập thu thập.
- Ground truth log không phụ thuộc Snort.

---

## GIAI ĐOẠN 2 — Redesign Labeling Pipeline (`dataset_builder.py`)

### Mục tiêu
Loại bỏ nhiễu nhãn do phụ thuộc Snort và rule "ưu tiên DoS khi chồng lấn".

### Các bước
1. Dùng `ground_truth_log_runN.csv` (từ Giai đoạn 1) làm nguồn nhãn chính — match theo `(src_ip, dst_ip, dst_port, flow_start_time)` nằm trong khoảng `[start_time_ms, end_time_ms]` của đúng 1 phiên tấn công.
2. **Bỏ rule ưu tiên DoS.** Thay bằng: nếu 1 flow overlap với ĐÚNG 1 loại tấn công → gán nhãn đó. Nếu overlap với NHIỀU loại (do lỗi lịch chạy) → đánh dấu `ambiguous`, loại khỏi tập train/eval chính (có thể giữ riêng để phân tích multi-label sau).
3. Benign chỉ gán cho flow **không overlap với bất kỳ attack session nào** (kiểm tra chéo với toàn bộ `ground_truth_log`, không chỉ 1 attack đang chạy gần nhất).
4. Dùng Snort alert làm **cột đối chiếu phụ** (`snort_agree: True/False`) để phân tích sau này — KHÔNG dùng để quyết định nhãn.
5. Sinh báo cáo chất lượng nhãn: tổng số flow, % ambiguous bị loại, % Snort đồng thuận với ground truth mới (chỉ mang tính tham khảo, không phải tiêu chí pass/fail).

### Output kỳ vọng
- `dataset_builder_v2.py`
- `label_quality_report_runN.md`

### DoD
- 0% nhãn phụ thuộc trực tiếp vào Snort.
- Tỷ lệ flow `ambiguous` bị loại được báo cáo minh bạch (không âm thầm gán bừa về 1 nhãn).

---

## GIAI ĐOẠN 3 — Chuẩn hóa & Đóng gói Preprocessing Pipeline

### Mục tiêu
Ngăn lỗi "scaler lệch pha với checkpoint" tái diễn lần thứ 4.

### Các bước
1. Đóng gói thành 1 class `HybridFeatureScaler` chứa: `scaler_77` (PowerTransformer frozen), `scaler_3custom` (PowerTransformer trainable-phase), danh sách tên feature theo đúng thứ tự, version string.
2. `HybridFeatureScaler.save(path)` / `.load(path)` ghi/đọc toàn bộ trong 1 file duy nhất (pickle hoặc joblib), tránh tình trạng quên lưu 1 trong 2 scaler.
3. Mỗi checkpoint model khi lưu PHẢI lưu kèm `HybridFeatureScaler` tương ứng trong cùng thư mục version (theo nguyên tắc #5 ở mục 1).
4. Viết sanity-check tự động `check_distribution_drift(batch_new, stats_at_fit_time)`: so sánh mean/std (hoặc KL divergence) của batch input mới với thống kê lưu lúc fit; cảnh báo nếu lệch vượt ngưỡng (vd: |z-score trung bình| > 3) thay vì âm thầm chạy tiếp.
5. Audit lại công thức `Custom_Fwd_Pkt_Rate`, `Custom_Slow_Index`, và feature thứ 3 — xác nhận không chứa thành phần thời gian tuyệt đối nhạy hạ tầng (đồng hồ WSL/NAT khác Router vật lý). Nếu có, đổi sang dạng tỷ lệ/nội tại flow.

### Output kỳ vọng
- `hybrid_feature_scaler.py` (class definition)
- `check_distribution_drift.py`

### DoD
- Không còn scaler nào được load/fit rời rạc bên ngoài class `HybridFeatureScaler`.
- Sanity-check chạy tự động mỗi lần inference, có log cảnh báo khi phát hiện drift.

---

## GIAI ĐOẠN 4 — Re-fit & Re-train trên dữ liệu đã làm sạch

### Mục tiêu
Train lại đúng theo Model Surgery, trên dữ liệu đã qua Giai đoạn 1-3.

### Các bước
1. Build lại Mixed Train Data = CIC-IDS-2017 (downsample, giữ tỷ lệ gốc) + dữ liệu mới từ Giai đoạn 1-2 (đã relabel, đã cân bằng Benign tốt hơn).
2. Re-fit **CHỈ** `scaler_3custom` trên Mixed Train Data này (giữ nguyên `scaler_77` đông cứng từ checkpoint trước — không refit).
3. Fine-tune model: freeze 77-feature embedding (như thiết kế Model Surgery hiện tại), train 3-feature embedding mới + classification head, dùng class weighting theo support thực tế của Mixed Train Data mới.
4. **Calibration check cho ngưỡng Suspicious (Cascade Stage 2):** vẽ histogram phân phối confidence score của Stage 1 trên validation set. Nếu phân phối quá cực đoan (gần như toàn bộ confidence > 0.95 hoặc < 0.05, không có vùng giữa), xác nhận giả thuyết overconfidence dưới domain shift. Cân nhắc:
   - Hạ ngưỡng Suspicious xuống mức thực tế quan sát được (không cố định 0.85 nếu dữ liệu không hỗ trợ).
   - Thêm **label smoothing** (vd: 0.05-0.1) vào CrossEntropyLoss để giảm overconfidence.
   - Cân nhắc Temperature Scaling sau train để hiệu chỉnh lại confidence (không đổi ranking, chỉ đổi độ "chắc chắn").
5. Lưu checkpoint mới theo đúng bundle versioning (mục 1, nguyên tắc #5).

### Output kỳ vọng
- `4_refit_retrain_v2.py`
- Checkpoint `v3_hybrid_run2fix/` đầy đủ bundle.
- Biểu đồ confidence distribution trước/sau calibration.

### DoD
- Stage 2 Cascade thực sự được kích hoạt cho > 0% mẫu trong validation set (không còn hiện tượng "0 mẫu Suspicious").
- Recall(Malicious) và Recall(Benign) trên validation Testbed đều cải thiện so với baseline run2 đã verify ở Giai đoạn 0.

---

## GIAI ĐOẠN 5 — Chuẩn hóa lại Evaluation Methodology

### Mục tiêu
Đảm bảo mọi con số báo cáo từ nay phản ánh đúng thực tế, không bị che bởi lớp đa số hay nhiễu thống kê.

### Các bước
1. Script đánh giá chuẩn xuất ra: Confusion Matrix tuyệt đối, Macro F1, Weighted F1, MCC, Balanced Accuracy, kèm cờ cảnh báo tự động với lớp có support < 100.
2. Phân tích riêng cặp nhầm lẫn **DoS Hulk ↔ Web Brute Force**: trích các sample bị nhầm, kiểm tra xem có thực sự trùng đặc trưng flow-level hay không. Nếu có, ghi nhận đây là giới hạn của flow-statistics-only approach (cần feature tầng ứng dụng để giải quyết triệt để — ghi vào phần "Hạn chế" của báo cáo thay vì kỳ vọng sửa bằng tuning).
3. Visualize embedding (t-SNE/UMAP) của Stage 1 trên cả CIC-2017 test set và Testbed/run2 mới — so sánh trước/sau Giai đoạn 4 để minh họa trực quan mức độ domain alignment đã cải thiện (giá trị cao cho phần báo cáo học thuật).

### Output kỳ vọng
- `5_standard_evaluation.py`
- Biểu đồ t-SNE/UMAP so sánh trước/sau.

### DoD
- Mọi báo cáo từ Giai đoạn 5 trở đi đều có đủ Macro F1 + Confusion Matrix tuyệt đối, không chỉ Accuracy/Weighted F1.

---

## GIAI ĐOẠN 6 — Tổng hợp So Sánh Toàn Bộ Version

### Mục tiêu
Có 1 bảng duy nhất tổng hợp tiến trình toàn dự án, dùng trực tiếp cho báo cáo học thuật cuối cùng.

### Các bước
- Viết `6_aggregate_all_versions.py` đọc toàn bộ kết quả đã lưu (Stage 1 gốc, Thử nghiệm 1, Stage 3, run2 trước/sau verify, v3_hybrid_run2fix) → xuất 1 bảng Markdown/CSV:

`Version | Scaler Strategy | Ground Truth Source | Accuracy | Macro F1 | MCC | Recall(Benign) | Recall(Malicious) | Cascade Stage2 Trigger Rate`

### DoD
- Bảng tổng hợp đủ tất cả version, sẵn sàng dán trực tiếp vào báo cáo cuối.
