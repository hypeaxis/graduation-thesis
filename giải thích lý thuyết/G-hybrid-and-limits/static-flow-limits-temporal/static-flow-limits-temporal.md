# Giới hạn của flow tĩnh — Infiltration & Botnet cần phân tích THỜI GIAN

## Nó sinh ra để giải quyết chuyện gì?

Có những tấn công mà **mỗi flow đơn lẻ trông hoàn toàn bình thường** — dấu hiệu chỉ lộ ra khi nhìn **chuỗi
nhiều flow theo thời gian**. Với các tấn công này, mô hình phân loại **từng flow một** (FTT, RF, KNN) về
nguyên lý **không thể** bắt được. Đây là **giới hạn căn bản**, không phải lỗi cấu hình.

Hai thủ phạm điển hình: **Infiltration** và **Botnet C2**.

> **So sánh đời thường:** nhìn **một khung hình lẻ** từ camera, bạn không biết ai đang lén lút — người đó chỉ
> đang đứng bình thường. Phải xem **cả đoạn video** (chuỗi thời gian) mới thấy hành vi rình mò lặp đi lặp lại.

---

## Infiltration: dấu hiệu nằm ngoài tầm flow tĩnh

Infiltration (CIC) là leo thang đặc quyền qua ứng dụng (Dropbox, iexplore). Mỗi flow CICFlowMeter bắt được chỉ
là **HTTP/HTTPS request bình thường** — thống kê flow **không phân biệt** được với duyệt web thường.

Dấu hiệu thật chỉ lộ khi quan sát **theo thời gian**:
- Tần suất kết nối ra server ngoài **tăng bất thường**.
- **DNS query** tới domain **chưa từng thấy**.
- **Upload dữ liệu** bất thường vào đêm khuya.

→ Đây là bài toán **phân tích chuỗi thời gian (temporal analysis)**, không phải phân loại điểm dữ liệu đơn lẻ.

---

## Botnet C2: nhịp tim ẩn trong dòng thời gian

Botnet C2 giao tiếp theo **nhịp đập định kỳ (periodic heartbeat)** ở tần suất thấp — **mỗi flow C2 riêng lẻ
trông như DNS/HTTP bình thường**. Chỉ khi nhìn nhiều flow liên tiếp mới thấy **tính chu kỳ** (interval cố định,
domain bất thường).

Vì thế Botnet F1 dù đã cải thiện đáng kể (0,4787 → 0,7344 nhờ [[hard-negative-mining]] + ensemble) **vẫn thuộc
nhóm thấp nhất** — cộng thêm sự đa dạng cao của các biến thể C2.

> **Nói đơn giản:** một tiếng "tít" thì bình thường; nhưng "tít... tít... tít" **đều đặn mỗi 30 giây** mới là
> dấu hiệu máy đang bị điều khiển từ xa. Model nhìn một "tít" thì chịu.

---

## Hệ quả & hướng giải quyết

| Giới hạn | Tấn công ảnh hưởng | Hướng giải quyết |
|---|---|---|
| Flow đơn lẻ thiếu ngữ cảnh | Infiltration, Botnet | **Session aggregation** (gộp nhiều flow → 1 vector dài) |
| Không có phân tích payload | Infiltration, Web Attack | **DPI** + multi-modal (flow + payload encoder) |
| Không phân tích thời gian | Infiltration, Botnet | **Graph/LSTM** trên chuỗi flow (temporal) |

Các hướng này **nằm ngoài phạm vi đồ án hiện tại** nhưng là **mở rộng tự nhiên tiếp theo**.

---

## Tóm lại

- Một số tấn công (**Infiltration, Botnet C2**) có **mỗi flow trông như Benign**; dấu hiệu chỉ ở **chuỗi thời gian**.
- Mô hình phân loại **flow đơn lẻ** (FTT/RF/KNN) **về nguyên lý không bắt được** ngữ cảnh temporal này.
- Hướng đi: **session aggregation, DPI multi-modal, graph/LSTM temporal**.

**Hiểu cái này thì làm được gì?** Bạn viết được phần **"Giới hạn & Hướng phát triển"** của luận văn một cách
thuyết phục — chỉ ra *ranh giới lý thuyết* của cách tiếp cận flow tĩnh, thay vì đổ lỗi cho model. Liên hệ
[[flow-features-cicflowmeter]] (nguồn gốc giới hạn) và [[portscan-inseparability-nat]] (một giới hạn dữ liệu khác).

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Hậu xử lý flow-level (chưa temporal) | `Final/05_Replay_Detection/ids_replay/postprocess.py` |
| Đặc trưng flow đơn lẻ | `Final/05_Replay_Detection/ids_replay/features.py` |

**Khi phản biện:** đây là **giới hạn**: code chỉ phân loại flow đơn lẻ; session aggregation / DPI / LSTM-temporal là **hướng mở rộng**, chưa hiện thực trong `Final/`.
