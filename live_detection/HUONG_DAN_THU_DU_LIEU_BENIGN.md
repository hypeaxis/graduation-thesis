# Hướng dẫn thu dữ liệu thật cho Live Detection (Bước 0) — step by step

**Thuộc:** Playbook cải thiện model live — [HUONG_DAN_CAI_THIEN_MODEL_LIVE.md](HUONG_DAN_CAI_THIEN_MODEL_LIVE.md) · **Bước 0**.
**Mục tiêu:** có `benign_real.csv` (dồi dào, nhãn Benign) + (tùy chọn) `<attack>_real.csv` (nhãn sạch), làm nền cho **Bước 1 (chẩn đoán)** và **Bước 2 (calibrate)**.
**Nguyên tắc tối thượng:** mọi thứ chỉ nằm trong `live_detection/`. Không retrain, không đụng model/replay ở bước này.

> **Vì sao phải thu:** model V8.5 báo nhầm ~52% benign thật thành tấn công vì **chưa từng thấy phân bố benign của mạng bạn** (covariate shift). 56 flow hiện có **quá ít** để calibrate/kết luận. Cần **≥ vài nghìn flow benign thật**.

---

## 0. Bức tranh tổng thể

```
tcpdump (eth0)  ──G CHUNK_SEC──►  chunk_*.pcap  ──cfm offline──►  chunk_*.pcap_Flow.csv (84 cột)
                                                                        │
                                                                        ▼  DROP_DIR = data/live/
                                                        (nếu server chạy → chuyển sang data/live/processed/)
                                                                        │
                                            gom + gán nhãn + tách val   ▼
                                     data/analysis/benign_real.csv  +  benign_val.csv
```

Thu benign **không cần server dashboard** — chỉ cần phần bắt gói. Server chỉ để xem realtime (và tự dọn file sang `processed/`).

> **Quy trình 2 phiên TÁCH BIỆT theo thời gian (cách bạn làm):**
> 1. **PHIÊN 1 — chỉ benign** (mục 2 + gom ở mục 3): thu cho xong, ra `benign_real.csv` + `benign_val.csv`. Kết thúc hẳn phiên này.
> 2. **PHIÊN 2 — chỉ tấn công** (mục 4, làm SAU, cần máy thứ hai): phiên riêng, ngày/giờ khác.
>
> Tách 2 phiên giúp **nhãn sạch tuyệt đối**: phiên benign không dính tấn công; phiên tấn công lọc theo `attacker_ip`. Đừng gộp chung một lần chạy.

---

## 1. Chuẩn bị (làm 1 lần)

### 1.1 Tiền điều kiện (trong WSL)

> ⚠️ **Phần bắt gói PHẢI chạy trên máy đã có CICFlowMeter V4 (`cfm`) + Java.** `cfm` là công cụ đã sinh ra dataset train → dùng nó mới đảm bảo parity 84 cột. Máy chưa có cfm/java thì **không chạy được** phiên thu; xem 1.1.3 để xử lý.

**1.1.1 tcpdump + quyền bắt gói**
```bash
command -v tcpdump || sudo apt install -y tcpdump
# cho tcpdump bắt gói không cần sudo mỗi lần (cấp quyền 1 lần):
sudo setcap cap_net_raw,cap_net_admin+eip "$(readlink -f "$(which tcpdump)")"
getcap "$(readlink -f "$(which tcpdump)")"    # phải thấy 'cap_net_raw' → OK
```

**1.1.2 Java + cfm (CICFlowMeter V4)**
```bash
command -v java || echo "!! CHUA CO JAVA — cai: sudo apt install -y openjdk-8-jre"

# cfm hay được build tại đường dẫn này (mặc định trong wsl/*.sh):
CFM_BIN="${CFM_BIN:-/home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm}"
if [ -x "$CFM_BIN" ]; then echo "OK cfm: $CFM_BIN";
else
  echo "!! KHONG THAY cfm o mac dinh. Tim khap may:"; find / -iname cfm -type f 2>/dev/null | head
  echo "   -> Neu thay o cho khac, dat bien: export CFM_BIN=/duong/dan/toi/cfm"
fi
```

