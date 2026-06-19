# Kế Hoạch Thực Thi Từng Bước Lắp Đặt & Vận Hành Testbed (Hybrid IDS)

Tài liệu này cung cấp hướng dẫn ở mức **"cầm tay chỉ việc"** (Step-by-Step), liệt kê chính xác cần tải gì, ở đâu, và chạy lệnh nào vào lúc nào trên 2 máy tính để mô phỏng lại hệ thống Custom IDS.

---

> [!IMPORTANT]
> **Định Nghĩa Các Thực Thể (Máy 1, Máy 2, Máy 3)**
> Để tránh gõ nhầm lệnh trên sai máy, vui lòng lưu ý kiến trúc:
> - **Máy 1:** Ubuntu WSL cài trên Windows 10 — Đóng vai trò **Attacker (Kẻ tấn công)**.
> - **Máy 2:** Windows 11 (Host OS) — Chỉ đóng vai trò cung cấp mạng và cấu hình `.wslconfig` để mirrored mạng.
> - **Máy 3:** Ubuntu WSL cài trên Win 11 (nằm trong Máy 2) — Đóng vai trò **Victim (Nạn nhân) & IDS Sensor**.

---

## Giai Đoạn 1: Chuẩn Bị & Cài Đặt Phần Mềm (Preparation)

### 1.1 Trên Máy 2 (Windows 11 Host)
Tính năng WSL Mirrored giúp Máy 3 có thể dùng chung IP và bắt được traffic trực tiếp từ mạng của Máy 2.

1. **Cấu hình mạng WSL Mirrored:**
   - Mở File Explorer, gõ vào thanh địa chỉ: `%userprofile%`
   - Tạo một file tên là `.wslconfig` với nội dung:
     ```ini
     [wsl2]
     networkingMode=mirrored
     ```
   - Mở PowerShell (Admin) và khởi động lại WSL: `wsl --shutdown`

### 1.2 Trên Máy 3 (Ubuntu WSL trên Máy 2)
Đây là hệ thống chốt chặn, cần cài đặt Docker để chạy mục tiêu nạn nhân, Snort để phát hiện chữ ký, và CICFlowMeter để trích xuất dòng chảy (Flow).

1. **Cài đặt các công cụ phòng thủ:**
   - Mở Terminal Ubuntu (Máy 3).
   - **Tải Docker & Docker Compose:**
     ```bash
     sudo apt update && sudo apt install docker.io docker-compose -y
     sudo usermod -aG docker $USER
     ```
   - **Tải Snort:**
     ```bash
     sudo apt install snort -y
     # Quá trình cài đặt sẽ hỏi dải mạng, hãy điền dải IP vật lý của mạng WiFi nhà bạn, ví dụ: 192.168.1.0/24
     ```
   - **Tải CICFlowMeter & Tcpdump (Công cụ bắt luồng):**
     ```bash
     # Gradle của CICFlowMeter yêu cầu Java 8, không dùng default-jdk (thường là Java 11+)
     sudo apt install tcpdump openjdk-8-jdk libpcap-dev -y
     export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
     
     git clone https://github.com/ahlashkari/CICFlowMeter.git
     cd CICFlowMeter/jnetpcap/linux/jnetpcap-1.4.r1425
     sudo cp libjnetpcap.so /usr/lib/
     cd ../../../
     ./gradlew build
     ```
     > [!TIP]
     > **Lưu ý Build:** Vì thư viện `jnetpcap` native cần khớp chính xác với kernel version của WSL, lệnh `./gradlew build` rất dễ bị lỗi. Nếu thất bại, bạn không cần build từ source mà hãy tải thẳng bản release pre-built `.zip` hoặc `.jar` từ trang Releases của repo CICFlowMeter trên Github.
   - **Tải Repository dự án của bạn:**
     ```bash
     git clone <URL_Repo_Của_Bạn> graduation-thesis
     cd graduation-thesis/Custom_IDS_Testbed
     ```

### 1.3 Trên Máy 1 (Ubuntu WSL trên Windows 10)
Máy 1 chỉ đóng vai trò chạy mã độc và kịch bản tấn công. Do dùng Win 10, môi trường WSL này tự động nằm sau NAT.

