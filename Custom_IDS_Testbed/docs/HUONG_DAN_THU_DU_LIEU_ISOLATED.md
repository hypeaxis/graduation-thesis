# Hướng Dẫn Thu Dữ Liệu ISOLATED (cho Replay-based Live Detection)

Tài liệu này hướng dẫn thu **mỗi loại tấn công trong một phiên capture riêng** để tạo
corpus replay cho hệ thống live detection. Mục tiêu: nhãn sạch (0% ambiguous), kiểm soát
được số lượng từng lớp, demo lặp lại được.

> **Vì sao isolated?** Cách thu gộp (run5–10) phải dựa vào bộ gán nhãn time-window ±5s +
> IP + port → benign rơi vào cửa sổ attack bị gán nhầm, sinh ra lớp rác `Ambiguous`.
> Khi mỗi loại thu riêng, ta gán nhãn **theo IP attacker** (đơn giản, sạch). Bạn đã tự
> chứng minh điều này ở run11 (PortScan thuần → **0% ambiguous**).

---

## 0. Hiện trạng — loại nào đã có, loại nào còn thiếu

| Loại | Trạng thái | Nguồn |
|---|---|---|
| **PortScan** | ✅ Đã có (sạch) | `docs/attack_capture_run11.pcap_Flow.csv` (325 PortScan + 253 Benign) |
| **Brute Force** | ❌ **CẦN THU** | hiện chỉ nằm trong run gộp run10 |
| **Web Attack** | ❌ **CẦN THU** | hiện chỉ nằm trong run gộp run10 |
| **DoS** | ❌ **CẦN THU** | hiện chỉ nằm trong run gộp run10 |
| **Benign (baseline riêng)** | ❌ **CẦN THU** | chưa có phiên benign-thuần dài để làm nền liên tục |

→ **Cần thu thêm 4 phiên:** `bruteforce`, `webattack`, `dos`, `benign`.
PortScan chỉ thu lại nếu muốn demo dài hơn 325 flow.

---

## 1. Chuẩn bị (làm 1 lần)

### 1.1. Sơ đồ 2 máy
- **Máy 1 (Attacker):** WSL Ubuntu trên Win10, IP `192.168.0.106` — chạy `collect_isolated.sh`.
- **Máy 3 (Victim):** WSL Ubuntu trên Win11, IP `192.168.0.103` — chạy `tcpdump` + dịch vụ mục tiêu.

> ⚠️ **Giữ IP cố định** suốt cả 4 phiên. Nhãn được gán theo IP attacker nên IP đổi giữa chừng sẽ làm hỏng nhãn.

### 1.2. Trên Máy 3 (Victim) — bật dịch vụ mục tiêu
```bash
sudo service apache2 start    # DVWA / web (port 80)  → cho Web Attack
sudo service ssh start        # SSH (port 22)         → cho Brute Force
sudo service vsftpd start     # FTP (port 21)         → cho Brute Force
# (hoặc: cd Custom_IDS_Testbed/configs && sudo docker-compose up -d)
```

### 1.3. Trên Máy 1 (Attacker) — cài công cụ & cấp quyền chạy
```bash
sudo apt update && sudo apt install -y nmap hydra sqlmap curl tcpdump
pip3 install slowloris
sudo gunzip -k /usr/share/wordlists/rockyou.txt.gz   # nếu chưa giải nén
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
chmod +x collect_isolated.sh
```

---

## 2. Quy trình thu từng loại

Mỗi loại = **1 phiên tcpdump riêng → 1 pcap riêng → 1 Flow.csv riêng** (không flow-bleed).
Quy ước: **Máy 3 = Victim** (`192.168.0.103`), **Máy 1 = Attacker** (`192.168.0.106`).

> **Khung 4 bước chung** (mọi loại đều theo): **(A)** Victim bật tcpdump riêng → **(B)**
> Attacker chạy `collect_isolated.sh` → **(C)** Victim Ctrl+C dừng tcpdump rồi chạy
> CICFlowMeter → **(D)** copy `*_Flow.csv` về `~/Graduation-Thesis/docs/` trên Máy 1.
> Bên dưới là lệnh **đầy đủ, điền sẵn** cho từng loại — làm tuần tự từng loại một.

---

### 2.1. PortScan ✅ (đã có run11 — chỉ thu lại nếu muốn nhiều flow hơn)

- **Dịch vụ Victim cần bật:** không cần dịch vụ cụ thể (chỉ quét cổng), chỉ cần máy bật.
- **Tool:** `nmap -sT` cổng 1–16000 · **Thời gian:** ~5 phút · **Kỳ vọng:** vài nghìn flow PortScan.

