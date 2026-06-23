# Kế hoạch V8.3 — Feature Engineering (Clean PortScan Data)

**Ngày lập:** 2026-06-23  
**Mục tiêu:** Thu thập dữ liệu PortScan sạch để mô hình học được tín hiệu phân biệt thật sự, đạt Macro F1 > 83%.

---

## 0. Sơ đồ hạ tầng Testbed

```
┌─────────────────────────┐        ┌──────────────────────────────────────┐
│  MÁY 1 (Attacker)       │        │  MÁY 2 (Windows 11)                  │
│  Windows 10             │        │                                       │
│  WSL Ubuntu             │        │   ┌──────────────────────────────┐    │
│  IP: 192.168.0.104      │◄──────►│   │  MÁY 3 (Victim)              │    │
│                         │        │   │  WSL Ubuntu trên Máy 2       │    │
│  Chạy:                  │        │   │  IP: 192.168.0.102           │    │
│  - auto_attack_v3.py    │        │   │                              │    │
│  - auto_benign_v2.py    │        │   │  Chạy:                       │    │
│  - orchestrator         │        │   │  - tcpdump                   │    │
│  - dataset_builder_v2.py│        │   │  - CICFlowMeter              │    │
│  - training scripts     │        │   │  - Apache/SSH/FTP (targets)  │    │
└─────────────────────────┘        │   └──────────────────────────────┘    │
                                   └──────────────────────────────────────┘
```

> **Máy Dev = Máy 1.** Tất cả xử lý dữ liệu và training đều chạy tại đây.

---

## 1. Bối cảnh & Kết luận từ V8.1 / V8.2

| Version | Phương pháp | PortScan F1 | Macro F1 | Kết luận |
|---|---|:-:|:-:|---|
| V8.1 | Threshold Calibration | 6.7% | 63% | Feature overlap → không thể tách |
| V8.2 | Cost-Sensitive Loss ×12 | 7.5% | 65% | Y hệt V8.1 → xác nhận overlap |

**Kết luận khoa học:** PortScan và Benign không thể phân tách trong không gian 80 chiều hiện tại.

---

## 2. Chẩn đoán nguyên nhân gốc rễ

### 2.1 Vấn đề WSL — closed-port RST bị chặn (Run8 & Run9)

`nmap -sT -p 1-16000` gửi 16,000 SYN nhưng CICFlowMeter trên Máy 3 chỉ capture **5–6 unique dst port**:

```
Kỳ vọng:  1 Src IP → 16,000 dst port → intensity >> 100
Thực tế:  1 Src IP →       5 dst port → intensity = 5
```

**Nguyên nhân:** WSL Mirrored Mode trên Máy 2 (Win11) — Windows TCP/IP stack của Máy 2 xử lý RST cho closed port trước khi packet vào eth0 của Máy 3. CICFlowMeter không thấy closed-port flows **dù đã tắt Windows Firewall**.

→ `Custom_PortScan_Intensity` (unique port count) **không khả thi** trong môi trường WSL.

### 2.2 Vấn đề Label Contamination — nguyên nhân chính (Run9)

`auto_benign_v2.py` chạy trên **Máy 1** (192.168.0.104), sinh HTTP request đến **Máy 3** (192.168.0.102:80). `dataset_builder_v2.py` label mọi flow từ `Dst IP = 192.168.0.102` trong time window là PortScan:

```
Class PortScan trong Run9 (1296 flows):
  ├── 1099 flows (84.8%): auto_benign HTTP bị label nhầm  ← VẤN ĐỀ
  │     Src IP = 192.168.0.104, Dst = 80, Duration ≈ 9s, FIN close
  └──  197 flows (15.2%): nmap probe thật
        Src IP = 192.168.0.104, Dst = 21/22/20, Duration ≈ 64ms
```

**Hệ quả:** 84.8% class PortScan trông y hệt Benign HTTP → model không thể học.

> **Tại sao không chạy benign từ Máy 3?**  
> `auto_benign_v2.py` trên Máy 3 (192.168.0.102) crawl chính Máy 3 (192.168.0.102).  
> Traffic tự kết nối (Src = Dst = 192.168.0.102) đi qua loopback, **không qua eth0**.  
> CICFlowMeter lắng nghe eth0 sẽ không capture được → mất toàn bộ benign data.

### 2.3 Tín hiệu phân biệt CÓ TỒN TẠI trong 197 nmap probe thật

| Feature | Nmap probe thật | Benign | DoS |
|---|:-:|:-:|:-:|
| `Flow_Duration` | **64 ms** | 16,684 ms | 7,692 ms |
| `Total_Length_Fwd_Packets` | **164 bytes** | 498 bytes | — |
| Tỉ lệ | **260× thấp hơn Benign** | baseline | — |

→ Nếu loại bỏ contamination, `Flow_Duration` đủ để phân biệt hoàn toàn.

---

