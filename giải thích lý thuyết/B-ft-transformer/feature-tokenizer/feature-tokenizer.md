# Feature Tokenizer — biến mỗi con số thành một "token"

## Nó sinh ra để giải quyết chuyện gì?

Transformer vốn sinh ra cho **câu chữ**: đầu vào là một chuỗi **token** (từ), mỗi từ đã là một vector nhúng.
Nhưng dữ liệu của ta là **dạng bảng (tabular)** — chỉ là `k` con số rời rạc (duration, số packet, cờ SYN…).

Câu hỏi: *làm sao biến một con số vô hồn thành một "token" giàu thông tin để Transformer xử lý?*

**Feature Tokenizer** chính là lời giải: nó **cấp cho mỗi đặc trưng một "phiên dịch viên" riêng**, dịch con số
đó thành một vector `d` chiều.

> **Nói nôm na:** Transformer chỉ nói được "tiếng vector". Mỗi đặc trưng của ta là một ngôn ngữ khác nhau
> (duration nói tiếng thời gian, byte nói tiếng dung lượng). Feature Tokenizer gắn cho mỗi đặc trưng một
> phiên dịch để tất cả cùng nói "tiếng vector".

---

## Công thức — bóc từng mảnh

Cho mẫu đầu vào `x = [x₁, x₂, …, x_k]`. Mỗi đặc trưng scalar `x_j` được ánh xạ thành vector nhúng `e_j`:

```
e_j = x_j · w_j + b_j        (w_j, b_j ∈ ℝ^d, RIÊNG cho từng đặc trưng)
```

- **`x_j`** → giá trị con số của đặc trưng thứ j (đã chuẩn hoá).
- **`w_j`** → vector "hướng" riêng của đặc trưng j; nhân với `x_j` để phóng to/thu nhỏ theo giá trị.
- **`b_j`** → vector "gốc" riêng, đảm bảo ngay cả khi `x_j = 0` token vẫn có thông tin về *danh tính* đặc trưng.
- **RIÊNG cho từng đặc trưng** → đây là điểm mấu chốt (xem dưới).

Số tham số của tầng này: `k × 2d` (mỗi đặc trưng có một cặp `w_j, b_j`).

---

## Điểm mấu chốt: mỗi đặc trưng có bộ chiếu RIÊNG (khác MLP)

Trong **MLP**, tất cả đặc trưng đi qua **cùng một ma trận trọng số** — nên con số `5` ở cột "duration" và
con số `5` ở cột "byte" bị đối xử **giống hệt nhau** ở lớp đầu.

Trong **Feature Tokenizer**, mỗi cột có `(w_j, b_j)` riêng → `duration=5` và `byte=5` biến thành **hai vector
hoàn toàn khác nhau**, mang theo *danh tính cột*.

> **So sánh đời thường:** MLP như một hòm thư chung — mọi lá thư nhét chung một khe. Feature Tokenizer như
> mỗi người có một hộp thư riêng có tên — nhìn là biết thư của ai.

---

## Thêm CLS token — "người tổng hợp"

Ta chèn thêm một token đặc biệt **CLS** vào đầu chuỗi:

```
T = [ e_CLS , e₁ , e₂ , … , e_k ]   ∈ ℝ^{(k+1) × d}
```

CLS không gắn với đặc trưng nào cả. Nhiệm vụ của nó: sau khi qua các tầng Attention, nó **gom góp thông tin
từ toàn bộ các token** để cuối cùng đại diện cho cả mẫu → đưa vào head phân loại.

> **Nói đơn giản:** CLS như **thư ký cuộc họp** — ngồi nghe tất cả phát biểu (các token đặc trưng), rồi cuối
> buổi tóm lại thành một kết luận.

---

## Ví dụ SỐ

Giả sử `d = 4`. Đặc trưng `Flow_Duration` sau chuẩn hoá có `x = 1,2`, với
`w = [0,5, −0,3, 0,8, 0,1]`, `b = [0, 0,2, −0,1, 0]`:

```
e = 1,2 · [0,5, −0,3, 0,8, 0,1] + [0, 0,2, −0,1, 0]
  = [0,60, −0,36, 0,96, 0,12] + [0, 0,2, −0,1, 0]
  = [0,60, −0,16, 0,86, 0,12]
```

Con số vô hồn `1,2` giờ đã thành một **vector 4 chiều** mang danh tính "duration" — sẵn sàng cho Attention.

---

## Tóm lại

- Feature Tokenizer **biến mỗi đặc trưng scalar `x_j` thành một token vector** `e_j = x_j w_j + b_j`.
- Mỗi đặc trưng có **bộ chiếu riêng** → giữ được *danh tính cột* (khác MLP dùng chung trọng số).
- **CLS token** được thêm vào để cuối cùng **tổng hợp toàn bộ input** cho phân loại.

**Hiểu cái này thì làm được gì?** Đây là cửa ngõ khiến Transformer dùng được cho dữ liệu bảng. Nó cũng là
chỗ mà đồ án thực hiện **Model Surgery** (thêm 3 hàng đặc trưng mới `77 → 80`) — vì mỗi đặc trưng là một hàng
độc lập trong ma trận embedding, ta ghép thêm hàng mà không phá phần cũ. Xem [[model-surgery]].