```bash
# (A) MÁY 3 — Victim:
sudo tcpdump -i eth0 -w ~/portscan_only.pcap

# (B) MÁY 1 — Attacker:
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
./collect_isolated.sh --type portscan

# (C) MÁY 3 — Victim (sau khi script báo xong): Ctrl+C dừng tcpdump, rồi:
sudo ./cfm ~/portscan_only.pcap ~/cicflow/

# (D) Copy về Máy 1:
cp ~/cicflow/portscan_only.pcap_Flow.csv /mnt/c/Users/<ban>/Desktop/
#   trên Máy 1:
cp /mnt/c/Users/<ban>/Desktop/portscan_only.pcap_Flow.csv ~/Graduation-Thesis/docs/
```

---

### 2.2. Brute Force (SSH + FTP)

- **Dịch vụ Victim cần bật:** SSH (22) + FTP (21).
- **Tool:** `hydra` + rockyou trên SSH/FTP · **Thời gian:** ~20 phút · **Kỳ vọng:** ~16k–20k flow.

```bash
# (A) MÁY 3 — Victim: bật dịch vụ rồi tcpdump
sudo service ssh start && sudo service vsftpd start
sudo tcpdump -i eth0 -w ~/bruteforce_only.pcap

# (B) MÁY 1 — Attacker:
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
./collect_isolated.sh --type bruteforce

# (C) MÁY 3 — Victim: Ctrl+C dừng tcpdump, rồi:
sudo ./cfm ~/bruteforce_only.pcap ~/cicflow/

# (D) Copy về Máy 1:
cp ~/cicflow/bruteforce_only.pcap_Flow.csv /mnt/c/Users/<ban>/Desktop/
cp /mnt/c/Users/<ban>/Desktop/bruteforce_only.pcap_Flow.csv ~/Graduation-Thesis/docs/
```

---

### 2.3. Web Attack (HTTP Brute + SQLi + XSS)

- **Dịch vụ Victim cần bật:** Apache/DVWA (cổng 80).
- **Tool:** `hydra http` + `sqlmap` + `curl` burst · **Thời gian:** ~15 phút · **Kỳ vọng:** ~14k–20k flow.

```bash
# (A) MÁY 3 — Victim: bật web rồi tcpdump
sudo service apache2 start          # đảm bảo DVWA truy cập được ở http://<victim>/DVWA/
sudo tcpdump -i eth0 -w ~/webattack_only.pcap

# (B) MÁY 1 — Attacker:
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
./collect_isolated.sh --type webattack

# (C) MÁY 3 — Victim: Ctrl+C dừng tcpdump, rồi:
sudo ./cfm ~/webattack_only.pcap ~/cicflow/

# (D) Copy về Máy 1:
cp ~/cicflow/webattack_only.pcap_Flow.csv /mnt/c/Users/<ban>/Desktop/
cp /mnt/c/Users/<ban>/Desktop/webattack_only.pcap_Flow.csv ~/Graduation-Thesis/docs/
```

---

### 2.4. DoS (Hulk + Slowloris)

- **Dịch vụ Victim cần bật:** Apache (cổng 80).
- **Yêu cầu Attacker:** có sẵn `hulk/hulk.py` (đã nằm trong repo) + `pip3 install slowloris`.
- **Tool:** `hulk` + `slowloris` · **Thời gian:** ~5 phút · **Kỳ vọng:** ~15k–20k flow.
- ⚠️ Đây là ca model **yếu nhất** (domain shift) — đừng để cuối demo, hoặc để cuối kèm giải thích.

```bash
# (A) MÁY 3 — Victim:
sudo service apache2 start
sudo tcpdump -i eth0 -w ~/dos_only.pcap

# (B) MÁY 1 — Attacker:
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
./collect_isolated.sh --type dos

# (C) MÁY 3 — Victim: Ctrl+C dừng tcpdump, rồi:
sudo ./cfm ~/dos_only.pcap ~/cicflow/

# (D) Copy về Máy 1:
cp ~/cicflow/dos_only.pcap_Flow.csv /mnt/c/Users/<ban>/Desktop/
cp /mnt/c/Users/<ban>/Desktop/dos_only.pcap_Flow.csv ~/Graduation-Thesis/docs/
```

---

### 2.5. Benign baseline (KHÔNG chạy attack)

