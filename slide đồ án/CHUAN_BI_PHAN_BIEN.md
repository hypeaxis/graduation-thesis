# CHUẨN BỊ BẢO VỆ — RIÊNG CHO CÔ PHẢN BIỆN

> File tổng hợp cách trình bày + phao lý thuyết, dựng riêng theo nhận xét của cô phản biện:
> *"Cô dễ, hiểu đề tài mình làm về gì là được. Trình bày ngọn ngành để cô hiểu đồ án là ok. Cô cho trình bày 15 phút rồi hỏi, không cần giải thích code. Nắm kĩ lý thuyết nhé."*
>
> Đi kèm: `GUIDELINE_SLIDE_BAO_VE.md` (khung 18 slide) · `THIET_KE_SLIDE_TUNG_SLIDE.md` (thiết kế từng slide).
> Đề tài: **Phát triển hệ thống phát hiện tấn công mạng bằng phát hiện bất thường** · SV: **Đỗ Tuấn Minh** (MSSV **20225741**) · GVHD: **PGS.TS. Nguyễn Linh Giang**.
> *(Cách tiếp cận kỹ thuật: lai ghép Snort + FT-Transformer — dùng khi mô tả giải pháp trong bài nói.)*

---

## 1. Đọc đúng ý cô → chiến lược

| Cô nói | Nghĩa thật | Bạn phải làm |
|---|---|---|
| "Hiểu đề tài làm về gì là được" | Chấm theo **độ rõ của bức tranh lớn**, không soi tiểu tiết | Ưu tiên **mạch kể**, không sa vào số liệu li ti |
| "Trình bày ngọn ngành để cô hiểu" | Cô là người **ngoài** mảng sâu này | Dùng **ngôn ngữ thường**; mỗi thuật ngữ giải thích 1 câu ngay khi nói ra |
| "Không cần giải thích code" | Đừng mở IDE, đừng nói hàm/thư viện | Nói **"cái gì" + "tại sao"**, tuyệt đối không "làm thế nào trong code" |
| "Nắm kĩ lý thuyết" | **Đây là chỗ cô sẽ hỏi** để kiểm tra bạn thật sự hiểu | Học thuộc **ý** phần 3 dưới (giải thích được mà không nhìn slide) |

**Rủi ro lớn nhất với cô này KHÔNG phải bị bắt lỗi kỹ thuật, mà là trình bày rối khiến cô không nắm được đề tài.**
→ Thắng bằng sự **mạch lạc**, không bằng sự phức tạp. Cô đã báo trước là dễ → đừng phòng thủ quá, hãy tự tin và chủ động.

---

## 2. Trình bày 15 phút — kể như một câu chuyện có nút thắt

Xương sống: **3 thách thức → 3 giai đoạn**. Câu chốt xuyên suốt phải nói ngay từ đầu:

> *"Không một cách tiếp cận đơn lẻ nào đủ, nên em ghép Snort với FT-Transformer, phát triển qua 3 giai đoạn — mỗi giai đoạn giải một thách thức mà giai đoạn trước lộ ra."*

### Dàn thời gian (canh 13 phút, chừa 2 phút đệm)

| Khối | Phút | Nói gì (ý chính) |
|---|---|---|
| **Mở** | 1,5 | Tấn công mạng tăng → bài toán NIDS = cho một *flow* (luồng kết nối), máy phán đoán lành tính / loại tấn công, **thời gian thực**. Nói ngay câu chốt trên. |
| **GĐ1 nền tảng** (NSL-KDD) | 1 | Chỉ định vị là **nền tảng lấy số liệu + xác định giới hạn của dataset** → lý do chuyển sang CIC. Không khoe là hệ thống triển khai. |
| **GĐ2 mất cân bằng** (CIC) | 3 | Vấn đề: Benign:Infiltration tới **65.000:1** → two-stage + hard negative mining → **Macro F1 0,93**. |
| **GĐ3 covariate shift** (Testbed) | 3–4 | Vấn đề: **99,55% rớt còn 21,93%** khi đổi môi trường → thu dữ liệu thật + train lại → **91,7%**. **← ĐIỂM NHẤN MẠNH NHẤT, dành nhiều thời gian nhất.** |
| **GĐ4 hybrid** (End-to-End) | 1,5 | Snort ↔ ML bù nhau: **DoS slowhttptest chỉ ML bắt**, **XSS chỉ Snort bắt** → không tấn công nào lọt cả hai tầng. |
| **Demo** | 1 | Chiếu dashboard; **nói ngay "đây là replay, không phải bắt gói trực tiếp"**. |
| **Kết** | 1,5 | Đối chiếu 3 mục tiêu → đều đạt; nêu hạn chế trung thực (5/9 lớp, PortScan surrogate). |

