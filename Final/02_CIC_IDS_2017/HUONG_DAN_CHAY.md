# GĐ2 — CIC-IDS-2017 (Two-Stage Cascade): HƯỚNG DẪN CHẠY

## 1. Mục tiêu & sơ đồ luồng
Phát triển **Two-Stage Cascade + Asymmetric Ensemble Voting** cho 9 lớp (gộp từ 15 nhãn gốc), với Hard Negative Mining (HNM).
```
Flow → Stage1 Gating (Benign vs Attack) → Stage2 Expert (FTT) + RF + KNN → Asymmetric Voting → 9 lớp
```

## 2. Cấu hình máy
CPU-only, RAM ≥ 16GB khuyến nghị (KNN/RF + dữ liệu lớn). Python 3.8–3.12.

## 3. Cài đặt từ 0
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install torch==2.3.0 scikit-learn lightgbm numpy pandas matplotlib jupyter
```

## 4. Tải dữ liệu thô + link
CIC-IDS-2017 (MachineLearningCSV): https://www.unb.ca/cic/datasets/ids-2017.html
Đặt các CSV vào `data/` (xem [data/README.md](data/README.md)).

## 5. Chạy/huấn luyện
- Tham khảo `notebooks/Intrusion-Detection-CIC-IDS2017.ipynb` (đã xoá output) cho EDA + pipeline.
- Thứ tự chạy hệ thống cuối (V7 = bản đạt 99,55% / 0,9294):
```bash
# Đặt CIC MachineLearningCSV vào data/raw/ (hoặc đặt env CIC_RAW_DIR), rồi:
python src/data_processing/cic_data_processor_v2.py                    # tiền xử lý → data/processed/
python src/archive/phase2_train_v4_stage1.py                          # Stage1 Gating (Benign vs Attack)
python src/training/scripts_v7/extract_hard_negatives_v7.py           # Hard Negative Mining (HNM)
python src/training/scripts_v7/phase2_train_v7_stage2_ensemble.py     # Stage2 Expert (FTT) + RF + KNN + Asymmetric Voting
python src/training/scripts_v7/evaluate_cascade_system_v7.py          # đánh giá → Accuracy/Macro F1
```
- Định nghĩa kiến trúc model: `src/models/phase2_ft_transformer_v2.py`. Các bản cũ (v5/v6) trong `src/archive/scripts_v5/`.
- ⚠️ Các script đọc đường dẫn dữ liệu qua biến môi trường `CIC_RAW_DIR` / `CIC_PROCESSED_DIR` (mặc định `data/raw`, `data/processed`); sửa nếu đặt dữ liệu nơi khác.

## 6. Kết quả mong đợi
Accuracy **99,55%**, Macro F1 **0,9294**. Đóng góp từng cải tiến: Two-Stage (+0,099), HNM (+0,036), Asymmetric Voting (+0,011). Report tham chiếu trong `results/`.

## 7. Troubleshooting
- KNN tốn RAM/đĩa (model ~24MB): cân nhắc giảm `n_neighbors` hoặc subsample.
- Notebook không có output: đúng — đã strip để giảm dung lượng; chạy lại để sinh kết quả.
- Trọng số cascade KHÔNG kèm gói — xem [models/README.md](models/README.md).
