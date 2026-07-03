# 🛡️ Hybrid NIDS — Hệ thống Phát hiện Xâm nhập Mạng lai ghép (Snort + FT-Transformer)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-Deep%20Learning-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![React](https://img.shields.io/badge/React-Frontend-61DAFB.svg)
![Snort](https://img.shields.io/badge/Snort-IDS-CD2027.svg)

> **Đồ án Tốt nghiệp:** Nghiên cứu và xây dựng hệ thống phát hiện xâm nhập mạng kết hợp **IDS dựa trên luật (Snort)** và **học sâu (FT-Transformer)**, đi từ dữ liệu benchmark (NSL-KDD, CIC-IDS-2017) đến một testbed thực chiến chạy trên WSL2 với dữ liệu tự thu.

---

## 📖 Tổng quan

Repo này là toàn bộ quá trình làm đồ án — **không chỉ sản phẩm cuối** mà cả 5 giai đoạn nghiên cứu, mỗi giai đoạn nằm trong một workspace riêng. Ý tưởng xuyên suốt:

```
            ┌─────────────┐      ┌──────────────────┐      ┌────────────────────┐
  Traffic → │  Snort 3    │ ───► │  CICFlowMeter     │ ───► │  FT-Transformer     │ ──► Cảnh báo
            │ (dấu hiệu)  │      │  (trích đặc trưng)│      │  (ML đa lớp)        │
            └─────────────┘      └──────────────────┘      └────────────────────┘
```

IDS luật (Snort) bắt nhanh, ít báo giả nhưng bỏ sót biến thể mới; mô hình học sâu (FT-Transformer) học hành vi từ flow, bắt được tấn công chưa có luật nhưng nhạy với covariate shift. Hai tầng bù điểm mù cho nhau.

---

## 🧭 Bản đồ 5 giai đoạn & workspace tương ứng

| GĐ | Workspace | Nội dung | Mô hình | Kết quả |
|----|-----------|----------|---------|---------|
| 1 | [`NSL_KDD_Workspace/`](NSL_KDD_Workspace/) | Nghiên cứu nền tảng, chứng minh tính khả thi trên bộ dữ liệu kinh điển NSL-KDD | FT-Transformer 122-feature + LightGBM + Meta-LR (Stacking) | Macro F1 ≈ **0,681** |
| 2 | [`CIC_IDS_2017_Workspace/`](CIC_IDS_2017_Workspace/) | Two-Stage Cascade + Asymmetric Ensemble Voting trên CIC-IDS-2017 (2,8 triệu dòng, 9 lớp) | Gating + Expert FT-Transformer V2 + Random Forest + KNN + HNM | Acc **99,55%**, Macro F1 **0,9294** |
| 3 | [`Custom_IDS_Testbed/`](Custom_IDS_Testbed/) + [`Domain_Adaptation_Workspace/`](Domain_Adaptation_Workspace/) + [`Phase3_4_Retrain/`](Phase3_4_Retrain/) | Testbed WSL2 thật (Snort + CICFlowMeter), chẩn đoán covariate shift, thu dữ liệu thực, retrain V5→V8.5 | FT-Transformer 80-feature V8.5 (5 lớp) | Macro F1 **91,7%** |
| 4 | [`Custom_IDS_Testbed/`](Custom_IDS_Testbed/) | Pipeline Hybrid IDS End-to-End: Snort + CICFlowMeter + FT-Transformer trên mạng LAN giả lập xuyên máy (Mirrored Networking WSL2) | Triển khai | Dashboard + pipeline WSL thật |
| 5 | [`live_detection/`](live_detection/) *(bản đang phát triển)* / [`Replay_Live_Detection/`](Replay_Live_Detection/) *(bản gốc)* | Demo realtime: **REPLAY** (phát lại corpus CSV đã thu) + **LIVE micro-batch** (`tcpdump` → CICFlowMeter offline mỗi chunk → suy luận) qua WebSocket lên dashboard | Tái dùng V8.5 | Macro F1 end-to-end **0,978** (với luật hậu xử lý); PortScan F1 0,996 |

> **`Final/`** là gói **nộp bài đã đóng gói portable** (đủ code 5 GĐ + trọng số demo + hướng dẫn, không kèm dữ liệu thô/báo cáo, mục tiêu zip < 30MB) — xem [Final/README.md](Final/README.md). `Final.zip` là bản zip của thư mục đó.

---

## 📂 Cấu trúc thư mục đầy đủ

| Thư mục | Vai trò |
|---|---|
| [`NSL_KDD_Workspace/`](NSL_KDD_Workspace/) | GĐ1 — data pipeline, training, `Final_Product/` (backend+frontend+inference demo NSL-KDD) |
| [`CIC_IDS_2017_Workspace/`](CIC_IDS_2017_Workspace/) | GĐ2 — feature engineering, FT-Transformer V2, Hybrid Cascade Ensemble, notebooks EDA |
| [`Custom_IDS_Testbed/`](Custom_IDS_Testbed/) | GĐ3/4 — testbed thực chiến: cấu hình Snort, script thu dữ liệu isolated (`collect_isolated.sh`), tài liệu kiến trúc Hybrid IDS |
| [`Domain_Adaptation_Workspace/`](Domain_Adaptation_Workspace/) | Nghiên cứu concept drift / domain adaptation khi model CIC-IDS-2017 gặp dữ liệu testbed lệch phân phối |
| [`Phase3_4_Retrain/`](Phase3_4_Retrain/) | Các vòng retrain V5 → V8.5 (SMOTE, Focal Loss, Cost-Sensitive Learning, Threshold Calibration) để giải quyết PortScan F1 thấp |
| [`Replay_Live_Detection/`](Replay_Live_Detection/) | Bản demo replay-based gốc (package `ids_replay/` kiến trúc SOLID) — kèm corpus CSV đầy đủ 5 lớp (~212MB) |
| [`live_detection/`](live_detection/) | Bản làm việc hiện tại (bản sao độc lập, self-contained từ `Replay_Live_Detection`), bổ sung chế độ **LIVE micro-batch** bắt gói thật qua WSL |
| [`Final/`](Final/) | Gói nộp bài portable, tổng hợp code + trọng số + hướng dẫn cả 5 GĐ (không kèm dữ liệu thô/báo cáo) |
| [`Noi_dung_do_an/`](Noi_dung_do_an/) | Nội dung viết luận văn (template LaTeX SOICT, nội dung từng chương, ghi chú) |
| [`docs/`](docs/) | Dữ liệu flow CSV thu thập được (pcap → CICFlowMeter) + `Project_Documentation/` (báo cáo thực trạng, roadmap, hướng dẫn thu dữ liệu) |
| [`work_session_logs/`](work_session_logs/) | Nhật ký từng phiên làm việc, theo ngày |
| `KE_HOACH_REFACTOR_FINAL.md` | Kế hoạch đã dùng để đóng gói `Final/` từ codebase gốc |
| `Instruction.md` | Kế hoạch xây dựng sản phẩm gốc theo 5 giai đoạn |

---

## ⚙️ Yêu cầu hệ thống

- Linux / WSL2 (Ubuntu 20.04/22.04); Windows 11 host cho nhánh Testbed (Mirrored Networking)
- Python 3.8–3.12 (torch chưa có wheel cho 3.14) & Node.js (cho `NSL_KDD_Workspace/Final_Product/frontend`)
- RAM 8GB tối thiểu, khuyến nghị 16GB cho CIC-IDS-2017 & Testbed
- CPU-only là đủ để chạy demo/inference

## 🚀 Chạy nhanh (demo hệ thống thật — REPLAY/LIVE V8.5)

```bash
cd live_detection
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000     # chạy TỪ thư mục live_detection/
# Mở http://localhost:8000 → chọn chế độ REPLAY (kịch bản có sẵn) hoặc LIVE (cần script WSL, xem HUONG_DAN_LIVE.md)
```

Các điểm vào khác:
1. **[NSL-KDD Final Product](NSL_KDD_Workspace/Final_Product/README.md)** — demo mô phỏng NSL-KDD (backend + frontend + inference)
2. **[CIC-IDS-2017 Cascade](CIC_IDS_2017_Workspace/README.md)** — huấn luyện lại Hybrid Ensemble
3. **[Custom IDS Testbed](Custom_IDS_Testbed/docs/)** — cấu hình Snort + CICFlowMeter + WSL mirrored network
4. **[Gói nộp bài `Final/`](Final/README.md)** — bản portable đầy đủ 5 giai đoạn, tự chứa, ít phụ thuộc nhất

---

## 🔬 Điểm sáng kỹ thuật

1. **Hybrid IDS (Signature + Anomaly):** kết hợp Snort (luật đã biết) với FT-Transformer (nhận diện zero-day qua hành vi flow).
2. **Two-Stage Cascade & Ensemble Voting:** tầng Gating chặn traffic bình thường, tầng Expert dùng Voting giữa Transformer và các thuật toán Tree-based để giảm False Positive.
3. **Luật hậu xử lý bù mô hình:** `ConfidenceThresholdRule` (hạ dự đoán tấn công có độ tin cậy thấp về Benign) + `PortScanRule` (đếm cổng đích theo cửa sổ thời gian) nâng Macro F1 end-to-end từ 0,679 lên 0,978 mà không cần train lại.
4. **Pipeline realtime từ gói tin thô đến nhãn:** `tcpdump` → CICFlowMeter (offline theo micro-batch) → FT-Transformer → WebSocket → dashboard, đo bằng mili-giây.
5. **Testbed mạng thật xuyên máy:** giả lập tấn công/nạn nhân trên 2 máy vật lý qua WSL2 Mirrored Networking, dùng để chẩn đoán và khắc phục covariate shift giữa dataset benchmark và mạng thật.

---

## 🛠️ Liên hệ & Tác giả
* **Sinh viên thực hiện**: Đỗ Tuấn Minh
* **Mã số sinh viên**: 20225741
* **Giáo viên hướng dẫn**: PGS. TS. Nguyễn Linh Giang
* **Trường/Khoa**: Đại học Bách Khoa Hà Nội, Trường Công nghệ Thông tin và Truyền thông (SOICT)
