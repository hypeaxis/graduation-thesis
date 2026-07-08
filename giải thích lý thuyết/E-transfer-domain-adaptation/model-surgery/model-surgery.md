# Model Surgery — "ghép thêm ngăn kéo" cho model không phá đồ cũ

## Nó sinh ra để giải quyết chuyện gì?

Sang Testbed, ta phát hiện cần **3 đặc trưng mới** đặc thù cho môi trường NAT (IAT_CV, Bwd_Pkt_Ratio,
Pkt_Size_Ratio) để phân biệt tốt hơn. Nhưng model cũ được huấn luyện với đúng **77 đặc trưng**.

Câu hỏi: làm sao **mở rộng 77 → 80 đặc trưng** mà **không vứt bỏ toàn bộ kiến thức đã học**?

**Model Surgery (phẫu thuật mô hình)** là câu trả lời: nhờ [[feature-tokenizer]] coi **mỗi đặc trưng là một
hàng độc lập** trong ma trận embedding, ta chỉ cần **ghép thêm hàng mới**, giữ nguyên các hàng cũ.

> **So sánh đời thường:** như **ghép thêm 3 ngăn kéo mới** vào một cái tủ — đồ đạc trong các ngăn cũ vẫn y
> nguyên, chỉ có 3 ngăn mới còn trống chờ sắp đồ.

---

## Công thức — bóc từng mảnh

```
W_new^emb = [ W_old^emb  ∈ ℝ^{k×d}      ]   ∈ ℝ^{(k+Δ)×d}
           [ W_newrows^emb ∈ ℝ^{Δ×d}    ]
```

- **`W_old^emb` (k×d)** → ma trận embedding cũ của 77 đặc trưng → **giữ nguyên (transplant — cấy ghép)**.
- **`W_newrows^emb` (Δ×d)** → `Δ = 3` hàng mới cho 3 đặc trưng NAT → **khởi tạo nhỏ** `N(0, 0,01)`, rồi
  **học trong fine-tuning**.
- Tất cả tham số còn lại của model → **không đổi**.

> **Nói đơn giản:** ghép 3 hàng mới (gần như bằng 0 lúc đầu để không gây sốc), rồi để chúng học dần trong lúc
> fine-tune. Phần cũ được bảo toàn.

---

## Vì sao khởi tạo N(0, 0.01) mà không random lớn?

Nếu 3 hàng mới khởi tạo giá trị lớn, chúng sẽ **bơm nhiễu mạnh** vào model đã ổn định → phá kiến thức cũ.
Khởi tạo **gần 0** (độ lệch chuẩn 0,01) khiến 3 đặc trưng mới ban đầu **gần như vô hình**, rồi *lớn dần* khi
model thấy chúng hữu ích.

> **So sánh:** người mới vào đội thì **quan sát trước, phát biểu sau** — không xông vào làm loạn ngay.

---

## Ví dụ SỐ — kết quả trong đồ án

Áp dụng Model Surgery **sau** [[layer-freezing-catastrophic-forgetting]]:

| Bước | MCC |
|---|---|
| Sau Layer Freezing | 0,6825 |
| **+ Model Surgery (77→80)** | **0,7333** |

→ Thêm 3 đặc trưng NAT đúng chỗ giúp MCC tăng **+0,05** — bằng chứng các đặc trưng mới thực sự mang thông tin
phân biệt mà 77 đặc trưng gốc thiếu.

---

## Tóm lại

- **Model Surgery** mở rộng Feature Tokenizer `k → k+Δ` bằng cách **ghép thêm Δ hàng mới** (init `N(0,0.01)`),
  **giữ nguyên** các hàng cũ (transplant).
- Nhờ mỗi đặc trưng là một hàng độc lập, việc này **không phá kiến thức đã học**.
- Trong đồ án: `77 → 80` với 3 đặc trưng NAT → MCC **0,6825 → 0,7333**.

**Hiểu cái này thì làm được gì?** Đây lại là kỹ thuật **chỉ FT-Transformer làm được** (RF/XGBoost không).
Cùng với [[layer-freezing-catastrophic-forgetting]], nó tạo nên bộ đôi thích nghi miền của đồ án.
