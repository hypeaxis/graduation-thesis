# Vì sao đồ án bỏ NSL-KDD để chuyển sang CIC-IDS-2017

## Câu hỏi này chắc chắn hội đồng sẽ hỏi

Và có một câu trả lời **sai** mà rất nhiều người nói:

> "Vì NSL-KDD cũ rồi ạ."

Nghe thì có vẻ đúng, nhưng nó là câu trả lời của người chưa từng làm. Hội đồng hỏi tiếp một câu là gãy:
*"Cũ thì sao? Cũ mà model vẫn học được pattern tấn công thì có sao đâu?"*

Câu trả lời **đúng** phải trả lời được: cũ **ở chỗ nào**, và cái cũ đó **chặn mình ở đâu**.

Trong đồ án này, việc chuyển dataset không phải là một lựa chọn thẩm mỹ. Nó là **hệ quả bắt buộc** của
ba thứ mình *đo được* và *đâm đầu vào tường*:

1. Mình đã chạm **trần thực nghiệm** của NSL-KDD — và chứng minh được đó là trần của *dữ liệu*, không phải của *model*.
2. Cái trần đó là **cứng**, vì nó được *thiết kế* vào trong dataset — không thuật toán nào phá được.
3. Và quan trọng nhất: **122 đặc trưng của NSL-KDD không thể tái tạo được từ traffic thật.**
   Nếu bám NSL-KDD thì Giai đoạn 4–5 (Snort + live detection) của đồ án **không thể tồn tại**.

Đi từng cái một.

---

## Bước 0 — NSL-KDD thực ra là dữ liệu năm nào?

Đây là chỗ nhiều người hiểu sai, nên phải làm rõ trước.

Nhìn tên "NSL-KDD" và biết nó công bố năm 2009 (Tavallaee và cộng sự), nhiều bạn tưởng dữ liệu là của 2009.
**Không phải.** Chuỗi phả hệ của nó thế này:

```
DARPA 1998  ─────►  KDD Cup 99  ─────►  NSL-KDD (2009)
(MIT Lincoln Lab,   (biến pcap thành    (dọn dẹp thống kê
 mô phỏng LAN        41 đặc trưng)       của KDD Cup 99)
 không quân Mỹ)
```

- **DARPA 1998**: người ta dựng một mạng LAN **mô phỏng** (simulated — không phải mạng thật của ai cả),
  cho chạy vài tuần, vừa sinh traffic bình thường vừa bắn tấn công vào, và ghi lại pcap.
- **KDD Cup 99**: lấy pcap đó, biến mỗi kết nối thành **41 đặc trưng** + 1 nhãn.
- **NSL-KDD (2009)**: phát hiện KDD Cup 99 có **cực nhiều bản ghi trùng lặp** (~78% ở tập train, ~75% ở tập test).
  Trùng lặp làm model chỉ cần "học vẹt" mấy bản ghi lặp nhiều là điểm cao vống lên.
  Nên nhóm Tavallaee **xoá trùng, cân lại độ khó** → ra NSL-KDD.

**Nói nôm na:** NSL-KDD là bản **dọn dẹp lại bảng Excel** của dữ liệu 1998.
Người ta *không* đi bắt lại traffic mới. Ruột vẫn là traffic mô phỏng của năm 1998.

Vậy nên khi mình nói "NSL-KDD cũ", cụ thể là: **traffic bên trong nó là traffic của telnet, ftp, finger, rlogin —
thời chưa có HTTPS phổ biến, chưa có botnet hiện đại, chưa có slowloris, chưa có Heartbleed.**

Nhưng — và đây là điểm quan trọng — *chỉ riêng "cũ" thì vẫn chưa đủ để bỏ nó.* Đi tiếp.

---

## Lý do 1 — Mình đã đo được trần, và trần đó là của DỮ LIỆU

Đây là lập luận mạnh nhất, vì nó có **số**.

Trong Giai đoạn 1, mình không hề bỏ NSL-KDD sớm. Mình đã đấm vào nó **6 vòng cải tiến**:

