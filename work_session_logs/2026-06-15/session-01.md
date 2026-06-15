# Báo cáo Nhật ký Công việc Chi tiết: Ngày 15 Tháng 06, 2026 (Phiên bản Model V3.1)

Phiên làm việc ngày hôm nay là một bước ngoặt cực kỳ quan trọng đối với dự án. Dưới sự tư vấn chuyên sâu về các giới hạn thực tế của học máy, toàn bộ Data Pipeline và kiến trúc AI đã bị mổ xẻ và xây dựng lại để loại bỏ hoàn toàn tình trạng "Học Vẹt" (Memorization/Data Leakage). 

Dưới đây là thống kê chi tiết **từng dòng code thay đổi và tác động dây chuyền** của chúng lên toàn bộ hệ thống:

---

## 1. Loại bỏ Rò rỉ Dữ liệu (Fixing Data Leakage)
### Sự thay đổi (What Changed?)
- **File tác động**: `cic_data_processor.py`
- **Chi tiết**: Viết thêm logic chặn đứng dòng dữ liệu đầu vào. Tự động tìm và drop 2 cột `Destination_Port` (Cổng đích) và `Fwd_Header_Length.1` (Cột lỗi trùng lặp của dataset gốc).

### Tác động & Hậu quả (Impacts & Side Effects)
- **Tác động tới AI**: Mất đi cột `Destination_Port`, mô hình bị mù hoàn toàn về khái niệm cổng mạng. Nếu trước đây nó gian lận bằng cách nhìn thấy luồng mạng nhắm vào Port 80 là auto chốt "Web Attack", thì bây giờ nó mất "phao cứu sinh".
- **Hệ quả đo lường**: Điểm Precision của lớp `Web Attack` và `Rare Attacks` tụt dốc không phanh xuống mức cực thấp (0.05 - 0.07). Tuy nhiên, đây là sự tụt giảm **cần thiết và trung thực**. Nó chứng minh rằng trên không gian phân tích Flow (Lớp Mạng/Giao vận) đơn thuần mà không có Data Payload tầng Ứng dụng, một cuộc tấn công Web Attack trông y hệt một luồng tải trang web (Benign) bình thường.

## 2. Phục hồi 7 Lớp Tấn công nguyên thuỷ (Fixing the Mapping Bug)
### Sự thay đổi (What Changed?)
- **File tác động**: `cic_data_processor.py`
- **Chi tiết**: Sửa lại từ điển (dictionary) `mapping`. Khắc phục lỗi thiếu sót key `'Web Attack'` sau khi chạy hàm Regex dọn ký tự Unicode rác. Đưa dữ liệu từ nhóm 6 Class trở về đúng 7 Class.

### Tác động & Hậu quả (Impacts & Side Effects)
- **Tác động tới Dữ liệu**: Lớp `Web Attack` (khoảng 2,180 mẫu) được hồi sinh, không còn bị đổ oan vào rổ `Rare Attacks` nữa. Tập Training hiện nay đã sạch và mang ý nghĩa thống kê chuẩn.
- **Hệ quả quá trình SMOTE**: Tại pha huấn luyện, thuật toán SMOTE của `phase2_train_v3.py` nhìn thấy thêm lớp `Web Attack` (vốn chỉ có >200 mẫu trong 300,000 dòng Train). SMOTE lập tức bơm thêm **49,700 mẫu dữ liệu nhân tạo** cho Web Attack, khiến nó tăng lên đủ 50,000 mẫu bằng với các lớp khác. Sự bùng nổ dữ liệu nhân tạo này làm gia tăng sự chồng lấn không gian của các mẫu (Overlap), giải thích lý do tại sao Macro-F1 lại có biến động mạnh.

