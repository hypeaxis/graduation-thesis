# Bao cao tien do theo ke hoach xay dung san pham

Cap nhat ngay: 2026-04-21

## 1) Tong quan

Tai thoi diem hien tai, cac hang muc da hoan thanh tap trung vao Giai doan 1 (Data Pipeline voi Snort), bao gom:
- Tao cau truc thu muc final de chua cau hinh va artifact chay that.
- Cai dat Snort thanh cong tren Linux.
- Cau hinh Snort de xuat log CSV co cau truc.
- Viet script tien xu ly log Snort thanh vector 122 dac trung theo schema model hien tai.
- Hoan tat sua moi truong .venv de chay duoc pandas/scikit-learn va script preprocessing.

## 2) Doi chieu theo ke hoach

## Giai doan 1: Xay dung Data Pipeline voi Snort

### 2.1 Thiet lap moi truong nen tang
- Trang thai: Da hoan thanh phan can thiet cho buoc hien tai.
- Da thuc hien:
  - Moi truong Linux/WSL dang duoc su dung de van hanh Snort + Python.
  - Da tao thu muc lam viec final tai:
    - /home/ning/Graduation-Thesis/final
  - Da sua dut diem .venv (tao lai environment, khoi phuc pip, cai package can thiet).

### 2.2 Trien khai va cau hinh Snort
- Trang thai: Da hoan thanh.
- Da thuc hien:
  - Cai Snort qua apt tren he thong.
  - Tao cau hinh toi thieu cho Snort tai:
    - /home/ning/Graduation-Thesis/final/snort.conf
  - Cau hinh output dang CSV (alert_csv) de parser de doc.
  - Kiem tra cau hinh thanh cong bang Snort test mode (-T).

### 2.3 Feature Extraction (log Snort -> 122 features)
- Trang thai: Da hoan thanh ban dau (MVP cho inference).
- Da thuc hien:
  - Viet script preprocessing tai:
    - /home/ning/Graduation-Thesis/final/snort_preprocess_122.py
  - Script doc log Snort CSV (cac truong: timestamp, msg, proto, src/dst, port, ...).
  - Trich xuat va suy dien cac nhom feature co the tinh tu Snort log:
    - protocol_type
    - service
    - flag
    - cac thong ke cua cua so 2 giay: count, srv_count, same_srv_rate, diff_srv_rate, srv_diff_host_rate
    - cac thong ke host-based tren 100 ket noi gan nhat: dst_host_count, dst_host_srv_count, ...
  - Dong bo thu tu cot theo schema model tu:
    - /home/ning/Graduation-Thesis/MLAnomalyDetection/artifacts_preprocess/feature_columns.json
  - Tu dong scale theo scaler huan luyen neu co:
    - /home/ning/Graduation-Thesis/MLAnomalyDetection/artifacts_preprocess/scaler.pkl
  - Output du lieu model-ready tai:
    - /home/ning/Graduation-Thesis/final/snort_features_122.csv
  - Da xac minh output co kich thuoc 122 cot (shape mau: (2, 122)).

### 2.4 Tep ho tro trong final
- /home/ning/Graduation-Thesis/final/snort.conf
- /home/ning/Graduation-Thesis/final/rules/local.rules
- /home/ning/Graduation-Thesis/final/log/alert.csv (mau thu nghiem)
- /home/ning/Graduation-Thesis/final/snort_preprocess_122.py
- /home/ning/Graduation-Thesis/final/snort_features_122.csv

## Giai doan 2: Toi uu do chinh xac va trien khai AI
- Trang thai: Chua trien khai trong dot nay.
- Chua lam:
  - Fine-tuning Autoencoder/Transformer.
  - Chuyen doi ONNX.
  - Tao FastAPI model service.
  - Toi uu latency cho production.

## Giai doan 3: Backend va Dashboard
- Trang thai: Chua trien khai trong dot nay.
- Chua lam:
  - Backend Node.js trung tam.
  - Socket.io/WebSocket realtime.
  - Dashboard giam sat va canh bao.

## Giai doan 4: Tich hop he thong va gia lap tan cong
- Trang thai: Chua trien khai trong dot nay.
- Chua lam:
  - Noi full luong Snort -> Preprocess -> Model API -> Backend -> Dashboard.
  - Gia lap tan cong bang nmap/hping3/Metasploit.
  - Danh gia thuc chien E2E.

## Giai doan 5: Bao cao va chuan bi bao ve
- Trang thai: Chua trien khai trong dot nay.
- Chua lam:
  - Hoan thien bao cao hoc thuat.
  - Chuan bi kich ban demo va video backup.

## 3) Ket luan tien do hien tai

- Muc tieu cot loi cua Giai doan 1 da dat duoc o muc chay duoc:
  - Snort da cai dat va cau hinh xuat log co cau truc.
  - Da co script tien xu ly bien doi log Snort thanh vector 122 cot dung schema model.
  - Moi truong .venv da on dinh de chay pipeline preprocessing.
- Cac giai doan 2-5 chua duoc trien khai trong pham vi cong viec hien tai.
