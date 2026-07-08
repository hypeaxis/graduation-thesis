# Multi-Head Self-Attention — cho các đặc trưng "hỏi chuyện" nhau

## Nó sinh ra để giải quyết chuyện gì?

Nhiều tấn công **không lộ ra ở một đặc trưng đơn lẻ**, mà ở **tổ hợp** của chúng.
Ví dụ: *"khi `src_bytes` cao **VÀ** `rerror_rate` cao **đồng thời** → tấn công R2L"*. Một mình `src_bytes`
cao thì bình thường; phải nhìn **quan hệ** giữa các đặc trưng mới thấy.

**Self-Attention** là cơ chế cho phép mỗi token (đặc trưng) **hỏi mọi token khác "bạn liên quan tới tôi
cỡ nào?"**, rồi trộn thông tin theo mức liên quan đó. Đây là trái tim của Transformer.

> **Nói nôm na:** thay vì mỗi đặc trưng tự làm việc một mình, chúng được ngồi lại "họp nhóm" — ai liên quan
> tới ai nhiều thì lắng nghe nhau nhiều.

---

## Ba vai: Query, Key, Value

Từ ma trận token `T`, ta chiếu ra ba ma trận:

```
Q = T·W^Q    (Query — "tôi đang tìm gì")
K = T·W^K    (Key   — "tôi có gì để chào")
V = T·W^V    (Value — "thông tin thực tôi mang")
```

> **So sánh đời thường:** như tra cứu thư viện. **Query** = câu hỏi bạn mang tới; **Key** = nhãn trên gáy
> mỗi cuốn sách; **Value** = nội dung bên trong sách. Bạn so câu hỏi (Q) với nhãn (K) để biết cuốn nào đáng
> đọc, rồi lấy nội dung (V) của cuốn đó.

---

## Công thức Attention — bóc từng mảnh

```
Attention(Q, K, V) = softmax( QKᵀ / √d_k ) · V
```

- **`QKᵀ`** → nhân Query với Key: ra **điểm liên quan** giữa mọi cặp token (token i hợp token j cỡ nào).
- **`/ √d_k`** → chia cho căn số chiều. Khi `d_k` lớn, tích `QKᵀ` dễ ra số khổng lồ → softmax bão hoà →
  **vanishing gradient** (gradient teo). Chia cho `√d_k` giữ giá trị ở mức vừa phải.
- **`softmax(…)`** → biến điểm liên quan thành **trọng số** cộng lại bằng 1 (phân bổ sự chú ý).
- **`· V`** → dùng trọng số đó **trộn Value** của các token → token mới = tổng có trọng số thông tin của
  những token liên quan.

> **Nói đơn giản:** mỗi token = "trung bình có trọng số" thông tin của những token mà nó thấy liên quan nhất.

---

## "Multi-Head" — nhiều góc nhìn song song

Thay vì một Attention, ta chạy **`h` đầu (head) song song**, mỗi head có bộ `W^Q, W^K, W^V` riêng:

```
MHSA(T) = Concat(head₁, …, head_h) · Wᴼ
```

Mỗi head học **một kiểu quan hệ khác nhau**: head này chuyên bắt cặp "duration ↔ byte", head kia bắt
"SYN flag ↔ số flow"… rồi nối lại.

> **So sánh:** như đọc một vụ án bằng nhiều chuyên gia — người soi tài chính, người soi thời gian, người soi
> hành vi — rồi tổng hợp. Nhiều góc nhìn tốt hơn một.

---

## Ví dụ trực giác

Token "src_bytes" mang Query "tôi có bất thường không?". Nó so với Key của mọi token khác:

- Với "rerror_rate": điểm liên quan **cao** → softmax cho trọng số lớn → hút mạnh thông tin từ nó.
- Với "duration": điểm liên quan thấp → gần như bỏ qua.

→ Token "src_bytes" sau Attention đã "biết" rằng `rerror_rate` cũng đang cao → tổ hợp này đẩy về phía **R2L**.
Đây là thứ MLP phải học *ngầm* và kém hiệu quả hơn.

---

## Tóm lại

- Self-Attention cho mỗi đặc trưng **hỏi mọi đặc trưng khác mức liên quan** qua `Q·Kᵀ`, rồi **trộn Value**
  theo trọng số softmax.
- Hệ số **`1/√d_k`** chống vanishing gradient khi số chiều lớn.
- **Multi-Head** = nhiều Attention song song, mỗi cái bắt một kiểu quan hệ → giàu hơn.

**Hiểu cái này thì làm được gì?** Đây chính là lý do đồ án **chọn FT-Transformer thay vì MLP/RF/XGBoost**:
Attention học **tường minh** tương tác đặc trưng, thay vì học ngầm. Nó cũng là nền để hiểu vì sao
[[layer-freezing-catastrophic-forgetting]] hiệu quả — tầng Attention thấp học quan hệ tổng quát.
