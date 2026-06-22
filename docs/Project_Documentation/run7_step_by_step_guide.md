# Hướng Dẫn Thu Thập Dữ Liệu Run7 — Step by Step

> **Mục tiêu**: Dataset ~350,000 flows, tỉ lệ Benign:Attack = 80:20, mỗi loại tấn công ~15k-20k flows
> **Thời gian**: ~60-75 phút
> **Ngày tạo**: 22/06/2026

---

## Kiến trúc hệ thống

```
┌─────────────────────┐          LAN 192.168.0.x          ┌─────────────────────┐
│    MÁY 1 (Attacker) │ ───────────────────────────────── │   MÁY 2 (Win 11)   │
│    Ubuntu WSL       │                                    │   Host OS           │
│    Win 10           │                                    │                     │
│                     │                                    │  ┌───────────────┐  │
│  • auto_attack_v3   │           Mirrored Network         │  │ MÁY 3 (Victim)│  │
│  • auto_benign_v2   │ ──────────────────────────────────▶│  │ Ubuntu WSL    │  │
│  • orchestrator     │                                    │  │ IP: 0.105     │  │
│                     │                                    │  │ DVWA+SSH+FTP  │  │
│  IP: 192.168.0.???  │                                    │  │ tcpdump       │  │
└─────────────────────┘                                    │  └───────────────┘  │
                                                           │  IP: 192.168.0.105  │
                                                           └─────────────────────┘
```

---

# PHẦN A — MÁY 3 (VICTIM) — Làm trước

> [!IMPORTANT]
> **Tất cả các bước dưới đây thực hiện trên Ubuntu WSL của Máy 2 (Win 11)**
> Máy 3 có IP: `192.168.0.105`

## Bước V1: Kiểm tra Mirrored Networking

Trên **Windows 11** (Máy 2), kiểm tra file `C:\Users\<Username>\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
hostAddressLoopback=true
```

Nếu chưa có hoặc chưa đúng → sửa lại → mở PowerShell chạy:
```powershell
wsl --shutdown
```
Rồi mở lại Ubuntu WSL.

**Kiểm tra IP:**
```bash
ip addr show eth0
# Hoặc trên Windows:
ipconfig
# → Phải thấy 192.168.0.105
```

---

## Bước V2: Khởi động các dịch vụ

Mở Terminal Ubuntu WSL trên Máy 3, chạy **từng lệnh**:

### 2a. SSH Server
```bash
sudo service ssh start
sudo service ssh status
# → Phải thấy: * sshd is running
```

### 2b. FTP Server
```bash
sudo service vsftpd start
sudo service vsftpd status
# → Phải thấy: * vsftpd is running
```

### 2c. DVWA (Web App)
```bash
sudo docker start dvwa 2>/dev/null || sudo docker run -d --name dvwa -p 80:80 vulnerables/web-dvwa
```

