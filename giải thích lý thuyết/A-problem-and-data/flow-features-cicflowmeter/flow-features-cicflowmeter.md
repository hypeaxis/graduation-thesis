# Trích xuất đặc trưng flow bằng CICFlowMeter

## Nó sinh ra để giải quyết chuyện gì?

Mô hình máy học không "ăn" được gói tin thô — nó cần **một dãy số có độ dài cố định**.
Nhưng một flow có thể gồm 2 gói hoặc 2000 gói, dài ngắn khác nhau. Làm sao biến một flow bất kỳ
thành **cùng một khuôn vector**?

**CICFlowMeter** giải quyết chuyện đó: nó **gom mọi gói của một flow lại và tính ra 77–80 con số thống kê**
mô tả flow đó.

> **So sánh đời thường:** giống **hoá đơn điện thoại cuối tháng** — bạn không thấy nội dung từng cuộc gọi,
> nhưng thấy *gọi bao nhiêu cuộc, tổng bao lâu, giờ nào, cho những số nào*. Từ hoá đơn đó vẫn đoán được
> nhiều điều về hành vi.

---

## Nó tính ra những con số gì?

Từ mỗi flow, CICFlowMeter trích các nhóm đặc trưng:

- **Thời lượng**: `Flow_Duration` (flow kéo dài bao lâu).
- **Số gói theo hướng**: `Fwd_Packets` (đi), `Bwd_Packets` (về).
- **Thống kê độ dài gói**: trung bình, độ lệch chuẩn, min, max — theo mỗi hướng.
- **IAT (Inter-Arrival Time — thời gian giữa hai gói liên tiếp)**: `Flow_IAT_Mean`, `Fwd_IAT_Std`…
- **Đếm cờ TCP**: SYN, FIN, RST, PSH, ACK, URG — bao nhiêu gói mang mỗi cờ.
- **Tốc độ**: `Flow_Bytes/s`, `Flow_Packets/s`.
- **Active/Idle time** và **cửa sổ TCP (window)**.

Bóc ý nghĩa vài cái:

- **`SYN_flag_count` cao, `FIN` ~0** → nhiều lần "gõ cửa" mà không "chào tạm biệt" đúng cách → mùi **quét cổng**.
- **`Flow_IAT_Mean` rất đều** → gói đến theo nhịp máy móc → mùi **bot/tự động**.
- **`Fwd_Pkt_Len_Max` ~60 byte** → toàn gói bé xíu (chỉ header SYN) → không phải truyền dữ liệu thật.

---

## Ưu điểm lớn nhất: đọc được cả traffic mã hoá

CICFlowMeter **chỉ nhìn metadata (thống kê), không cần mở payload**. Vì thế:

- Với traffic **TLS/HTTPS mã hoá** — nơi nội dung là một mớ bí ẩn — nó **vẫn tính được** duration, kích thước gói, nhịp độ…
- Không cần giải mã, không đụng tới quyền riêng tư nội dung.

> **Nói đơn giản:** không cần biết *người ta nói gì*, chỉ cần biết *họ nói nhanh hay chậm, dài hay ngắn,
> với ai* — thế là đủ để nghi ngờ.

---

## Ví dụ SỐ: PortScan vs Benign web

| Đặc trưng | PortScan | Benign HTTP |
|---|---|---|
| `Flow_Duration` | < 1ms | 100ms – vài giây |
| `Fwd_Pkt_Len_Max` | ~60 byte (chỉ SYN) | 100–1500 byte |
| `SYN_flag_count` | cao | thấp (1/kết nối) |
| Số flow/session | hàng trăm cổng | 1–5 |

Nhìn bảng là thấy: **nhiều đặc trưng cùng "chỉ tay"** về phía PortScan → tách được khỏi Benign.

---

## Giới hạn căn bản — cái nó KHÔNG thấy

Vì chỉ nhìn thống kê 5-tuple, CICFlowMeter **mù với nội dung payload**:

- **Infiltration** (tấn công ẩn trong HTTP GET bình thường) → flow trông y như duyệt web.
- **Heartbleed** (khai thác phần mở rộng TLS handshake) → dấu vết nằm trong payload, không lộ ra thống kê.

> Đây chính là lý do đồ án cần **kết hợp thêm Snort (đọc payload)** và bàn về giới hạn ở Chương 4.

---

## Tóm lại

- CICFlowMeter **biến một flow độ dài bất kỳ thành vector 77–80 con số thống kê** cố định.
- Các nhóm chính: thời lượng, số/độ dài gói, IAT, cờ TCP, tốc độ, active/idle.
- **Mạnh:** chạy được với **traffic mã hoá** (chỉ dùng metadata). **Yếu:** **không thấy payload**
  → bỏ sót tấn công ẩn trong nội dung.

**Hiểu cái này thì làm được gì?** Bạn biết **model đang nhìn cái gì** để đoán — và quan trọng hơn, biết
**nó mù ở đâu**, từ đó giải thích được vì sao một số tấn công (Infiltration, Heartbleed) cần phương pháp khác.
