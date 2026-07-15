# "3 giai đoạn không khác nhau quá nhiều — model train ở cả 3 giai đoạn"

Đây là lời phê đáng sợ nhất trong các lời phê, vì nó **đúng một nửa**. Và nửa đúng đó không nằm ở đồ án —
nó nằm ở *cách kể chuyện*. Bài này bóc ra: 3 giai đoạn thật sự khác nhau ở đâu, chỗ nào giống nhau **có chủ đích**,
và câu trả lời 30 giây khi hội đồng đâm thẳng câu hỏi này.

---

## 1. Trước hết, thừa nhận: lời phê đúng ở chỗ nào

Nếu slide đang kể theo trục **dataset**, thì người nghe nhận được đúng ba câu:

> GĐ1: train FT-Transformer trên NSL-KDD → Macro F1 0,681
> GĐ2: train FT-Transformer trên CIC-IDS-2017 → Macro F1 0,929
> GĐ3: train FT-Transformer trên Testbed → Macro F1 0,917

Ba câu này *giống hệt nhau*, chỉ thay tên bộ dữ liệu. Nghe xong, câu hỏi tự nhiên bật ra:
**"Vậy sao không train thẳng trên testbed cho xong? Hai giai đoạn đầu để làm gì?"**

Và tệ hơn: ba con số F1 kia **không so sánh được với nhau** (4 lớp / 9 lớp / 5 lớp, ba bộ dữ liệu khác nhau).
Xếp chúng cạnh nhau trông như một "đường tiến bộ" — nhưng nó không phải. Đó là cái bẫy tự đào.

Vấn đề là slide đang kể theo **dữ liệu**. Thực tế 3 giai đoạn khác nhau theo **câu hỏi khoa học** và theo
**bản chất của phép train**.

---

## 2. Sự thật kỹ thuật quan trọng nhất: chỉ có **2 lần** train từ đầu, lần thứ 3 **không phải train**

Đây là mảnh mà hầu như slide nào cũng bỏ sót, và nó lật ngược cả lời phê.

| Giai đoạn | Trọng số khởi đầu | Đây là gì? |
|---|---|---|
| GĐ1 — NSL-KDD | ngẫu nhiên (random init) | **Train from scratch** — huấn luyện từ số 0 |
| GĐ2 — CIC-IDS-2017 | ngẫu nhiên (random init) | **Train from scratch** — huấn luyện từ số 0 |
| GĐ3 — Testbed (V8.5) | **nạp từ checkpoint có sẵn** | **Fine-tune** — tinh chỉnh, không phải train lại |

Bằng chứng nằm thẳng trong code, không phải suy diễn:

```python
# Phase3_4_Retrain/v8/v8.5_Combined/v8_5_train.py:200-207
model = FTTransformer(num_features=80, num_classes=5, ...)
state = torch.load(BASE_MODEL_PATH, map_location='cpu')   # ← nạp trọng số cũ
model.load_state_dict(state)                              # ← KHÔNG random init
```

Và learning rate cũng không phải một giá trị chung, mà **chia theo tầng** (`make_param_groups`, dòng 94):

```
backbone (embedding + block 1,2) : lr = 1e-5     ← gần như đóng băng, chỉ chỉnh vi mô
mid      (block 3,4 + norm)      : lr = 1.5e-5
head     (classifier)            : lr = 3e-5     ← chỉnh mạnh nhất, gấp 3 lần backbone
```

**Nói nôm na:** GĐ1 và GĐ2 là *xây nhà*. GĐ3 **không đập nhà đi xây lại** — nó là *cải tạo*:
móng và tường giữ nguyên (lr 1e-5, gần như không đụng), chỉ sửa mạnh phần nội thất tiếp xúc với người dùng
(classifier, lr 3e-5).

Ai bảo "train ở cả 3 giai đoạn" là đang hiểu GĐ3 sai bản chất. GĐ3 là **transfer learning** —
và transfer learning chỉ tồn tại được **vì đã có GĐ2**.

### Thêm một chi tiết đắt: GĐ1 → GĐ2 **không** chuyển được trọng số, GĐ2 → GĐ3 **thì có**

Vì sao? Vì **không gian đặc trưng** (feature space) khác nhau:

- GĐ1: 41 cột NSL-KDD, one-hot các cột chữ → **122 đặc trưng**.
- GĐ2: CICFlowMeter cho toàn số, không còn cột chữ → **77 đặc trưng**, tên hoàn toàn khác.

Hai không gian này không tương thích — nạp trọng số của cái này vào cái kia là vô nghĩa
(giống như đưa chìa khóa nhà cho người ở một thành phố khác). Nên GĐ2 **buộc** phải train lại từ đầu.

