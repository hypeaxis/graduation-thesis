# GĐ3 — Testbed + Retrain V8.5: HƯỚNG DẪN CHẠY

## 1. Mục tiêu & sơ đồ luồng
Chẩn đoán **covariate shift** khi đưa mô hình CIC sang môi trường mạng thật (WSL2 Testbed), thu dữ liệu thực, và **tái huấn luyện hoàn toàn** thành **V8.5** (5 lớp: PortScan, Brute Force, Web Attack, DoS, Benign).
```
Thu traffic thật (WSL2) → CICFlowMeter → dataset Testbed → retrain FTT 80-feat (v8.1→v8.5) → V8.5
```

## 2. Cấu hình máy
i7 8c/16t, RAM 16GB, CPU-only. **Win11 + WSL2 Ubuntu 22.04 mirrored networking** (bắt buộc để thu dữ liệu thật). Python 3.8–3.12.

## 3. Cài đặt từ 0
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch==2.3.0 scikit-learn numpy pandas matplotlib
# Công cụ thu/tấn công: snort, CICFlowMeter, nmap, hydra, slowhttptest, hping3 (xem ../HUONG_DAN_CAI_DAT.md)
```

## 4. Tải/thu dữ liệu
Đây là GĐ **tự thu dữ liệu thật** — xem chi tiết [HUONG_DAN_THU_DU_LIEU.md](HUONG_DAN_THU_DU_LIEU.md). Có thể bổ sung CIC để map nhãn (xem `data/README.md`).

## 5. Chạy/huấn luyện
- **Thu dữ liệu:** `data_collection/auto_attack*.py`, `auto_benign*.py`, `dataset_builder*.py`, `background_traffic_generator.py`, `hulk/` (DoS).
- **Chẩn đoán shift:** `retrain/src/check_distribution_drift.py`, `retrain/src/5b_visualize_embeddings_tsne.py`.
- **Retrain V8.5:**
```bash
python retrain/v8/v8.5_Combined/build_dataset_v8_5.py     # dựng Combined_V8_5
bash   retrain/v8/v8.5_Combined/run_train_v8_5.sh          # train V8.5
```
- **Domain adaptation (chẩn đoán):** `retrain/domain_adaptation/` (refit scaler, finetune freeze...).

## 6. Kết quả mong đợi
V8.5 Macro F1 **91,7%** trên val đa miền (đáng tin hơn 97% của bản đồng nhất miền). Báo cáo: `retrain/v8/v8.5_Combined/ket_qua_v8_5.md`, figures trong `results/`. Ngưỡng tối ưu: `results/optimal_threshold.json`.

## 7. Troubleshooting
- **PortScan không tách được trong WSL2**: do NAT đổi phân phối đặc trưng flow — giải bằng dữ liệu surrogate (data portscan thu trên Win11 host) + luật hậu xử lý (xem GĐ5).
- CICFlowMeter không ra cổng đích đúng: kiểm tra mirrored networking.
- Trọng số V8.5 đã kèm ở [../05_Replay_Detection/models/](../05_Replay_Detection/models/) — không cần train lại nếu chỉ demo.