### Ba nguyên tắc nói cho cô này
1. **Mỗi con số kèm một câu "nghĩa là gì".** Đừng nói "MCC = −0,015" rồi đi tiếp → nói *"âm, tức là mô hình đoán sai còn tệ hơn tung đồng xu"*.
2. **Định vị demo là replay ≠ live** ngay khi chiếu — tránh bị hỏi bắt bí.
3. Nếu lỡ giờ: **cắt GĐ1 trước**, KHÔNG cắt covariate shift và hybrid.

---

## 3. PHAO LÝ THUYẾT — học thuộc *ý*, giải thích được mà không nhìn slide

> Cách dùng: mỗi mục là một câu hỏi cô có thể hỏi + **đoạn trả lời mẫu 2–3 câu bằng lời thường**. Học ý, đừng học vẹt. Mỗi khái niệm đều có trang chi tiết trong `giải thích lý thuyết/_theory_hub/`.

### NHÓM 1 — Bắt buộc thuộc lòng (gần như chắc chắn bị hỏi)

**1.1. "Flow là gì? Hệ thống lấy đầu vào từ đâu?"**
> Một *flow* là một phiên trao đổi dữ liệu giữa hai đầu (cùng cặp IP–cổng, cùng giao thức). Em không phân tích từng gói tin lẻ mà gom cả phiên lại, rồi công cụ **CICFlowMeter** tính ra khoảng 80 con số thống kê mô tả phiên đó: tổng số gói, kích thước gói trung bình, thời gian giữa các gói (IAT), số lần bật các cờ như SYN/ACK… Chính bộ số này là đầu vào cho mô hình.
> *(Đây là gốc của cả hệ thống — không giải thích được flow là mất nền.)*

**1.2. "Vì sao chọn FT-Transformer, không dùng MLP hay Random Forest?"**
> Vì cơ chế **Attention** của Transformer học được **tương tác giữa các đặc trưng**, chứ không nhìn từng đặc trưng rời rạc. Nhiều tấn công chỉ lộ ra khi *kết hợp* nhiều dấu hiệu — ví dụ Infiltration = đích lạ **và** upload cao **và** vào lúc khuya — chứ không đặc trưng đơn lẻ nào đủ. Trước khi vào Transformer, mỗi con số được **Feature Tokenizer** biến thành một vector riêng (mỗi cột có bộ chiếu riêng, nên "5 giây duration" khác hẳn "5 byte"), giữ được *danh tính* của từng đặc trưng — điều mà MLP dùng chung trọng số làm mất đi.
> *(Trang: `feature-tokenizer.html`, `multi-head-self-attention.html`.)*

**1.3. "Vì sao dùng Macro F1 mà không dùng Accuracy?"**
> Vì dữ liệu quá mất cân bằng — Benign chiếm 80–99%. Nếu dùng Accuracy, mô hình cứ đoán "tất cả là Benign" đã được ~90% điểm, nhưng vô dụng vì bỏ sót hết tấn công. **Macro F1 tính điểm đều cho mọi lớp rồi lấy trung bình**, nên lớp tấn công hiếm có trọng số ngang lớp Benign → phản ánh đúng năng lực bắt tấn công. Em còn báo cáo kèm **MCC** và **Balanced Accuracy** để chắc chắn kết quả không bị thổi phồng.