| Phiên bản | Cải tiến | Macro-F1 |
|---|---|:---:|
| v2 | Baseline + SMOTE | 0,638 |
| v7 | Boost-minority validation set | 0,644 |
| v8 | Behavioral features (tự chế thêm feature) | 0,641 ❌ revert |
| v9 | Sửa U2R val starvation | 0,654 |
| v10 | Autoencoder-score-as-feature | 0,627 ❌ revert |
| v11 | Stacking thêm LightGBM | 0,668 |
| **Cuối** | **FTT + LightGBM → Meta-LR** | **0,6809** |

Nhìn kỹ cột cuối. Mình quăng vào đó toàn bộ kho vũ khí:
SMOTE, Class-Balanced Focal Loss, WeightedRandomSampler, Autoencoder gate, Stacking Ensemble, LightGBM...

Kết quả sau tất cả nỗ lực đó: **+0,043**. Từ 0,638 lên 0,681.

Rồi mang **cùng họ kiến trúc** (FT-Transformer) sang CIC-IDS-2017:

> **Macro-F1 = 0,9294.**

Đặt cạnh nhau:

- Đổi **model** (6 vòng, hàng tuần công sức): **+0,03**
- Đổi **dataset** (giữ nguyên tư duy kiến trúc): **+0,25**

**Nói nôm na:** khi bạn thay đủ mọi thứ ở model mà kim đồng hồ nhích được 3 vạch,
rồi đổi dữ liệu thì nó nhảy 25 vạch — nút thắt cổ chai (bottleneck) **nằm ở dữ liệu**, không nằm ở model.
Đây là một chẩn đoán kinh điển trong ML, và mình có số để chứng minh nó chứ không nói mồm.

> ⚠️ Một lưu ý trung thực: hai con số 0,68 và 0,93 **không so sánh trực tiếp được** với nhau
> (khác số lớp, khác độ khó, khác phân phối). Cái mình rút ra không phải "CIC dễ hơn nên điểm cao hơn",
> mà là: **trên NSL-KDD, mọi cải tiến thuật toán đều tắt dần về 0** — đó mới là tín hiệu của trần dữ liệu.

---

## Lý do 2 — Vì sao trần đó là trần CỨNG: mổ xẻ lớp R2L

Bây giờ phải trả lời: *sao biết là trần của dữ liệu chứ không phải mình chưa đủ giỏi?*

Nhìn vào bảng kết quả per-class cuối cùng của Giai đoạn 1:

| Lớp | Precision | Recall | F1 | Support |
|---|:---:|:---:|:---:|:---:|
| Normal | 0,7154 | 0,9682 | 0,8228 | 9.711 |
| DoS | 0,9630 | 0,8032 | 0,8759 | 7.458 |
| Probe | 0,8024 | 0,7852 | 0,7937 | 2.421 |
| **R2L** | **0,9681** | **0,2523** | **0,4003** | 2.885 |
| U2R | 0,5517 | 0,4776 | 0,5120 | 67 |

Dừng lại ở dòng **R2L** (Remote-to-Local — tấn công từ xa để chiếm quyền truy cập máy nạn nhân,
kiểu dò mật khẩu `guess_passwd`). Cặp số này rất lạ:

- **Precision = 0,9681** → khi model *dám* phán "đây là R2L", nó đúng **96,8%** số lần.
- **Recall = 0,2523** → nhưng nó chỉ *dám* phán trong **1/4** số ca R2L thật sự có.

**Đọc cặp số này ra tiếng Việt:** model **không hề ngu**. Nó biết R2L trông như thế nào —
bằng chứng là hễ nó nhận ra thì gần như không bao giờ nhầm. Vấn đề là **3/4 số ca R2L trong tập test,
nó nhìn vào mà không thấy gì hết.**

Vì sao? Đây là chỗ then chốt:

> **62% mẫu R2L trong tập test đi qua giao thức `pop3`.
> Trong khi R2L ở tập train chủ yếu đi qua `telnet` và `ftp`.**

Hiện tượng này gọi là **protocol shift** (dịch: lệch giao thức) — một dạng của **distribution shift**
(lệch phân phối giữa train và test).

Và nó chí mạng vì cách feature `service` được mã hoá: **one-hot encoding**.
`service` có 70 giá trị → biến thành 70 cột 0/1. Nghĩa là:

