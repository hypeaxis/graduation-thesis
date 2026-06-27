# Kế hoạch cải thiện F1 — xử lý Benign recall thấp (False Positive)

Tài liệu ghi lại chẩn đoán và kế hoạch chỉnh sửa để nâng **macro-F1** của hệ thống IDS
replay-based (model FT-Transformer V8.5). Vấn đề cốt lõi: **Benign recall thấp** kéo
precision các lớp tấn công xuống, do đó hạ macro-F1.

---

## 1. Vấn đề

Đo trên file `benign_only.pcap_Flow.csv` (29.486 flow benign):

| Dự đoán | Số flow | Ghi chú |
|---|---|---|
| **Benign (đúng)** | 19.569 | **Benign recall ≈ 66.4%** |
| Web Attack (sai) | 5.935 | FP |
| DoS (sai) | 3.038 | FP |
| Brute Force (sai) | 942 | FP |
| PortScan (sai) | 2 | FP |

→ **~33.6% benign bị gán nhầm thành tấn công.** Trong khi đó recall tấn công rất cao:
Web Attack 99.3%, DoS 98.8%, Brute Force 97.8%.

**Hệ quả F1:** benign là nguồn false positive lớn → **precision** của Web Attack/DoS giảm →
**macro-F1 giảm**. Vậy đòn bẩy F1 không phải tăng flow tấn công, mà là **giảm FP benign**.

---

## 2. Chẩn đoán — 3 nguyên nhân (theo mức độ quan trọng)

**(1) Bộ sinh benign (`auto_benign_v2.py`) tạo traffic trông giống tấn công — lớn nhất.**
- FP dồn vào **Web Attack + DoS** — đúng chữ ký "nhiều HTTP request ngắn, packets/s cao";
  `auto_benign` bắn HTTP/SSH/FTP liên tục bằng script → giống HTTP-flood / web-attack.
- Đối chiếu quyết định: benign là **phản hồi victim** (Src=`192.168.0.101`) trong các file
  tấn công lại phân đúng Benign tới **95–98%**. Chỉ benign **do attacker host `.106` sinh ra**
  (active, tốc độ cao) mới bị nhầm → **vấn đề ở cách sinh benign, không phải model hỏng.**

**(2) Domain shift.** V8.5 học "benign" chủ yếu từ CIC-IDS-2017 + benign testbed cũ; benign
mới (WSL/NAT, IAT & window size khác) lệch phân phối → bị đẩy sang lớp tấn công gần nhất.

**(3) Model train thiên về recall tấn công.** Dùng focal loss + class weight (sqrt-balanced)
để đẩy recall tấn công lên 97–99%; cái giá là biên quyết định nghiêng về "nhạy tấn công" →
**benign bị hi sinh** (đánh đổi precision/recall kinh điển).

---

## 3. Các phương án khắc phục

### Phương án A — Ngưỡng confidence (nhanh, không train lại) `[làm trước]`
Chỉ gán nhãn tấn công khi `confidence ≥ T`; ngược lại → Benign.

- **Cách làm:**
  1. Chạy **threshold sweep**: quét T ∈ {0.5, 0.7, 0.8, 0.9, 0.95} trên benign + 3 file tấn công,
     đo (Benign recall, attack recall từng loại) tại mỗi T → chọn T cân bằng.
  2. Thêm tham số `conf_threshold` vào `replay_config.json` + áp trong `Detector.predict`
     (hoặc khi build `Corpus`): nếu `conf < T` → ép nhãn `Benign`.
  3. (tuỳ chọn) thêm slider ngưỡng trên dashboard để demo trực quan tradeoff.
- **Ưu:** triển khai nhanh, thấy F1 nhích ngay, có câu chuyện học thuật (precision/recall tradeoff).
- **Nhược:** chỉ giảm FP ở các dự đoán "lưỡng lự"; nếu model nhầm với confidence cao thì không cứu được.
- **Công sức:** thấp (sửa server, đã có sẵn hàm validate).

