# Checklist Tuning Model 41-Feature

Tai lieu nay dung de theo doi qua trinh tinh chinh model chinh hien tai cua do an: Tabular Transformer 41-feature.

## 1. Muc tieu tuning

- [x] Chot model chinh la pipeline 41-feature.
- [x] Giu tuong thich voi pipeline inference hien tai.
- [ ] Cai thien Macro-F1.
- [ ] Cai thien F1 cho R2L.
- [ ] Cai thien F1 cho U2R.
- [ ] Giu Accuracy o muc on dinh, khong doi Macro-F1 lay Accuracy.
- [ ] Dam bao ket qua on dinh qua nhieu seed.

## 2. Khoa baseline

- [x] Xac nhan pipeline chinh trong `final/primary_pipeline.json`.
- [x] Giu nguyen schema 41-feature: 38 numeric + 3 categorical.
- [x] Giu nguyen artifact preprocessing trong `MLAnomalyDetection/artifacts_preprocess_41emb/`.
- [x] Ghi lai ket qua baseline hien tai:
  - [x] Accuracy: `0.8017922100967083`
  - [x] Macro-F1: `0.6632157296354305`
  - [x] Weighted-F1: `0.7894882161472069`
  - [x] Macro-precision: `0.7354037043874042`
  - [x] Macro-recall: `0.6649466662717282`
  - [x] F1 tung lop: Normal `0.8071395881006864`, DoS `0.9192783869826671`, Probe `0.7217663149667839`, R2L `0.4602510460251046`, U2R `0.40764331210191085`
- [x] Luu confusion matrix va classification report cua baseline.

## 3. On dinh quy trinh danh gia

- [x] Chay lai baseline voi it nhat 3 seed.
- [x] Ghi lai mean/std cho Accuracy: mean `0.7717`, std `0.0200`.
- [x] Ghi lai mean/std cho Macro-F1: mean `0.6313`, std `0.0136`.
- [x] Ghi lai mean/std cho R2L F1: mean `0.3334`, std `0.0051`.
- [x] Ghi lai mean/std cho U2R F1: mean `0.4558`, std `0.0456`.
- [x] Danh gia xem model co on dinh truoc khi tuning sau hay khong: Val Macro-F1 kha on dinh (mean `0.9681`, std `0.0047`) nhung test Macro-F1/Accuracy giam so voi baseline `40/8`, vi vay tam thoi chua dung cau hinh `20/4` lam baseline moi.

## 4. Tuning imbalance

### 4.1 Loss

- [x] Chay baseline voi Focal Loss hien tai.
- [ ] Thu dieu chinh alpha cho R2L/U2R.
- [ ] Thu class-balanced focal loss neu can.
- [ ] So sanh ket qua voi baseline.

### 4.2 Sampler

- [ ] Thu WeightedRandomSampler.
- [ ] Thu batch-balanced sampling neu can.
- [ ] So sanh cac truong hop:
  - [ ] Chi doi loss
  - [ ] Chi doi sampler
  - [ ] Doi ca loss va sampler

## 5. Tuning threshold va calibration

- [ ] Luu xac suat du doan tren validation set.
- [ ] Thu temperature scaling.
- [ ] Thu threshold rieng cho R2L.
- [ ] Thu threshold rieng cho U2R.
- [ ] Kiem tra confusion matrix sau calibration.
- [ ] Danh gia false positive co tang qua nhieu hay khong.

## 6. Tuning optimizer va scheduler

- [ ] Thu learning rate `1e-4`.
- [ ] Thu learning rate `3e-4`.
- [ ] Thu learning rate `5e-5`.
- [ ] Thu weight decay `1e-4`.
- [ ] Thu weight decay `5e-4`.
- [ ] Thu weight decay `1e-3`.
- [ ] Thu scheduler phuc tap hon neu can, vi du warmup + cosine decay.
- [ ] So sanh tren cung seed hoac cung bo seed.

## 7. Tuning regularization

- [ ] Thu dropout `0.1`.
- [ ] Thu dropout `0.2`.
- [ ] Thu dropout `0.3`.
- [ ] Thu label smoothing `0.05` neu can.
- [ ] Thu label smoothing `0.1` neu can.
- [ ] Kiem tra khoang cach train/val de phat hien overfitting.

## 8. Tuning kien truc

- [ ] Chi tuning kien truc sau khi da thu loss, sampler va threshold.
- [ ] Thu `d_model = 128`.
- [ ] Thu `d_model = 192`.
- [ ] Thu `d_model = 256`.
- [ ] Thu `num_layers = 4`.
- [ ] Thu `num_layers = 6`.
- [ ] Thu `num_heads = 4`.
- [ ] Thu `num_heads = 8`.
- [ ] Khong doi qua nhieu tham so cung luc.

## 9. Nguyen tac chay thi nghiem

- [ ] Moi lan chi doi 1 nhom yeu to.
- [ ] Dat ten run ro rang.
- [ ] Luu cau hinh cua tung run.
- [ ] Luu metric cua tung run.
- [ ] Luu file ket qua cho top run.
- [ ] Luu confusion matrix cho top run.
- [ ] Luu classification report cho top run.

## 10. Bang theo doi run

| Run ID | Thay doi | Seed | Val Macro-F1 | Test Accuracy | Test Macro-F1 | R2L F1 | U2R F1 | Ghi chu |
|--------|----------|------|--------------|---------------|---------------|--------|--------|--------|
| baseline_seed42 | Baseline `20e_p4` | 42 | 0.9628 | 0.7943 | 0.6470 | 0.3317 | 0.4511 | Early stop epoch 12, best epoch 8 |
| baseline_seed52 | Baseline `20e_p4` | 52 | 0.9700 | 0.7562 | 0.6240 | 0.3294 | 0.5035 | Early stop epoch 14, best epoch 10 |
| baseline_seed62 | Baseline `20e_p4` | 62 | 0.9716 | 0.7645 | 0.6229 | 0.3392 | 0.4127 | Chay du 20 epoch, best epoch 17 |

## 11. Tieu chi chot model cuoi

- [ ] Khong chon model chi theo Accuracy.
- [ ] Uu tien Macro-F1 truoc.
- [ ] Uu tien cai thien R2L F1.
- [ ] Uu tien cai thien U2R F1.
- [ ] Kiem tra do on dinh qua nhieu seed.
- [x] Dam bao tuong thich voi `final/snort_tabular_transformer_41emb_inference.py`.

## 12. Viec chua uu tien o giai doan nay

- [ ] Chua quay lai nhanh 122-feature lam model chinh.
- [ ] Chua dua Autoencoder hai tang vao luong chinh.
- [ ] Chua uu tien ONNX.
- [ ] Chua uu tien FastAPI/backend/frontend.
- [ ] Chua uu tien benchmark latency sau.
- [ ] Chua mo rong sang CIC-IDS khi model hien tai chua chot.

## 13. Thu tu thuc hien de xuat

- [x] Buoc 1: Re-run baseline voi nhieu seed.
- [ ] Buoc 2: Tune loss.
- [ ] Buoc 3: Tune sampler.
- [ ] Buoc 4: Tune threshold va calibration.
- [ ] Buoc 5: Tune optimizer va scheduler.
- [ ] Buoc 6: Tune regularization.
- [ ] Buoc 7: Tune kien truc.
- [ ] Buoc 8: Chay lai top cau hinh voi nhieu seed.
- [ ] Buoc 9: Chot model cuoi cung.
