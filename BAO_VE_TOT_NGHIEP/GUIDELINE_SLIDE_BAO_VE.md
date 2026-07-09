# GUIDELINE SLIDE BẢO VỆ ĐỒ ÁN TỐT NGHIỆP
## Đề tài: Phát triển hệ thống phát hiện tấn công mạng bằng phát hiện bất thường
> Cách tiếp cận kỹ thuật: lai ghép Snort + FT-Transformer · SV: Đỗ Tuấn Minh (MSSV 20225741) · GVHD: PGS.TS. Nguyễn Linh Giang

> Tài liệu này dựng riêng cho đồ án này, dựa trên: (1) 2 hướng dẫn làm slide của HUST trong `các hướng dẫn, mẫu/`, và (2) nội dung thực tế trong `Final/` + `Noi_dung_do_an/`.
>
> **Phạm vi bảo vệ lần này:** CHỈ trình bày nội dung đã hoàn thành trong `Final/` và quyển trong `Noi_dung_do_an/`. **KHÔNG** trình bày các nội dung đang phát triển trong `live_detection/` (bắt gói trực tiếp/real-time capture). Bản thân `Final/README.md` cũng nêu rõ **"replay ≠ live"**: demo hệ thống thật = **GĐ5 replay V8.5**; đường bắt gói trực tiếp chỉ được nhắc như **hướng phát triển**.

---

## 0. Ràng buộc bắt buộc (từ 2 file hướng dẫn HUST)

| Mục | Yêu cầu |
|---|---|
| Thời gian trình bày | **12–15 phút** |
| Số slide | **15–18 slide** (phần vượt → đưa vào **Phụ lục**) |
| Template | **HUST PPT Template 2022, tỉ lệ 4x3** (file `HUST_PPT_template_2022_blue_4x3.pptx` đã có sẵn trong folder) |
| Định hướng đề tài | **Nghiên cứu + tích hợp** (xem Mục 1 bên dưới) |
| Nội dung | Tóm tắt báo cáo + **chú trọng công việc cá nhân đã làm và kết quả nổi bật** |

**Luật vàng khi làm slide (rút từ hướng dẫn — tuân thủ tuyệt đối):**
- ❌ KHÔNG copy/paste câu/đoạn văn từ báo cáo vào slide. Slide là gạch đầu dòng + hình, không phải văn xuôi.
- ❌ KHÔNG trình bày theo chương/mục như báo cáo ("Chương 1, Chương 2…"). Trình bày theo **mạch vấn đề → giải pháp → kết quả**.
- ✅ Hiểu **mọi** hình, công thức, ký hiệu, từ viết tắt trên slide (hội đồng sẽ hỏi).
- ✅ Tránh từ tuyệt đối. Nói "một trong những…", "đạt mức cạnh tranh…", KHÔNG nói "tốt nhất", "giải quyết triệt để".
- ✅ Nếu có thay đổi lớn so với báo cáo → phải chỉ rõ khi trình bày.
- ✅ **Tuyệt đối không lỗi chính tả.** Bấm giờ tập nói thử ít nhất 2 lần.

---

## 1. Định hướng đề tài & cách phân bổ slide

Đồ án này là **hỗn hợp Nghiên cứu + Tích hợp hệ thống**, nghiêng về **nghiên cứu** (mục 2.2 trong hướng dẫn HUST):
- Phần **nghiên cứu** (trọng tâm): 3 giai đoạn — kiến trúc mô hình, xử lý mất cân bằng lớp, chẩn đoán & giải quyết covariate shift.
- Phần **tích hợp/ứng dụng**: hệ thống Hybrid IDS End-to-End (Snort + CICFlowMeter + FTT V8.5) + demo replay (GĐ5).

→ Áp dụng cấu trúc **2.2 (định hướng nghiên cứu)**: *Tổng quan → Phân tích bài toán → Giải quyết bài toán theo từng giai đoạn → Kết quả & đánh giá → Kết luận*, có bổ sung 1 slide hệ thống End-to-End cho phần tích hợp.

