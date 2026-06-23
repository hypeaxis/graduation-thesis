# Hướng 1 — Tăng Số Round PortScan (Run11)

**Ngày lập:** 2026-06-23  
**Ý tưởng:** Run10 chỉ có 7 PortScan flows vì WSL chỉ capture open ports (~3-4 port đang mở). Chạy 50 round scan liên tiếp → ~350 flows sạch → dùng SMOTE lên ~2000.

---

## 1. Bối cảnh

Run10 xác nhận: nmap quét 16,000 port nhưng CICFlowMeter chỉ thấy các port ĐANG MỞ:

| Port | Dịch vụ | Số flow / round |
|---|---|:-:|
| 80 | Apache | ~4 |
| 22 | SSH | ~1 |
| 21 | FTP | ~1 |
| **Tổng** | | **~6-7** |

Mỗi round = 1 lần gọi `auto_attack_v3.py --phase portscan` = 3 lần nmap:
- `nmap -sT -T5 -p 1-5000` (~3-4s)
- `nmap -sT -T5 -p 5001-10000` (~3-4s)  
- `nmap -sT -T4 -p 10001-16000` (~4-5s)
- Gap giữa các scan: 8-12s
- **Tổng 1 round: ~35s**

→ 50 round × 7 flows = **~350 PortScan flows sạch**

---

## 2. Chiến lược

```
Run10 (đã có):   Benign 52k + BruteForce 3k + WebAttack 25k + DoS 20k
Run11 (tạo mới): CHỈ PortScan, 50 round, ~350 flows sạch
                          ↓ SMOTE
                       ~2000 flows
Dataset V8.3 = Run10 (4 class) + Run11 (PortScan SMOTE) → Train
```

---

## 3. Script đã tạo: `run11_portscan_boost.sh`

File tại: `Custom_IDS_Testbed/scripts/run11_portscan_boost.sh`

**Điểm quan trọng trong script:**
- Xóa ground truth cũ trước khi chạy (tránh append nhầm từ lần trước)
- Giữa mỗi round: sleep 10s (dataset_builder dùng cửa sổ ±5s, cần ít nhất 5s gap)
- Không chạy benign → 0% contamination
- Tự động đếm PortScan events khi kết thúc

---

## 4. Quy trình thực hiện

### Bước 1 — Máy 3 (Victim — WSL Ubuntu trên Máy 2 Win11)

Mở **2 terminal riêng biệt** trên Máy 3:

```bash
# Terminal 1: Bật services
sudo service apache2 start && sudo service ssh start && sudo service vsftpd start
curl -s -o /dev/null -w "HTTP: %{http_code}\n" http://localhost/
# Kỳ vọng: HTTP: 200

# Terminal 2: Bắt đầu capture (KHÔNG đóng trong suốt quá trình)
sudo tcpdump -i eth0 -w ~/attack_capture_run11.pcap
```

### Bước 2 — Máy 1 (Attacker — WSL Ubuntu Win10, máy này)

```bash
cd /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts
chmod +x run11_portscan_boost.sh
./run11_portscan_boost.sh
```

Ước tính: **~30 phút** (50 round × 35s + overhead).

### Bước 3 — Sau khi xong, Máy 3

```bash
# Terminal 2: Ctrl+C để dừng tcpdump

# Chạy CICFlowMeter
cd ~/CICFlowMeter   # hoặc path cài CICFlowMeter
sudo ./cfm ~/attack_capture_run11.pcap ~/cicflow_output/

# Copy CSV về Máy 1 qua Windows shared folder
cp ~/cicflow_output/attack_capture_run11.pcap_Flow.csv \
   /mnt/c/Users/<username>/Desktop/
```

### Bước 4 — Máy 1: Build dataset

```bash
# Copy file CSV vào docs/
cp /mnt/c/Users/<username>/Desktop/attack_capture_run11.pcap_Flow.csv \
   /home/ning/Graduation-Thesis/docs/

cd /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts

python3 dataset_builder_v2.py \
    --csv /home/ning/Graduation-Thesis/docs/attack_capture_run11.pcap_Flow.csv \
    --ground-truth /home/ning/Graduation-Thesis/Custom_IDS_Testbed/docs/ground_truth_log_run11.csv
```

---

## 5. Verify sau khi build

```python
import pandas as pd

raw = pd.read_csv('/home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/Raw_Labeled_Dataset.csv')

print("=== Phân bố nhãn ===")
print(raw['Label'].value_counts())
# Kỳ vọng: PortScan >= 300, các class khác <= 500 (ít vì không chạy attack khác)

ps = raw[raw['Label'] == 'PortScan']
print("\n=== PortScan Dst Port ===")
print(ps['Destination_Port'].value_counts())
# Kỳ vọng: chỉ port 80/22/21

print("\n=== PortScan Flow_Duration (μs) ===")
print(ps['Flow_Duration'].describe())
# Kỳ vọng: median << 500,000 μs

print("\n=== Src IP (phải chỉ là Attacker) ===")
print(ps['Src IP'].value_counts())
# Kỳ vọng: CHỈ 192.168.0.104
```

