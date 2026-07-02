# live_detection — bản làm việc cho Live Detection

> **Nguồn gốc:** đây là **bản sao độc lập** của `Final/05_Replay_Detection` (copy ngày 2026-07-02), dùng làm nơi phát triển/thử nghiệm đường xử lý **live thật** (bắt gói trực tiếp) mà không đụng tới bản replay gốc. Đường dẫn đã chỉnh về **self-contained** (`REPO_ROOT = HERE`).

## Trạng thái hiện tại: có CẢ hai chế độ — REPLAY và LIVE (micro-batch)
Gói hỗ trợ 2 chế độ chạy trên cùng model V8.5 + pipeline hậu xử lý (parity tuyệt đối), chọn ngay trên dashboard:

- **REPLAY** — phát lại flow đã thu sẵn dưới dạng CSV (`*_Flow.csv` do CICFlowMeter xuất), đẩy từng flow theo thời gian thực qua **WebSocket** lên dashboard để FT-Transformer **V8.5** suy luận. Dùng để demo/đo trên dữ liệu **có nhãn**.
- **LIVE — bắt gói trực tiếp, kiến trúc micro-batch** (đã chạy end-to-end): `tcpdump` bắt gói ở WSL, **xoay pcap mỗi `CHUNK_SEC` giây**, rồi cho **CICFlowMeter V4 (`cfm`) chạy OFFLINE** trên từng chunk → CSV đẩy atomic sang `data/live/`; server quét thư mục đó (`LiveFlowSource`) và suy luận realtime, **không có nhãn thật**. Cố ý **né live-sniff của cfm (`-i eth0`)** vì không ổn định trên WSL — giữ `cfm` offline để đảm bảo parity 84/84 cột với dataset train. Chi tiết vận hành: [HUONG_DAN_LIVE.md](HUONG_DAN_LIVE.md).

## Kiến trúc (đã refactor SOLID — package `ids_replay/`)
| Module | Trách nhiệm |
|---|---|
| `config.py` | Nạp + giữ cấu hình (`Settings`) |
| `corpus.py` | Nạp corpus CSV (nguồn REPLAY) |
| `live_source.py` | `LiveFlowSource`: quét `data/live/` tìm CSV mới (do `cfm` ở WSL đẩy sang) → events; dùng chung extractor/model/pipeline với replay (nguồn LIVE) |
| `features.py` | Trích/chuẩn hoá 80 đặc trưng |
| `model.py` | FT-Transformer V8.5 classifier |
| `postprocess.py` | `ConfidenceThresholdRule` (Phương án A) + `PortScanRule` (D1) |
| `scenarios.py` | Quản lý kịch bản replay |
| `explain.py` | Giải thích dự đoán |
| `streaming.py` | `ConnectionManager` (WebSocket) + `ReplayEngine` (phát CSV) + `LiveEngine` (poll `data/live/` realtime) |
| `api.py` | Tạo FastAPI app — endpoint REPLAY (`/api/play` …) và LIVE (`/api/live/start`, `/api/live/stop`); live & replay loại trừ nhau |
| `server.py` | **Composition root** — wire mọi dependency (DI), gồm cả `LiveFlowSource`/`LiveEngine` (thư mục drop qua biến `LIVE_DROP_DIR`) |
| `wsl/capture_and_extract.sh` + `wsl/extract_chunk.sh` | Lớp bắt gói LIVE ở WSL: `tcpdump` xoay pcap → `cfm` offline mỗi chunk → CSV sang `data/live/` |

`live_replay_server.py` chỉ là shim tương thích lệnh cũ (`from server import app`).

> **`model_defs/`** (vendored): chứa `phase2_ft_transformer_v2.py` (kiến trúc FT-Transformer) + `hybrid_feature_scaler.py`. Trong repo gốc 2 file này nằm rải rác (`CIC_IDS_2017_Workspace/src/models`, `Phase3_4_Retrain/src`); ở gói này chúng được đóng kèm để **self-contained** — `ids_replay/model.py` nạp chúng qua `model_defs/`.

## Chạy server (chung cho cả REPLAY và LIVE)
```bash
cd live_detection
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000     # PHẢI chạy từ thư mục live_detection/
# Mở http://localhost:8000 → dashboard có 2 chế độ:
#   • REPLAY: chọn kịch bản → xem flow + nhãn dự đoán vs nhãn thật
#   • LIVE  : bấm "LIVE" → server quét data/live/ và hiển thị flow realtime
```
> Đường dẫn model/data trong `replay_config.json` là **tương đối so với chính thư mục `live_detection/`** (bản độc lập đặt `REPO_ROOT = HERE` trong `server.py`). Toàn bộ tài nguyên (`models/`, `data/`, `model_defs/`) nằm trong thư mục này → self-contained.

## Chạy LIVE (bắt gói trực tiếp — micro-batch)
Cần thêm lớp bắt gói ở **WSL** (song song với server): `tcpdump` xoay pcap → `cfm` offline mỗi chunk → CSV vào `data/live/`.
```bash
# Ở WSL, cùng bản repo với server (để data/live/ khớp nhau):
bash wsl/capture_and_extract.sh                 # eth0, chunk 8s (mặc định)
IFACE=eth0 CHUNK_SEC=5 bash wsl/capture_and_extract.sh   # tuỳ chỉnh
```
> Nếu server và script capture chạy ở **2 bản repo khác nhau** (vd server ở `/home/ning`, capture ghi sang `/mnt/d`), đặt biến `LIVE_DROP_DIR` cho server trỏ đúng thư mục drop mà script đang ghi. Yêu cầu WSL: `tcpdump` + CICFlowMeter V4 (`cfm`) đã build. Xử lý sự cố + tinh chỉnh: xem [HUONG_DAN_LIVE.md](HUONG_DAN_LIVE.md).

## Dữ liệu kèm theo
Chỉ kèm **`data/dos_only.pcap_Flow.csv`** (mẫu nhỏ) để demo chạy ngay kịch bản DoS. Các kịch bản `portscan / bruteforce / webattack / benign` **không kèm** (nặng ~212MB) — xem [data/README.md](data/README.md) để thu/tải.

## Cấu hình quyết định (từ `replay_config.json`)
- `conf_threshold = 0.6` (**Phương án A**): dự đoán tấn công có confidence < ngưỡng → hạ về Benign. Theo Bảng tiến trình replay (Chương 5): T=0,6 đưa **Macro F1 0,679 → 0,725**, Benign Recall **75,4% → 95,2%** (attack recall vẫn ~98%).
- `portscan_rule` (**D1**, bật): đếm cổng đích theo nguồn, cửa sổ 2s, ngưỡng 15 cổng → recall 99,2%, benign FP 0%. Nâng **PortScan F1 từ 0,000 → 0,996** mà không train lại.
- **Kết hợp cả hai luật hậu xử lý → Macro F1 cuối = 0,978** (đúng số liệu End-to-End trong báo cáo).

## Trọng số
`models/v8_5_model.pt` + `v8_5_scaler.pkl` + `v8_5_encoder.pkl` (5 lớp: PortScan, Brute Force, Web Attack, DoS, Benign). Macro F1 V8.5 ≈ **91,7%** trên val đa miền.
