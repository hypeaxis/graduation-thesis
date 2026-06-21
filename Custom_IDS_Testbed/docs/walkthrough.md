# Hướng Dẫn Vận Hành Testbed 100% WSL

Tài liệu này hướng dẫn chi tiết cách để Laptop 1 (Win 10 WSL) khởi phát cuộc tấn công sang Laptop 2 (Win 11 WSL) và ghi nhận kết quả hiển thị trên Giao diện (GUI).

---

## Bước 1: Chuẩn bị Máy Phòng Thủ (Laptop 2 - Win 11)

1. Đảm bảo file `.wslconfig` trên thư mục User của Windows 11 đã có dòng `networkingMode=mirrored`.
2. Mở cửa sổ **Ubuntu (WSL)** trên Laptop 2, điều hướng tới thư mục chứa file `docker-compose.yml` (trong thư mục `configs` của repo này). Khởi chạy mục tiêu:
   ```bash
   sudo docker-compose up -d
   ```
3. Mở thêm 2 tab Ubuntu khác trên Laptop 2:
   - **Tab 1 (Chạy Snort):**
     ```bash
     sudo snort -i eth0 -c /etc/snort/snort.conf -l /var/log/snort/
     ```
   - **Tab 2 (Chạy CICFlowMeter):**
     ```bash
     # Di chuyển vào thư mục CICFlowMeter của bạn
     sudo ./cfm eth0 /var/log/cicflowmeter/
     ```
     > [!WARNING]
     > **Lưu ý quan trọng trên WSL:** CICFlowMeter cần quyền raw socket để lắng nghe card `eth0`. Trên WSL (kể cả chế độ `mirrored`), card `eth0` đôi khi không expose đúng như mong đợi dẫn đến lỗi không bắt được gói.
     > **Cách Fallback (Xử lý offline):** Nếu lệnh trên thất bại hoặc không ra luồng mới, hãy chạy tcpdump để ghi lại pcap trước:
     > `sudo tcpdump -i eth0 -w capture.pcap`
     > Sau đó tắt tcpdump và cho CICFlowMeter đọc file offline để trích xuất feature:
     > `sudo ./cfm capture.pcap /var/log/cicflowmeter/`
4. Mở tab Ubuntu thứ 3 (Chạy Backend Machine Learning):
   ```bash
   # Di chuyển vào thư mục scripts
   python3 hybrid_ml_backend_example.py
   ```
5. Mở Command Prompt trên Windows 11 gõ `ipconfig` để lấy IP WiFi của Laptop 2 (Ví dụ: `192.168.1.55`).

---

## Bước 2: Kích Hoạt Tấn Công (Laptop 1 - Win 10)

Vì Laptop 1 dùng Windows 10, bạn không cần thiết lập `.wslconfig`. Mọi giao tiếp mạng từ WSL sẽ tự động thông qua NAT của Windows.

1. Lấy toàn bộ repo Github này về môi trường Ubuntu (WSL) trên Laptop 1.
2. Cài đặt các thư viện phụ thuộc:
   ```bash
   sudo apt update && sudo apt install nmap hydra -y
   pip3 install requests slowloris
   ```
3. Mở file `scripts/auto_attack.py` và `scripts/auto_benign.py`, sửa dòng `VICTIM_IP = "192.168.x.x"` thành IP WiFi của Laptop 2 đã lấy ở trên.

**Phát động tấn công:**
Mở 2 Terminal trên Laptop 1:
- Cửa sổ 1: Chạy `python3 auto_benign.py` để tạo nhiễu băng thông.
- Cửa sổ 2: Chạy `python3 auto_attack.py`. Kịch bản này đã được tinh chỉnh để dùng chế độ TCP Connect (`-sT`) vượt qua NAT của WSL Windows 10 một cách mượt mà.

---

## Bước 3: Theo Dõi Live Detection