## 3. Tối ưu lấy mẫu chống Tràn RAM (NumPy Stratified Sampling)
### Sự thay đổi (What Changed?)
- **File tác động**: `cic_data_processor.py`
- **Chi tiết**: Thay đổi hàm cắt dữ liệu ngẫu nhiên cũ. Xóa bỏ hoàn toàn hàm `df.groupby('Label')` của Pandas (nguyên nhân gây Crash OOM Exit Code 137 trên bộ nhớ 4GB RAM). Viết lại hoàn toàn bằng thuần mảng NumPy (`np.where` và `np.unique`).

### Tác động & Hậu quả (Impacts & Side Effects)
- **Tác động tới Bộ nhớ**: Quá trình chia 2.8 triệu dòng dữ liệu giờ đây cực kỳ trơn tru, không ăn lố một MB RAM nào. Không còn hiện tượng Crash tiến trình.
- **Tác động tới Dữ liệu**: 300,000 dòng dữ liệu của tập `cic_train_chunk.csv` giờ đây được phân bổ **chuẩn tỉ lệ vàng** của tập 2.8 triệu dòng gốc (Stratified). Những lớp cực hiếm như Heartbleed/Infiltration (nay là Rare Attacks) được bảo toàn không trượt một mẫu nào. Mô hình lần đầu tiên được chiêm ngưỡng bức tranh phân bố chính xác nhất.

## 4. Bù trừ và Tập trung (Epochs & Focal Loss)
### Sự thay đổi (What Changed?)
- **File tác động**: `phase2_train_v3.py`
- **Chi tiết**: Nâng số lượng `NUM_EPOCHS` từ 10 lên 15. Tiếp tục giữ cường độ phạt mạnh của Focal Loss (`gamma=2.0`).

### Tác động & Hậu quả (Impacts & Side Effects)
- Nhờ thêm thời gian (15 Epochs thay vì 10), Model đã kịp hội tụ được lớp `Brute Force` (F1 đạt 0.6074) dù đã mất đi thông tin Port (vốn Brute Force FTP/SSH rất hay dùng các port cố định).
- Độ chính xác cực kì đáng sợ: Các lớp truyền thống như **DDoS, DoS, PortScan, Benign** đều đạt F1 từ **91% đến 98%**, cho thấy sức mạnh của kiến trúc FT-Transformer không hề bị phai nhạt đối với các cuộc tấn công gây rối loạn mạng (Traffic anomalies).

---

## TỔNG KẾT BÀI TOÁN & GIẢI PHÁP TIẾP THEO
Việc cởi bỏ "kính lúp" `Destination_Port` đã khiến AI lộ rõ điểm yếu trí mạng của dòng IDS phân tích Luồng (Flow-based Analysis) đối với những cuộc tấn công có kỹ năng ngụy trang tầng Ứng dụng (L7) như Web Attack hay Slowloris.

Thay vì cố gắng "ép" một con AI phải hoàn hảo 100% bằng cách nhồi lại các feature gây Data Leakage, chúng ta đã chốt giải pháp **Kiến trúc phòng thủ chiều sâu (Defense-in-depth)**:
1. **Snort làm khiên trước**: Snort sẽ dùng chữ ký để bắt gọn các cuộc lướt Port / Web Attack.
2. **AI làm màng lọc dị thường**: AI chỉ phán đoán các Flow. Do Precision của AI đối với lớp ẩn nấp đang thấp (dễ sinh False Positives), ta dùng màng lọc thứ 3.
3. **Sliding Window Cửa Sổ Trượt**: Nếu AI la lên "ĐÂY LÀ WEB ATTACK" chỉ với 1 gói tin, ta lờ nó đi. Nhưng nếu AI la lên **X lần trong Y phút từ cùng 1 IP**, Backend mới chính thức phong toả (Alert).

Chỉ có kiến trúc đa tầng (Hybrid) như vậy mới thực sự biến đồ án này thành một sản phẩm có thể thương mại và áp dụng thực tiễn cho doanh nghiệp. Mọi hiện vật huấn luyện (`best_model_v3_ema.pt`, `cic_scaler.pkl`) đã được chốt hạ và chờ ngày được cấy vào Backend.
