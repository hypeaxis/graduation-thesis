# Power Transformer — Yeo-Johnson: "bẻ cong thước đo" cho dữ liệu lệch

## Nó sinh ra để giải quyết chuyện gì?

Dữ liệu thật đời hay bị **lệch (skewed)** — đặc biệt là dữ liệu mạng: số byte, số packet,
thời lượng flow… đa số nhỏ, nhưng thỉnh thoảng có vài giá trị **cực to** (một cuộc tấn công
gửi 10 triệu packet chẳng hạn).

Vấn đề: rất nhiều mô hình và phép tính thống kê ngầm giả định dữ liệu **cân đối, hình chuông
(Gaussian — phân phối chuẩn)**. Khi dữ liệu lệch một đống về một phía, chúng học kém đi.

> **Nói nôm na:** giống một lớp học mà 3 bạn cao 1m6 nhưng 1 bạn cao 3m — cái "trung bình chiều cao"
> trở nên vô nghĩa, mọi phép tính bị anh khổng lồ kéo méo hết.

**Power Transformer** là cái "nắn" lại đống dữ liệu lệch đó cho về gần hình chuông.
**Yeo-Johnson** là một công thức cụ thể để nắn.

---

## Ý tưởng cốt lõi: dùng lũy thừa để kéo cái đuôi lại

Chữ **"power" nghĩa là lũy thừa** — vì phép biến đổi này nâng dữ liệu lên số mũ **λ (lambda)**.
Tùy λ mà nó bóp hay giãn thang đo:

- **λ nhỏ (gần 0)** → hành xử như **log**, *bóp* mấy giá trị khổng lồ lại gần → chữa lệch phải (right-skew).
- **λ = 1** → *không đổi gì cả* (giữ nguyên, chỉ dịch).
- **λ lớn (>1)** → *giãn* ra → chữa lệch trái (left-skew).

> **So sánh đời thường:** như cái **thang đo log của động đất (Richter)** hay **âm lượng (decibel)** —
> độ 8 với độ 4 thật ra khác nhau cả chục nghìn lần, nhưng log ép chúng về một khoảng nhìn được.
> Yeo-Johnson làm y hệt, nhưng **tự dò xem bóp mạnh cỡ nào là vừa**.

---

## Vì sao là "Yeo-Johnson" mà không phải "Box-Cox"?

Có một anh tiền bối là **Box-Cox** cũng làm y chang, nhưng **chỉ chạy được với số dương (> 0)**.
Dữ liệu có số 0 hoặc số âm là nó chịu.

**Yeo-Johnson chính là bản vá:** xử lý được cả **số âm và số 0**. Nó khéo ở chỗ dùng **hai công thức
khác nhau** cho phần dương và phần âm, ghép lại cho mượt tại điểm 0.

> **Nói đơn giản:** Box-Cox = phiên bản chỉ cho số dương. Yeo-Johnson = bản nâng cấp, nhét số nào vào cũng nuốt được.

---

## Công thức — bóc từng mảnh

Gọi `y` là giá trị gốc, `λ` là tham số, `ψ` (psi) là giá trị sau biến đổi:

**Khi y ≥ 0:**

```
ψ = ((y + 1)^λ − 1) / λ          nếu λ ≠ 0
ψ = ln(y + 1)                    nếu λ = 0
```

**Khi y < 0:**

```
ψ = −((−y + 1)^(2−λ) − 1) / (2−λ)   nếu λ ≠ 2
ψ = −ln(−y + 1)                     nếu λ = 2
```

Nhìn rối, nhưng bóc ra thì đơn giản:

- **`(y + 1)^λ`** → phần "lũy thừa", chính là chỗ *bẻ cong thước đo*. λ quyết định cong bao nhiêu.
- **`+1` bên trong** → cái mẹo để `y = 0` không làm vỡ log (`ln(0)` là âm vô cực).
- **`− 1) / λ`** → chuẩn hóa lại để khi λ→0 công thức trơn tru biến thành **log** (đây là lý do λ=0 lại ra `ln`,
  không phải trùng hợp).
