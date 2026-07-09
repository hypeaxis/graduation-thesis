# KỊCH BẢN THUYẾT TRÌNH BẢO VỆ
## Đề tài: Phát triển hệ thống phát hiện tấn công mạng bằng phát hiện bất thường
> Cách tiếp cận: lai ghép Snort + FT-Transformer · SV: Đỗ Tuấn Minh (20225741) · GVHD: PGS.TS. Nguyễn Linh Giang

> Đây là **lời nói** (speaker script) cho từng slide, đi kèm `THIET_KE_SLIDE_TUNG_SLIDE.md` (thiết kế slide). Bám `GUIDELINE_SLIDE_BAO_VE.md`.
>
> **Mục tiêu thời lượng: ~13 phút** (khung an toàn trong 12–15 phút). Lời trong ngoặc *(…)* là chỉ dẫn diễn đạt, KHÔNG đọc. Chữ **in đậm** = chỗ nhấn giọng.
>
> **3 nguyên tắc khi nói:** (1) nói theo mạch *vấn đề → giải pháp → kết quả*, KHÔNG đọc slide; (2) tránh từ tuyệt đối — nói "một trong những", "đạt mức cạnh tranh"; (3) mỗi giai đoạn giải đúng **một** thách thức — lặp lại mạch này để hội đồng nhớ.

---

## Thông điệp cốt lõi (thuộc lòng — xương sống cả bài)

> "Không một hướng tiếp cận đơn lẻ nào đủ. Em xây hệ thống **lai ghép Snort + FT-Transformer** qua **3 giai đoạn nghiên cứu tuần tự**, trong đó **kết quả giai đoạn trước lộ ra vấn đề của giai đoạn sau**: NSL-KDD làm nền tảng → CIC-IDS-2017 đạt Macro F1 0,93 → Testbed thực giải quyết covariate shift, đạt Macro F1 0,92."

Ba thách thức = ba giai đoạn: ⚖️ mất cân bằng → GĐ2 · 🔀 covariate shift → GĐ3 · 🧩 giới hạn một tầng → Hybrid.

> **Khung đề tài (nhớ gắn khi nói):** tên đồ án nhấn *phát hiện bất thường* — đó là **triết lý phát hiện** (tách bình thường/bất thường → định danh), được hiện thực bằng **kiến trúc hai tầng** (Anomaly Gate → phân loại) cộng lai ghép Snort. Bắt buộc nói cụm "phát hiện bất thường" ở **Slide 3** và **Slide 7** để lời nói khớp tên đề tài. **Không** claim cả hệ thống là học không giám sát (bộ phân loại cuối là có giám sát — xem Q&A).

---

## Ngân sách thời gian

| Khối slide | Phút | Cộng dồn |
|---|---|---|
| 1–3 Mở đầu | ~1,5 | 1,5 |
| 4–5 Thách thức + lý do FTT | ~2,0 | 3,5 |
| 6 Kiến trúc tổng quan | ~1,0 | 4,5 |
| 7 GĐ1 NSL-KDD | ~1,0 | 5,5 |
| 8–10 GĐ2 CIC | ~3,0 | 8,5 |
| 11–13 GĐ3 + V8.5 + hệ thống | ~3,0 | 11,5 |
| 14–15 End-to-End + demo | ~1,5 | 13,0 |
| 16–18 Kết luận | ~1,0 | ~14 |

**Nếu quá giờ:** rút gọn Slide 7 (GĐ1) và Slide 8. **TUYỆT ĐỐI không cắt** Slide 11 (covariate shift) và Slide 14 (bổ sung Hybrid).

---

# LỜI NÓI TỪNG SLIDE

## Slide 1 — Trang bìa · ~15 giây

> "Kính chào Hội đồng. Em là **Đỗ Tuấn Minh**, MSSV **20225741**. Em xin trình bày đồ án tốt nghiệp: **Phát triển hệ thống phát hiện tấn công mạng bằng phát hiện bất thường**, dưới sự hướng dẫn của **PGS.TS. Nguyễn Linh Giang**."

*(Không đọc lại toàn bộ bìa. Đứng thẳng, nhìn hội đồng, chuyển slide.)*

---

## Slide 2 — Nội dung trình bày · ~20 giây

