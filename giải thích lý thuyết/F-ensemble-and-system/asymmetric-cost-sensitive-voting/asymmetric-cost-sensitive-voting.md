# Asymmetric Voting — bỏ phiếu theo CHI PHÍ sai, không phải theo đa số

## Nó sinh ra để giải quyết chuyện gì?

Cách gộp ensemble quen thuộc là **Majority Voting (đa số 2/3)**. Nó **tối ưu khi chi phí của mọi loại sai là
NHƯ NHAU**. Nhưng trong IDS, **cái giá của các kiểu sai rất khác nhau tùy lớp**:

- Bỏ sót một **Infiltration** → có thể để lộ dữ liệu (data breach) hàng tháng trời. **Cực đắt.**
- Báo nhầm quá nhiều **Botnet** → đội SOC ngập trong báo động giả, **mệt mỏi cảnh báo (alert fatigue)** rồi
  bỏ qua cả cảnh báo thật. **Cũng đắt, nhưng theo kiểu khác.**

**Asymmetric / Cost-sensitive Voting** điều chỉnh luật bỏ phiếu **theo chi phí sai của từng lớp**, thay vì
đếm phiếu ngang nhau.

> **So sánh đời thường:** **báo cháy** thì thà báo nhầm còn hơn bỏ sót (một mạng người > vài lần hú còi thừa).
> Nhưng **báo động trộm gọi cảnh sát** thì cần chắc chắn, kẻo gọi hoài cảnh sát sẽ chẳng thèm đến. Hai loại
> báo động, hai ngưỡng khác nhau.

---

## Hai loại chi phí sai

- **FN (False Negative — bỏ sót)**: có tấn công mà báo là bình thường.
- **FP (False Positive — báo nhầm)**: bình thường mà báo là tấn công.

Tùy lớp mà cái nào đắt hơn → chọn luật gộp khác nhau.

---

## Luật bất đối xứng — bóc từng mảnh

| Lớp | Vấn đề của FTT | Chi phí | Luật gộp |
|---|---|---|---|
| **Infiltration** | FTT hay **bỏ sót** (FN cao) | FN **rất đắt** (lộ dữ liệu) | **OR**(RF, KNN) → Infiltration |
| **Botnet** | FTT hay **báo dư** (FP cao) | FP đắt (alert fatigue) | **AND**(FTT, RF, KNN) → Botnet |
| Các lớp khác | Cân bằng | — | **Majority (2/3)** |

- **Infiltration Priority Rule (OR):** *chỉ cần MỘT trong RF/KNN* nói Infiltration là gán Infiltration →
  **tăng Recall** (bắt được nhiều hơn), đổi lấy giảm Precision. Hợp lý vì FN quá đắt.
- **Botnet Consensus Rule (AND):** *phải CẢ BA* đồng thuận mới gán Botnet → **giảm mạnh FP**, đổi lấy giảm
  Recall vừa phải. Hợp lý vì FTT sau HNM hay báo dư Botnet.

> **Nói đơn giản:** với lớp "thà bắt nhầm còn hơn bỏ sót" → dùng OR (dễ dãi). Với lớp "phải chắc mới báo" →
> dùng AND (khắt khe).

---

## Ví dụ trực giác

Một flow, ba phiếu: FTT=Benign, RF=Infiltration, KNN=Benign.

- **Majority 2/3:** → Benign (bỏ sót Infiltration → nguy hiểm!).
- **OR-rule cho Infiltration:** chỉ cần RF kêu → **gán Infiltration** → cứu được ca bỏ sót đắt giá.

---

## Tóm lại

- **Majority Voting** chỉ tối ưu khi chi phí FP = FN. IDS thì **không** — mỗi lớp một kiểu chi phí.
- **Asymmetric Voting:** Infiltration dùng **OR** (tăng Recall, sợ FN); Botnet dùng **AND** (giảm FP, sợ alert
  fatigue); còn lại **Majority**.

**Hiểu cái này thì làm được gì?** Bạn thấy ensemble không chỉ là "gộp cho chính xác hơn" mà còn là **công cụ
quản trị rủi ro** theo chi phí thực tế — một điểm sáng thực tiễn của đồ án. Nền lý thuyết: [[bias-variance-ensemble]],
[[inductive-bias-diversity]].

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Infiltration Priority OR-rule | `Final/02_CIC_IDS_2017/src/training/scripts_v7/evaluate_cascade_system_v7.py:191` |

**Khi phản biện:** luật trong code: `if rf=='Infiltration' or knn=='Infiltration' or (ft=='Infiltration' and ft_prob>=thr)` → gán Infiltration (tăng recall); các lớp khác dùng majority.
