# Roadmap Kỹ Thuật: Khắc Phục Concept Drift cho FT-Transformer IDS

> File này dùng để giao cho coding agent thực hiện tuần tự. Mỗi giai đoạn có: Mục tiêu, Input cần thiết, Các bước thực hiện, Output kỳ vọng, và Tiêu chí hoàn thành (DoD). Agent PHẢI dừng lại hỏi người dùng nếu thiếu input bắt buộc — không được đoán bừa cấu trúc code hoặc tham số.

## 0. Bối cảnh (đã xác nhận qua thực nghiệm)

- Model: FT-Transformer custom PyTorch, train trên CIC-IDS-2017 (num_layers=4, num_heads=8, d_model=128, AdamW, Dropout).
- Baseline gốc trên Testbed nội bộ (Slowloris-Python qua WSL/NAT): Accuracy 21.93%, Recall(Malicious) = 0.218.
- **Thử nghiệm 1 (đã chạy):** Re-fit PowerTransformer trực tiếp trên Testbed → Accuracy SỤT xuống 6.87%, Recall(Malicious) = 0.0673.
  - Nguyên nhân xác nhận: re-fit scaler trên domain lệch lớp cực đoan (37 Benign / 22,672 Malicious) làm tâm phân phối (mean=0) dịch theo cụm Malicious-Slowloris, vô tình trùng với vùng không gian mà model gốc học là "Benign".
  - **Quyết định:** Scaler gốc (fit trên CIC-IDS-2017) PHẢI được giữ nguyên, không re-fit. Dùng `joblib`/pickle hiện có, không tạo scaler mới ở các bước sau.
- Dữ liệu Testbed hiện có: 37 Benign, 22,672 Malicious (rất mất cân bằng, mẫu Benign quá ít để đánh giá Precision đáng tin cậy).

## 1. Nguyên tắc bắt buộc cho toàn bộ roadmap (Agent phải tuân thủ tuyệt đối)

1. **Không re-fit PowerTransformer/Scaler** trên dữ liệu Testbed dưới bất kỳ hình thức nào ở các bước tiếp theo.
2. **Không train từ đầu (from scratch)** — chỉ fine-tune từ checkpoint CIC-IDS-2017 đã có.
3. Mọi lần đánh giá phải báo cáo đủ: Confusion Matrix dạng số tuyệt đối, Accuracy, Precision/Recall/F1 theo từng lớp, **Balanced Accuracy**, **Matthews Correlation Coefficient (MCC)**. Không chỉ dùng Accuracy/weighted-avg vì lệch lớp cực đoan.
4. Mọi script đánh giá phải tách riêng kết quả trên: (a) tập test CIC-IDS-2017 gốc (kiểm tra catastrophic forgetting), (b) tập Testbed.
5. Đặt tên file tiếp theo theo số thứ tự: `2_finetune_freeze.py`, `3_domain_alignment.py`, v.v. để giữ mạch thực nghiệm có thể trace lại cho báo cáo.
6. Mỗi script phải log ra file `results/expN_<tên>.json` chứa toàn bộ metrics + timestamp + config dùng, để tổng hợp bảng so sánh cuối báo cáo.

## 2. Câu hỏi Agent PHẢI hỏi người dùng trước khi viết code (chưa có câu trả lời)

- [ ] Source code class FT-Transformer (`__init__` + `forward`), đặc biệt cách khai báo các attention block (`nn.ModuleList`? tên attribute là gì?).
- [ ] Đoạn code load checkpoint hiện tại (`torch.load` + khởi tạo model + `load_state_dict`).
- [ ] Optimizer/loss setup gốc (loss function, có `class weight` chưa, lr/weight_decay của lần train CIC-IDS-2017).
- [ ] Đường dẫn dữ liệu: file CIC-IDS-2017 đã xử lý, file Testbed đã xử lý, file scaler `.pkl`/`.joblib` gốc.
- [ ] Phần cứng khả dụng (GPU/CPU, VRAM) để quyết định batch size hợp lý.

**Nếu thiếu bất kỳ mục nào ở trên, Agent dừng lại và hỏi — không tự suy đoán tên attribute hoặc cấu trúc dữ liệu.**

---

