# Snort + FT-Transformer — hệ lai bù điểm mù cho nhau

## Nó sinh ra để giải quyết chuyện gì?

Không một phương pháp nào bắt được **mọi** kiểu tấn công. Đồ án ghép **hai hướng đối lập** để chúng che điểm
mù cho nhau:

- **Snort** — hệ **dựa luật (rule-based)**, soi ở tầng **gói tin (packet: payload + header)**.
- **FT-Transformer** — hệ **học máy (ML-based)**, soi ở tầng **flow (thống kê 5-tuple)**.

> **So sánh đời thường:** như phối hợp **chó nghiệp vụ đánh hơi** (Snort — nhận ra *mùi đã biết* cực nhanh, cực
> chính xác) với **camera AI phân tích hành vi** (FTT — phát hiện *bất thường mới lạ* chưa có trong danh sách).
> Mỗi bên giỏi một kiểu.

---

## So sánh hai hướng — bóc từng mảnh

| Tiêu chí | Snort (rule-based) | FT-Transformer (ML-based) |
|---|---|---|
| Tầng phân tích | Packet (payload + header) | Flow (thống kê 5-tuple) |
| Độ trễ | Microsecond (real-time) | Vài giây (near-realtime) |
| Tấn công **đã biết** | Rất tốt | Tốt |
| Tấn công **chưa có luật** | **Không** | **Có** |
| Traffic **mã hoá** | **Không** (cần đọc payload) | **Có** (chỉ dùng metadata) |
| Nhạy **covariate shift** | Không | Có |

→ Nhìn bảng thấy rõ: **chỗ Snort mù thì FTT sáng, và ngược lại**.

---

## Vì sao KẾT HỢP thay vì chọn một?

Ba ví dụ bổ sung điển hình:

- **Snort bắt XSS/SQLi** qua payload HTTP body → FTT bỏ sót (vì flow statistics giống Benign HTTP bình thường).
- **FTT bắt DoS slow-connection** qua flow duration và IAT bất thường → Snort bỏ sót nếu chưa có rule cho
  slow-rate DoS đó.
- **FTT bắt BruteForce SSH** qua số kết nối TCP thất bại → Snort bỏ sót nếu công cụ tấn công không khớp signature.

> **Nói đơn giản:** Snort mạnh ở "đã biết mặt điểm tên", FTT mạnh ở "ngửi thấy điều bất thường lạ". Gộp lại
> mới phủ được cả hai loại.

---

## Kiến trúc chạy song song

Hai thành phần chạy **độc lập, song song** trên cùng một luồng traffic:

```
Traffic → interface ┬─▶ Snort (packet-level, real-time)         ─┐
                    └─▶ tcpdump → CICFlowMeter → PowerTransformer → FTT ─┴─▶ Alert Aggregator → Dashboard
```

Kết quả từ hai nguồn được [[alert-aggregator]] hợp nhất.

---

## Tóm lại

- **Hệ lai** = **Snort** (rule-based, packet, đã biết, real-time) + **FTT** (ML, flow, chưa biết, mã hoá) chạy
  **song song, độc lập**.
- Kết hợp vì **điểm mù bù nhau**: Snort bắt XSS/SQLi (payload); FTT bắt DoS chậm & BruteForce (flow) và tấn
  công chưa có luật.

**Hiểu cái này thì làm được gì?** Bạn giải thích được **triết lý thiết kế tổng thể** của đồ án — không tôn thờ
một phương pháp, mà ghép để phủ điểm mù. Đầu ra hợp nhất bởi [[alert-aggregator]]; giới hạn còn lại nằm ở
[[static-flow-limits-temporal]].
