# Stacking Ensemble — hội đồng có "chủ tọa" biết tổng hợp

## Nó sinh ra để giải quyết chuyện gì?

Khi có nhiều mô hình cùng dự đoán, cách đơn giản là **bỏ phiếu (voting)** — nhưng voting đối xử mọi mô hình
**ngang nhau** và không học được *mô hình nào giỏi ở tình huống nào*.

**Stacking (xếp chồng)** thông minh hơn: nó thêm một **mô hình cấp trên (meta-learner — bộ học tổng hợp)**
để **học cách kết hợp** đầu ra của các mô hình cấp dưới. Đây là tầng 2 trong nhánh NSL-KDD của đồ án.

> **So sánh đời thường:** một **hội đồng chuyên gia** cùng cho ý kiến, nhưng có thêm một **chủ tọa** đã học từ
> kinh nghiệm rằng *"vụ tài chính thì nghe ông A, vụ kỹ thuật thì nghe bà B"* — biết trọng ai lúc nào, thay vì
> đếm phiếu ngang nhau.

---

## Kiến trúc hai tầng — bóc từng mảnh

```
        ┌─ Base model 1 ─┐
  x ────┼─ Base model 2 ─┼──▶ [dự đoán 1, 2, 3] ──▶ Meta-learner ──▶ nhãn cuối
        └─ Base model 3 ─┘
```

- **Base models (mô hình cơ sở)** → nhiều bộ phân loại khác nhau, mỗi cái đưa ra dự đoán (xác suất/nhãn).
- **Đầu ra của chúng** trở thành **đầu vào mới** cho tầng trên.
- **Meta-learner** → học từ các dự đoán đó *cách tổng hợp tối ưu* để ra nhãn cuối.

> **Khác voting:** voting cố định luật (đa số thắng). Stacking **học luật kết hợp** từ dữ liệu → linh hoạt hơn.

---

## Vì sao Stacking mạnh?

- Các base model **giỏi ở những vùng khác nhau**; meta-learner học **khi nào tin ai** → khai thác điểm mạnh
  từng cái.
- Điều kiện để hiệu quả (giống mọi ensemble): các base model phải **đủ đa dạng** — sai trên những mẫu khác nhau.
  Xem [[inductive-bias-diversity]] và [[bias-variance-ensemble]].

> **Nói đơn giản:** ba cái đầu cùng nghĩ một kiểu thì thêm chủ tọa cũng vô ích; ba cái nghĩ khác nhau thì chủ
> tọa mới có cái để tổng hợp.

---

## Ví dụ trực giác

- Base model 1 (cây) mạnh ở mẫu gần biên cục bộ; Base model 2 (lân cận) mạnh ở vùng đông; Base model 3
  (Transformer) mạnh ở tương tác đặc trưng.
- Meta-learner học: với flow kiểu này → nghiêng theo model 3; kiểu kia → theo model 1. Kết quả tốt hơn từng
  cái đơn lẻ **và** hơn voting cứng.

---

## Tóm lại

- **Stacking** = nhiều **base model** → đầu ra của chúng làm đầu vào cho một **meta-learner** học **cách kết hợp**.
- Mạnh hơn voting vì **học luật tổng hợp** thay vì đếm phiếu ngang nhau.
- Vẫn cần các base model **đa dạng** mới hiệu quả.

**Hiểu cái này thì làm được gì?** Bạn phân biệt được **Stacking** (có meta-learner, dùng ở NSL-KDD Stage 2) với
**Voting** ([[asymmetric-cost-sensitive-voting]], dùng ở CIC) — hai cách ghép mô hình khác nhau trong cùng đồ án.