Nhưng GĐ2 → GĐ3 thì cùng họ CICFlowMeter: 77 đặc trưng cũ **giữ nguyên**, chỉ **thêm 3 đặc trưng mới**
đặc thù cho môi trường NAT (IAT_CV, Bwd_Pkt_Ratio, Pkt_Size_Ratio) → 80. Đó là **Model Surgery**:
chép nguyên 77 hàng embedding cũ, ghép thêm 3 hàng mới khởi tạo trung tính.

Bằng chứng nó có tác dụng thật: MCC **0,6825 → 0,7333** sau khi ghép 3 đặc trưng.

---

## 3. Chỗ giống nhau là **cố ý** — đó là biến kiểm soát

Cái duy nhất giữ nguyên xuyên suốt là **khung xương** FT-Transformer:
`d_model=128, num_heads=8, num_layers=4, d_ff=512`.

Đây không phải lười. Đây là **control variable** (biến kiểm soát) của một thí nghiệm.

> **So sánh đời thường:** muốn biết đất nào tốt hơn thì phải **trồng cùng một giống cây** ở cả ba mảnh.
> Nếu mỗi mảnh trồng một giống khác nhau, cây mảnh nào lớn hơn cũng chẳng kết luận được gì —
> tại đất tốt hay tại giống khỏe?

Giữ nguyên kiến trúc để khi kết quả khác nhau, ta **quy được nguyên nhân về dữ liệu và về miền (domain)**,
chứ không phải về kiến trúc. Nếu mỗi giai đoạn đổi một model khác, toàn bộ mạch lập luận
"model rơi khi gặp traffic thật" **sụp**, vì hội đồng sẽ hỏi ngay: "hay là tại anh đổi model?"

Đây là câu trả lời cần thuộc: **giống nhau là bằng chứng, không phải sự lặp lại.**

---

## 4. Ba giai đoạn = ba **câu hỏi** khác nhau, ba **kẻ thù** khác nhau

Đây là cách kể đúng. Mỗi giai đoạn phải trả lời: *câu hỏi gì → kẻ thù nào → phải phát minh vũ khí gì →
bàn giao cái gì cho giai đoạn sau*.

| | **GĐ1 — NSL-KDD** | **GĐ2 — CIC-IDS-2017** | **GĐ3 — Testbed thật** |
|---|---|---|---|
| **Câu hỏi** | Transformer có "ăn" được dữ liệu bảng không? Có đáng đầu tư tiếp không? | Chịu nổi quy mô lớn + mất cân bằng khủng khiếp không? | Model giỏi trên benchmark có sống được với traffic thật không? |
| **Kẻ thù** | Chính giả thuyết (Transformer sinh ra cho chuỗi, không cho bảng) | **Imbalance** — Benign áp đảo, Heartbleed có 10 mẫu | **Domain shift** — lab ≠ đời thật |
| **Vũ khí mới** | Feature Tokenizer, AE Gate, Stacking với LightGBM | Cascade 2 tầng, Focal Loss γ=1,5, Yeo-Johnson, RF/KNN veto | Layer Freezing, **Model Surgery**, Hybrid Scaler, layer-wise LR |
| **Bằng chứng vũ khí có tác dụng** | FTT đơn lẻ **thua LightGBM** → phải Stacking mới lên 0,681 | 1 tầng 0,7831 → **cascade 0,9294** | Refit scaler **thất bại** → freezing + surgery: MCC 0,6825 → **0,7333** |
| **Bàn giao gì** | **Kiến trúc** (mỗi đặc trưng = 1 token = 1 Linear riêng) | **Trọng số backbone 77 đặc trưng** — tài sản thật | Hệ thống chạy được → GĐ4/5 |

Đọc hàng "bàn giao" theo chiều ngang, sẽ thấy **sợi chỉ đỏ**:

```
GĐ1 ──(bản vẽ kiến trúc)──▶ GĐ2 ──(trọng số 77 feat)──▶ GĐ3 ──(fine-tune)──▶ GĐ5 (v8_7)
      không chuyển trọng số        Model Surgery 77→80      layer-wise LR
```

Và đây là cú chốt đẹp nhất của cả đồ án: **quyết định kiến trúc ở GĐ1 mới là thứ cứu GĐ3.**