**1.4. "Covariate shift là gì? Vì sao mô hình sụp đổ khi đổi môi trường?"**
> Là hiện tượng **phân phối dữ liệu đầu vào lúc triển khai khác lúc huấn luyện**, dù bản chất "cái gì là tấn công" không đổi. Trong đồ án: CIC được thu trên switch Gigabit, còn Testbed của em chạy trên máy ảo WSL2 qua NAT của Windows — lớp ảo hoá + NAT làm **kích thước gói và thời gian gói (IAT, số cờ) bị lệch đi**. Cùng một cú quét cổng nhưng đi qua "đường ống" khác thì các con số thống kê đo được khác, nên mô hình nhìn vào thấy lạ và đoán sai. Kết quả: Accuracy **99,55% → 21,93%**, MCC **−0,015** (sai có hệ thống, tệ hơn đoán bừa).
> *(Trang: `covariate-shift.html`. Đây là điểm nhấn nghiên cứu mạnh nhất — phải trơn tru.)*

### NHÓM 2 — Nên thuộc (hỏi nếu cô tò mò về cách giải quyết)

**2.1. "Hard Negative Mining là gì?"**
> Em cho mô hình chạy, **gom lại đúng những mẫu nó đoán sai** ("hard negatives"), rồi đưa các mẫu khó đó vào huấn luyện lại với trọng số cao hơn (w = 2,0), lặp 2 vòng. Cách này **tập trung gradient đúng vào biên quyết định** — nơi mô hình đang nhầm — nên hiệu quả hơn là tăng đều trọng số cho cả lớp. Kết quả: Botnet F1 0,48 → 0,65, Infiltration 0,38 → 0,59, vượt cả cách tăng class weight ×10.
> *(Trang: `hard-negative-mining.html`.)*

**2.2. "Two-stage cascade — vì sao lại hai tầng?"**
> Tầng 1 (**Gating**) chỉ làm việc nhẹ: phân biệt Benign / nghi ngờ, lọc bỏ khoảng **82,7% Benign** ngay từ đầu. Tầng 2 (**Expert**) chỉ nhận ~17% traffic khó còn lại để phân loại chi tiết thành 9 lớp. Tách như vậy để **gradient của lớp hiếm không bị khối Benign khổng lồ lấn át** — nếu gộp một tầng, mô hình chỉ lo đoán đúng Benign.
> *(Trang: `two-stage-cascade-gating-expert.html`.)*

**2.3. "Snort là gì? Ghép Snort với ML để làm gì?"**
> **Snort** là hệ phát hiện theo **dấu hiệu (rule)** — có sẵn luật thì bắt rất nhanh và chính xác, nhưng **mù với cái chưa có luật / tấn công zero-day**. **ML** thì học theo thống kê, bắt được cái "trông lạ" nhưng dễ bỏ sót tấn công *trông giống lưu lượng bình thường*. Hai cái bù nhau: trong thử nghiệm, **DoS slowhttptest** trông như HTTP hợp lệ nên **chỉ ML bắt được**, còn **XSS payload ngắn** thì **chỉ Snort bắt** nhờ luật khớp chuỗi `<script>`. Ghép lại → không tấn công nào lọt qua cả hai tầng.
> *(Trang: `snort-hybrid-ids.html`, `alert-aggregator.html`.)*

### NHÓM 3 — Biết đủ để không đứng hình (chỉ cần 1 câu)

**3.1. "Focal Loss là gì?"** → Một hàm mất mát **phạt nặng những mẫu mô hình còn đoán sai/khó**, giảm trọng số mẫu dễ, để mô hình dồn sức học lớp hiếm thay vì lớp Benign đã quá dễ. *(Trang: `focal-loss.html`, `class-balanced-focal-loss.html`.)*

