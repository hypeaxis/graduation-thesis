# Kế hoạch xây dựng demo IDS replay-based dashboard

Tài liệu này chia việc xây dựng UI demo cho hệ thống phát hiện xâm nhập (intrusion detection) dạng replay-based thành các giai đoạn cụ thể, kèm task, deliverable và ước lượng công sức. Mục tiêu cuối cùng là một dashboard web phục vụ buổi bảo vệ đồ án, cân bằng giữa trình diễn metrics (Accuracy, F1) và khả năng tương tác.

Ước lượng tổng: khoảng **10–14 ngày công** cho một người. Phần đánh dấu `[MVP]` là tối thiểu phải có để demo chạy được; phần `[+]` là nâng cao, làm nếu còn thời gian.

---

## Kiến trúc tổng thể

```
File kịch bản (.csv flow)  ─►  Replay Engine (FastAPI)  ─►  Model dự đoán
                                       │                          │
                                       ▼                          ▼
                              WebSocket emit { features, ground_truth, prediction, confidence }
                                       │
                                       ▼
                              Frontend React: bảng flow + metrics + confusion matrix + explainability
```

- Backend: FastAPI giữ replay engine + model + endpoint SHAP.
- Giao tiếp: WebSocket cho stream flow real-time; REST cho danh sách kịch bản và SHAP theo flow.
- Frontend: React, nhận flow và cập nhật UI; tự tính metric tích lũy phía client.

---

## Giai đoạn 0 — Chuẩn bị & thiết kế (≈1 ngày)

| Task | Deliverable | Ưu tiên |
|------|-------------|---------|
| Chốt **data contract**: định nghĩa chính xác JSON một flow gửi qua WebSocket (các cột feature, ground_truth, prediction, confidence, timestamp) | File `schema.md` hoặc Pydantic model | `[MVP]` |
| Kiểm tra lại các file kịch bản (benign, DoS, brute force, web attack, port scan) — đảm bảo cùng định dạng cột, có nhãn ground truth | Danh sách file đã chuẩn hóa | `[MVP]` |
| Xác nhận model load được độc lập và `predict()` chạy trên một flow đơn lẻ | Script test `predict_one.py` | `[MVP]` |
| Tạo một file "mixed" trộn benign + nhiều loại tấn công để demo kịch bản thực tế | `mixed_scenario.csv` | `[+]` |

Lưu ý: chốt data contract sớm là quan trọng nhất — nó cho phép làm backend và frontend song song mà không phải sửa đi sửa lại.

---

## Giai đoạn 1 — Backend & Replay Engine (≈3–4 ngày)

| Task | Deliverable | Ưu tiên |
|------|-------------|---------|
| Dựng khung FastAPI, endpoint `GET /scenarios` trả danh sách file kịch bản | App chạy được | `[MVP]` |
| **Model wrapper**: load model một lần khi khởi động, hàm dự đoán nhận flow → trả prediction + confidence | Module `model.py` | `[MVP]` |
| **Replay engine**: generator đọc lần lượt từng flow trong file, đẩy qua model | Module `replay.py` | `[MVP]` |
| **WebSocket** `/ws/replay`: stream từng flow kèm ground_truth + prediction, có độ trễ điều chỉnh được (điều khiển tốc độ) | Endpoint hoạt động | `[MVP]` |
| Điều khiển **play / pause / restart / speed** qua message từ client | Logic xử lý lệnh | `[MVP]` |
| Lưu lại toàn bộ cặp (truth, pred) trong session để tính confusion matrix cuối | State trong session | `[MVP]` |
| Endpoint `GET /explain/{flow_id}` trả **SHAP values** / feature importance cho một flow | Endpoint giải thích | `[+]` |
| Chế độ "chạy nhanh toàn bộ" trả thẳng metric tổng kết không cần stream | Endpoint `/run_full` | `[+]` |

---

## Giai đoạn 2 — Frontend UI (≈4–5 ngày)