**Thông điệp cốt lõi (mạch xuyên suốt — phải bám):**
> "Không một hướng tiếp cận đơn lẻ nào đủ. Tôi xây hệ thống **lai ghép Snort + FT-Transformer** qua **3 giai đoạn nghiên cứu tuần tự**, trong đó **kết quả của giai đoạn trước lộ ra vấn đề của giai đoạn sau**: NSL-KDD (nền tảng) → CIC-IDS-2017 (Macro F1 0,93) → Testbed thực (giải quyết covariate shift, Macro F1 0,92)."

Mỗi giai đoạn giải quyết đúng 1 thách thức. Ba thách thức = ba giai đoạn = xương sống bài nói:
1. Mất cân bằng lớp cực đoan → GĐ2 (HNM + Asymmetric Voting).
2. Covariate shift train↔deploy → GĐ3 (chẩn đoán + thu dữ liệu thực + retrain V8.5).
3. Giới hạn một tầng đơn lẻ → GĐ4 Hybrid (Snort bù ML và ngược lại).

---

## 2. Bố cục 18 slide (khung chi tiết)

> Cột "Nói gì" = ý chính để **nói**, KHÔNG phải chữ để dán lên slide. Cột "Hình/Bảng" ưu tiên dùng file có sẵn trong `SOICT_DATN_Research_VIE_Template/figures/`.

### PHẦN ĐẦU (Slide 1–3)

**Slide 1 — Trang bìa**
- Nội dung: Tên đề tài · Họ tên SV + MSSV + Lớp/Viện · GVHD · Trường/Viện (theo template).
- Nói: 1 câu giới thiệu tên đề tài, không đọc nguyên bìa.

**Slide 2 — Nội dung trình bày**
- Liệt kê 5 mục: Mục tiêu · Bài toán & thách thức · Phương pháp (3 giai đoạn) · Kết quả thực nghiệm · Kết luận & hướng phát triển.
- Nói: 20–30 giây, chỉ "map" cho hội đồng biết đường đi.

**Slide 3 — Đặt vấn đề & Mục tiêu**
- Đặt vấn đề (ngắn): tấn công mạng tăng — dẫn 1 số liệu ấn tượng (IBM 2023: chi phí trung bình 1 vụ vi phạm dữ liệu 4,45 triệu USD, thời gian phát hiện TB 204 ngày).
- Mục tiêu (phát biểu 3 gạch): (1) Macro F1 > 0,9 trên CIC-IDS-2017; (2) Macro F1 > 0,9 trên Testbed thực; (3) Hybrid Snort + ML phát hiện bổ sung trong End-to-End.
- Nói: nêu bài toán NIDS = phân loại flow Benign/tấn công real-time; chốt bằng 3 mục tiêu.

### PHẦN THÂN — Nghiên cứu (Slide 4–13)

**Slide 4 — Bài toán & Ba thách thức cốt lõi**  *(bản lề của cả bài)*
- 3 thách thức, mỗi cái 1 dòng + 1 con số:
  1. **Mất cân bằng cực đoan** — Benign 83–99%, Infiltration <0,01%, tỉ lệ tới **65.000:1**.
  2. **Covariate shift** — mô hình CIC đạt 99,55% nhưng rơi xuống **21,93%** khi deploy sang Testbed WSL2.
  3. **Giới hạn một tầng** — Snort bỏ sót zero-day; ML bỏ sót tấn công "trông giống Benign".
- Hình gợi ý: `fig_cic_imbalance.png` (minh hoạ mất cân bằng).
- Nói: đây là 3 thách thức → dẫn thẳng vào 3 giai đoạn. **Nhấn**: mỗi giai đoạn giải đúng 1 thách thức.