### Phương án B — Thu lại benign "đời" hơn (sửa gốc rễ) `[bản chính thức]`
Làm benign giống người dùng thật thay vì bắn liên tục.

- **Cách làm:**
  1. Sửa `auto_benign_v2.py`: tăng **think-time** ngẫu nhiên giữa request (1–10s), đa dạng
     **đích** (nhiều URL/cổng/dịch vụ), xen kẽ idle, giảm số request/giây mỗi worker.
  2. Thu lại `benign_only` theo quy trình isolated (xem `HUONG_DAN_THU_DU_LIEU_ISOLATED.md`).
  3. Validate lại Benign recall trên file mới.
- **Ưu:** sửa đúng nguồn gốc FP; benign mới sát thực tế → cả demo lẫn (nếu) train đều tốt hơn.
- **Nhược:** phải thu lại dữ liệu; cần thời gian.
- **Công sức:** trung bình.

### Phương án C — Fine-tune lại V8.5 `[nếu còn thời gian]`
Cân bằng lại biên quyết định.

- **Cách làm:**
  1. Thêm benign testbed mới (Phương án B) vào tập train.
  2. **Giảm class weight** của các lớp tấn công (bớt thiên lệch), hoặc tăng tỉ lệ benign.
  3. Train lại, theo dõi **macro-F1** + Benign recall + attack recall (đừng để recall tấn công
     tụt quá nhiều).
- **Ưu:** giải quyết triệt để, kể cả các nhầm lẫn confidence cao.
- **Nhược:** rủi ro overfit / phải tinh chỉnh; tốn công nhất; cần đảm bảo không phá recall tấn công.
- **Công sức:** cao.

### Phương án D — Cải thiện PortScan (F1 0.023 → mục tiêu ≥ 0.85) `[ưu tiên cao]`

PortScan đang là điểm kéo macro-F1 xuống mạnh nhất: recall 1.2%, 85 flow tấn công bị nhầm
chủ yếu thành **DoS (55/85)**.

**Nguyên nhân gốc:**
1. **Thiếu đặc trưng phân biệt port-spread.** V8.5 dùng 80 feature **KHÔNG có**
   `Custom_PortScan_Intensity` (số cổng đích duy nhất / src trong cửa sổ ~2s) — đặc trưng
   từng có trong `dataset_builder_v2.py` (feature thứ 81). Thiếu nó, model không "thấy" được
   việc quét nhiều cổng → portscan (nhiều flow ngắn tới nhiều cổng) trông y hệt DoS (nhiều
   flow ngắn tới 1 cổng).
2. **Quá ít data:** chỉ 131 flow (85 từ attacker) — phần lớn cổng bị firewall **drop** →
   flow 1 gói bị CICFlowMeter loại (đã ghi nhận ở khâu thu).
3. Domain shift: nmap -sT trên WSL/NAT khác với portscan trong CIC-2017.

**Các hướng xử lý (chọn theo công sức):**

- **D1 — Hybrid rule hậu xử lý (KHUYẾN NGHỊ, hợp kiến trúc Snort + ML, không train lại):**
  Sau khi model dự đoán, đếm số **dst port duy nhất theo src trong cửa sổ ngắn**; nếu vượt
  ngưỡng (vd > 15 cổng/2s) → **override nhãn thành PortScan**. Đây đúng tinh thần "chữ ký +
  ML" của đồ án; Snort vốn bắt portscan rất tốt. Bù trực tiếp cho đặc trưng còn thiếu.
  - *Công sức:* thấp–trung bình (thêm bước aggregate trong inference/replay; cần cột Src IP +
    Timestamp — corpus replay đã giữ các cột này).

- **D2 — Thu thêm PortScan data nhiều flow:** **tắt firewall victim** để cổng đóng trả RST
  (flow 2 gói được CICFlowMeter giữ) + quét nhiều dải/nhiều vòng → vài nghìn flow. Dùng cho
  cả demo lẫn (nếu) train lại.
  - *Công sức:* trung bình (thu lại).

