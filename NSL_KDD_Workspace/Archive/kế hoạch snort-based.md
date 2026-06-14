Kế hoạch xây dựng sản phẩm (Snort-based)

ĐỒ ÁN CUỐI KHÓA

---

> **Cập nhật lần cuối:** 12/04/2026
> **Trạng thái tổng quan:** 🟡 Đang triển khai Giai đoạn 1 (Snort pipeline)

---

# Giai đoạn 1: Xây dựng Data Pipeline với Snort

**Mục tiêu:** Bắt lưu lượng mạng thực tế bằng Snort và chuyển log/alert sang vector 122 đặc trưng chuẩn NSL-KDD.

**Trạng thái:** 🟡 Đang thực hiện (25%)

## 1.1 Thiết lập môi trường

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 1.1.1 | Cài đặt WSL2 | `wsl --install -d Ubuntu-22.04` | ✅ Hoàn thành |
| 1.1.2 | Cấu hình VS Code | Remote - WSL, Python, Docker, REST Client | ✅ Hoàn thành |
| 1.1.3 | Khởi tạo Git repository | `git init`, `.gitignore`, cấu trúc thư mục | ✅ Hoàn thành |
| 1.1.4 | Cài đặt Snort | `sudo apt install snort` (hoặc build source) | ⬜ Chưa bắt đầu |
| 1.1.5 | Thiết lập cấu trúc project | Tạo folders: `/sniffer`, `/model`, `/backend`, `/frontend` | ✅ Hoàn thành |

## 1.2 Triển khai Snort Packet Logger

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 1.2.1 | Cấu hình `snort.conf` | HOME_NET, rules path, preprocessors cơ bản | ⬜ Chưa bắt đầu |
| 1.2.2 | Thiết lập output plugin | Xuất unified2/JSON/alert fast + log packets | ⬜ Chưa bắt đầu |
| 1.2.3 | Tạo bộ rules nền tảng | ICMP flood, SYN flood, scan, brute force | ⬜ Chưa bắt đầu |
| 1.2.4 | Chạy Snort ở logger mode | `snort -i <iface> -A fast -l /var/log/snort` | ⬜ Chưa bắt đầu |
| 1.2.5 | Xác thực dữ liệu đầu ra | Kiểm tra log rotation, timestamp, packet metadata | ⬜ Chưa bắt đầu |
| 1.2.6 | Viết smoke test cho Snort | Verify service start/stop, verify output files | ⬜ Chưa bắt đầu |

## 1.3 Feature Extraction (122 đặc trưng NSL-KDD)

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 1.3.1 | Thiết kế parser log Snort | Script Python đọc alert/log theo stream | ⬜ Chưa bắt đầu |
| 1.3.2 | Implement Basic Features (1-9) | duration, protocol_type, service, flag, src_bytes, dst_bytes... | ⬜ Chưa bắt đầu |
| 1.3.3 | Implement Content Features (10-22) | land, wrong_fragment, urgent, hot, num_failed_logins... | ⬜ Chưa bắt đầu |
| 1.3.4 | Implement Time-based Features (23-31) | count, srv_count, serror_rate, srv_serror_rate... | ⬜ Chưa bắt đầu |
| 1.3.5 | Implement Host-based Features (32-41) | dst_host_count, dst_host_srv_count, dst_host_same_srv_rate... | ⬜ Chưa bắt đầu |
| 1.3.6 | Thêm 80 derived features | One-hot encoding, statistical aggregations | ⬜ Chưa bắt đầu |
| 1.3.7 | Normalize features | Min-max scaling hoặc Z-score normalization | ⬜ Chưa bắt đầu |
| 1.3.8 | Viết output module | Xuất vector 122 chiều dạng JSON cho Model API | ⬜ Chưa bắt đầu |

**Deliverables Giai đoạn 1:**
- [ ] Snort capture/log hoạt động ổn định trên WSL
- [ ] Parser chuyển log Snort sang features thành công
- [ ] Output vector 122 chiều đúng format đầu vào model

---

