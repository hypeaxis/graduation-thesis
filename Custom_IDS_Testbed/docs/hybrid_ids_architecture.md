# Tích Hợp Kiến Trúc Hybrid IDS (CICFlowMeter + Snort)

Kiến trúc này giải quyết bài toán cốt lõi: Sử dụng Model Machine Learning đã train bằng CIC-IDS-2017 (Anomaly-based) kết hợp với các luật có sẵn của Snort (Signature-based). Đây được gọi là mô hình **Hybrid IDS**, cực kỳ lý tưởng cho đồ án tốt nghiệp.

## 1. Cấu Trúc Data Pipeline Mới

Trong kiến trúc mới, cả Snort và CICFlowMeter sẽ cùng được khởi chạy trên các máy ảo (Sensor). 

```mermaid
graph TD
    A[Attacker (Máy 1)] -->|Tấn công| B(Mạng LAN / WiFi)
    B --> C[Card Mạng Máy Ảo (Sensor)]
    
    C -->|Bắt gói tin song song| D[Snort]
    C -->|Bắt gói tin song song| E[CICFlowMeter V4.0]
    
    D -->|Luật tĩnh| F[alert.csv / json]
    E -->|Gộp Flow & Tính 78 đặc trưng| G[realtime_flow.csv]
    
    F -->|Đọc realtime| H[Python Backend]
    G -->|Đọc realtime| H
    
    H -->|Phân tích Anomaly| I{Model CIC-IDS-2017 v7}
    H -->|Phân tích Signature| J{Snort Rules}
    
    I -->|Kết quả Dự đoán| K[Gộp dữ liệu]
    J -->|Cảnh báo| K
    
    K -->|Phát qua WebSocket| L((Custom GUI Frontend))
```

## 2. Các Bước Cài Đặt CICFlowMeter Để Chạy Real-time

Bạn cần cài đặt công cụ trích xuất đặc trưng mạng:
1. Clone thư mục mã nguồn CICFlowMeter: `git clone https://github.com/ahlashkari/CICFlowMeter.git`
2. Biên dịch công cụ bằng Gradle hoặc sử dụng bản build sẵn `.zip`.
3. Chạy CICFlowMeter ở chế độ dòng lệnh (CLI), chỉ định card mạng cần nghe ngóng:
   ```bash
   # Chạy lắng nghe trực tiếp trên card mạng eth0 (Hoặc wlan0)
   sudo ./cfm eth0 /var/log/cicflowmeter/
   ```
4. Lúc này, CICFlowMeter sẽ liên tục xuất ra các file `.csv` chứa mảng 78+ con số thống kê ngay tại thư mục `/var/log/cicflowmeter/`.

## 3. Bản chất của Backend ML (Mới)

Backend lúc này sẽ theo dõi (tail) file CSV của **CICFlowMeter**.
- Mỗi khi có dòng dữ liệu mới (đại diện cho 1 flow hoàn chỉnh), Backend sẽ bóc tách lấy 78 đặc trưng đó (Flow Duration, Fwd Pkt Len, v.v.).
- Backend truyền trực tiếp mảng 78 đặc trưng này vào hàm `model.predict()`.
- Lấy kết quả (`Benign` hoặc `DDoS`, `PortScan`, v.v.) và đẩy lên Custom GUI để vẽ đường đạn.

*(Đoạn code đọc CICFlowMeter và apply Model đã được tôi viết lại trong file `scripts/hybrid_ml_backend_example.py`)*