**Slide 5 — Giới hạn các hướng tiếp cận hiện hành & lý do chọn FT-Transformer**
- Bảng 3 dòng ngắn: Signature (Snort) — nhanh, bỏ sót zero-day; ML thống kê (RF/SVM) — kém với lớp <0,01%; DL/FTT.
- Điểm chốt: **FT-Transformer** dùng Attention học **tương tác giữa đặc trưng** (vd Infiltration = destination bất thường + upload cao + khuya) → phù hợp dữ liệu tabular hơn MLP/RF.
- Nói: giải thích tại sao chọn FTT chứ không MLP thường (phải hiểu để trả lời câu hỏi).

**Slide 6 — Kiến trúc tổng quan hệ thống (3 giai đoạn + Hybrid)**
- Sơ đồ: `Traffic → Snort (dấu hiệu) → CICFlowMeter (trích đặc trưng) → FT-Transformer (ML đa lớp) → Cảnh báo`.
- Kèm sơ đồ nhân-quả 3 giai đoạn: NSL-KDD → CIC-IDS-2017 → Testbed (mũi tên = kết quả GĐ trước lộ vấn đề GĐ sau).
- Nói: đây là bức tranh lớn; các slide sau đi sâu từng khối.

**Slide 7 — Giai đoạn 1: Mô hình nền tảng (NSL-KDD)**
- Kiến trúc 2 tầng: **Autoencoder Anomaly Gate** (lọc Benign) + **Stacking Ensemble** (FT-Transformer + LightGBM → Meta-LR).
- Kỹ thuật mất cân bằng: CB-Focal Loss, Boost-Minority Val Set, WeightedRandomSampler.
- Kết quả: **Macro F1 = 0,6809** (đánh giá trung thực train/test tách biệt); R2L Recall thấp = **giới hạn cứng của dataset** (protocol shift telnet→pop3), không phải lỗi mô hình.
- Hình: `fig_nslkdd_ablation.png` hoặc `fig_nslkdd_perclass.png`.
- Nói: GĐ1 là **nền tảng để lấy số liệu & xác nhận ceiling của NSL-KDD** → lý do chuyển sang CIC. KHÔNG khoe đây là "hệ thống triển khai".

**Slide 8 — Giai đoạn 2: Two-Stage Cascade (CIC-IDS-2017)**
- Kiến trúc: **Gating Network** (nhị phân Benign/Suspicious, ngưỡng 0,85, lọc ~82,7% Benign) → **Expert Network** (9 lớp, gộp từ 15 nhãn gốc).
- Nói: giải thích vì sao 2 tầng — tầng 1 gánh phần lớn traffic, tầng 2 chuyên sâu cho phần khó (17,3% suspicious).

**Slide 9 — Giai đoạn 2: Hard Negative Mining cho lớp tấn công hiếm**
- Ý tưởng: thu mẫu bị phân loại sai, retrain với trọng số $w_{hard}=2{,}0$; lặp 2 vòng.
- Kết quả: Botnet F1 **0,4787 → 0,6512 (+36%)**, Infiltration F1 **0,3821 → 0,5903 (+54,5%)** — **vượt** class weight ×10.
- Hình: `fig_hnm_ablation.png`.
- Nói: nhấn "tăng gradient vào biên quyết định" hiệu quả hơn "tăng class weight đều tay".

**Slide 10 — Giai đoạn 2: Asymmetric Ensemble Voting & kết quả**
- Ensemble FTT + Random Forest + KNN; **luật bỏ phiếu bất đối xứng** cho Botnet (Consensus) & Infiltration (Priority).
- Kết quả cuối GĐ2: **Accuracy 99,55% · Macro F1 = 0,9294**; Infiltration F1 0,7407, Botnet F1 0,7344.
- Hình: `fig_ensemble_compare.png`.
- Nói: giải thích vì sao Asymmetric (Macro F1 cao hơn Majority Vote dù Accuracy nhỉnh thấp hơn) — vì tăng đúng 2 lớp hiếm có trọng số bằng nhau trong Macro F1. → **Đạt mục tiêu 1.**