# Giai đoạn 2: Tối ưu và Triển khai Mô hình

**Mục tiêu:** Nâng độ chính xác mô hình và đưa Model API vào môi trường production.

**Trạng thái:** ⬜ Chưa bắt đầu

## 2.1 Fine-tuning và đánh giá mô hình

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 2.1.1 | Đánh giá baseline | Autoencoder + Transformer trên tập validation | ⬜ Chưa bắt đầu |
| 2.1.2 | Tối ưu dữ liệu train | Re-balance classes, xử lý outlier, calibration | ⬜ Chưa bắt đầu |
| 2.1.3 | Tuning threshold | Giảm False Positive Rate | ⬜ Chưa bắt đầu |
| 2.1.4 | So sánh nhiều phiên bản | Chọn model theo F1, FPR, latency | ⬜ Chưa bắt đầu |

## 2.2 Đóng gói mô hình (Model Optimization)

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 2.2.1 | Export Autoencoder sang ONNX | `torch.onnx.export()` với dynamic batch size | ⬜ Chưa bắt đầu |
| 2.2.2 | Export Transformer sang ONNX | Xử lý attention mask, positional encoding | ⬜ Chưa bắt đầu |
| 2.2.3 | Validate ONNX models | So sánh output với model gốc (tolerance < 1e-5) | ⬜ Chưa bắt đầu |
| 2.2.4 | Optimize ONNX Runtime | Quantization INT8, graph optimization | ⬜ Chưa bắt đầu |
| 2.2.5 | Benchmark performance | Đo latency, throughput theo batch sizes | ⬜ Chưa bắt đầu |

## 2.3 Xây dựng Model API (FastAPI)

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 2.3.1 | Khởi tạo FastAPI project | `pip install fastapi uvicorn onnxruntime` | ⬜ Chưa bắt đầu |
| 2.3.2 | Viết Pydantic schemas | Input: vector 122 chiều, Output: prediction + confidence | ⬜ Chưa bắt đầu |
| 2.3.3 | Implement `/predict` endpoint | Load ONNX model, inference, return kết quả | ⬜ Chưa bắt đầu |
| 2.3.4 | Thêm `/batch_predict` endpoint | Xử lý nhiều samples cùng lúc | ⬜ Chưa bắt đầu |
| 2.3.5 | Implement `/health` endpoint | Health check cho monitoring | ⬜ Chưa bắt đầu |
| 2.3.6 | Tối ưu độ trễ | Target `< 10ms` cho single prediction | ⬜ Chưa bắt đầu |

**Deliverables Giai đoạn 2:**
- [ ] Model đạt chất lượng theo KPI (FPR, F1)
- [ ] ONNX models hoạt động chính xác
- [ ] API endpoint `/predict` latency < 10ms

---

# Giai đoạn 3: Phát triển Backend và Dashboard

**Mục tiêu:** Xây dựng tầng điều phối, lưu trữ và hiển thị cảnh báo thời gian thực.

**Trạng thái:** ⬜ Chưa bắt đầu

## 3.1 Backend Server (Node.js)

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 3.1.1 | Khởi tạo Node.js project | `npm init`, cài Express.js | ⬜ Chưa bắt đầu |
| 3.1.2 | Thiết kế REST API routes | `/api/alerts`, `/api/stats`, `/api/config` | ⬜ Chưa bắt đầu |
| 3.1.3 | Nhận kết quả từ Model API | Pull/push kết quả phân loại từ FastAPI | ⬜ Chưa bắt đầu |
| 3.1.4 | Implement alert storage | SQLite/PostgreSQL cho persistent storage | ⬜ Chưa bắt đầu |
| 3.1.5 | Viết alert aggregation logic | Nhóm alerts theo IP, time window | ⬜ Chưa bắt đầu |
| 3.1.6 | Add authentication | JWT tokens cho admin access | ⬜ Chưa bắt đầu |

