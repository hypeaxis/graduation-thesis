# Transformer Block & Feed-Forward Network (Pre-LayerNorm)

## Nó sinh ra để giải quyết chuyện gì?

Self-Attention giỏi cho các token **trao đổi thông tin với nhau**, nhưng bản thân nó chỉ là phép trộn
**tuyến tính**. Để mạng thực sự mạnh, ta cần thêm:

1. **Xử lý phi tuyến** riêng cho từng token (FFN).
2. **Đường tắt (residual)** để gradient không teo khi mạng sâu.
3. **Chuẩn hoá (LayerNorm)** để huấn luyện ổn định.

Gói cả ba thứ đó quanh Attention → ta có một **Transformer Block**. Xếp chồng `L` block → mô hình sâu.

> **Nói nôm na:** Attention là buổi "họp nhóm trao đổi"; FFN là lúc mỗi người "về bàn tự tiêu hoá thông tin";
> residual + LayerNorm là "giữ bản ghi chú gốc và sắp xếp lại cho gọn" để không rối.

---

## Feed-Forward Network (FFN) — bóc từng mảnh

FFN áp dụng **độc lập trên từng token** (cùng một trọng số cho mọi token):

```
FFN(z) = GELU(z·W₁ + b₁)·W₂ + b₂        với  d_ff = 4d
```

- **`z·W₁ + b₁`** → nở token từ `d` chiều lên `d_ff = 4d` chiều (không gian rộng hơn để "suy nghĩ").
- **`GELU(…)`** → hàm kích hoạt phi tuyến (mượt hơn ReLU) — chỗ mạng học được quan hệ *cong*, không chỉ thẳng.
- **`·W₂ + b₂`** → ép trở lại `d` chiều để nối tiếp block sau.

> **Nói đơn giản:** FFN như cho mỗi token một "phòng làm việc rộng gấp 4" để nghiền ngẫm, xong thu gọn kết quả.

---

## Residual + LayerNorm: Transformer Block (Pre-LN)

Đề tài dùng biến thể **Pre-LayerNorm**: LayerNorm được áp *trước* khi vào Attention/FFN, rồi mới **cộng
đường tắt** (đúng như code: `x = x + sublayer(LayerNorm(x))` — ổn định hơn khi mạng sâu):

```
T'  = T  + MHSA( LayerNorm(T)  )     ← chuẩn hoá TRƯỚC, xong cộng đường tắt
T'' = T' + FFN(  LayerNorm(T') )
```

Bóc ý nghĩa:

- **`LayerNorm(T)`** → chuẩn hoá (mean 0, var 1) *trước*, để đầu vào Attention/FFN luôn "sạch", giữ các con
  số không phình to/teo nhỏ qua từng tầng → ổn định. (Đây là điểm khác Post-LN, nơi chuẩn hoá đặt *sau*.)
- **`T + …` (residual)** → *cộng thêm* kết quả sublayer vào token gốc, không thay thế. Nhờ "đường tắt" này,
  gradient chảy thẳng về tầng dưới → tránh **vanishing gradient**, huấn luyện được mạng sâu.

> **So sánh đời thường:** residual như **bản nháp gốc luôn được giữ lại** — mỗi tầng chỉ ghi chú *bổ sung*
> lên trên, lỡ tầng nào ghi bậy vẫn còn bản gốc để lần về.

---

## Xếp chồng L tầng → CLS → phân loại

Sau `L` Transformer Block, ta lấy **CLS token** ở tầng cuối (đã hút thông tin toàn bộ input) đưa qua head:

```
ŷ = softmax( e_CLS^(L) · W_cls + b_cls )
```

→ ra phân phối xác suất trên các lớp (Benign / các loại tấn công).

**Cấu hình trong đề tài** (ví dụ Testbed V8.5): `d = 128`, `h = 8` heads, `L = 4` tầng, `d_ff = 512`.
Expert Network dùng nhỏ hơn (`d = 64`, `L = 3`) vì chỉ nhận 34 đặc trưng và ~17% traffic.

---

## Ví dụ trực giác một vòng đời token

1. Token "SYN_flag" vào Block 1 → **Attention**: hút thêm thông tin từ "số flow", "duration".
2. **FFN**: tự nghiền tổ hợp đó, bật lên tín hiệu "giống quét cổng".
3. **Residual + LN**: giữ bản gốc + chuẩn hoá.
4. Lặp qua Block 2, 3, 4 → tín hiệu ngày càng rõ.
5. **CLS** gom lại → head phán "PortScan".

---

## Tóm lại

- **Transformer Block** = MHSA + FFN, mỗi cái bọc trong **residual + LayerNorm** (kiểu Pre-LN).
- **FFN** (`GELU`, `d_ff = 4d`) cho mỗi token xử lý **phi tuyến** riêng.
- **Residual** tạo đường tắt chống vanishing gradient; **LayerNorm** giữ ổn định. Chồng `L` tầng rồi
  đọc **CLS** → softmax phân loại.

**Hiểu cái này thì làm được gì?** Bạn nắm được *toàn bộ đường đi* từ đặc trưng thô đến nhãn — và hiểu vì sao
có thể **đóng băng vài tầng** ([[layer-freezing-catastrophic-forgetting]]) khi thích nghi miền: tầng thấp
học cái tổng quát, tầng cao học cái đặc thù.

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| TransformerBlock Pre-LN: x + sublayer(LN(x)) | `Final/01_NSL_KDD/src/models/phase2_ft_transformer.py:245` |
| FFN: Linear→GELU→Dropout→Linear | `Final/01_NSL_KDD/src/models/phase2_ft_transformer.py:235` |
| Config mặc định d=128,h=8,L=4,d_ff=512 | `Final/01_NSL_KDD/src/models/phase2_ft_transformer.py:255` |

**Khi phản biện:** code là **Pre-LayerNorm thật** (`x = x + sublayer(LayerNorm(x))`). Quyển đồ án viết công thức dạng Post-LN (`LayerNorm(x + sublayer(x))`) — nếu hội đồng hỏi, giải thích rằng **triển khai thực tế là Pre-LN**.
