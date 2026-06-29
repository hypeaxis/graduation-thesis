# 📋 KẾ HOẠCH REFACTOR — Tổng hợp đồ án vào thư mục `Final/`

> **File này là bản kế hoạch PORTABLE.** Mục đích: push lên GitHub → kéo về **codebase ĐÚNG** → thực thi tại đó.
> **Cách dùng:** làm tuần tự **Bước 0 → 12**. Bước 0 (khảo sát) BẮT BUỘC vì đường dẫn/tên thư mục ở codebase đúng có thể khác.
> **Nguyên tắc xuyên suốt:** chỉ TẠO MỚI thư mục `Final/`, **không xoá/sửa** bất kỳ file nào sẵn có (chỉ copy đi).

---

## 1. Mục tiêu & Ràng buộc (đã chốt)

| # | Yêu cầu | Chi tiết |
|---|---|---|
| 1 | **Thư mục mới `Final/`** | THUẦN THÊM MỚI — không xoá/sửa file sẵn có. |
| 2 | **Zip < 30MB** | Tiêu chí áp dụng cho **file .zip cuối**, KHÔNG phải thư mục thô. Code/`.md`/`.tex` nén ~3–5× → thư mục thô có thể >30MB vẫn đạt. Vẫn LOẠI data nặng (`*.pcap`, `*_Flow.csv`, dataset gốc). |
| 3 | **Chia theo giai đoạn như trong đồ án** | **5 giai đoạn**; GĐ5 = Replay Detection (đã build, demo chạy được). |
| 4 | **Đầy đủ code/pipeline** | Toàn bộ code, KHÔNG kèm data thô (chỉ hướng dẫn tải/thu). |
| 5 | **Kèm trọng số để demo chạy ngay** | Ít nhất 1 mô hình chạy được out-of-box. |
| 6 | **Hướng dẫn CHI TIẾT TỐI ĐA, chia theo giai đoạn** | Mỗi GĐ: cấu hình máy, cài đặt từ 0, **link tải dataset thô**, thu dữ liệu, chạy step-by-step, kết quả mong đợi, troubleshooting. |

**Ánh xạ giai đoạn (theo Chương 3 & 5 đồ án):**

| Giai đoạn | Nội dung | Mô hình | Kết quả (Chương 5) |
|---|---|---|---|
| **GĐ1** | NSL-KDD — mô hình nền tảng (Autoencoder Gate + Stacking Ensemble) | FT-Transformer 122-feature + LightGBM + Meta-LR | Macro F1 ≈ **0,681** |
| **GĐ2** | CIC-IDS-2017 — Two-Stage Cascade + Asymmetric Ensemble Voting (9 lớp) | Gating + Expert + RF + KNN + HNM | Acc **99,55%**, Macro F1 **0,9294** |
| **GĐ3** | Testbed — chẩn đoán covariate shift + thu dữ liệu thực + retrain V8.5 (5 lớp) | FT-Transformer 80-feature V8.5 | Macro F1 **91,7%** |
| **GĐ4** | End-to-End Hybrid IDS (Snort + CICFlowMeter + FTT + Dashboard) | Triển khai | Demo web + pipeline WSL |
| **GĐ5** | Phát hiện **dạng REPLAY** (KHÔNG phải live thật): phát lại CSV flow đã thu → suy luận → đẩy realtime qua WebSocket lên dashboard. Đã refactor SOLID (package `ids_replay/`). | Tái dùng V8.5 (đã có trên đĩa) | Demo chạy được |

---

## 2. BƯỚC 0 — Khảo sát codebase ĐÚNG (bắt buộc trước khi copy)

```bash
# Cây thư mục + dung lượng
du -sh */ | sort -h
# Tìm code nguồn
find . -name "*.py" -not -path "*/.git/*" -not -path "*/node_modules/*" | head -100
# Tìm TRỌNG SỐ mô hình (quyết định cái gì demo được)
find . -not -path "*/.git/*" \( -name "*.pt" -o -name "*.pth" -o -name "*.h5" -o -name "*.pkl" -o -name "*.onnx" \) -exec du -h {} \;
find . -name "*.tar.gz" -exec du -h {} \;   # model có thể nằm trong archive
# Tìm sản phẩm chạy được (backend/frontend/inference)
find . \( -name "main.py" -o -name "*pipeline_service*" -o -name "index.html" -o -name "run*.sh" \) -not -path "*/.git/*"
# Tìm đồ án (LaTeX + PDF + chương)
find . \( -name "*.tex" -o -name "DoAn.pdf" -o -name "Chuong*.md" \)
# Dữ liệu nặng cần LOẠI
find . -type f -size +5M -not -path "*/.git/*" -exec du -h {} \; | sort -h
cat .gitignore
```

