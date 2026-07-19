# Two-Stage Cascade (Gating + Expert) — chia để trị

## Nó sinh ra để giải quyết chuyện gì?

Bắt **một model** vừa phải **lọc ~83% Benign** ra khỏi tấn công, vừa phải **phân biệt tinh tế giữa 9 loại tấn công**
là quá tải. Gradient bị **xé làm hai nhiệm vụ** đối chọi: học "Benign vs Attack" và học "Attack A vs Attack B"
cùng lúc → cả hai đều kém.

**Two-Stage Cascade (thác hai tầng)** chia bài toán thành hai chuyên gia nối tiếp — một kiểu **Mixture of
Experts (MoE — hỗn hợp chuyên gia)**:

1. **Gating Network** — tầng sàng lọc: *"flow này có đáng ngờ không?"* (nhị phân).
2. **Expert Network** — tầng chuyên sâu: *"nếu đáng ngờ thì là loại tấn công nào?"* (9 lớp).

> **So sánh đời thường:** như **bệnh viện phân luồng**. **Y tá sàng lọc** (Gating) nhìn nhanh xem ai khoẻ cho về,
> ai đáng ngờ chuyển vào trong. **Bác sĩ chuyên khoa** (Expert) chỉ tập trung chẩn đoán sâu cho nhóm đáng ngờ,
> không bị đám đông người khoẻ làm nhiễu.

---

## Tầng 1 — Gating Network

- Bài toán **nhị phân** đơn giản: Benign vs Suspicious, dùng **đầy đủ 77 đặc trưng**.
- **Ngưỡng bảo thủ 85%** (không phải 50%): chỉ cho một flow "thoát" ra Benign nếu model **rất chắc** nó lành.
- Kết quả: **~82,7% traffic (Benign) thoát khỏi pipeline**; **~17,3% (Suspicious)** đi tiếp xuống Expert.

**Vì sao ngưỡng 85%?** Bỏ sót một Infiltration ở tầng 1 là **mất vĩnh viễn** (không có cơ hội thứ hai).
Nên thà đẩy thêm chút Benign xuống tầng 2 (tốn công) còn hơn để lọt tấn công. → **ưu tiên recall tấn công**.

---

## Tầng 2 — Expert Network

- Chỉ nhận **~17,3% traffic** (các flow Suspicious) → phân loại thành **9 lớp**.
- Dùng **34 đặc trưng** (sau lọc tương quan — xem [[pearson-correlation-filter]]), cấu hình nhỏ hơn (`d=64, L=3`).
- **Lợi ích then chốt:** vì 83% Benign đã bị lọc ở tầng 1, gradient của Expert **không còn phải "đấu" với biển
  Benign** → dồn toàn lực **phân biệt giữa các loại tấn công**.

> **Nói đơn giản:** tách "gác cổng" khỏi "chẩn đoán chuyên sâu" → mỗi tầng làm tốt một việc, thay vì một model
> ôm đồm cả hai rồi hỏng cả hai.

---

## Ví dụ trực giác

- Một model đơn: 100% traffic vào, gradient bị ~83% Benign chi phối → các lớp tấn công hiếm bị chèn ép.
- Cascade: Gating tống 82,7% Benign ra trước → Expert chỉ còn xử lý 17,3% đã "cô đặc tấn công" → học sắc nét hơn.

Kết quả đồ án (CIC Stage 2): **Accuracy 99,55%, Macro-F1 = 0,9294**.

---

## Tóm lại

- **Two-Stage Cascade** = **Gating** (nhị phân, lọc Benign, ngưỡng bảo thủ 85%) → **Expert** (9 lớp, chỉ ~17,3%
  traffic) — một dạng **Mixture of Experts**.
- Tách hai nhiệm vụ đối chọi → mỗi tầng chuyên biệt → gradient Expert tập trung phân biệt tấn công.

**Hiểu cái này thì làm được gì?** Bạn nắm **xương sống kiến trúc** của hệ CIC trong đồ án, và hiểu vì sao chia
tầng lại thắng một model "ôm đồm". Các mảnh ghép: khai thác mẫu khó (trong Expert), và ensemble
[[bias-variance-ensemble]] ở đầu ra.

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Gate Stage-1 + Stage-2 (Snort/NSL) | `Final/01_NSL_KDD/src/inference_product/snort_two_stage_inference.py:238` |
| Cascade 9 lớp (Testbed) | `Final/03_Testbed_Retrain/data_collection/testbed_inference_cascade_9class.py` |
| Đánh giá cascade (CIC) | `Final/02_CIC_IDS_2017/src/training/scripts_v7/evaluate_cascade_system_v7.py` |

**Khi phản biện:** code in ra `stage1_normal_gate_rate` / `stage1_attack_gate_rate` — chứng minh Gating lọc phần lớn Benign trước khi vào Expert.