**1.1.3 Nếu máy CHƯA có cfm/java**
- **Cách A (khuyến nghị):** thu trên đúng **máy đã build CICFlowMeter** (máy có eth0 LAN thật, mô tả trong báo cáo). Đây là máy dùng để chạy demo live.
- **Cách B:** cài trên máy này: `sudo apt install -y openjdk-8-jdk git` → clone & build CICFlowMeter V4 → lấy đường dẫn `.../bin/cfm` → `export CFM_BIN=...` trước khi chạy mục 2.
- **cfm ở đường dẫn khác** thì **không cần sửa script** — chỉ cần đặt biến môi trường: `export CFM_BIN=/duong/dan/toi/cfm` (cả `capture_and_extract.sh` lẫn `extract_chunk.sh` đều đọc biến này).

### 1.2 Tạo thư mục làm việc
```bash
cd /home/ning/Graduation-Thesis/live_detection
mkdir -p data/analysis training
```

### 1.3 Xác định interface bắt gói
```bash
ip -brief addr    # tìm interface mang IP LAN thật (thường eth0). Ghi nhớ để đặt IFACE nếu khác eth0.
```

---

## 2. PHIÊN 1 — Thu benign thật (làm trước, cho xong hẳn)

> Ý tưởng: cho pipeline chạy trong khi bạn **dùng máy bình thường**. Toàn bộ flow phiên này = Benign.
> Làm trọn vẹn tới hết mục 3 (gom + tách val) rồi mới chuyển sang Phiên 2.

### 2.1 Bật bắt gói
```bash
cd /home/ning/Graduation-Thesis/live_detection

# CHUNK_SEC=60: chunk dài để flow hoàn tất trong 1 pcap, tránh cắt vụn (thu để phân tích/train
# nên dùng 30–60s; chunk ngắn 5–8s chỉ hợp demo realtime cho "mượt").
CHUNK_SEC=60 bash wsl/capture_and_extract.sh
```
Mỗi chunk sẽ in: `[extract_chunk] OK -> .../chunk_YYYYMMDD_HHMMSS.pcap_Flow.csv`.
> Nếu `Operation not permitted` → chưa `setcap` (mục 1.1), hoặc chạy kèm `sudo`.

### 2.2 Tạo lưu lượng benign ĐA DẠNG (song song, ≥ 20–30 phút)
Mục tiêu **≥ 3.000–5.000 flow**. Càng đa dạng port/giao thức càng tốt:
- **Web:** lướt ≥ 10–15 site khác nhau (báo, wiki, github, shopping…), cả HTTP lẫn HTTPS.
- **Streaming:** xem YouTube/nhạc vài phút (traffic dài, nhiều gói).
- **Tải file:** tải vài file vừa (ISO nhỏ, zip, `apt update`…).
- **Nền:** để OS chạy (cập nhật, đồng bộ cloud, DNS…).
- **Khác (nếu có):** gọi video, ping, ssh nội bộ.

> ⛔ **TUYỆT ĐỐI không chạy tấn công** (nmap/hping/hydra/…) trong phiên này — sẽ làm bẩn nhãn Benign.

> ⚠️ **Traffic phải đi qua đúng interface `tcpdump` đang nghe.** Kiểm `ip -brief addr`:
> - **WSL mirrored** (eth0 mang IP LAN thật, vd `192.168.x`): tcpdump thấy cả traffic của trình duyệt Windows → lướt web ở đâu cũng được.
> - **WSL NAT** (eth0 dạng `172.x`/`10.x`): tcpdump **chỉ thấy traffic sinh từ trong WSL**. → phải tạo benign **từ chính WSL** (vd `curl`, `wget`, `apt update`, `git clone`…), trình duyệt Windows sẽ KHÔNG được bắt.
> Ví dụ sinh benign đa dạng từ WSL:
> ```bash
> for u in example.com wikipedia.org github.com kernel.org debian.org; do curl -s "https://$u" -o /dev/null; done
> sudo apt update; wget -q https://speed.hetzner.de/100MB.bin -O /tmp/x.bin && rm /tmp/x.bin
> ```

### 2.3 Dừng
`Ctrl-C` ở terminal capture. Kiểm nhanh số CSV thu được:
```bash
ls -1 data/live/*.csv data/live/processed/*.csv 2>/dev/null | wc -l
```

