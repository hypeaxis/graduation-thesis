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

## 4) Noi dung co the dua vao bao cao GR2

Phan duoi day duoc viet theo dang van ban ky thuat, co the tai su dung va mo rong dan trong bao cao chinh.

### 4.1 Mo ta bai toan va muc tieu giai doan hien tai

Trong pham vi da hoan thanh den thoi diem hien tai, he thong duoc trien khai theo huong Snort-based, trong do Snort dam nhiem vai tro thu thap va ghi nhan su kien mang, con script Python dam nhiem vai tro chuyen doi du lieu log thanh vector dac trung co cau truc de phuc vu mo hinh hoc may. Muc tieu cua giai doan nay khong phai la toi uu hoa mo hinh AI ngay lap tuc, ma la xay dung duoc mot data pipeline on dinh, co kha nang chuyen du lieu mang thuc te thanh dau vao tuong thich voi schema da duoc su dung trong qua trinh huan luyen.

Huong tiep can nay giai quyet mot bai toan thuc te quan trong cua de tai: du lieu NSL-KDD chi ton tai duoi dang tap benchmark offline, trong khi san pham cuoi can tiep nhan du lieu mang thoi gian thuc. Vi vay, can phai co mot lop trung gian de anh xa thong tin tu log Snort sang bo dac trung dau vao cua mo hinh. Ket qua dat duoc o giai doan hien tai cho thay kien truc nay kha thi o muc MVP, dong thoi tao nen nen tang ky thuat cho cac buoc toi uu AI va tich hop he thong o cac giai doan sau.

### 4.2 Thiet lap moi truong va to chuc thu muc trien khai

Moi truong thuc nghiem duoc to chuc tren Linux/WSL, ket hop voi VS Code va Python virtual environment de dam bao kha nang lap lai va tach biet phu thuoc. Trong repo, thu muc final duoc tao rieng de chua cac thanh phan phuc vu chay that, bao gom file cau hinh Snort, rules, log thu nghiem va cac artifact preprocessing. Cach to chuc nay giup phan tach ro giua phan nghien cuu mo hinh trong MLAnomalyDetection va phan trien khai pipeline xu ly du lieu dau vao.

Trong qua trinh thuc hien, moi truong .venv da duoc sua lai de dam bao cac thu vien can thiet nhu pandas va scikit-learn co the hoat dong on dinh. Day la dieu kien bat buoc de script preprocessing co the doc log, canh chinh schema va scale du lieu theo dung artifact da luu tu qua trinh train.

### 4.3 Trien khai va cau hinh Snort cho bai toan thu thap du lieu

Snort da duoc cai dat va cau hinh o muc toi thieu nham phuc vu muc tieu ghi nhan su kien duoi dang CSV co cau truc. File cau hinh duoc dat tai final/snort.conf va su dung output plugin alert_csv voi cac truong timestamp, thong tin chu ky canh bao, giao thuc, dia chi IP nguon/dich va cong nguon/dich. Viec lua chon output dang CSV giup don gian hoa lop parser phia sau, vi script Python co the doc truc tiep du lieu theo cot ma khong can xu ly them cac format nhi phan hoac format can parser phuc tap hon.

Tu goc do he thong, Snort trong giai doan nay dong vai tro nhu mot cam bien su kien mang. Thay vi phu thuoc hoan toan vao rule-based alert de ket luan tan cong, thong tin log cua Snort duoc xem la nguon dau vao de sinh dac trung phuc vu phan lop bang mo hinh AI. Huong tiep can nay phu hop voi muc tieu cua de tai, vi no ket hop duoc uu diem cua he thong IDS truyen thong va mo hinh hoc may trong mot pipeline thong nhat.

### 4.4 Thiet ke module chuyen doi log Snort thanh vector dac trung

Thanh phan trung tam da duoc hoan thanh trong giai doan nay la script final/snort_preprocess_122.py. Script nay thuc hien cac buoc chinh gom doc log Snort dang CSV, chuan hoa cac truong giao thuc, cong dich va trang thai ket noi, tinh toan cac dac trung thong ke theo cua so thoi gian, va cuoi cung anh xa ket qua ve dung schema dau vao cua mo hinh.

Ve mat dac trung, he thong hien tai da suy dien duoc cac nhom thong tin cot loi co the khai thac tu log Snort, bao gom protocol_type, service, flag, cac thong ke theo cua so 2 giay nhu count, srv_count, same_srv_rate, diff_srv_rate, srv_diff_host_rate, va cac thong ke host-based tren 100 ket noi gan nhat nhu dst_host_count, dst_host_srv_count, dst_host_same_srv_rate va dst_host_same_src_port_rate. Cac thong tin nay duoc xay dung theo huong gan nhat voi nhom dac trung cua NSL-KDD, nham tang muc do tuong thich giua du lieu mang thuc te va du lieu huan luyen offline.

Mot diem ky thuat quan trong la pipeline hien tai khong dung truc tiep 41 dac trung raw cua NSL-KDD trong qua trinh train/inference, ma dung schema 122 cot sau khi one-hot encoding cac cot phan loai nhu protocol_type, service va flag. Do do, script Snort preprocessing khong chi sinh dac trung co nghia, ma con phai canh chinh thu tu cot theo feature_columns.json va ap dung scaler.pkl neu artifact nay ton tai. Cach lam nay giup vector dau vao tu pipeline thuc te giong voi vector ma mo hinh da hoc trong giai doan train.

### 4.5 Ket qua dat duoc va artifact da sinh ra

Sau khi hoan thanh module preprocessing, pipeline da tao duoc file dau ra model-ready tai final/snort_features_122.csv. Ket qua kiem tra mau cho thay file dau ra co dung 122 cot theo schema da khoa, phu hop voi mong doi cua he thong train hien tai. Nhu vay, giai doan 1 da dat duoc ket qua quan trong nhat: bien doi du lieu log Snort thanh vector co the dua vao pipeline AI ma khong can can thiep thu cong.

Ngoai file vector dac trung, thu muc final hien dang chua cac artifact trien khai thuc te gom final/snort.conf, final/rules/local.rules, final/log/alert.csv, final/snort_preprocess_122.py va final/snort_features_122.csv. Tap hop nay co y nghia nhu mot MVP ky thuat cho phan dau cua san pham, dong thoi la bang chung rang de tai da vuot qua giai doan y tuong va da co ket qua chay duoc tren moi truong thuc.

### 4.6 Gioi han hien tai va huong mo rong tiep theo

Mac du pipeline Snort va preprocessing da hoat dong, he thong hien tai moi chi giai quyet duoc bai toan dau vao du lieu. Cac thanh phan phia sau nhu fine-tuning mo hinh, dong goi ONNX, model serving bang FastAPI, backend realtime va dashboard giam sat van chua duoc hoan tat trong dot cong viec nay. Ben canh do, viec suy dien dac trung tu log Snort hien moi dat muc MVP, nghia la da du de chay thu nghiem inference, nhung chua the xem la tai hien day du luu luong mang o muc packet-level nhu trong cac bo du lieu benchmark chuan.

Trong giai doan tiep theo, huong phat trien hop ly la tiep tuc hoan thien lop AI sao cho checkpoint mo hinh tuong thich truc tiep voi schema 122 cot cua pipeline Snort, sau do moi tien hanh dong goi model va tich hop sang backend/dashboard. Cach di nay giup dam bao moi thanh phan moi deu duoc dat tren mot nen tang du lieu dau vao da duoc kiem soat va co kha nang lap lai.