```
telnet  →  [0,0,...,1,...,0,0]
pop3    →  [0,1,...,0,...,0,0]
```

Hai vector này **trực giao** — vuông góc nhau. Khoảng cách giữa chúng bằng đúng khoảng cách giữa
`pop3` và một service ngẫu nhiên bất kỳ. Model **không có bất kỳ cây cầu ngữ nghĩa nào**
để suy ra "à, dò mật khẩu qua pop3 chắc cũng giống dò mật khẩu qua telnet".
Với nó, `pop3` chỉ là một cột nó **chưa từng thấy sáng lên** trong lúc học R2L.

**Phép so sánh đời thường:**
Bạn ôn thi Toán suốt 3 tháng bằng đề tiếng Việt. Vào phòng thi, đề Toán **y hệt về nội dung**
nhưng in bằng **tiếng Nhật**. Bạn được 2,5/10.
Điểm thấp đó **không đo được** việc bạn giỏi Toán hay không. Nó đo một thứ khác hoàn toàn.

Đó chính xác là thứ Macro-F1 = 0,68 trên NSL-KDD đang đo.

### Không phải mình chưa thử phá trần — mình đã thử và thất bại có hệ thống

| Đã thử | Vì sao thất bại |
|---|---|
| SMOTE ×20 cho lớp hiếm | Nội suy (interpolate) bên trong cụm **20 điểm** `warezmaster` của train **không thể** tạo ra độ phủ cho **944 điểm** test. Sinh thêm điểm giả trong một vùng hẹp thì vẫn là vùng hẹp đó. |
| Tự chế thêm behavioral features (v8) | −0,003. Feature mới cũng phải tính từ đúng bộ dữ liệu đó — không tạo ra thông tin mới. |
| Autoencoder score làm feature (v10) | −0,011. R2L/U2R có reconstruction error **thấp** (chúng *trông giống* traffic bình thường) → tín hiệu này vô dụng với đúng 2 lớp cần cứu. |
| Bỏ hard gate, đổi ngưỡng, chỉnh loss... | Nhích được vài phần nghìn rồi tắt. |

Thêm hai sự thật nữa **được cố tình thiết kế vào** NSL-KDD:

- **KDDTest+ chứa những loại tấn công KHÔNG hề có trong KDDTrain+** (tài liệu thường nêu con số 17 loại mới).
  Đây là **chủ ý** của nhóm tác giả — họ muốn dataset đo được khả năng tổng quát hoá sang tấn công lạ.
- **U2R chỉ có 52 mẫu train** (0,04% toàn bộ tập train). Học "leo thang đặc quyền" từ 52 ví dụ.

**Chốt lại lý do 2:** distribution shift ở NSL-KDD **không phải là bug, nó là feature** —
là dụng ý thiết kế của người tạo dataset. Bạn **không thể** sửa một dụng ý thiết kế bằng cách chỉnh loss function.
Muốn phá nó, chỉ có một cách: **đổi dữ liệu**.

---

## Lý do 3 — Cái lý do quyết định: KHÔNG THỂ tái tạo 122 feature từ traffic thật

Hai lý do trên là về **độ chính xác**. Lý do này là về **sự tồn tại của cả hệ thống** — và nó mới là
lý do khiến việc chuyển dataset trở thành *bắt buộc*, chứ không phải *nên làm*.

### 122 chiều đó thực chất là gì?

41 đặc trưng gốc của NSL-KDD chia làm 4 nhóm:

| Nhóm | Số feature | Ví dụ | Tính từ traffic thật được không? |
|---|:---:|---|---|
| **Basic** | 9 | `duration`, `protocol_type`, `service`, `flag`, `src_bytes` | ✅ Được — chỉ cần đọc header |
| **Content** | **13** | `hot`, `num_failed_logins`, `root_shell`, `su_attempted`, `num_file_creations`, `is_guest_login` | ❌ **KHÔNG** |
| **Time-based traffic** | 9 | `count`, `srv_count`, `serror_rate` (cửa sổ 2 giây) | ✅ Được |
| **Host-based traffic** | 10 | thống kê trên 100 kết nối gần nhất | ✅ Được |

