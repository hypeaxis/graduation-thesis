# GĐ5 — Corpus replay

Đây là **nguồn duy nhất** của corpus replay trong repo. `Final/05_Replay_Detection/data/` symlink về thư mục này — đừng nhân bản thêm.

| Kịch bản | File | Kích thước |
|---|---|---|
| PortScan | `portscan_only.pcap_Flow.csv` | ~86MB |
| Brute Force | `bruteforce_only.pcap_Flow.csv` | ~100MB |
| Benign | `benign_only.pcap_Flow.csv` | ~17MB |
| Web Attack | `webattack_only.pcap_Flow.csv` | ~12MB |
| DoS | `dos_only.pcap_Flow.csv` | ~6,7MB |

`replay_config.json` đã trỏ sẵn đường dẫn `data/<file>`.

> Định dạng: CSV do **CICFlowMeter** xuất (mỗi dòng = 1 flow với ~80 đặc trưng thống kê).

## Thu lại nếu cần

| Kịch bản | Cách lấy |
|---|---|
| PortScan | thu trên Win11 host (nmap) → CICFlowMeter |
| Brute Force | hydra trên Testbed → CICFlowMeter |
| Web Attack | DVWA + payload → CICFlowMeter |
| Benign | background traffic → CICFlowMeter |

Quy trình thu chi tiết: [../../Final/03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md](../../Final/03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md).

## `analysis/`

Dataset dùng cho huấn luyện/đánh giá (benign thật, các lớp tấn công tách riêng) — xem `../training/`.
