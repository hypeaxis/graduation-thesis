# Báo cáo thực trạng phần Live Detection

**Ngày:** 02/07/2026
**Phạm vi:** thư mục `live_detection/` — nhánh phát hiện xâm nhập thời gian thực (micro-batch: tcpdump → CICFlowMeter V4 → FT-Transformer V8.5).
**Mục đích:** tổng hợp kiến trúc, kết quả kiểm chứng, các lỗi đã sửa, và đánh giá độ chính xác thực tế của phần live.

---

## 1. Tóm tắt điều hành (TL;DR)

- **Đường ống live đã chạy đúng end-to-end**: bắt gói trực tiếp trên card mạng → trích đặc trưng bằng đúng công cụ tạo dataset (CICFlowMeter V4) → model V8.5 suy luận realtime → đẩy lên dashboard qua WebSocket. Không còn "chạy file có sẵn".
- **Đã sửa 2 lỗi chặn đứng luồng live** (lệch thư mục drop; script thiếu quyền thực thi) — trước khi sửa, hệ thống bắt được gói nhưng **không sinh ra flow nào** lên dashboard.
- **Hạn chế lớn còn tồn tại**: trên **traffic Internet thật (benign)**, model báo nhầm **~52% flow benign thành tấn công** với độ tin cậy cao. Đây là **covariate/domain shift ở phía dữ liệu**, không phải lỗi lập trình. Chỉ số Macro-F1 0.978 chỉ đúng trên tập test CIC-IDS-2017.

---

## 2. Kiến trúc & cơ chế live (thực tế đang chạy)

```
┌─ WSL (Ubuntu, networkingMode=mirrored) — bắt gói + trích đặc trưng ──────────┐
│  tcpdump -i eth0 -G <CHUNK_SEC> -w chunk_%time.pcap  -z extract_chunk.sh      │
│     └─ mỗi CHUNK_SEC giây đóng 1 pcap → tcpdump gọi extract_chunk.sh <pcap>   │
│          └─ cfm (CICFlowMeter V4, OFFLINE) → <chunk>_Flow.csv (84 cột)        │
│               └─ ghi atomic (.part → rename) vào data/live/                   │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                        │ data/live/  (thư mục drop)
┌──────────────────────────────────────▼───────────────────────────────────────┐
│  Server FastAPI (uvicorn)                                                      │
│  LiveEngine poll data/live/ mỗi 1s → LiveFlowSource đọc CSV mới                │
│     → FeatureExtractor (80 đặc trưng, y hệt replay)                            │
│     → model V8.5 (FT-Transformer) → ConfidenceThresholdRule + PortScanRule     │
│     → broadcast từng flow qua WebSocket → dashboard (tab 🔴 LIVE)             │
│  File đã xử lý chuyển sang data/live/processed/                                │
└───────────────────────────────────────────────────────────────────────────────┘
```

**Vì sao micro-batch chứ không live-sniff:** cfm live (`-i eth0`) không ổn định trên WSL; cfm **offline trên pcap** dùng đúng logic công cụ đã sinh dataset → parity 84/84 cột, không lệch schema.

**Độ trễ:** ≈ `CHUNK_SEC` (mặc định 8s) + vài mili-giây cfm.

**Tách bạch 2 chế độ (đã xác minh độc lập hoàn toàn):**
| | REPLAY | LIVE |
|---|---|---|
| Kích hoạt | `/api/play` (nút ▶) | `/api/live/start` (nút 🔴 LIVE) |
| Nguồn dữ liệu | `data/*_Flow.csv` (có nhãn) | `data/live/*.csv` (WSL sinh realtime) |
| Code đọc | CorpusLoader → ScenarioService → ReplayEngine | LiveFlowSource → LiveEngine |
| Hiển thị | Accuracy/F1/Confusion Matrix | Chỉ dự đoán + cảnh báo (không nhãn thật) |

`LiveFlowSource` **không** import corpus, **không** đụng `replay_files`. Hai nhánh chỉ dùng chung model/scaler (chủ đích, để parity).

---

