# Session Log - 2026-06-02 (session-01)

## Goal
- Kiem tra lai noi dung da thuc hien trong repo.
- Kiem tra lai model dang dung va danh gia dau hieu overfitting.
- Thiet lap day du de co the chay/hiem thi thanh san pham web.
- Ghi day du ket qua phien lam viec vao log.

## Context Checked
- Tai lieu tien do va checklist:
  - `CHECKLIST_TUNING_MODEL_41EMB.md`
  - `final/BAO_CAO_TIEN_DO_THEO_KE_HOACH.md`
- Log cac phien truoc:
  - `work_session_logs/2026-05-31/session-02.md`
- Cau hinh pipeline chinh:
  - `final/primary_pipeline.json`
- Artifact ket qua train:
  - `MLAnomalyDetection/outputs/nslkdd_ft_experiments/*/results/training_summary.csv`
  - `MLAnomalyDetection/outputs/tabular_transformer_41emb/results/training_summary.csv`
- Stack san pham web:
  - `backend/app/main.py`
  - `backend/app/pipeline_service.py`
  - `frontend/index.html`
  - `frontend/app.js`
  - `frontend/styles.css`

## Model Verification
- Pipeline dang active: `122-feature-ft-transformer`.
- Checkpoint dang dung:
  - `MLAnomalyDetection/outputs/nslkdd_ft_experiments/nslkdd_ft_sampler_weighted_seed62/models/best_model.pt`
- Thong so metric tu `final/primary_pipeline.json`:
  - best_val_macro_f1: `0.7544`
  - test_accuracy: `0.8005`
  - test_macro_f1: `0.6679`

## Overfitting Check (Val vs Test Macro-F1 Gap)
Da tinh lai tu tat ca run trong `nslkdd_ft_experiments`:

| Run | Val Macro-F1 | Test Macro-F1 | Gap (Val-Test) | Test Acc |
|---|---:|---:|---:|---:|
| nslkdd_ft_baseline_seed42 | 0.8088 | 0.5582 | 0.2505 | 0.7477 |
| nslkdd_ft_sampler_weighted_seed42 | 0.7484 | 0.6098 | 0.1386 | 0.7909 |
| nslkdd_ft_sampler_weighted_seed52 | 0.8309 | 0.6268 | 0.2042 | 0.7707 |
| nslkdd_ft_sampler_weighted_seed62 | 0.7544 | 0.6679 | 0.0865 | 0.8005 |
| nslkdd_ft_weighted_dropout02_seed42 | 0.7089 | 0.6443 | 0.0645 | 0.8058 |
| nslkdd_ft_weighted_scalar025_seed42 | 0.8270 | 0.5825 | 0.2445 | 0.7684 |

Tong hop:
- Mean gap (122-feature): `0.1648`.
- Gap lon nhat: baseline_seed42 (`0.2505`).
- Best deploy run seed62 co gap `0.0865` (co overfit nhe-vua, nhung kha tot hon cac run con lai).

Kiem tra model 41-feature:
- `best_val_macro_f1 = 0.9628`, `test_macro_f1 = 0.6470`.
- Gap = `0.3158` (overfitting ro rang).

Ket luan overfitting:
- Co dau hieu overfitting tren ca nhom 122-feature va 41-feature.
- Muc overfitting cua model dang deploy (122 seed62) thap hon dang ke so voi nhieu run khac, nen van hop ly de dung lam model chinh hien tai.

## Product Setup / Runtime Validation
Da smoke test end-to-end khi server chay:
1. `GET /api/health` tra ve status ok.
2. `POST /api/simulate` sinh CSV gia lap thanh cong.
3. `POST /api/detect` chay preprocess + inference thanh cong.

Ket qua detect smoke:
- total_vectors: `60`
- predicted_counts: `{'DoS': 3, 'Normal': 44, 'Probe': 9, 'R2L': 3, 'U2R': 1}`
- mean_confidence: `0.7526`
- max_confidence: `0.9924`

