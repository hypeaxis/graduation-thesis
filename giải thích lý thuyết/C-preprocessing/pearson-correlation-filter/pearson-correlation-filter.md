# Lọc tương quan Pearson — bỏ bớt đặc trưng "kể chuyện trùng nhau"

## Nó sinh ra để giải quyết chuyện gì?

CICFlowMeter cho **77 đặc trưng**, nhưng nhiều cái **nói gần như cùng một điều**. Ví dụ `Flow_Bytes/s` và
`Flow_Packets/s` thường lên xuống cùng nhau; giữ cả hai chẳng thêm thông tin mà chỉ **tăng chiều, thêm nhiễu,
train chậm** — đặc biệt hại cho Expert Network vốn cần gọn.

**Lọc tương quan Pearson** giải quyết: đo mức "đi cùng nhau" của từng cặp đặc trưng, nếu **quá giống** thì
**bỏ bớt một cái**.

> **So sánh đời thường:** hai nhân chứng kể lại vụ việc **y hệt nhau** → chỉ cần nghe một người là đủ. Nghe
> cả hai không thêm thông tin, chỉ **tốn thời gian và gây rối**.

---

## Hệ số Pearson — bóc từng mảnh

```
r(X, Y) = Cov(X, Y) / (σ_X · σ_Y)
```

- **`Cov(X, Y)`** → hiệp phương sai: X và Y có xu hướng **cùng tăng/cùng giảm** không.
- **`σ_X, σ_Y`** → độ lệch chuẩn, để chuẩn hoá về khoảng cố định.
- **`r`** → nằm trong **[−1, +1]**:
  - `r = +1`: đi cùng nhau hoàn hảo (một tăng, kia tăng y hệt).
  - `r = 0`: không liên quan tuyến tính.
  - `r = −1`: ngược nhau hoàn hảo.

> **Nói đơn giản:** `r` đo "hai cột này có kể chung một câu chuyện không". `|r|` càng gần 1 càng trùng lặp.

---

## Luật lọc trong đồ án

```
Nếu |r| > 0,95 giữa hai đặc trưng  →  bỏ đi MỘT trong hai
```

- Ngưỡng **0,95** = "gần như trùng". Cặp nào vượt ngưỡng → giữ một, bỏ một.
- Kết quả: **77 → 34 đặc trưng** cho **Expert Network**.

**Điểm tinh tế:** **KHÔNG lọc cho Gating Network** — Gating giữ **đầy đủ 77 đặc trưng**.

---

## Vì sao Expert lọc mà Gating thì không?

- **Gating** làm bài toán **nhị phân đơn giản** ("đáng ngờ không?") — cần **tín hiệu đầy đủ**, kể cả dư một chút
  cũng không sao, và không nên bỏ sót manh mối lọc tấn công.
- **Expert** làm bài toán **9 lớp tinh vi** trên chỉ ~17,3% traffic — **giảm chiều** giúp gradient tập trung,
  bớt overfit, học phân biệt tấn công sắc nét hơn. Xem [[two-stage-cascade-gating-expert]].

> **Nói nôm na:** người gác cổng cần nghe hết mọi tiếng động; chuyên gia phân tích thì cần bàn làm việc gọn gàng.

---

## Ví dụ trực giác

Cặp `Flow_Bytes/s` ↔ `Flow_Packets/s` có `r = 0,97 > 0,95` → bỏ một. Model mất gần như **0 thông tin** (vì cái
còn lại đã "kể" gần hết), nhưng **giảm được một chiều** → nhẹ và ổn định hơn.

---

## Tóm lại

- **Pearson `r`** đo mức hai đặc trưng "đi cùng nhau" (`[−1,1]`); `|r|` gần 1 = trùng lặp.
- Đồ án bỏ đặc trưng có **`|r| > 0,95`** → **77 → 34** cho **Expert**; **giữ đủ 77 cho Gating**.
- Giảm chiều → bớt nhiễu, bớt overfit, train nhanh, gradient tập trung.

**Hiểu cái này thì làm được gì?** Bạn giải thích được một **quyết định thiết kế tinh tế** (lọc cho Expert nhưng
không cho Gating) và hiểu vì sao Expert dùng cấu hình nhỏ (`d=64`). Gắn với [[yeo-johnson-power-transform]]
(cùng nằm ở bước tiền xử lý).

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Chọn đặc trưng (RandomForest importance) | `Final/01_NSL_KDD/src/data_processing/feature_selection.py` |
| Tập 34 đặc trưng của Expert (CIC) | `Final/02_CIC_IDS_2017/src/training/scripts_v7/phase2_train_v7_stage2_ensemble.py:74` |

**Khi phản biện:** quyển đồ án mô tả **lọc Pearson r > 0,95 (77→34)**; trong code, tập **34 đặc trưng Expert** được định nghĩa tường minh, còn `feature_selection.py` (NSL-KDD) chọn theo **importance**. Nên làm rõ đúng cơ chế lọc khi bị hỏi.