## 3.2 Real-time Communication (WebSocket)

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 3.2.1 | Cài đặt Socket.io | `npm install socket.io` | ⬜ Chưa bắt đầu |
| 3.2.2 | Setup WebSocket server | Tích hợp vào Express app | ⬜ Chưa bắt đầu |
| 3.2.3 | Implement `alert:new` event | Push alert mới đến tất cả clients | ⬜ Chưa bắt đầu |
| 3.2.4 | Implement `stats:update` event | Cập nhật thống kê real-time | ⬜ Chưa bắt đầu |

## 3.3 Frontend Dashboard (React)

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 3.3.1 | Khởi tạo frontend project | `npm create vite` | ⬜ Chưa bắt đầu |
| 3.3.2 | Implement Dashboard layout | Header, sidebar, main content area | ⬜ Chưa bắt đầu |
| 3.3.3 | Traffic overview chart | Biểu đồ lưu lượng theo thời gian | ⬜ Chưa bắt đầu |
| 3.3.4 | Attack distribution chart | Phân bố loại tấn công | ⬜ Chưa bắt đầu |
| 3.3.5 | Alert table + filter | Bảng log cảnh báo có tìm kiếm/lọc | ⬜ Chưa bắt đầu |
| 3.3.6 | Severity colors + notifications | Mức cảnh báo theo màu và âm thanh | ⬜ Chưa bắt đầu |

**Deliverables Giai đoạn 3:**
- [ ] Backend API hoạt động ổn định
- [ ] WebSocket push alerts real-time
- [ ] Dashboard hiển thị đầy đủ thông tin

---

# Giai đoạn 4: Tích hợp hệ thống và Giả lập Tấn công

**Mục tiêu:** Nối toàn bộ pipeline và kiểm chứng khả năng phát hiện dưới tải tấn công.

**Trạng thái:** ⬜ Chưa bắt đầu

## 4.1 System Integration

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 4.1.1 | Chuẩn hóa luồng dữ liệu | `Snort -> Preprocess Script -> FastAPI -> Node.js -> Dashboard` | ⬜ Chưa bắt đầu |
| 4.1.2 | Thiết kế format JSON chuẩn | Metadata + feature vector + prediction | ⬜ Chưa bắt đầu |
| 4.1.3 | Implement queue/circuit breaker | Chống nghẽn khi traffic tăng đột biến | ⬜ Chưa bắt đầu |
| 4.1.4 | End-to-end testing | Test luồng đầy đủ từ packet đến alert UI | ⬜ Chưa bắt đầu |
| 4.1.5 | Stress testing | Benchmark với 1000+ packets/s | ⬜ Chưa bắt đầu |

## 4.2 Attack Scenarios Testing

| Bước | Loại tấn công | Tool/Command | Expected Detection | Trạng thái |
|------|--------------|--------------|-------------------|------------|
| 4.2.1 | DoS - SYN Flood | `hping3 -S --flood -p 80 <victim>` | DoS | ⬜ Chưa bắt đầu |
| 4.2.2 | DoS - ICMP Flood | `hping3 --icmp --flood <victim>` | DoS | ⬜ Chưa bắt đầu |
| 4.2.3 | Probe - Port Scan | `nmap -sS -p 1-65535 <victim>` | Probe | ⬜ Chưa bắt đầu |
| 4.2.4 | Probe - Service Scan | `nmap -sV <victim>` | Probe | ⬜ Chưa bắt đầu |
| 4.2.5 | R2L - SSH Brute Force | `hydra -l root -P wordlist.txt ssh://<victim>` | R2L | ⬜ Chưa bắt đầu |
| 4.2.6 | U2R - Privilege Escalation | Metasploit/custom payload | U2R | ⬜ Chưa bắt đầu |

## 4.3 Performance Evaluation

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 4.3.1 | Detection Rate | % attacks detected correctly | ⬜ Chưa bắt đầu |
| 4.3.2 | False Positive Rate | % normal traffic bị gắn attack | ⬜ Chưa bắt đầu |
| 4.3.3 | Response Time | Attack -> Alert hiển thị trên dashboard | ⬜ Chưa bắt đầu |
| 4.3.4 | So sánh với IDS truyền thống | Snort IDS mode / Suricata | ⬜ Chưa bắt đầu |

