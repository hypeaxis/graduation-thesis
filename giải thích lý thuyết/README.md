# 📚 Giải thích lý thuyết đồ án — kiểu "Tự học"

Toàn bộ lý thuyết dùng trong quyển đồ án, giải thích theo phong cách **"trực giác trước, công thức sau"**.
Mỗi lý thuyết là một folder gồm:

- `*.md` — bản văn bản đầy đủ (vấn đề → ý tưởng → công thức bóc mảnh → ví dụ số → tóm lại)
- `infographic.html` — nguồn infographic (mở bằng trình duyệt)
- `infographic.png` — ảnh infographic độ phân giải cao (chèn thẳng vào luận văn/slide)

## Trang tổng hợp để đọc lại nhanh

- Link mở trực tiếp trang tổng hợp: [_theory_hub/index.html](./_theory_hub/index.html)
- Nếu đang đọc README trong VS Code, chỉ cần **Ctrl + Click** vào link trên để mở file.
- Nếu mở thư mục bằng File Explorer, có thể vào folder `_theory_hub` rồi mở file `index.html` bằng trình duyệt.
- Mỗi thẻ lý thuyết trong hub sẽ mở ra **một trang 2 cột**:
	- bên trái là **bản văn bản** render từ file `*.md`
	- bên phải là **infographic** lấy từ `infographic.html` và `infographic.png`
- Toàn bộ code tạo trang này nằm ngay trong folder này: `build_theory_hub.py`

### Cách sử dụng hub

1. Mở [_theory_hub/index.html](./_theory_hub/index.html).
2. Dùng ô **tìm kiếm** ở cột trái để lọc nhanh theo tên lý thuyết, ví dụ: `focal loss`, `model surgery`, `snort`.
3. Bấm vào một thẻ lý thuyết để vào trang chi tiết.
4. Ở trang chi tiết:
	 - cột trái là phần đọc lại lý thuyết dạng văn bản
	 - cột phải là infographic để xem song song
	 - có các nút mở nhanh `markdown gốc`, `infographic.html`, `infographic.png`

### Tái sinh trang tổng hợp sau khi sửa nội dung

Chạy trong thư mục `giải thích lý thuyết`:

```powershell
python .\build_theory_hub.py
```

> **29 lý thuyết**, chia 7 phần theo mạch từ *đặc trưng đầu vào → kiến trúc → xử lý mất cân bằng → thích nghi
> miền → ensemble → hệ lai & giới hạn*.

---

## A. Nền tảng bài toán & dữ liệu
1. [IDS = phân loại có giám sát trên flow](A-problem-and-data/ids-supervised-flow-classification/ids-supervised-flow-classification.md)
2. [Trích đặc trưng flow bằng CICFlowMeter](A-problem-and-data/flow-features-cicflowmeter/flow-features-cicflowmeter.md)
3. [Mất cân bằng & chỉ số Macro-F1, MCC](A-problem-and-data/class-imbalance-metrics/class-imbalance-metrics.md)

## B. FT-Transformer (kiến trúc lõi)
4. [Feature Tokenizer](B-ft-transformer/feature-tokenizer/feature-tokenizer.md)
5. [Multi-Head Self-Attention](B-ft-transformer/multi-head-self-attention/multi-head-self-attention.md)
6. [Transformer Block & FFN](B-ft-transformer/transformer-block-ffn/transformer-block-ffn.md)

## C. Tiền xử lý
7. [PowerTransformer Yeo-Johnson](C-preprocessing/yeo-johnson-power-transform/yeo-johnson.md)
8. [Lọc tương quan Pearson](C-preprocessing/pearson-correlation-filter/pearson-correlation-filter.md)

## D. Xử lý mất cân bằng
9. [Cross-Entropy](D-imbalance-handling/cross-entropy/cross-entropy.md)
10. [Focal Loss](D-imbalance-handling/focal-loss/focal-loss.md)
11. [Class-Balanced Focal Loss](D-imbalance-handling/class-balanced-focal-loss/class-balanced-focal-loss.md)
12. [SMOTE & SMOTE-ENN](D-imbalance-handling/smote-smote-enn/smote-smote-enn.md)
13. [Weighted Random Sampling](D-imbalance-handling/weighted-random-sampling/weighted-random-sampling.md)
14. [Label Smoothing](D-imbalance-handling/label-smoothing/label-smoothing.md)

## E. Học chuyển giao & thích nghi miền
15. [Covariate Shift](E-transfer-domain-adaptation/covariate-shift/covariate-shift.md)
16. [Layer Freezing & Catastrophic Forgetting](E-transfer-domain-adaptation/layer-freezing-catastrophic-forgetting/layer-freezing-catastrophic-forgetting.md)
17. [Model Surgery](E-transfer-domain-adaptation/model-surgery/model-surgery.md)
18. [Scaler–Embedding Coupling (Re-fit Scaler thất bại)](E-transfer-domain-adaptation/scaler-embedding-coupling/scaler-embedding-coupling.md)

## F. Ensemble & hệ thống
19. [Two-Stage Cascade (Gating + Expert)](F-ensemble-and-system/two-stage-cascade-gating-expert/two-stage-cascade-gating-expert.md)
20. [Autoencoder Gate + ngưỡng tái tạo](F-ensemble-and-system/autoencoder-gate-threshold/autoencoder-gate-threshold.md)
21. [Stacking Ensemble](F-ensemble-and-system/stacking-ensemble/stacking-ensemble.md)
22. [Bias–Variance & Ensemble giảm Variance](F-ensemble-and-system/bias-variance-ensemble/bias-variance-ensemble.md)
23. [Đa dạng Inductive Bias (FTT+RF+KNN)](F-ensemble-and-system/inductive-bias-diversity/inductive-bias-diversity.md)
24. [Asymmetric / Cost-sensitive Voting](F-ensemble-and-system/asymmetric-cost-sensitive-voting/asymmetric-cost-sensitive-voting.md)

## G. Hệ lai & giới hạn
26. [Snort + FT-Transformer (hệ lai)](G-hybrid-and-limits/snort-hybrid-ids/snort-hybrid-ids.md)
27. [Alert Aggregator](G-hybrid-and-limits/alert-aggregator/alert-aggregator.md)
28. [PortScan không phân tách dưới NAT](G-hybrid-and-limits/portscan-inseparability-nat/portscan-inseparability-nat.md)

---

## 4 trụ cột chính khi bảo vệ

| Trụ | Lý thuyết cốt lõi |
|---|---|
| **Kiến trúc** | FT-Transformer (4–6) |
| **Mất cân bằng** | Focal / CB-Focal / SMOTE / Sampling (9–14) |
| **Thích nghi miền** | Covariate Shift → Layer Freezing → Model Surgery (15–18) |
| **Ensemble + hệ lai** | Bias-Variance, Asymmetric Voting, HNM, Snort (19–27) |

*Để tạo PNG khổ in: mở `infographic.html` trong trình duyệt → Ctrl+P → Save as PDF.*
