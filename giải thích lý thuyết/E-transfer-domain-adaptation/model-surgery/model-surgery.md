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

- **`W_old^emb` (k×d)** → ma trận embedding cũ của 77 đặc trưng → **cấy ghép nguyên (transplant)**: code chép
  đè `state_dict` của từng `feature_embeddings[i]` (i = 0…76) từ model cũ sang.
- **`W_newrows^emb` (Δ×d)** → `Δ = 3` hàng mới cho 3 đặc trưng NAT → **khởi tạo mới (fresh)** rồi **học trong
  fine-tuning**. Các khối Transformer, LayerNorm và classifier cũng được **chép nguyên** từ model cũ.
- Tất cả tham số còn lại của model → **không đổi**.

> **Nói đơn giản:** ghép 3 hàng mới (khởi tạo lại từ đầu), rồi để chúng học dần trong lúc fine-tune. Phần cũ
> (77 hàng + blocks + classifier) được bảo toàn.

> ⚠️ **Chính xác theo code:** 3 hàng mới dùng **init mặc định của lớp `nn.Linear(1, d)`** (xavier_uniform cho
> weight, 0 cho bias). Quyển đồ án mô tả ý tưởng khởi tạo nhỏ `N(0, 0,01)`; ở đây tinh thần là **hàng mới bắt
> đầu "trung tính", không phá phần cũ**, dù con số init cụ thể là default của PyTorch.

---

## Vì sao hàng mới nên "trung tính" lúc đầu?

Nếu 3 hàng mới mang tín hiệu quá mạnh ngay từ đầu, chúng sẽ **bơm nhiễu** vào model đã ổn định → phá kiến thức
cũ. Khởi tạo trung tính (giá trị nhỏ quanh 0) khiến 3 đặc trưng mới ban đầu **gần như vô hình**, rồi *lớn dần*
khi model thấy chúng hữu ích trong fine-tuning.

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

- **Model Surgery** mở rộng Feature Tokenizer `k → k+Δ` bằng cách **ghép thêm Δ hàng mới** (init mới, trung tính),
  **giữ nguyên** các hàng cũ (transplant).
- Nhờ mỗi đặc trưng là một hàng độc lập, việc này **không phá kiến thức đã học**.
- Trong đồ án: `77 → 80` với 3 đặc trưng NAT → MCC **0,6825 → 0,7333**.

**Hiểu cái này thì làm được gì?** Đây lại là kỹ thuật **chỉ FT-Transformer làm được** (RF/XGBoost không).
Cùng với [[layer-freezing-catastrophic-forgetting]], nó tạo nên bộ đôi thích nghi miền của đồ án.

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Transplant 77 emb + copy blocks/classifier; model 80 | `Final/03_Testbed_Retrain/retrain/domain_adaptation/3_feature_engineering_v2.py:245` |
| Chép cls_token + transformer_blocks | `Final/03_Testbed_Retrain/retrain/domain_adaptation/3_feature_engineering_v2.py:263` |

**Khi phản biện:** code copy `state_dict` 77 embedding cũ + blocks + norm + classifier; **3 embedding mới dùng init mặc định của `nn.Linear`** (không phải `N(0, 0,01)` như quyển mô tả) — nếu hỏi, làm rõ đây là init 'trung tính' để không phá phần cũ.