> "Bài trình bày gồm 5 phần: **mục tiêu và bài toán**, **ba thách thức cốt lõi**, **phương pháp qua ba giai đoạn nghiên cứu**, **kết quả thực nghiệm**, và **kết luận**. Em xin đi thẳng vào bài toán."

*(Nói nhanh, đây chỉ là bản đồ đường đi.)*

---

## Slide 3 — Đặt vấn đề & Mục tiêu · ~50 giây

> "Tấn công mạng ngày càng gây thiệt hại lớn. Theo báo cáo IBM 2023, mỗi vụ vi phạm dữ liệu tốn trung bình **4,45 triệu đô-la** và mất trung bình **204 ngày** để phát hiện.
>
> Bài toán phát hiện xâm nhập mạng, gọi tắt là NIDS, là phân loại mỗi **flow** — tức một phiên kết nối mạng — thành lưu lượng bình thường hoặc một loại tấn công, **trong thời gian thực**.
>
> Cách tiếp cận của đồ án là **phát hiện bất thường**: trước hết **tách lưu lượng bình thường khỏi lưu lượng bất thường** — cái lệch khỏi hành vi bình thường — rồi mới **định danh** nó là loại tấn công nào. Nguyên lý này chạy xuyên suốt **kiến trúc hai tầng** của cả ba giai đoạn.
>
> Đồ án đặt ra **ba mục tiêu**: một, Macro F1 vượt 0,9 trên bộ chuẩn CIC-IDS-2017; hai, Macro F1 vượt 0,9 trên **Testbed thực** do em tự thu dữ liệu; ba, chứng minh Snort và học máy **phát hiện bổ sung cho nhau** trong hệ thống End-to-End."

*(Ba mục tiêu này sẽ được đối chiếu "Đạt" ở cuối bài — nhấn để hội đồng ghi nhớ.)*

---

## Slide 4 — Ba thách thức cốt lõi · ~70 giây *(bản lề)*

> "Triển khai NIDS học máy thực tế vấp phải **ba thách thức**.
>
> **Thứ nhất — mất cân bằng lớp cực đoan.** Lưu lượng bình thường chiếm 83 đến 99%, trong khi tấn công nguy hiểm như Infiltration dưới 0,01%. Tỉ lệ có thể tới **65.000 trên 1**. Mô hình thông thường bị lớp Benign lấn át, không học được lớp tấn công hiếm.
>
> **Thứ hai — covariate shift.** Mô hình huấn luyện trên dữ liệu lab, khi mang sang môi trường mạng khác thì phân phối đặc trưng đổi hoàn toàn. Trong thực nghiệm của em, mô hình đạt 99,55% trên CIC nhưng rơi xuống **21,93%** khi chuyển sang Testbed WSL2.
>
> **Thứ ba — giới hạn của một tầng đơn lẻ.** Snort bỏ sót tấn công chưa có dấu hiệu; còn học máy bỏ sót tấn công mà thống kê flow trông giống lưu lượng bình thường.
>
> Điểm mấu chốt của đồ án: **mỗi thách thức được giải quyết bởi đúng một giai đoạn nghiên cứu.**"

*(Đây là slide quan trọng nhất về cấu trúc. Nói chậm, rõ ba con số: 65.000:1 · 21,93% · và ý "giới hạn một tầng".)*

---

## Slide 5 — Lý do chọn FT-Transformer · ~50 giây

> "Vì sao không dùng một hướng có sẵn? IDS theo dấu hiệu như Snort thì nhanh nhưng **bỏ sót zero-day**. Học máy thống kê như Random Forest thì **kém với lớp dưới 0,01%**.
>
> Em chọn **FT-Transformer** vì cơ chế **Attention học được tương tác giữa các đặc trưng**, thay vì xử lý từng đặc trưng độc lập như MLP. Điều này quan trọng với NIDS: một tấn công như Infiltration **không lộ ra ở một đặc trưng đơn lẻ**, mà chỉ bộc lộ qua **tổ hợp** — ví dụ điểm đến bất thường, cộng với upload dữ liệu cao, cộng với thời điểm khuya đêm. Vì vậy FT-Transformer phù hợp với dữ liệu dạng bảng hơn MLP hay Random Forest."

*(Nếu hội đồng hỏi "vì sao không MLP" — câu này chính là câu trả lời. Phải hiểu chắc "Attention học tương tác đặc trưng".)*