**3 câu hỏi then chốt cần trả lời:**
1. **Trọng số nào tồn tại trên đĩa?** (NSL-KDD `best_model.pt`? V8.5 `v8_5_model.pt`? CIC cascade? trong `.tar.gz`?) → quyết định GĐ nào demo được ngay.
2. **Sản phẩm chạy được nằm ở đâu?** (thư mục kiểu `Final_Product` gồm backend+frontend+inference?) → lõi GĐ4; giữ nguyên cấu trúc để không phải sửa path.
3. ~~Đồ án (LaTeX/PDF/chương md)~~ → **KHÔNG đưa vào gói** (nộp nơi khác). Bỏ qua phần báo cáo.

> ✅ *Đã khảo sát repo này (2026-06-29) — số liệu THẬT:*
> - **GĐ4 demo NSL-KDD**: sản phẩm wired đầy đủ tại `NSL_KDD_Workspace/Final_Product/` (backend + frontend + inference + `models/` gồm `best_model.pt` 10MB, `autoencoder_v2_best.h5`, `scaler.pkl`, các JSON). Chạy được out-of-box.
> - **GĐ5 replay V8.5**: trọng số CÓ trên đĩa tại `Phase3_4_Retrain/v8/v8.5_Combined/` → `v8_5_model.pt` (4.4MB) + `v8_5_scaler.pkl` + `v8_5_encoder.pkl`. Đủ để GĐ5 demo chạy.
> - **Data nặng cần LOẠI**: `Replay_Live_Detection/data/*.pcap_Flow.csv` (~212MB tổng), CIC cascade `.pkl` (RF 8MB, KNN 24MB), dataset gốc (NSL-KDD/CIC CSV).

---

## 3. Cấu trúc `Final/` mục tiêu

```
Final/
├── README.md                       # Tổng quan, sơ đồ kiến trúc, bản đồ 4 GĐ, chính sách dung lượng, quick-start
├── HUONG_DAN_CAI_DAT.md            # Cài đặt CHUNG: WSL2, Python venv, deps lõi, link dataset, Snort, CICFlowMeter
├── MODELS.md                       # Kiểm kê trọng số: ship sẵn / phải train / cách lấy
├── KeHoach_SanPham.md              # Bản sao kế hoạch giai đoạn (tham chiếu)
├── .gitignore                      # NESTED — re-include *.pt/*.pkl/*.h5 trong Final/ (KHÔNG sửa .gitignore gốc)
├── 01_NSL_KDD/
│   ├── src/{data_processing,models,training}/   # preprocess 122-feat, train AE/FTT/LightGBM, stacking, eval
│   ├── data/README.md              # link tải KDDTrain+/KDDTest+ (KHÔNG kèm data)
│   ├── results/                    # classification_report, confusion_matrix.png, training_summary
│   └── HUONG_DAN_CHAY.md
├── 02_CIC_IDS_2017/
│   ├── src/{data_processing,models,training,archive}/   # FTT V2, gating/expert/HNM/ensemble
│   ├── notebooks/                  # notebook ĐÃ XOÁ output (15MB→<1MB)
│   ├── data/README.md   ├── models/README.md
│   ├── results/                    # final_v7 reports, final_system_architecture.md
│   └── HUONG_DAN_CHAY.md
├── 03_Testbed_Retrain/
│   ├── data_collection/            # auto_attack*, auto_benign*, dataset_builder*, orchestrators, hulk/, snort_rules/
│   ├── retrain/{src,v8,domain_adaptation}/   # v8.1–v8.5, domain adaptation
│   ├── data/README.md   ├── models/README.md
│   ├── results/                    # figures, optimal_threshold.json, báo cáo v5/v8
│   ├── HUONG_DAN_THU_DU_LIEU.md    # ⭐ thu dữ liệu thực (WSL2 mirrored, victim, Kali, CICFlowMeter)
│   └── HUONG_DAN_CHAY.md
├── 04_HybridIDS_Deployment/
│   ├── product/                    # COPY NGUYÊN VẸN sản phẩm (backend/inference/frontend/models)
│   │   └── models/                 # + best_model.pt + scaler.pkl  ← wired-in, chạy KHÔNG cần sửa path
│   ├── wsl_pipeline/               # testbed_inference cascade + snort_preprocess (pipeline thật, cần V8.5)
│   ├── snort/                      # snort_rules + configs
│   ├── HUONG_DAN_CHAY.md           # (A) demo web; (B) full WSL Snort+CICFlowMeter+FTT
│   └── HUONG_DAN_MO_PHONG_TAN_CONG.md
└── 05_Replay_Detection/            # phát hiện dạng REPLAY (KHÔNG phải live thật)
    ├── ids_replay/                 # package SOLID: api, config, corpus, explain, features, model, postprocess, scenarios, streaming
    ├── server.py                   # composition root  →  uvicorn server:app
    ├── live_replay_server.py       # shim tương thích lệnh cũ (from server import app)
    ├── dashboard.html              # frontend realtime (WebSocket)
    ├── replay_config.json          # SỬA path → models/ + data/ nội bộ GĐ5
    ├── models/                     # + v8_5_model.pt + v8_5_scaler.pkl + v8_5_encoder.pkl  ← wired-in, demo chạy
    ├── data/README.md              # link/cách thu corpus CSV (LOẠI *_Flow.csv ~212MB)
    └── README.md                   # cách chạy replay + giải thích rõ "replay ≠ live"

# ⛔ KHÔNG kèm BaoCao/ (đồ án) — nộp ở nơi khác, ngoài gói Final/.
```