1. **Cài đặt công cụ:**
   - Mở Terminal Ubuntu (Máy 1).
   - **Tải công cụ tấn công mạng (Nmap, Hydra) & Python:**
     ```bash
     sudo apt update && sudo apt install nmap hydra python3-pip -y
     # Lưu ý: Thêm cờ --break-system-packages do các bản Ubuntu mới chặn pip3 cài trực tiếp
     pip3 install requests slowloris --break-system-packages
     ```
   - **Tải Repository dự án của bạn:**
     ```bash
     git clone <URL_Repo_Của_Bạn> graduation-thesis
     cd graduation-thesis/Custom_IDS_Testbed/scripts
     ```

---

## Giai Đoạn 2: Vận Hành Hệ Thống (Execution Order)

> [!IMPORTANT]
> **Thứ tự thực thi rất quan trọng.** Bạn phải khởi động toàn bộ lớp phòng thủ trên **Máy 3** trước khi bắn traffic từ **Máy 1**.
> Xác định IP của mục tiêu: Trên Máy 2 (Win 11), mở Command Prompt gõ `ipconfig` để xem IP IPv4 của card Wi-Fi (ví dụ: `192.168.1.55`). Do chế độ Mirrored, IP này cũng chính là IP của Máy 3.

### T0: Khởi động Nạn nhân (Victim)
- **Trên Máy 3:** Mở Tab Ubuntu số 1.
- Chạy Docker mô phỏng các ứng dụng mục tiêu (Ví dụ: DVWA, Juice-shop).
  ```bash
  cd ~/graduation-thesis/Custom_IDS_Testbed/configs
  sudo docker-compose up -d
  ```

### T1: Kích hoạt Capture (Bắt gói tin)
- **Trên Máy 3:** Mở Tab Ubuntu số 2.
- Do vấn đề raw socket của eth0 trên WSL, ta sử dụng **tcpdump** để ghi luồng trước (đảm bảo 100% không mất gói tin).
  ```bash
  sudo tcpdump -i eth0 -w attack_capture.pcap
  ```
  *(Để terminal này chạy nền).*

### T2: Kích hoạt IDS Tĩnh (Snort)
- **Trên Máy 3:** Mở Tab Ubuntu số 3.
- Trước khi chạy, phải tải Rules và cấu hình mạng (nếu không Snort sẽ chạy nhưng không ra bất kỳ alert nào):
  ```bash
  # Tải Community Rules
  wget https://www.snort.org/downloads/community/community-rules.tar.gz
  tar -xvf community-rules.tar.gz
  sudo cp community-rules/* /etc/snort/rules/
  
  # Khai báo HOME_NET trong snort.conf
  sudo sed -i 's/ipvar HOME_NET any/ipvar HOME_NET 192.168.1.0\/24/' /etc/snort/snort.conf
  ```
- Chạy Snort để lắng nghe song song trực tiếp.
  ```bash
  sudo snort -A console -c /etc/snort/snort.conf -i eth0 -l /var/log/snort/
  ```
  *(Để terminal này chạy nền. Nó sẽ liên tục in ra cảnh báo nếu thấy mã độc).*

### T3: Bắt đầu Mô phỏng Người dùng bình thường (Benign)
- **Trên Máy 1:** Mở Tab Ubuntu số 1.
- Traffic bình thường (Benign) cực kỳ quan trọng để ML không bị mất cân bằng lớp. Nếu file `auto_benign.py` chưa có sẵn, bạn có thể tạo nhanh một script bash đơn giản chạy vòng lặp tạo traffic rác:
  ```bash
  # Tạo file benign.sh
  echo 'while true; do curl -s http://192.168.1.55 > /dev/null; sleep 1; done' > benign.sh
  chmod +x benign.sh
  ./benign.sh
  ```
  *(Nếu đã có `auto_benign.py`, bạn mở file sửa IP thành `192.168.1.55` rồi chạy `python3 auto_benign.py`. Để script chạy ngầm sinh traffic).*