---

## Slide 6 — Kiến trúc tổng quan · ~60 giây

> "Đây là bức tranh tổng thể. Về **pipeline xử lý**: lưu lượng đi qua **Snort** để khớp dấu hiệu, song song được **CICFlowMeter** trích đặc trưng flow, rồi đưa vào **FT-Transformer** phân loại đa lớp; cuối cùng **Alert Aggregator** hợp nhất cảnh báo hai nguồn.
>
> Về **mạch nghiên cứu**, hệ thống được xây qua **ba giai đoạn nối tiếp**: NSL-KDD làm nền tảng, sang CIC-IDS-2017 đạt Macro F1 0,93, rồi sang Testbed thực đạt 0,92. Điểm đặc biệt là các mũi tên này mang tính **nhân-quả**: **kết quả của giai đoạn trước chính là lý do phát sinh vấn đề của giai đoạn sau**. Các slide tiếp theo em sẽ đi sâu từng khối."

*(Chỉ tay theo mũi tên khi nói "nhân-quả". Đây là chỗ khung hoá cả phần thân.)*

---

## Slide 7 — Giai đoạn 1: NSL-KDD · ~60 giây

> "**Giai đoạn 1** thiết lập kiến trúc nền tảng trên NSL-KDD. Kiến trúc gồm **hai tầng**: một **Autoencoder Anomaly Gate** — đây chính là thành phần **phát hiện bất thường đúng nghĩa** mà tên đề tài nói tới: nó học tái tạo lưu lượng bình thường, cái gì tái tạo méo, lệch khỏi bình thường thì bị coi là bất thường, **không cần nhãn tấn công**; sau đó một **Stacking Ensemble** kết hợp FT-Transformer với LightGBM qua một Meta Logistic Regression để phân loại tấn công.
>
> Để xử lý mất cân bằng, em dùng CB-Focal Loss, Boost-Minority Validation, và Weighted Random Sampler.
>
> Kết quả **Macro F1 bằng 0,6809**, với đánh giá train/test tách biệt nghiêm ngặt. Lớp R2L có Recall thấp, nhưng đây là **giới hạn cứng của bộ dữ liệu** — do dịch chuyển giao thức telnet sang pop3 giữa train và test — chứ không phải lỗi mô hình. **Chính giới hạn này là lý do em chuyển sang CIC-IDS-2017.**"

*(Định vị GĐ1 là nền tảng, KHÔNG khoe là hệ thống triển khai. Nếu quá giờ, rút còn 2 câu: kiến trúc + con số + "ceiling của dataset → chuyển CIC".)*

---

## Slide 8 — Giai đoạn 2: Two-Stage Cascade · ~60 giây

> "**Giai đoạn 2** trên CIC-IDS-2017, với 9 lớp gộp từ 15 nhãn gốc. Vấn đề: nếu phân loại 9 lớp trực tiếp thì gradient bị 83% Benign chi phối — baseline chỉ đạt Macro F1 0,78.
>
> Em tái thiết kế thành **Two-Stage Cascade**. Tầng một là **Gating Network** — chỉ trả lời câu hỏi nhị phân 'có đáng ngờ không?' — với ngưỡng **0,85**, lọc khoảng **82,7% Benign** ra khỏi pipeline. Tầng hai là **Expert Network** phân loại 9 lớp, nhưng chỉ phải xử lý **17,3% lưu lượng đáng ngờ** còn lại.
>
> Ngưỡng 0,85 là **bảo thủ có chủ đích**: em ưu tiên không bỏ sót tấn công hơn là giảm khối lượng xử lý. Riêng việc tách hai tầng đã nâng Macro F1 từ 0,78 lên **0,88**."

*(Nếu hội đồng hỏi vì sao 0,85 mà không 0,5: bỏ sót một Infiltration ở tầng 1 là mất vĩnh viễn, nên chấp nhận đẩy nhiều flow xuống tầng 2.)*

---

## Slide 9 — Giai đoạn 2: Hard Negative Mining · ~55 giây