---

## 4. Bảng GIỮ / LOẠI

| Loại | Giữ vào `Final/` | LOẠI (giảm dung lượng) |
|---|---|---|
| Code | ✅ Toàn bộ `.py/.sh/.js/.html` của 4 GĐ + package `ids_replay/` GĐ5 | `__pycache__`, `.venv`, `node_modules` |
| Notebook | ✅ Đã **xoá output** | Notebook còn output (nặng) |
| Trọng số | ✅ Mô hình demo (NSL-KDD ~10MB) + JSON config nhỏ | Trọng số train-lại-được + archive `.tar.gz` lớn |
| Dữ liệu | ❌ (chỉ `data/README.md` + link) | **Tất cả** `*.pcap`, `*_Flow.csv`, dataset gốc (KDDTrain+, CIC CSV), replay corpus |
| Báo cáo | ❌ KHÔNG kèm (nộp nơi khác) | **Toàn bộ** `DoAn.pdf` + `.tex` + figures + chương `.md` + LaTeX artifacts |
| Kết quả | ✅ report `.txt/.md`, `.json`, figures `.png` nhỏ | log phiên, output train trung gian lớn |
| Docs nội bộ | ✅ kiến trúc, walkthrough hữu ích | `ke_hoach_*.md` nội bộ, `work_session_logs/`, `archive_v*`, `Archive/` |

---

## 5. Xử lý TRỌNG SỐ mô hình

1. **Mô hình demo (bắt buộc):** nếu nằm trong archive, trích ra:
   `tar -xzf <model>.tar.gz -C Final/04_HybridIDS_Deployment/product/models --strip-components=2 <path>/best_model.pt <path>/scaler.pkl`
   → đặt cạnh `autoencoder*.h5` + JSON trong `product/models/`.
2. **Trọng số CIC cascade:** KHÔNG kèm (RF 8MB + KNN 24MB nặng); viết `models/README.md` mô tả cấu trúc mong đợi sau train + kết quả đã đạt.
3. **V8.5 cho GĐ5 (KÈM):** copy `v8_5_model.pt` (4.4MB) + `v8_5_scaler.pkl` + `v8_5_encoder.pkl` từ `Phase3_4_Retrain/v8/v8.5_Combined/` vào `05_Replay_Detection/models/`; SỬA `replay_config.json` (`model.*` và `replay_files.*`) trỏ về `models/` & `data/` nội bộ GĐ5. Lưu ý `server.py` tính `REPO_ROOT = HERE.parents[0]` → chỉnh lại base path nếu đổi cấu trúc.

---

## 6. Nguyên tắc SỬA ĐƯỜNG DẪN (để file copy sang vẫn chạy)