## 3. Giải pháp: Tách thời điểm PortScan khỏi Benign

### Nguyên lý

Thay vì thay đổi **nơi** chạy benign (không khả thi do WSL loopback), thay đổi **thời điểm** chạy benign:

```
TRƯỚC (sai — Run7/8/9):
  Timeline: [Benign ON] ──────────────────────────────────────────────────
            [Attack   ] ──[PortScan]──[BruteForce]──[WebAttack]──[DoS]──

  Kết quả: Benign chạy ĐỒNG THỜI với PortScan → contamination

SAU (đúng — Run10):
  Timeline: [Benign OFF] [PortScan] [gap] [Benign ON] ──────────────────
            [Attack    ] ─────────────────[BruteForce]──[WebAttack]──[DoS]

  Kết quả: PortScan chạy KHI KHÔNG CÓ BENIGN → 0% contamination
```

`dataset_builder_v2.py` dùng cửa sổ `±5 giây`. Nếu benign bắt đầu sau khi PortScan kết thúc tối thiểu 10 giây → không có flow benign nào bị label nhầm thành PortScan.

---

## 4. Thay đổi cần thực hiện

### 4.1 Sửa `auto_attack_v3.py` — chạy PortScan độc lập trước

Hiện tại `auto_attack_v3.py` chạy tuần tự: PortScan → BruteForce → WebAttack → DoS.  
Orchestrator cần tách PortScan ra chạy riêng trước khi start benign.

`auto_attack_v3.py` đã hỗ trợ `--phase` argument:
```bash
python3 auto_attack_v3.py --target IP --run-name NAME --phase portscan
python3 auto_attack_v3.py --target IP --run-name NAME --phase bruteforce
# ... etc.
```

### 4.2 Tạo `run10_orchestrator.sh` — thứ tự mới

Thay đổi so với `run9_orchestrator.sh`:
- **Bỏ** warm-up benign ở đầu
- **Thêm** phase: chạy PortScan trước khi start benign
- **Giữ** benign chạy cùng với BruteForce/WebAttack/DoS như cũ

Cấu trúc orchestrator mới:

```bash
# [PHASE 0] Chạy PortScan TRƯỚC — không có benign
echo "[PHASE 0] PortScan (no benign)..."
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase portscan --skip-check

# Chờ 30 giây để đảm bảo cửa sổ ±5s không overlap
echo "Chờ 30s trước khi bật benign..."
sleep 30

# [PHASE 1] Bật benign traffic
echo "[PHASE 1] Bắt đầu benign traffic..."
python3 auto_benign_v2.py --target $TARGET --workers $BENIGN_WORKERS &
BENIGN_PID=$!

# Warm-up benign 5 phút
sleep 300

# [PHASE 2-4] Các tấn công còn lại với benign đang chạy
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase bruteforce --skip-check
sleep 30
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase webattack --skip-check
sleep 30
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase dos --skip-check

# Cool-down 10 phút
sleep 600

# Dừng benign
kill $BENIGN_PID
```

> **Lưu ý về Ground Truth:** `auto_attack_v3.py` ghi `ground_truth_log_run10.csv` theo từng `--phase`. Cần đảm bảo tất cả phase đều append vào cùng 1 file (không ghi đè). Kiểm tra logic `run_attack()` trong `auto_attack_v3.py` — hiện tại mở file theo mode `'w'` (overwrite). **Cần sửa thành `'a'` (append) cho run10.**

---

## 5. Sửa `auto_attack_v3.py` — append ground truth thay vì overwrite

Kiểm tra phần mở file log trong `auto_attack_v3.py` và sửa mode từ `'w'` → `'a'` khi chạy theo phase, hoặc thêm flag `--append-log`.

---

## 6. Quy trình thu thập Run10

### Thứ tự thực hiện

**Máy 3 (WSL Ubuntu trên Máy 2 - Win11) — Mở 3 terminal:**

```bash
# Terminal 1 — Bật dịch vụ
sudo service apache2 start && sudo service ssh start && sudo service vsftpd start
curl -s -o /dev/null -w "HTTP: %{http_code}\n" http://localhost/

# Terminal 2 — Bắt đầu capture (KHÔNG đóng suốt quá trình)
sudo tcpdump -i eth0 -w ~/attack_capture_run10.pcap
```

**Máy 1 (WSL Ubuntu - Win10, máy này):**

```bash
cd /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts
./run10_orchestrator.sh
# Ước tính: ~70–80 phút tổng
```

**Sau khi orchestrator hoàn tất — Máy 3:**

```bash
# Terminal 2: Ctrl+C để dừng tcpdump

# Chạy CICFlowMeter
cd /path/to/CICFlowMeter
sudo ./cfm ~/attack_capture_run10.pcap ~/cicflow_output/

# Copy về Máy 1 (qua shared Windows folder hoặc scp)
cp ~/cicflow_output/attack_capture_run10.pcap_Flow.csv \
   /mnt/c/Users/<username>/Desktop/
```