> "Với hai lớp hiếm nhất — Botnet và Infiltration — em dùng **Hard Negative Mining**. Ý tưởng: sau mỗi vòng huấn luyện, thu lại đúng những mẫu **bị phân loại sai**, đưa trở lại tập train với trọng số gấp đôi, rồi huấn luyện lại — lặp **hai vòng**.
>
> Kết quả: Botnet F1 tăng từ 0,4787 lên **0,6512**, tức **cộng 36%**; Infiltration F1 tăng từ 0,3821 lên **0,5903**, tức **cộng 54,5%**.
>
> Quan trọng hơn, cách này **vượt** việc chỉ tăng class weight ×10. Lý do: tăng class weight tác động đều lên cả mẫu đã đúng, còn Hard Negative Mining **tập trung gradient vào đúng vùng biên quyết định** — nơi mô hình đang nhầm."

*(Thông điệp 1 câu để nhớ: "tăng gradient vào biên quyết định hiệu quả hơn tăng class weight đều tay".)*

---

## Slide 10 — Giai đoạn 2: Asymmetric Voting & kết quả · ~65 giây

> "Bước cuối Giai đoạn 2 là **Asymmetric Ensemble Voting**, kết hợp FT-Transformer, Random Forest và KNN — ba mô hình **sai trên những mẫu khác nhau** nên bổ sung được cho nhau.
>
> Em thiết kế **hai luật bất đối xứng** theo chi phí sai khác nhau của từng lớp. Với **Infiltration** — luật *ưu tiên*: chỉ cần Random Forest **hoặc** KNN bỏ phiếu là nhận, vì bỏ sót Infiltration nguy hiểm hơn nhiều so với báo nhầm. Với **Botnet** — luật *đồng thuận*: phải **cả ba** mô hình cùng đồng ý mới nhận, vì FT-Transformer hay nhầm Benign nhàn rỗi thành Botnet, gây báo động giả.
>
> Kết quả cuối Giai đoạn 2: **Accuracy 99,55% và Macro F1 bằng 0,9294** — **đạt mục tiêu thứ nhất**.
>
> Một điểm em muốn giải thích: Asymmetric Voting có Accuracy **thấp hơn chút** so với Majority Vote, nhưng Macro F1 **cao hơn** — vì nó nâng đúng hai lớp hiếm, mà trong Macro F1 mọi lớp có trọng số bằng nhau bất kể số mẫu."

*(Đây là chỗ thể hiện hiểu sâu về metric. Nhấn "0,9294 → đạt mục tiêu 1".)*

---

## Slide 11 — Giai đoạn 3: Chẩn đoán Covariate Shift · ~70 giây *(điểm nhấn mạnh nhất)*

> "**Giai đoạn 3** là phần em tâm đắc nhất. Khi mang mô hình CIC — đang đạt 99,55% — sang Testbed WSL2 thật, Accuracy **rơi xuống 21,93%**. Đáng chú ý hơn, hệ số MCC bằng **âm 0,015** — nghĩa là mô hình **phân loại sai ngược có hệ thống**, tệ hơn cả đoán ngẫu nhiên.
>
> Điều phản trực giác là: khi em thử **fit lại bộ chuẩn hoá** trên dữ liệu mới, kết quả còn **tệ hơn — xuống 6,87%**. Lý do: embedding của FT-Transformer đã gắn với khoảng giá trị của scaler cũ; thay scaler tạo mâu thuẫn nội bộ.
>
> Nguyên nhân gốc là chuyển từ switch vật lý Gigabit sang card mạng ảo Hyper-V với NAT — làm đổi kích thước gói và thời điểm gói, ảnh hưởng trực tiếp đến đặc trưng IAT và đếm cờ.
>
> Kết luận chẩn đoán: **fine-tuning không đủ**. Buộc phải **thu dữ liệu tấn công thực và huấn luyện lại hoàn toàn**."

*(Slide mạnh nhất — nói chậm, để con số 21,93% và −0,015 "ngấm". Không cắt slide này dù thiếu giờ.)*

---

## Slide 12 — Giai đoạn 3: Testbed & tính trung thực · ~65 giây

