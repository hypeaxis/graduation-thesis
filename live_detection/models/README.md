# GĐ5 — Trọng số V8.5 (kèm sẵn)

```
v8_5_model.pt      # FT-Transformer 80-feature, 5 lớp
v8_5_scaler.pkl    # StandardScaler (sklearn)
v8_5_encoder.pkl   # LabelEncoder nhãn lớp
```

5 lớp: `PortScan, Brute Force, Web Attack, DoS, Benign`. Macro F1 ≈ 91,7% (val đa miền).

Đường dẫn được khai báo trong `../replay_config.json` (tương đối so với `live_detection/`, tức `models/...`). Không cần chỉnh nếu chạy `uvicorn server:app` từ thư mục `live_detection/`.

Train lại: xem `../../Final/03_Testbed_Retrain/HUONG_DAN_CHAY.md`.
