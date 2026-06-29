# Kế hoạch sản phẩm — Bản đồ giai đoạn & quyết định thiết kế (tham chiếu)

Tài liệu tham chiếu nhanh cho người đọc gói. Chi tiết kỹ thuật nằm trong báo cáo (nộp ở nơi khác).

## Mạch nghiên cứu 5 giai đoạn
Mỗi giai đoạn xuất phát từ kết quả định lượng của giai đoạn trước:

1. **NSL-KDD (nền tảng):** thiết lập Two-Stage (AE Gate + Stacking Ensemble), xác nhận giới hạn trên của dataset 1998 → Macro F1 ≈ 0,681.
2. **CIC-IDS-2017:** phát triển Two-Stage Cascade + Asymmetric Ensemble Voting cho 9 lớp + Hard Negative Mining → Macro F1 0,9294 (Acc 99,55%).
3. **Testbed + Retrain:** chẩn đoán covariate shift, thu dữ liệu thật trên WSL2, retrain hoàn toàn → **V8.5** (80-feature, 5 lớp) Macro F1 91,7%.
4. **Hybrid IDS End-to-End:** ghép Snort (dấu hiệu) + CICFlowMeter + FT-Transformer + Dashboard.
5. **Replay Detection:** phát lại corpus CSV, suy luận realtime qua WebSocket bằng V8.5 (replay ≠ live).

## Bốn quyết định thiết kế then chốt (phân tích trong báo cáo)
| Quyết định | Lý do |
|---|---|
| Focal Loss + CB-alpha | Mất cân bằng >1000:1; tổng gradient Benign áp đảo nếu dùng Cross-Entropy thuần |
| Hard Negative Mining > tăng class weight | +13% Botnet F1 so với class weight ×10; cải thiện boundary learning |
| Asymmetric Ensemble Voting | FTT + RF + KNN có inductive bias khác nhau → correlation thấp → giảm variance |
| Luật hậu xử lý kiểu dấu hiệu (đếm cổng) | Bù đặc trưng PortScan mà V8.5 thiếu, rẻ hơn train lại: F1 0,000 → 0,996 |

## Giới hạn đã xác nhận
- **PortScan trong WSL2 không phân tách** (NAT đổi phân phối flow) — giải bằng dữ liệu surrogate.
- **Infiltration/Botnet** bị giới hạn bởi phân tích flow tĩnh — cần temporal analysis hoặc DPI.

> Xem `README.md` để biết bản đồ thư mục và quick-start.
