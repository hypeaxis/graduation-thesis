# GĐ2 — Trọng số CIC cascade (PHẢI TRAIN LẠI — không kèm gói)

Để giữ dung lượng nhỏ, trọng số cascade **không** đi kèm. Cấu trúc mong đợi sau khi train:

```
02_CIC_IDS_2017/models/
├── stage1_gating/        # FT-Transformer Gating (Benign vs Attack)
├── stage2/
│   ├── best_rf_model.pkl     # Random Forest (~8MB)
│   └── best_knn_model.pkl    # KNN (~24MB — nặng)
└── final_cic_ids_2017/   # ensemble + config
```

Train: chạy script trong `../src/training/` theo thứ tự ở [../HUONG_DAN_CHAY.md](../HUONG_DAN_CHAY.md).

**Kết quả đã đạt:** Accuracy 99,55%, Macro F1 0,9294 (9 lớp). Report đối chiếu trong `../results/`.