**3.2. "Vì sao re-fit lại scaler còn tệ hơn (21,93% → 6,87%)?"** → Vì scaler và phần embedding của mô hình **học cùng nhau, khớp tay nhau**. Embedding kỳ vọng đầu vào theo "thước đo" của scaler cũ; nếu chỉ thay scaler mà không cập nhật mô hình thì như **đổi đơn vị bản đồ từ km sang dặm nhưng người đọc vẫn hiểu là km** → càng chỉnh càng loạn. Lời giải đúng là đổi scaler **đồng thời** với fine-tune tầng cao. *(Trang: `scaler-embedding-coupling.html`.)*

**3.3. "PortScan surrogate — có phải 'ăn gian' không?"** → Không giấu: trong môi trường NAT của WSL2, PortScan **không phân tách được qua mọi thuật toán** (<9% F1) — đây là **vấn đề của dữ liệu môi trường, không phải mô hình**. Nên với lớp PortScan em dùng **dữ liệu thay thế (surrogate) từ CIC**, và ghi rõ đây là hạn chế. Ở hệ thống End-to-End, PortScan được bắt bằng **luật hậu xử lý đếm cổng** (F1 ~0,996) mà không cần train lại. *(Trang: `portscan-inseparability-nat.html`.)*

---

## 4. Bộ số phải nhớ chính xác (khớp báo cáo)

| Ngữ cảnh | Con số |
|---|---|
| Mất cân bằng CIC | Benign:Infiltration **65.000:1** |
| Kết quả GĐ2 (CIC) | Accuracy **99,55%** · Macro F1 **0,9294** |
| HNM | Botnet **0,48 → 0,65** · Infiltration **0,38 → 0,59** |
| Covariate shift | **99,55% → 21,93%** · MCC **−0,015** · re-fit scaler **6,87%** |
| Dataset thật V8.5 | **111.825 flows · 5 lớp** |
| Kết quả V8.5 (Testbed) | Macro F1 **91,7%** · Balanced Acc **91,1%** · MCC **0,865** |
| Đánh giá trung thực | Val đồng nhất miền ~97% vs val đa dạng miền **91,7%** (chênh do chất lượng đánh giá) |
| GĐ1 (NSL-KDD) | Macro F1 **0,6809** (giới hạn cứng của dataset) |
| Phần cứng | i7 Gen11 · 16GB RAM · **không GPU** · WSL2 Ubuntu 22.04 |

**3 mục tiêu (khép vòng ở slide kết):** (1) Macro F1 > 0,9 trên CIC → **0,9294 ✔** · (2) Macro F1 > 0,9 trên Testbed → **0,917 ✔** · (3) Snort + ML bổ sung End-to-End → **xác nhận ✔**.

---

## 5. Chuẩn bị hỏi–đáp — câu cô phản biện dễ hỏi

> Cô dạng này hỏi để **kiểm tra bạn có hiểu cái mình viết**, không hỏi để bắt bí. Bình tĩnh, trả lời bằng bản chất.

