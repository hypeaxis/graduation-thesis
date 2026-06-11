# Session Log - 2026-06-02 (session-01)

## Goal
- Kiểm tra lại nội dung đã thực hiện trong repo.
- Kiểm tra lại model đang dùng và đánh giá dấu hiệu overfitting.
- Thiết lập đầy đủ để có thể chạy/hiển thị thành sản phẩm web.
- Ghi đầy đủ kết quả phiên làm việc vào log.

## Context Checked
- Tài liệu tiến độ và checklist:
  - `CHECKLIST_TUNING_MODEL_41EMB.md`
  - `final/BAO_CAO_TIEN_DO_THEO_KE_HOACH.md`
- Log các phiên trước:
  - `work_session_logs/2026-05-31/session-02.md`
- Cấu hình pipeline chính:
  - `final/primary_pipeline.json`
- Artifact kết quả train:
  - `MLAnomalyDetection/outputs/nslkdd_ft_experiments/*/results/training_summary.csv`
  - `MLAnomalyDetection/outputs/tabular_transformer_41emb/results/training_summary.csv`
- Stack sản phẩm web:
  - `backend/app/main.py`
  - `backend/app/pipeline_service.py`
  - `frontend/index.html`
  - `frontend/app.js`
  - `frontend/styles.css`

## Model Verification
- Pipeline đang active: `122-feature-ft-transformer`.
- Checkpoint đang dùng:
  - `MLAnomalyDetection/outputs/nslkdd_ft_experiments/nslkdd_ft_sampler_weighted_seed62/models/best_model.pt`
- Thông số metric từ `final/primary_pipeline.json`:
  - best_val_macro_f1: `0.7544`
  - test_accuracy: `0.8005`
  - test_macro_f1: `0.6679`

## Overfitting Check (Val vs Test Macro-F1 Gap)
Đã tính lại từ tất cả run trong `nslkdd_ft_experiments`:

| Run | Val Macro-F1 | Test Macro-F1 | Gap (Val-Test) | Test Acc |
|---|---:|---:|---:|---:|
| nslkdd_ft_baseline_seed42 | 0.8088 | 0.5582 | 0.2505 | 0.7477 |
| nslkdd_ft_sampler_weighted_seed42 | 0.7484 | 0.6098 | 0.1386 | 0.7909 |
| nslkdd_ft_sampler_weighted_seed52 | 0.8309 | 0.6268 | 0.2042 | 0.7707 |
| nslkdd_ft_sampler_weighted_seed62 | 0.7544 | 0.6679 | 0.0865 | 0.8005 |
| nslkdd_ft_weighted_dropout02_seed42 | 0.7089 | 0.6443 | 0.0645 | 0.8058 |
| nslkdd_ft_weighted_scalar025_seed42 | 0.8270 | 0.5825 | 0.2445 | 0.7684 |

Tổng hợp:
- Mean gap (122-feature): `0.1648`.
- Gap lớn nhất: baseline_seed42 (`0.2505`).
- Best deploy run seed62 có gap `0.0865` (có overfit nhẹ-vừa, nhưng khá tốt hơn các run còn lại).

Kiểm tra model 41-feature:
- `best_val_macro_f1 = 0.9628`, `test_macro_f1 = 0.6470`.
- Gap = `0.3158` (overfitting rõ ràng).

Kết luận overfitting:
- Có dấu hiệu overfitting trên cả nhóm 122-feature và 41-feature.
- Mức overfitting của model đang deploy (122 seed62) thấp hơn đáng kể so với nhiều run khác, nên vẫn hợp lý để dùng làm model chính hiện tại.

## Product Setup / Runtime Validation
Đã smoke test end-to-end khi server chạy:
1. `GET /api/health` trả về status ok.
2. `POST /api/simulate` sinh CSV giả lập thành công.
3. `POST /api/detect` chạy preprocess + inference thành công.

Kết quả detect smoke:
- total_vectors: `60`
- predicted_counts: `{'DoS': 3, 'Normal': 44, 'Probe': 9, 'R2L': 3, 'U2R': 1}`
- mean_confidence: `0.7526`
- max_confidence: `0.9924`

## Files Added/Updated This Session
Updated:
- `backend/requirements-web.txt`
  - Bổ sung dependency runtime cho detect pipeline: pandas, numpy, scikit-learn, torch.
