# GĐ5 — Replay Detection (phát hiện dạng phát lại)

## ⚠️ "Replay" ≠ "Live"
Hệ thống này **phát lại** các flow đã thu sẵn dưới dạng CSV (`*_Flow.csv` do CICFlowMeter xuất), đẩy từng flow theo thời gian thực qua **WebSocket** lên dashboard, và để FT-Transformer **V8.5** suy luận. Nó **KHÔNG bắt gói trực tiếp** từ card mạng. Đường xử lý live thật là hướng phát triển — nhưng dùng đúng mô hình, bộ tiền xử lý và logic quyết định mà bản live sẽ dùng.

## Kiến trúc (đã refactor SOLID — package `ids_replay/`)
| Module | Trách nhiệm |
|---|---|
| `config.py` | Nạp + giữ cấu hình (`Settings`) |
| `corpus.py` | Nạp corpus CSV |
| `features.py` | Trích/chuẩn hoá 80 đặc trưng |
| `model.py` | FT-Transformer V8.5 classifier |
| `postprocess.py` | `ConfidenceThresholdRule` (Phương án A) + `PortScanRule` (D1) |
| `scenarios.py` | Quản lý kịch bản replay |
| `explain.py` | Giải thích dự đoán |
| `streaming.py` | `ReplayEngine` + `ConnectionManager` (WebSocket) |
| `api.py` | Tạo FastAPI app |
| `server.py` | **Composition root** — wire mọi dependency (DI) |

`live_replay_server.py` chỉ là shim tương thích lệnh cũ (`from server import app`).

> **`model_defs/`** (vendored): chứa `phase2_ft_transformer_v2.py` (kiến trúc FT-Transformer) + `hybrid_feature_scaler.py`. Trong repo gốc 2 file này nằm rải rác (`CIC_IDS_2017_Workspace/src/models`, `Phase3_4_Retrain/src`); ở gói này chúng được đóng kèm để **self-contained** — `ids_replay/model.py` nạp chúng qua `model_defs/`.

## Chạy
```bash
cd 05_Replay_Detection
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000     # PHẢI chạy từ thư mục 05_Replay_Detection/
# Mở dashboard.html → chọn kịch bản → xem flow + nhãn dự đoán realtime
```
> Đường dẫn model/data trong `replay_config.json` là **tương đối so với `Final/`** (= thư mục cha của `05_Replay_Detection/`, do `server.py` đặt `REPO_ROOT = HERE.parents[0]`). Nếu di chuyển thư mục, chỉnh lại `REPO_ROOT` hoặc các path trong config.

## Dữ liệu kèm theo
Chỉ kèm **`data/dos_only.pcap_Flow.csv`** (mẫu nhỏ) để demo chạy ngay kịch bản DoS. Các kịch bản `portscan / bruteforce / webattack / benign` **không kèm** (nặng ~212MB) — xem [data/README.md](data/README.md) để thu/tải.

## Cấu hình quyết định (từ `replay_config.json`)
- `conf_threshold = 0.6` (**Phương án A**): dự đoán tấn công có confidence < ngưỡng → hạ về Benign. Theo Bảng tiến trình replay (Chương 5): T=0,6 đưa **Macro F1 0,679 → 0,725**, Benign Recall **75,4% → 95,2%** (attack recall vẫn ~98%).
- `portscan_rule` (**D1**, bật): đếm cổng đích theo nguồn, cửa sổ 2s, ngưỡng 15 cổng → recall 99,2%, benign FP 0%. Nâng **PortScan F1 từ 0,000 → 0,996** mà không train lại.
- **Kết hợp cả hai luật hậu xử lý → Macro F1 cuối = 0,978** (đúng số liệu End-to-End trong báo cáo).

## Trọng số
`models/v8_5_model.pt` + `v8_5_scaler.pkl` + `v8_5_encoder.pkl` (5 lớp: PortScan, Brute Force, Web Attack, DoS, Benign). Macro F1 V8.5 ≈ **91,7%** trên val đa miền.
