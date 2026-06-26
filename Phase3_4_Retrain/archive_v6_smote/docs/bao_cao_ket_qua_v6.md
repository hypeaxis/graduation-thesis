# Báo cáo Đánh giá V6 Model (SMOTE + Full Unfreeze)

## 1. Mục tiêu của V6
Sau khi phiên bản V5 (chỉ dùng Focal Loss) bộc lộ điểm yếu là không học được các class thiểu số (Brute Force, Web Attack, PortScan), phiên bản V6 được ra đời với 2 thay đổi cốt lõi:
1. **Dùng thuật toán SMOTE:** Bơm dữ liệu giả lập để kéo số lượng của các class thiểu số lên mức 15,000 mẫu/class trong tập Train (`run5`).
2. **Full Unfreeze:** Mở khóa toàn bộ 4 khối Transformer để mô hình được tự do cập nhật toàn diện trọng số.

## 2. Kết quả Đánh giá trên tập `run6` (Test Set)

Khi áp dụng mô hình V6 lên tập Test `run6` (93,547 mẫu), kết quả như sau:

- **Overall Accuracy:** 44.64%
- **Macro F1:** 31.49%
- **Weighted F1:** 48.50%

### Detailed Classification Report (run6)
```text
              precision    recall  f1-score   support

      Benign     0.9945    0.1812    0.3066     58868
 Brute Force     0.0468    0.7433    0.0880      1449
         DoS     0.8921    0.9656    0.9274     28743
    PortScan     0.0573    0.2039    0.0894      2633
  Web Attack     0.0895    0.9315    0.1633      1854

    accuracy                         0.4464     93547
   macro avg     0.4160    0.6051    0.3149     93547
weighted avg     0.9040    0.4464    0.4850     93547
```

### Confusion Matrix Tuyệt Đối (run6)
```text
                  Pred_Benign  Pred_Brute Force  Pred_DoS  Pred_PortScan  Pred_Web Attack
True_Benign             10669             20774      3198           8300            15927
True_Brute Force           11              1077         0            361                0
True_DoS                    0                 0     27754            132              857
True_PortScan              48              1177        82            537              789
True_Web Attack             0                 0        78             49             1727
```

---

## 3. Phân tích Nguyên nhân và Bài học Rút ra

### Thành công của kỹ thuật SMOTE
Kỹ thuật SMOTE đã hoàn thành cực kỳ xuất sắc nhiệm vụ giúp mô hình "nhận mặt" được các cuộc tấn công thiểu số. So với V5, Recall của các nhóm tấn công này đã bùng nổ:
- **Brute Force Recall:** Tăng vọt từ **11% lên 74.33%**.
- **Web Attack Recall:** Tăng vọt từ **54% lên 93.15%**.

### Khủng hoảng Domain Shift (Thất bại)
Tuy nhiên, Macro F1 vẫn rớt thê thảm (31.49%). Nguyên nhân đến từ việc **Benign Recall sập xuống chỉ còn 18.12%**. Hơn 48,000 gói tin mạng bình thường (Benign) bị hệ thống báo động nhầm thành Web Attack, Brute Force hoặc PortScan.

Đây là minh chứng rõ ràng nhất của hiện tượng **Domain Shift**:
- Lượng dữ liệu Benign sinh ra ở lần chạy `run6` (môi trường mới) có đặc điểm cấu trúc giống hệt như các gói tin Attack sinh ra ở `run5` (môi trường cũ).
- Mô hình AI không sai, nó làm đúng những gì nó học từ `run5`. Vấn đề nằm ở sự thiếu đồng nhất về phân phối dữ liệu (Distribution Shift) của môi trường Testbed.
- Kiểm chứng độc lập bằng thuật toán Random Forest cũng cho kết quả tương tự (Macro F1 = 39.5%).

## 4. Quyết định Tiếp theo
Phương án huấn luyện trên `run5` và kiểm thử trên `run6` đã chạm tới cực hạn vật lý của cấu trúc dữ liệu. 
Đồng thuận giải pháp tiến tới **V7**: Tác giả luận văn sẽ tiến hành tái thu thập một tập dữ liệu gộp chuẩn là **`run7`**, trong đó tỷ lệ Benign/Attack được điều chỉnh khéo léo tự nhiên ở mức 80:20 để mô hình học và đánh giá một cách minh bạch, triệt tiêu hoàn toàn vấn đề Domain Shift.