Feature Tokenizer coi mỗi đặc trưng là **một `nn.Linear` độc lập** (một `ModuleList` 80 cái Linear riêng).
Chính vì thế, muốn thêm 3 đặc trưng chỉ cần **thêm 3 Linear mới**, 77 cái cũ giữ nguyên trọng số.
Nếu GĐ1 chọn MLP thường (một Linear chung `80 → d` trộn hết đặc trưng ngay tầng đầu),
thì **Model Surgery là bất khả thi** — muốn thêm 3 đặc trưng phải train lại từ đầu, mà testbed
lúc đó chỉ có **~37 flow benign**, train lại từ đầu là chết chắc.

> **Nói đơn giản:** GĐ1 không đưa cho GĐ3 một đồng trọng số nào, nhưng nó đưa cho GĐ3 **cái tủ có ngăn kéo rời**.
> Nhờ vậy 2 năm sau mới ghép thêm được 3 ngăn mà không phải đóng lại cả cái tủ.

---

## 5. Ba lần "train" khác nhau về **kỹ thuật**, không chỉ khác dữ liệu

Nếu hội đồng vẫn đòi cụ thể, đây là bảng cho thấy gần như **không có gì trùng nhau** ngoài khung xương:

| Thành phần | GĐ1 (NSL-KDD) | GĐ2 (CIC-IDS-2017) | GĐ3 (Testbed / V8.5) |
|---|---|---|---|
| Khởi tạo trọng số | random | random | **nạp V8.4** |
| Số đặc trưng | 122 (one-hot) | 77 (số thuần) | **80** (77 kế thừa + 3 mới) |
| Số lớp | 4 | 6 (tầng 1) + 5 (tầng 2) | 5 |
| Scaler | MinMaxScaler | **PowerTransformer Yeo-Johnson** | **Hybrid** (2 PowerTransformer ghép) |
| Hàm mất mát | Cross-Entropy | **Focal γ=1,5** + label smoothing 0,05 | **Focal γ=2,0** + label smoothing 0,10 |
| Chống overfit | chỉ dropout 0,1 | dropout 0,2 + DropPath 0,1 | dropout 0,15 + DropPath 0,15 + **LayerScale + GEGLU** |
| Optimizer / lịch LR | Adam | AdamW + **Warmup** + Cosine + **EMA** | AdamW + Cosine, **bỏ warmup, bỏ EMA**, LR **chia 3 tầng** |
| Kiến trúc hệ thống | AE Gate + Stacking | **Cascade 2 tầng** + RF/KNN veto | **1 model phẳng** + Snort rule |
| Tiêu chí dừng | Macro F1 (val) | Macro F1 (val) | GĐ5: **FPR trên benign THẬT** held-out |

Chú ý hàng **optimizer** — đây là chỗ ghi điểm nếu bị hỏi sâu:

> **Vì sao GĐ2 có warmup còn GĐ3 bỏ warmup?**
> Warmup sinh ra để **bảo vệ giai đoạn trọng số ngẫu nhiên**: lúc mới khởi tạo, trọng số vô nghĩa,
> learning rate lớn ngay từ bước 1 sẽ đẩy model đi lung tung. GĐ3 **không có trọng số ngẫu nhiên** —
> nó bắt đầu từ một model đã tốt. Không có gì để bảo vệ → warmup vô nghĩa, thậm chí có hại
> (làm chậm quá trình bám vào miền mới).
> EMA cũng vậy: nó làm mượt dao động của train-from-scratch. Fine-tune LR 1e-5 gần như không dao động.

**Dùng đúng công cụ cho đúng tình huống, thay vì bê nguyên cấu hình cũ** — đó mới là điều chứng minh
người làm *hiểu* chứ không copy.

Và hàng cuối cùng — **tiêu chí dừng** — là thay đổi lớn nhất của cả đồ án: từ GĐ3 sang GĐ5,
thứ được tối ưu **không còn là Macro F1** nữa mà là **tỉ lệ báo động giả trên traffic bình thường thật**.
Hàm mục tiêu của cả hệ thống đã đổi. Đó không phải "lặp lại một giai đoạn", đó là đổi cả định nghĩa thành công.

---

## 6. Câu hỏi chắc chắn bị hỏi: "Vậy bỏ GĐ1, GĐ2 đi, train thẳng trên testbed được không?"

**Không — và lý do là con số.**

Testbed lúc bắt đầu chỉ có **~37 flow benign**. Model FT-Transformer V8.5 có **1.088.005 tham số**.
Train 1,09 triệu tham số trên vài chục đến vài nghìn flow = **học vẹt** (model thuộc lòng từng mẫu,
gặp flow lạ là sập).

Model cần biết trước "một flow tấn công *trông như thế nào*" — kiến thức đó đến từ **hàng triệu flow
của CIC-IDS-2017 ở GĐ2**. Testbed chỉ đủ để dạy model *"ở mạng CỦA TÔI thì bình thường trông thế nào"*.