Còn con số **122** ra từ đâu? Từ one-hot:

```
41 feature  −  3 feature phân loại  +  (protocol_type 3 + service 70 + flag 11 = 84 cột)
= 38 + 84 = 122 chiều
```

### Vấn đề chết người nằm ở 13 feature nhóm "content"

Nhìn kỹ mấy cái tên này:

- `num_failed_logins` — *số lần đăng nhập sai trong phiên này*
- `root_shell` — *phiên này có giành được shell root không*
- `su_attempted` — *có gõ lệnh `su` không*
- `is_guest_login` — *có đăng nhập bằng tài khoản guest không*

Để tính được `num_failed_logins`, bạn phải **đọc được nội dung (payload) của phiên đăng nhập
và hiểu được ngữ nghĩa của giao thức đó**. Ở DARPA 1998 thì làm được — vì telnet/ftp hồi đó
truyền **plaintext** (không mã hoá), và vì đó là môi trường mô phỏng, người ta nắm ground truth.

Bây giờ là **2026**. Traffic thật là **HTTPS / TLS — đã mã hoá**.
Bạn `tcpdump` một phiên đăng nhập, mở payload ra, và nhìn thấy… một đống byte ngẫu nhiên.

> **`num_failed_logins` = ?**
> Không tính được. Không bao giờ tính được. Không có công cụ open-source nào trên đời
> xuất ra được vector NSL-KDD 41 chiều từ file pcap thật — chính xác là vì 13 feature này.

### Và đây là chỗ kế hoạch gốc của đồ án đã vỡ

Mở `Instruction.md`, Giai đoạn 1 viết nguyên văn:

> *"Viết script chạy ngầm để đọc log từ Snort... Output cuối cùng là vector **122 chiều** khớp với format
> đầu vào của mô hình AI."*

Đến lúc bắt tay làm mới lộ ra sự thật: **9 feature basic + 19 feature traffic thì tính được.
13 feature content thì KHÔNG.**

Mà nếu bỏ 13 feature content đi thì sao? Nhìn lại danh sách:
`hot`, `num_failed_logins`, `root_shell`, `su_attempted`...

Đây **chính xác** là những feature mang tín hiệu của **R2L** (dò mật khẩu → `num_failed_logins`)
và **U2R** (leo thang đặc quyền → `root_shell`, `su_attempted`).

Nghĩa là: cắt 13 feature content → model chạy live sẽ **mù đúng hai lớp vốn đã yếu nhất**.
Đi vào ngõ cụt hoàn hảo. 🙂

### CIC-IDS-2017 giải quyết chuyện này thế nào

Khác biệt căn bản, và mình muốn nhấn mạnh vì đây là **insight quan trọng nhất của cả bài**:

> **80 đặc trưng của CIC-IDS-2017 không phải là một quy ước ghi trong paper.
> Chúng là ĐẦU RA CỦA MỘT CHƯƠNG TRÌNH: CICFlowMeter.**

Định nghĩa feature **không nằm trong file CSV** — nó **nằm trong code**. Và code đó là mã nguồn mở, tải về chạy được.

Nên ở cả hai đầu, mình dùng **đúng một hàm sinh feature**:

```
Lúc TRAIN:   pcap của CIC (2017)  ──► CICFlowMeter ──► 80 cột ──► FT-Transformer
Lúc DEPLOY:  tcpdump máy mình     ──► CICFlowMeter ──► 80 cột ──► FT-Transformer
                                       ▲ CÙNG MỘT TOOL, CÙNG MỘT ĐỊNH NGHĨA
```

Thuật ngữ cho chuyện này là **feature-generating process** (tiến trình sinh đặc trưng) —
và nguyên tắc vàng là: **tiến trình sinh đặc trưng lúc train phải trùng với lúc deploy.**
Nếu không trùng, model của bạn ở production đang ăn một loại thức ăn khác với lúc nó tập luyện.

Và đây **chính là** thứ `live_detection/` trong đồ án đang chạy thật:
`tcpdump` → CICFlowMeter → FT-Transformer V8.5 → WebSocket → dashboard.

