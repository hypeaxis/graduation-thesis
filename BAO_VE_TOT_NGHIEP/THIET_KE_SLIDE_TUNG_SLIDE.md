# THIẾT KẾ SLIDE BẢO VỆ — TỪNG SLIDE
## Đề tài: Phát triển hệ thống phát hiện tấn công mạng bằng phát hiện bất thường
> Cách tiếp cận kỹ thuật: lai ghép Snort + FT-Transformer

> Tài liệu này là **bản thiết kế chi tiết từng slide** để dựng file PowerPoint. Đi kèm với `KICH_BAN_THUYET_TRINH.md` (lời nói). Cả hai bám theo `GUIDELINE_SLIDE_BAO_VE.md`.
>
> **Ràng buộc bắt buộc:** 18 slide (không kể phụ lục) · template **HUST PPT 2022 tỉ lệ 4×3** (`HUST_PPT_template_2022_blue_4x3.pptx`) · 12–15 phút · mỗi slide **≤ 6 dòng**, gạch đầu dòng + hình (KHÔNG văn xuôi) · KHÔNG từ tuyệt đối ("nhất", "triệt để") · demo ghi rõ **replay ≠ live**.
>
> **Quy ước đọc:** *Nội dung on-slide* = chữ thật sẽ hiện trên slide (đã rút gọn). *Hình/Bảng* = file trong `Noi_dung_do_an/SOICT_DATN_Research_VIE_Template/figures/` (dùng bản `.png`). *Ghi chú thiết kế* = bố cục, màu, hiệu ứng, nhấn mạnh.

---

## Bảng màu & quy ước hình thức (áp dụng toàn bộ slide)

| Yếu tố | Quy ước |
|---|---|
| Màu chủ đạo | Xanh HUST (theo template) cho tiêu đề & khối nhấn |
| Màu nhấn kết quả "Đạt" | Xanh lá đậm cho số liệu đạt mục tiêu (0,9294 · 0,917) |
| Màu cảnh báo/vấn đề | Đỏ/cam cho con số sụt giảm (21,93% · MCC −0,015) |
| Font | Theo template HUST (tiêu đề đậm, thân ~24pt, số liệu lớn ~40pt) |
| 3 giai đoạn | Dùng **3 màu cố định** xuyên suốt: GĐ1 xám-xanh · GĐ2 xanh dương · GĐ3 cam — để hội đồng nhận diện mạch |
| Footer | Số slide + tên viết tắt đề tài (góc phải dưới) |
| Chú thích hình | Cỡ nhỏ, ghi nguồn dưới mỗi hình (vd "Nguồn: thực nghiệm CIC-IDS-2017") |

**Icon dẫn 3 thách thức ↔ 3 giai đoạn** (dùng lặp lại để tạo mạch): ⚖️ mất cân bằng · 🔀 covariate shift · 🧩 giới hạn một tầng.

---

# PHẦN ĐẦU (Slide 1–3)

## Slide 1 — Trang bìa

- **Layout:** Trang bìa mẫu HUST. Logo trường trên cùng, khối tên đề tài giữa, thông tin SV/GVHD dưới.
- **Nội dung on-slide:**
  - Tên đề tài: **"Phát triển hệ thống phát hiện tấn công mạng bằng phát hiện bất thường"**
  - Sinh viên: **Đỗ Tuấn Minh** — MSSV **20225741** — Lớp **Việt Nhật 07**, **Trường Công nghệ Thông tin và Truyền thông**
  - Giảng viên hướng dẫn: **PGS.TS. Nguyễn Linh Giang**
  - *[Trường / Viện · Tháng, Năm bảo vệ]*
- **Hình/Bảng:** Logo HUST (có sẵn trong template).
- **Ghi chú thiết kế:** Không nhồi chữ. Không đọc nguyên bìa khi nói. Kiểm tra chính tả tên đề tài & tên GVHD (đây là chỗ hay bị soi nhất).

---

## Slide 2 — Nội dung trình bày

- **Layout:** 1 cột, 5 mục đánh số, mỗi mục 1 icon nhỏ.
- **Nội dung on-slide:**
  1. Mục tiêu & bài toán
  2. Ba thách thức cốt lõi
  3. Phương pháp — 3 giai đoạn nghiên cứu
  4. Kết quả thực nghiệm
  5. Kết luận & hướng phát triển
