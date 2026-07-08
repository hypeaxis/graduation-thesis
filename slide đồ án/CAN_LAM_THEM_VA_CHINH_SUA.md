# VIỆC CẦN LÀM THÊM & CHỈNH SỬA — Slide bảo vệ

> Tổng hợp mọi việc còn lại cho bộ slide `Slide_Bao_Ve_HUST.pptx`. File này sinh tự động bằng `build_deck.py` từ template `HUST_PPT_template_2022_blue_4x3.pptx`.
>
> Tài liệu liên quan: [THIET_KE_SLIDE_TUNG_SLIDE.md](THIET_KE_SLIDE_TUNG_SLIDE.md) (thiết kế) · [KICH_BAN_THUYET_TRINH.md](KICH_BAN_THUYET_TRINH.md) (lời nói) · [GUIDELINE_SLIDE_BAO_VE.md](GUIDELINE_SLIDE_BAO_VE.md) (ràng buộc).

---

## A. BẮT BUỘC điền — placeholder đang để trống `[…]`

| Slide | Vị trí | Nội dung cần điền |
|---|---|---|
| **S1 — Bìa** | Khối giữa/dưới | Họ tên · MSSV · Lớp/Viện · GVHD (học hàm học vị + họ tên) · tháng/năm bảo vệ |
| **S15 — Demo** | Khung xám giữa slide | **Ảnh chụp màn hình** `Final/05_Replay_Detection/dashboard.html` đang chạy kịch bản "dos" |
| **S18 — Cảm ơn** | Dòng dưới | Họ tên + email/liên hệ |

> Cách điền: có thể sửa trực tiếp trong PowerPoint, HOẶC sửa các chuỗi `[…]` trong `build_deck.py` rồi chạy lại (xem Mục E).

---

## B. BẮT BUỘC làm — chưa tự động hoá được

- [ ] **Xem trực quan trong PowerPoint.** Bản dựng mới chỉ được kiểm tra bằng toạ độ/ước lượng (không tràn viền, không đè footer, không tràn chữ). **Chưa render ảnh** vì máy không có LibreOffice → cần mở mắt thường soát 1 lượt.
- [ ] **Chụp & chèn ảnh dashboard cho S15** (xem Mục A). Trước khi chụp, chạy dashboard theo hướng dẫn trong `Final/05_Replay_Detection/`.
- [ ] **Kiểm tra font tiếng Việt** hiển thị đúng dấu trên máy trình chiếu (slide dùng Calibri — có sẵn trên Windows; nếu trình chiếu máy khác, nhúng font: *File → Options → Save → Embed fonts in the file*).
- [ ] **Bấm giờ tập nói ≥ 2 lần**, mục tiêu ~13 phút, trần 15 phút (kịch bản ở `KICH_BAN_THUYET_TRINH.md`).

---

## C. NÊN chỉnh — nâng chất lượng (tuỳ chọn)

- [ ] **S6 & S8 (sơ đồ khối):** sơ đồ hiện vẽ bằng shape cơ bản. Nếu muốn đẹp hơn, thay bằng SmartArt hoặc vẽ lại trong PowerPoint cho canh lề mượt.
- [ ] **S4 (3 thách thức):** cân nhắc thêm hình `fig_cic_imbalance.png` bên phải nếu thấy slide trống (hiện đang ưu tiên 3 thẻ số cho gọn).
- [ ] **Màu 3 giai đoạn:** đang dùng xám (GĐ1) · xanh (GĐ2) · cam (GĐ3). Nếu trường yêu cầu bảng màu khác, sửa `GRAY/S2COL/S3COL` trong `build_deck.py`.
- [ ] **Hiệu ứng chuyển/animation:** bản sinh tự động không có animation. Thêm tay trong PowerPoint nếu cần (đừng lạm dụng — hội đồng ưu tiên nội dung).
- [ ] **Đánh số trang:** template có placeholder số trang; bật qua *Insert → Header & Footer → Slide number* nếu chưa hiện.
- [ ] **Logo Viện/Khoa** (nếu có yêu cầu riêng): chèn thêm ở S1.

---

## D. KIỂM TRA trước khi nộp (đối chiếu guideline)

- [ ] Đúng template HUST 4×3, logo/màu trường giữ nguyên.
- [ ] 18 slide chính + phụ lục tách riêng (bản dựng: 18 chính + 3 phụ lục = 21).
- [ ] Mỗi slide ≤ 6 dòng; không có đoạn văn copy nguyên từ báo cáo.
- [ ] Mọi từ viết tắt nói được: NIDS, FTT, HNM, MCC, WSL2, NAT, IAT, AE Gate.
- [ ] Không từ tuyệt đối ("nhất", "triệt để").
- [ ] **S15 ghi rõ REPLAY ≠ LIVE**; `live_detection` chỉ xuất hiện ở S17 (hướng phát triển).
- [ ] Số liệu khớp báo cáo: 0,6809 · 0,9294 / 99,55% · 21,93% / −0,015 · 6,87% · 91,7% / 91,1% / 0,865 · 65.000:1.
- [ ] **0 lỗi chính tả**, đặc biệt tên đề tài & tên GVHD ở S1.
- [ ] Chuẩn bị trả lời 9 câu hỏi Q&A (cuối `KICH_BAN_THUYET_TRINH.md`).

---

## E. Cách sinh lại / chỉnh sửa file slide bằng script

```bash
cd "<repo>"
source .venv/bin/activate           # cần: pip install python-pptx Pillow
python "slide đồ án/build_deck.py"   # → ghi đè slide đồ án/Slide_Bao_Ve_HUST.pptx
```

- Script **portable**: tự suy ra thư mục repo từ vị trí file, chạy được trên máy khác.
- Sửa nội dung slide = sửa trực tiếp trong `build_deck.py` (mỗi slide là một khối `# ===== SLIDE n =====`).
- ⚠️ Chạy lại script sẽ **ghi đè** `Slide_Bao_Ve_HUST.pptx` → nếu đã chỉnh tay trong PowerPoint, sao lưu trước hoặc chuyển hẳn sang chỉnh tay.

---

## F. Trạng thái hiện tại (đã xong)

- [x] Dựng 21 slide từ template chuẩn HUST 4×3, xoá 13 slide demo gốc.
- [x] Chèn 6 hình thật từ `figures/` (S7, S9, S10, S11, S13, P2).
- [x] Sơ đồ khối tự vẽ: pipeline + 3 giai đoạn (S6), Two-Stage (S8), Testbed (S12), thẻ covariate shift (S11).
- [x] Neo guideline: 3 màu giai đoạn, khối "Đạt mục tiêu", bảng bổ sung DoS↔XSS, dải REPLAY ≠ LIVE.
- [x] Kiểm tra tự động: không tràn viền, không đè footer, không tràn chữ; file mở lại hợp lệ (21 slide, 4:3).
</content>