**Phép so sánh đời thường:**
NSL-KDD đưa cho bạn **con cá** (một bảng số đã nấu chín, ăn xong là hết).
CIC-IDS-2017 đưa cho bạn **cái cần câu** (cái tool sinh ra bảng số đó).
Muốn làm hệ thống chạy trên mạng thật, bạn bắt buộc phải có **cái cần câu**.

---

## Lý do 4 — Nhãn phải khớp với thứ mình bắn được

Cái này ngắn nhưng rất thuyết phục khi bảo vệ.

Testbed của đồ án là một máy **Kali Linux** trong LAN. Những gì mình **thực sự bắn ra được**:
DoS Hulk, slowhttptest, PortScan bằng nmap, brute-force SSH bằng hydra...

Bây giờ đối chiếu bộ nhãn của hai dataset:

| | Các lớp tấn công |
|---|---|
| **NSL-KDD** | `buffer_overflow`, `rootkit`, `warezmaster`, `snmpgetattack`, `guess_passwd`, `phf`, `loadmodule`... trên nền `telnet` / `finger` / `rlogin` |
| **CIC-IDS-2017** | **DoS Hulk**, **DoS slowhttptest**, DoS GoldenEye, slowloris, DDoS LOIT, **PortScan**, **FTP-Patator / SSH-Patator** (brute force), Web Attack, Botnet ARES, Infiltration, Heartbleed |

Bộ nhãn của CIC-IDS-2017 **chồng khít** lên đúng những gì Kali bắn ra được.
Bộ nhãn của NSL-KDD thì **không map** vào bất cứ thứ gì mình có thể sinh ra trong testbed năm 2026.

Đây chính là lý do bộ nhãn 5 lớp của V8.5 (Benign / DoS / PortScan / BruteForce / …) trông như bây giờ —
nó là **con đẻ** của lựa chọn dataset này.

Cộng thêm chuyện quy mô, vì FT-Transformer là deep learning và deep learning thì đói dữ liệu:

| | Số dòng | Số đặc trưng | Số lớp |
|---|---:|:---:|:---:|
| NSL-KDD (test) | 22.542 | 122 (sau one-hot) | 5 |
| CIC-IDS-2017 | **2.830.743** | 77–80 | 9 (gộp từ 15 nhãn gốc) |

Gấp **125 lần**.

---

## Phần trung thực nhất: đổi dataset KHÔNG phải viên đạn bạc

Nếu chỉ kể tới đây thì bài này là quảng cáo, không phải nghiên cứu. Nên phải nói nốt phần này —
và nghịch lý thay, đây lại là **câu trả lời mạnh nhất** khi hội đồng vặn.

CIC-IDS-2017 đạt **99,55% Accuracy** trên chính nó. Nghe hoàn hảo.
Mang thẳng model đó sang testbed WSL2 của mình:

> **Accuracy = 21,93%. MCC = −0,015.**

MCC âm nghĩa là **còn tệ hơn đoán bừa**. Sụt **77,62%**.

Nghĩa là CIC-IDS-2017 **cũng dính covariate shift** — traffic của nó bắt trên switch vật lý Gigabit,
còn testbed của mình là card mạng ảo Hyper-V + NAT của Windows. Timing khác, MTU khác, TCP window khác.

Vậy bài học rút ra **không phải** là *"NSL-KDD tệ, CIC-IDS-2017 tốt"*. Bài học đúng là:

> **Hiệu năng của NIDS bị quyết định bởi việc phân phối lúc train có khớp môi trường deploy hay không.**
> NSL-KDD lệch ngay ở vòng **train → test của chính nó**.
> CIC-IDS-2017 lệch ở vòng **benchmark → testbed**.

Điểm khác biệt sống còn giữa hai cái lệch đó:

| | NSL-KDD | CIC-IDS-2017 |
|---|---|---|
| Có bị lệch phân phối không? | Có | Có |
| **Sửa được không?** | ❌ **Không.** Không có cách nào sinh thêm dữ liệu NSL-KDD từ mạng thật — vì không tính được 13 feature content. | ✅ **Được.** Chạy CICFlowMeter trên traffic testbed của chính mình → thu dữ liệu thật → retrain. |
| Kết quả | Kẹt ở 0,68 vĩnh viễn | Thu data thật → **V8.5, Macro-F1 = 91,7%** |

