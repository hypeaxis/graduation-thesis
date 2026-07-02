# Hướng dẫn đầy đủ — Live Detection (kiến trúc micro-batch)

Tài liệu này mô tả toàn bộ phần **phát hiện xâm nhập theo thời gian thực** trong `live_detection/`:
bối cảnh, lý do chọn công cụ, kiến trúc, cách cài đặt, cách chạy demo và xử lý sự cố.

---

## 1. Bối cảnh & vấn đề

Hệ thống trước đây chạy theo kiểu **replay**: phát lại các file CSV flow đã thu sẵn
(`*_Flow.csv`) rồi cho model FT-Transformer **V8.5** suy luận. Mục tiêu của phần này là
chuyển sang **live thật**: bắt gói trực tiếp từ card mạng → trích đặc trưng → dự đoán realtime.

Ràng buộc cốt lõi: **model đã được train trên đặc trưng do một công cụ cụ thể sinh ra.**
Nếu đổi công cụ trích đặc trưng khi live, phân phối đặc trưng sẽ lệch (domain shift) và
macro-F1 (đang 0.978) sẽ tụt → buộc phải train lại. Vì vậy tiêu chí số một là **feature parity**.

---

## 2. Lý do chọn công cụ (đã kiểm chứng)

| Công cụ | Kết luận |
|---|---|
| **NFStream** | ❌ Định nghĩa flow khác hẳn → domain shift lớn → phải sinh lại data + retrain. |
| **pyflowmeter** | ❌ Cũ, không maintain. |
| **cicflowmeter (pip, hieulw 0.5.0)** | ❌ CLI hỏng (bug lệch tham số positional); output **snake_case** khác schema data train; không maintain. |
| **HERA** | ⚠️ Chỉ offline PCAP→CSV, **không** làm live → chỉ hợp cho chuẩn bị dataset. |
| **Java CICFlowMeter V4 (`cfm`)** | ✅ **Chính là công cụ đã tạo dataset của đồ án.** |

**Bằng chứng quyết định:**
- Tài liệu thu dữ liệu (`Custom_IDS_Testbed/docs/walkthrough.md`) dùng `./cfm` = Java CICFlowMeter V4.
- Chạy `cfm` offline trên pcap cho ra header **khớp 84/84 cột, đúng thứ tự** với `data/*.pcap_Flow.csv` dùng để train.
- `cfm` chế độ **offline không cần quyền root**; chỉ chế độ live-sniff (`-i eth0`) là không ổn định trên WSL (đây là blocker gốc).

**Kết luận:** giữ nguyên `cfm` để đảm bảo parity, nhưng **né live-sniff** bằng kiến trúc **micro-batch**
(bắt gói bằng `tcpdump`, xoay pcap theo chu kỳ, rồi cho `cfm` đọc offline).
Đây cũng chính là workaround mà chính tài liệu đồ án đã ghi lại.

---

## 3. Kiến trúc

```
┌─ WSL (Ubuntu-20.04) — bắt gói + trích đặc trưng ────────────────────────────┐
│                                                                             │
│  tcpdump -i eth0 -G <CHUNK_SEC> -w chunk_%time.pcap  -z extract_chunk.sh    │
│        │  (xoay pcap mỗi CHUNK_SEC giây; postrotate gọi extract_chunk.sh)   │
│        ▼                                                                     │
│  extract_chunk.sh:  cfm <chunk>.pcap  (CICFlowMeter V4, OFFLINE)            │
│        │            → <chunk>.pcap_Flow.csv                                  │
│        ▼            → ghi atomic (.part → rename) vào DROP_DIR               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                        │  DROP_DIR = data/live/
                                        │  (WSL: /mnt/d/…  ↔  Windows: d:\…)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│  Windows — server FastAPI (đã có sẵn torch + model)                          │
│                                                                             │
│  LiveEngine  →  watch data/live/*.csv (poll 1s)                             │
│      → LiveFlowSource: đọc CSV mới                                          │
│          → FeatureExtractor (80 đặc trưng, y hệt replay)                    │
│          → model V8.5 (FT-Transformer)                                      │
│          → postprocess: ConfidenceThresholdRule + PortScanRule             │
│      → broadcast từng flow qua WebSocket → dashboard (realtime)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

Vì sao chia đôi WSL / Windows:
- **WSL đã có sẵn** `cfm` (đã build) + `tcpdump` → không phải cài gì cho phần bắt gói.
- **Windows đã có sẵn** torch + model + server chạy ổn → không phải dựng lại ML stack trong WSL.
- Hai bên nối nhau qua thư mục chia sẻ `data/live/` (`/mnt/d` = `d:\`).

---

## 4. Thành phần mã nguồn

| File | Vai trò |
|---|---|
| `wsl/capture_and_extract.sh` | Bật `tcpdump` xoay pcap, gọi postrotate |
| `wsl/extract_chunk.sh` | Chạy `cfm` offline mỗi chunk → đẩy CSV sang `data/live/` |
| `ids_replay/live_source.py` | `LiveFlowSource`: CSV mới trong drop → events đã dự đoán |
| `ids_replay/streaming.py` | `LiveEngine` (song song `ReplayEngine`) — poll + broadcast |
| `ids_replay/api.py` | Endpoint `/api/live/start`, `/api/live/stop` |
| `server.py` | Composition root — khởi tạo & wire `LiveEngine` |
| `dashboard.html` | Nút **🔴 LIVE**, hiển thị flow live (không có nhãn thật) |

Phần trích đặc trưng + model + hậu xử lý **dùng chung y hệt luồng replay** → parity tuyệt đối,
không sửa `features.py` / `model.py` / `postprocess.py`.

---

## 5. Yêu cầu môi trường

**Windows:**
- Python 3.x + các gói: `fastapi`, `uvicorn[standard]`, `torch`, `pandas`, `scikit-learn`, `joblib`.

**WSL (Ubuntu-20.04):**
- `tcpdump` (`sudo apt install tcpdump`).
- Java 8 (đã có) + CICFlowMeter V4 đã build tại
  `/home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm`.

---

## 6. Cài đặt (một lần)

### 6.1 Windows — server
```bash
cd live_detection
pip install fastapi "uvicorn[standard]" torch pandas scikit-learn joblib
uvicorn server:app --host 127.0.0.1 --port 8000
# mở http://127.0.0.1:8000
```

### 6.2 WSL — cho tcpdump bắt gói không cần sudo mỗi lần

> ⚠️ Các lệnh dưới đây là **lệnh Linux — phải chạy BÊN TRONG WSL**, không phải PowerShell.

Mở WSL rồi chạy (sẽ hỏi mật khẩu Linux của user):
```bash
wsl -d Ubuntu-20.04          # (gõ trong terminal Windows để vào WSL)

