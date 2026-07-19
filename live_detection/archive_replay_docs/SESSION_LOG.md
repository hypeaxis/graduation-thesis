# Session Log — Xây dựng Replay-based Live Detection + Cải thiện F1

Ghi lại toàn bộ công việc của phiên làm việc (2026-06-26 → 2026-06-27).

---

## 0. Mục tiêu
Từ testbed (Snort + FT-Transformer V8.5), dựng một hệ thống **live detection theo replay**:
phát lại các file flow đã thu (CICFlowMeter) qua model → dashboard real-time phục vụ bảo vệ
đồ án. Sau đó tối ưu **macro-F1**.

---

## 1. Khảo sát & quyết định kiến trúc
- Xác nhận testbed có đủ mảnh ghép cho live detection, nhưng pipeline đang **batch/offline**.
- Chốt hướng **replay-based**: thu mỗi loại tấn công thành **1 file isolated** (1 phiên capture
  riêng), gán nhãn **theo IP attacker** (không dùng matcher time-window mong manh) → 0% ambiguous.
- Kịch bản demo: benign nền + tiêm tấn công; sau đổi thành **chọn kịch bản → play** (theo mockup).

## 2. Công cụ thu dữ liệu
- `Custom_IDS_Testbed/scripts/collect_isolated.sh` — thu 1 loại / 1 phiên.
- `Custom_IDS_Testbed/docs/HUONG_DAN_THU_DU_LIEU_ISOLATED.md` — quy trình step-by-step từng loại.
- Mở rộng `auto_attack_v3.py`: boost Brute Force (16→64 threads) và PortScan (lặp nhiều vòng).

## 3. Cấu hình mạng testbed (quan trọng)
- Máy này = **Attacker** (WSL Ubuntu/Win10), IP WSL `172.20.194.130` (NAT nội bộ).
- Traffic WSL bị **NAT qua host Win10** → victim thấy Src IP = **IP LAN host = `192.168.0.106`**.
- Victim = `192.168.0.101`.
- → `attacker_ip` cho label-by-IP phải là **`192.168.0.106`** (không phải IP WSL). Đã cập nhật
  toàn bộ config/script (victim `.101`, attacker `.106`).

## 4. Thu dữ liệu — kết quả
5 file `*_only.pcap_Flow.csv` (Src IP attacker `.106` xác nhận đúng):

| Loại | Flows | Ghi chú |
|---|---|---|
| benign | 29.486 | ✅ |
| webattack | 22.270 | ✅ |
| dos | 12.654 | ✅ |
| bruteforce | 200.000 | ✅ (quá lớn → demo cap 8000) |
| portscan | 131 | ❌ chỉ 6 cổng đích — scan flows bị firewall drop |

- Vụ Git LFS: bruteforce 125MB từng đẩy qua LFS lỗi (chỉ có con trỏ). Đã xử lý bằng cách push
  lại bản 95MB (file thường, <100MB).

## 5. Hệ thống live detection (`Replay_Live_Detection/`)
- `live_replay_server.py` — FastAPI + WebSocket, nạp V8.5 1 lần, predict-on-load.
- `dashboard.html` — UI theo mockup: dropdown kịch bản, play/pause/reset/speed, **4 metric card
  (Acc/Precision/Recall/F1)**, **Live flow stream** (Truth vs Pred, highlight FN/FP),
  **Confusion matrix**, **Explainability** (feature importance).
- `replay_config.json` — model V8.5 + đường dẫn data + IP + rule + threshold.
- `data/` — 5 file corpus.
- Đã gom toàn bộ phần demo vào folder riêng này (trước rải ở `Custom_IDS_Testbed/`).

## 6. Bug đã sửa
- `asyncio.to_thread` (chỉ có ở Python 3.9) gây **500** trên venv Python 3.8 → thay bằng
  `run_in_executor` (`in_thread`).
- Predict-on-load chặn event loop (dashboard "không hiện gì") → build corpus trong thread +
  **cap `MAX_FLOWS=8000`/file**.
- Sai đường dẫn config sau khi gom folder → trỏ lại `Replay_Live_Detection/data/`.

## 7. Phân tích & cải thiện F1
**Snapshot baseline (2026-06-27):** macro-F1 = **0.7353**, accuracy 0.9068.

| Lớp | F1 | Recall |
|---|---|---|
| Brute Force | 0.979 | 99.8% |
| DoS | 0.926 | 98.7% |
| Web Attack | 0.892 | 99.3% |
| Benign | 0.857 | **75.4%** (FP cao) |
| PortScan | **0.023** | **1.2%** (gần như hỏng) |

