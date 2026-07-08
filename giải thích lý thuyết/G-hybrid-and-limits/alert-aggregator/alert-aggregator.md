# Alert Aggregator — hợp nhất cảnh báo, xác nhận chéo

## Nó sinh ra để giải quyết chuyện gì?

Hệ lai của đồ án có **hai nguồn cảnh báo chạy song song** ([[snort-hybrid-ids]]): Snort (packet-level) và FTT
(flow-level). Nếu cứ để hai luồng cảnh báo đổ thẳng ra màn hình, đội vận hành sẽ **ngập trong thông báo rời rạc**,
khó biết cái nào thật sự quan trọng.

**Alert Aggregator (bộ hợp nhất cảnh báo)** đứng ở cuối, gom hai nguồn lại, **khử trùng lặp** và **nâng độ tin
cậy** khi hai bên cùng chỉ vào một sự việc.

> **So sánh đời thường:** hai bảo vệ tuần tra **độc lập** cùng bấm chuông báo về **một căn phòng** → gần như
> chắc chắn có chuyện thật → trực ban **nâng mức ưu tiên**, cử người tới ngay. Chỉ một người báo thì vẫn ghi
> nhận, nhưng độ chắc thấp hơn.

---

## Cơ chế hợp nhất — bóc từng mảnh

- **Đối chiếu theo session:** hai cảnh báo được coi là "cùng một sự việc" nếu trỏ về **cùng một session**
  (cùng 5-tuple / khoảng thời gian).
- **Confirmed alert (cảnh báo được xác nhận):** nếu **cả Snort và FTT** cùng báo trên một session → hợp nhất
  thành **một** cảnh báo, **mức ưu tiên tăng** (độ tin cậy cao vì hai phương pháp độc lập cùng đồng ý).
- **Single-source alert:** nếu chỉ một nguồn báo → vẫn ghi nhận nhưng ưu tiên thấp hơn.

> **Nói đơn giản:** hai chứng cứ độc lập trùng khớp thì đáng tin hơn nhiều so với một chứng cứ đơn lẻ.

---

## Vì sao "độc lập" là quan trọng?

Snort và FTT nhìn ở **hai tầng khác nhau** (payload vs flow) và **sai theo những kiểu khác nhau**. Khi hai
phương pháp *độc lập về bản chất* cùng chỉ vào một mục tiêu, xác suất **cả hai cùng báo nhầm y hệt** là rất
thấp → tín hiệu đồng thuận **đáng tin cậy**.

Đây là cùng một tinh thần với [[bias-variance-ensemble]]: **nguồn độc lập → đồng thuận có giá trị cao**.

---

## Ví dụ trực giác

- Một tấn công **SQLi**: Snort bắt qua payload; FTT có thể cũng thấy flow bất thường. → Trùng session → **confirmed,
  ưu tiên cao** → đội SOC xử lý trước.
- Một **DoS slow-connection**: chỉ FTT bắt (Snort chưa có rule). → Single-source, vẫn báo nhưng ưu tiên vừa.

---

## Tóm lại

- **Alert Aggregator** gom cảnh báo từ Snort + FTT, đối chiếu theo **session**.
- Cùng session ở **cả hai nguồn** → **confirmed alert**, ưu tiên tăng; một nguồn → vẫn ghi nhận, ưu tiên thấp hơn.
- Giá trị đến từ việc hai nguồn **độc lập** cùng đồng thuận.

**Hiểu cái này thì làm được gì?** Bạn thấy mảnh ghép cuối biến hai model rời rạc thành **một hệ thống vận hành
được** — giảm alert fatigue và làm nổi bật cảnh báo đáng tin. Nối tiếp [[snort-hybrid-ids]].