- **Hình/Bảng:** không (hoặc thanh tiến trình ngang minh hoạ 5 bước).
- **Ghi chú thiết kế:** Đây là "bản đồ" cho hội đồng. Có thể highlight mục 3 & 4 (trọng tâm). Nói ≤ 30 giây.

---

## Slide 3 — Đặt vấn đề & Mục tiêu

- **Layout:** Chia đôi. Trái = "Vấn đề" (2 số liệu lớn). Phải = "Mục tiêu" (3 gạch).
- **Nội dung on-slide:**
  - **Vấn đề:** Tấn công mạng gia tăng — IBM 2023: chi phí TB **4,45 triệu USD/vụ**, phát hiện TB **204 ngày**.
  - Bài toán NIDS = phân loại mỗi *flow* → Benign / loại tấn công, **thời gian thực**.
  - **Mục tiêu:**
    - (1) Macro F1 **> 0,9** trên CIC-IDS-2017
    - (2) Macro F1 **> 0,9** trên Testbed thực
    - (3) Snort + ML **phát hiện bổ sung** trong hệ thống End-to-End
- **Hình/Bảng:** icon $ và đồng hồ cho 2 số liệu; không cần hình nặng.
- **Ghi chú thiết kế:** 2 con số IBM để cỡ lớn tạo ấn tượng. 3 mục tiêu đánh số rõ — sẽ được "đối chiếu Đạt" lại ở Slide 16 (tạo vòng khép kín).

---

# PHẦN THÂN — NGHIÊN CỨU (Slide 4–13)

## Slide 4 — Bài toán & Ba thách thức cốt lõi *(bản lề cả bài)*

- **Layout:** 3 khối ngang, mỗi khối 1 icon + 1 câu + 1 con số lớn. Dưới cùng: 1 dòng "→ 3 giai đoạn".
- **Nội dung on-slide:**
  - ⚖️ **Mất cân bằng cực đoan** — Benign 83–99%; Benign:Infiltration tới **65.000:1**
  - 🔀 **Covariate shift** — CIC 99,55% → Testbed WSL2 **21,93%**
  - 🧩 **Giới hạn một tầng** — Snort bỏ sót zero-day; ML bỏ sót tấn công "giống Benign"
  - *→ Mỗi thách thức được giải bởi đúng một giai đoạn.*
- **Hình/Bảng:** `fig_cic_imbalance.png` (bar chart log-scale minh hoạ mất cân bằng) — đặt cạnh khối ⚖️.
- **Ghi chú thiết kế:** Slide quan trọng nhất về mặt cấu trúc. 3 icon ở đây = 3 màu giai đoạn, sẽ lặp lại ở Slide 6/7/8/11. Con số 65.000:1 và 21,93% để cỡ lớn, màu đỏ.

---

## Slide 5 — Giới hạn hướng tiếp cận hiện hành & lý do chọn FT-Transformer

- **Layout:** Bảng 3 dòng (trên) + 1 khối "chốt" (dưới).
- **Nội dung on-slide:**

  | Hướng | Ưu | Nhược |
  |---|---|---|
  | Signature (Snort) | Nhanh, chính xác với tấn công đã biết | Bỏ sót zero-day / không có dấu hiệu |
  | ML thống kê (RF/SVM) | Không cần viết rule | Kém với lớp < 0,01% |
  | **DL — FT-Transformer** | **Attention học tương tác đặc trưng** | Hộp đen, cần đủ dữ liệu |

  - **Chốt:** Infiltration lộ qua **tổ hợp** (đích lạ + upload cao + khuya) → FTT hợp tabular hơn MLP/RF.
- **Hình/Bảng:** (tuỳ chọn) icon Attention nối 3 đặc trưng → 1 nhãn.
- **Ghi chú thiết kế:** Phải **hiểu** ô "Attention học tương tác đặc trưng" — hội đồng sẽ hỏi "vì sao không MLP". Không nói "FTT tốt nhất".

---

## Slide 6 — Kiến trúc tổng quan (Pipeline + 3 giai đoạn nhân-quả)

