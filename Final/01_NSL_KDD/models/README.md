# GĐ1 — Trọng số NSL-KDD (kèm sẵn để TÁI HIỆN SỐ LIỆU)

> NSL-KDD là **giai đoạn nền tảng** của đồ án — giá trị là **số liệu** (xác lập kiến trúc Two-Stage + giới hạn trên của dataset 1998), KHÔNG phải hệ thống triển khai. Hệ thống End-to-End thật của đồ án là **V8.5** (xem GĐ4/GĐ5).

Trọng số kèm theo để chạy lại đánh giá và đối chiếu số liệu:
```
best_model.pt            # FT-Transformer 122-feature (4 lớp: DoS/Probe/R2L/U2R)
autoencoder_v2_best.h5   # Autoencoder Gate (Stage 1)
scaler.pkl               # MinMaxScaler
feature_columns.json     # 122 feature
inference_config.json    # model_kwargs + class_names + ngưỡng
dataset_profile.json · train_stats.json · test_stats.json
```

Code nạp/đánh giá (tham khảo): `../src/inference_product/` (loader gốc) + `../src/training/evaluate_class_aware_gate.py`.

## Số liệu mong đợi (đối chiếu Chương 5 đồ án)
| Chỉ số | Giá trị |
|---|---|
| Macro F1 (đầu-cuối, KDDTest+, 5 lớp) | **0,6809** |
| Accuracy | 80,09% |
| Per-class F1 | Normal 0,823 · Probe 0,794 · U2R 0,512 |

> Lưu ý: các script trong `inference_product/` giả định layout sản phẩm cũ (`PROJECT_ROOT = parents[2]`). Để chạy lại có thể cần chỉnh đường dẫn model về thư mục này — nhưng số liệu đã có sẵn trong báo cáo + `../results/`.