> **Đây là câu chốt hạ khi bảo vệ:**
> *"CIC-IDS-2017 không hoàn hảo — em cũng đã đo được nó sụt còn 21,93% trên testbed.
> Nhưng nó **khả hồi (recoverable)**, còn NSL-KDD thì **không**.
> Vì công cụ sinh đặc trưng của CIC-IDS-2017 chạy được trên mạng thật, nên em có thể thu dữ liệu của
> chính môi trường triển khai rồi huấn luyện lại. Với NSL-KDD thì con đường đó bị chặn ngay từ đầu."*

---

## Vậy Giai đoạn 1 có phí không? Không.

Câu này hội đồng cũng hay hỏi: *"Biết thế sao không dùng CIC-IDS-2017 từ đầu cho đỡ mất thời gian?"*

Ba ý trả lời:

**1. NSL-KDD là phòng thí nghiệm rẻ.**
125 nghìn dòng, train xong trong vài phút. Toàn bộ kho vũ khí xử lý mất cân bằng —
Class-Balanced Focal Loss, WeightedRandomSampler, Boost-Minority Validation Set, Two-Stage Gate, Stacking Ensemble —
đều được **phát triển và kiểm chứng ở đây trước**, rồi mới đem sang xài trên 2,8 triệu flow của Giai đoạn 2.
Thử ý tưởng trên tập nhỏ trước khi đốt tài nguyên vào tập lớn là quy trình đúng, không phải lãng phí.

**2. Bản thân việc chứng minh được cái trần là một kết quả khoa học.**
Nói "NSL-KDD có hạn chế" thì ai cũng nói được — đó là ý kiến.
Đưa ra bảng 6 vòng cải tiến tắt dần về 0, chỉ đúng ra 62% R2L test nằm ở `pop3`, và chứng minh
precision 0,97 / recall 0,25 nghĩa là *model không ngu mà là mù* — **đó là bằng chứng.**
Đồ án có một mạch nhân–quả: kết quả giai đoạn trước **sinh ra** vấn đề của giai đoạn sau.

**3. Cái trần đó chính là thứ hợp thức hoá toàn bộ phần còn lại của đồ án.**
Không có nó, việc chuyển sang CIC-IDS-2017 chỉ là "em thấy dataset này xịn hơn".
Có nó, việc chuyển sang CIC-IDS-2017 là **kết luận bắt buộc rút ra từ số liệu**.

---

## Tóm lại

- **Không phải vì NSL-KDD "cũ".** Mà vì (a) mình đã đo được trần 0,68 và chứng minh trần đó là của *dữ liệu*
  (đổi model: +0,03; đổi dataset: +0,25); (b) trần đó **cứng** vì distribution shift được *thiết kế* vào dataset
  (62% R2L test dùng `pop3`, train dùng `telnet` — one-hot khiến hai cái này trực giao, model không nội suy được);
  và (c) **13 feature "content" của NSL-KDD không tính được từ traffic thật đã mã hoá.**

- **Lý do (c) là lý do quyết định.** 80 feature của CIC-IDS-2017 là *đầu ra của CICFlowMeter* — một công cụ
  chạy được trên pcap thật. Nhờ vậy **cùng một tiến trình sinh đặc trưng** dùng được ở cả lúc train lẫn lúc deploy.
  Không có nó, Giai đoạn 4–5 (Snort + live detection) của đồ án đơn giản là **không tồn tại**.

- **Và CIC-IDS-2017 cũng không hoàn hảo** — nó sụt còn 21,93% trên testbed WSL2.
  Nhưng nó **khả hồi**: thu dữ liệu thật bằng chính CICFlowMeter → retrain → V8.5 đạt Macro-F1 91,7%.
  Đó mới là điểm khác biệt thật sự giữa hai dataset.

---

## Bộ câu hỏi hội đồng hay vặn + cách đỡ