- **Layout:** 2 tầng.
  - *Tầng trên — Pipeline End-to-End (ngang):* `Traffic → Snort (dấu hiệu) → CICFlowMeter (trích đặc trưng) → FT-Transformer (ML đa lớp) → Alert Aggregator → Cảnh báo`.
  - *Tầng dưới — Mạch 3 giai đoạn (ngang, mũi tên nhân-quả):* `NSL-KDD (nền tảng) → CIC-IDS-2017 (Macro F1 0,93) → Testbed thực (Macro F1 0,92)`.
- **Nội dung on-slide:** chỉ nhãn khối + 3 mũi tên; chú thích mũi tên: *"kết quả GĐ trước lộ vấn đề GĐ sau"*.
- **Hình/Bảng:** Sơ đồ tự vẽ (SmartArt/hình khối). Có thể tham chiếu `fig_theory_linkage.png` để phụ hoạ liên kết lý thuyết (hoặc để Phụ lục).
- **Ghi chú thiết kế:** Đây là bức tranh lớn; các slide sau "zoom" từng khối. Dùng 3 màu giai đoạn cho 3 khối dưới. Giữ sơ đồ thoáng, ≤ 6 khối mỗi tầng.

---

## Slide 7 — Giai đoạn 1: Mô hình nền tảng (NSL-KDD)

- **Layout:** Trái = sơ đồ 2 tầng; Phải = kết quả + 1 dòng "bài học".
- **Nội dung on-slide:**
  - Kiến trúc 2 tầng: **Autoencoder Anomaly Gate** (lọc Benign, không cần nhãn tấn công) → **Stacking Ensemble** (FTT + LightGBM → Meta-LR)
  - Mất cân bằng: CB-Focal Loss · Boost-Minority Val · WeightedRandomSampler
  - **Kết quả: Macro F1 = 0,6809** (đánh giá train/test tách biệt)
  - R2L Recall thấp = **giới hạn cứng của dataset** (protocol shift telnet→pop3), không phải lỗi mô hình → lý do chuyển sang CIC
- **Hình/Bảng:** `fig_nslkdd_perclass.png` (per-class) hoặc `fig_nslkdd_ablation.png`.
- **Ghi chú thiết kế:** Định vị GĐ1 là **nền tảng lấy số liệu & xác định ceiling**, KHÔNG khoe là "hệ thống triển khai". Màu GĐ1 (xám-xanh).

---

## Slide 8 — Giai đoạn 2: Two-Stage Cascade (CIC-IDS-2017)

- **Layout:** Sơ đồ luồng ngang, có nhãn tỉ lệ % trên mũi tên.
- **Nội dung on-slide:**
  - **Gating Network** (nhị phân Benign/Suspicious, ngưỡng **0,85**) → lọc **~82,7% Benign** thoát pipeline
  - **Expert Network** (9 lớp, gộp từ 15 nhãn gốc) chỉ xử lý **~17,3% Suspicious**
  - Vì sao 2 tầng: tách "phát hiện bất thường" khỏi "phân loại chi tiết" → gradient lớp hiếm không bị 83,4% Benign lấn át
  - *Ablation:* 1-Stage Macro F1 0,7831 → Two-Stage 0,8817
- **Hình/Bảng:** Sơ đồ Two-Stage tự vẽ (Traffic → Gating → Benign thoát / Suspicious → Expert → 9 lớp).
- **Ghi chú thiết kế:** Ngưỡng 0,85 là điểm hay bị hỏi — nhấn "bảo thủ để ưu tiên recall tấn công". Màu GĐ2 (xanh dương).

---

## Slide 9 — Giai đoạn 2: Hard Negative Mining cho lớp hiếm

- **Layout:** Trái = vòng lặp HNM (4 bước); Phải = biểu đồ cải thiện.
- **Nội dung on-slide:**
  - Ý tưởng: thu mẫu **phân loại sai** → thêm vào train với **$w_{hard}=2{,}0$** → lặp **2 vòng**
  - Botnet F1: **0,4787 → 0,6512 (+36%)**
  - Infiltration F1: **0,3821 → 0,5903 (+54,5%)**
  - **Vượt** class weight ×10 (Botnet: HNM 0,6512 vs weight 0,5218)