## GIAI ĐOẠN 1 — Layer Freezing Fine-Tuning (ưu tiên cao nhất, làm trước)

### Mục tiêu
Fine-tune nhẹ phần cuối model để thích nghi với domain Testbed mà không phá vỡ representation tổng quát đã học từ CIC-IDS-2017.

### Bước 1.1 — Audit kiến trúc
- Đọc class FT-Transformer, liệt kê chính xác tên các module con (embedding layer, 4 attention block, classification head).
- Xác định: 4 block attention có phải là list đồng nhất (`nn.ModuleList`) hay 4 layer riêng biệt được định nghĩa thủ công? Việc freeze sẽ khác nhau tùy trường hợp.

### Bước 1.2 — Chuẩn bị dữ liệu mixed-domain
- Tập train fine-tune = CIC-IDS-2017 (downsample còn ~20-30% kích thước gốc, giữ tỷ lệ lớp gốc) + toàn bộ Testbed (37 Benign + 22,672 Malicious).
- **Oversample Benign Testbed** (ví dụ SMOTE trên không gian đã scale, hoặc duplicate + nhiễu Gaussian nhỏ) để tránh batch nào cũng không có Benign Testbed.
- Tính `class_weight` tự động theo công thức nghịch đảo tần suất:
  `weight[c] = N_total / (num_classes * count[c])`
  tính trên tập train fine-tune cuối cùng (sau oversample), không tính trên tỷ lệ gốc 37:22672.
- Giữ riêng một validation set Testbed (tách trước khi oversample, không rò rỉ) để theo dõi qua từng epoch.

### Bước 1.3 — Freeze & Fine-tune
- Freeze: embedding layer + 2 block attention đầu (`requires_grad = False`).
- Mở khóa: 2 block attention cuối + classification head.
- Optimizer: AdamW, dùng **2 param group riêng**:
  - Param group đã unfreeze: lr = lr_gốc / 10 đến /20.
  - Nếu sau này thử mở thêm layer: lr thấp hơn nữa cho layer càng gần đầu vào.
- Loss: `CrossEntropyLoss(weight=class_weight_tensor)`.
- Số epoch: bắt đầu nhỏ (5-10 epoch), có early stopping theo Balanced Accuracy trên validation Testbed.
- Bắt buộc checkpoint tốt nhất theo Balanced Accuracy (không theo Accuracy thường, vì lệch lớp).

### Bước 1.4 — Kiểm tra Catastrophic Forgetting
- Sau fine-tune, chạy lại model trên tập test CIC-IDS-2017 gốc.
- So sánh Accuracy/F1 trước và sau — nếu giảm > 5-10 điểm %, coi là forgetting đáng kể, cần giảm lr hoặc tăng tỷ trọng CIC-2017 trong batch.

### Output kỳ vọng
- `2_finetune_freeze.py`
- `checkpoints/ft_transformer_finetuned_v1.pt`
- `results/exp2_finetune_freeze.json` (đủ metrics theo mục 1.3 ở trên)

### Tiêu chí hoàn thành (DoD)
- Recall(Malicious) trên Testbed > 0.218 (vượt baseline gốc) — đây là điều kiện tối thiểu để coi giai đoạn 1 có tác dụng.
- Recall(Benign) không sụp xuống quá thấp do oversample lệch (theo dõi cả hai chiều, tránh lặp lại lỗi của Thử nghiệm 1 theo hướng ngược lại).
- Forgetting trên CIC-2017 test set ở mức chấp nhận được (định nghĩa ngưỡng cụ thể trước khi chạy, ví dụ < 5 điểm % Accuracy).

**→ Nếu DoD đạt: dừng ở đây, viết kết quả vào báo cáo, không cần Giai đoạn 2.**
**→ Nếu chưa đạt: chuyển sang Giai đoạn 2.**

---

## GIAI ĐOẠN 2 — Domain Alignment (CORAL / DANN), chỉ làm nếu Giai đoạn 1 chưa đủ

### Mục tiêu
Ép embedding của hai domain (CIC-2017 và Testbed) gần nhau hơn trong không gian feature, không cần nhãn đầy đủ ở domain đích.