- **Nhánh `y < 0`** dùng số mũ **`2−λ`** và dấu trừ ở ngoài → *phản chiếu gương* logic của nhánh dương
  sang phía âm, để hai bên đối xứng và nối liền tại 0.

> **Chỉ cần nhớ 1 câu:** cả đống ký hiệu đó chỉ để nói *"nâng y lên mũ λ một cách an toàn cho cả số âm,
> 0 và dương, và mượt tại λ=0"*.

---

## Ví dụ SỐ cho thấy tận mắt

Giả sử feature "số byte của flow" có 4 giá trị lệch phải nặng:

```
gốc:      1        2        10        1000
```

Khoảng cách giữa 10 và 1000 to khủng khiếp — model sẽ bị giá trị 1000 "chiếm sóng".

Cho λ = 0 (tức dùng `ln(y+1)`):

```
ln(1+1)    = 0.69
ln(2+1)    = 1.10
ln(10+1)   = 2.40
ln(1000+1) = 6.91
```

Nhìn thấy chưa? Khoảng cách **10 → 1000** (cách nhau 990 đơn vị) giờ chỉ còn **2.40 → 6.91** (cách 4.5).
Cái đuôi khổng lồ **bị kéo về gần**, dữ liệu bớt lệch, cân đối hơn hẳn.

---

## Ai chọn λ? — Máy tự dò, bạn không phải chỉnh tay

Đây là chỗ hay nhất. Bạn **không cần đoán λ**. Thuật toán dùng **Maximum Likelihood Estimation
(MLE — ước lượng hợp lý cực đại)**: nó thử rất nhiều giá trị λ, mỗi lần đo xem "dữ liệu sau biến đổi
giống hình chuông cỡ nào", rồi **chọn λ làm nó giống chuông nhất**.

> **So sánh:** như bạn vặn nút lấy nét (focus) máy ảnh — vặn qua vặn lại tới khi ảnh nét nhất thì dừng.
> Ở đây "nét" = "giống phân phối chuẩn nhất", và máy tự vặn giùm bạn.

---

## Trong `sklearn` và gắn với đồ án

```python
from sklearn.preprocessing import PowerTransformer
pt = PowerTransformer(method='yeo-johnson')  # mặc định luôn là yeo-johnson
X_new = pt.fit_transform(X)
```

Một điểm hay lưu ý: mặc định nó còn **standardize** sau khi biến đổi (đưa về trung bình 0, phương sai 1) —
tức bạn được combo *"nắn về chuông + đưa về cùng thang đo"* trong một bước.

**Với live-detection:** các feature như `flow_duration`, `total_bytes`, `packets_per_sec` thường lệch phải
khủng khiếp. Yeo-Johnson kéo đuôi về giúp:

- Model (nhất là mấy loại nhạy với thang đo/phân phối) học ổn định hơn.
- Giảm chuyện một flow tấn công cực lớn làm lệch scaler.
- ⚠️ **Nhớ:** `fit` transformer **chỉ trên tập train**, rồi `transform` lên test — nếu fit cả trên test
  là **rò rỉ dữ liệu (data leakage)**, kết quả đẹp giả.

---

## Tóm lại

- **Yeo-Johnson** = phép biến đổi lũy thừa **nắn dữ liệu lệch về gần hình chuông (Gaussian)**,
  bằng cách nâng lên mũ **λ**.
- Nó là **bản nâng cấp của Box-Cox**: chạy được cả **số âm và 0**.
- **λ do máy tự dò** bằng MLE để dữ liệu giống chuông nhất — bạn không phải chọn.

**Hiểu cái này thì làm được gì?** Bạn biết *khi nào nên dùng* (feature lệch nặng, có số 0/âm),
*tránh được data leakage* khi fit, và giải thích được trong luận văn **vì sao** bước tiền xử lý này giúp
mô hình detection ổn định hơn — thay vì chỉ "em thấy trong sklearn nên em dùng".
