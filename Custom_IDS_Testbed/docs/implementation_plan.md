# Kế Hoạch Cập Nhật Toàn Diện: Kiến Trúc 100% WSL & Hybrid IDS

Vì bạn vừa xác nhận **Laptop 1 (Attacker) cũng sử dụng WSL**, đồng thời chúng ta đã chốt mô hình **Hybrid IDS (Snort + CICFlowMeter)** ở bước trước, toàn bộ dự án cần được đập đi xây lại (từ tài liệu đến script) để đồng nhất.

Dưới đây là kế hoạch thay đổi toàn bộ nội dung thư mục `Custom_IDS_Testbed`.

## User Review Required

> [!CAUTION]
> **Giới hạn của WSL Win 10 khi Tấn công:**
> Mặc dù chúng ta đã chuyển Nmap sang chế độ TCP Connect Scan (`-sT`), nhưng vì Laptop 1 dùng WSL trên Windows 10 (nằm sau lớp NAT), một số kỹ thuật quét mạng như **UDP Scan** hay **OS Fingerprinting** vẫn sẽ không tái tạo được chính xác. Dataset bạn tự tạo có thể sẽ thiếu các class này, hoặc các feature liên quan bị méo lệch so với thực tế.

> [!IMPORTANT]
> **Đã xác nhận môi trường:**
> Laptop 1 được xác nhận sử dụng Windows 10. Do đó, các tài liệu hướng dẫn và mã nguồn sẽ được tinh chỉnh xoay quanh giới hạn NAT của WSL trên Win 10.

---

## Proposed Changes / Kiến Trúc Quy Hoạch Mới

### 1. Cập Nhật Sơ Đồ Mạng (Topology)
- **Attacker (Máy 1):** Windows Host 1 -> WSL (Chạy `auto_attack.py` và `auto_benign.py`).
- **Mạng truyền dẫn:** Mạng WiFi LAN nội bộ nối 2 Laptop.
- **Victim & Sensor (Máy 2):** Windows Host 2 (Windows 11) -> WSL (Chạy Docker Victim, Snort, CICFlowMeter). 

### 2. Sửa Đổi Các File Tài Liệu (Docs)
#### [MODIFY] [walkthrough.md](file:///home/ning/Graduation-Thesis/Custom_IDS_Testbed/docs/walkthrough.md)
Xóa bỏ hoàn toàn quy trình liên quan đến Wireshark. Thay thế bằng hướng dẫn chuẩn bị môi trường WSL cho cả 2 máy. Hướng dẫn cách bật Snort và CICFlowMeter trên Máy 2, sau đó chạy script trên Máy 1.

#### [MODIFY] [hybrid_ids_architecture.md](file:///home/ning/Graduation-Thesis/Custom_IDS_Testbed/docs/hybrid_ids_architecture.md)
Vẽ lại sơ đồ luồng dữ liệu Mermaid, thể hiện rõ đường đi của gói tin từ WSL (Laptop 1) -> Card WiFi vật lý -> WSL (Laptop 2).

#### [MODIFY] [implementation_plan.md](file:///home/ning/Graduation-Thesis/Custom_IDS_Testbed/docs/implementation_plan.md)
Xóa bỏ bản kế hoạch cũ, phản ánh kế hoạch kiến trúc 100% WSL này.

#### [MODIFY] [task.md](file:///home/ning/Graduation-Thesis/Custom_IDS_Testbed/docs/task.md)
Reset lại Task list cho quy trình thiết lập WSL mới.

### 3. Sửa Đổi Mã Nguồn (Scripts)
#### [MODIFY] [auto_attack.py](file:///home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/auto_attack.py)
Cập nhật các command tấn công đảm bảo tương thích hoàn toàn với môi trường WSL (ví dụ: dùng Nmap Connect Scan `-sT` thay vì SYN Scan `-sS` để tránh lỗi raw socket của WSL mặc định).

#### [MODIFY] [hybrid_ml_backend_example.py](file:///home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts/hybrid_ml_backend_example.py)
Chỉnh sửa logic đọc luồng để hiển thị cảnh báo từ IP vật lý của Laptop 1.

---

## Verification Plan

Sau khi tôi sửa lại toàn bộ file, bạn sẽ kiểm chứng bằng cách:
1. Đọc lại `walkthrough.md` để thấy quy trình đã thay đổi hoàn toàn (không còn Wireshark, có WSL cho máy 1).
2. Chạy thử `auto_attack.py` trên Laptop 1 WSL để xem có bắn được traffic xuyên qua WiFi sang Laptop 2 WSL hay không.