- **Hình/Bảng:** `fig_hnm_ablation.png`.
- **Ghi chú thiết kế:** Thông điệp 1 câu: *"tăng gradient vào **biên quyết định** hiệu quả hơn tăng class weight đều tay"*. Vòng lặp vẽ dạng chu trình (train → infer → thu hard neg → retrain).

---

## Slide 10 — Giai đoạn 2: Asymmetric Ensemble Voting & Kết quả

- **Layout:** Trên = sơ đồ 3 mô hình + 2 luật; Dưới = khối kết quả lớn.
- **Nội dung on-slide:**
  - Ensemble: **FTT + Random Forest + KNN** (sai trên mẫu khác nhau → bổ sung)
  - **2 luật bất đối xứng:**
    - Infiltration — *Ưu tiên*: RF **hoặc** KNN bỏ phiếu → nhận (tăng Recall)
    - Botnet — *Đồng thuận*: **cả 3** cùng phiếu mới nhận (tăng Precision, chống FP)
  - **Kết quả GĐ2: Accuracy 99,55% · Macro F1 = 0,9294** → **Đạt mục tiêu 1**
  - Infiltration F1 0,7407 · Botnet F1 0,7344
- **Hình/Bảng:** `fig_ensemble_compare.png`.
- **Ghi chú thiết kế:** Giải thích nghịch lý: Asymmetric có Accuracy **thấp hơn** Majority (99,55 vs 99,61) nhưng Macro F1 **cao hơn** — vì 2 lớp hiếm có trọng số bằng nhau trong Macro F1. Khối "0,9294 → Đạt mục tiêu 1" tô xanh lá.

---

## Slide 11 — Giai đoạn 3: Chẩn đoán Covariate Shift *(điểm nhấn mạnh nhất)*

- **Layout:** Biểu đồ cột "sụt giảm" cỡ lớn (99,55% → 21,93% → 6,87%) + 1 khối "phản trực giác".
- **Nội dung on-slide:**
  - CIC → Testbed WSL2: Accuracy **99,55% → 21,93%**, **MCC = −0,015** (sai ngược, tệ hơn đoán ngẫu nhiên)
  - Phản trực giác: **Re-fit Scaler còn tệ hơn** → **6,87%**
  - Nguyên nhân: switch vật lý → Hyper-V NAT đổi packet size & timing (IAT, flag counts)
  - **Kết luận:** fine-tuning không đủ → buộc **thu dữ liệu thực + retrain hoàn toàn**
- **Hình/Bảng:** `fig_da_comparison.png`.
- **Ghi chú thiết kế:** Đây là đóng góp nghiên cứu mạnh nhất — dành thời gian. Con số 21,93% & −0,015 màu đỏ, cỡ rất lớn. Màu GĐ3 (cam). **Không cắt slide này dù quá giờ.**

---

## Slide 12 — Giai đoạn 3: Custom IDS Testbed & Tính trung thực đánh giá

- **Layout:** Trái = sơ đồ Testbed 2 máy; Phải = 2 khối "trung thực phương pháp".
- **Nội dung on-slide:**
  - Thu tấn công **thực** từ Kali Linux trên LAN (WSL2 Mirrored Networking) → dataset **V8.5: 111.825 flows, 5 lớp**
  - **Trung thực 1 — PortScan không phân tách trong NAT:** < 9% F1 qua **mọi** thuật toán (vấn đề dữ liệu) → dùng **surrogate CIC Friday PortScan**
  - **Trung thực 2 — Val đa dạng miền tin cậy hơn:** val đồng nhất miền ~97% nhưng val đa dạng miền **91,7%**; riêng BruteForce F1 chênh **14%** → chênh do **chất lượng đánh giá**
- **Hình/Bảng:** Sơ đồ Testbed (Kali → LAN/WiFi → Windows+WSL2 victim). Tuỳ chọn `fig_portscan_inseparable.png` (hoặc để Phụ lục).
- **Ghi chú thiết kế:** Chủ động nêu 2 điểm trung thực = ghi điểm phương pháp luận. Đây là **đóng góp 4** (bằng chứng val đồng nhất miền inflate metric).

---

## Slide 13 — Giai đoạn 3: Kết quả V8.5 & Hệ thống Hybrid End-to-End