- **Dịch vụ Victim cần bật:** bật **HẾT** (apache2 + ssh + vsftpd) để traffic benign đa dạng.
- **Tool:** `auto_benign_v2.py` · **Thời gian:** ~10 phút (`--duration 600`) · **Kỳ vọng:** vài nghìn
  flow benign, **không** có flow xuất phát từ `192.168.0.106`.
- ⚠️ Tuyệt đối **không** chạy bất kỳ tấn công nào song song trong phiên này.

```bash
# (A) MÁY 3 — Victim: bật hết dịch vụ rồi tcpdump
sudo service apache2 start && sudo service ssh start && sudo service vsftpd start
sudo tcpdump -i eth0 -w ~/benign_only.pcap

# (B) MÁY 1 — Attacker:
cd ~/Graduation-Thesis/Custom_IDS_Testbed/scripts
./collect_isolated.sh --type benign --duration 600

# (C) MÁY 3 — Victim: Ctrl+C dừng tcpdump, rồi:
sudo ./cfm ~/benign_only.pcap ~/cicflow/

# (D) Copy về Máy 1:
cp ~/cicflow/benign_only.pcap_Flow.csv /mnt/c/Users/<ban>/Desktop/
cp /mnt/c/Users/<ban>/Desktop/benign_only.pcap_Flow.csv ~/Graduation-Thesis/docs/
```

---

## 3. Gán nhãn (label-by-IP — sạch, không cần time-window)

Vì mỗi file isolated chỉ có 1 loại, gán nhãn theo IP cực đơn giản:

- **File attack** (`<loại>_only.pcap_Flow.csv`): flow có `Src IP == 192.168.0.106`
  (attacker) → nhãn = `<loại>`; còn lại (phản hồi victim, nền) → `Benign`.
- **File benign** (`benign_only.pcap_Flow.csv`): toàn bộ → `Benign`.

> Đây là phần sẽ được build cùng `live_replay_server.py` (engine replay đọc raw Flow.csv,
> tự gán `true_label` theo IP để overlay accuracy trên dashboard). Bạn **không** cần dùng
> `dataset_builder_v2.py` (matcher time-window) cho corpus replay.

---

## 4. Kiểm tra chất lượng sau mỗi phiên

Sau khi copy Flow.csv về `docs/`, kiểm tra nhanh:
```bash
cd ~/Graduation-Thesis/docs
# Số flow và số IP nguồn (kỳ vọng: chủ yếu attacker + victim)
python3 - <<'PY'
import pandas as pd, glob
for f in sorted(glob.glob('*_only.pcap_Flow.csv')):
    df = pd.read_csv(f); df.columns = df.columns.str.strip()
    print(f, '| flows:', len(df), '| Src IP top:', df['Src IP'].value_counts().head(3).to_dict())
PY
```
Tiêu chí đạt:
- File attack: phần lớn flow đi từ/đến IP attacker `192.168.0.106`. Tổng flow > vài trăm.
- File benign: KHÔNG có flow từ IP attacker; đa dạng port/đích là tốt.

---

## 5. Checklist hoàn thành corpus replay

- [ ] `bruteforce_only.pcap_Flow.csv` (trong `docs/`)
- [ ] `webattack_only.pcap_Flow.csv`
- [ ] `dos_only.pcap_Flow.csv`
- [ ] `benign_only.pcap_Flow.csv` (≥ 5 phút, không attack)
- [x] PortScan: dùng `attack_capture_run11.pcap_Flow.csv` (đã có) — *hoặc* thu lại
      `portscan_only` nếu cần dài hơn: `./collect_isolated.sh --type portscan`

Khi đủ 4 file mới + PortScan → sẵn sàng nạp vào `live_replay_server.py` để demo theo kịch
bản: **benign nền liên tục → tiêm dần PortScan → Brute Force → Web Attack → DoS**.

---

## 6. Lưu ý quan trọng

1. **Không bật benign khi thu attack**, và không bật attack khi thu benign. Việc trộn
   "benign nền + attack" được làm lúc **replay**, không phải lúc capture → giữ nhãn sạch.
2. **Mỗi loại một pcap riêng** — đừng dùng chung 1 file tcpdump cho nhiều loại (tránh
   flow-bleed ở ranh giới).
3. **Thứ tự demo:** cân nhắc không để DoS/Slowloris ở cuối (ca model yếu nhất do domain
   shift), hoặc để cuối kèm giải thích học thuật.
4. **Trung thực trong báo cáo:** đây là *replay-based live detection* (mô phỏng luồng đến
   từ dữ liệu đã thu), không phải real-time capture thuần.
