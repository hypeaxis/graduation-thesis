# Label Smoothing — dạy model bớt "kiêu ngạo"

## Nó sinh ra để giải quyết chuyện gì?

Khi huấn luyện, ta thường đưa nhãn dạng **cứng (hard label)**: đúng lớp = 1, sai = 0. Điều này ép model
**tự tin 100%** vào một đáp án. Hệ quả: model dễ **kiêu ngạo (overconfident)** và **overfit** — nhớ vẹt
dữ liệu train, kém khi gặp dữ liệu mới.

**Label Smoothing (làm mượt nhãn)** sửa nhẹ: thay vì bắt model tin tuyệt đối, ta **chừa lại một chút nghi ngờ**.

> **So sánh đời thường:** thay vì bắt học sinh trả lời "chắc chắn 100% đáp án A", ta dạy em "khoảng 90% là A,
> chừa 10% cho khả năng mình nhầm". Thái độ khiêm tốn này giúp em **tổng quát hoá** tốt hơn, ít bảo thủ.

---

## Công thức — bóc từng mảnh

```
y_c^smooth = (1 − ε) · y_c + ε / C
```

- **`y_c`** → nhãn cứng gốc (1 hoặc 0).
- **`ε` (epsilon)** → mức làm mượt (đề tài V8.5 dùng `ε = 0,10`).
- **`(1 − ε)·y_c`** → kéo đỉnh "1" xuống còn `1 − ε` (vd 0,90).
- **`ε / C`** → rải phần `ε` đều cho **tất cả C lớp** (mỗi lớp được một chút xác suất nhỏ).

Ví dụ 5 lớp, `ε = 0,10`: nhãn cứng `[0, 1, 0, 0, 0]` → nhãn mượt `[0,02, 0,92, 0,02, 0,02, 0,02]`.

> **Nói đơn giản:** đỉnh nhọn "1" bị bạt xuống 0,92, phần dư 0,08 chia đều cho các lớp còn lại → mục tiêu
> "mềm" hơn, model không bị ép tin tuyệt đối.

---

## Khi nào KHÔNG nên dùng — bài học từ đồ án

Label Smoothing **rải xác suất cho mọi lớp**, kể cả lớp cực hiếm. Với **Heartbleed chỉ 10 mẫu**, việc này
**làm loãng** tín hiệu vốn đã ít ỏi → hại nhiều hơn lợi.

Vì thế đồ án **dùng `ε=0,10` cho Testbed V8.5** (giảm overfit) nhưng **KHÔNG dùng cho CIC Expert Network**
(vì ảnh hưởng xấu tới các lớp siêu hiếm như Heartbleed).

> **Bài học:** cùng một kỹ thuật, tốt ở ngữ cảnh này nhưng hại ở ngữ cảnh khác — phải hiểu *vì sao* mới dùng đúng chỗ.

---

## Tóm lại

- Label Smoothing biến nhãn cứng `1/0` thành nhãn mềm: `y^smooth = (1−ε)y + ε/C`.
- Tác dụng: giảm **overconfidence** và **overfit**, giúp model tổng quát hoá tốt hơn.
- **Cẩn trọng:** làm loãng tín hiệu lớp siêu hiếm → đồ án dùng cho V8.5 nhưng bỏ với CIC Expert (Heartbleed 10 mẫu).

**Hiểu cái này thì làm được gì?** Bạn biết một "nút chỉnh" nhỏ để chống overfit, và quan trọng hơn — biết
**khi nào tắt nó đi**, một quyết định tinh tế đáng ghi trong luận văn.