| Trường hợp | Cách xử lý |
|---|---|
| **Sản phẩm chạy được** (`product/`) | **GIỮ NGUYÊN** cấu trúc `backend/inference/frontend/models` → path tương đối tự đúng. Chỉ thêm weights. Kiểm tra default path trong `pipeline_service.py`/inference (sửa 1 dòng nếu lệch). |
| **Script train/eval** (GĐ1/2/3) tham chiếu chéo workspace | Chuẩn hoá về `data/` + `models/` nội bộ từng GĐ **và ghi rõ trong HUONG_DAN_CHAY.md**. |
| **GĐ5 replay** | `server.py` import `ids_replay` (relative — OK) nhưng `Settings.load(…, REPO_ROOT)` giải path trong `replay_config.json` theo repo gốc → đổi `replay_config.json` sang path nội bộ GĐ5 (`models/…`, `data/…`) **và** chỉnh `REPO_ROOT` trong `server.py` nếu lệch. |
| Tên thư mục | Dùng **ASCII** (tránh lỗi encoding khi zip/chạy). Tiếng Việt để trong nội dung. |

---

## 7. YÊU CẦU FILE HƯỚNG DẪN (chi tiết tối đa, chia theo GĐ)

**Mỗi `HUONG_DAN_CHAY.md` PHẢI đủ 7 mục (lệnh copy-paste được):**

| # | Mục | Nội dung |
|---|---|---|
| 1 | Mục tiêu + sơ đồ luồng | Riêng cho GĐ đó |
| 2 | **Cấu hình máy/phần cứng** | i7 Gen11 8c/16t, RAM 16GB, SSD NVMe, **CPU-only**; Host Win11 22H2 + WSL2 Ubuntu 22.04; tối thiểu vs khuyến nghị |
| 3 | **Cài đặt từ 0** | WSL2, Python 3.8, venv, `pip install` đúng phiên bản (torch, tensorflow, lightgbm, scikit-learn, fastapi, uvicorn), công cụ hệ thống của GĐ (Snort 3, CICFlowMeter, nmap, hydra, slowhttptest, DVWA) |
| 4 | **Tải dữ liệu thô + LINK** | Đặt vào `data/`, cấu trúc thư mục mong đợi, checksum |
| 5 | **Chạy/huấn luyện** | Thứ tự script, tham số CLI, thời gian ước lượng, output ở đâu |
| 6 | **Kết quả mong đợi** | Đối chiếu số liệu Chương 5 + cách đọc |
| 7 | **Troubleshooting** | Lỗi thường gặp |

**Danh sách file hướng dẫn:** `README.md`, `HUONG_DAN_CAI_DAT.md`, `MODELS.md`, `KeHoach_SanPham.md`, mỗi GĐ một `HUONG_DAN_CHAY.md`, + `03/HUONG_DAN_THU_DU_LIEU.md`, `04/HUONG_DAN_MO_PHONG_TAN_CONG.md`, `05/README.md`, mỗi `data/README.md` & `models/README.md`.

**Bảng LINK nhúng vào hướng dẫn:**

| Tài nguyên | Link |
|---|---|
| NSL-KDD | https://www.unb.ca/cic/datasets/nsl.html · mirror: https://www.kaggle.com/datasets/hassan06/nslkdd |
| CIC-IDS-2017 | https://www.unb.ca/cic/datasets/ids-2017.html (MachineLearningCSV hoặc PCAP) |
| CICFlowMeter | https://github.com/ahlashkari/CICFlowMeter · Python: https://github.com/hieulw/cicflowmeter |
| Snort 3 + rules | https://www.snort.org/downloads · https://rules.emergingthreats.net/ |
| DVWA | https://github.com/digininja/DVWA |
| Công cụ tấn công | nmap https://nmap.org · thc-hydra · slowhttptest · hping3 (`apt`), wordlist `rockyou.txt` |
| WSL2 mirrored networking | `.wslconfig` → `networkingMode=mirrored` |

---

## 8. Ngân sách dung lượng (tham chiếu — **mục tiêu: file .zip < 30MB**)

> Tiêu chí <30MB tính trên **file .zip**, KHÔNG phải thư mục thô. Code/`.md`/`.tex` nén ~3–5×, nên thư mục thô ~20–25MB vẫn ra zip <30MB thoải mái.

| Hạng mục | ~Size thô |
|---|---|
| GĐ4 `product/models/` (best_model.pt 10MB + AE 0.7MB + scaler + JSON) | ~10,7MB |
| GĐ5 `models/` V8.5 (v8_5_model.pt 4.4MB + scaler + encoder) | ~4,4MB |
| Code 4 GĐ + GĐ5 (sau strip notebook) | ~2–3MB |
| Hướng dẫn `.md` + results (png/txt nhỏ) | ~1MB |
| ~~BaoCao~~ | KHÔNG kèm (nộp nơi khác) |
| **Tổng thô** | **~18–19MB** → **zip ~10–15MB**, dư biên độ lớn so với 30MB |