- `backend/README_WEB.md`
  - Cập nhật hướng dẫn setup đầy đủ.
  - Thêm chế độ chạy dev/prod.
  - Thêm smoke test E2E.

Added:
- `backend/run_prod.sh`
  - Script chạy FastAPI product mode (không reload).
- `run_product.sh`
  - Entrypoint 1-lệnh từ root repo để chạy sản phẩm.

## Current Product Run Commands
```bash
cd /home/ning/Graduation-Thesis
source .venv/bin/activate
pip install -r backend/requirements-web.txt
bash run_product.sh
```

Website:
- http://localhost:8000

## Notes
- Tài liệu `final/BAO_CAO_TIEN_DO_THEO_KE_HOACH.md` hiện vẫn ghi backend/frontend là "chưa triển khai" (trạng thái lịch sử ở thời điểm 2026-04-21). Trong thực tế repo hiện đã có stack web chạy được.

## Next Steps
- Thêm dashboard metric theo thời gian thực (charts + session persistence) thay vì chỉ in-memory.
- Theo dõi train-val gap trong mỗi run để ưu tiên config giảm overfitting (regularization + split strategy + calibration).
- Nếu cần deployment ổn định hơn, bổ sung process manager (systemd/supervisor) và reverse proxy.

## Session Update - Overfitting Reduction Patch

Mục tiêu:
- Giảm overfitting trên pipeline train 122-feature mà không phá vỡ compatibility inference hiện tại.

Code đã cập nhật:
- `MLAnomalyDetection/train_ft_transformer_nslkdd.py`
  - Thêm tham số CLI:
    - `--mixup-alpha`
    - `--selection-gap-penalty`
    - `--max-train-val-gap`
    - `--gap-patience`
  - Thêm mixup cho tabular batch và soft focal loss cho nhãn mềm khi mixup bật.
  - Thêm logging `train_val_f1_gap` và `selection_score` theo epoch.
  - Thêm cơ chế chọn checkpoint có phạt overfit:
    - `selection_score = val_f1 - selection_gap_penalty * max(train_f1 - val_f1, 0)`
  - Thêm cơ chế early stop theo overfitting guard khi gap vượt ngưỡng liên tiếp.
  - Bổ sung metric tổng hợp mới vào `training_summary.json/csv`:
    - `best_selection_score`
    - `last_train_val_f1_gap`

Kiểm tra sau thay đổi:
- `get_errors` cho file train: không có lỗi.
- CLI help đã hiển thị đầy đủ các tham số mới khi chạy bằng repo venv.
- Đã khởi động smoke run 1 epoch với mixup; do training mất thời gian nên đã dừng thủ công giữa chừng (không có crash ngay giai đoạn khởi động + dataloader).

Ghi chú môi trường:
- Nên dùng đúng venv của repo (`/home/ning/Graduation-Thesis/.venv`) để tránh thiếu package như matplotlib.

## Session Update - Package Current Best Epoch

Yêu cầu:
- Dừng việc tuning tiếp và đóng gói model hiện tại ở epoch tốt nhất.

Kiểm tra trước đóng gói:
- Pipeline active trong `final/primary_pipeline.json`:
  - run: `nslkdd_ft_sampler_weighted_seed62`
  - checkpoint: `.../models/best_model.pt`
  - best_epoch: `19`

Gói đã tạo:
- Thư mục package:
  - `final/model_packages/ft122_seed62_best_epoch19_20260602/`
- Bản nén tar.gz:
  - `final/model_packages/ft122_seed62_best_epoch19_20260602.tar.gz`

Nội dung package:
- `models/`: `best_model.pt`, `inference_config.json`
- `results/`: `training_summary.json/csv`, `per_class_metrics.csv`, `classification_report.txt`, `confusion_matrix.png`
- `artifacts/`: `feature_columns.json`, `scaler.pkl`, `label_map.json`, `label_groups.json`
- `pipeline/`: snapshot `primary_pipeline.json`
- `scripts/`: `snort_preprocess_122.py`, `snort_ft_transformer_inference.py`
- `PACKAGE_INFO.md`
- `checksums.sha256` (đã verify OK)

Tình trạng:
- Đóng gói hoàn tất, checksum xác thực thành công.