> "Em xây một **Custom IDS Testbed**: dùng Kali Linux tấn công thật một máy victim trên mạng LAN, qua cơ chế WSL2 Mirrored Networking. Từ đó thu được dataset **V8.5 gồm 111.825 flows, 5 lớp**.
>
> Em xin chủ động nêu **hai điểm trung thực về phương pháp**.
>
> **Một**, lớp **PortScan không phân tách được trong môi trường NAT**: F1 dưới 9% qua **mọi** thuật toán em thử — đây là vấn đề của dữ liệu, không phải mô hình. Em giải quyết bằng **dữ liệu surrogate** là PortScan từ CIC Friday, thu trên phần cứng thật.
>
> **Hai**, khi đánh giá BruteForce, tập kiểm định **đồng nhất miền** cho con số cao khoảng 97%, nhưng tập **đa dạng miền** — trộn công cụ hydra với Patator — chỉ cho **91,7%**; riêng BruteForce chênh **14%**. Chênh lệch này phản ánh **chất lượng đánh giá**, và con số 91,7% **đáng tin cậy hơn**."

*(Chủ động nêu điểm yếu = ghi điểm phương pháp luận. Đây là đóng góp 4: bằng chứng val đồng nhất miền inflate metric ~14%.)*

---

## Slide 13 — Giai đoạn 3: Kết quả V8.5 & Hệ thống · ~55 giây

> "Mô hình cuối **V8.5 đạt Macro F1 91,7%, Balanced Accuracy 91,1%, MCC 0,865** trên tập đa dạng miền — **đạt mục tiêu thứ hai**. Trong đó PortScan F1 100% nhờ surrogate, DoS 0,93, BruteForce 0,86 với Recall 0,90.
>
> Về hệ thống, em tích hợp **Snort 3, CICFlowMeter và FT-Transformer V8.5** chạy song song. Đáng chú ý là toàn bộ chạy trên **phần cứng phổ thông** — Intel i7 thế hệ 11, 16GB RAM, **không cần GPU** — trên WSL2 Ubuntu 22.04. Điều này cho thấy hệ thống **khả thi để triển khai thực tế**."

*(Chuyển mạch từ "nghiên cứu mô hình" sang "hệ thống chạy được thật". Nhấn "không GPU".)*

---

## Slide 14 — End-to-End: Tính bổ sung Snort ↔ ML · ~60 giây

> "Thử nghiệm End-to-End trên 5 loại tấn công cho thấy **tính bổ sung** giữa hai tầng.
>
> Hai trường hợp là linh hồn của kiến trúc lai ghép. **DoS slowhttptest** — mỗi HTTP request đều hoàn toàn hợp lệ nên **Snort mù hoàn toàn**, nhưng học máy thấy được thời lượng flow bất thường nên bắt được. Ngược lại, **XSS payload ngắn** — không có pattern flow đặc trưng nên **học máy bỏ sót**, nhưng Snort với luật khớp chuỗi `<script>` bắt được ngay ở tầng ứng dụng.
>
> Kết luận: **không tấn công nào bị bỏ sót hoàn toàn bởi cả hai tầng cùng lúc.** Đây chính là giá trị thật của lai ghép, chứ không phải gộp cho có — **đạt mục tiêu thứ ba**."

*(Đây là điểm mạnh thứ hai của bài — không cắt. Nhấn cặp đối lập DoS↔XSS.)*

---

## Slide 15 — Demo hệ thống (Replay V8.5) · ~40 giây

> "Đây là hệ thống đang hoạt động, phát hiện realtime với kịch bản DoS. Em xin nói rõ để tránh hiểu nhầm: đây là chế độ **replay** — tức phát lại corpus flow đã thu sẵn dưới dạng CSV, rồi suy luận realtime qua WebSocket. **Đây đúng là hệ thống End-to-End mà báo cáo đo lường.**
>
> Phần **bắt gói trực tiếp** — live capture — hiện **đang được phát triển** và nằm trong hướng phát triển, chưa nằm trong kết quả đã báo cáo."

*(BẮT BUỘC nói câu "replay ≠ live" để hội đồng không hỏi bắt bí. Nói minh bạch, tự tin.)*

---

## Slide 16 — Đối chiếu mục tiêu & Đóng góp · ~45 giây