**❓ "Nhiều paper vẫn dùng NSL-KDD mà, nó vẫn là benchmark chuẩn đấy chứ?"**
> Đúng ạ, và em vẫn dùng — ở Giai đoạn 1, đúng vai trò của nó: **benchmark để so sánh thuật toán**.
> Nhưng đồ án của em không dừng ở so sánh thuật toán, mà phải **chạy được trên mạng thật**.
> Ở vai trò thứ hai đó thì NSL-KDD không đáp ứng được, vì bộ đặc trưng của nó không tái tạo được từ pcap.
> (Nhân tiện, nếu ai đó báo cáo 99% trên KDDTest+ 5 lớp thì con số đó gần như chắc chắn có vấn đề về
> giao thức đánh giá — với distribution shift được thiết kế sẵn trong đó, mức 0,65–0,70 mới là trung thực.)

**❓ "Sao không dùng CSE-CIC-IDS2018 cho mới hơn?"**
> Về nguyên tắc là dùng được ạ, vì nó cũng do CIC làm và cũng dùng CICFlowMeter — nên lập luận "cần cái cần câu"
> của em vẫn thoả. Em chọn 2017 vì: quy mô vừa sức máy (2,8 triệu flow so với ~16 triệu),
> tập tấn công đa dạng hơn cho phân loại đa lớp, và nó có lớp **PortScan** tách riêng —
> lớp mà sau này em phải dùng làm **dữ liệu surrogate** vì PortScan trong WSL2 không phân tách được
> (F1 < 9% ở mọi thuật toán).

**❓ "Sao không dùng UNSW-NB15?"**
> Vì đặc trưng của UNSW-NB15 sinh bằng **Argus/Bro**, không phải CICFlowMeter.
> Chọn nó là em lại rơi vào đúng cái bẫy cũ: **bộ feature của dataset khác với bộ feature mà pipeline live sinh ra.**
> Chọn CIC-IDS-2017 là để train và deploy dùng **chung một công cụ**.

**❓ "Vậy em kết luận NSL-KDD là dataset tồi?"**
> Không ạ. Em kết luận là **NSL-KDD không phù hợp với BÀI TOÁN CỦA EM.**
> Nó vẫn tốt cho việc so sánh thuật toán trên một benchmark có distribution shift thật.
> Nó chỉ không dùng được khi bạn cần một hệ thống **cắm vào mạng thật rồi chạy**.

---

## Muốn đào sâu hơn thì...

- **Bản chất toán học của protocol shift:** đây là một ca **covariate shift** — phân phối đầu vào
  P(x) đổi giữa train và test, trong khi quan hệ nhãn P(y|x) về cơ bản giữ nguyên
  (dò mật khẩu vẫn là dò mật khẩu, dù qua telnet hay pop3). Với covariate shift *có phần chồng lấp*
  thì kỹ thuật domain adaptation còn cứu được. Nhưng ở đây, do one-hot làm `pop3` và `telnet` **trực giao**,
  phần chồng lấp gần như **bằng 0** ở đúng chiều mang thông tin — nên adaptation cũng bó tay.
  Đây cũng chính là mạch nối sang `Domain_Adaptation_Workspace/` ở giai đoạn sau.
- **Câu hỏi mở để tự nghĩ:** nếu thay one-hot cho `service` bằng một **embedding học được**
  (giống word embedding), liệu model có tự học được rằng `pop3` và `telnet` "gần nhau" ở khía cạnh
  "đều là giao thức có đăng nhập" không? Về lý thuyết thì có khả năng — nhưng chỉ khi trong tập train
  có đủ tín hiệu để học ra khoảng cách đó. Với 995 mẫu R2L, gần như chắc chắn là không đủ.
  (Đây là một hướng thảo luận đẹp cho phần "hướng phát triển" ở Chương 6.)

---

## Liên quan

- [[ids-supervised-flow-classification]] — vì sao bài toán được đặt trên *flow* chứ không phải *packet*
- [[flow-features-cicflowmeter]] — 80 đặc trưng đó cụ thể là gì, tính ra sao
- [[class-imbalance-metrics]] — vì sao dùng Macro-F1 chứ không dùng Accuracy để đo
- [[snort-hybrid-ids]] — tầng luật bù cho điểm mù của tầng ML