**⭐ CÂU QUAN TRỌNG NHẤT (vì tên đề tài nhấn "phát hiện bất thường"):**
**"Đề tài tên là *phát hiện bất thường* — mô hình của em có phải anomaly detection (học không giám sát) không?"**
> "Dạ, *phát hiện bất thường* là **nguyên lý thiết kế xuyên suốt** hệ thống, ở hai mức:
> **(1) Kiến trúc hai tầng** — tầng 1 chỉ trả lời *"flow này có lệch khỏi bình thường (Benign) không?"*, tầng 2 mới phân loại cụ thể là tấn công gì. Ở giai đoạn nền tảng (NSL-KDD), tầng 1 này là một **Autoencoder** đúng nghĩa phát hiện bất thường: em chỉ dạy nó *tái tạo lại lưu lượng bình thường*; flow nào tái tạo méo (lỗi vượt ngưỡng τ) thì coi là bất thường — **không cần nhãn tấn công**. Ở hệ thống cuối (CIC / V8.5), tầng lọc này là bộ phân loại nhị phân Benign/nghi ngờ (Gating, ngưỡng 0,85) làm đúng vai trò tách *bình thường* khỏi *bất thường*.
> **(2) Bản chất phát hiện của ML** — khác Snort dò theo *dấu hiệu cố định*, FT-Transformer phát hiện tấn công dựa trên **sự bất thường thống kê trong đặc trưng flow** (ví dụ DoS slow: duration/IAT bất thường) → bắt được cả tấn công *chưa có luật*."
>
> ⚠️ **Ranh giới trung thực (để không bị hỏi vặn):** bộ phân loại cuối cùng (V8.5) là **học có giám sát đa lớp**, KHÔNG phải anomaly detection thuần không giám sát; Autoencoder không giám sát nằm ở **GĐ1 nền tảng**. Nếu cô hỏi *"model cuối có phải unsupervised anomaly detection không?"* → trả lời thẳng: *"Phần phân loại là có giám sát; 'phát hiện bất thường' là **triết lý phát hiện** — tách bình thường/bất thường rồi định danh — và được hiện thực hoá đúng nghĩa bằng Autoencoder ở giai đoạn nền tảng."* **Đừng claim cả hệ thống là không giám sát.**
> *(Trang lý thuyết: `autoencoder-gate-threshold.html`, `two-stage-cascade-gating-expert.html`.)*

1. **"Em giải thích lại flow / FT-Transformer / covariate shift cho cô nghe."** → Xem Nhóm 1. Đây là dạng hỏi số 1 của cô.
2. **"Vì sao Macro F1 chứ không Accuracy?"** → Mục 1.3.
3. **"Hệ thống có chạy real-time thật không?"** → Demo là **replay** (phát lại flow đã thu, suy luận realtime qua WebSocket); đường **bắt gói trực tiếp đang phát triển** — trung thực, đúng phạm vi báo cáo.
4. **"Vì sao Testbed chỉ có 5/9 lớp?"** → DDoS/Botnet/Infiltration/Heartbleed cần hạ tầng phức tạp (nhiều máy, malware C2, OpenSSL cụ thể) vượt điều kiện thực nghiệm LAN gia đình → nêu như **hạn chế + hướng phát triển**.
5. **"Đóng góp mới của em là gì?"** → 4 đóng góp: (1) Two-Stage Cascade + Asymmetric Voting; (2) HNM 2 vòng cho lớp hiếm; (3) **chẩn đoán covariate shift + Testbed thật + bằng chứng val đồng nhất miền thổi phồng metric**; (4) Hybrid IDS End-to-End trên **phần cứng phổ thông**.
6. **"Hạn chế của đề tài?"** → Chủ động nêu trước khi cô hỏi: 5/9 lớp; PortScan dùng surrogate; flow-based khó với Botnet/Infiltration; FTT là hộp đen (thiếu explainability); độ trễ ML ~30s với DoS.

### Câu thoát hiểm khi chưa chắc
> *"Dạ để em giải thích theo cách em hiểu…"* rồi nói **bản chất**. Cô cần thấy bạn *hiểu*, không cần bạn đọc thuộc định nghĩa sách. Không bịa số — nếu không nhớ con số chính xác, nói khoảng ("khoảng chín mươi mấy phần trăm") thay vì đoán bừa.

---

## 6. Checklist trước ngày bảo vệ

- [ ] Đọc lại phần 3 (phao lý thuyết) Nhóm 1 & 2 tới mức **nói được mà không nhìn**.
- [ ] Thuộc bộ số ở phần 4.
- [ ] Bấm giờ tập nói **≥ 2 lần**, canh **≤ 13 phút**.
- [ ] Chuẩn bị sẵn câu định vị **"replay ≠ live"** cho slide demo.
- [ ] Mở sẵn `giải thích lý thuyết/_theory_hub/index.html` để ôn nhanh các infographic.
- [ ] Kiểm tra chính tả slide 1 (tên đề tài, tên GVHD) — chỗ hay bị soi nhất.
