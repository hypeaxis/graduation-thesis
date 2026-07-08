# Autoencoder Gate + ngưỡng tái tạo — "vẽ lại được thì là quen"

## Nó sinh ra để giải quyết chuyện gì?

Ở nhánh **NSL-KDD**, tầng 1 (Gating) cần quyết định *"flow này có bất thường không?"*. Thay vì huấn luyện một
bộ phân loại nhị phân thông thường, đồ án dùng một ý tưởng đẹp: **Autoencoder (AE — bộ tự mã hoá)** kết hợp
**ngưỡng lỗi tái tạo (reconstruction threshold)**.

Ý tưởng: dạy model **vẽ lại (tái tạo)** những flow **bình thường (Normal)**. Về sau, cái gì nó **vẽ lại được
gọn gàng** thì là quen (Normal); cái gì nó **vẽ lại méo mó** thì là lạ (bất thường) → đẩy sang tầng 2.

> **So sánh đời thường:** một hoạ sĩ luyện vẽ lại **khuôn mặt người bình thường** đến mức thành thạo. Đưa một
> khuôn mặt quen → vẽ lại giống y. Đưa một khuôn mặt **quái dị chưa từng thấy** → bản vẽ méo mó, sai lệch nhiều
> → "à, cái này lạ!".

---

## Autoencoder hoạt động thế nào?

```
x ──[ Encoder ]──▶ z (nén nhỏ) ──[ Decoder ]──▶ x̂ (tái tạo)
```

- **Encoder** nén `x` xuống một biểu diễn nhỏ `z` (bottleneck — nút thắt cổ chai).
- **Decoder** cố dựng lại `x̂` từ `z`.
- Huấn luyện **chỉ trên dữ liệu Normal**, tối thiểu hoá **lỗi tái tạo** `‖x − x̂‖²`.

Vì chỉ học Normal, AE **giỏi tái tạo Normal** nhưng **vụng về với dữ liệu lạ** → lỗi tái tạo của mẫu bất thường
sẽ **cao vọt**.

---

## Cổng theo ngưỡng τ — bóc từng mảnh

```
lỗi tái tạo  E(x) = ‖x − x̂‖²

E(x) < τ  →  Normal    (thoát khỏi pipeline)
E(x) ≥ τ  →  Suspicious (chuyển xuống Stage 2)
```

- **`E(x)`** → sai số giữa flow gốc và bản tái tạo.
- **`τ` (tau)** → ngưỡng quyết định. Đặt thấp → nhạy (bắt nhiều nghi ngờ, nhưng nhiều báo nhầm); đặt cao →
  lọc gắt (ít báo nhầm, nhưng dễ sót).

> **Nói đơn giản:** "vẽ lại sai quá ngưỡng cho phép" = đáng ngờ.

---

## Ưu điểm: học được cả tấn công CHƯA TỪNG THẤY

Vì AE **chỉ cần dữ liệu Normal** để học, nó có thể **gắn cờ những bất thường chưa từng xuất hiện trong tập
train** (zero-day) — chỉ cần chúng "khác Normal đủ nhiều". Đây là lợi thế của hướng **anomaly detection**
so với bộ phân loại thuần dựa trên nhãn tấn công đã biết.

---

## Tóm lại

- **Autoencoder Gate** học **tái tạo dữ liệu Normal**; mẫu lạ → **lỗi tái tạo cao**.
- Cổng theo **ngưỡng τ**: `E(x) < τ` → Normal thoát; `E(x) ≥ τ` → Suspicious xuống tầng 2.
- Ưu điểm: chỉ cần dữ liệu Normal, gắn cờ được cả bất thường chưa từng thấy.

**Hiểu cái này thì làm được gì?** Bạn thấy một cách tiếp cận **Gating khác** với bên CIC ([[two-stage-cascade-gating-expert]]):
NSL-KDD dùng AE + ngưỡng, minh hoạ tư duy "sàng lọc trước, chuyên sâu sau" bằng **anomaly detection**.
Tầng 2 sau đó là [[stacking-ensemble]].