**Slide 11 — Giai đoạn 3: Chẩn đoán Covariate Shift**  *(điểm nhấn nghiên cứu mạnh nhất)*
- Con số sốc: CIC→Testbed WSL2 **Accuracy 99,55% → 21,93%**, **MCC = −0,015** (sai ngược, tệ hơn đoán ngẫu nhiên).
- Phản trực giác: **Re-fit Scaler còn tệ hơn** (21,93% → 6,87%).
- Hình: `fig_da_comparison.png`.
- Nói: đây là phát hiện quan trọng — fine-tuning không đủ, buộc phải **thu dữ liệu thực + retrain hoàn toàn**.

**Slide 12 — Giai đoạn 3: Custom IDS Testbed & mô hình V8.5**
- Thu dữ liệu tấn công **thực** từ Kali Linux trên LAN (WSL2 Mirrored Networking) → dataset **V8.5: 111.825 flows, 5 lớp**.
- 2 điểm trung thực về phương pháp (nên chủ động nêu — hội đồng sẽ hỏi):
  - **PortScan không phân tách trong NAT** → xác nhận <9% F1 qua mọi thuật toán (vấn đề dữ liệu, không phải mô hình) → dùng **dữ liệu surrogate CIC Friday PortScan**.
  - **Val set đa dạng miền** (hydra + CIC Patator) cho con số **tin cậy hơn** (91,7%) so với val đồng nhất miền (97%) — chênh 14% là do **chất lượng đánh giá**.
- Nói: nhấn tính trung thực trong đánh giá — đây là đóng góp 4 (bằng chứng val đồng nhất miền inflate metric ~14%).

**Slide 13 — Giai đoạn 3: Kết quả V8.5 & Hệ thống Hybrid End-to-End**
- Kết quả V8.5: **Macro F1 = 91,7% · Balanced Acc 91,1% · MCC 0,865**; PortScan F1 100%, BruteForce F1 0,86 (Recall 0,90). → **Đạt mục tiêu 2.**
- Hệ thống tích hợp: Snort 3 + CICFlowMeter + FTT V8.5 chạy song song trên **phần cứng phổ thông** (i7 Gen11, 16GB RAM, **không GPU**), WSL2 Ubuntu 22.04.
- Hình: `fig_v85_perclass.png`.
- Nói: chuyển mạch từ "nghiên cứu mô hình" sang "hệ thống chạy được thật".

### PHẦN KẾT QUẢ TÍCH HỢP & KẾT LUẬN (Slide 14–18)

**Slide 14 — Thử nghiệm End-to-End: Tính bổ sung Snort ↔ ML**
- Bảng gọn 5 loại tấn công × {Snort, FTT}: điểm chốt **DoS slowhttptest chỉ ML bắt** (HTTP hợp lệ, Snort mù); **XSS payload ngắn chỉ Snort bắt** (`content:"<script>"`).
- Kết luận: **không tấn công nào bị bỏ sót hoàn toàn bởi cả hai tầng.** → **Đạt mục tiêu 3.**
- Nói: đây là bằng chứng "lai ghép" thực sự có giá trị, không phải gộp cho có.

**Slide 15 — Demo hệ thống (GĐ5 Replay V8.5)**  *(ảnh chụp màn hình dashboard)*
- Ảnh: `Final/05_Replay_Detection/dashboard.html` đang phát hiện realtime (chọn kịch bản "dos").
- ⚠️ **Nói rõ ràng minh bạch:** đây là **replay** — phát lại corpus flow đã thu (CSV) rồi suy luận realtime qua WebSocket, **KHÔNG bắt gói trực tiếp**. Đây đúng là hệ thống End-to-End thật mà báo cáo đo. Đường **live capture** là **hướng phát triển** (đừng trình bày như đã xong).
- Nói: 1 câu định vị "replay ≠ live" để tránh hội đồng hiểu nhầm và hỏi bắt bí.

