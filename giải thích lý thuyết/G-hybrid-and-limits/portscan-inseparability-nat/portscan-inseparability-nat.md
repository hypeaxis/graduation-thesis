# PortScan không phân tách dưới NAT — giới hạn của DỮ LIỆU, không phải model

## Nó sinh ra để giải quyết chuyện gì?

Đây là một trong những **bài học sâu sắc nhất** của đồ án: có những thất bại **không thể sửa bằng thuật toán**,
vì gốc rễ nằm ở **cách dữ liệu được thu thập**.

PortScan trên phần cứng thật (CIC) thì **tách được** khỏi Benign. Nhưng khi thu qua **WSL2 + NAT**, nó **trộn
lẫn** vào Benign đến mức **mọi mô hình đều bó tay**.

> **So sánh đời thường:** một **dấu vân tay** vốn nhận diện được. Nhưng nếu bạn photocopy nó qua một máy in
> **nhoè nát**, thì dù thuật toán nhận diện có xịn đến đâu cũng chịu — vì **thông tin đã mất ngay từ khâu thu**.

---

## Trên phần cứng thật (CIC): PortScan TÁCH được

nmap quét qua switch Gigabit → CICFlowMeter thấy **hàng trăm flow TCP SYN ngắn** tới nhiều cổng:

| Đặc trưng | PortScan (CIC) | Benign HTTP |
|---|---|---|
| `Flow_Duration` | < 1ms | 100ms – vài giây |
| `Fwd_Pkt_Len_Max` | ~60 B (SYN) | 100–1500 B |
| `SYN_flag_count` | cao | thấp |
| Số flow/session | hàng trăm | 1–5 |

→ **Nhiều đặc trưng cùng chỉ tay** về PortScan → phân tách rõ ràng.

---

## Dưới WSL2 + NAT: đặc trưng bị PHÁ VỠ

Đường đi của gói tin: `Kali → Router → Windows host → Hyper-V vSwitch → WSL2 eth0`. **NAT xử lý gói trước khi
tới WSL**, gây ra:

1. **Consolidation:** nmap gửi 65.536 SYN → NAT gộp thành **~7 flow** theo session riêng của Hyper-V.
2. **Timing đổi:** overhead ảo hoá thêm độ trễ → `Flow_IAT_Mean` không còn thấp đặc trưng.
3. **Duration tăng:** mỗi "flow" PortScan WSL thành kết nối dài, thay vì hàng trăm kết nối ngắn.
4. **Byte count tăng:** do gộp, mỗi flow mang nhiều gói hơn.

| Đặc trưng | PortScan CIC | **PortScan WSL** | Benign HTTP |
|---|---|---|---|
| `Flow_Duration` | < 1ms | **50–500ms** | 100ms – vài giây |
| Số flow/session | hàng trăm | **~7** | 1–5 |
| Phân biệt với Benign? | **Có** | **KHÔNG** | — |

→ PortScan WSL giờ **trông y như Benign** → không còn ranh giới để học.

---

## Bằng chứng: NHIỀU thuật toán cùng thất bại → lỗi ở dữ liệu

| Cấu hình | PortScan F1 | Kết luận |
|---|---|---|
| FTT, CE Loss | 7,5% | không học được |
| FTT, Focal Loss γ=2 | 6,8% | không phải vấn đề gradient |
| FTT, class_weight ×5 | 8,1% | không cải thiện |
| Random Forest | 5,2% | cùng thất bại |
| KNN | 4,9% | cùng thất bại |
| **FTT + inject CIC PortScan** | **100%** | **giải pháp dữ liệu** |

Khi **nhiều thuật toán với inductive bias khác nhau đều thất bại như nhau**, gần như chắc chắn vấn đề nằm ở
**chất lượng/tính đại diện của dữ liệu**, không phải model. Sửa bằng **dữ liệu surrogate** (tiêm PortScan CIC) → 100%.

> **Nói đơn giản:** không phải model dốt — mà **manh mối đã bị NAT xoá sạch** trước khi model kịp nhìn.

---

## Tóm lại

- PortScan **tách được** trên CIC nhưng **không phân tách** dưới WSL2 vì **NAT gộp flow, đổi timing/duration**
  → giống hệt Benign.
- **Nhiều thuật toán cùng thất bại** = bằng chứng vấn đề ở **dữ liệu thu thập**, không phải model. Giải pháp:
  dữ liệu surrogate (CIC PortScan) → F1 100%.

**Hiểu cái này thì làm được gì?** Bạn nắm một nguyên tắc chẩn đoán vàng: **khi mọi model đều tịt như nhau, hãy
nghi ngờ dữ liệu, không phải thuật toán**. Liên hệ [[focal-loss]] (vô ích ở đây) và khai thác mẫu khó
(cũng bó tay khi không phân tách).

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Tiêm CIC PortScan – gộp dataset | `Final/03_Testbed_Retrain/retrain/v8/v8.3_Feature_Engineering/huong2_inject_cic_portscan/combine_datasets.py` |
| Khớp đặc trưng CIC→Testbed | `Final/03_Testbed_Retrain/retrain/v8/v8.3_Feature_Engineering/huong2_inject_cic_portscan/feature_mapper.py` |
| Train với surrogate data | `Final/03_Testbed_Retrain/retrain/v8/v8.3_Feature_Engineering/huong2_inject_cic_portscan/v8_3_train_huong2.py` |

**Khi phản biện:** giải pháp là **dữ liệu surrogate** (tiêm PortScan từ CIC), đưa F1 lên ~100% — không phải chỉnh thuật toán. Bằng chứng lỗi nằm ở dữ liệu, không phải model.
