# Đa dạng Inductive Bias (FTT + RF + KNN) — sai khác nhau nên bù được cho nhau

## Nó sinh ra để giải quyết chuyện gì?

[[bias-variance-ensemble]] cho ta **điều kiện vàng**: ensemble chỉ mạnh khi các mô hình **sai trên những mẫu
khác nhau** (tương quan `ρ` thấp). Câu hỏi thực tế: **làm sao đảm bảo chúng sai khác nhau?**

Câu trả lời của đồ án: chọn ba mô hình có **inductive bias (thiên kiến quy nạp)** hoàn toàn khác nhau —
**FT-Transformer + Random Forest + KNN**. "Inductive bias" là *giả định ngầm về cách dữ liệu vận hành* mà mỗi
thuật toán mang theo; giả định khác nhau → cách nhìn khác nhau → **sai ở những chỗ khác nhau**.

> **So sánh đời thường:** giao một vụ án cho **ba chuyên gia soi ba kiểu**: người soi tài chính, người soi thời
> gian, người soi hành vi. Họ **sai ở những chỗ khác nhau**, nên gộp lại thì che được điểm mù của nhau.

---

## Ba inductive bias, ba kiểu sai

| Mô hình | Inductive bias | Sai trên mẫu nào |
|---|---|---|
| **FT-Transformer** | Học **tương tác đặc trưng** qua Attention — góc nhìn **toàn cục** | Mẫu có tương tác phức tạp, không nhất quán trong train |
| **Random Forest** (150 cây, depth 25) | **Phân vùng** không gian đặc trưng — góc nhìn **cục bộ** | Mẫu gần biên quyết định phức tạp ở chiều cao |
| **KNN** (K=16, distance-weighted) | **Lân cận** — học lười (lazy), dựa vào hàng xóm gần | Mẫu ở vùng thưa, xa các điểm train |

Ba cách nhìn khác nhau về căn bản → ba tập mẫu-sai khác nhau → **`ρ` thấp** → [[bias-variance-ensemble]] phát huy.

---

## Vì sao KHÔNG chọn ba model giống nhau?

Nếu ghép FTT + FTT + FTT (chỉ khác seed), cả ba có **cùng inductive bias** → cùng sai một kiểu → `ρ` cao →
ensemble gần như vô ích (theo đúng công thức `Var(f̄) = σ²` khi `ρ=1`).

> **Nói đơn giản:** muốn hội đồng khôn ngoan, đừng mời ba người **suy nghĩ y hệt nhau**.

---

## Ví dụ trực giác

Một flow Botnet nằm ở **vùng thưa** (ít mẫu tương tự trong train):

- **KNN** dễ sai (không có hàng xóm gần đáng tin).
- Nhưng **FTT** có thể vẫn đúng nhờ bắt được **tương tác đặc trưng** đặc thù Botnet.
- → Ensemble lấy được cái đúng của FTT, bù cho cái sai của KNN.

Ngược lại, ở một mẫu có tương tác rối mà FTT bối rối, **RF phân vùng cục bộ** lại có thể bắt đúng.

---

## Tóm lại

- **Inductive bias** = giả định ngầm của mỗi thuật toán về dữ liệu. Khác nhau → sai khác nhau.
- Đồ án chọn **FTT (toàn cục) + RF (cục bộ) + KNN (lân cận)** để đảm bảo **`ρ` thấp** → ensemble giảm variance thật.
- Ghép các model giống nhau (`ρ` cao) thì vô ích.

**Hiểu cái này thì làm được gì?** Bạn biết **cách thiết kế ensemble đúng** — không phải cứ gộp nhiều model, mà
phải gộp model **đa dạng**. Đây là cầu nối giữa lý thuyết [[bias-variance-ensemble]] và luật gộp
[[asymmetric-cost-sensitive-voting]].

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Train 3 model khác bias (FTT/RF/KNN) | `Final/02_CIC_IDS_2017/src/training/scripts_v7/phase2_train_v7_stage2_ensemble.py` |

**Khi phản biện:** FTT (Attention – toàn cục) + RandomForest (cây – cục bộ) + KNN (lân cận – lazy): ba bias khác nhau được chọn **có chủ đích** để ép ρ thấp.
