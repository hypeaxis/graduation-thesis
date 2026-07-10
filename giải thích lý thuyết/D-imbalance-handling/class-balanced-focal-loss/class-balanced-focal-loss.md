# Class-Balanced Focal Loss — cân trọng số theo "số mẫu hữu hiệu"

## Nó sinh ra để giải quyết chuyện gì?

[[focal-loss]] có phần `α_t` để cân giữa các lớp. Câu hỏi: **đặt `α` cho mỗi lớp bằng bao nhiêu?**

Cách ngây thơ là **nghịch đảo tần suất** `α_c = 1/n_c` (lớp ít mẫu → trọng số lớn). Nhưng khi một lớp cực hiếm
(Heartbleed chỉ **10 mẫu**), `1/n_c` **bùng nổ**, tạo trọng số cực đoan làm mất ổn định huấn luyện.

**Class-Balanced Focal Loss** (Cui et al., 2019) sửa chỗ này bằng ý tưởng **"số mẫu hữu hiệu (effective number)"**:
thêm một mẫu vào lớp đã đông thì *gần như vô ích* (nó trùng lặp thông tin), nên đừng tính đủ 1.

> **Nói nôm na:** mẫu thứ 1.000.000 của Benign chẳng dạy model điều gì mới; còn mẫu thứ 5 của Heartbleed thì
> quý như vàng. Công thức này phản ánh đúng cái "độ quý" giảm dần đó.

---

## Công thức — bóc từng mảnh

```
α_c = (1 − β) / (1 − β^{n_c}) ,   β = 0,9999
```

- **`n_c`** → số mẫu của lớp c.
- **`β` (beta)** → hằng số gần 1, điều khiển mức "bão hoà" (mẫu mới đóng góp giảm dần nhanh cỡ nào).
- **`β^{n_c}`** → khi `n_c` lớn thì số này → 0; khi `n_c` nhỏ thì → gần 1.

Xét hai cực:

- **Lớp đông** (Benign, hàng triệu mẫu): `β^{n_c} → 0` ⇒ `α_c → 1−β = 0,0001` — **rất nhỏ**.
- **Lớp hiếm** (Heartbleed, 10 mẫu): `β^{10} ≈ 0,999` ⇒ `α_c → (1−β)/(1−β) = 1` — **chạm trần**.

> **Điểm hay:** `α_c` có **trần tự nhiên tại 1** — không bao giờ nổ lên vô cực như `1/n_c`. Ổn định hơn hẳn
> khi tỷ lệ lớp chênh **>1000:1**.

---

## Ví dụ SỐ: so với nghịch đảo tần suất

| Lớp | $n_c$ | $1/n_c$ (ngây thơ) | CB-alpha (β=0,9999) |
|---|---|---|---|
| Benign | 2.300.000 | 0,00000043 | 0,0001 |
| DoS | 250.000 | 0,000004 | 0,0001 |
| Heartbleed | 10 | **0,1** | **≈ 1,0** |

Với `1/n_c`, khoảng cách trọng số Benign↔Heartbleed lên tới **~230.000 lần** → dễ gây "sốc" gradient.
CB-alpha nén khoảng cách đó về mức lành mạnh, có **trần** rõ ràng.

---

## Tóm lại

- CB-Focal đặt `α_c = (1−β)/(1−β^{n_c})` dựa trên **số mẫu hữu hiệu** — mẫu thêm vào lớp đông có giá trị giảm dần.
- Kết quả: trọng số lớp hiếm **chạm trần 1**, không bùng nổ như `1/n_c` → **ổn định** khi lệch >1000:1.

**Hiểu cái này thì làm được gì?** Bạn giải thích được vì sao đồ án chọn CB-alpha thay vì nghịch đảo tần suất —
một chi tiết nhỏ nhưng quyết định độ ổn định khi train với Heartbleed chỉ 10 mẫu. Gắn với [[focal-loss]].

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Tham số β = 0,9999 (effective number) | `Final/01_NSL_KDD/src/training/train_ft_transformer_nslkdd.py:57` |
| α theo effective number → nạp vào FocalLoss | `Final/01_NSL_KDD/src/training/train_ft_transformer_nslkdd.py` |

**Khi phản biện:** `--class-balanced-beta` mặc định **0.9999** đúng như lý thuyết; α có trần tại 1 nên không nổ khi lớp cực hiếm.
