# Replay-based Live Detection — Hướng Dẫn Chạy

Hệ thống phát lại các file flow đã thu (CICFlowMeter `*_Flow.csv`) qua model **V8.5**
(FT-Transformer 80 feature, 5 lớp: `Benign / Brute Force / DoS / PortScan / Web Attack`)
và hiển thị phát hiện theo thời gian thực trên dashboard.

```
[Dashboard] ←─ WebSocket ─┐
                          │
[Replay engine] ── đọc *_Flow.csv → 80 feature → V8.5 → dự đoán → phát theo rate
                          │
        baseline benign (chạy nền) + tiêm tấn công (chồng lên)
```

Thành phần:
- `live_replay_server.py` — backend FastAPI + WebSocket (nạp V8.5 một lần, predict-on-load).
- `dashboard.html` — giao diện (vanilla JS, **không cần internet/CDN**).
- `replay_config.json` — khai báo đường dẫn model + file replay + IP attacker.

---

## 1. Yêu cầu (đã có sẵn trong `.venv`)

Thư viện cần: `fastapi`, `uvicorn`, `torch`, `pandas`, `scikit-learn`, `joblib`, `websockets`
— tất cả đã có trong `.venv` của repo. Kiểm tra nhanh:

```bash
cd /home/ning/Graduation-Thesis
.venv/bin/python3 -c "import fastapi, uvicorn, torch, pandas, sklearn, joblib; print('deps OK')"
```

Nếu thiếu (môi trường khác):
```bash
.venv/bin/pip install fastapi uvicorn[standard] torch pandas scikit-learn joblib
```

---

## 2. Chạy server

```bash
cd /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/live_replay
/home/ning/Graduation-Thesis/.venv/bin/python3 -m uvicorn live_replay_server:app \
    --host 0.0.0.0 --port 8000
```

Khi thấy log:
```
[*] Nạp model V8.5 ...
[*] Sẵn sàng. Classes: ['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']
[*] File replay sẵn có: ['portscan']
```
→ Mở trình duyệt: **http://localhost:8000**

> Dừng server: `Ctrl+C`.

---

## 3. Kịch bản demo (làm trên dashboard)

1. **Bật Benign baseline** → nút "▶ Bật Benign baseline". Dashboard giữ trạng thái
   `● HỆ THỐNG BÌNH THƯỜNG`, biểu đồ chủ yếu xanh (chứng minh FP thấp). Chỉnh "Tốc độ nền".
2. Đợi ~30–60s cho baseline ổn định.
3. **Tiêm tấn công**: bấm nút loại tấn công (PortScan / Brute Force / Web Attack / DoS).
   - Banner chuyển đỏ `⚠ ĐANG BỊ TẤN CÔNG`.
   - Biểu đồ nổi cột màu theo loại dự đoán.
   - Panel phải hiện **Accuracy live** (dự đoán vs nhãn-theo-IP) + phân bố dự đoán.
4. Để pha tự kết thúc (hoặc "■ Dừng tấn công") → banner về xanh.
5. Lặp cho các loại còn lại. Chỉnh "Tốc độ tấn công" tùy nhịp trình bày.

> Mẹo: cân nhắc **không** để DoS/Slowloris ở cuối (ca model yếu nhất do domain shift),
> hoặc để cuối kèm giải thích học thuật.

---

## 4. Trạng thái dữ liệu & cách thêm file còn thiếu

| Loại | File (trong `replay_config.json`) | Trạng thái |
|---|---|---|
| PortScan | `docs/attack_capture_run11.pcap_Flow.csv` | ✅ Có |
| Brute Force | `docs/bruteforce_only.pcap_Flow.csv` | ❌ Cần thu |
| Web Attack | `docs/webattack_only.pcap_Flow.csv` | ❌ Cần thu |
| DoS | `docs/dos_only.pcap_Flow.csv` | ❌ Cần thu |
| Benign | `docs/benign_only.pcap_Flow.csv` | ❌ Cần thu |

- Nút của loại **chưa có file** sẽ tự **mờ đi** ("⚠ … (chưa thu)") cho tới khi bạn thu xong.
- **Benign baseline vẫn chạy được ngay hôm nay**: nếu chưa có `benign_only`, server tự
  fallback lấy các flow benign từ file PortScan (run11) để làm nền.
- Thu các file còn thiếu bằng hướng dẫn:
  [HUONG_DAN_THU_DU_LIEU_ISOLATED.md](../../docs/HUONG_DAN_THU_DU_LIEU_ISOLATED.md)
  và script [collect_isolated.sh](../collect_isolated.sh):
  ```bash
  cd /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts
  ./collect_isolated.sh --type bruteforce
  ./collect_isolated.sh --type webattack
  ./collect_isolated.sh --type dos
  ./collect_isolated.sh --type benign --duration 600
  ```
  Sau khi copy `*_Flow.csv` về thư mục `docs/` đúng tên trong bảng trên → **restart server**,
  nút tương ứng sẽ tự bật.

### Sửa cấu hình
Mở `replay_config.json` để đổi:
- `attacker_ip` — IP máy tấn công (dùng gán nhãn-theo-IP cho overlay accuracy). **Phải khớp
  IP thật lúc thu** (mặc định `192.168.0.104`).
- `replay_files` — đường dẫn từng file (tương đối so với gốc repo `Graduation-Thesis/`).

---

## 5. API tham khảo (nếu muốn script demo, không bắt buộc)

```bash
# Liệt kê file + lớp model
curl -s localhost:8000/api/files | python3 -m json.tool

# Bật baseline benign 8 flow/giây
curl -s -X POST localhost:8000/api/baseline -H 'Content-Type: application/json' \
     -d '{"on":true,"rate":8}'

# Tiêm PortScan 25 flow/giây (loop=false: chạy hết file rồi dừng)
curl -s -X POST localhost:8000/api/attack -H 'Content-Type: application/json' \
     -d '{"attack":"portscan","rate":25,"loop":false}'

# Dừng tấn công / tắt baseline
curl -s -X POST localhost:8000/api/attack/stop
curl -s -X POST localhost:8000/api/baseline -H 'Content-Type: application/json' -d '{"on":false}'
```

---

## 6. Khắc phục sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| `ModuleNotFoundError: phase2_ft_transformer_v2` / `hybrid_feature_scaler` | Chạy server **từ đúng thư mục** `live_replay/`; server tự thêm path. Kiểm tra 2 file tồn tại trong `CIC_IDS_2017_Workspace/src/models/` và `Phase3_4_Retrain/src/`. |
| `[*] File replay sẵn có: []` | Đường dẫn trong `replay_config.json` sai hoặc file chưa có. Đối chiếu bảng mục 4. |
| Nút tấn công bị mờ | Chưa có file cho loại đó → thu bằng `collect_isolated.sh` rồi restart server. |
| Dashboard không cập nhật | Mở DevTools (F12) xem WebSocket `/ws` có kết nối; thử reload trang. |
| Accuracy thấp bất ngờ | Bình thường với một số loại do **domain shift** (CIC→testbed). Đây là nội dung học thuật để bàn trong báo cáo, không phải lỗi hệ thống. |
| Port 8000 bận | Đổi `--port 8001` (và mở `http://localhost:8001`). |

---

## 7. Lưu ý trung thực cho báo cáo
Đây là **replay-based live detection** (mô phỏng luồng đến thời gian thực từ dữ liệu đã thu),
không phải real-time packet capture. Có thể giữ thêm đường `snort -i eth0 + CICFlowMeter`
làm chế độ "true live" cho một lần demo trực tiếp nếu hội đồng yêu cầu.
