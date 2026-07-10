# Cross-Entropy Loss — và vì sao nó "đuối" khi dữ liệu lệch

## Nó sinh ra để giải quyết chuyện gì?

Khi model phân loại, ta cần một cách **đo model sai bao nhiêu** để mà sửa. **Cross-Entropy (CE — entropy chéo)**
là hàm mất mát (loss) tiêu chuẩn cho bài toán phân loại: nó phạt nặng khi model **tự tin nhưng sai**.

Hiểu CE là bước đệm bắt buộc để hiểu vì sao đồ án phải chuyển sang **Focal Loss** ([[focal-loss]]).

---

## Công thức — bóc từng mảnh

```
L_CE = − Σ_c  y_c · log(ŷ_c)
```

- **`y_c`** → nhãn đúng (1 nếu đúng lớp c, 0 nếu không) — dạng one-hot.
- **`ŷ_c`** → xác suất model dự đoán cho lớp c.
- **`log(ŷ_c)`** → càng đoán đúng với xác suất cao thì `log` càng gần 0 (loss nhỏ); đoán sai/tự tin bậy thì
  `log` âm sâu (loss lớn).

Vì `y` one-hot, tổng rút gọn còn: `L_CE = −log(p_t)`, với **`p_t`** = xác suất model gán cho **nhãn đúng**.

> **Nói nôm na:** loss = "mức ngạc nhiên". Model gán 0,95 cho đáp án đúng → ít ngạc nhiên (loss 0,05).
> Gán 0,01 cho đáp án đúng → sốc nặng (loss 4,6).

---

## Vấn đề chí mạng: gradient bị lớp đông nuốt

Xét một batch: **1000 mẫu Benign dễ** (`p_t = 0,95`) và **10 mẫu BruteForce khó** (`p_t = 0,4`).

```
Tổng gradient Benign     ∝ 1000 × (−log 0,95) ≈ 1000 × 0,051 = 51
Tổng gradient BruteForce ∝ 10   × (−log 0,40) ≈ 10   × 0,916 = 9,16
```

Kết quả đau lòng: **dù mỗi mẫu BruteForce gánh gradient lớn hơn 18× mỗi mẫu Benign**, nhưng vì Benign đông
gấp 100 lần, **tổng gradient Benign vẫn áp đảo 5,6:1**.

→ Model bị kéo liên tục về phía "làm tốt Benign", **ít cơ hội học lớp thiểu số**.

> **So sánh đời thường:** một lớp học có 1000 em đã giỏi cứ rì rầm khoe điểm, át hết tiếng 10 em đang thật sự
> cần thầy kèm. Thầy (model) bị cuốn theo số đông, bỏ quên nhóm cần nhất.

---

## Ví dụ SỐ trực quan

| Mẫu | $p_t$ | gradient/mẫu | × số lượng | Tổng |
|---|---|---|---|---|
| Benign (1000) | 0,95 | 0,051 | ×1000 | **51** |
| BruteForce (10) | 0,40 | 0,916 | ×10 | **9,16** |

Tỷ lệ đóng góp **BruteForce : Benign = 1 : 5,6** → sai hướng ta mong muốn (ta muốn model *chú ý hơn* vào lớp hiếm).

---

## Tóm lại

- Cross-Entropy = `−log(p_t)`, phạt theo "mức ngạc nhiên" khi đoán sai nhãn đúng.
- **Điểm yếu:** khi dữ liệu lệch, **rất nhiều mẫu dễ của lớp đông** cộng dồn gradient, **át** lớp hiếm
  (Benign áp đảo BruteForce 5,6:1 dù mỗi mẫu hiếm quan trọng hơn).

**Hiểu cái này thì làm được gì?** Bạn thấy rõ *gốc rễ* của vấn đề mất cân bằng nằm ở **gradient**, từ đó hiểu
vì sao [[focal-loss]] (thêm hệ số hạ trọng số mẫu dễ) lại là liều thuốc đúng bệnh — chứ không phải cứ đổi
kiến trúc model.

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| CE = trường hợp γ=0 của FocalLoss | `Final/01_NSL_KDD/src/models/phase2_ft_transformer.py:10` |
| log_softmax + gather(log_pt) | `Final/01_NSL_KDD/src/models/phase2_ft_transformer.py:31` |

**Khi phản biện:** code dùng `log_softmax` nội bộ (ổn định số học); `p_t` lấy bằng `gather` tại nhãn đúng — đúng như phân tích gradient.