- **D3 — Khôi phục feature `Custom_PortScan_Intensity` + train lại model 81-feature:** giải
  pháp triệt để nhất về phía model, nhưng phải đổi số feature (80 → 81) và train lại V8.5.
  - *Công sức:* cao. Gắn với Phương án C.

**Ưu tiên (CẬP NHẬT sau khi thử D1):** Đã thử D1 trên data hiện tại → thất bại vì data
portscan chỉ còn 6 cổng (không có port-spread). ⇒ **D2 là điều kiện TIÊN QUYẾT**: thu lại
portscan (firewall victim TẮT) để có đủ dải cổng → SAU đó bật lại D1 (rule) hoặc D3 (retrain).
Code D1 đã sẵn trong server, chỉ cần `portscan_rule.enabled=true` khi data tốt.

---

## 4. Thứ tự khuyến nghị

> Hai điểm kéo macro-F1 xuống: **PortScan (F1 0.023)** và **Benign recall (75%)**. PortScan
> nặng hơn nên ưu tiên trước.

1. **A (threshold benign)** — độc lập, làm ngay; giảm FP benign → F1 nhích lên cho demo.
2. **D2 (thu lại PortScan, firewall victim TẮT)** — mở khoá việc sửa PortScan (data hiện hỏng).
3. **D1 (bật lại rule port-spread)** *(sau khi có D2)* + **B (thu lại benign "đời" hơn)**.
4. **C + D3 (fine-tune model 81-feature có `Custom_PortScan_Intensity`)** — nếu còn thời gian.

> ⚠️ Đã thử D1 trước (2026-06-27) nhưng thất bại do data portscan thiếu port-spread (xem
> snapshot mục 7). Vì vậy A lên làm trước, PortScan phải chờ D2.

> Lưu ý đo F1: chốt **macro-F1** (trung bình theo lớp), tính nhất quán giữa dashboard (client)
> và đánh giá offline. Ghi rõ cách tính trong báo cáo.

---

## 5. Tiêu chí thành công

- **PortScan F1:** từ 0.023 → **≥ 0.85** (recall 1.2% → ≥ 0.85).
- **Benign recall:** từ ~66% → **≥ 90%** (FP < 10%).
- **Attack recall (BF/DoS/Web):** giữ **≥ 95%** (không hi sinh khi giảm FP / thêm rule).
- **Macro-F1:** từ **0.7353** → kỳ vọng **> 0.90**; báo cáo kèm confusion matrix trước/sau.

---

## 6. Rủi ro & lưu ý

- Threshold quá cao → bỏ sót tấn công (attack recall tụt). Phải dò T cân bằng, không chọn mù.
- Thu lại benign vẫn phải **isolated** (attacker IP `192.168.0.106`, không chạy attack song song).
- Khi fine-tune, dễ "chữa benign mà hỏng tấn công" — luôn theo dõi đồng thời cả hai chiều.
- Minh bạch trong báo cáo: nêu rõ FP benign đến từ bộ sinh benign tự động + domain shift, và
  cách đã xử lý — đây là điểm cộng học thuật, không phải điểm yếu cần giấu.

---

## 7. SNAPSHOT chỉ số — mốc gốc để so sánh (2026-06-27)

> **Đây là baseline TRƯỚC mọi chỉnh sửa.** Mỗi lần áp dụng một phương án (A/B/C), chạy lại
> cùng cách đo và thêm một snapshot mới bên dưới để đối chiếu.

**Cách đo (giữ cố định để so sánh công bằng):**
- Model: V8.5 (`v8_5_model.pt`), chưa chỉnh sửa.
- Dữ liệu: 5 file `*_only.pcap_Flow.csv`, mỗi file lấy ≤ 8000 flow (cùng cap với demo).
- Nhãn: label-by-IP (Src == `192.168.0.106` → nhãn loại của file; còn lại → Benign).
- Gộp tất cả file → `classification_report` (macro). Tổng: **32.131 flow**.

### Bảng chỉ số tổng (gộp)

