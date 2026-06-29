# GĐ4 — Hybrid IDS End-to-End (V8.5): HƯỚNG DẪN CHẠY

> **Hệ thống End-to-End thật của đồ án dùng FT-Transformer V8.5** (không phải NSL-KDD). Tầng dấu hiệu (Snort) + tầng học máy (V8.5) bù điểm mù cho nhau. **Demo chạy được** của E2E là hệ thống **replay** ở [../05_Replay_Detection/](../05_Replay_Detection/) (đã verify chạy).

## 1. Mục tiêu & sơ đồ luồng
```
Traffic → Snort 3 (dấu hiệu) ─┐
                              ├─► hợp nhất cảnh báo (hai tầng bù nhau)
   pcap → CICFlowMeter → FT-Transformer V8.5 (ML, 80-feat, 5 lớp) ─┘
```
Kiểm chứng: DoS slowhttptest chỉ ML bắt; XSS payload ngắn chỉ Snort bắt → mỗi tầng là điều kiện cần.

## 2. Cấu hình máy
i7 Gen11 8c/16t, RAM 16GB, **CPU-only**. Win11 22H2 + WSL2 Ubuntu 22.04 (mirrored networking). Python 3.8–3.12.

## 3. Cài đặt từ 0
```bash
# Tầng ML (V8.5): xem ../05_Replay_Detection/requirements.txt (torch, fastapi...)
# Tầng dấu hiệu + trích đặc trưng:
sudo apt install -y snort                 # Snort 3
# CICFlowMeter: https://github.com/ahlashkari/CICFlowMeter (hoặc bản Python hieulw)
sudo apt install -y nmap hydra slowhttptest hping3
```
Chi tiết: [../HUONG_DAN_CAI_DAT.md](../HUONG_DAN_CAI_DAT.md).

## 4. Tải/thu dữ liệu
Corpus tấn công thu trên Testbed — xem [../03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md](../03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md).

## 5. Chạy
**(A) Demo E2E nhanh nhất — hệ thống replay V8.5:**
```bash
cd ../05_Replay_Detection && uvicorn server:app --port 8000   # mở dashboard.html
```
**(B) Pipeline thật (Snort + CICFlowMeter + V8.5):**
- `wsl_pipeline/testbed_inference_cascade_v2.py`, `testbed_inference_cascade_9class.py` — inference V8.5 trên `*_Flow.csv`.
- `snort/` — rules + configs để Snort sinh alert.
- Luồng: Snort sinh alert → CICFlowMeter xuất `*_Flow.csv` → script inference V8.5 phân loại → đối chiếu hai tầng.

## 6. Kết quả mong đợi
- Tính bổ sung hai tầng (Bảng E2E Chương 5): mỗi loại tấn công được ít nhất một tầng phát hiện.
- Trên corpus phát lại: V8.5 đơn lẻ Macro F1 0,679 → + ngưỡng tin cậy + luật quét cổng → **Macro F1 0,978** (PortScan F1 0,000 → 0,996).

## 7. Troubleshooting
| Lỗi | Xử lý |
|---|---|
| PortScan không tách được (WSL2) | NAT đổi phân phối flow → dùng surrogate (thu trên Win11 host) + luật đếm cổng (GĐ5) |
| CICFlowMeter sai cổng đích | kiểm tra mirrored networking |
| Snort không sinh alert | kiểm tra iface + ruleset trong `snort/` |
| Muốn xem demo ngay không cần Snort | dùng (A) hệ thống replay V8.5 |