**Kiểm tra DVWA:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost/DVWA/login.php
# → Phải trả về: 200 hoặc 302
```

> [!TIP]
> Nếu Docker chưa cài: `sudo apt install docker.io -y && sudo systemctl start docker`
> Nếu DVWA image chưa có: `sudo docker pull vulnerables/web-dvwa`

---

## Bước V3: Kiểm tra các port đang mở

```bash
ss -tlnp | grep -E ':(21|22|80)\b'
```

**Kết quả mong muốn** (3 dòng):
```
LISTEN  0  128  *:22    *:*    users:(("sshd",...))
LISTEN  0  32   *:21    *:*    users:(("vsftpd",...))
LISTEN  0  511  *:80    *:*    users:(("apache2",...))  hoặc docker
```

> [!WARNING]
> Nếu thiếu port nào → quay lại Bước V2 kiểm tra service tương ứng.

---

## Bước V4: Chuẩn bị thư mục lưu dữ liệu

```bash
mkdir -p ~/run7_data
cd ~/run7_data
```

---

## Bước V5: Bắt đầu tcpdump (BẮT PACKET)

> [!IMPORTANT]
> **ĐÂY LÀ BƯỚC QUAN TRỌNG NHẤT — PHẢI LÀM TRƯỚC KHI MÁY 1 BẮN TRAFFIC**

```bash
sudo tcpdump -i eth0 -w ~/run7_data/attack_run7.pcap
```

**Để terminal này chạy liên tục, KHÔNG đóng, KHÔNG Ctrl+C.**

Mở thêm 1 tab terminal mới nếu cần thao tác.

> [!TIP]
> Kiểm tra tcpdump đang chạy ở tab khác:
> ```bash
> ps aux | grep tcpdump
> ```

---

## Bước V6: (Tuỳ chọn) Monitor realtime

Mở tab terminal mới trên Máy 3:

```bash
# Xem số packet bắt được theo thời gian thực
watch -n 5 'ls -lh ~/run7_data/attack_run7.pcap'
```

---

## ⏸️ DỪNG TẠI ĐÂY — Chuyển sang Máy 1

> Khi thấy tcpdump đang chạy và file pcap đang tăng kích thước → Máy 3 đã sẵn sàng.
> Giờ chuyển sang **Máy 1** để bắt đầu tấn công.

---
---

# PHẦN B — MÁY 1 (ATTACKER) — Làm sau

> [!IMPORTANT]
> **Chỉ bắt đầu phần này SAU KHI Máy 3 đã chạy tcpdump (Bước V5)**

## Bước A1: Kiểm tra kết nối tới Victim

```bash
ping -c 3 192.168.0.105
```
→ Phải thấy reply, 0% packet loss.

```bash
nmap -p 21,22,80 192.168.0.105
```
→ Phải thấy 3 port **open**:
```
PORT   STATE SERVICE
21/tcp open  ftp
22/tcp open  ssh
80/tcp open  http
```

> [!WARNING]
> Nếu port nào hiện `filtered` hoặc `closed` → quay lại Máy 3 kiểm tra service.

---

## Bước A2: Kiểm tra công cụ tấn công

```bash
# Kiểm tra tất cả tools cần thiết
which nmap hydra sqlmap slowloris curl
```
→ Tất cả phải trả về đường dẫn (không lỗi).

```bash
# Kiểm tra rockyou.txt
ls -lh /usr/share/wordlists/rockyou.txt
```
→ Phải thấy file ~140MB.

```bash
# Kiểm tra hulk.py
ls -l ~/Graduation-Thesis/Custom_IDS_Testbed/scripts/hulk/hulk.py
```

**Nếu thiếu tool nào:**
```bash
sudo apt install nmap hydra sqlmap curl -y
pip3 install requests slowloris --break-system-packages
# Nếu rockyou.txt bị nén:
sudo gunzip /usr/share/wordlists/rockyou.txt.gz
```

---

## Bước A3: Di chuyển tới thư mục scripts

```bash
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
```

---

## Bước A4: CHẠY — Có 2 cách

### Cách 1: Tự động (Khuyến nghị) ⭐

Chạy orchestrator — nó sẽ tự động:
1. Bật benign traffic (50 workers)
2. Đợi 5 phút warm-up
3. Chạy 4 phase tấn công
4. Đợi 10 phút cool-down
5. Dừng benign

```bash
./run7_orchestrator.sh
```

> Bạn chỉ cần ngồi chờ ~60-75 phút.

---

### Cách 2: Thủ công (Nếu muốn kiểm soát từng bước)

**Terminal Tab 1 — Benign Traffic:**
```bash
python3 auto_benign_v2.py --target 192.168.0.105 --workers 50
```
→ Để chạy liên tục, xem progress báo cáo mỗi 30s.

**Terminal Tab 2 — Đợi 5 phút rồi chạy Attack:**
```bash
# Đợi 5 phút sau khi benign bắt đầu
sleep 300

# Chạy toàn bộ 4 phase
python3 auto_attack_v3.py --target 192.168.0.105 --run-name run7
```

**Hoặc chạy từng phase riêng:**
```bash
python3 auto_attack_v3.py --target 192.168.0.105 --run-name run7 --phase portscan
python3 auto_attack_v3.py --target 192.168.0.105 --run-name run7 --phase bruteforce
python3 auto_attack_v3.py --target 192.168.0.105 --run-name run7 --phase webattack
python3 auto_attack_v3.py --target 192.168.0.105 --run-name run7 --phase dos
```

---

## Bước A5: Theo dõi tiến trình

Trong khi chạy, mở tab mới:

```bash
# Xem ground truth log đang ghi
watch -n 10 'wc -l ../docs/ground_truth_log_run7.csv && echo "---" && tail -3 ../docs/ground_truth_log_run7.csv'
```

---

## ⏸️ KHI ATTACK XONG — ĐỢI 10 PHÚT rồi dừng tất cả

---
---

# PHẦN C — SAU KHI THU THẬP XONG

## Bước P1: Dừng các chương trình

### Trên Máy 1 (Attacker):
```bash
# Ctrl+C tại terminal chạy benign traffic (nếu chạy thủ công)
# Orchestrator sẽ tự dừng nếu dùng Cách 1
```

### Trên Máy 3 (Victim):
```bash
# Ctrl+C tại terminal chạy tcpdump
# → File attack_run7.pcap đã được lưu
ls -lh ~/run7_data/attack_run7.pcap
```

---

## Bước P2: Chạy CICFlowMeter trích xuất flow (Trên Máy 3)

```bash
# Chạy CICFlowMeter trên file pcap
sudo /home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm \
    ~/run7_data/attack_run7.pcap \
    ~/run7_data/
```

→ Kết quả: file `attack_run7.pcap_Flow.csv`

```bash
# Kiểm tra kết quả
wc -l ~/run7_data/attack_run7.pcap_Flow.csv
head -2 ~/run7_data/attack_run7.pcap_Flow.csv
```

---

## Bước P3: Copy file CSV về Máy 1

### Cách 1: Qua GitHub
```bash
# Trên Máy 3:
cd ~/Graduation-Thesis
cp ~/run7_data/attack_run7.pcap_Flow.csv docs/
git add docs/attack_capture_run7.pcap_Flow.csv
git commit -m "Add run7 flow data"
git push