---

## 9. gitignore (KHÔNG sửa file gốc)

Tạo **file MỚI `Final/.gitignore`** (nested, ghi đè rule `*.pt/*.pkl/*.h5` của `.gitignore` gốc trong phạm vi `Final/`):
```
!**/*.pt
!**/*.pkl
!**/*.h5
!**/*.onnx
```

---

## 10. ✅ BẢNG CHECKLIST CÔNG VIỆC (Board)

| # | Công việc | Phụ thuộc |
|---|---|---|
| 0 | Khảo sát codebase đúng (Mục 2) — định vị code/weights/sản phẩm | — |
| 1 | Tạo cây thư mục `Final/` (4 GĐ + GĐ5 + data/models placeholder) | 0 |
| 2 | **GĐ4 product**: copy sản phẩm + trích weights vào `product/models/` (DEMO CHẠY ĐƯỢC) | 0,1 |
| 3 | GĐ4 `wsl_pipeline/` + `snort/` | 1 |
| 4 | GĐ1: copy `src/` + `results/` | 1 |
| 5 | GĐ2: copy `src/` + strip notebook + `results/` | 1 |
| 6 | GĐ3: copy `data_collection/` + `retrain/` + `results/` | 1 |
| 7 | GĐ5 replay: copy `ids_replay/` + `server.py` + `live_replay_server.py` + `dashboard.html` + V8.5 weights vào `models/` + sửa `replay_config.json` | 1 |
| 8 | ~~BaoCao~~ — BỎ (báo cáo nộp nơi khác, không vào gói) | — |
| 9 | Viết `data/README.md` + `models/README.md` mọi GĐ | 1 |
| 10 | Viết toàn bộ hướng dẫn 7-mục (Mục 7) | 2–9 |
| 11 | Tạo `Final/.gitignore` | 1 |
| 12 | **Verify** (Mục 11) | tất cả |

---

## 11. VERIFICATION (kiểm thử cuối)

| Kiểm tra | Lệnh / Tiêu chí |
|---|---|
| Dung lượng (ZIP) | `cd Final && zip -rq ../Final.zip . -x '*/.venv/*' '*/__pycache__/*' && du -h ../Final.zip` < 30MB; `find Final -size +5M` rà file nặng bất thường |
| **Demo chạy được** | `cd Final/04_HybridIDS_Deployment/product` → venv + `pip install -r requirements.txt` → `uvicorn backend.app.main:app --port 8000` → `/api/config` báo `checkpoint_exists=true, scaler_exists=true` → simulate/detect thấy dashboard. *(Cần Python 3.8–3.12; torch/tensorflow chưa có wheel cho 3.14.)* |
| Wiring không cần deps | Script kiểm path: PROJECT_ROOT→`product/`, mọi artifact tồn tại, `best_model.pt` là zip hợp lệ, `feature_columns.json` = 122. |
| **Demo GĐ5 replay** | `cd Final/05_Replay_Detection` → venv + deps → `uvicorn server:app --port 8000` → mở `dashboard.html`, chọn kịch bản → thấy flow phát lại + nhãn dự đoán realtime. `replay_config.json` trỏ `models/v8_5_model.pt` nội bộ. |
| Đầy đủ | Mỗi GĐ có code + `HUONG_DAN_CHAY.md`; mở vài script kiểm path nội bộ |
| **Không phá repo** | `git status --porcelain` chỉ thấy `Final/` (untracked) + `Final/.gitignore`; KHÔNG có dòng `M`/`D` |

---

## 12. Lưu ý khi triển khai trên codebase ĐÚNG

- **Luôn chạy Bước 0 trước** để xác nhận đúng repo + đúng vị trí weights (tránh lặp lại sai sót chọn nhầm codebase).
- Ưu tiên **demo tự chứa** (mô hình + simulator) làm phương án "chạy ngay" an toàn nhất.
- Môi trường chạy thật là **WSL2 + Python 3.8–3.12** (không phải Python 3.14 trên Windows — torch chưa hỗ trợ).
- Sau khi hoàn tất, có thể nhờ Claude thực thi từng mục trong **Bảng Checklist (Mục 10)** theo thứ tự phụ thuộc.