| Task | Deliverable | Ưu tiên |
|------|-------------|---------|
| Khung layout dashboard theo mockup đã duyệt (control bar trên, metrics, bảng flow, confusion matrix, panel explain) | Layout tĩnh | `[MVP]` |
| **Thanh điều khiển**: dropdown chọn kịch bản, nút play/pause/restart, slider tốc độ, progress bar | Component hoạt động | `[MVP]` |
| **Bảng flow trực tiếp**: nhận flow qua WebSocket, append theo thời gian, cột Truth và Prediction cạnh nhau, confidence, tô màu theo class | Component bảng | `[MVP]` |
| Highlight đỏ các dòng dự đoán sai (FP/FN), gắn nhãn rõ | Logic highlight | `[MVP]` |
| **Panel metrics real-time**: Accuracy, Precision, Recall, F1 cập nhật khi flow chạy | Component metric cards | `[MVP]` |
| **Confusion matrix động**: heatmap cập nhật real-time | Component heatmap | `[MVP]` |
| **Panel explainability**: click vào flow → gọi `/explain`, hiển thị feature importance | Component + modal | `[+]` |
| **Đồ thị topology mạng** animate src→dst, node đỏ khi bị tấn công (eye candy) | Component đồ thị | `[+]` |
| Bộ đếm FP/FN nổi bật + nút export/chụp metric cho slide | Tiện ích phụ | `[+]` |

---

## Giai đoạn 3 — Tích hợp, kiểm thử & polish (≈2 ngày)

| Task | Deliverable | Ưu tiên |
|------|-------------|---------|
| Chạy end-to-end từng kịch bản, kiểm tra metric khớp với kết quả offline của model | Báo cáo kiểm thử | `[MVP]` |
| Xử lý edge case: file rỗng, mất kết nối WebSocket, model lỗi trên flow lạ | Code phòng thủ | `[MVP]` |
| Tinh chỉnh tốc độ replay sao cho người xem kịp đọc nhưng không quá chậm | Cấu hình tốc độ mặc định | `[MVP]` |
| Thống nhất bảng màu theo class (benign/DoS/brute force/web/portscan) nhất quán toàn UI | Palette cố định | `[MVP]` |
| Responsive cơ bản để chiếu trên màn hình lớn / máy chiếu | UI ổn định | `[+]` |

---

## Giai đoạn 4 — Chuẩn bị bảo vệ (≈1 ngày)

| Task | Deliverable | Ưu tiên |
|------|-------------|---------|
| Tập dượt kịch bản demo: mở app → chọn DoS → chạy chậm → chỉ ra flow bị bắt → mở confusion matrix → giải thích một dự đoán | Kịch bản trình bày | `[MVP]` |
| Chuẩn bị **phương án dự phòng**: video screen-record toàn bộ demo phòng khi máy/mạng trục trặc | File video | `[MVP]` |
| Chuẩn bị câu trả lời cho các câu hỏi hay gặp (model gì, vì sao FP/FN, dataset, độ trễ thực tế) | Ghi chú Q&A | `[MVP]` |
| Chốt 2 chế độ trình diễn: "chạy nhanh ra metric" và "chạy chậm diễn giải flow" | Demo flow đã chốt | `[MVP]` |

---

## Đường cắt MVP (nếu thiếu thời gian)

Nếu chỉ còn ít thời gian, ưu tiên đủ chuỗi sau để demo vẫn thuyết phục:

1. Chọn kịch bản → play/pause → bảng flow chạy với Truth vs Prediction cạnh nhau.
2. Highlight dòng sai (FP/FN).
3. Metrics real-time (đặc biệt F1) + confusion matrix cuối.

Ba thứ này là cốt lõi để hội đồng tin model. Explainability (SHAP) và topology animation là điểm cộng, không bắt buộc.

---

## Rủi ro & lưu ý

- **SHAP có thể chậm** trên một số model — nếu tính real-time bị lag, hãy tính trước (precompute) cho vài flow mẫu để demo, đừng tính live.
- **Metric phía client phải khớp** với kết quả offline — kiểm tra kỹ cách cộng dồn, dễ sai ở chỗ tính F1 theo macro vs weighted. Chốt một cách và ghi rõ trong báo cáo.
- **Đừng giấu ground truth rồi mới tiết lộ** — luôn để Truth và Prediction song song; minh bạch tạo uy tín tốt hơn với hội đồng.
- **Luôn có video dự phòng** — sự cố kỹ thuật trong buổi bảo vệ là rủi ro lớn nhất và dễ phòng nhất.

---

## Gợi ý phân bổ thời gian (bản 12 ngày)

| Ngày | Việc chính |
|------|-----------|
| 1 | Giai đoạn 0: data contract, chuẩn hóa dữ liệu, test model |
| 2–5 | Giai đoạn 1: backend + replay engine + WebSocket |
| 6–9 | Giai đoạn 2: frontend (ưu tiên các phần `[MVP]` trước) |
| 10–11 | Giai đoạn 3: tích hợp, kiểm thử, polish; thêm `[+]` nếu kịp |
| 12 | Giai đoạn 4: tập dượt, quay video dự phòng, chuẩn bị Q&A |