## Files Added/Updated This Session
Updated:
- `backend/requirements-web.txt`
  - Bo sung dependency runtime cho detect pipeline: pandas, numpy, scikit-learn, torch.
- `backend/README_WEB.md`
  - Cap nhat huong dan setup day du.
  - Them che do chay dev/prod.
  - Them smoke test E2E.

Added:
- `backend/run_prod.sh`
  - Script chay FastAPI product mode (khong reload).
- `run_product.sh`
  - Entrypoint 1-lenh tu root repo de chay san pham.

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
- Tai lieu `final/BAO_CAO_TIEN_DO_THEO_KE_HOACH.md` hien van ghi backend/frontend la "chua trien khai" (trang thai lich su o thoi diem 2026-04-21). Trong thuc te repo hien da co stack web chay duoc.

## Next Steps
- Them dashboard metric theo thoi gian thuc (charts + session persistence) thay vi chi in-memory.
- Theo doi train-val gap trong moi run de uu tien config giam overfitting (regularization + split strategy + calibration).
- Neu can deployment on dinh hon, bo sung process manager (systemd/supervisor) va reverse proxy.

## Session Update - Overfitting Reduction Patch

Muc tieu:
- Giam overfitting tren pipeline train 122-feature ma khong pha vo compatibility inference hien tai.

Code da cap nhat:
- `MLAnomalyDetection/train_ft_transformer_nslkdd.py`
  - Them tham so CLI:
    - `--mixup-alpha`
    - `--selection-gap-penalty`
    - `--max-train-val-gap`
    - `--gap-patience`
  - Them mixup cho tabular batch va soft focal loss cho nhan mem khi mixup bat.
  - Them logging `train_val_f1_gap` va `selection_score` theo epoch.
  - Them co che chon checkpoint co phat overfit:
    - `selection_score = val_f1 - selection_gap_penalty * max(train_f1 - val_f1, 0)`
  - Them co che early stop theo overfitting guard khi gap vuot nguong lien tiep.
  - Bo sung metric tong hop moi vao `training_summary.json/csv`:
    - `best_selection_score`
    - `last_train_val_f1_gap`

Kiem tra sau thay doi:
- `get_errors` cho file train: khong co loi.
- CLI help da hien thi day du cac tham so moi khi chay bang repo venv.
- Da khoi dong smoke run 1 epoch voi mixup; do training mat thoi gian nen da dung thu cong giua chung (khong co crash ngay giai doan khoi dong + dataloader).

Ghi chu moi truong:
- Nen dung dung venv cua repo (`/home/ning/Graduation-Thesis/.venv`) de tranh thieu package nhu matplotlib.

## Session Update - Package Current Best Epoch

Yeu cau:
- Dung viec tuning tiep va dong goi model hien tai o epoch tot nhat.

Kiem tra truoc dong goi:
- Pipeline active trong `final/primary_pipeline.json`:
  - run: `nslkdd_ft_sampler_weighted_seed62`
  - checkpoint: `.../models/best_model.pt`
  - best_epoch: `19`

Goi da tao:
- Thu muc package:
  - `final/model_packages/ft122_seed62_best_epoch19_20260602/`
- Ban nen tar.gz:
  - `final/model_packages/ft122_seed62_best_epoch19_20260602.tar.gz`

Noi dung package:
- `models/`: `best_model.pt`, `inference_config.json`
- `results/`: `training_summary.json/csv`, `per_class_metrics.csv`, `classification_report.txt`, `confusion_matrix.png`
- `artifacts/`: `feature_columns.json`, `scaler.pkl`, `label_map.json`, `label_groups.json`
- `pipeline/`: snapshot `primary_pipeline.json`
- `scripts/`: `snort_preprocess_122.py`, `snort_ft_transformer_inference.py`
- `PACKAGE_INFO.md`
- `checksums.sha256` (da verify OK)

Tinh trang:
- Dong goi hoan tat, checksum xac thuc thanh cong.
