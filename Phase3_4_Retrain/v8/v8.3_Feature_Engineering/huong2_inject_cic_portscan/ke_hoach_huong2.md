# Hướng 2 — Inject PortScan từ CIC-IDS-2017

**Ngày lập:** 2026-06-23  
**Ý tưởng:** CIC-IDS-2017 có 158,930 PortScan flows thu trên phần cứng thật (không có WSL blind spot). Inject 5,000 flows vào training set để model học được pattern nmap probe thật sự.

---

## 1. Tài nguyên có sẵn

| Dataset | File | PortScan flows |
|---|---|:-:|
| CIC-IDS-2017 | `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | **158,930** |
| Run10 testbed | `Cleaned_Labeled_Dataset_run10.csv` | 7 (bỏ qua) |

**Không cần thu thêm dữ liệu.** Toàn bộ xử lý trên Máy 1 (máy này).

---

## 2. Thách thức kỹ thuật đã giải quyết

| Vấn đề | Giải pháp |
|---|---|
| CIC dùng tên cột có khoảng trắng (` Flow Duration`) | `feature_mapper.py` rename chính xác theo mapping |
| CIC thiếu Port_Is_* features (5 features) | Tính từ ` Destination Port` trong CIC raw |
| CIC thiếu Custom_* features (7 features) | Tính lại từ đúng công thức trong `dataset_builder_v2.py` |
| `Custom_PortScan_Intensity` cần Src IP + timestamps | Đặt = 0.0 cho toàn bộ CIC (model học từ các features khác) |
| CIC có 78 features, testbed cần 81 | feature_mapper.py bổ sung 3 nhóm còn thiếu |
| CIC Bwd PSH Flags / Bwd URG Flags không có trong EXPECTED_FEATURES_81 | Bỏ hoàn toàn — không cần |

---

## 3. Files đã tạo

| File | Vai trò |
|---|---|
| `feature_mapper.py` | Load CIC raw → rename + tính 81 features → lưu `cic_portscan_mapped.csv` |
| `combine_datasets.py` | Merge run10 (4 class) + CIC PortScan (5k) → `Combined_V8_3_Huong2.csv` |

---

## 4. Quy trình thực hiện

Tất cả chạy trên **Máy 1** (máy này, WSL Ubuntu).

### Bước 1 — Đảm bảo run10 đã được đổi tên

```bash
# Kiểm tra file run10 có sẵn chưa
ls /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/Cleaned_Labeled_Dataset_run10.csv

# Nếu chưa có (chỉ có Cleaned_Labeled_Dataset.csv) thì rename:
cp /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/Cleaned_Labeled_Dataset.csv \
   /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/Cleaned_Labeled_Dataset_run10.csv
```

### Bước 2 — Chạy feature_mapper.py

```bash
cd /home/ning/Graduation-Thesis/Phase3_4_Retrain/v8/v8.3_Feature_Engineering/huong2_inject_cic_portscan

python3 feature_mapper.py
```

**Output:** `cic_portscan_mapped.csv` (~158k rows, 82 columns = 81 features + Label)  
**Thời gian:** ~30-60 giây

Kiểm tra output:
```
[+] Đủ 81 features ✓
[+] Saved: cic_portscan_mapped.csv (158,XXX rows)
Flow_Duration mean: XXX μs   ← kỳ vọng << 500,000 μs (nmap probe ngắn)
RST_Flag_Count mean: X.XX    ← kỳ vọng > 0 (nmap TCP connect gửi RST sau SYN-ACK)
```

### Bước 3 — Chạy combine_datasets.py

```bash
python3 combine_datasets.py
```

**Output:** `Combined_V8_3_Huong2.csv` (~105k rows, 82 columns)

Phân bố kỳ vọng:
```
Benign         : ~52,000  (50%)
Web Attack     : ~25,000  (24%)
DoS            : ~20,000  (19%)
PortScan       :  5,000   (5%)   ← từ CIC-IDS-2017
Brute Force    :  3,000   (3%)
```

### Bước 4 — Verify phân biệt PortScan vs Benign

```python
import pandas as pd

df = pd.read_csv('Combined_V8_3_Huong2.csv')

ps = df[df['Label'] == 'PortScan']
bn = df[df['Label'] == 'Benign']

print("Flow_Duration (μs):")
print(f"  PortScan median : {ps['Flow_Duration'].median():>12,.0f}")
print(f"  Benign   median : {bn['Flow_Duration'].median():>12,.0f}")
# Kỳ vọng: PortScan << Benign

print("\nRST_Flag_Count:")
print(f"  PortScan mean : {ps['RST_Flag_Count'].mean():.3f}")
print(f"  Benign   mean : {bn['RST_Flag_Count'].mean():.3f}")
# Kỳ vọng: PortScan > Benign (nmap gửi RST)
```

---

## 5. Training V8.3 Hướng 2

Dùng training script hiện có (`4c_retrain_focal_v5.py`) với input là `Combined_V8_3_Huong2.csv`.  
Không cần model surgery — vẫn 81 features (hoặc 80 nếu bỏ Custom_PortScan_Intensity), load `v7_model.pt`.

```bash
cd /home/ning/Graduation-Thesis/Phase3_4_Retrain

# Cần kiểm tra --data argument của 4c_retrain_focal_v5.py và điều chỉnh
python3 4c_retrain_focal_v5.py \
    --data v8/v8.3_Feature_Engineering/huong2_inject_cic_portscan/Combined_V8_3_Huong2.csv \
    --model-out v8/v8.3_Feature_Engineering/huong2_inject_cic_portscan/v8_3_huong2_model.pt \
    --epochs 30 \
    --lr 3e-5
```

> **Lưu ý:** Dùng lr thấp hơn (3e-5 thay vì 5e-5) vì domain shift CIC 2017 → testbed 2026. Model cần học PortScan từ CIC nhưng không quên patterns từ run10.

---

## 6. Kỳ vọng kết quả

| Class | V8.2 F1 | Hướng 2 kỳ vọng |
|---|:-:|:-:|
| Benign | 50.8% | > 75% |
| DoS | 91.4% | > 88% |
| Brute Force | 91.9% | > 88% |
| Web Attack | 85.2% | > 83% |
| **PortScan** | **7.5%** | **> 70%** |
| **Macro F1** | **65.4%** | **> 81%** |

---

## 7. Rủi ro và biện pháp

| Rủi ro | Mức độ | Biện pháp |
|---|:-:|---|
| Domain shift CIC 2017 → WSL testbed 2026 | Cao | lr thấp, dropout 0.3+, early stopping |
| `Custom_PortScan_Intensity = 0` cho toàn bộ CIC | Trung bình | Model học từ Flow_Duration và RST_Flag_Count |
| PortScan (5k) nhỏ hơn nhiều so với Benign (52k) | Trung bình | Focal Loss đã handle imbalance; tăng CIC_PS_SAMPLE nếu cần |
| Feature phân phối khác biệt (CIC vs WSL) | Thấp | Batch norm trong FT-Transformer giúp normalize |