### Lựa chọn A — CORAL Loss (đơn giản hơn, làm trước)
- Lấy output của Transformer encoder (trước classification head) cho 1 batch CIC-2017 và 1 batch Testbed (không cần nhãn Testbed cho phần này).
- Tính CORAL loss = khoảng cách Frobenius giữa ma trận hiệp phương sai (covariance) của 2 batch embedding:
  `L_CORAL = (1/4d^2) * ||Cov_source - Cov_target||_F^2`
  (d = chiều embedding).
- Tổng loss = `CrossEntropyLoss (có class weight)` + `lambda * L_CORAL`, với `lambda` bắt đầu nhỏ (0.1-0.5), tăng dần theo epoch (warm-up).

### Lựa chọn B — DANN (nếu CORAL chưa đủ)
- Thêm 1 domain discriminator nhỏ (MLP 2 lớp) nhận embedding, dự đoán domain (source/target).
- Thêm Gradient Reversal Layer (GRL) giữa encoder và discriminator: forward giữ nguyên, backward nhân gradient với `-lambda`.
- Train đồng thời: encoder cố "đánh lừa" discriminator (làm 2 domain không phân biệt được trong không gian embedding), classification head vẫn học task chính trên dữ liệu có nhãn.

### Output kỳ vọng
- `3_domain_alignment_coral.py` (và `3b_domain_alignment_dann.py` nếu cần thử B)
- `results/exp3_domain_alignment.json`

### Tiêu chí hoàn thành
- Recall(Malicious) trên Testbed cải thiện rõ rệt so với Giai đoạn 1.
- Embedding 2 domain (visualize bằng t-SNE/UMAP trước/sau) cho thấy 2 cụm gần nhau hơn — đính kèm hình minh họa cho báo cáo (rất có giá trị học thuật).

---

## GIAI ĐOẠN 3 — Feature Engineering bổ sung (song song, không phụ thuộc Giai đoạn 1-2)

### Mục tiêu
Giảm phụ thuộc vào giá trị tuyệt đối nhạy hạ tầng (IAT, Window Size, MTU).

### Việc cần làm
- Audit `Custom_Fwd_Pkt_Rate`, `Custom_Slow_Index`: kiểm tra công thức có chứa thời gian tuyệt đối (giây thực) hay không.
- Thêm các đặc trưng dạng tỷ lệ/nội tại flow thay vì giá trị tuyệt đối, ví dụ:
  - Coefficient of Variation của IAT (std/mean trong cùng flow) thay vì IAT trung bình tuyệt đối.
  - Tỷ lệ gói tin nhỏ (<X bytes) / tổng số gói trong flow.
  - Số kết nối đồng thời tới cùng cặp (dst_ip, dst_port) trong cửa sổ thời gian trượt.
- Train lại (fine-tune tiếp từ checkpoint Giai đoạn 1 hoặc 2) với bộ feature mở rộng này, so sánh ablation: có/không các feature mới.

### Output kỳ vọng
- `feature_engineering_v2.py`
- Bảng ablation so sánh metrics có/không feature domain-invariant mới.

---

## GIAI ĐOẠN 4 — Mở rộng dữ liệu Testbed (song song, không cần coding agent, cần người thu thập)

- Thu thêm traffic Benign thực tế trên Testbed (hiện chỉ 37 mẫu — không đủ để Precision đáng tin cậy).
- Mục tiêu tối thiểu: vài trăm mẫu Benign để confidence interval của Precision/Recall thu hẹp đáng kể.
- Khi có dữ liệu mới, chạy lại toàn bộ pipeline đánh giá (không cần train lại ngay) để có con số đáng tin cậy hơn cho báo cáo.

---

## 5. Bảng tổng hợp nộp báo cáo cuối (Agent cần tự động sinh ra)

Viết script `4_aggregate_report.py` đọc toàn bộ `results/exp*.json` và xuất ra 1 bảng Markdown/CSV duy nhất gồm các cột:
`Experiment | Scaler | Fine-tune strategy | Accuracy | Balanced Accuracy | MCC | Recall(Benign) | Recall(Malicious) | F1(Malicious) | Forgetting on CIC-2017 (Δ Accuracy)`

Đây là bảng sẽ được dùng trực tiếp trong báo cáo học thuật để so sánh tiến trình qua từng thử nghiệm.