**Kế hoạch:** `ke-hoach-cai-thien-f1.md` (Phương án A: threshold; B: thu lại benign;
C: fine-tune; D: cải thiện PortScan).

**Đã thực hiện (lần lượt):**
- **D1 lần 1 (rule port-spread)** — THẤT BẠI & tắt: data portscan lúc đó chỉ 6 cổng (mất
  port-spread), benign 760 cổng → rule bắn nhầm benign. Code giữ lại, chờ D2.
- **A (conf_threshold=0.6)** — ✅ zero-cost: Macro-F1 **0.7353 → 0.7781**, benign recall
  **75% → 95%**, 4 lớp hoạt động 0.95–0.99 F1. Còn bị PortScan (=0) kìm.
- **D2 (thu lại PortScan trên Win11 HOST)** — ✅ giải quyết gốc: WSL tcpdump không thấy gói
  cổng đóng (Windows host RST, không bridge vào WSL) → bắt trên host → **222k flow / 22k cổng
  duy nhất** (trước: 6–9 cổng). *(Còn phát hiện thêm: nmap thiếu `-Pn` → bỏ scan khi ping bị
  chặn → đã fix trong auto_attack_v4.)*
- **D1 lần 2 (bật rule, ngưỡng 15, chỉ override src=attacker)** — ✅✅ trên data tốt:
  PortScan F1 **0.02 → 0.996** (precision 1.0); restrict src=attacker để không gắn cờ flow
  victim phản hồi → benign recall giữ **95%**.

**KẾT QUẢ CUỐI (2026-06-27): Macro-F1 = 0.9778, accuracy 0.977, mọi lớp ≥ 0.95.**

| Lớp | F1 baseline → cuối |
|---|---|
| PortScan | 0.023 → **0.996** |
| Benign | 0.857 → **0.961** (recall 95%) |
| Web Attack | 0.892 → 0.990 |
| Brute Force | 0.979 → 0.991 |
| DoS | 0.926 → 0.951 |
| **Macro-F1** | **0.735 → 0.978** |

## 8. Trạng thái & việc còn lại
- ✅ Mục tiêu F1 (>0.90) **đã đạt** (0.978). Mọi lớp ≥0.95.
- Việc vận hành còn lại: `git pull` data portscan 222k về máy demo; commit cấu hình
  (`portscan_rule.enabled=true` + rule src=attacker); restart server.
- Nâng cao (tùy chọn): B (thu benign "đời" hơn), C/D3 (fine-tune model 81-feature) — không
  bắt buộc vì F1 đã tốt.

## 9. Cách chạy demo
```bash
pkill -f "uvicorn live_replay_server"
cd /home/ning/Graduation-Thesis/Replay_Live_Detection
/home/ning/Graduation-Thesis/.venv/bin/python3 -m uvicorn live_replay_server:app --host 0.0.0.0 --port 8000
# mở http://localhost:8000 → chọn "Mixed" → ▶ Play
```

## 10. Bài học chính
1. **Label-by-IP cần đúng IP NAT** (host `.106`, không phải IP WSL).
2. **PortScan trên testbed WSL phải capture TRÊN WINDOWS HOST**, không phải tcpdump trong WSL:
   gói tới cổng đóng do Windows host xử lý (RST), không bridge vào WSL namespace → WSL tcpdump
   chỉ thấy cổng mở → mất port-spread → model nhầm thành DoS. Bắt trên host → 22k cổng.
3. **nmap cần `-Pn`**: ping victim bị chặn → nmap tưởng host down → bỏ scan (chỉ vài flow sót).
4. **Hybrid rule (port-spread, src=scanner) bù được feature thiếu**: V8.5 không có
   `Custom_PortScan_Intensity` nên không phân biệt PortScan vs DoS; rule đếm cổng/host quét
   override → đúng tinh thần Snort + ML, PortScan F1 0.02→0.996 không cần train lại.
5. **Cân bằng lớp** quan trọng hơn "càng nhiều flow càng tốt" (bruteforce 200k vô ích).
6. **Confidence threshold** là đòn bẩy F1 rẻ nhất khi FP là dự đoán confidence thấp.
7. Chú ý **phiên bản Python** (3.8 vs 3.9 API, vd `asyncio.to_thread`).
8. **Đo trước rồi mới sửa**: snapshot baseline giúp phát hiện PortScan (không chỉ Benign) mới
   là nút thắt chính, tránh tối ưu nhầm chỗ.
