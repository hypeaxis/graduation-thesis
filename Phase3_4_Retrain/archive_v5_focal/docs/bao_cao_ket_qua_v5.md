# Báo cáo Đánh giá V5 Model và Phân tích Lỗi

## 1. Kết quả Threshold Calibration (trên `run5` validation)

| Metric | Giá trị |
|--------|---------|
| Ngưỡng tối ưu (Benign) | **0.76** |
| Malicious Recall | **99.20%** |
| Benign Recall | **96.42%** |
| False Positive Rate (FPR) | **3.58%** |

*Nhận xét:* Trên chính tập dữ liệu cùng phân phối với tập Train (run5), mô hình đã đạt được mức cân bằng xuất sắc. Trọng số Focal Loss đã phát huy tác dụng cực tốt.

## 2. Kết quả Đánh giá Chính thức (trên `run6` test set)

Khi mang mô hình v5 áp dụng vào thực tế trên tập `run6`, kết quả bị sụt giảm nghiêm trọng:

- **Overall Accuracy:** 76.11%
- **Macro F1:** 38.90%
- **Weighted F1:** 78.69%
- **Binary F1 (Attack vs Benign):** ~75.1%

### Detailed Classification Report (run6)
```text
              precision    recall  f1-score   support

      Benign     0.9206    0.7136    0.8040     58868
 Brute Force     0.0644    0.1118    0.0818      1449
         DoS     0.8355    0.9741    0.8995     28743
    PortScan     0.4211    0.0061    0.0120      2633
  Web Attack     0.0856    0.5469    0.1480      1854

    accuracy                         0.7611     93547
   macro avg     0.4654    0.4705    0.3890     93547
weighted avg     0.8506    0.7611    0.7869     93547
```

### Confusion Matrix Tuyệt Đối (run6)
```text
                  Pred_Benign  Pred_Brute Force  Pred_DoS  Pred_PortScan  Pred_Web Attack
True_Benign             42009              2088      4913             20             9838
True_Brute Force         1285               162         0              2                0
True_DoS                  261                 0     27999              0              483
True_PortScan            1606               264       231             16              516
True_Web Attack           473                 0       367              0             1014
```

**KẾT LUẬN:** Mục tiêu Macro F1 > 90% đã THẤT BẠI. 
Nguyên nhân chính đến từ sự sụp đổ của các class thiểu số (Brute Force, PortScan, Web Attack) và sự xuất hiện của **Domain Shift** (khác biệt hành vi) của luồng Benign giữa `run5` và `run6`.

---

## 3. Chẩn đoán Nguyên nhân Thất bại

### A. Vấn đề mất cân bằng cực đoan trong từng Batch
Tập `run5` có 111,426 mẫu, nhưng Brute Force chỉ có 628 mẫu (0.5%), Web Attack 271 mẫu (0.2%).
Với Batch Size = 256, trung bình một batch mô hình chỉ nhìn thấy **chưa tới 1 mẫu Web Attack hoặc Brute Force**. Dù Focal Loss có phạt nặng đến đâu, tín hiệu gradient từ 1 mẫu là quá nhiễu (noisy) để mô hình có thể học được đặc trưng tổng quát.
→ Dẫn tới Recall của PortScan trên `run6` chỉ đạt 0.6%, Brute Force đạt 11%.

### B. Vấn đề Domain Shift & "Đóng băng" (Freeze) quá nhiều
Trong file `4c_retrain_focal_v5.py`, chúng ta đã đóng băng (freeze) 77 features và **2 khối Transformer Block đầu tiên** (chỉ train 2 block cuối). Kỹ thuật này phù hợp nếu dữ liệu Testbed gần giống CIC-IDS-2017. 
Nhưng thực tế, hành vi mạng của `run6` khác biệt rất lớn so với `run5` (Benign Recall tụt từ 96% xuống 71%). Việc khóa cứng các lớp sâu của Transformer khiến mô hình không đủ độ linh hoạt để thích nghi với môi trường mạng mới.

---

## 4. Kế hoạch Khắc phục Đề xuất (Hướng tới >90% F1)

Để xử lý triệt để 2 vấn đề trên, đề xuất chạy lại một phiên bản **V6** với 2 sự thay đổi quyết định:

1. **Sử dụng SMOTE (Synthetic Minority Over-sampling Technique):**
   - Trước khi đưa vào huấn luyện, dùng SMOTE bơm các class thiểu số (Brute Force, PortScan, Web Attack) lên mức an toàn để mô hình học được đặc trưng (VD: 15,000 mẫu/class).
   - Đảm bảo mỗi Batch đều chứa lượng dữ liệu đủ lớn để mô hình học được pattern tấn công.

2. **Unfreeze toàn bộ Transformer (Full Fine-tuning):**
   - Mở khóa toàn bộ 4 khối Transformer để mô hình được tự do cập nhật toàn diện bộ trọng số (Weights) theo đúng phân phối của dữ liệu Testbed. Không đóng băng nữa.
