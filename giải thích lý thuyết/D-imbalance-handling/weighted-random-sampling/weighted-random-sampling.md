# Weighted Random Sampling — "bốc thăm thiên vị" lớp hiếm

## Nó sinh ra để giải quyết chuyện gì?

Còn một cách nữa để chống mất cân bằng, khác cả loss ([[focal-loss]]) lẫn tạo mẫu ([[smote-smote-enn]]):
**thay đổi tần suất mỗi mẫu được đưa vào batch huấn luyện**.

Thay vì bốc mẫu đều nhau (lớp đông xuất hiện nhiều, lớp hiếm hầu như vắng mặt), **Weighted Random Sampling**
cho **mỗi mẫu một trọng số** để lớp hiếm được **bốc ra thường xuyên hơn**, cân bằng lại mỗi epoch.

> **So sánh đời thường:** như hòm phiếu bốc thăm có thiên vị — lớp hiếm được bỏ vào **nhiều vé hơn**, nên khi
> rút, nó xuất hiện đều đặn thay vì bị lớp đông lấn át.

---

## Công thức — bóc từng mảnh

Trọng số cơ bản theo tần suất nghịch:

```
w_i = N / (K · n_c)
```

- **`N`** → tổng số mẫu.
- **`K`** → số lớp.
- **`n_c`** → số mẫu của lớp chứa mẫu i.

→ Lớp càng ít mẫu (`n_c` nhỏ) → trọng số `w_i` càng lớn → càng hay được bốc.

**Biến thể "làm mượt" dùng trong V8.5** (tránh trọng số cực đoan):

```
w_i = √( N / (K · n_c) ) ,   rồi clip về [0,5 ; 2,0]
```

- **`√(…)`** → khai căn để **nén** khoảng cách trọng số (lớp siêu hiếm không nhảy vọt quá đà).
- **`clip [0,5; 2,0]`** → chặn trên/dưới, không cho mẫu nào bị bốc quá nhiều hay quá ít.

> **Nói đơn giản:** vẫn thiên vị lớp hiếm, nhưng **có chừng mực** — không để nó xuất hiện áp đảo đến mức model
> quên mất lớp đông trông thế nào.

---

## Khác gì Focal Loss?

| | Weighted Sampling | Focal Loss |
|---|---|---|
| Can thiệp vào | **Dữ liệu** model *nhìn thấy* (tần suất) | **Loss** (trọng số gradient mỗi mẫu) |
| Cơ chế | Bốc lớp hiếm ra nhiều hơn | Hạ trọng số mẫu dễ |
| Có thể **kết hợp** | ✔ | ✔ |

> Hai cái **không loại trừ nhau** — đồ án dùng phối hợp: sampling để lớp hiếm có mặt, Focal để trong batch đó
> mẫu khó được ưu tiên.

---

## Ví dụ trực giác

Batch 256 mẫu, bốc đều: có thể **0 mẫu Heartbleed** (vì nó chỉ chiếm 0,0004%). Với weighted sampling, Heartbleed
được nhân trọng số lớn → gần như batch nào cũng có vài mẫu → model **thực sự được nhìn** nó để học.

---

## Tóm lại

- Weighted Random Sampling cho **mỗi mẫu một trọng số** (`w_i = N/(K·n_c)`) để **lớp hiếm được bốc ra nhiều hơn**.
- Biến thể V8.5 **khai căn + clip [0,5; 2,0]** để thiên vị *có chừng mực*, tránh cực đoan.
- Can thiệp ở **tầng dữ liệu**, bổ sung (không thay thế) [[focal-loss]] ở tầng loss.

**Hiểu cái này thì làm được gì?** Bạn phân biệt được **ba tầng chống mất cân bằng** — dữ liệu (sampling/SMOTE),
loss (Focal/CB), và boundary (khai thác mẫu khó ở biên quyết định) — và biết chúng phối hợp thế nào trong đồ án.

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| WeightedRandomSampler (w = 1/class_counts) | `Final/01_NSL_KDD/src/training/train_ft_transformer_nslkdd.py:289` |
| Biến thể V8.5 (√ + clip) | `Final/03_Testbed_Retrain/retrain/v8/v8.5_Combined/v8_5_train.py` |

**Khi phản biện:** NSL-KDD dùng inverse-frequency đơn giản (`1/class_counts`); V8.5 dùng biến thể **làm mượt (√) + clip [0,5; 2,0]**.