**Deliverables Giai đoạn 4:**
- [ ] Hệ thống integrated chạy ổn định
- [ ] Detection Rate > 95%
- [ ] Response Time < 500ms
- [ ] Video demo tấn công và detection

---

# Giai đoạn 5: Viết báo cáo và Chuẩn bị Bảo vệ

**Mục tiêu:** Hoàn thiện tài liệu, slide và demo cho hội đồng.

**Trạng thái:** ⬜ Chưa bắt đầu

## 5.1 Hoàn thiện báo cáo

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 5.1.1 | Cập nhật Chương kiến trúc | Luồng Snort-based và quyết định thiết kế | ⬜ Chưa bắt đầu |
| 5.1.2 | Cập nhật Chương triển khai | Cấu hình Snort, parser, model serving | ⬜ Chưa bắt đầu |
| 5.1.3 | Cập nhật Chương thí nghiệm | Attack simulation + confusion matrix | ⬜ Chưa bắt đầu |
| 5.1.4 | Review toàn văn | Chính tả, format, consistency | ⬜ Chưa bắt đầu |

## 5.2 Chuẩn bị thuyết trình và demo

| Bước | Công việc | Chi tiết | Trạng thái |
|------|-----------|----------|------------|
| 5.2.1 | Chuẩn bị slide 20 trang | Bài toán, kiến trúc, kết quả, kết luận | ⬜ Chưa bắt đầu |
| 5.2.2 | Chuẩn bị demo live | Script tấn công + dashboard cảnh báo | ⬜ Chưa bắt đầu |
| 5.2.3 | Quay video backup | Dự phòng khi môi trường demo lỗi | ⬜ Chưa bắt đầu |
| 5.2.4 | Luyện Q&A | Ưu/nhược điểm, false positive, khả năng scale | ⬜ Chưa bắt đầu |

**Deliverables Giai đoạn 5:**
- [ ] Báo cáo hoàn chỉnh
- [ ] Slide thuyết trình
- [ ] Video demo backup
- [ ] Sẵn sàng bảo vệ

---

# Timeline Tổng quan

| Giai đoạn | Thời gian dự kiến | Bắt đầu | Deadline | Tiến độ |
|-----------|-------------------|---------|----------|---------|
| GĐ 1: Snort Data Pipeline | 3-4 tuần | 02/03/2026 | 30/03/2026 | 🟡 25% |
| GĐ 2: Model Optimization + API | 2-3 tuần | 31/03/2026 | 20/04/2026 | ⬜ 0% |
| GĐ 3: Backend + Dashboard | 3-4 tuần | 21/04/2026 | 18/05/2026 | ⬜ 0% |
| GĐ 4: Integration + Attack Simulation | 2-3 tuần | 19/05/2026 | 08/06/2026 | ⬜ 0% |
| GĐ 5: Report + Defense | 2-3 tuần | 09/06/2026 | 30/06/2026 | ⬜ 0% |
| **Tổng cộng** | **~17 tuần** | **02/03/2026** | **30/06/2026** | **~6%** |

---

# Công việc tiếp theo (Next Actions)

1. [GĐ 1.2.1] Cấu hình `snort.conf` và output logger
2. [GĐ 1.2.2] Viết script parser log Snort -> vector 122 chiều
3. [GĐ 1.2.3] Kiểm thử với traffic giả lập nhẹ và đối chiếu output

---

# Tech Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| Packet Capture | Snort | Capture + rule-based logging |
| Feature Extraction | Python | Parse Snort log -> 122 NSL-KDD features |
| Model Serving | FastAPI + ONNX Runtime | ML inference |
| Backend | Node.js + Express + Socket.io | API gateway, orchestration, realtime |
| Frontend | React + Chart.js/Recharts | Dashboard visualization |
| Database | SQLite/PostgreSQL | Alert storage |
| DevOps | Docker + Git | Containerization, version control |