### 2.4 (Tùy chọn) xem realtime khi thu
Muốn vừa thu vừa xem trên dashboard: mở thêm terminal chạy server **trước** khi bắt gói:
```bash
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
#  kiểm log: [*] Live drop dir: .../live_detection/data/live   ← phải trùng DROP_DIR của script
```
Mở http://127.0.0.1:8000 → mode **🔴 LIVE**. (Server sẽ tự dời CSV sang `processed/`.)

---

## 3. Gom benign + kiểm chất lượng + tách validation (KẾT THÚC Phiên 1)

Ngay sau khi dừng capture ở Phiên 1: lưu đoạn dưới thành `training/consolidate_benign.py` rồi chạy. Nó nối mọi CSV, gán nhãn Benign, kiểm 84 cột/NaN/inf, tách train/val. **Xong mục này là hoàn tất Phiên 1** — có thể sang Bước 1/2 mà chưa cần tấn công.

```python
# live_detection/training/consolidate_benign.py
"""Gom CSV live (cfm) -> benign_real.csv + benign_val.csv, kiểm chất lượng.
Chạy:  python training/consolidate_benign.py            (từ thư mục live_detection/)
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent          # = live_detection/
SRC_DIRS = [HERE / "data" / "live" / "processed", HERE / "data" / "live"]
OUT_DIR = HERE / "data" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
VAL_FRAC = 0.20
SEED = 42
LABEL = "Benign"

# 1) gom mọi *_Flow.csv (bỏ file .part đang ghi dở)
files = []
for d in SRC_DIRS:
    if d.exists():
        files += [p for p in d.glob("*.csv") if not p.name.endswith(".part")]
if not files:
    sys.exit("[!] Khong tim thay CSV nao trong data/live/ hay data/live/processed/. Da chay capture chua?")

frames = []
for p in sorted(files):
    try:
        df = pd.read_csv(p, low_memory=False)
        df.columns = df.columns.str.strip()
        if not df.empty:
            frames.append(df)
    except Exception as e:
        print(f"  [bo qua] {p.name}: {e}")
big = pd.concat(frames, ignore_index=True)
print(f"[*] Gom {len(files)} file -> {len(big)} flow, {big.shape[1]} cot")

# 2) kiem chat luong
n_cols = big.shape[1]
print(f"[*] So cot: {n_cols} (dataset train chuan = 84)")
num = big.select_dtypes(include=[np.number])
n_nan = int(num.isna().sum().sum())
n_inf = int(np.isinf(num.to_numpy(dtype=float, na_value=0.0)).sum())
print(f"[*] NaN: {n_nan} | inf: {n_inf}  (feature extractor se nan_to_num, nhung nen biet)")

# 3) gan nhan Benign ca me
big["Label"] = LABEL

# 4) tach train/val (khong lam ban benign bang cach shuffle co seed)
big = big.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
n_val = int(len(big) * VAL_FRAC)
val, train = big.iloc[:n_val], big.iloc[n_val:]

train.to_csv(OUT_DIR / "benign_real.csv", index=False)
val.to_csv(OUT_DIR / "benign_val.csv", index=False)
print(f"[+] benign_real.csv: {len(train)} flow  ->  {OUT_DIR/'benign_real.csv'}")
print(f"[+] benign_val.csv : {len(val)} flow  (giu rieng cho Buoc 2 calibrate)")
if len(big) < 3000:
    print(f"[canh bao] Chi {len(big)} flow (<3000). Nen thu them de calibrate dang tin.")
```

Chạy:
```bash
cd /home/ning/Graduation-Thesis/live_detection
python3 training/consolidate_benign.py
```

---

## 4. PHIÊN 2 — Thu tấn công thật (phiên RIÊNG, làm SAU, cần máy thứ hai)

> **Chỉ bắt đầu phiên này sau khi đã hoàn tất Phiên 1** (đã có `benign_real.csv` từ mục 3). Đây là lần chạy khác, ngày/giờ khác, có máy thứ 2 trong LAN. Dùng cho **Bước 3 (kiểm chứng)** và **Bước 5 (fine-tune)**. Chưa có máy thứ 2 thì cứ dừng ở Phiên 1 — Bước 1–2 chỉ cần benign.

