# GĐ1 — NSL-KDD (mô hình nền tảng): HƯỚNG DẪN CHẠY

## 1. Mục tiêu & sơ đồ luồng
Thiết lập kiến trúc nền: **Autoencoder Gate → Stacking Ensemble** (FT-Transformer 122-feat + LightGBM + Meta-LR) trên NSL-KDD, xác lập giới hạn trên của bộ dữ liệu 1998.
```
KDDTrain+ → preprocess 122-feat → AE Gate (Normal vs Attack) → Stacking (FTT + LightGBM → Meta-LR) → 5 lớp
```

## 2. Cấu hình máy
CPU-only, RAM ≥ 8GB. Python 3.8–3.12. (Xem [../HUONG_DAN_CAI_DAT.md](../HUONG_DAN_CAI_DAT.md).)

## 3. Cài đặt từ 0
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch==2.3.0 tensorflow==2.13.1 lightgbm scikit-learn numpy pandas
```

## 4. Tải dữ liệu thô + link
NSL-KDD: https://www.unb.ca/cic/datasets/nsl.html (mirror: https://www.kaggle.com/datasets/hassan06/nslkdd).
Đặt `KDDTrain+.txt`, `KDDTest+.txt` vào `data/` (xem [data/README.md](data/README.md)).

## 5. Chạy/huấn luyện
Thứ tự script trong `src/`:
```bash
python src/data_processing/preprocessing_pipeline.py      # tiền xử lý 122 feature
python src/data_processing/generate_ae_features.py        # đặc trưng AE Gate
python src/training/train_ft_transformer_nslkdd.py        # FT-Transformer
python src/training/train_lightgbm_ensemble.py            # LightGBM
python src/training/stacking_ensemble.py                  # Meta-LR stacking
```
Thời gian: vài chục phút (CPU). Output: trọng số + report trong thư mục `outputs/` do script tạo.

## 6. Kết quả mong đợi
Macro F1 ≈ **0,681** (đối chiếu Chương 5), Acc 80,09%, per-class Normal 0,823 / Probe 0,794 / U2R 0,512. Giới hạn bởi protocol shift R2L — không vượt được bằng thuật toán.

> Trọng số 122-feat **đã kèm sẵn** trong `models/` để tái hiện/đối chiếu số liệu (xem [models/README.md](models/README.md)). NSL-KDD là giai đoạn **nền tảng**, không phải hệ thống triển khai — hệ thống thật là V8.5 (GĐ4/GĐ5).

## 7. Troubleshooting
- LightGBM lỗi OpenMP: `sudo apt install libgomp1`.
- TensorFlow nặng: chỉ cần cho AE Gate; phần FTT/LightGBM chạy độc lập được.
- Thiếu RAM khi SMOTE: giảm batch hoặc dùng máy ≥16GB.