> "Đối chiếu lại **ba mục tiêu ban đầu**: Macro F1 trên CIC đạt **0,9294**; trên Testbed thực đạt **0,917**; và tính bổ sung Snort–học máy đã được **xác nhận** trong End-to-End. Cả ba đều đạt.
>
> Đồ án có **bốn đóng góp**: một, kiến trúc Two-Stage Cascade với Asymmetric Voting; hai, Hard Negative Mining hai vòng cho lớp hiếm; ba, chẩn đoán covariate shift cùng Testbed thực và bằng chứng metric bị thổi phồng bởi đánh giá đồng nhất miền; bốn, hệ thống Hybrid IDS End-to-End trên phần cứng phổ thông."

*(Slide "khép vòng" với Slide 3. Nói dứt khoát, tự tin nhưng không dùng từ tuyệt đối.)*

---

## Slide 17 — Hạn chế & Hướng phát triển · ~40 giây

> "Về **hạn chế**, em nêu trung thực: Testbed chỉ thu được 5 trên 9 lớp do điều kiện thực nghiệm; phương pháp flow-based khó với Infiltration và Botnet; PortScan phải dùng surrogate; FT-Transformer là mô hình hộp đen thiếu khả năng giải thích; và độ trễ học máy với DoS còn khoảng 30 giây.
>
> **Hướng phát triển** xuất phát trực tiếp từ các hạn chế đó: phân tích **theo phiên** bằng LSTM hoặc Temporal Transformer cho Botnet, Infiltration và Web Attack; tự động hoá kỹ thuật đặc trưng; Federated Learning nhiều site; và **hoàn thiện đường bắt gói trực tiếp** — phần hiện đang phát triển."

*(Đây là chỗ hợp lý duy nhất nhắc live_detection — như tương lai, KHÔNG phải kết quả.)*

---

## Slide 18 — Cảm ơn · ~10 giây

> "Trên đây là toàn bộ nội dung đồ án. Em xin **trân trọng cảm ơn Hội đồng đã lắng nghe** và rất mong nhận được góp ý của các thầy cô."

*(Dừng, mỉm cười, sẵn sàng Q&A.)*

---

# CHUẨN BỊ HỎI–ĐÁP (câu hội đồng hay hỏi)

**⭐ "Đề tài tên là *phát hiện bất thường* — mô hình của em có phải anomaly detection (học không giám sát) không?"**  *(câu khả năng cao nhất vì tên đề tài)*
> "Phát hiện bất thường" là **nguyên lý thiết kế xuyên suốt**, ở hai mức: (1) **kiến trúc hai tầng** — tầng 1 tách *bình thường/bất thường*, tầng 2 định danh loại tấn công; ở GĐ1 tầng 1 là **Autoencoder** đúng nghĩa (học tái tạo Benign, lỗi vượt ngưỡng = bất thường, không cần nhãn tấn công), ở V8.5 tầng lọc là Gating nhị phân Benign/nghi ngờ (ngưỡng 0,85). (2) **Bản chất ML**: khác Snort dò dấu hiệu cố định, FT-Transformer phát hiện bằng **bất thường thống kê trong đặc trưng flow** nên bắt được cả tấn công chưa có luật.
> **Ranh giới trung thực:** bộ phân loại cuối (V8.5) là **học có giám sát đa lớp**, không phải anomaly detection thuần không giám sát; Autoencoder không giám sát nằm ở GĐ1 nền tảng. Nếu bị hỏi vặn "model cuối có phải unsupervised không?" → trả thẳng: *phần phân loại là có giám sát; "phát hiện bất thường" là triết lý phát hiện, hiện thực đúng nghĩa bằng Autoencoder ở giai đoạn nền tảng.* **Đừng claim cả hệ thống là không giám sát.**

**"Vì sao dùng Macro F1 chứ không Accuracy?"**
> Accuracy bị lớp Benign trên 80% chi phối — mô hình đoán tất cả là Benign vẫn được ~83%. Macro F1 phạt đều mọi lớp, phản ánh đúng năng lực với lớp tấn công hiếm. Em bổ sung MCC và Balanced Accuracy để đánh giá robustness.

**"Vì sao FT-Transformer, không phải MLP hay Random Forest?"**
> Attention học tương tác **giữa** các đặc trưng. Tấn công như Infiltration chỉ lộ qua tổ hợp đặc trưng chứ không qua đặc trưng đơn lẻ — MLP xử lý đặc trưng gần như độc lập, Random Forest phân nhánh theo ngưỡng từng đặc trưng, đều kém với loại tương tác này.