**Slide 16 — Đối chiếu mục tiêu & Tổng kết đóng góp**
- Bảng: 3 mục tiêu → đều **Đạt** (0,9294 / 0,917 / bổ sung End-to-End xác nhận).
- 4 đóng góp (mỗi cái 1 dòng): (1) Two-Stage Cascade + Asymmetric Voting; (2) HNM 2 vòng cho lớp hiếm; (3) Chẩn đoán covariate shift + Testbed thực + bằng chứng inflate metric; (4) Hybrid IDS End-to-End trên phần cứng phổ thông.

**Slide 17 — Hạn chế & Hướng phát triển**
- Hạn chế (nêu trung thực, ngắn): Testbed chỉ 5/9 lớp (thiếu DDoS, Botnet, Infiltration, Heartbleed do điều kiện thực nghiệm); flow-based khó với Infiltration/Botnet; PortScan dùng surrogate; FTT là hộp đen (thiếu explainability); độ trễ ML ~30s với DoS.
- Hướng phát triển: **Temporal/session-level analysis** (LSTM/Temporal Transformer) cho Botnet/Infiltration & Web Attack; automated feature engineering; Federated Learning multi-site; **và hoàn thiện đường bắt gói trực tiếp (live capture) — hiện đang phát triển**.
- Nói: đây là chỗ hợp lý duy nhất để nhắc `live_detection` — như **định hướng tương lai**, không phải kết quả đã có.

**Slide 18 — Cảm ơn**
- "Trân trọng cảm ơn các thầy/cô đã lắng nghe." + thông tin liên hệ nếu muốn.

---

## 3. Bảng ánh xạ Hình có sẵn → Slide

| File hình (`figures/`) | Dùng ở slide |
|---|---|
| `fig_cic_imbalance.png` | 4 (mất cân bằng lớp) |
| `fig_nslkdd_ablation.png` / `fig_nslkdd_perclass.png` | 7 (GĐ1) |
| `fig_hnm_ablation.png` | 9 (Hard Negative Mining) |
| `fig_ensemble_compare.png` | 10 (Asymmetric Voting) |
| `fig_da_comparison.png` | 11 (covariate shift) |
| `fig_v85_perclass.png` | 13 (kết quả V8.5) |
| `fig_portscan_inseparable.png` | Slide 12 hoặc **Phụ lục** (PortScan không phân tách) |
| Ảnh chụp `dashboard.html` | 15 (demo) |
| Sơ đồ pipeline (vẽ lại từ `Final/README.md`) | 6 (kiến trúc tổng quan) |

> Dùng bản **`.png`** để chèn PowerPoint (bản `.pdf` cùng tên dành cho LaTeX). Nếu cần vẽ lại sơ đồ kiến trúc/nhân-quả 3 giai đoạn, tham khảo `Chuong1_Gioi_thieu.md` (Hình 1.2) và sơ đồ ASCII trong `Final/README.md`.

---

## 4. Ngân sách thời gian (mục tiêu ~13 phút)

| Khối slide | Phút |
|---|---|
| 1–3 Mở đầu (bìa, nội dung, mục tiêu) | ~1,5 |
| 4–5 Bài toán & thách thức, lý do chọn FTT | ~2 |
| 6 Kiến trúc tổng quan | ~1 |
| 7 GĐ1 NSL-KDD | ~1 |
| 8–10 GĐ2 CIC (cascade, HNM, ensemble) | ~3 |
| 11–13 GĐ3 covariate shift + V8.5 + hệ thống | ~3 |
| 14–15 End-to-End + demo | ~1,5 |
| 16–18 kết luận, hạn chế, cảm ơn | ~1 |

Nếu quá giờ: cắt bớt chi tiết ở slide 7 (GĐ1 chỉ là nền tảng) và slide 8, KHÔNG cắt slide 11 (covariate shift) và 14 (bổ sung Hybrid) — đó là 2 điểm mạnh nhất.