### T3.5: Kiểm tra kết nối mạng (Sanity Check)
- **Trước khi tấn công**, trên Máy 1 mở Tab số 2, hãy kiểm tra xem Attacker có nhìn thấy Nạn nhân không:
  ```bash
  ping 192.168.1.55 -c 4
  curl -I http://192.168.1.55
  ```
- **Lưu ý:** Nếu lệnh curl báo Connection Refused hoặc Timeout, Docker trên Máy 3 chưa chạy đúng hoặc tường lửa Windows 11 đang chặn. Phải sửa lỗi mạng trước khi đi tiếp.

### T4: Phát động Tấn công (Attack)
- **Trên Máy 1:** Mở Tab Ubuntu số 2.
- Sửa IP mục tiêu trong `auto_attack.py` thành `192.168.1.55`.
  ```bash
  python3 auto_attack.py
  ```
- *Lưu ý:* `auto_attack.py` phải được lập trình để sử dụng `nmap -sT` (TCP Connect) do giới hạn WSL Win 10 NAT. Dataset của bạn sẽ bị thiếu nhãn Botnet và các dấu hiệu OS fingerprinting UDP, đây là điều đã được xác nhận.

---

## Giai Đoạn 3: Kết thúc & Đồng Bộ Xử Lý Hậu Kỳ (Post-processing)

Sau khi `auto_attack.py` chạy xong (khoảng vài phút đến vài chục phút tùy lượng payload).

### T5: Dọn dẹp & Tắt Capture
- **Trên Máy 1:** Nhấn `Ctrl+C` ở Tab số 1 để dừng kịch bản `auto_benign.py`.
- **Trên Máy 3:**
  - Qua Tab 2: Nhấn `Ctrl+C` để tắt `tcpdump`. Ta thu được file `attack_capture.pcap`.
  - Qua Tab 3: Nhấn `Ctrl+C` để tắt `Snort`. Vào `/var/log/snort/` copy file alert ra ngoài:
    ```bash
    sudo cp /var/log/snort/alert ~/graduation-thesis/Custom_IDS_Testbed/docs/
    ```

### T6: Trích xuất Flow (Tính năng CIC-IDS-2017)
- **Trên Máy 3:**
  - Ta sẽ cho CICFlowMeter đọc file pcap vừa lưu:
    ```bash
    cd ~/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin
    sudo ./cfm ~/attack_capture.pcap ~/graduation-thesis/Custom_IDS_Testbed/docs/
    ```
  - Kết quả sinh ra file `attack_capture.pcap_Flow.csv` chứa 78 đặc trưng toán học của luồng mạng.

### T7: Chạy Machine Learning Backend (Hybrid Sync)
- **Trên Máy 3:**
  - Nhập dữ liệu từ file `alert` của Snort và file `CSV` của CICFlowMeter vào mô hình Python ML.
  - Lúc này, **Logic Đồng Bộ Nhãn (Label Synchronization)** kích hoạt. Do Snort alert và CICFlowMeter timestamps lệch nhau, `hybrid_ml_backend_example.py` sẽ thực hiện đối chiếu theo thứ tự ưu tiên:
    1. **So khớp ưu tiên:** `Src IP`, `Dst IP`, `Dst Port` (bắt buộc khớp).
    2. **Cửa sổ thời gian (Tiebreaker):** Với các loại tấn công kéo dài như Brute Force, một flow có thể span 60–120 giây. Nếu dùng cứng `± 2 giây` sẽ bỏ sót nhãn. Do đó, logic match cần ưu tiên Tuple 3 yếu tố trên trước, và timestamp chỉ dùng để gỡ hòa (tiebreak) nếu có nhiều flow trùng lặp trong cùng khoảng thời gian.
  - Bạn chạy mô hình để ra output cuối cùng:
    ```bash
    cd ~/graduation-thesis/Custom_IDS_Testbed/scripts
    python3 hybrid_ml_backend_example.py --csv ../docs/attack_capture.pcap_Flow.csv --snort-alert ../docs/alert
    ```

---
**Chúc mừng!** Tới đây bạn đã hoàn thành một vòng đời giả lập, bắt gói tin, trích xuất và xử lý dữ liệu với mô hình Hybrid IDS. Dữ liệu đầu ra đã sẵn sàng cho Frontend vẽ biểu đồ.