# Trên Máy 1:
cd ~/Graduation-Thesis
git pull
```

### Cách 2: Qua SCP (nếu network cho phép)
```bash
# Trên Máy 1:
scp user@192.168.0.105:~/run7_data/attack_run7.pcap_Flow.csv \
    ~/Graduation-Thesis/docs/attack_capture_run7.pcap_Flow.csv
```

### Cách 3: Copy thủ công qua USB/shared folder

---

## Bước P4: Gán nhãn Dataset (Trên Máy 1)

```bash
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts

python3 dataset_builder_v2.py \
    --csv ../../docs/attack_capture_run7.pcap_Flow.csv \
    --ground-truth ../docs/ground_truth_log_run7.csv
```

**Kiểm tra kết quả:**
```bash
python3 -c "
import pandas as pd
df = pd.read_csv('Cleaned_Labeled_Dataset.csv')
print('=== PHÂN BỐ NHÃN RUN7 ===')
print(f'Tổng: {len(df):,} flows')
print()
counts = df['Label'].value_counts()
for label, count in counts.items():
    pct = count / len(df) * 100
    print(f'  {label:15s}: {count:>8,} flows ({pct:5.1f}%)')
print()
benign = counts.get('Benign', 0)
attack = len(df) - benign
print(f'Benign: {benign:,} ({benign/len(df)*100:.1f}%)')
print(f'Attack: {attack:,} ({attack/len(df)*100:.1f}%)')
"
```

**Kết quả mong muốn:**
```
=== PHÂN BỐ NHÃN RUN7 ===
Tổng: ~350,000 flows

  Benign         : ~280,000 flows ( 80.0%)
  DoS            :  ~17,500 flows (  5.0%)
  PortScan       :  ~17,500 flows (  5.0%)
  Brute Force    :  ~17,500 flows (  5.0%)
  Web Attack     :  ~17,500 flows (  5.0%)

Benign: ~280,000 (80.0%)
Attack: ~70,000 (20.0%)
```

---

## Bước P5: Rename và lưu trữ

```bash
# Copy dataset sạch về thư mục chính
cp Cleaned_Labeled_Dataset.csv ~/Graduation-Thesis/docs/run7_dataset.csv
cp Raw_Labeled_Dataset.csv ~/Graduation-Thesis/docs/run7_raw_dataset.csv

# Commit
cd ~/Graduation-Thesis
git add docs/run7_*.csv Custom_IDS_Testbed/docs/ground_truth_log_run7.csv
git commit -m "Add run7 dataset (80-20 balanced)"
git push
```

---

# Checklist nhanh

| # | Bước | Máy | Trạng thái |
|---|------|-----|-----------|
| V1 | Kiểm tra Mirrored Network | Máy 2/3 | ☐ |
| V2 | Khởi động SSH + FTP + DVWA | Máy 3 | ☐ |
| V3 | Kiểm tra ports 21, 22, 80 open | Máy 3 | ☐ |
| V4 | Tạo thư mục ~/run7_data | Máy 3 | ☐ |
| V5 | **Chạy tcpdump** | Máy 3 | ☐ |
| A1 | Ping + Nmap kiểm tra kết nối | Máy 1 | ☐ |
| A2 | Kiểm tra tools (nmap, hydra, sqlmap...) | Máy 1 | ☐ |
| A3 | cd vào thư mục scripts | Máy 1 | ☐ |
| A4 | **Chạy orchestrator hoặc thủ công** | Máy 1 | ☐ |
| A5 | Theo dõi tiến trình | Máy 1 | ☐ |
| P1 | Dừng tất cả chương trình | Cả 2 | ☐ |
| P2 | Chạy CICFlowMeter | Máy 3 | ☐ |
| P3 | Copy CSV về Máy 1 | Cả 2 | ☐ |
| P4 | Gán nhãn (dataset_builder_v2.py) | Máy 1 | ☐ |
| P5 | Lưu trữ + commit | Máy 1 | ☐ |

---

# Xử lý sự cố (Troubleshooting)

| Vấn đề | Nguyên nhân | Cách fix |
|--------|------------|----------|
| Ping victim timeout | WSL chưa bật mirrored | Sửa .wslconfig → wsl --shutdown |
| Port 80 filtered | Firewall Win 11 | Tắt firewall hoặc thêm rule cho port 80 |
| Docker không chạy | Service chưa start | `sudo systemctl start docker` |
| hydra lỗi "could not connect" | Service victim chưa bật | Bật SSH/FTP trên victim |
| tcpdump: permission denied | Thiếu sudo | Chạy với `sudo tcpdump ...` |
| File pcap quá lớn (>10GB) | Traffic quá nhiều | Bình thường, cần ~5-10GB cho 350k flows |
| CICFlowMeter lỗi Java | Sai version Java | Cài `openjdk-8-jdk`, set JAVA_HOME |
| Benign flows quá ít | Victim bị quá tải | Giảm workers xuống 30 |
