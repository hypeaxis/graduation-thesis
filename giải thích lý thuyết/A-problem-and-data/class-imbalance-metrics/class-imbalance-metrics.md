# Mất cân bằng dữ liệu & chỉ số đánh giá đúng (Macro-F1, MCC)

## Nó sinh ra để giải quyết chuyện gì?

Trong dữ liệu IDS, các lớp **lệch nhau khủng khiếp**:

- **Benign chiếm 80–90%** traffic.
- **Giữa các lớp tấn công cũng lệch**: DoS/DDoS có hàng triệu flow, còn **Heartbleed chỉ 10 flow**.

Hệ quả nguy hiểm: một mô hình **lười** — cứ đoán "tất cả là Benign" — vẫn đạt **Accuracy 82,7%** trên CIC,
nhưng **hoàn toàn vô dụng** vì bỏ sót 100% tấn công.

> **So sánh đời thường:** như chấm điểm một bác sĩ bằng câu *"tỷ lệ nói đúng người khoẻ mạnh"*. Trong một
> đám đông toàn người khoẻ, bác sĩ cứ phán "ai cũng khoẻ" là được điểm cao chót vót — nhưng bỏ sót đúng
> mấy người bệnh cần cứu.

Vì thế ta cần **chỉ số đánh giá khác Accuracy**.

---

## Nền tảng: Precision, Recall, F1 cho từng lớp

Với một lớp (ví dụ "PortScan"):

- **Precision (độ chính xác)** = trong những cái model *báo* là PortScan, bao nhiêu % *đúng* là PortScan.
  → đo mức "báo bừa".
- **Recall (độ phủ)** = trong những cái *thật sự* là PortScan, model *bắt được* bao nhiêu %.
  → đo mức "bỏ sót".
- **F1** = trung bình điều hoà của hai cái trên:

```
F1 = 2 · (Precision · Recall) / (Precision + Recall)
```

> **Nói nôm na:** Precision hỏi *"báo có chuẩn không?"*, Recall hỏi *"có bỏ sót không?"*,
> F1 ép cả hai phải cùng tốt (chỉ một cái cao thì F1 vẫn thấp).

---

## Macro-F1: cho lớp hiếm được "một phiếu bầu" ngang nhau

**Macro-F1** = **trung bình cộng F1 của tất cả các lớp**, mỗi lớp trọng số **bằng nhau**:

```
Macro-F1 = (F1_Benign + F1_DoS + … + F1_Heartbleed) / C
```

Điểm mấu chốt: Heartbleed (10 mẫu) và Benign (2,3 triệu mẫu) **đóng góp NGANG nhau**. Nên nếu model bỏ bê
lớp hiếm, Macro-F1 **tụt ngay** — khác hẳn Accuracy vốn bị lớp đông "nuốt trọn".

> **So sánh:** Accuracy giống bỏ phiếu theo **đầu người** (đông thắng); Macro-F1 giống bỏ phiếu theo
> **mỗi lớp một phiếu** (nhỏ mấy cũng có tiếng nói).

---

## MCC: một con số "thành thật" cho dữ liệu lệch

**MCC (Matthews Correlation Coefficient — hệ số tương quan Matthews)** dùng cả 4 ô của ma trận nhầm lẫn
(TP, TN, FP, FN):

```
MCC = (TP·TN − FP·FN) / √((TP+FP)(TP+FN)(TN+FP)(TN+FN))
```

- Giá trị nằm trong **[−1, +1]**.
- **+1** = hoàn hảo; **0** = đoán như tung đồng xu; **âm** = đoán *sai có hệ thống* (tệ hơn cả đoán bừa).

Nó "thành thật" vì chỉ cao khi model làm tốt **đồng thời cả 4 ô** — không thể ăn gian bằng cách chỉ chiều lớp đông.

> **Ví dụ trong đồ án:** khi apply model CIC thẳng sang Testbed, **MCC = −0,015** → không chỉ kém mà còn
> *phân loại sai hướng có hệ thống*. Con số âm này nói lên điều Accuracy không nói được.

---

## Ví dụ SỐ: mô hình "lười" bị lộ mặt

| Chỉ số | Model đoán "tất cả Benign" | Ý nghĩa |
|---|---|---|
| Accuracy | **82,7%** (đẹp giả) | bị 82,7% Benign nuốt trọn |
| Macro-F1 | **rất thấp** (F1 mọi lớp attack = 0) | lộ ngay sự vô dụng |
| MCC | **≈ 0** | đoán như tung đồng xu |

---

## Tóm lại

- Dữ liệu IDS **lệch hai chiều** → **Accuracy đánh lừa** (model lười vẫn 82,7%).
- **Macro-F1**: trung bình F1 mọi lớp, **mỗi lớp một phiếu** → lớp hiếm bị bỏ bê là tụt điểm ngay.
- **MCC**: một con số trong **[−1,1]** dùng cả 4 ô ma trận nhầm lẫn → **thành thật** kể cả khi lệch,
  báo được cả trường hợp "sai có hệ thống".

**Hiểu cái này thì làm được gì?** Bạn chọn đúng thước đo để **báo cáo trong luận văn** và để **tuning model** —
tránh cái bẫy kinh điển "accuracy 99% mà chẳng bắt được tấn công nào".

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Macro-F1 làm mục tiêu tối ưu ngưỡng | `Final/01_NSL_KDD/src/training/evaluate_class_aware_gate.py:127` |
| Macro-F1 objective (Nelder-Mead) | `Final/01_NSL_KDD/src/training/stacking_ensemble.py:94` |
| Báo cáo per-class + macro (CIC) | `Final/02_CIC_IDS_2017/src/training/scripts_v7/evaluate_cascade_system_v7.py` |

**Khi phản biện:** mọi lựa chọn ngưỡng/ensemble đều **tối ưu theo Macro-F1** (không phải Accuracy) — trả lời được câu 'vì sao không dùng accuracy?'.
