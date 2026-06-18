# Kế Hoạch Triển Khai Kiến Trúc Sinh Dữ Liệu (Môi trường Windows + WSL)

Dựa trên cấu hình thực tế của bạn (sử dụng WSL - Ubuntu for Windows trên cả 2 laptop), kế hoạch đã được cấu trúc lại hoàn toàn.

**Thách thức lớn nhất với WSL:** Theo mặc định, WSL2 nằm sau một lớp NAT của Windows (IP nội bộ ảo), nên máy tính khác (Laptop 1) không thể "nhìn thấy" hay quét mạng thẳng vào WSL trên Laptop 2 được. 
**Giải pháp:** Chúng ta phải đưa WSL trên Laptop 2 ra cùng mạng vật lý (Bridged Network) thông qua Hyper-V, hoặc dùng tính năng Mirrored Network của Windows 11.

---

## User Review Required

> [!WARNING]
> Môi trường Windows có **Windows Defender Firewall**. Tính năng này mặc định sẽ chặn đứng các cuộc tấn công (như Ping flood, Nmap scan, Brute force) từ Laptop 1 bay vào. 
> Bắt buộc: Bạn phải **tắt tạm thời Firewall** trên Laptop 2 (Hoặc tạo Rule cho phép mọi kết nối đến) trong quá trình thu thập dữ liệu PCAP.

## Open Questions
1. **Phiên bản Windows:** Laptop 2 của bạn đang chạy Windows 10 hay Windows 11? (Windows 11 có tính năng `mirrored` network rất nhàn, còn Windows 10 sẽ phải dùng Hyper-V Manager để làm Bridge).
2. **Cáp mạng / WiFi:** Laptop 1 và Laptop 2 có đang kết nối chung một mạng WiFi / LAN nội bộ không?

---

## Proposed Changes / Kiến Trúc Quy Hoạch

- **Máy 1 (Attacker):** WSL Ubuntu trên Laptop 1.
- **Máy 2 (Capture/Gateway):** Môi trường Windows gốc trên Laptop 2. Chạy phần mềm Wireshark bản Windows.
- **Máy 3 (Victim):** WSL Ubuntu trên Laptop 2. (Sẽ cấu hình dùng chung dải mạng IP vật lý với Windows).

---

### [Phase 1: Máy 3 - Victim (WSL trên Laptop 2)]

Phải cấu hình để mạng của WSL "thông" với bên ngoài. 

#### 1. Cấu hình Mạng (Trên Windows Laptop 2):
**Cách Khuyên Dùng (Nếu dùng Windows 11):**
Mở Notepad (hoặc File Explorer), tạo một file có tên `.wslconfig` nằm tại thư mục gốc của User: `C:\Users\<Tên_User_Của_Bạn>\.wslconfig`.
Thêm nội dung sau vào file:
```ini
[wsl2]
networkingMode=mirrored
```
*(Sau khi lưu, mở PowerShell/CMD chạy lệnh `wsl --shutdown` để khởi động lại WSL. Lúc này WSL sẽ dùng chung IP vật lý của Windows).*

**Cách 2 (Nếu dùng Windows 10 Pro có Hyper-V):**
1. Mở `Hyper-V Manager` trên Windows -> `Virtual Switch Manager`.
2. Tạo mới một `External` virtual switch, trỏ vào card mạng WiFi/LAN vật lý đang dùng. Đặt tên là `WSL_Bridge`.
3. Tạo file `.wslconfig` như trên nhưng với nội dung:
```ini
[wsl2]
networkingMode=bridged
vmSwitch=WSL_Bridge
ipv6=true
```

#### 2. Tắt Firewall trên Laptop 2:
Mở `Windows Security` -> `Firewall & network protection` -> Tắt cả 3 mục (Domain, Private, Public) tạm thời khi thu thập dữ liệu.

#### 3. Chạy Nạn nhân (Trong WSL Laptop 2):
Mở terminal Ubuntu của Máy 3:
```bash
# Cài đặt Docker
sudo apt update
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker $USER

# Chạy mục tiêu giả lập
sudo docker run --rm -d -p 80:80 vulnerables/web-dvwa
```
Dùng lệnh `ip addr` trong WSL để xem IP. (Nếu là Mirrored, nó chính là IP của Laptop 2). Giả sử IP là `192.168.1.100`.

---

### [Phase 2: Máy 2 - Capture (Windows Laptop 2)]

Chịu trách nhiệm bắt lưu lượng khi nó vừa chạm tới card mạng của máy tính trước khi chui vào WSL.

#### 1. Cài đặt Wireshark:
1. Tải và cài đặt Wireshark for Windows (chọn cài đặt kèm theo Npcap).
2. Mở Wireshark lên.

#### 2. Quá trình bắt gói tin:
1. Trong Wireshark, chọn Card mạng vật lý đang kết nối (Card WiFi hoặc Ethernet).
2. Ở thanh Filter (bộ lọc) màu xanh lá phía trên cùng, gõ:
   `ip.addr == 192.168.1.100` *(Thay bằng IP của WSL / Laptop 2)*.
3. Bấm nút Vây cá mập (Start) để bắt đầu bắt gói tin và thu thập file PCAP.

---

### [Phase 3: Máy 1 - Attacker (WSL Laptop 1)]

Tạo ra traffic tấn công.

#### 1. Cài đặt Tools:
Mở terminal Ubuntu trên Laptop 1:
```bash
sudo apt update
sudo apt install nmap hydra sqlmap hping3 python3 python3-pip -y
pip3 install requests slowloris
```

#### 2. Kịch bản Tấn công:
Thực hiện tấn công thẳng vào IP của Máy 3 (Ví dụ: `192.168.1.100`).
```bash
# 1. Quét cổng
nmap -A -T4 192.168.1.100

# 2. Tấn công DoS Slowloris
slowloris 192.168.1.100 -p 80

# 3. Tấn công Web (nếu có lỗ hổng)
hydra -l admin -P /usr/share/wordlists/rockyou.txt 192.168.1.100 http-get /login.php
```

---

## Verification Plan

### Test cấu hình mạng
1. Mở WSL trên Laptop 1, gõ lệnh `ping <IP_Của_WSL_Laptop2>`.
2. Nếu PING thành công -> **Windows Firewall đã tắt và cấu hình mạng WSL thành công.**
3. Mở Wireshark trên Windows Laptop 2, bạn sẽ thấy các dòng giao thức `ICMP` hiện lên màn hình. Lúc này Testbed của bạn đã hoàn hảo để hoạt động!
