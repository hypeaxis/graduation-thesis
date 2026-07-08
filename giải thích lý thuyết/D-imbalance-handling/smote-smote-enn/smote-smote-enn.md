# SMOTE & SMOTE-ENN — "vẽ thêm" mẫu thiểu số

## Nó sinh ra để giải quyết chuyện gì?

Một cách khác để chống mất cân bằng: thay vì chỉnh loss ([[focal-loss]]), ta **chỉnh dữ liệu** — tạo thêm
mẫu cho lớp hiếm cho bớt lệch.

Cách thô sơ là **sao chép** mẫu hiếm (oversampling), nhưng bản sao y hệt khiến model **học vẹt** (overfit).
**SMOTE (Synthetic Minority Over-sampling Technique)** thông minh hơn: nó **tạo mẫu MỚI bằng cách nội suy**
giữa các mẫu hiếm có sẵn.

> **So sánh đời thường:** trên bản đồ, giữa hai ngôi nhà cùng một khu phố, ta "vẽ thêm" một ngôi nhà mới nằm
> đâu đó trên đoạn nối hai nhà — vẫn thuộc khu phố đó, nhưng là một địa chỉ mới, không phải bản sao.

---

## Công thức — bóc từng mảnh

```
x_new = x_i + λ · (x_kr − x_i) ,   λ ~ Uniform(0, 1)
```

- **`x_i`** → một mẫu thiểu số bất kỳ.
- **`x_kr`** → một **láng giềng ngẫu nhiên** trong K-NN (K láng giềng gần nhất) của `x_i`, **cùng lớp**.
- **`x_kr − x_i`** → vector nối từ `x_i` tới láng giềng.
- **`λ ~ Uniform(0,1)`** → chọn ngẫu nhiên một điểm **trên đoạn thẳng** giữa hai mẫu.

→ `x_new` là một điểm mới nằm giữa hai mẫu hiếm cùng lớp → "lấp đầy" vùng thưa thớt của lớp thiểu số.

> **Nói đơn giản:** đứng giữa hai bạn cùng đội rồi tạo ra một "bạn ảo" ngay giữa họ.

---

## SMOTE-ENN: dọn nhiễu sau khi vẽ

SMOTE có thể vẽ mẫu mới **lấn sang vùng của lớp khác** (gần biên giới) → tạo nhiễu. **ENN (Edited Nearest
Neighbors)** là bước dọn dẹp đi kèm: **xoá những mẫu mà đa số láng giềng của nó thuộc lớp khác** (mẫu "lạc chỗ",
nằm sai phía biên).

> **So sánh:** SMOTE là vẽ thêm người vào đội; ENN là mời ra ngoài những ai đứng lẫn sang sân đội bạn cho
> ranh giới rõ ràng.

---

## Giới hạn: nội suy không tạo ra "sự đa dạng" thật

SMOTE chỉ nội suy **giữa các mẫu đã có**. Khi lớp cực hiếm nằm trong không gian **rất nhiều chiều**, các mẫu
tổng hợp chủ yếu là **bản sao gần** — không thêm được thông tin mới thật sự.

Ví dụ trong đồ án: **U2R chỉ 52 mẫu trong không gian 122 chiều** → SMOTE tạo ra toàn điểm sát nhau, diversity
không tăng bao nhiêu.

> **Nói nôm na:** vẽ thêm 1000 người "y chang" thì đội vẫn nghèo nàn ý tưởng — số lượng tăng nhưng *chất* không tăng.

---

## Tóm lại

- SMOTE **tạo mẫu thiểu số mới** bằng nội suy tuyến tính giữa một mẫu và láng giềng cùng lớp
  (`x_new = x_i + λ(x_kr − x_i)`).
- **SMOTE-ENN** thêm bước ENN **xoá mẫu nhiễu gần biên** cho ranh giới sạch.
- **Giới hạn:** với lớp cực hiếm trong không gian nhiều chiều, mẫu tổng hợp chỉ là bản sao gần → ít giá trị thật.

**Hiểu cái này thì làm được gì?** Bạn biết SMOTE là *lựa chọn phía dữ liệu*, và hiểu vì sao với các lớp siêu
hiếm nó không phải "viên đạn bạc" — một lý do đồ án nghiêng về giải pháp phía loss ([[focal-loss]]) và
[[hard-negative-mining]].
