# Ke hoach tinh chinh model huong toi >90% (Linux + Python + Snort)

## 1) Muc tieu

- Benchmark NSL-KDD 5 lop: Accuracy >= 90%.
- Chi so kem theo: Macro-F1 >= 0.65, R2L F1 >= 0.45, U2R F1 >= 0.30.
- Mo hinh phai giu duoc kha nang dua vao pipeline Linux + Snort + Python sau nay.

## 2) Hien trang can uu tien

- Pipeline v2 da sua loi lech cot, label map va scaler leakage.
- Muc benchmark hien tai van quanh 75-79%, nen can tinh chinh co he thong, khong chi doi tham so.
- Diem yeu nhat van la lop hiem R2L/U2R va cach xu ly mat can bang.

## 3) Viec can lam truoc

1. Khoa schema du lieu train/test/inference.
- Luu thu tu feature cu the, test/inference phai align dung schema train.
- Bat buoc kiem tra so cot, label map, va scaler da fit tren train.

2. Cung co target label.
- Dam bao map day du Normal, DoS, Probe, R2L, U2R.
- Log so mau truoc/sau map de tranh mat du lieu ngau nhien.

3. On dinh preprocessing.
- Chi fit scaler tren train.
- Luu preprocessing artifact de tai su dung khi train lai va inference.

## 4) Ke hoach tinh chinh Transformer

Uu tien thu tu:

1. Loss.
- CE + class weight.
- Focal Loss.
- Class-balanced focal loss neu R2L/U2R van thap.

2. Sampling.
- WeightedRandomSampler hoac batch-balanced sampling.

3. Optimizer va scheduler.
- AdamW.
- Warmup ngan + cosine decay.

4. Regularization.
- Dropout 0.1 / 0.2 / 0.3.
- Label smoothing 0.05 - 0.1.
- Weight decay 1e-4 den 1e-3.

5. Kien truc.
- Thu d_model 128 / 192 / 256.
- Thu 4 / 6 / 8 layers.
- Thu 4 / 8 heads.

6. Calibration.
- Temperature scaling.
- Threshold rieng cho lop hiem, dac biet R2L va U2R.

## 5) Lo trinh thuc thi

### Buoc 1: Chot pipeline du lieu
- Tao bo v2 va chay sanity check.
- Xac nhan khong con mismatch cot, khong con scaler leakage, khong con label bi drop.

### Buoc 2: Chay baseline Transformer tren v2
- Danh gia lai tren full data da chuan hoa.
- Luu ro Accuracy, Macro-F1, per-class F1.

### Buoc 3: Tuning co kiem soat
- Thu lan luot Loss -> Sampler -> Optimizer/Scheduler -> Regularization -> Architecture.
- Moi lan chi doi 1 nhom tham so de biet cai nao co tac dong thuc.

### Buoc 4: Neu van chua dat 90%
- Thu mo hinh 2 tang: Autoencoder binary detector -> Transformer phan loai attack.
- Chi ap dung neu benchmark 1 tang khong vuot duoc nguong ro rang.

### Buoc 5: Danh gia va chot model
- Chay 3-5 random seeds.
- Bao cao mean/std cho Accuracy va Macro-F1.
- Chon model on dinh, khong chi chon run cao nhat.

## 6) Tieu chi thanh cong

- Accuracy >= 90% tren test v2.
- Macro-F1 >= 0.65.
- R2L/U2R cai thien ro rang so voi baseline hien tai.
- Pipeline co the noi sang Snort-based real-time stack sau nay.

## 7) Thu tu uu tien ngan gon

1. Sua preprocessing va schema.
2. Chay baseline Transformer tren v2.
3. Tuning loss, sampler, threshold.
4. Neu chua dat, thu 2 tang.
5. Chay da seed va chot phien ban tot nhat.