## 3. Kết quả kiểm chứng (đã chạy thật)

| Hạng mục | Kết quả |
|---|---|
| tcpdump bắt gói trên eth0 | ✅ 657–781 gói/lần test |
| tcpdump → cfm postrotate | ✅ sinh CSV mỗi chunk (sau khi sửa +x) |
| CSV live parity schema | ✅ 84/84 cột khớp dataset train, 0 NaN, 0 inf |
| Server nuốt CSV → WebSocket | ✅ nhận flow live, `truth` rỗng (đúng bản chất live) |
| Dashboard 2 chế độ | ✅ REPLAY/LIVE tách bạch, chuyển chế độ tự dừng engine kia |
| Model chạy đúng trên dữ liệu train | ✅ dos_only → 1611 DoS / 374 Benign (đúng lớp) |

---

## 4. Các lỗi đã phát hiện & sửa

### 4.1 Lệch thư mục drop (DROP_DIR ≠ nơi server watch)
- **Triệu chứng:** bấm LIVE nhưng dashboard trống.
- **Nguyên nhân:** repo tồn tại **2 bản song song** (`/home/ning/...` và `/mnt/d/ĐỒ ÁN/...`). Script WSL hardcode ghi CSV sang bản `/mnt/d`, còn server watch `data/live/` của bản đang chạy → hai thư mục khác nhau.
- **Đã sửa:** script tự suy `DROP_DIR` từ vị trí của nó (`../data/live`); server đọc biến `LIVE_DROP_DIR` (mặc định `HERE/data/live`) và **in ra khi khởi động** để đối chiếu. Quy tắc: chạy server + script từ **cùng một bản repo**, hoặc set `LIVE_DROP_DIR`/`DROP_DIR` cho khớp.

### 4.2 Script thiếu quyền thực thi (+x) — lỗi nghiêm trọng nhất
- **Triệu chứng:** bật server + capture + duyệt web nhưng **không có flow nào**; pcap chất đống trong `~/live_cap/pcap/`.
- **Nguyên nhân:** `tcpdump -z` gọi `extract_chunk.sh` bằng `execlp()` — bắt buộc file có bit `+x`. Script là `-rw-r--r--` → báo `compress_savefile: execlp(...) failed: Permission denied` → **cfm không bao giờ chạy** → không sinh CSV. (tcpdump vẫn bắt gói bình thường nên dễ tưởng nhầm capture hỏng.)
- **Đã sửa:** `chmod +x` cả 2 script; ghi bit `+x` vào **git** (mode 100755) để clone/copy sau vẫn giữ; thêm **tự chữa** trong `capture_and_extract.sh` (tự `chmod +x` + kiểm tra `-x` trước khi chạy, báo lỗi rõ) — vì bản trên `/mnt/d` (DrvFs) hay mất bit thực thi.

---

## 5. Môi trường mạng (WSL mirrored)

- `.wslconfig`: `networkingMode=mirrored`, `hostAddressLoopback=true`.
- `eth0` mang **IP LAN thật** `192.168.1.121/24`, gateway `192.168.1.1` (WSL nằm trực tiếp trên LAN, không NAT).
- **tcpdump trên eth0 bắt được:** mọi traffic đi/đến máy (cả app Windows lẫn WSL), tấn công từ máy khác nhắm vào `192.168.1.121`.
- **Không bắt được:** traffic giữa 2 máy khác trong LAN (giới hạn switch — cần SPAN/port-mirroring), và **self-scan** (quét chính `192.168.1.121` từ cùng máy đi qua loopback chứ không qua eth0).
- ⇒ Muốn demo tấn công: **bắn từ máy khác** vào `192.168.1.121`.

---

## 6. Đánh giá độ chính xác trên traffic thật ⚠️

Chạy model V8.5 trên **56 flow duyệt web thật** (curl example.com/google/wikipedia — toàn bộ là **benign**):

| Model dự đoán | Số flow | Tỉ lệ | Confidence TB |
|---|---|---|---|
| Benign ✅ | 27 | 48% | 0.66 |
| **DoS ❌ (sai)** | 17 | 30% | 0.85 |
| **Web Attack ❌ (sai)** | 12 | 21% | 0.88 |

