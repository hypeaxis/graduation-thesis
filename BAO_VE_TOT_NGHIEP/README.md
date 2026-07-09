# BỘ TÀI LIỆU BẢO VỆ TỐT NGHIỆP — TỔNG HỢP

**Đề tài:** Phát triển hệ thống phát hiện tấn công mạng bằng phát hiện bất thường
*(Cách tiếp cận kỹ thuật: lai ghép Snort + FT-Transformer)*

**Sinh viên:** Đỗ Tuấn Minh — MSSV **20225741** — Lớp **Việt Nhật 07**, **Trường Công nghệ Thông tin và Truyền thông**
**GVHD:** PGS.TS. Nguyễn Linh Giang

> Folder này gom **toàn bộ** tài liệu cần cho buổi bảo vệ vào một nơi: slide, hướng dẫn làm slide, kịch bản nói, ôn lý thuyết, và chuẩn bị phản biện. Các file `.md` liên kết chéo nhau bằng tên file → **giữ nguyên cùng cấp**, đừng đổi tên hay tách vào thư mục con.

---

## 1. Có gì trong folder này

| File | Là gì | Khi nào dùng |
|---|---|---|
| **`Slide_Bao_Ve_HUST.pptx`** | Bộ slide bảo vệ (18 slide chính + phụ lục), template HUST 4×3 | Trình chiếu khi bảo vệ |
| **`GUIDELINE_SLIDE_BAO_VE.md`** | Ràng buộc + khung 18 slide + ánh xạ hình → slide | Đọc khi cần hiểu *vì sao* slide bố cục vậy |
| **`THIET_KE_SLIDE_TUNG_SLIDE.md`** | Thiết kế chi tiết từng slide (layout, màu, nội dung on-slide) | Khi chỉnh sửa slide |
| **`KICH_BAN_THUYET_TRINH.md`** | **Lời nói** từng slide (~13 phút) + Q&A + checklist | **Học thuộc ý để tập nói** |
| **`TONG_HOP_LY_THUYET.md`** | Toàn bộ nền tảng lý thuyết dùng trong đồ án (công thức + vai trò) | Tra cứu sâu khi ôn |
| **`CHUAN_BI_PHAN_BIEN.md`** | **Chuẩn bị riêng cho cô phản biện**: chiến lược + phao lý thuyết + Q&A | **Đọc kỹ nhất — trọng tâm "nắm kĩ lý thuyết"** |
| **`CAN_LAM_THEM_VA_CHINH_SUA.md`** | Bảng theo dõi việc còn phải làm cho bộ slide | Rà trước khi nộp/bảo vệ |
| **`fig_theory_linkage.png`** | Sơ đồ liên kết lý thuyết (hình phụ trợ, tuỳ chọn cho Slide 6/phụ lục) | Nếu muốn chèn thêm |
| **`mau_tham_khao_HUST/`** | 2 file hướng dẫn làm slide bảo vệ chính thức của HUST | Tham khảo chuẩn trường |

---

## 2. Thứ tự đọc/chuẩn bị đề xuất

1. **`CHUAN_BI_PHAN_BIEN.md`** — nắm chiến lược cho cô phản biện + học phao lý thuyết (Nhóm 1 & 2 phải nói được mà không nhìn slide).
2. **`KICH_BAN_THUYET_TRINH.md`** — tập nói theo lời từng slide, bấm giờ ≤ 15 phút (mục tiêu ~13).
3. **`Slide_Bao_Ve_HUST.pptx`** — mở PowerPoint soát mắt thường 1 lượt (font, tràn viền), điền nốt phần còn trống (mục 3).
4. **`TONG_HOP_LY_THUYET.md`** — tra sâu khi gặp khái niệm chưa chắc.
5. **`CAN_LAM_THEM_VA_CHINH_SUA.md`** — checklist cuối trước khi nộp.

---

## 3. Trạng thái điền slide (cập nhật)

**Đã điền:** tên đề tài · Sinh viên (Đỗ Tuấn Minh, 20225741) · Lớp/Trường · GVHD (PGS.TS. Nguyễn Linh Giang) · khung "phát hiện bất thường" ở Slide 3 & 7.

**Còn phải làm (xem chi tiết trong `CAN_LAM_THEM_VA_CHINH_SUA.md`):**
- [ ] **Slide 1 bìa:** điền `Hà Nội, [tháng] / [năm]` khi có lịch bảo vệ.
- [ ] **Slide 18 cảm ơn:** thay `[email/liên hệ]` (tuỳ chọn).
- [ ] **Slide 15 demo:** chụp & chèn ảnh màn hình `dashboard.html` chạy kịch bản "dos".
- [ ] Mở PowerPoint soát mắt thường (font tiếng Việt, không tràn viền/đè footer).
- [ ] Bấm giờ tập nói ≥ 2 lần.

---

## 4. Ghi nhớ khi bảo vệ (rút gọn)

- **Với cô phản biện:** thắng bằng **sự mạch lạc**, không bằng sự phức tạp. Mỗi con số kèm một câu *"nghĩa là gì"*. Không giải thích code.
- **Câu ⭐ khả năng cao nhất:** *"Đề tài tên 'phát hiện bất thường' — model có phải anomaly detection không?"* → trả lời: là **triết lý phát hiện** (tách bình thường/bất thường → định danh) + **Autoencoder ở GĐ1**; **không** claim cả hệ thống là học không giám sát (bộ phân loại cuối là có giám sát). Chi tiết trong `CHUAN_BI_PHAN_BIEN.md` và `KICH_BAN_THUYET_TRINH.md`.
- **Demo = replay ≠ live:** nói rõ ngay khi chiếu Slide 15.

---

## 5. Nguồn & cập nhật

- Đây là **bản tổng hợp (copy)**. **Nguồn dựng slide** — script `build_deck.py` + các template HUST — vẫn nằm ở thư mục **`slide đồ án/`** của repo (script gắn với layout repo để lấy hình từ `Noi_dung_do_an/.../figures`).
- Nếu **chỉnh nội dung slide**: sửa `build_deck.py` trong `slide đồ án/` rồi build lại, sau đó copy `Slide_Bao_Ve_HUST.pptx` mới sang đây (hoặc điền trực tiếp trong PowerPoint bản ở folder này).
- Nếu muốn biến folder này thành **nơi canonical duy nhất** (không giữ bản ở `slide đồ án/` nữa) → báo để chỉnh đường dẫn output của `build_deck.py` trỏ thẳng vào đây.