**"Dùng surrogate CIC PortScan có phải 'ăn gian' không?"**
> Không giấu, em ghi rõ trong báo cáo là hạn chế. Em đã chứng minh PortScan **không phân tách được trong NAT** qua mọi thuật toán — F1 dưới 9% — nên đây là vấn đề dữ liệu môi trường WSL2, không phải mô hình. Ở End-to-End, PortScan còn được bắt bằng **luật hậu xử lý đếm cổng** với F1 0,996 mà không cần train lại.

**"Đã thu được PortScan/tấn công thật đầy đủ trong WSL2 chưa?"**
> Báo cáo này dùng surrogate cho lớp PortScan của V8.5. Việc thu dữ liệu tấn công thật đầy đủ hơn, kèm bắt gói trực tiếp, **đang được tiếp tục phát triển** — thuộc hướng phát triển, chưa nằm trong kết quả đã báo cáo.

**"Vì sao Testbed chỉ 5 lớp?"**
> DDoS, Botnet, Infiltration, Heartbleed cần hạ tầng phức tạp — nhiều máy phối hợp, malware C2, phiên bản OpenSSL cụ thể — vượt điều kiện thực nghiệm LAN gia đình. Em nêu đây là hạn chế và hướng phát triển.

**"Hệ thống có chạy real-time không? Demo là thật hay giả lập?"**
> Demo hiện là **replay**: phát lại flow đã thu, suy luận realtime qua WebSocket — đúng là hệ thống End-to-End mà báo cáo đo. Đường bắt gói trực tiếp đang phát triển. Em nói rõ để đúng phạm vi báo cáo.

**"Re-fit Scaler vì sao lại tệ hơn?"**
> Mô hình đã học embedding gắn với khoảng giá trị của scaler cũ trên CIC. Thay scaler mới tạo mâu thuẫn giữa dữ liệu đầu vào và embedding đã học — nên Accuracy tụt từ 21,93% xuống 6,87%. Chi tiết ở Mục 4.5 báo cáo.

**"MCC âm nghĩa là gì?"**
> MCC nằm trong [−1, 1]; bằng 0 là đoán ngẫu nhiên. MCC âm 0,015 nghĩa là mô hình phân loại **sai ngược có hệ thống** — tệ hơn cả đoán ngẫu nhiên — chứ không chỉ là "kém".

**"Đóng góp mới so với FT-Transformer gốc là gì?"**
> Em không đề xuất kiến trúc FTT mới. Đóng góp nằm ở **hệ thống hoá quanh nó**: Two-Stage Cascade, Asymmetric Voting theo chi phí lớp, HNM hai vòng, quy trình chẩn đoán và khắc phục covariate shift với Testbed thực, và bằng chứng định lượng về việc đánh giá đồng nhất miền thổi phồng metric.

---

# CHECKLIST TRƯỚC KHI BẢO VỆ

- [ ] Thuộc thông điệp cốt lõi (3 giai đoạn nhân-quả) — đọc trơn không nhìn.
- [ ] Bấm giờ tập nói ≥ 2 lần, tổng ≤ 15 phút (mục tiêu ~13).
- [ ] Nói được mọi con số mà không cần nhìn slide: 0,6809 · 0,9294 · 99,55% · 21,93% · −0,015 · 6,87% · 91,7% · 65.000:1.
- [ ] Giải thích được mọi từ viết tắt: NIDS, FTT, HNM, MCC, WSL2, NAT, IAT, AE Gate.
- [ ] Tập trả lời trơn 10 câu Q&A ở trên — **đặc biệt câu ⭐ "phát hiện bất thường" (khớp tên đề tài) + ranh giới "không claim cả hệ thống là không giám sát"**.
- [ ] Có nói cụm **"phát hiện bất thường"** ở Slide 3 (khung bài toán) và Slide 7 (Autoencoder Anomaly Gate) — để lời nói khớp tên đề tài.
- [ ] Slide 11 (covariate shift) và Slide 14 (bổ sung Hybrid) nói kỹ dù thiếu giờ.
- [ ] Câu "replay ≠ live" ở Slide 15 nói rõ ràng, không lảng tránh.
- [ ] Không dùng từ tuyệt đối ("nhất", "triệt để"); dùng "một trong những", "đạt mức cạnh tranh".
</content>
