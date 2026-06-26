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
cd /home/ning/Graduation-Thesis/Replay_Live_Detection
/home/ning/Graduation-Thesis/.venv/bin/python3 -m uvicorn live_replay_server:app \
    --host 0.0.0.0 --port 8000
```

Khi thấy log:
```
[*] Nạp model V8.5 ...
[*] Sẵn sàng. Classes: ['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']
[*] File replay sẵn có: ['portscan', 'bruteforce', 'webattack', 'dos', 'benign']
```
→ Mở trình duyệt: **http://localhost:8000**

> Dừng server: `Ctrl+C`.

---

## 3. Kịch bản demo (làm trên dashboard)

1. **Chọn kịch bản** ở dropdown "🎬 Kịch bản": `Mixed (tất cả)` cho metric đầy đủ 5 lớp,
   hoặc 1 loại đơn (DoS / PortScan / Brute Force / Web Attack / Benign).
2. Bấm **▶ Play** → flow chạy trong "Live flow stream" (Truth vs Pred cạnh nhau, dòng
   sai tô đỏ + nhãn ⚠ FN/FP).
3. Theo dõi:
   - **4 thẻ metric** (Accuracy / Precision / Recall / **F1**) cập nhật real-time.
   - **Confusion matrix** đậm dần trên đường chéo (dự đoán đúng).
   - **"Vì sao dự đoán X?"** hiện top đặc trưng quan trọng của loại đang bị phát hiện.
4. **⏸ Pause / ↻ Reset** và **slider Tốc độ** (0.5×–8×) để điều chỉnh nhịp trình bày.

> Mẹo: dùng `Mixed` để khoe F1 macro + confusion matrix đủ 5 lớp; dùng kịch bản đơn
> (vd DoS) khi muốn tập trung giải thích một loại tấn công.

---

## 4. Trạng thái dữ liệu (corpus replay nằm trong `data/`)

| Loại | File (`data/`) | Flows | Trạng thái |
|---|---|---|---|
| PortScan | `portscan_only.pcap_Flow.csv` | ~131 | 🟡 thấp, nên thu thêm |
| Brute Force | `bruteforce_only.pcap_Flow.csv` | ~200.000 | ✅ (nên downsample ~30k) |
| Web Attack | `webattack_only.pcap_Flow.csv` | ~22.270 | ✅ |
| DoS | `dos_only.pcap_Flow.csv` | ~12.654 | ✅ |
| Benign | `benign_only.pcap_Flow.csv` | ~29.486 | ✅ |

- Nút của loại **thiếu file** sẽ tự **mờ đi** ("⚠ … (chưa thu)") cho tới khi có file trong `data/`.
- Tất cả file thu với attacker IP `192.168.0.106` → label-by-IP overlay chạy đúng.
- Thu thêm/thu lại bằng hướng dẫn:
  [HUONG_DAN_THU_DU_LIEU_ISOLATED.md](../Custom_IDS_Testbed/docs/HUONG_DAN_THU_DU_LIEU_ISOLATED.md)
  và script [collect_isolated.sh](../Custom_IDS_Testbed/scripts/collect_isolated.sh):
  ```bash
  cd /home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts
  ./collect_isolated.sh --type portscan        # thu thêm PortScan
  ```
  Sau khi thu, copy `*_Flow.csv` vào **`Replay_Live_Detection/data/`** (đúng tên trên) →
  **restart server**, nút tương ứng tự bật.

### Sửa cấu hình
Mở `replay_config.json` để đổi:
- `attacker_ip` — IP máy tấn công (dùng gán nhãn-theo-IP cho overlay accuracy). **Phải khớp
  IP thật lúc thu** (hiện tại `192.168.0.106`).
- `replay_files` — đường dẫn từng file (tương đối so với gốc repo `Graduation-Thesis/`).

---

## 5. API tham khảo (nếu muốn script demo, không bắt buộc)

```bash
# Liệt kê kịch bản + lớp model
curl -s localhost:8000/api/scenarios | python3 -m json.tool

# Chạy 1 kịch bản ở tốc độ 2× (mixed | dos | portscan | bruteforce | webattack | benign)
curl -s -X POST localhost:8000/api/play -H 'Content-Type: application/json' \
     -d '{"scenario":"mixed","speed":2}'

# Pause / Resume / Reset / đổi tốc độ
curl -s -X POST localhost:8000/api/pause
curl -s -X POST localhost:8000/api/resume
curl -s -X POST localhost:8000/api/reset
curl -s -X POST localhost:8000/api/speed -H 'Content-Type: application/json' -d '{"speed":4}'

# Feature importance (explainability) cho 1 lớp
curl -s 'localhost:8000/api/explain/DoS' | python3 -m json.tool
```

Metrics (Accuracy/Precision/Recall/F1 macro) + confusion matrix được **tính phía client**
từ luồng `{truth, pred}` qua WebSocket — khớp cách tính offline (macro trên các lớp có mặt).

---

## 6. Khắc phục sự cố

| Triệu chứng | Cách xử lý |
|---|---|
| `ModuleNotFoundError: phase2_ft_transformer_v2` / `hybrid_feature_scaler` | Chạy server **từ đúng thư mục** `Replay_Live_Detection/`; server tự thêm path. Kiểm tra 2 file tồn tại trong `CIC_IDS_2017_Workspace/src/models/` và `Phase3_4_Retrain/src/`. |
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
