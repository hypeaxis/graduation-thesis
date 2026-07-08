# Bias–Variance & Ensemble giảm Variance — vì sao "hỏi nhiều người" tốt hơn

## Nó sinh ra để giải quyết chuyện gì?

Vì sao gộp nhiều mô hình (ensemble) lại tốt hơn một mô hình? Câu trả lời nằm ở **phân rã Bias–Variance** và
một điều kiện cốt lõi: **các mô hình phải sai trên những mẫu khác nhau**.

Hiểu cái này để biết *khi nào ensemble giúp ích* và *khi nào vô dụng*.

---

## Phân rã lỗi: Bias² + Variance + nhiễu

Lỗi tổng quát hoá của một mô hình tách thành ba phần:

```
E[(y − f(x))²] = Bias² + Variance + σ²_noise
```

- **Bias (độ chệch)** → mô hình **sai hệ thống** (quá đơn giản, bỏ sót quy luật). Ví dụ: đường thẳng cố fit
  dữ liệu cong.
- **Variance (phương sai)** → mô hình **quá nhạy với dữ liệu train**, đổi tập train là đổi kết quả (overfit).
- **`σ²_noise`** → nhiễu vốn có, không sửa được.

> **Nói nôm na:** Bias là "bắn lệch tâm đều đều"; Variance là "bắn tản mát tứ tung". Ensemble chủ yếu **giảm
> Variance** (gom các phát tản mát về gần tâm).

---

## Công thức ensemble giảm Variance — bóc từng mảnh

Với `M` mô hình có cùng phương sai `σ²` và **tương quan trung bình `ρ`** giữa chúng:

```
Var(f̄) = σ²/M · [ 1 + (M − 1)·ρ ]
```

- **`σ²/M`** → nếu các mô hình **độc lập**, phương sai giảm `M` lần.
- **`ρ` (rho)** → mức các mô hình **cùng sai giống nhau**. Đây là yếu tố quyết định.

Hai cực đoan:

- **`ρ → 0` (độc lập hoàn toàn):** `Var(f̄) → σ²/M` — ensemble giảm phương sai **M lần**. Tuyệt vời.
- **`ρ = 1` (giống hệt nhau):** `Var(f̄) = σ²` — ensemble **chẳng giúp gì**. Gộp 100 bản sao vẫn như 1.

> **Kết luận vàng:** *để ensemble hiệu quả, các mô hình thành phần phải sai trên những mẫu KHÁC nhau (`ρ` thấp).*

---

## So sánh đời thường

Hỏi ý kiến một quyết định:

- Hỏi **10 người độc lập, nền tảng khác nhau** → trung bình ý kiến rất đáng tin (ρ thấp).
- Hỏi **10 người cùng một phe, cùng đọc một nguồn** → họ cùng sai một kiểu → trung bình vẫn sai (ρ cao).

---

## Ví dụ SỐ

`σ² = 1`, `M = 3`:

- `ρ = 0`: `Var = 1/3 ≈ 0,33` → giảm 3 lần.
- `ρ = 0,3`: `Var = (1/3)(1 + 2·0,3) = 0,53` → vẫn giảm đáng kể.
- `ρ = 1`: `Var = (1/3)(1 + 2) = 1` → không giảm gì.

→ Muốn ensemble mạnh, phải **ép `ρ` xuống thấp** bằng cách chọn mô hình **đa dạng**.

---

## Tóm lại

- Lỗi = **Bias² + Variance + nhiễu**; ensemble chủ yếu **giảm Variance**.
- `Var(f̄) = (σ²/M)[1 + (M−1)ρ]` → chỉ giảm mạnh khi **tương quan `ρ` thấp** (các mô hình sai khác nhau).
- `ρ=1` (mô hình giống nhau) → ensemble vô dụng.

**Hiểu cái này thì làm được gì?** Bạn hiểu **điều kiện sống còn** của ensemble, và vì sao đồ án cố tình chọn
**FTT + RF + KNN** — ba mô hình có [[inductive-bias-diversity]] để `ρ` thấp. Đầu ra được ghép bằng
[[asymmetric-cost-sensitive-voting]].
