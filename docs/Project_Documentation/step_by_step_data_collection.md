# Hướng Dẫn Từng Bước Thu Thập Dữ Liệu Testbed (Kiến Trúc 3 Máy)

Tài liệu này cung cấp hướng dẫn ở mức **"cầm tay chỉ việc"** (Step-by-Step), liệt kê chính xác các thao tác để chạy kịch bản thu thập dữ liệu (Data Collection) xuyên suốt các máy tính theo kiến trúc chuẩn hóa (không phụ thuộc nhãn Snort).

---

## 1. Định Nghĩa Kiến Trúc Hệ Thống (Architecture)

Quy trình thu thập dữ liệu bao gồm 3 thực thể tham gia:

1. **Máy 1 (Attacker):** Hệ điều hành Ubuntu WSL chạy trên Windows 10 (Máy của bạn hiện tại). Đây là nơi khởi chạy các script tự động tấn công và script sinh traffic nền (Benign). Do giới hạn của WSL Win 10, máy này đứng sau NAT và sẽ giao tiếp ra ngoài qua IP của Win 10.
2. **Máy 2 (Host OS):** Máy tính chạy Windows 11. Đóng vai trò cung cấp tài nguyên mạng cho Máy 3.
3. **Máy 3 (Victim / Sensor):** Hệ điều hành Ubuntu WSL chạy bên trong Máy 2 (Win 11). Nhờ tính năng `Mirrored Networking` của Win 11, Máy 3 sẽ hứng chịu trực tiếp các gói tin tấn công và cũng là nơi cắm các Sensor (CICFlowMeter/tcpdump) để bắt gói tin.

---

## 2. Giai Đoạn Chuẩn Bị (Chỉ làm 1 lần)

### 2.1 Tại Máy 2 & Máy 3 (Nạn nhân & Hệ thống bắt gói)
- **Cấu hình Mirrored Network (Máy 2):** Đảm bảo đã có file `.wslconfig` bật `networkingMode=mirrored`. Mở Command Prompt gõ `ipconfig` lấy IP mạng LAN của máy (Ví dụ: `192.168.1.103`).
- **Cài đặt Dịch vụ (Máy 3):** Đảm bảo SSH, FTP, Docker (chạy DVWA) đang hoạt động. *(Xem file `wsl_victim_setup_guide.md` để biết chi tiết).*
- **Cài đặt tcpdump & CICFlowMeter (Máy 3):**
  ```bash
  sudo apt update && sudo apt install tcpdump openjdk-8-jdk -y
  # Tải CICFlowMeter bản biên dịch sẵn (hoặc tự build nếu có thể) để trích xuất đặc trưng flow.
  ```

### 2.2 Tại Máy 1 (Kẻ tấn công)
- Đảm bảo đã cài các công cụ tấn công: `sudo apt install nmap hydra sqlmap python3-pip -y`
- Đảm bảo đã cài thư viện python: `pip3 install requests slowloris --break-system-packages`
- Ping thử sang Máy 2/3 để đảm bảo mạng thông suốt: `ping 192.168.1.103`

---

## 3. Giai Đoạn Vận Hành Thu Thập (Execution Order)

> [!IMPORTANT]
> **Thứ tự thực thi rất quan trọng.** Bạn phải kích hoạt hệ thống ghi nhận (Capture) trên Máy 3 trước khi bắn bất kỳ traffic nào từ Máy 1.

### T1: Kích hoạt Capture (Bắt gói tin) trên Máy 3
- Mở Terminal Ubuntu trên Máy 3 (Victim).
- Khởi chạy lệnh bắt gói tin toàn cục trên card mạng chính (eth0). Việc lưu ra file `.pcap` đảm bảo không sót bất kỳ gói nào:
  ```bash
  sudo tcpdump -i eth0 -w attack_capture_run3.pcap
  ```
  *(Để terminal này chạy nền).*

### T2: Khởi chạy Traffic Nền (Benign) trên Máy 1
- Mở Terminal Ubuntu (Tab 1) trên Máy 1 (Attacker).
- Kích hoạt script sinh traffic nền (truy cập Web, SSH hợp lệ) nhằm đảm bảo lượng dữ liệu sạch chiếm > 25%.
  ```bash
  python3 background_traffic_generator.py --target 192.168.1.103
  ```
  *(Để terminal này chạy nền).*

### T3: Phát động Kịch bản Tấn công trên Máy 1
- Mở Terminal Ubuntu (Tab 2) trên Máy 1 (Attacker).
- Chạy kịch bản tấn công tự động. Kịch bản này sẽ tự ghi nhận chính xác thời gian (millisecond) bắt đầu và kết thúc của từng đợt tấn công ra file CSV (Ground Truth).
  ```bash
  python3 auto_attack_v2.py --target 192.168.1.103
  ```
- *Đợi cho đến khi script `auto_attack_v2.py` in ra thông báo hoàn tất toàn bộ tiến trình.*

---

## 4. Giai Đoạn Xử Lý Hậu Kỳ (Post-processing)

### T4: Dừng Capture và Dọn dẹp
- **Tại Máy 1:** Bấm `Ctrl+C` ở Tab 1 để dừng script `background_traffic_generator.py`. Lấy file `ground_truth_log_run3.csv` vừa được sinh ra.
- **Tại Máy 3:** Bấm `Ctrl+C` để dừng `tcpdump`. Chúng ta thu được file `attack_capture_run3.pcap`.

### T5: Trích xuất Flow mạng bằng CICFlowMeter
- Chuyển file `.pcap` từ Máy 3 sang thư mục chứa `CICFlowMeter` (Có thể copy qua máy nào cài Java 8 ổn định nhất).
- Chạy lệnh trích xuất:
  ```bash
  sudo /home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm /home/ning/attack_capture_run3.pcap /home/ning/graduation-thesis/docs/
  ```
- Kết quả nhận được file `attack_capture_run3.pcap_Flow.csv` chứa các đặc trưng toán học của luồng mạng.

### T6: Gán Nhãn (Labeling) Dữ Liệu
- Đem cả 2 file: `attack_capture_run3.pcap_Flow.csv` và `ground_truth_log_run3.csv` bỏ chung vào một thư mục (Ví dụ: `Graduation-Thesis/docs`).
- Chạy công cụ gán nhãn v2:
  ```bash
  python3 dataset_builder_v2.py --csv ../docs/attack_capture_run3.pcap_Flow.csv --ground-truth ../docs/ground_truth_log_run3.csv
  ```
- File output `Cleaned_Labeled_Dataset.csv` sinh ra từ bước này chính là bộ dataset hoàn chỉnh nhất, sạch sẽ, không phụ thuộc Snort và sẵn sàng nạp vào Pipeline Huấn Luyện (Phase 3 & 4).