- **Layout:** Trái = bảng/biểu đồ per-class V8.5; Phải = khối "hệ thống chạy thật".
- **Nội dung on-slide:**
  - **V8.5: Macro F1 = 91,7% · Balanced Acc 91,1% · MCC 0,865** → **Đạt mục tiêu 2**
  - PortScan F1 100% (surrogate) · DoS F1 0,93 · BruteForce F1 0,86 (Recall 0,90)
  - Hệ thống: **Snort 3 + CICFlowMeter + FTT V8.5** chạy song song
  - Phần cứng **phổ thông**: i7 Gen11, 16GB RAM, **không GPU**, WSL2 Ubuntu 22.04
- **Hình/Bảng:** `fig_v85_perclass.png`.
- **Ghi chú thiết kế:** Chuyển mạch từ "nghiên cứu mô hình" → "hệ thống chạy được". Khối "91,7% → Đạt mục tiêu 2" tô xanh lá. Nhấn "không GPU" (điểm cộng tính khả thi).

---

# PHẦN KẾT QUẢ TÍCH HỢP & KẾT LUẬN (Slide 14–18)

## Slide 14 — Thử nghiệm End-to-End: Tính bổ sung Snort ↔ ML

- **Layout:** Bảng gọn 5 hàng × 2 cột {Snort, FTT}, tô màu ô "chỉ 1 tầng bắt được".
- **Nội dung on-slide:**

  | Tấn công | Snort | FTT V8.5 |
  |---|---|---|
  | PortScan (nmap) | ✔ | ✔ |
  | BruteForce (hydra) | ✔ | ✔ |
  | **DoS slowhttptest** | ✖ (HTTP hợp lệ) | **✔ chỉ ML** |
  | Web Attack SQLi | ✔ | ✔ |
  | **Web Attack XSS** | **✔ chỉ Snort** (`<script>`) | ✖ payload ngắn |

  - **Kết luận:** không tấn công nào bị bỏ sót hoàn toàn bởi **cả hai** tầng → **Đạt mục tiêu 3**
- **Hình/Bảng:** bảng tự làm (2 ô nhấn màu: DoS→ML, XSS→Snort).
- **Ghi chú thiết kế:** Đây là bằng chứng "lai ghép" có giá trị thật. 2 ô đối lập (DoS/XSS) là linh hồn slide — tô nổi bật. **Không cắt slide này.**

---

## Slide 15 — Demo hệ thống (GĐ5 Replay V8.5)

- **Layout:** Ảnh chụp dashboard chiếm ~70% slide + 1 dải chú thích "replay ≠ live".
- **Nội dung on-slide:**
  - Ảnh chụp `dashboard.html` đang phát hiện realtime (kịch bản "dos")
  - Dải chú thích rõ: **Replay** — phát lại corpus flow đã thu (CSV) → suy luận realtime qua WebSocket
  - ⚠️ **Đây là hệ thống End-to-End thật mà báo cáo đo. Bắt gói trực tiếp (live capture) = hướng phát triển.**
- **Hình/Bảng:** ảnh chụp `Final/05_Replay_Detection/dashboard.html`.
- **Ghi chú thiết kế:** **Bắt buộc** có 1 câu định vị "replay ≠ live" để tránh hội đồng hỏi bắt bí. Nếu demo trực tiếp được thì càng tốt, nhưng vẫn phải nói rõ bản chất replay.

---

## Slide 16 — Đối chiếu mục tiêu & Tổng kết đóng góp

- **Layout:** Trên = bảng 3 mục tiêu → Đạt; Dưới = 4 đóng góp (mỗi cái 1 dòng, icon).
- **Nội dung on-slide:**

  | Mục tiêu | Kết quả |
  |---|---|
  | Macro F1 > 0,9 trên CIC | **0,9294 ✔** |
  | Macro F1 > 0,9 trên Testbed | **0,917 ✔** |
  | Snort + ML bổ sung End-to-End | **Xác nhận ✔** |

  - **4 đóng góp:** (1) Two-Stage Cascade + Asymmetric Voting · (2) HNM 2 vòng cho lớp hiếm · (3) Chẩn đoán covariate shift + Testbed thực + bằng chứng inflate metric · (4) Hybrid IDS End-to-End trên phần cứng phổ thông
