# Phụ lục A. Cấu hình môi trường thực nghiệm

## A.1 Cấu hình WSL2 Mirrored Networking

WSL2 Mirrored Networking cho phép WSL interface nhận traffic trực tiếp từ mạng LAN vật lý, thay vì qua NAT của Hyper-V. Đây là yêu cầu bắt buộc để CICFlowMeter thu thập flow features giống với môi trường mạng thực.

**Kích hoạt Mirrored Networking:**

Tạo hoặc chỉnh sửa file `%USERPROFILE%\.wslconfig` trên Windows 11:

```ini
[wsl2]
networkingMode=mirrored
```

Sau đó khởi động lại WSL2:

```powershell
wsl --shutdown
wsl
```

**Kiểm tra cấu hình:**

```bash
# Trong WSL2 Ubuntu — kiểm tra interface eth0 nhận IP LAN
ip addr show eth0
# Kỳ vọng: IP thuộc dải 192.168.x.x (LAN), không phải 172.x.x.x (NAT)
```

**Lưu ý:** Mirrored Networking yêu cầu Windows 11 Build 22621.2359 trở lên và WSL 2.0.0 trở lên. Kiểm tra phiên bản WSL bằng `wsl --version`.

---

## A.2 Cài đặt và cấu hình Snort 3

**Cài đặt dependencies:**

```bash
sudo apt update
sudo apt install -y build-essential libpcap-dev libpcre2-dev \
    libdnet-dev zlib1g-dev liblzma-dev openssl libssl-dev \
    cmake flex bison git pkg-config

# LibDAQ (Data Acquisition Library)
git clone https://github.com/snort3/libdaq.git
cd libdaq && ./bootstrap && ./configure && make && sudo make install
cd ..

# Snort 3
git clone https://github.com/snort3/snort3.git
cd snort3
./configure_cmake.sh --prefix=/usr/local --enable-tcmalloc
cd build && make -j$(nproc) && sudo make install
```

**Kiểm tra cài đặt:**

```bash
snort --version
# Kỳ vọng: Snort++ 3.x.x
```

**Cấu hình snort.lua cơ bản cho Testbed:**

```lua
-- /usr/local/etc/snort/snort.lua (cấu hình tối thiểu)
HOME_NET = '192.168.1.0/24'
EXTERNAL_NET = 'any'

ips = {
    enable_builtin_rules = true,
    include = RULE_PATH .. '/local.rules',
}

alert_fast = {
    file = true,
    packet = false,
}
```

**File rules tùy chỉnh cho Testbed (`local.rules`):**

```
# Phát hiện DoS HTTP flood
alert tcp $EXTERNAL_NET any -> $HOME_NET 80 \
    (msg:"DoS HTTP Flood detected"; \
     flow:to_server; threshold:type threshold,track by_src,count 100,seconds 1; \
     sid:1000001; rev:1;)

# Phát hiện SSH BruteForce (fallback — FTT xử lý chính)
alert tcp $EXTERNAL_NET any -> $HOME_NET 22 \
    (msg:"SSH BruteForce attempt"; \
     flow:to_server,established; threshold:type threshold,track by_src,count 10,seconds 5; \
     sid:1000002; rev:1;)
```

**Chạy Snort trên interface WSL:**

```bash
sudo snort -c /usr/local/etc/snort/snort.lua \
    -i eth0 \
    -l /var/log/snort \
    --daq-dir /usr/local/lib/daq \
    -A fast \
    &
```

---

## A.3 Triển khai CICFlowMeter

CICFlowMeter trích xuất 77–80 đặc trưng thống kê flow từ pcap file hoặc live interface.

**Cài đặt CICFlowMeter (Java 8):**

```bash
# Cài Java 8
sudo apt install openjdk-8-jdk

# Tải CICFlowMeter từ repository University of New Brunswick
# (sử dụng bản fork với bug fixes cho Linux)
git clone https://github.com/datthinh1801/cicflowmeter.git
cd cicflowmeter
mvn package -DskipTests
```

**Thu thập flow từ pcap:**

```bash
java -jar target/CICFlowMeter-4.0-SNAPSHOT.jar \
    /path/to/capture.pcap \
    /path/to/output/flows/
```

**Thu thập flow real-time từ interface:**

```bash
# Capture pcap song song với Snort
sudo tcpdump -i eth0 -w /tmp/capture.pcap &

# Sau khi tấn công kết thúc, xử lý pcap
java -jar target/CICFlowMeter-4.0-SNAPSHOT.jar \
    /tmp/capture.pcap \
    /tmp/flows/
```

**Xử lý đặc trưng trong Python (PowerTransformer V8.5 scaler):**

```python
import pandas as pd
from sklearn.preprocessing import PowerTransformer
import joblib

# Load scaler đã train trên Testbed V8.5
scaler = joblib.load('models/testbed_v85_scaler.pkl')

# Load flow CSV từ CICFlowMeter
flows = pd.read_csv('/tmp/flows/capture_ICTAI_Flow.csv')

# Xử lý Inf/NaN
flows.replace([float('inf'), float('-inf')], float('nan'), inplace=True)
flows.dropna(inplace=True)

# Transform
X = scaler.transform(flows[FEATURE_COLUMNS])
```

---

## A.4 Hướng dẫn khởi động pipeline End-to-End

**Thứ tự khởi động:**

```bash
# 1. Khởi động Snort (background)
sudo snort -c /usr/local/etc/snort/snort.lua -i eth0 \
    -l /var/log/snort -A fast &

# 2. Khởi động capture pcap (background)
sudo tcpdump -i eth0 -w /tmp/live_capture.pcap &

# 3. Khởi động inference daemon (Python)
python3 inference_daemon.py \
    --pcap /tmp/live_capture.pcap \
    --model models/ftt_v85.pt \
    --scaler models/testbed_v85_scaler.pkl \
    --output /var/log/ids/ml_alerts.log &

echo "IDS Pipeline started. Snort + FTT V8.5 active."
```

**Dừng pipeline:**

```bash
sudo pkill -f "snort -c"
sudo pkill -f "tcpdump -i eth0"
sudo pkill -f "inference_daemon.py"
```

**Kiểm tra log:**

```bash
# Snort alerts
tail -f /var/log/snort/alert_fast.txt

# ML alerts
tail -f /var/log/ids/ml_alerts.log
```

**Lưu ý phần cứng:** Pipeline yêu cầu ít nhất 8 GB RAM (CICFlowMeter Java heap + PyTorch). GPU không bắt buộc cho inference (CPU inference đủ với batch nhỏ), nhưng GPU giảm latency xuống < 1 giây cho batch 128 flows.
