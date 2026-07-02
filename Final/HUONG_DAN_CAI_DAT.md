# HƯỚNG DẪN CÀI ĐẶT CHUNG

Áp dụng cho mọi giai đoạn. Mỗi GĐ có thêm `HUONG_DAN_CHAY.md` riêng với phần cài đặt đặc thù.

## 1. Cấu hình máy

| | Tối thiểu | Khuyến nghị (môi trường phát triển đồ án) |
|---|---|---|
| CPU | 4 nhân | **i7 Gen11 8c/16t** |
| RAM | 8 GB | **16 GB** |
| Đĩa | 10 GB trống | SSD NVMe |
| GPU | Không cần | Không cần (**CPU-only**) |
| OS | Linux / WSL2 | **Win11 22H2 + WSL2 Ubuntu 22.04** |
| Python | 3.8–3.12 | 3.8 (đã kiểm thử) — ⚠️ **không dùng 3.14**, torch/tensorflow chưa có wheel |

## 2. WSL2 (nếu chạy trên Windows)

```powershell
# PowerShell (admin)
wsl --install -d Ubuntu-22.04
```
Cho GĐ3/GĐ4 (thu dữ liệu + pipeline thật) cần **mirrored networking** — tạo `C:\Users\<user>\.wslconfig`:
```ini
[wsl2]
networkingMode=mirrored
```
Khởi động lại WSL: `wsl --shutdown`.

## 3. Python venv + deps lõi

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
```
Deps lõi (phiên bản đã kiểm thử):
```
torch==2.3.0          # FT-Transformer (mọi GĐ)
tensorflow==2.13.1    # Autoencoder Gate .h5 (GĐ1, GĐ4) — GĐ5 KHÔNG cần
lightgbm              # Stacking ensemble (GĐ1)
scikit-learn          # scaler/encoder, RF/KNN (GĐ2)
fastapi==0.111.0 uvicorn==0.30.0 pydantic==2.7.2
numpy pandas joblib
```
GĐ5 (demo chạy ngay) có sẵn `requirements.txt` — cài bằng `pip install -r requirements.txt`. Các GĐ khác dùng lệnh `pip install` ghi trực tiếp trong `HUONG_DAN_CHAY.md` của GĐ đó.

## 4. Công cụ hệ thống theo GĐ

| Công cụ | Dùng ở | Cài |
|---|---|---|
| **Snort 3** | GĐ4 | `sudo apt install snort` hoặc build từ https://www.snort.org/downloads |
| **CICFlowMeter** | GĐ3, GĐ4 | Java: https://github.com/ahlashkari/CICFlowMeter · Python: https://github.com/hieulw/cicflowmeter |
| nmap, thc-hydra, slowhttptest, hping3 | GĐ3, GĐ4 (sinh tấn công) | `sudo apt install nmap hydra slowhttptest hping3` |
| DVWA | GĐ4 (mục tiêu web) | https://github.com/digininja/DVWA |
| wordlist `rockyou.txt` | brute-force | `/usr/share/wordlists/rockyou.txt` (gói `wordlists`) |

## 5. Link tải dataset thô

| Dataset | Link |
|---|---|
| NSL-KDD | https://www.unb.ca/cic/datasets/nsl.html · mirror Kaggle: https://www.kaggle.com/datasets/hassan06/nslkdd |
| CIC-IDS-2017 | https://www.unb.ca/cic/datasets/ids-2017.html (MachineLearningCSV hoặc PCAP) |
| Snort rules | https://www.snort.org/downloads · https://rules.emergingthreats.net/ |

Đặt dữ liệu theo cấu trúc mô tả trong `data/README.md` của từng GĐ.
