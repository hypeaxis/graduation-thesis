# Covariate Shift — khi "cảm giác đầu vào" đổi, model lạc lối

## Nó sinh ra để giải quyết chuyện gì?

Model của đồ án học rất tốt trên **CIC-IDS-2017**. Nhưng khi đem áp thẳng sang **Testbed (WSL2)** tự dựng,
nó **sụp đổ**: MCC = **−0,015** (còn tệ hơn đoán bừa). Vì sao?

Câu trả lời là **Covariate Shift (dịch chuyển hiệp biến)** — một dạng *domain shift* nơi **phân phối đầu vào
thay đổi**, dù bản chất "cái gì là tấn công" không đổi.

> **So sánh đời thường:** bạn học lái xe trên **sân tập bằng phẳng**, ra **đường thật gồ ghề** thì lúng túng.
> *Luật lái xe* (quan hệ đầu vào → hành động) không đổi, nhưng *cảm giác mặt đường* (đầu vào) đổi hoàn toàn
> → phản xạ cũ không còn khớp.

---

## Công thức — bóc từng mảnh

```
P_source(x) ≠ P_target(x)     nhưng    P(y | x) ≈ không đổi (về lý thuyết)
```

- **`P_source(x)`** → phân phối đặc trưng ở miền nguồn (CIC, thu trên switch Gigabit).
- **`P_target(x)`** → phân phối ở miền đích (Testbed WSL2, qua Hyper-V NAT).
- **`P(y | x)`** → quy luật "đặc trưng này ứng với nhãn kia" — **về lý thuyết vẫn giữ nguyên**.

Vấn đề: model học `P(y|x)` **trên vùng đầu vào của CIC**. Khi đầu vào dịch sang vùng khác (Testbed), model
bị hỏi về những vùng nó **chưa từng thấy khi học** → đoán sai.

---

## Vì sao phân phối đổi? — nguyên nhân cụ thể

| Nguồn gây shift | Ảnh hưởng lên đặc trưng |
|---|---|
| Switch Gigabit (CIC) xử lý frame đầy đủ | baseline "sạch" |
| Card mạng ảo Hyper-V có overhead ảo hoá | thay đổi **packet size** và **timing** |
| NAT của Windows thêm độ trễ, đổi ACK timing | lệch **IAT** và **flag counts** |
| PowerTransformer fit trên phân phối CIC | ánh xạ **sai** khi gặp phân phối Testbed |

> **Nói nôm na:** cùng một cú quét cổng, nhưng đi qua "đường ống" khác (ảo hoá + NAT) thì các con số thống kê
> đo được lệch đi — model nhìn vào thấy "lạ", không nhận ra.

---

## Ví dụ SỐ

Áp model CIC thẳng sang Testbed: **MCC = −0,015**. Con số **âm** không chỉ nói "kém" mà nói **"sai có hệ thống"**
— model phân loại lệch hướng đều đặn, đúng dấu hiệu của covariate shift nghiêm trọng.

---

## Tóm lại

- **Covariate Shift:** `P_source(x) ≠ P_target(x)` trong khi `P(y|x)` về lý thuyết không đổi.
- Trong đồ án: CIC (switch Gigabit) vs Testbed (Hyper-V NAT) tạo phân phối đặc trưng khác nhau → **MCC = −0,015**
  khi transfer trực tiếp.
- Nguyên nhân: ảo hoá + NAT làm đổi packet size, timing, IAT, flag; scaler cũ ánh xạ sai.

**Hiểu cái này thì làm được gì?** Đây là *chẩn đoán bệnh* cho Giai đoạn 3 của đồ án. Hiểu đúng bệnh (đầu vào
dịch, không phải model dốt) mới kê đúng thuốc: [[layer-freezing-catastrophic-forgetting]] và [[model-surgery]] —
và hiểu vì sao [[scaler-embedding-coupling]] khiến "đổi mỗi scaler" lại thất bại.

---

## 🔧 Ánh xạ sang codebase (`Final/`)

Nơi lý thuyết này được **hiện thực trong code** — dùng để phản biện chính xác:

| Vai trò trong code | File · vị trí |
|---|---|
| Chẩn đoán drift phân phối CIC↔Testbed | `Final/03_Testbed_Retrain/retrain/src/check_distribution_drift.py` |
| Thử transfer thẳng / refit scaler | `Final/03_Testbed_Retrain/retrain/domain_adaptation/1_refit_scaler_test.py` |

**Khi phản biện:** MCC âm khi transfer thẳng là **bằng chứng định lượng** của covariate shift; nguyên nhân là ảo hoá + NAT (xem chương phân tích).
