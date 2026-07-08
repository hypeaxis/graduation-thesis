# Scaler–Embedding Coupling — vì sao "đổi mỗi scaler" lại thất bại

## Nó sinh ra để giải quyết chuyện gì?

Khi gặp [[covariate-shift]], ý tưởng đầu tiên rất tự nhiên: *"Phân phối đổi thì mình **fit lại scaler**
(PowerTransformer) trên Testbed là xong!"*. Nghe hợp lý — nhưng thực nghiệm cho kết quả **tệ hơn**:
Accuracy từ 21,93% (transfer thẳng) **rơi xuống 6,87%** khi Re-fit Scaler.

Vì sao? Vì **scaler và embedding của model bị "khoá tay nhau" (coupled)** — không thể thay một cái độc lập.

> **So sánh đời thường:** một bản đồ được vẽ theo **thang đo cây số**. Giờ bạn lén đổi thước sang **dặm** nhưng
> **không báo cho người đọc bản đồ**. Người đọc vẫn hiểu mọi khoảng cách theo cây số → đi lạc hết. Đổi thước
> mà không đổi cách đọc = thảm hoạ.

---

## Model gồm hai mảnh học CÙNG NHAU

FT-Transformer thực chất là chuỗi hai thành phần, cả hai đều học từ CIC:

```
X_raw ──[ f_CIC: PowerTransformer ]──▶ X_scaled ──[ g_CIC: FTT embedding ]──▶ H_latent
```

- **`f_CIC`** → scaler, ánh xạ dữ liệu thô → dữ liệu đã chuẩn hoá **theo phân phối CIC**.
- **`g_CIC`** → embedding của FTT, được học để **kỳ vọng đầu vào có phân phối `f_CIC(X_CIC)`**.

Mấu chốt: `g_CIC` đã học rằng *"giá trị `x_j` nằm trong khoảng [a,b] theo scaler CIC thì mang ý nghĩa Z"*.

---

## Vì sao Re-fit Scaler phá vỡ mọi thứ

Khi thay `f_CIC` bằng `f_Testbed` (fit scaler mới trên Testbed):

1. `X_scaled^new = f_Testbed(X_raw^Testbed)` có **phân phối khác** `f_CIC(X_raw^CIC)`.
2. Nhưng `g_CIC` **vẫn kỳ vọng phân phối cũ** → **mâu thuẫn nội bộ**.
3. Khoảng giá trị ứng với "ý nghĩa Z" đã **dịch chuyển**, nhưng embedding **không hề hay biết** → hiểu sai toàn bộ.

> **Nói đơn giản:** bạn đổi đơn vị đầu vào, nhưng cái "bộ não" phía sau vẫn đọc theo đơn vị cũ → càng chỉnh
> càng loạn. Kết quả: Accuracy 21,93% → **6,87%**.

---

## Nguyên tắc rút ra

> **Scaler phải được thay đổi CÙNG LÚC với ít nhất một phần tham số model — không thể đổi một trong hai một
> cách độc lập.**

Đây chính là lý do giải pháp đúng là **[[layer-freezing-catastrophic-forgetting]]** (đổi scaler *và* fine-tune
tầng cao cùng nhau), chứ không phải chỉ thay scaler.

---

## Ví dụ SỐ

| Cách làm | Accuracy | Nhận xét |
|---|---|---|
| Transfer thẳng (giữ nguyên tất cả) | 21,93% | kém do covariate shift |
| **Re-fit Scaler (đổi mỗi scaler)** | **6,87%** | **tệ hơn** — mâu thuẫn scaler↔embedding |
| Layer Freezing (đổi scaler + fine-tune) | cải thiện rõ | đổi đồng thời → khớp lại |

---

## Tóm lại

- FTT = **scaler `f_CIC` + embedding `g_CIC`** học cùng nhau; `g` kỳ vọng đúng phân phối mà `f` tạo ra.
- **Re-fit Scaler đơn lẻ** tạo **mâu thuẫn nội bộ** (embedding đọc sai khoảng giá trị) → Accuracy 21,93% → 6,87%.
- **Nguyên tắc:** đổi scaler phải **đồng thời** với việc cập nhật (một phần) tham số model.

**Hiểu cái này thì làm được gì?** Bạn giải thích được một kết quả *phản trực giác* trong luận văn — vì sao một
bước tưởng "hiển nhiên đúng" lại làm hỏng, và vì sao [[layer-freezing-catastrophic-forgetting]] mới là lời giải.
