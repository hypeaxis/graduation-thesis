# Hướng dẫn Cấu hình WSL Ubuntu (Windows 11) làm Victim Testbed

Trong kịch bản tấn công, **Máy 1 (Attacker)** sẽ gửi các gói tin tấn công và luồng traffic nền (Benign) sang **Máy 3 (Ubuntu WSL chạy bên trong Máy 2 - Windows 11)**. Để kịch bản chạy thành công, Máy 3 cần mở một số dịch vụ (Web, SSH, FTP) và cấu hình mạng để Máy 1 có thể "nhìn thấy".

---

## Bước 1: Cấu hình Mạng (Networking) cho WSL2

Mặc định WSL2 trên Windows 11 sử dụng mạng NAT riêng, làm cho Máy 1 khó ping trực tiếp được vào IP của WSL. Cách tốt nhất trên Windows 11 là bật tính năng **Mirrored Networking** (đòi hỏi Windows 11 22H2 trở lên).

1. Trên Windows 11, mở notepad và tạo/chỉnh sửa file ở đường dẫn: `C:\Users\<Tên_User_Của_Bạn>\.wslconfig`
2. Thêm nội dung sau vào file:
   ```ini
   [wsl2]
   networkingMode=mirrored
   hostAddressLoopback=true
   ```
3. Lưu lại và khởi động lại WSL bằng cách mở PowerShell chạy lệnh: `wsl --shutdown`. Lần tới khi mở Ubuntu WSL, nó sẽ dùng chung dải IP LAN với máy Windows 11. *(Nếu Máy 2 có IP là 192.168.0.103 thì Máy 3 cũng lắng nghe trên IP đó)*.

---

## Bước 2: Cài đặt các dịch vụ cần thiết trên Ubuntu WSL

Mở Terminal của Ubuntu WSL và chạy các lệnh cài đặt cơ bản:

### 1. Cài đặt SSH (Phục vụ SSH Brute Force & Traffic Nền)
```bash
sudo apt update
sudo apt install openssh-server -y
# Khởi động SSH
sudo service ssh start
# Đảm bảo SSH chạy đúng ở port 22
```
*Lưu ý: Bạn có thể cần thiết lập mật khẩu cho một user (ví dụ user `root` mật khẩu `password123`) để script hydra tấn công ra kết quả.*

### 2. Cài đặt FTP (Phục vụ FTP Brute Force & Traffic Nền)
```bash
sudo apt install vsftpd -y
# Mở file cấu hình
sudo nano /etc/vsftpd.conf
# Tìm và sửa các dòng sau (bỏ dấu #):
# write_enable=YES
# local_enable=YES
sudo service vsftpd restart
```

### 3. Cài đặt Web Server & DVWA (Phục vụ SQL Injection & Web Brute Force)
Cách dễ nhất để chạy DVWA (Damn Vulnerable Web App) trên WSL là thông qua Docker.

**Cài đặt Docker trên WSL:**
```bash
sudo apt install docker.io -y
sudo systemctl start docker
sudo usermod -aG docker $USER
```
*(Bạn nên tắt WSL đi bật lại để user nhận quyền docker)*

**Chạy DVWA qua Docker:**
```bash
sudo docker run --rm -it -p 80:80 vulnerables/web-dvwa
```
Khi này DVWA sẽ chạy ở cổng 80 của Máy 3 (và tự động phản chiếu ra IP của Máy 2 nếu đã bật Mirrored Network).

---

## Bước 3: Cài đặt Snort và CICFlowMeter (Phục vụ việc Monitor)
Nếu bạn vẫn dùng Snort để dự phòng cảnh báo và CICFlowMeter để bắt gói:

1. **Cài đặt Snort:**
   ```bash
   sudo apt install snort -y
   ```
   *(Nhớ cấu hình dải `HOME_NET` trong `/etc/snort/snort.conf` trỏ về IP của WSL, và copy `local.rules` vào thư mục rules như đã hướng dẫn trước đó)*

2. **Cài đặt CICFlowMeter:**
   Chạy CICFlowMeter trên chính WSL hoặc trên Windows 11 để capture port mạng (eth0/Wi-Fi). Nếu bật Mirrored Mode, bạn bắt trên Windows hay WSL đều được.

---

## Bước 4: Chạy thử nghiệm
Từ **Máy 1 (Attacker)**, bạn chạy lệnh Nmap để quét IP của Windows 11 (Máy 2) xem có thấy các cổng 21 (FTP), 22 (SSH), 80 (HTTP) không.

```bash
nmap -p 21,22,80 <IP_CỦA_MÁY_2>
```

Nếu kết quả trả về là `open`, bạn đã cấu hình thành công! Bây giờ kịch bản tấn công và giả lập traffic nền có thể diễn ra hoàn hảo.
