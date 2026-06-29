# Hybrid NIDS — Phát hiện xâm nhập mạng lai ghép (Snort + FT-Transformer)

Gói sản phẩm cuối của đồ án tốt nghiệp. Tổng hợp **toàn bộ code/pipeline qua 5 giai đoạn nghiên cứu**, kèm trọng số để demo chạy ngay, **không kèm dữ liệu thô** (chỉ hướng dẫn tải/thu).

> ⚠️ Gói này **KHÔNG kèm báo cáo (đồ án)** — báo cáo được nộp ở nơi khác.

---

## 1. Ý tưởng cốt lõi

Không hướng tiếp cận đơn lẻ nào đủ phủ mọi vector tấn công:

- **IDS dựa trên dấu hiệu (Snort):** phát hiện nhanh, FP thấp, nhưng bỏ sót biến thể mới / zero-day.
- **IDS học máy (FT-Transformer):** học đặc trưng hành vi từ flow, bắt được tấn công chưa có luật, nhưng khó với tấn công "trông giống Benign" và nhạy với covariate shift.

→ **Hybrid IDS** ghép hai tầng để mỗi tầng bù điểm mù của tầng kia.

```
            ┌─────────────┐      ┌──────────────────┐      ┌────────────────────┐
  Traffic → │  Snort 3    │ ───► │  CICFlowMeter     │ ───► │  FT-Transformer     │ ──► Cảnh báo
            │ (dấu hiệu)  │      │  (trích đặc trưng)│      │  (ML đa lớp)        │
            └─────────────┘      └──────────────────┘      └────────────────────┘
```

---

## 2. Bản đồ 5 giai đoạn

| GĐ | Thư mục | Nội dung | Mô hình | Kết quả (Chương 5 đồ án) |
|----|---------|----------|---------|--------------------------|
| 1 | [01_NSL_KDD/](01_NSL_KDD/) | Mô hình **nền tảng** (AE Gate + Stacking Ensemble) — giá trị là **số liệu**, không phải hệ thống triển khai | FT-Transformer 122-feat + LightGBM + Meta-LR | Macro F1 ≈ **0,681** |
| 2 | [02_CIC_IDS_2017/](02_CIC_IDS_2017/) | Two-Stage Cascade + Asymmetric Ensemble Voting (9 lớp) | Gating + Expert + RF + KNN + HNM | Acc **99,55%**, Macro F1 **0,9294** |
| 3 | [03_Testbed_Retrain/](03_Testbed_Retrain/) | Chẩn đoán covariate shift + thu dữ liệu thực + retrain V8.5 (5 lớp) | FT-Transformer 80-feat V8.5 | Macro F1 **91,7%** |
| 4 | [04_HybridIDS_Deployment/](04_HybridIDS_Deployment/) | Hybrid IDS End-to-End (Snort + CICFlowMeter + **FT-Transformer V8.5**) | Triển khai | pipeline WSL; **demo chạy = GĐ5 replay** |
| 5 | [05_Replay_Detection/](05_Replay_Detection/) | Phát hiện **dạng replay** (phát lại corpus CSV, suy luận realtime qua WebSocket) | Tái dùng V8.5 | Demo replay, PortScan F1 0,996 |

> **Lưu ý "replay ≠ live":** GĐ5 phát lại các flow đã thu sẵn (CSV) rồi đẩy realtime lên dashboard — **không bắt gói trực tiếp**. Đường xử lý thời gian thực hoàn toàn là hướng phát triển.

---

## 3. Quick-start — demo hệ thống thật (GĐ5 replay V8.5)

**Yêu cầu:** WSL2 Ubuntu 22.04 (hoặc Linux), **Python 3.8–3.12** (torch chưa có wheel cho 3.14), CPU-only là đủ.

> Đây là **demo của hệ thống End-to-End thật** (V8.5 + luật hậu xử lý) — đúng cái báo cáo đo Macro F1 0,978.

```bash
cd 05_Replay_Detection
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000        # chạy TỪ thư mục 05_Replay_Detection/
# Mở dashboard.html → chọn kịch bản "dos" (corpus đi kèm) → xem nhãn dự đoán realtime
```

Xem chi tiết từng GĐ trong `HUONG_DAN_CHAY.md` tương ứng và [HUONG_DAN_CAI_DAT.md](HUONG_DAN_CAI_DAT.md) (cài đặt chung).

> **NSL-KDD (GĐ1)** chỉ là giai đoạn nền tảng: trọng số kèm trong `01_NSL_KDD/models/` để **tái hiện số liệu** (Macro F1 0,681), KHÔNG phải hệ thống triển khai.

---

## 4. Chính sách dung lượng & dữ liệu

- Mục tiêu: **file .zip < 30MB**. Gói thô ~27MB; sau zip ~12–16MB.
- **KHÔNG kèm dữ liệu thô** (NSL-KDD, CIC CSV, pcap, *_Flow.csv corpus) — xem `data/README.md` mỗi GĐ để tải/thu.
- **Kèm trọng số:** V8.5 `v8_5_model.pt` (GĐ5 — hệ thống thật, demo chạy) + NSL-KDD `best_model.pt` (GĐ1 — chỉ để tái hiện số liệu nền tảng). Trọng số CIC cascade phải train lại — xem [MODELS.md](MODELS.md).
- Corpus replay GĐ5: chỉ kèm `dos_only` (mẫu nhỏ) để demo chạy; các kịch bản khác xem [05_Replay_Detection/data/README.md](05_Replay_Detection/data/README.md).

---

## 5. Bản đồ tài liệu

| File | Nội dung |
|------|----------|
| [HUONG_DAN_CAI_DAT.md](HUONG_DAN_CAI_DAT.md) | Cài đặt chung: WSL2, Python venv, deps lõi, Snort 3, CICFlowMeter, link dataset |
| [MODELS.md](MODELS.md) | Kiểm kê trọng số: ship sẵn / phải train / cách lấy |
| [KeHoach_SanPham.md](KeHoach_SanPham.md) | Bản đồ giai đoạn & quyết định thiết kế (tham chiếu) |
| `0X_*/HUONG_DAN_CHAY.md` | Hướng dẫn chạy chi tiết từng giai đoạn (7 mục) |
| [03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md](03_Testbed_Retrain/HUONG_DAN_THU_DU_LIEU.md) | Thu dữ liệu thực (WSL2 mirrored + victim + Kali + CICFlowMeter) |
| [04_HybridIDS_Deployment/HUONG_DAN_MO_PHONG_TAN_CONG.md](04_HybridIDS_Deployment/HUONG_DAN_MO_PHONG_TAN_CONG.md) | Mô phỏng tấn công cho demo End-to-End |
