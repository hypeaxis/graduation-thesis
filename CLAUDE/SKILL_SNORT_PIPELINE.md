# Cẩm nang Kỹ năng: Snort-based Data Pipeline (SKILL_SNORT_PIPELINE.md)

**Mục đích:** Hướng dẫn cấu hình Snort, chuẩn hóa log pipeline và trích xuất 122 đặc trưng NSL-KDD phục vụ hệ thống IDS học máy.

## 1. Vòng đời pipeline Snort chuẩn
1. **Snort Capture:** Chạy Snort ở logger mode để ghi nhận traffic và alerts.
2. **Structured Output:** Xuất alert/log theo format dễ parse (fast/unified2/JSON).
3. **Parser Service:** Script đọc log theo stream, làm sạch dữ liệu, chuẩn hóa schema.
4. **Feature Builder:** Tính các đặc trưng trong cửa sổ thời gian 2 giây.
5. **Model Input:** Gửi vector 122 chiều sang FastAPI `/predict` hoặc `/batch_predict`.

## 2. Cấu hình Snort tối thiểu

### 2.1 Các điểm cần chỉnh trong `snort.conf`
- `HOME_NET`, `EXTERNAL_NET`
- `RULE_PATH`, `SO_RULE_PATH`
- Bật preprocessors cần thiết
- Cấu hình output (alert fast hoặc unified2)

### 2.2 Lệnh chạy Snort (logger mode)
```bash
sudo snort -i eth0 -A fast -l /var/log/snort -c /etc/snort/snort.conf
```

### 2.3 Kiểm tra nhanh
```bash
# Theo dõi alert theo thời gian thực
tail -f /var/log/snort/alert

# Kiểm tra Snort process
ps aux | grep snort
```

## 3. Thiết kế parser log Snort

### 3.1 Nguyên tắc parser
- Không parse theo từng dòng rời rạc khi dữ liệu thiếu context.
- Dùng state machine hoặc buffer để ghép đủ trường dữ liệu.
- Chuẩn hóa timestamp về UTC.
- Gắn `connection_id` để nhóm events cùng flow.

### 3.2 Schema trung gian gợi ý
```json
{
  "timestamp": "2026-04-12T12:30:45.123Z",
  "src_ip": "192.168.1.10",
  "dst_ip": "192.168.1.20",
  "src_port": 54321,
  "dst_port": 80,
  "protocol": "TCP",
  "tcp_flags": "S",
  "payload_len": 0,
  "snort_sid": 1000001,
  "snort_msg": "SYN flood suspected"
}
```

## 4. Tính 122 đặc trưng NSL-KDD từ log Snort

### 4.1 Cửa sổ thời gian 2 giây
- Dùng sliding window theo `timestamp`.
- Mỗi khi connection kết thúc hoặc timeout, chốt vector features.

### 4.2 Ánh xạ nhóm đặc trưng
- **Basic (1-9):** protocol, service, bytes, land, urgent...
- **Content (10-22):** dựa vào payload/signature (nếu có)
- **Time-based (23-31):** thống kê theo cùng host/service trong 2 giây
- **Host-based (32-41):** thống kê theo 100 kết nối gần nhất
- **Derived (42-122):** one-hot protocol/service/flag

### 4.3 Chuẩn hóa đầu vào
- Numeric features: min-max hoặc z-score
- Categorical features: mapping + one-hot đúng thứ tự cột
- Kiểm tra chiều vector luôn bằng 122

## 5. Gửi dữ liệu sang Model API

### 5.1 Payload gợi ý
```json
{
  "features": [0.12, 0.0, 1.0, 0.0],
  "metadata": {
    "src_ip": "192.168.1.10",
    "dst_ip": "192.168.1.20",
    "sid": 1000001
  }
}
```

### 5.2 Khuyến nghị hiệu năng
- Batch 32-256 samples mỗi lần gọi `/batch_predict`
- Timeout gọi model: 2-5 giây
- Retry có backoff cho lỗi tạm thời

## 6. Lỗi thường gặp và cách xử lý

| Vấn đề | Triệu chứng | Cách xử lý |
|--------|-------------|------------|
| Log format không ổn định | Parse fail, mất trường | Áp dụng parser theo regex + fallback strategy |
| Burst traffic | Queue tăng đột biến | Bật batch mode + giới hạn queue + drop policy |
| Mất đồng bộ thời gian | count/srv_count sai | Chuẩn hóa timezone, dùng monotonic clock khi tính window |
| Feature dimension mismatch | Model trả 422 | Thêm bước validate `len(features) == 122` |

## 7. Checklist trước khi chuyển sang Phase 2
- [ ] Snort ghi log ổn định trong 30-60 phút liên tục
- [ ] Parser không crash khi gặp log lỗi/thiếu field
- [ ] Tỷ lệ parse thành công > 99%
- [ ] Vector 122 chiều đúng format và thứ tự cột
- [ ] Pipeline end-to-end tạo được prediction thực tế
