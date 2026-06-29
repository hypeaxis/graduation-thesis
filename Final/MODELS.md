# MODELS — Kiểm kê trọng số

| Mô hình | GĐ | File trong gói | Trạng thái | Ghi chú |
|---|---|---|---|---|
| **V8.5 80-feat (hệ thống THẬT)** | 3/5 | `05_Replay_Detection/models/{v8_5_model.pt,v8_5_scaler.pkl,v8_5_encoder.pkl}` | ✅ **Ship sẵn** (~4,4MB) | **Demo replay chạy ngay**, 5 lớp |
| NSL-KDD FT-Transformer 122-feat | 1 | `01_NSL_KDD/models/best_model.pt` (~10MB) | ✅ Ship sẵn | Chỉ để **tái hiện số liệu** nền tảng (F1 0,681), KHÔNG phải hệ thống triển khai |
| NSL-KDD Autoencoder Gate | 1 | `01_NSL_KDD/models/autoencoder_v2_best.h5` | ✅ Ship sẵn | Cần TensorFlow |
| NSL-KDD scaler + config | 1 | `01_NSL_KDD/models/{scaler.pkl,feature_columns.json,inference_config.json}` | ✅ Ship sẵn | 122 feature, 4 lớp |
| CIC cascade — Gating/Expert (FTT) | 2 | — | ❌ Phải train | Xem `02_CIC_IDS_2017/HUONG_DAN_CHAY.md` |
| CIC cascade — RF stage2 | 2 | — | ❌ Phải train (RF ~8MB) | `models/README.md` |
| CIC cascade — KNN stage2 | 2 | — | ❌ Phải train (KNN ~24MB, quá nặng) | `models/README.md` |

## Quy ước

- **Ship sẵn** = đã có trong gói, demo chạy out-of-box (chỉ cần cài deps).
- **Phải train** = không kèm để giữ dung lượng nhỏ; chạy script train trong GĐ tương ứng để tái tạo. Kết quả mong đợi ghi trong `HUONG_DAN_CHAY.md` + `models/README.md` của GĐ đó.

## Kiểm tra nhanh trọng số demo

```bash
python3 - <<'PY'
import torch
for p in ["01_NSL_KDD/models/best_model.pt",
          "05_Replay_Detection/models/v8_5_model.pt"]:
    ck = torch.load(p, map_location="cpu")
    print(p, "→ OK", type(ck).__name__)
PY
```
