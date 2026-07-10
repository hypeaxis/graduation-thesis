# Hard Negative Mining — chỉ ôn lại những câu làm SAI

## Nó sinh ra để giải quyết chuyện gì?

Với các lớp khó (Botnet, Infiltration), cách quen thuộc là **tăng class weight** — nhân trọng số cho *toàn bộ*
mẫu của lớp đó. Nhưng cách này lãng phí: nó tăng gradient cho **cả những mẫu vốn đã phân loại đúng dễ dàng**.

**Hard Negative Mining (HNM — khai thác mẫu khó)** sắc bén hơn: chỉ **tăng trọng số cho những mẫu đang bị
phân loại SAI** (hard negatives — nằm sai phía ranh giới). Model bị buộc phải **tinh chỉnh đúng chỗ đang sai**.

> **So sánh đời thường:** ôn thi mà **chỉ làm lại những câu từng sai**, không phí thời gian ôn lại câu đã chắc.
> Hiệu quả dồn đúng vào điểm yếu.

---

## HNM vs tăng class weight — khác biệt cốt lõi

| | Tăng class weight | Hard Negative Mining |
|---|---|---|
| Tăng gradient cho | **Mọi** mẫu của lớp (kể cả đã đúng) | **Chỉ** mẫu đang bị sai |
| Model học tốt hơn về | **Phân phối** của lớp | **Ranh giới (boundary)** quyết định |
| Ví dụ | `w_Botnet = 10` cho tất cả Botnet | thu hard negatives sau mỗi vòng, tăng `w_hard = 2` |

> **Nói đơn giản:** class weight dạy model "lớp này quan trọng đấy"; HNM dạy model "chỗ *này* mày đang vẽ sai
> đường biên, sửa đi".

---

## Liên hệ lý thuyết: Boosting & Curriculum Learning

- **Boosting / AdaBoost** (Schapire, 1990): sau mỗi weak learner, **tăng trọng số mẫu bị sai** để cái tiếp theo
  tập trung vào chúng. HNM chính là **một hiện thân của tư tưởng này**: sau mỗi vòng, thu mẫu sai → vòng sau chú ý.
- **Curriculum Learning** (Bengio, 2009): học **dễ trước, khó sau**. Vòng 1 (không HNM) học mẫu dễ; vòng HNM
  sau đó tập trung "mẫu khó nhất theo định nghĩa của chính model đã học".

---

## Ví dụ SỐ — kết quả trong đồ án

| Phương án | Botnet F1 | Infiltration F1 |
|---|---|---|
| Không HNM, không class weight | 0,4787 | 0,3821 |
| Class weight Botnet ×10 | 0,5218 | 0,4198 |
| HNM 1 vòng (w_hard=2) | 0,5934 | 0,5213 |
| **HNM 2 vòng (w_hard=2)** | **0,6512** | **0,5903** |

→ HNM 2 vòng vượt class weight ×10: **+13% Botnet F1**, **+17% Infiltration F1**.

---

## Giới hạn: cần hai lớp PHÂN TÁCH được

HNM chỉ hiệu quả khi hai lớp **có thể phân tách** nhưng ranh giới **chưa được học đúng**. Với **PortScan/Benign
WSL** — hai lớp **không phân tách** (xem [[portscan-inseparability-nat]]) — HNM vô ích: không tồn tại ranh giới
nào để học tốt hơn, tăng trọng số mẫu sai chỉ **bơm nhiễu**.

---

## Tóm lại

- **HNM** chỉ tăng trọng số **mẫu đang bị sai** → tinh chỉnh **ranh giới**, không phí sức lên mẫu đã đúng.
- Là hiện thân của **Boosting** + **Curriculum Learning**; đồ án đạt **+13% Botnet F1** so với class weight ×10.
- Chỉ hiệu quả khi hai lớp **phân tách được** — trùng lẫn thì bó tay.

**Hiểu cái này thì làm được gì?** Bạn nắm **tầng thứ ba** của chống mất cân bằng (sau dữ liệu và loss): tinh
chỉnh **boundary**. Dùng trong Expert Network của [[two-stage-cascade-gating-expert]].

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Trích hard negatives (double HNM Botnet) | `Final/02_CIC_IDS_2017/src/training/scripts_v7/extract_hard_negatives_v7.py:87` |
| Bản v5 | `Final/02_CIC_IDS_2017/src/archive/scripts_v5/extract_hard_negatives_v5.py` |

**Khi phản biện:** code thu các mẫu Stage-1 coi là **Suspicious** (gồm cả True Positive lẫn hard negative) rồi tăng trọng số ở vòng huấn luyện Stage-2 tiếp theo — đúng tinh thần Boosting.