- **Hình/Bảng:** không bắt buộc; có thể lặp lại 3 màu giai đoạn cho 3 đóng góp đầu.
- **Ghi chú thiết kế:** Cột "Kết quả" tô xanh lá. Đây là slide "khép vòng" với Slide 3.

---

## Slide 17 — Hạn chế & Hướng phát triển

- **Layout:** 2 cột. Trái = Hạn chế; Phải = Hướng phát triển.
- **Nội dung on-slide:**
  - **Hạn chế:** Testbed chỉ **5/9 lớp** (thiếu DDoS, Botnet, Infiltration, Heartbleed) · flow-based khó với Infiltration/Botnet · PortScan dùng surrogate · FTT hộp đen (thiếu explainability) · độ trễ ML ~30s với DoS
  - **Hướng phát triển:** Temporal/session-level (LSTM/Temporal Transformer) cho Botnet/Infiltration & Web Attack · automated feature engineering · Federated Learning multi-site · **hoàn thiện đường bắt gói trực tiếp (live capture) — đang phát triển**
- **Hình/Bảng:** không bắt buộc.
- **Ghi chú thiết kế:** Nêu hạn chế **trung thực, ngắn** = ghi điểm. Đây là **chỗ hợp lý duy nhất** để nhắc `live_detection` — như định hướng tương lai, KHÔNG phải kết quả đã có.

---

## Slide 18 — Cảm ơn

- **Layout:** 1 dòng lời cảm ơn giữa slide + logo trường + thông tin liên hệ (tuỳ chọn).
- **Nội dung on-slide:** *"Trân trọng cảm ơn Hội đồng đã lắng nghe."* + email/liên hệ (tuỳ chọn).
- **Hình/Bảng:** logo HUST.
- **Ghi chú thiết kế:** Slide dừng trong lúc Q&A — nên tối giản, chuyên nghiệp, đúng chính tả.

---

# PHỤ LỤC (slide dự phòng — KHÔNG nằm trong 18 slide chính, dùng khi hội đồng hỏi)

| Slide phụ lục | Nội dung | Hình |
|---|---|---|
| P1 | Bảng per-class **đầy đủ** CIC-IDS-2017 (9 lớp) | (bảng 5.3.5) |
| P2 | Bảng per-class **đầy đủ** V8.5 (5 lớp) + nguồn validation | (bảng 5.5.3) |
| P3 | Ablation Two-Stage & HNM vs class weight | (bảng 5.3.1 / 5.3.4) |
| P4 | **PortScan không phân tách** — <9% F1 mọi thuật toán | `fig_portscan_inseparable.png` |
| P5 | Cấu hình phần cứng/phần mềm (Phụ lục A) + siêu tham số (Phụ lục B) | (bảng) |
| P6 | Bảng **độ trễ** phát hiện Snort vs FTT | (bảng 5.6.3) |
| P7 | Layer Freezing / Model Surgery (thực nghiệm chẩn đoán trung gian) | (bảng 5.4.2) |

---

# CHECKLIST DỰNG SLIDE (đối chiếu trước khi nộp)

- [ ] Đúng template HUST 4×3, đúng logo/màu trường.
- [ ] 18 slide chính; phần dư đã chuyển Phụ lục.
- [ ] Mỗi slide ≤ 6 dòng; không đoạn văn copy từ báo cáo.
- [ ] 3 màu giai đoạn nhất quán (GĐ1/GĐ2/GĐ3) ở Slide 4,6,7,8,11,16.
- [ ] Mọi hình có chú thích nguồn; mọi từ viết tắt (NIDS, FTT, HNM, MCC, WSL2, IAT, NAT…) hiểu & nói được.
- [ ] Không từ tuyệt đối ("nhất", "triệt để").
- [ ] Slide 15 ghi rõ **replay ≠ live**; `live_detection` chỉ xuất hiện ở Slide 17.
- [ ] Số liệu khớp báo cáo: 0,6809 · 0,9294 / 99,55% · 21,93% / −0,015 · 6,87% · 91,7% / 91,1% / 0,865 · 65.000:1.
- [ ] 0 lỗi chính tả (đặc biệt Slide 1).
- [ ] Đã bấm giờ tập nói ≥ 2 lần, ≤ 15 phút.
</content>
</invoke>
