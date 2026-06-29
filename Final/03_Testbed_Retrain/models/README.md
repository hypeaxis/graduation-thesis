# GĐ3 — Trọng số V8.5

Trọng số V8.5 (FT-Transformer 80-feature, 5 lớp) **đã ship sẵn** ở GĐ5:
```
../05_Replay_Detection/models/
├── v8_5_model.pt
├── v8_5_scaler.pkl
└── v8_5_encoder.pkl
```

Các phiên bản trung gian (v8.1–v8.4) train lại được bằng script trong `../retrain/v8/`. Trọng số `.pt` của chúng không kèm gói.

**Kết quả V8.5:** Macro F1 91,7% (val đa miền). Chi tiết: `../retrain/v8/v8.5_Combined/ket_qua_v8_5.md`.