**Máy 1 — Build dataset:**

```bash
# Copy file CSV vào docs/
cp /mnt/c/Users/<username>/Desktop/attack_capture_run10.pcap_Flow.csv \
   /home/ning/Graduation-Thesis/docs/attack_capture_run10.pcap_Flow.csv

cd /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts
python3 dataset_builder_v2.py \
    --csv ../../docs/attack_capture_run10.pcap_Flow.csv \
    --ground-truth ../docs/ground_truth_log_run10.csv
```

---

## 7. Verify sau khi build dataset

Chạy trên **Máy 1:**

```python
import pandas as pd

raw = pd.read_csv('/home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/Raw_Labeled_Dataset.csv')

# Kiểm tra 1: contamination đã hết chưa
ps = raw[raw['Label']=='PortScan']
print("PortScan Dst Ports:", ps['Destination_Port'].value_counts().to_dict())
# KỲ VỌNG: port 80 <= 10 flows (chỉ nmap probe, KHÔNG có benign HTTP)

# Kiểm tra 2: Flow_Duration discriminative
print(raw.groupby('Label')['Flow_Duration'].agg(['mean','median']).round(0))
# KỲ VỌNG: PortScan mean << 500,000 μs | Benign mean >> 5,000,000 μs

# Kiểm tra 3: phân bố nhãn
print(raw['Label'].value_counts())
# KỲ VỌNG: PortScan >= 200 flows (clean nmap probes)
```

---

## 8. Kế hoạch Training V8.3 (sau khi có Run10 sạch)

### 8.1 Feature mới: `Custom_Short_RST_Probe`

Dù `Flow_Duration` đã đủ discriminative, thêm 1 binary feature giúp model học nhanh hơn:

```python
# Trong dataset_builder_v2.py — thêm vào hàm extract_custom_features()
df['Custom_Short_RST_Probe'] = (
    (df['Flow_Duration'] < 500_000) &  # Flow ngắn < 500ms
    (df['RST_Flag_Count'] >= 1)        # Đóng bằng RST (nmap pattern)
).astype(float)
# Feature 81: = 1.0 cho nmap probes, = 0.0 cho HTTP/SSH/benign flows
```

### 8.2 Model Surgery: 80 → 81 features

```python
# Load v7_model.pt (80 features)
model_old = FTTransformer(num_features=80, ...)
model_old.load_state_dict(torch.load('v7_model.pt'))

# Tạo model mới với 81 features
model_new = FTTransformer(num_features=81, ...)

# Copy 80 embedding weights cũ
model_new.feature_tokenizer.weight.data[:80] = \
    model_old.feature_tokenizer.weight.data[:80]
# Feature thứ 81: random init (đã được khởi tạo mặc định)

# Unfreeze toàn bộ và train
```

### 8.3 Training data

| Dataset | Vai trò |
|---|---|
| Run10 (clean) | PortScan sạch — dùng làm PortScan training source |
| Run7 train split | DoS / BruteForce / WebAttack / Benign — giữ nguyên |
| Kết hợp | Mixed train set đủ 5 class |

### 8.4 Kỳ vọng kết quả

| Class | V8.2 F1 | V8.3 F1 (kỳ vọng) |
|---|:-:|:-:|
| Benign | 50.8% | > 80% |
| DoS | 91.4% | > 90% |
| Brute Force | 91.9% | > 90% |
| Web Attack | 85.2% | > 85% |
| **PortScan** | **7.5%** | **> 70%** |
| **Macro F1** | **65.4%** | **> 83%** |

---

## 9. Fallback nếu Run10 vẫn ít PortScan data

Nếu sau fix chỉ có ~200 nmap flows (quá ít):

1. **Tăng số round scan:** sửa `phase_portscan()` trong `auto_attack_v3.py` thêm nhiều range scan hơn hoặc lặp lại nhiều lần.
2. **SMOTE chỉ trên clean PortScan:** augment từ 200 → 2000 flows (sau khi đã loại contamination).
3. **Chấp nhận kết quả V8.2 làm final:** document WSL limitation là novel academic finding, đề xuất hardware testbed cho future work.

---

## 10. Danh sách files cần tạo / sửa

| File | Hành động | Máy thực hiện |
|---|---|---|
| `run10_orchestrator.sh` | **TẠO MỚI** — PortScan trước, benign sau | Máy 1 |
| `auto_attack_v3.py` | **SỬA** — mode append log khi dùng `--phase` | Máy 1 |
| `dataset_builder_v2.py` | **SỬA** — thêm `Custom_Short_RST_Probe` (feature 81) | Máy 1 |
| `v8.3_training_script.py` | **TẠO MỚI** — model surgery 80→81, train | Máy 1 |
| `auto_benign_v2.py` | Không sửa | — |
| `auto_attack_v3.py` PortScan phase | Không sửa | — |
