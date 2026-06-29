# GĐ3 — HƯỚNG DẪN THU DỮ LIỆU THỰC (Testbed WSL2)

Thu traffic thật trong mạng lab để retrain V8.5, giải quyết covariate shift.

## 1. Mô hình mạng
```
┌────────────── Win11 Host (22H2) ──────────────┐
│  WSL2 Ubuntu 22.04 (networkingMode=mirrored)   │
│   ├── Victim   (DVWA / dịch vụ web, SSH)        │
│   ├── Attacker (Kali tools: nmap, hydra, ...)   │
│   └── Sensor   (Snort 3 + CICFlowMeter)         │
└────────────────────────────────────────────────┘
```
**Bắt buộc** `.wslconfig` → `networkingMode=mirrored` (xem [../HUONG_DAN_CAI_DAT.md](../HUONG_DAN_CAI_DAT.md)).

## 2. Công cụ
`snort`, `CICFlowMeter`, `nmap`, `thc-hydra`, `slowhttptest`, `hping3`, `DVWA`, wordlist `rockyou.txt`.

## 3. Quy trình thu (mỗi loại 1 corpus riêng)
| Loại | Sinh tấn công | Script hỗ trợ |
|---|---|---|
| Benign | background traffic + duyệt web bình thường | `data_collection/auto_benign*.py`, `background_traffic_generator.py` |
| PortScan | `nmap -sS -p- <victim>` (thu trên **Win11 host** để có phân phối cổng đúng) | `data_collection/auto_attack*.py` |
| Brute Force | `hydra -L users -P rockyou.txt <victim> ssh/http` | `auto_attack*.py` |
| DoS | `slowhttptest`, `hulk/` | `data_collection/hulk/` |
| Web Attack | payload SQLi/XSS lên DVWA | `auto_attack*.py` |

Các bước:
1. Bật capture: `snort -i <iface> -L pcap` (hoặc tcpdump) ghi `*.pcap`.
2. Chạy kịch bản tấn công/benign tương ứng.
3. Trích đặc trưng: `cicflowmeter -f <file>.pcap -c <file>_Flow.csv`.
4. Gắn nhãn + gộp: `data_collection/dataset_builder*.py` → CSV có cột label.

## 4. Dựng dataset V8.5
```bash
python retrain/v8/v8.5_Combined/build_dataset_v8_5.py   # gộp 5 lớp → Combined_V8_5.csv
```
Bổ sung Web Attack từ CIC nếu thiếu mẫu: `retrain/v8/v8.5_Combined/cic_webattack_mapper.py`.

## 5. Lưu ý quan trọng
- **PortScan trong WSL2 không tách được** (NAT đổi phân phối đặc trưng flow) → dùng dữ liệu surrogate thu trên Win11 host + luật hậu xử lý đếm cổng (GĐ5).
- Giữ mỗi corpus 1 file `*_Flow.csv` riêng để replay (GĐ5).
