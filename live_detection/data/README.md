# GĐ5 — Corpus replay

## Kèm sẵn trong gói
- `dos_only.pcap_Flow.csv` (~6,4MB) — kịch bản DoS, để demo chạy ngay.

## KHÔNG kèm (nặng ~212MB tổng) — tự thu/tải
| Kịch bản | File | Cách lấy |
|---|---|---|
| PortScan | `portscan_only.pcap_Flow.csv` (~82MB) | thu trên Win11 host (nmap) → CICFlowMeter |
| Brute Force | `bruteforce_only.pcap_Flow.csv` (~95MB) | hydra trên Testbed → CICFlowMeter |
| Web Attack | `webattack_only.pcap_Flow.csv` (~12MB) | DVWA + payload → CICFlowMeter |
| Benign | `benign_only.pcap_Flow.csv` (~17MB) | background traffic → CICFlowMeter |

Quy trình thu chi tiết: [../../Final/03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md](../../Final/03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md).

Sau khi có file, đặt vào thư mục này — `replay_config.json` đã trỏ sẵn đường dẫn `data/<file>`.

> Định dạng: CSV do **CICFlowMeter** xuất (mỗi dòng = 1 flow với ~80 đặc trưng thống kê).