Nói cách khác: **GĐ2 dạy model đọc, GĐ3 dạy model đọc đúng giọng địa phương.** Bỏ GĐ2 thì GĐ3
không có gì để fine-tune — nó rơi ngược về train-from-scratch trên 37 flow.

Còn GĐ1? Trung thực mà nói: **GĐ1 không đóng góp một trọng số nào.** Nó đóng góp hai thứ:
1. **Quyết định kiến trúc** (Feature Tokenizer) — thứ khiến Model Surgery ở GĐ3 khả thi. Không có nó, GĐ3 bế tắc.
2. **Bài học ensemble** — phát hiện FTT thua LightGBM trên dữ liệu bảng nhỏ, nên phải kết hợp chứ không thay thế.
   Bài học này quay lại ở GĐ2 (RF/KNN veto) và GĐ4 (Snort + FTT).

Nếu hội đồng ép "GĐ1 có bắt buộc không?" — **đừng chống chế**. Trả lời thẳng:

> *"Về mặt trọng số thì không bắt buộc. GĐ1 là giai đoạn thăm dò trên benchmark chuẩn để trả lời
> câu hỏi khả thi trước khi đổ tài nguyên vào dữ liệu lớn — đó là quy trình nghiên cứu bình thường.
> Giá trị còn lại của nó là quyết định kiến trúc, và quyết định đó mới là thứ cứu giai đoạn 3."*

Thành thật về giới hạn của một giai đoạn **mạnh hơn** là bảo vệ nó bằng lý lẽ yếu.

---

## 7. Trả lời 30 giây (thuộc lòng cái này)

> *"Ba giai đoạn không phải ba lần huấn luyện lại cùng một mô hình. Chỉ **hai** giai đoạn đầu train từ đầu,
> và chúng buộc phải tách rời vì hai không gian đặc trưng không tương thích — 122 đặc trưng one-hot của
> NSL-KDD với 77 đặc trưng CICFlowMeter.*
>
> *Giai đoạn 3 **không** train từ đầu: nó **nạp trọng số** của giai đoạn 2, ghép thêm 3 đặc trưng bằng
> Model Surgery, rồi fine-tune với learning rate chia theo tầng — 1e-5 cho backbone, 3e-5 cho classifier.
> Đó là transfer learning, và nó chỉ tồn tại được **nhờ** giai đoạn 2.*
>
> *Thứ duy nhất em giữ nguyên là khung kiến trúc, và giữ nguyên **có chủ đích**: đó là biến kiểm soát,
> để mọi chênh lệch kết quả quy được về **dữ liệu và miền**, chứ không phải về kiến trúc.*
>
> *Ba giai đoạn khác nhau ở **câu hỏi**: giai đoạn 1 hỏi tính khả thi, giai đoạn 2 đánh mất cân bằng,
> giai đoạn 3 đánh domain shift. Ba kẻ thù khác nhau, ba bộ vũ khí khác nhau."*

---

## 8. Sửa slide thế nào cho hết bị phê

1. **Đổi tiêu đề slide từ tên dataset sang câu hỏi.**
   ❌ "GĐ2 — CIC-IDS-2017" → ✅ "GĐ2 — Đánh trận mất cân bằng: 1 tầng 0,78 → cascade 0,93"

2. **Thêm một slide "sợi chỉ đỏ"** với mũi tên trọng số (mục 4). Đây là slide quan trọng nhất để dập lời phê:
   nó cho thấy các giai đoạn **nối vào nhau**, không phải xếp cạnh nhau.

3. **Đừng xếp 3 con số F1 lên cùng một trục.** Chúng khác dataset, khác số lớp — không so sánh được.
   Thay vào đó, mỗi giai đoạn dùng **cặp số nội bộ của chính nó** (trước/sau khi áp vũ khí mới):
   - GĐ1: FTT đơn lẻ → **Stacking 0,681**
   - GĐ2: 1 tầng 0,7831 → **cascade 0,9294**
   - GĐ3: refit scaler (thất bại) → **freezing + surgery, MCC 0,6825 → 0,7333**
   - GĐ5: FPR **24,26% → 0,29%**

   Bốn cặp số này mới là bằng chứng "mỗi giai đoạn giải một bài toán riêng và giải được".

4. **Nói thẳng chữ "fine-tune" trên slide GĐ3.** Chỉ cần một dòng
   *"không train lại — nạp trọng số GĐ2, layer-wise LR 1e-5 / 1,5e-5 / 3e-5"* là lời phê tự tan.
