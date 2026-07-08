# Layer Freezing & Catastrophic Forgetting — giữ nền, học lại phần ngọn

## Nó sinh ra để giải quyết chuyện gì?

Khi gặp [[covariate-shift]], ta muốn **fine-tune (tinh chỉnh)** model cho miền mới (Testbed). Nhưng có hai cái bẫy:

1. Testbed **rất ít dữ liệu** — train lại toàn bộ từ đầu sẽ overfit.
2. Nếu cập nhật *tất cả* tham số, model **quên sạch** kiến thức CIC đã học — gọi là
   **Catastrophic Forgetting (quên thảm hoạ)**.

**Layer Freezing (đóng băng tầng)** giải cả hai: **giữ nguyên (đóng băng) các tầng thấp**, chỉ **cập nhật các
tầng cao**. Ít tham số phải học → hợp với ít dữ liệu, và kiến thức nền được bảo toàn.

> **So sánh đời thường:** bạn đã giỏi tiếng Anh, giờ sang vùng có tiếng lóng địa phương. Bạn **giữ nguyên ngữ
> pháp nền tảng** (tầng thấp), chỉ **học lại một ít từ vựng địa phương** (tầng cao) — chứ không đi học lại
> tiếng Anh từ đầu.

---

## Vì sao phân tầng lại hợp lý?

Trong FT-Transformer, các tầng học ở **mức trừu tượng khác nhau**:

- **Tầng Attention THẤP** → học **quan hệ tổng quát**, bất biến theo môi trường: *"duration ngắn + byte thấp →
  flow ngắn"*, *"SYN cao → scan"*. Những cái này đúng ở cả CIC lẫn Testbed.
- **Tầng CAO** → học **phân biệt đặc thù miền**: *"Botnet heartbeat vs Benign idle"* — phụ thuộc phân phối CIC.

→ Khi sang Testbed: **đóng băng tầng thấp** (giữ cái tổng quát), **cập nhật tầng cao** (học lại cái đặc thù).

```
θ_fine* = argmin_{θ_fine}  L( f_{θ_freeze, θ_fine}(x_target),  y_target )
```

- **`θ_freeze`** → tham số tầng thấp, **giữ nguyên**.
- **`θ_fine`** → tham số tầng cao + head, **được cập nhật**.

---

## Đo "quên thảm hoạ": Catastrophic Forgetting

```
CF = (Acc_source_before − Acc_source_after) / Acc_source_before × 100%
```

- Đo model **tụt bao nhiêu % hiệu năng trên CIC (miền nguồn)** sau khi fine-tune cho Testbed.
- CF thấp = ít quên = giữ được kiến thức cũ.

**Kết quả đồ án:** đóng băng **2/4 tầng** → **CF = 0,61%** → vẫn giữ **99,39%** hiệu năng CIC.
Đây là điểm cân bằng **plasticity (dẻo — học cái mới) ↔ stability (ổn — nhớ cái cũ)**.

> **Nói đơn giản:** học thêm giọng địa phương mà gần như không quên tiếng Anh gốc (chỉ rơi 0,61%).

---

## Ví dụ trực giác

- Đóng băng **0 tầng** (train hết): học Testbed tốt nhưng **quên CIC nhiều** (CF cao).
- Đóng băng **cả 4 tầng** (chỉ chỉnh head): nhớ CIC nhưng **học Testbed kém** (quá cứng).
- Đóng băng **2/4 tầng**: điểm ngọt — nhớ CIC (CF 0,61%) *và* thích nghi Testbed.

---

## Tóm lại

- **Layer Freezing:** đóng băng tầng thấp (kiến thức tổng quát), chỉ cập nhật tầng cao (đặc thù miền) → hợp
  khi ít dữ liệu và tránh quên.
- **Catastrophic Forgetting** đo bằng `CF` = % tụt hiệu năng miền nguồn; đóng băng 2/4 tầng → **CF = 0,61%**.
- Là cách cân bằng **plasticity ↔ stability**.

**Hiểu cái này thì làm được gì?** Đây là kỹ thuật **không thể làm với Random Forest/XGBoost** — một lý do
đồ án chọn FT-Transformer ([[multi-head-self-attention]]). Thường đi kèm [[model-surgery]] để thêm đặc trưng mới.
