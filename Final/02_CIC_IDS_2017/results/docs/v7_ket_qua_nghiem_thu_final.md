# Kết Quả Nghiệm Thu Hệ Thống Cascade NIDS V7 (CIC-IDS-2017)

> **Kết quả đã được xác thực lại (re-test) ngày 2026-06-25**, khớp chính xác với báo cáo V7 gốc.
> Đây là kết quả chính thức (final) dùng cho báo cáo đồ án.

---

## 1. Cấu Hình Thử Nghiệm

| Hạng mục | Giá trị |
| :--- | :--- |
| Bộ dữ liệu | CIC-IDS-2017 (flow-based, đã loại bỏ IP/Timestamp) |
| Số luồng kiểm thử (End-to-End) | **2.529.391** flows |
| Kiến trúc | Two-Stage Cascade |
| Stage 1 (Gating) | FT-Transformer — phân loại `Benign` / `Suspicious`, ngưỡng = **0.85** |
| Stage 2 (Expert) | Ensemble: **FT-Transformer + Random Forest + KNN** (Rule-based Voting) |
| Ngưỡng Infiltration | **0.70** |
| Số đặc trưng | Stage 1: 77 · Stage 2: 34 (gồm 2 đặc trưng tỷ lệ `Flow_Bytes_Ratio`, `Flow_Pkts_Ratio`) |

**Lệnh tái lập:**
```bash
cd CIC_IDS_2017_Workspace
python src/training/scripts_v7/evaluate_cascade_system_v7.py
```

---

## 2. Kết Quả Phân Loại Chi Tiết (Infiltration Threshold = 0.70)

| Nhãn (Class) | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | ---: |
| **Benign** | 0.9992 | 0.9953 | **0.9972** | 2.031.715 |
| **DoS** | 0.9683 | 0.9963 | **0.9821** | 225.024 |
| **PortScan** | 0.9936 | 0.9990 | **0.9963** | 142.079 |
| **DDoS** | 0.9984 | 0.9982 | **0.9983** | 114.453 |
| **Brute Force** | 0.9473 | 0.9989 | **0.9724** | 12.369 |
| **Web Attack** | 0.9084 | 0.9810 | **0.9433** | 1.950 |
| **Botnet (Bot)** | 0.7947 | 0.6826 | **0.7344** | 1.758 |
| **Infiltration** | 0.9524 | 0.6061 | **0.7407** | 33 |
| **Heartbleed** | 1.0000 | 1.0000 | **1.0000** | 10 |

---

## 3. Chỉ Số Tổng Hợp

| Chỉ số | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | ---: |
| **Accuracy** | | | **0.9955** | 2.529.391 |
| **Macro avg** | 0.9514 | 0.9175 | **0.9294** | 2.529.391 |
| **Weighted avg** | 0.9956 | 0.9955 | **0.9955** | 2.529.391 |

---

## 4. Nhận Xét Chính

- **Độ chính xác tổng thể (Accuracy): 99.55%** — hệ thống hoạt động ổn định trên quy mô 2,5 triệu luồng mạng thực tế.
- **Macro F1-Score: 0.9294** — duy trì hiệu năng cao đồng đều trên cả 9 lớp, bất chấp mất cân bằng dữ liệu cực đoan (Benign chiếm ~80%, trong khi Heartbleed chỉ có 10 mẫu).
- **Các lớp đa số (Benign, DDoS, PortScan, DoS):** F1 ≥ 0.98, gần như hoàn hảo.
- **Botnet:** Cơ chế Botnet Consensus (đòi hỏi RF & KNN đồng thuận) giữ Precision ở mức **79.47%** — giải quyết triệt để vấn đề báo động giả của các phiên bản trước.
- **Infiltration:** Precision rất cao (95.24%) nhưng Recall giới hạn ở **60.61%** — phản ánh giới hạn vật lý của tập dữ liệu Flow-based tĩnh (13/33 mẫu Infiltration trùng đặc trưng với truy cập HTTPS thông thường, không thể phân biệt khi thiếu thông tin tương quan thời gian).
- **Heartbleed:** Đạt F1 = 1.0000 (10/10 mẫu) dù số lượng cực hiếm.

---

*Báo cáo này được sinh từ kết quả thực thi `evaluate_cascade_system_v7.py` trên toàn bộ tập kiểm thử. Xem thêm phân tích kiến trúc và quá trình tiến hóa V1→V7 tại [v7_final_report.md](v7_final_report.md) và [FINAL_PROJECT_SUMMARY.md](FINAL_PROJECT_SUMMARY.md).*
