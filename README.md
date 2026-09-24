# AI-Powered & Hybrid Network Intrusion Detection System (Hybrid NIDS)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![Snort](https://img.shields.io/badge/Snort%203-IDS-CD2027.svg)
![WebSocket](https://img.shields.io/badge/WebSocket-Realtime-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> **Hệ thống Phát hiện Xâm nhập Mạng thông minh thời gian thực kết hợp Luật tĩnh (Snort 3), Học sâu dòng chảy (FT-Transformer V8.5) và Luật hậu xử lý tương quan.**

---

## 1. Giới thiệu Tổng quan (Overview)

Hệ thống **AI-Powered Hybrid NIDS** được thiết kế để giám sát, phân tích dòng chảy mạng và phát hiện các mối đe dọa an ninh mạng nguy hiểm (*DoS, Brute Force, PortScan, Web Attacks...*) theo thời gian thực.

### Điểm đột phá kiến trúc:
1. **Kiến trúc Lai ghép (Hybrid IDS)**: Kết hợp tốc độ và độ chính xác của **Snort 3** (Signature-based IDS) với năng lực nhận diện biến thể bất thường của **Học sâu (Anomaly-based IDS)**.
2. **FT-Transformer V8.5 chống Covariate Shift**: Mô hình Feature Tokenizer Transformer được tinh chỉnh đặc thù, giải quyết thành công sự suy giảm hiệu năng khi chuyển giao từ dữ liệu học thuật (CIC-IDS-2017) sang môi trường mạng vật lý / WSL2 thực tế.
3. **Bộ luật hậu xử lý thông minh (Domain-Specific Postprocessing)**: Áp dụng cơ chế lọc ngưỡng tin cậy ($T=0.6$) và luật theo dõi cửa sổ trượt quét cổng (Sliding Window Rule D1), đưa **Macro F1 toàn hệ thống lên 0.978** và triệt tiêu False Positives.
4. **Kiến trúc Live Micro-batch Parity**: Giải quyết bài toán bắt gói trực tiếp từ card mạng bằng cách kết hợp `tcpdump` xoay file theo chu kỳ và Java **CICFlowMeter V4** (`cfm`) chế độ offline, đảm bảo **100% feature parity (80/80 cột)** không bị lệch phân phối đặc trưng.

```
                    ┌─────────────┐      ┌──────────────────┐      ┌────────────────────┐
Lưu lượng mạng ───► │   Snort 3   │ ───► │  CICFlowMeter    │ ───► │  FT-Transformer    │ ──► Dashboard Cảnh báo
                    │ (Dấu hiệu)  │      │  (Trích 80 Flow) │      │  (AI phân loại)    │     (WebSocket)
                    └─────────────┘      └──────────────────┘      └────────────────────┘
```

---

## 2. Bản đồ Cấu trúc Dự án (Project Structure)

Dự án được tổ chức rõ ràng theo các module chức năng:

```
graduation-thesis/
├── live_detection/                     [SẢN PHẨM PHÁT HIỆN TRỰC TIẾP] Live Micro-batch
│   ├── wsl/                            # Script bắt gói (tcpdump) và trích flow (cfm) trên WSL
│   ├── ids_replay/                     # Package lõi: LiveEngine, FeatureExtractor, Model V8.5, Rules
│   ├── models/                         # Trọng số V8.5 (v8_5_model.pt, scaler, encoder)
│   ├── server.py                       # FastAPI WebSocket Server (Composition Root)
│   ├── dashboard.html                  # Giao diện SOC Dashboard thời gian thực
│   └── HUONG_DAN_LIVE.md               # Hướng dẫn chi tiết vận hành luồng bắt gói trực tiếp
│
├── Final/                              [GÓI SẢN PHẨM ĐỘC LẬP] Đóng gói chuẩn < 30MB
│   ├── 01_NSL_KDD/                     # Giai đoạn 1: Nghiên cứu nền tảng NSL-KDD
│   ├── 02_CIC_IDS_2017/                # Giai đoạn 2: Xử lý dữ liệu lớn, FT-Transformer V2, Cascade Voting
│   ├── 03_Testbed_Retrain/             # Giai đoạn 3: Sinh dữ liệu tự động, chẩn đoán Covariate Shift & V8.5
│   ├── 04_HybridIDS_Deployment/        # Giai đoạn 4: Tích hợp toàn trình Snort + WSL + Pipeline
│   ├── 05_Replay_Detection/            # Giai đoạn 5: Hệ thống Replay kèm trọng số V8.5 chạy ngay
│   ├── HUONG_DAN_CAI_DAT.md            # Cài đặt chung: WSL2, Python venv, Snort 3, CICFlowMeter
│   ├── MODELS.md                       # Bản kiểm kê toàn bộ file trọng số
│   └── README.md                       # Hướng dẫn tổng quan gói Final
├── Final.zip                           File zip hoàn chỉnh nộp lưu trữ / bảo vệ (<30MB)
│
└── Các Không gian Nghiên cứu Gốc:
    ├── NSL_KDD_Workspace/              # Thử nghiệm ban đầu với NSL-KDD (Autoencoder + FT-Transformer)
    ├── CIC_IDS_2017_Workspace/         # Huấn luyện sâu với CIC-IDS-2017 (2.8 triệu mẫu)
    ├── Custom_IDS_Testbed/             # Môi trường thực nghiệm WSL2, kịch bản tấn công tự động
    ├── Phase3_4_Retrain/               # Lịch sử các phiên bản retrain v5 -> v8.5
    └── Domain_Adaptation_Workspace/    # Phân tích độ lệch miền (Domain Shift)
```

---

## 3. Tiến trình 5 Giai đoạn & Kết quả Thực nghiệm

| Giai đoạn | Thư mục | Trọng tâm nghiên cứu | Mô hình & Thuật toán | Kết quả (F1 / Accuracy) |
| :--- | :--- | :--- | :--- | :--- |
| **GĐ 1** | [`Final/01_NSL_KDD`](./Final/01_NSL_KDD) | Mô hình nền tảng trên NSL-KDD (122 đặc trưng). | Autoencoder Gate + FT-Transformer + LightGBM (Stacking) | Macro F1 ≈ **0.6809** |
| **GĐ 2** | [`Final/02_CIC_IDS_2017`](./Final/02_CIC_IDS_2017) | Giải quyết mất cân bằng cực đoan trên 2.8M mẫu. | FT-Transformer V2 + Two-Stage Cascade + Asymmetric Voting | Accuracy **99.55%**, Macro F1 **0.9294** |
| **GĐ 3** | [`Final/03_Testbed_Retrain`](./Final/03_Testbed_Retrain) | Chẩn đoán Covariate Shift & huấn luyện lại. | FT-Transformer V8.5 Combined (80 đặc trưng, 5 lớp) | Macro F1 **91.70%** (Validation đa miền) |
| **GĐ 4** | [`Final/04_HybridIDS_Deployment`](./Final/04_HybridIDS_Deployment) | Tích hợp toàn trình trên WSL Mirrored Network. | Snort 3 + CICFlowMeter + FT-Transformer V8.5 | Đo lường độ trễ & tính bổ sung Snort/ML |
| **GĐ 5** | [`Final/05_Replay_Detection`](./Final/05_Replay_Detection)<br>[`live_detection`](./live_detection) | Phát hiện Replay & Live Micro-batch thời gian thực. | FT-Transformer V8.5 + Confidence Threshold + PortScan Rule | **Macro F1 = 0.978**, **Accuracy = 97.7%** |

---

## 4. Hướng dẫn Khởi chạy Nhanh (Quick Start)

### 4.1 Phương án 1: Chạy bản Demo Replay (An toàn 100% trên Windows / Linux)

Phương án này phát lại dòng chảy dữ liệu thực nghiệm đã thu thập, chạy mượt mà không cần quyền root hay card mạng:

```bash
cd Final/05_Replay_Detection
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên Linux/WSL:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn server:app --host 127.0.0.1 --port 8000
```
- Mở trình duyệt tại: `http://127.0.0.1:8000` (hoặc mở trực tiếp file `dashboard.html`).
- Chọn kịch bản (ví dụ: `DoS`) và bấm **Play** để quan sát luồng suy luận thời gian thực.

---

### 4.2 Phương án 2: Chạy bản Live Detection Bắt gói Trực tiếp (WSL + Windows)

Bắt gói tin thật từ card mạng, trích xuất đặc trưng và phân loại trực tiếp:

1. **Khởi động Server phân tích (Windows Host):**
   ```bash
   cd live_detection
   pip install fastapi "uvicorn[standard]" torch pandas scikit-learn joblib
   uvicorn server:app --host 127.0.0.1 --port 8000
   ```
2. **Khởi động Bộ bắt gói (bên trong WSL):**
   ```bash
   # Cấp quyền cho tcpdump không cần sudo (làm 1 lần)
   sudo setcap cap_net_raw,cap_net_admin+eip "$(readlink -f "$(which tcpdump)")"

   # Chạy script bắt gói và trích xuất chunk
   bash live_detection/wsl/capture_and_extract.sh
   ```
3. Mở `http://127.0.0.1:8000` và bấm nút **LIVE** trên Dashboard để theo dõi lưu lượng mạng trực tiếp.

> Xem chi tiết tài liệu hướng dẫn vận hành tại: [`live_detection/HUONG_DAN_LIVE.md`](./live_detection/HUONG_DAN_LIVE.md).

---

## 5. Tài liệu Nghiên cứu & Hướng dẫn Kỹ thuật

- **Hướng dẫn Vận hành Live Detection**: [`live_detection/HUONG_DAN_LIVE.md`](./live_detection/HUONG_DAN_LIVE.md)
- **Hướng dẫn Cài đặt Hệ thống**: [`Final/HUONG_DAN_CAI_DAT.md`](./Final/HUONG_DAN_CAI_DAT.md)
- **Kiểm kê Trọng số Mô hình**: [`Final/MODELS.md`](./Final/MODELS.md)
- **Báo cáo Tiến trình Thử nghiệm & Mô hình V8.5**: [`Phase3_4_Retrain/v8/tong_hop_tat_ca_versions.md`](./Phase3_4_Retrain/v8/tong_hop_tat_ca_versions.md)

---

## 6. Yêu cầu Môi trường (Prerequisites)

- **Hệ điều hành**: Windows 11 + WSL 2 (Ubuntu 20.04/22.04 LTS).
- **Python**: 3.8 – 3.12 (khuyến nghị 3.10 hoặc 3.11).
- **RAM**: Tối thiểu 8GB (khuyến nghị 16GB).
- **Công cụ An ninh**: Snort 3, Java 8 (chạy CICFlowMeter-4.0 `cfm`), `tcpdump`, `nmap`, `hydra`.