---

## 5. Chuẩn bị hỏi–đáp (câu hội đồng dễ hỏi)

- **"Vì sao Macro F1 chứ không Accuracy?"** → Accuracy bị Benign (80%+) chi phối; Macro F1 phạt đều mọi lớp, phản ánh đúng năng lực với lớp tấn công hiếm. (kèm MCC, Balanced Acc cho robustness).
- **"Vì sao FT-Transformer, không phải MLP/RF?"** → Attention học tương tác giữa đặc trưng; tấn công như Infiltration chỉ lộ qua tổ hợp đặc trưng, không qua đặc trưng đơn lẻ.
- **"Dùng surrogate CIC PortScan có phải 'ăn gian'?"** → Không giấu; đã chứng minh PortScan không phân tách trong NAT qua **mọi** thuật toán (<9% F1) → vấn đề dữ liệu môi trường WSL2, không phải mô hình. Đã ghi rõ đây là **hạn chế** (không tổng quát sang WSL2 thực với nmap thường). Ở End-to-End, PortScan được bắt bằng **luật hậu xử lý đếm cổng** (F1 0,996) mà không cần train lại — bổ trợ cho lớp ML.
- **"Đã thu được PortScan/tấn công thật trong WSL2 chưa?"** → Báo cáo này dùng **surrogate cho lớp PortScan của V8.5**. Việc thu dữ liệu tấn công thật đầy đủ hơn (kèm bắt gói trực tiếp) **đang được tiếp tục phát triển** — thuộc hướng phát triển, chưa nằm trong kết quả đã báo cáo. *(Bám đúng quyển; không claim là đã hoàn tất.)*
- **"Vì sao Testbed chỉ 5 lớp?"** → DDoS/Botnet/Infiltration/Heartbleed cần hạ tầng phức tạp (nhiều máy, malware C2, OpenSSL cụ thể) vượt điều kiện thực nghiệm LAN gia đình → nêu như hạn chế + hướng phát triển.
- **"Hệ thống có chạy real-time không?"** → Demo hiện là **replay** (phát lại flow đã thu, suy luận realtime qua WebSocket); đường **bắt gói trực tiếp đang phát triển** — trung thực, đúng phạm vi báo cáo.
- **"Re-fit Scaler vì sao tệ hơn?"** → Thay scaler tạo mâu thuẫn với embedding FTT đã học (giải thích ở Mục 4.5 báo cáo) — hiểu để trả lời, đừng chỉ đọc số.

---

## 6. Phụ lục (nếu vượt 18 slide — đưa xuống đây, không bỏ)

- Bảng per-class đầy đủ CIC-IDS-2017 (9 lớp) & V8.5 (5 lớp).
- Ablation study chi tiết (bảng Two-Stage, HNM vs class weight).
- `fig_portscan_inseparable.png` + bảng chứng minh <9% F1.
- Cấu hình phần cứng/phần mềm (Phụ lục A) & bảng siêu tham số (Phụ lục B).
- Bảng độ trễ phát hiện Snort vs FTT.

---

## 7. Checklist trước khi nộp slide

- [ ] Đúng template HUST 4x3, đúng logo/màu trường.
- [ ] 15–18 slide (không kể phụ lục), phần dư đã chuyển Phụ lục.
- [ ] Không có đoạn văn copy từ báo cáo; mỗi slide ≤ 6 dòng.
- [ ] Mọi hình có nguồn/chú thích; mọi từ viết tắt (NIDS, FTT, HNM, MCC, WSL2, IAT…) hiểu và nói được.
- [ ] Không từ tuyệt đối ("nhất", "triệt để").
- [ ] Slide demo ghi rõ **replay ≠ live**; `live_detection` chỉ xuất hiện ở slide Hướng phát triển.
- [ ] 0 lỗi chính tả.
- [ ] Đã bấm giờ tập nói ≥ 2 lần, ≤ 15 phút.
