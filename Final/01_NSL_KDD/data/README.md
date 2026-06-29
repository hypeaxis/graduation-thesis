# GĐ1 — Dữ liệu NSL-KDD (KHÔNG kèm trong gói)

Tải và đặt vào thư mục này:

| File | Nguồn |
|---|---|
| `KDDTrain+.txt` | https://www.unb.ca/cic/datasets/nsl.html |
| `KDDTest+.txt` | (mirror Kaggle: https://www.kaggle.com/datasets/hassan06/nslkdd) |

Cấu trúc mong đợi:
```
01_NSL_KDD/data/
├── KDDTrain+.txt
└── KDDTest+.txt
```
Sau đó chạy `src/data_processing/preprocessing_pipeline.py` để sinh đặc trưng 122-feature.