Bây giờ bạn quay sang màn hình **Laptop 2**.
- Tab chạy CICFlowMeter sẽ báo có các luồng Flow mới được trích xuất liên tục.
- Tab chạy Backend Python sẽ liên tục đọc các luồng này, phân tích qua mô hình CIC-IDS-2017 và in ra kết quả như `"Phát hiện DoS Slowloris!"`.
- Bạn có thể viết thêm code Frontend kết nối tới Backend này để vẽ biểu đồ mũi tên đâm từ IP Laptop 1 sang IP Laptop 2.

---

## Bước 4: Đồng Bộ Nhãn và Chuẩn Hóa Dataset (Post-Processing)

Khi đã thu thập xong file `alert` (từ Snort) và file `.csv` (từ CICFlowMeter), bạn cần tạo ra một tập dữ liệu gộp đã gán nhãn cho Machine Learning.

1. Chạy script chuẩn bị dữ liệu:
   ```bash
   cd scripts
   python3 dataset_builder.py --csv ../docs/attack_capture.pcap_Flow.csv --alert ../docs/alert
   ```
2. Script này sẽ:
   - Dựa vào Time Window ($\pm$ 2 phút) và IP để đối chiếu cảnh báo của Snort sang luồng mạng của CICFlowMeter.
   - Gán nhãn `Malicious` hoặc `Benign`.
   - Làm sạch rác (giá trị `Infinity`, `NaN`).
   - Xóa các cột định danh (IP, Port, Flow ID, Timestamp).
   - Chuẩn hóa MinMax [0,1] trên 77 đặc trưng còn lại.
3. Kết quả là file `Cleaned_Labeled_Dataset.csv` hoàn toàn sạch sẽ, sẵn sàng để load thẳng vào mô hình PyTorch của bạn (như FT-Transformer).

---

## Bước 5: Đánh Giá Chéo (Cross-Evaluation) & Nhận Xét Học Thuật

Khi chạy mô hình **FT-Transformer (Stage 1)** (được huấn luyện hoàn hảo trên tập dữ liệu chuẩn CIC-IDS-2017) để dự đoán luồng tấn công thực tế từ Testbed, kết quả thu được rất đáng chú ý:

- **Độ chính xác (Accuracy):** Chỉ đạt `21.93%`
- **Tỉ lệ nhận diện tấn công (Recall - Malicious):** `21.80%` (Tức là gần 80% luồng tấn công Slowloris đã "qua mặt" được mô hình).

**Giải thích hiện tượng học thuật (Concept Drift):**
Sự sụt giảm nghiêm trọng này là bằng chứng rõ ràng cho bài toán **Cross-Domain Shift** (Sự chênh lệch miền dữ liệu) trong lĩnh vực IDS:
1. **Khác biệt về môi trường:** Mạng CIC-IDS-2017 được xây dựng trên hệ thống Switch/Router vật lý cũ, trong khi Testbed hiện tại chạy trên cơ chế NAT của Windows WSL với độ trễ (Latency), kích thước cửa sổ (Window Size) và MTU khác biệt.
2. **Sự tiến hóa của công cụ:** Tool `slowloris` phiên bản mới dùng trong Testbed tạo ra kích thước gói tin và thời gian IAT (Inter-Arrival Time) khác với kịch bản Slowhttptest năm 2017.
3. **Overfitting trên Testbed cũ:** Mô hình Deep Learning đã học quá sâu vào các đặc trưng "đặc thù" của mạng CIC-IDS-2017 thay vì bản chất của tấn công.

> [!TIP]
> **Hướng phát triển đồ án:** Đây là một kết quả tuyệt vời để đưa vào quyển Báo cáo Đồ án. Nó chứng minh rằng một mô hình IDS không thể chỉ train một lần rồi dùng mãi mãi. Để khắc phục, sinh viên có thể đề xuất kỹ thuật **Transfer Learning (Học Chuyển Giao)** hoặc **Fine-tuning** mô hình FT-Transformer với một phần nhỏ dữ liệu của Testbed nội bộ để nâng Accuracy lên lại 99%.