**→ ~52% flow benign bị báo nhầm thành tấn công**, với confidence cao nên `conf_threshold=0.6` không lọc được. Ví dụ:
- `192.168.1.121 → 172.66.147.243:80` (HTTP thường) → **Web Attack 0.89**
- `192.168.1.121 → 103.102.166.224:443` (TLS thường) → **DoS 0.86**

### Đã loại trừ lỗi kỹ thuật (⇒ đây là shift dữ liệu thật)
1. Parity cột hoàn hảo: live 84 cột = train 84 cột (0 thiếu/thừa).
2. Feature sạch: 0 NaN, 0 inf.
3. Model dự đoán đúng trên dữ liệu train-distribution (dos_only → DoS).

### Diễn giải
Dùng CICFlowMeter chỉ đảm bảo **parity ở khâu trích đặc trưng** (cùng công cụ, cùng schema). Nó **KHÔNG** giải quyết việc model được train trên traffic **lab** (CIC-IDS-2017 benign do B-Profile sinh) trong khi traffic Internet thật có thống kê luồng khác hẳn → **domain shift ở phía dữ liệu**, benign thật bị đẩy sang DoS/Web Attack.

> **Lưu ý cho báo cáo:** Macro-F1 **0.978** là trên tập test **CIC-IDS-2017** (giữ nguyên để báo cáo). Còn live trên mạng thật thì FP cao — cần nêu **trung thực như một giới hạn** của triển khai (đúng tinh thần bàn về covariate shift).

---

## 7. Trạng thái từng thành phần

| Thành phần | Trạng thái |
|---|---|
| Bắt gói (tcpdump/eth0) | ✅ Hoạt động |
| Trích đặc trưng (cfm V4, parity) | ✅ Hoạt động, 84/84 cột |
| Đường ống drop → server → WebSocket | ✅ Hoạt động |
| Dashboard 2 chế độ REPLAY/LIVE | ✅ Hoạt động, tách bạch rõ |
| Phát hiện tấn công (khi có tấn công thật) | ⚠️ Chưa kiểm chứng với tấn công thật từ máy khác |
| Độ chính xác trên benign thật | ❌ FP ~52% (covariate shift) |
| Luật PortScanRule | ⚠️ Cần đặt đúng `attacker_ip` mới kích hoạt |

---

## 8. Khuyến nghị (theo thứ tự ưu tiên)

1. **Kiểm chứng phát hiện tấn công thật:** từ máy thứ hai trong LAN, chạy portscan/DoS vào `192.168.1.121`, xác nhận model bắt đúng (và đặt `attacker_ip` trong `replay_config.json` = IP máy tấn công để PortScanRule hoạt động).
2. **Giảm false positive trên benign** (nếu muốn demo live "sạch"):
   - Thu vài nghìn flow **benign của chính mạng này** (duyệt web thường) → **fine-tune** hoặc ít nhất **calibrate lại ngưỡng theo từng lớp**.
   - Hoặc giới hạn demo live vào kịch bản có tấn công rõ, kèm ghi chú FP trên benign.
3. **Báo cáo trung thực:** đưa mục "hạn chế covariate shift trên môi trường live thật" vào chương kết luận — phân biệt rõ: parity công cụ (đã đạt) ≠ khớp phân bố traffic (chưa đạt).

---

## 9. Cách chạy nhanh (tham chiếu)

```bash
# Terminal 1 — server
cd /home/ning/graduation-thesis/live_detection
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000
#   kiểm tra log: [*] Live drop dir: .../live_detection/data/live

# Terminal 2 — bắt gói
cd /home/ning/graduation-thesis/live_detection
CHUNK_SEC=5 bash wsl/capture_and_extract.sh
#   mỗi chunk in: [extract_chunk] OK -> .../chunk_....pcap_Flow.csv

# Trình duyệt: http://127.0.0.1:8000 → tab 🔴 LIVE → Bắt đầu bắt gói → tạo traffic
```