# --- từ đây là bên trong WSL ---
sudo setcap cap_net_raw,cap_net_admin+eip "$(readlink -f "$(which tcpdump)")"
getcap "$(readlink -f "$(which tcpdump)")"   # kiểm tra: có 'cap_net_raw' là OK
```

> Thông báo *"Sudo is disabled on this machine"* khi gõ ở PowerShell là **sudo của Windows**,
> không liên quan. `sudo` bên trong WSL vẫn hoạt động bình thường.

---

## 7. Chạy demo

1. **Windows:** đảm bảo server đang chạy → mở `http://127.0.0.1:8000` → bấm **🔴 LIVE**.
2. **WSL:** bật bắt gói:
   ```bash
   bash "/mnt/d/ĐỒ ÁN/graduation-thesis/live_detection/wsl/capture_and_extract.sh"
   ```
   (nếu chưa `setcap`, chạy kèm `sudo`:)
   ```bash
   sudo IFACE=eth0 bash "/mnt/d/ĐỒ ÁN/graduation-thesis/live_detection/wsl/capture_and_extract.sh"
   ```
3. **Tạo traffic** (tấn công hoặc benign). Sau mỗi ~`CHUNK_SEC` giây, flow mới hiện trên
   dashboard kèm nhãn dự đoán; có tấn công → banner **⚠ PHÁT HIỆN TẤN CÔNG**.
4. **Dừng:** bấm **⏹ Dừng LIVE** trên dashboard, và `Ctrl-C` ở WSL.

---

## 8. Tham số (biến môi trường cho script WSL)

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `IFACE` | `eth0` | interface bắt gói |
| `CHUNK_SEC` | `8` | độ dài mỗi chunk = độ trễ near-real-time |
| `DROP_DIR` | `/mnt/d/…/live_detection/data/live` | nơi đẩy CSV cho server |
| `CAP_DIR` | `/home/ning/live_cap/pcap` | nơi tcpdump ghi pcap tạm (ext4, nhanh) |
| `CFM_BIN` | `/home/ning/CICFlowMeter/.../bin/cfm` | đường dẫn cfm |
| `BPF` | `ip and (tcp or udp)` | bộ lọc gói (giống CICFlowMeter) |

Ví dụ chunk 5 giây trên interface khác:
```bash
IFACE=eth1 CHUNK_SEC=5 bash .../capture_and_extract.sh
```

---

## 9. Xử lý sự cố

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| `which/readlink/sudo not recognized` (PowerShell) | Đang chạy lệnh Linux ở Windows. Vào WSL trước (`wsl -d Ubuntu-20.04`). |
| `tcpdump: Operation not permitted` | Chưa `setcap`. Chạy lệnh setcap (mục 6.2) hoặc chạy script bằng `sudo`. |
| Dashboard không thấy flow | Kiểm tra CSV có rơi vào `data/live/` không; xem log tcpdump ở WSL; đảm bảo có traffic khớp `BPF`. |
| `cfm: Could not find or load main class` | Đang dùng nhầm `build/scripts/cfm`. Phải dùng `build/distributions/CICFlowMeter-4.0/bin/cfm`. |
| Nhãn live sai lệch nhiều | Kiểm tra `attacker_ip` trong `replay_config.json` (PortScanRule đọc IP này). |
| Cảnh báo `InconsistentVersionWarning` (sklearn) | scaler/encoder pickle bằng sklearn 1.3.2. Không chặn; muốn sạch thì pin `scikit-learn==1.3.2`. |

---

## 10. Ghi chú kỹ thuật

- **Không có nhãn thật (truth) khi live** → dashboard ẩn confusion matrix & metrics,
  chỉ hiển thị dự đoán + cảnh báo. Đúng bản chất phát hiện thực tế.
- **Ghi CSV atomic**: `extract_chunk.sh` ghi ra `.part` rồi `rename` → server không bao giờ đọc file dở.
- File CSV đã xử lý được chuyển vào `data/live/processed/`.
- **Độ trễ** ≈ `CHUNK_SEC` (thời gian gom 1 chunk) + thời gian `cfm` xử lý (mili-giây với chunk nhỏ).
- Đây là bản **độc lập** của `Final/05_Replay_Detection`, đường dẫn đã chỉnh self-contained (`REPO_ROOT = HERE`).
