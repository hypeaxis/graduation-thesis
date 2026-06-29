# Hướng dẫn cấu hình Snort trên Máy 2 (Victim)

Để Snort trên máy Nạn nhân (Victim) có thể phát hiện đúng các nhãn tấn công cho Testbed, bạn cần cấu hình Snort sử dụng bộ luật `local.rules` vừa được tạo.

## Các bước thực hiện:

1. **Copy file luật sang máy Nạn Nhân:**
   Sử dụng USB hoặc lệnh `scp` để chép file `local.rules` từ thư mục `Custom_IDS_Testbed/snort_rules/` của máy này sang máy Nạn Nhân (Laptop 2).
   ```bash
   scp Custom_IDS_Testbed/snort_rules/local.rules user_may_2@192.168.0.103:~/
   ```

2. **Chép đè vào thư mục rules của Snort:**
   Trên máy 2, mở terminal và ghi đè file này vào thư mục chứa luật nội bộ của Snort (thường là `/etc/snort/rules/` hoặc tương tự tùy cấu hình hệ điều hành).
   ```bash
   sudo cp ~/local.rules /etc/snort/rules/local.rules
   ```

3. **Chỉnh sửa file cấu hình `snort.conf`:**
   Mở file `/etc/snort/snort.conf` trên máy 2.
   Tìm biến `$HOME_NET` và đảm bảo nó trỏ đúng về địa chỉ IP của máy 2 (VD: `var HOME_NET 192.168.0.103/32` hoặc `192.168.0.0/24`).
   Kéo xuống phần có chữ `Step #7: Customize your rule set`, đảm bảo dòng lệnh gọi file `local.rules` không bị comment (không có dấu `#` ở đầu):
   ```text
   include $RULE_PATH/local.rules
   ```

4. **Khởi động lại Snort:**
   Chạy lại Snort trên máy 2 để nhận luật mới.
   ```bash
   sudo systemctl restart snort
   ```
   Hoặc chạy lệnh trực tiếp:
   ```bash
   sudo snort -A fast -c /etc/snort/snort.conf -i eth0
   ```
   *(Nhớ thay `eth0` bằng tên card mạng thực tế của máy 2, có thể xem bằng lệnh `ip a`)*

Sau khi hoàn tất, bạn có thể chạy lại script `auto_attack.py` ở máy 1. Các thông báo cảnh báo của Snort lúc này sẽ chứa rõ các chữ "PortScan", "Brute Force", "Web Attack SQL", "DoS Hulk" thay vì chỉ có "ICMP" hay "BAD-TRAFFIC". Khi đó, script `dataset_builder.py` của chúng ta sẽ bóc tách và phân loại thành bảng 9 class một cách hoàn hảo!