| Lớp | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Benign | 0.9921 | **0.7543** | 0.8570 | 11.225 |
| Brute Force | 0.9603 | 0.9976 | 0.9786 | 7.099 |
| DoS | 0.8709 | 0.9874 | 0.9255 | 6.435 |
| **PortScan** | 0.5000 | **0.0118** | **0.0230** | 85 |
| Web Attack | 0.8105 | 0.9926 | 0.8924 | 7.287 |
| **Accuracy** | | | **0.9068** | |
| **Macro avg** | 0.8268 | 0.7487 | **0.7353** | |
| Weighted avg | 0.9183 | 0.9068 | 0.9034 | |
| Balanced accuracy | | 0.7487 | | |

### Recall lớp chính theo từng file
| File | Flows | Recall lớp chính |
|---|---|---|
| benign | 8000 | 65.9% |
| portscan | 131 | **1.2%** |
| bruteforce | 8000 | 99.8% |
| webattack | 8000 | 99.3% |
| dos | 8000 | 98.7% |

### Hai điểm kéo macro-F1 xuống (con số cần cải thiện)
1. **PortScan — F1 0.023, recall 1.2%** (nặng nhất). 85 flow portscan từ attacker bị nhầm chủ
   yếu thành **DoS** (55/85) và Benign (15). Nguyên nhân nghi: data portscan quá ít/không đại
   diện + chữ ký nmap -sT (flow ngắn) giống DoS → **cần thu thêm PortScan + xem lại đặc trưng**
   (bổ sung mục này vào kế hoạch ngoài Benign recall).
2. **Benign — recall 75.4% (file riêng 65.9%)** → nguồn FP (mục 1–4 ở trên).

**Mục tiêu sau chỉnh sửa:** Macro-F1 từ **0.7353** → kỳ vọng **> 0.90** (chủ yếu nhờ kéo
PortScan-F1 và Benign-recall lên), giữ recall 3 lớp mạnh ≥ 0.95.

---

### Snapshot sau chỉnh sửa (điền dần)

| Ngày | Thay đổi | Macro-F1 | Benign recall | PortScan F1 | Ghi chú |
|---|---|---|---|---|---|
| 2026-06-27 | *(baseline, chưa sửa)* | 0.7353 | 0.7543 | 0.0230 | mốc gốc |
| 2026-06-27 | Thử D1 (rule port-spread) → **ĐÃ TẮT** | 0.7092 | 0.6018 | 0.0011 | Regression. Data portscan chỉ có 6 cổng (scan flows bị firewall drop) còn benign 760 cổng → rule bắn nhầm benign, không bắt được portscan. Revert. |
| 2026-06-27 | **A — conf_threshold=0.6** ✅ | **0.7781** | **0.9513** | 0.0000 | Benign recall 75→95%, Web F1 0.89→0.99, DoS 0.93→0.95, BF 0.98→0.99, accuracy 0.91→**0.97**, weighted-F1 0.90→**0.97**. Macro-F1 chỉ còn bị PortScan (=0) kìm → cần D2. |
| 2026-06-27 | **A + D2 + D1** (thu PortScan trên Win11 host + bật rule, src=attacker) ✅✅ | **0.9778** | **0.9518** | **0.9959** | D2: capture trên Win11 host → PortScan 222k flow / **22k cổng**. D1: rule port-spread bật (ngưỡng 15, chỉ override src=attacker) → PortScan F1 0.02→**0.996** (precision 1.0), benign recall giữ 95%. **Mọi lớp ≥0.95, accuracy 0.977.** ĐẠT mục tiêu. |

> **Phát hiện quan trọng:** không thể cải thiện PortScan bằng rule/model trên data hiện tại
> vì **tín hiệu port-spread đã mất** (chỉ 6 cổng đích sống sót). **Bắt buộc làm D2 trước**
> (thu lại portscan với firewall victim TẮT → cổng đóng trả RST → flow giữ đủ dải cổng quét),
> rồi mới bật lại D1 hoặc retrain (D3).