### 4.1 Chốt IP (QUAN TRỌNG)
`replay_config.json` là **nguồn chân lý**. Xác nhận đúng LAN thật rồi sửa nếu cần:
```bash
grep -E 'attacker_ip|victim_ip' replay_config.json
# victim_ip  = máy ĐANG chạy live capture (máy này)
# attacker_ip = máy thứ hai sinh tấn công
```
> ⚠️ Đang có mâu thuẫn: báo cáo ghi máy live là `192.168.1.121`, còn config ghi `192.168.0.103`. **Dùng IP thật của LAN bạn** — kiểm bằng `ip -brief addr`, rồi cập nhật cả `victim_ip` lẫn `attacker_ip`. Bắn sai IP → `PortScanRule` không kích hoạt, mọi số đo vô nghĩa.

### 4.2 Bật lại capture rồi bắn tấn công (từ MÁY THỨ HAI, nhắm vào `victim_ip`)
Trên máy victim, bật lại `CHUNK_SEC=60 bash wsl/capture_and_extract.sh` (như mục 2.1). Từ máy thứ hai, **ghi lại mốc thời gian bắt đầu/kết thúc từng loại**:
```bash
# ví dụ, thay <VICTIM_IP> = victim_ip trong config
nmap -sS -p1-1000 <VICTIM_IP>                 # PortScan
sudo hping3 --flood -S -p 80 <VICTIM_IP>      # DoS (SYN flood) — chạy vài chục giây rồi Ctrl-C
# hydra / web attack tùy nhu cầu
```
> **Lưu ý mạng (WSL mirrored):** self-scan (quét chính victim từ cùng máy) đi qua loopback, **không qua eth0** → không bắt được. **Phải bắn từ máy khác.**

### 4.3 Gán nhãn theo IP + thời gian
Gom CSV của phiên này (giống mục 3 nhưng nhãn khác): flow có `Src IP == attacker_ip` trong cửa sổ thời gian tấn công → nhãn tương ứng (PortScan/DoS/…) → `data/analysis/<attack>_real.csv`. Cách gán "theo IP tấn công + thời điểm" **sạch hơn** nhãn CIC gốc vì bạn biết chính xác flow nào là tấn công.

---

## 5. Tiêu chí Done (Bước 0)
- [ ] `data/analysis/benign_real.csv` có **≥ vài nghìn flow** (lý tưởng ≥ 3.000–5.000).
- [ ] `data/analysis/benign_val.csv` (validation giữ riêng) đã tách.
- [ ] Kiểm: đúng **84 cột**, số NaN/inf đã biết (không bất thường).
- [ ] (Phiên 2, nếu đã làm) có ít nhất 1–2 loại tấn công thật nhãn sạch trong `data/analysis/<attack>_real.csv`.

---

## 6. Cạm bẫy thường gặp
- **Chunk quá ngắn** → flow bị cắt vụn, `Bytes/s`/`Packets/s` méo. Thu để phân tích: **CHUNK_SEC 30–60s**.
- **Thu quá ít** (vài chục flow) → mọi kết luận/calibrate sau đó vô nghĩa. Đủ vài nghìn.
- **Chạy tấn công lẫn trong phiên benign** → bẩn nhãn. Tách phiên rõ ràng.
- **DROP_DIR ≠ nơi server watch** (nếu bật server): đối chiếu log `[*] Live drop dir:` với đường `capture_and_extract.sh` in ra.
- **Bit +x của script bị mất** (repo trên `/mnt/d`): `capture_and_extract.sh` đã tự `chmod +x`; nếu vẫn lỗi `execlp ... Permission denied` thì `chmod +x wsl/*.sh`.
- **Self-scan không bắt được** (mục 4.2): tấn công phải bắn từ máy khác.

---

## 7. Bước tiếp theo
Có `benign_real.csv` + `benign_val.csv` rồi → sang:
- **Bước 1 — Chẩn đoán:** KS-test `benign_real` vs benign CIC (`cic_train_full.csv`) + SHAP trên flow FP → tìm 3–5 feature thủ phạm.
- **Bước 2 — Calibrate:** temperature scaling trên `benign_val` + ngưỡng theo lớp (nâng riêng DoS/Web Attack). Quick win, không retrain.

Xem chi tiết trong [HUONG_DAN_CAI_THIEN_MODEL_LIVE.md](HUONG_DAN_CAI_THIEN_MODEL_LIVE.md).