---

## 6. Kết hợp Run10 + Run11 và SMOTE

Chạy script sau trên **Máy 1:**

```python
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.preprocessing import LabelEncoder
import numpy as np

SCRIPTS_DIR = '/home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts'

# Lưu Cleaned_Labeled_Dataset.csv của run10 trước khi build run11
# (dataset_builder_v2.py overwrite file này mỗi lần chạy)
# → Rename file run10 ra trước: Cleaned_Labeled_Dataset_run10.csv

run10 = pd.read_csv(f'{SCRIPTS_DIR}/Cleaned_Labeled_Dataset_run10.csv')
run11 = pd.read_csv(f'{SCRIPTS_DIR}/Cleaned_Labeled_Dataset_run11.csv')

# Từ run10: bỏ 7 PortScan (quá ít, không đại diện)
run10_base = run10[run10['Label'] != 'PortScan'].copy()

# Từ run11: chỉ lấy PortScan
run11_ps = run11[run11['Label'] == 'PortScan'].copy()

print(f"Run10 (no PortScan): {len(run10_base)}")
print(f"Run11 PortScan:      {len(run11_ps)}")

# Merge
common_cols = [c for c in run10_base.columns if c in run11_ps.columns]
combined = pd.concat([
    run10_base[common_cols],
    run11_ps[common_cols]
], ignore_index=True)

print("\nTrước SMOTE:")
print(combined['Label'].value_counts())

# SMOTE: tăng PortScan lên 2000
le = LabelEncoder()
X = combined.drop('Label', axis=1).values
y = le.fit_transform(combined['Label'])

ps_label = le.transform(['PortScan'])[0]
smote = SMOTE(
    sampling_strategy={ps_label: 2000},
    k_neighbors=min(5, run11_ps.shape[0] - 1),
    random_state=42
)
X_res, y_res = smote.fit_resample(X, y)

df_res = pd.DataFrame(X_res, columns=combined.drop('Label', axis=1).columns)
df_res['Label'] = le.inverse_transform(y_res)

print("\nSau SMOTE:")
print(df_res['Label'].value_counts())

df_res.to_csv(f'{SCRIPTS_DIR}/Combined_V8_3_Huong1.csv', index=False)
print("\nSaved: Combined_V8_3_Huong1.csv")
```

> **Lưu ý quan trọng:** Trước khi chạy `dataset_builder_v2.py` cho run11, phải **đổi tên file run10** để không bị overwrite:
> ```bash
> cp /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/Cleaned_Labeled_Dataset.csv \
>    /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/Cleaned_Labeled_Dataset_run10.csv
> ```

---

## 7. Training V8.3 Hướng 1

Dùng `4c_retrain_focal_v5.py` với input = `Combined_V8_3_Huong1.csv`.  
Không cần model surgery — vẫn 80 features, load `v7_model.pt` làm khởi điểm.

```bash
cd /home/ning/Graduation-Thesis/Phase3_4_Retrain

python3 4c_retrain_focal_v5.py \
    --data Custom_IDS_Testbed/scripts/Combined_V8_3_Huong1.csv \
    --model-out v8_3_huong1_model.pt \
    --epochs 30 \
    --lr 5e-5
```

---

## 8. Kỳ vọng kết quả

| Class | V8.2 F1 | Hướng 1 kỳ vọng |
|---|:-:|:-:|
| Benign | 50.8% | > 80% F1 |
| DoS | 91.4% | > 90% |
| Brute Force | 91.9% | > 90% |
| Web Attack | 85.2% | > 85% |
| **PortScan** | **7.5%** | **> 60%** |
| **Macro F1** | **65.4%** | **> 80%** |

> Kỳ vọng PortScan F1 ~60-70% do SMOTE synthetic data thiếu diversity (chỉ 3 dst port). Nếu < 50% → chuyển sang Hướng 2.

---

## 9. Rủi ro

| Rủi ro | Mức độ | Biện pháp |
|---|:-:|---|
| SMOTE thiếu diversity (3 dst port) | Cao | Kết hợp Hướng 2 nếu F1 < 50% |
| Model overfit trên 3 open ports | Trung bình | Dropout 0.3+, early stopping |
| Run11 vẫn ít hơn 300 flows | Thấp | Tăng ROUNDS lên 100 trong script |
| `Cleaned_Labeled_Dataset.csv` bị overwrite | Chắc chắn | Rename thành `_run10.csv` trước khi build run11 |
