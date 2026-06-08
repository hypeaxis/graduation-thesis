# Session Log - 2026-06-07 (session-02)

## Goal
- Phase 3: Khắc phục lỗi overfitting trên tập data giả của SMOTE (từ Phase 2).
- Thử nghiệm các phương pháp cải thiện model generalization dựa trên kiến trúc **V1** (baseline tốt nhất) mà không can thiệp bằng Oversampling:
  1. Tăng Regularization (Dropout 0.3, Weight Decay 1e-3).
  2. Data Augmentation dạng nội suy liên tục (Mixup).
  3. Cost-sensitive Learning (tăng Focal Gamma).

## Code Changes
### 1. `run_nslkdd_ft_experiments.py`
Thêm các cấu hình thử nghiệm V3:
- `v3_reg_dropout03_seed62`: Dropout=0.3
- `v3_reg_wd1e3_seed62`: Weight Decay=1e-3
- `v3_mixup02_seed62`: Mixup Alpha=0.2
- `v3_focal_gamma3_seed62`: Focal Gamma=3.0
- `v3_full_reg_seed62`: Mixup 0.2 + Dropout 0.2 + Weight Decay 1e-3 + Gamma 3.0

### 2. `train_ft_transformer_nslkdd.py`
(Các argument `--weight-decay`, `--dropout`, `--mixup-alpha`, `--gamma` đã có sẵn từ các phiên bản trước, không cần sửa đổi thêm).

## Training Status
- Đã khởi động 5 runs dưới background task. Thời lượng 20 epochs/run với Early Stopping (patience=6).
- Kết quả sẽ được so sánh với Baseline V1 (Macro-F1 0.6679).

## Results
Đã hoàn thành 5/5 runs:
| Metric | Baseline V1 | v3_reg_dropout03 | v3_reg_wd1e3 | v3_mixup02 | v3_focal_gamma3 | v3_full_reg |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|
| Accuracy | **0.8005** | 0.7600 | 0.7793 | 0.7656 | 0.7825 | 0.7402 |
| Macro-F1 | **0.6679** | 0.5693 | 0.6317 | 0.5946 | 0.6544 | 0.5596 |
| Best Epoch| 19 | 5 | 4 | 20 | 4 | 3 |

**Phân tích tổng hợp:** 
- `v3_reg_dropout03`: Việc tăng mức Dropout lên 0.3 trên 122 tokens độc lập gây mất mát thông tin quá lớn, làm model underfit trầm trọng và F1 giảm mạnh (0.56).
- `v3_reg_wd1e3`: Tăng L2 Regularization (Weight Decay) lên 1e-3 cũng không mang lại F1 tốt hơn Baseline (giảm xuống 0.63). Weight Decay lớn dường như hạn chế capacity của mô hình, khiến nó không học đủ các patterns phức tạp của dataset.
- `v3_mixup02`: Kỹ thuật Mixup (Alpha=0.2) cho kết quả F1 (0.59) thấp hơn Baseline. Việc nội suy liên tục trên Tabular features rời rạc có thể sinh ra các mẫu dữ liệu không thực tế (out-of-distribution) gây nhiễu cho mô hình.
- `v3_focal_gamma3`: Tăng Focal Gamma lên 3.0 giúp mô hình tập trung mạnh hơn vào các hard samples, cho F1 tương đối cao (0.6544) gần bằng Baseline và hội tụ rất nhanh (ngay epoch 4). Tuy nhiên nó vẫn không thể vượt qua mức 0.6679.
- `v3_full_reg`: Áp dụng đồng thời tất cả các kỹ thuật phạt (Mixup 0.2 + Dropout 0.2 + WD 1e-3 + Gamma 3.0) dẫn đến underfitting nghiêm trọng, F1 tụt rớt xuống mức thấp nhất (0.5596).

**Kết luận Phase 3:**
Việc bổ sung thêm các Regularization mạnh (Dropout cao, Weight Decay, Mixup, hay tăng độ nhạy Cost-sensitive Learning) trên kiến trúc FT-Transformer V1 không mang lại cải thiện F1 nào trên tập test thực tế của NSL-KDD. Lý do cốt lõi vẫn nằm ở việc tập test chứa các loại tấn công zero-day (như `snmpgetattack`, `httptunnel`) hoàn toàn vắng mặt ở tập train. Các kỹ thuật này có thể chống overfit rất tốt trên tập validation, nhưng không cung cấp cho mô hình khả năng "suy diễn luật" cho những kiểu tấn công chưa từng gặp. 

Do đó, **Kiến trúc Baseline V1 (Macro-F1: 0.6679)** vẫn là phương án có điểm số cân bằng tốt nhất tính đến hiện tại.

## Phụ lục: Thử nghiệm thông số CIC-IDS2017
Anh đã yêu cầu chạy thử nghiệm NSL-KDD với các tham số y hệt như mô hình đã train thành công trên CIC-IDS2017 (`v3_cicids_params`):
- **Cấu hình:** Batch Size = 512, Weight Decay = 1e-5, Focal Alpha = 0.25 (hằng số thay vì class-balanced).
- **Kết quả:** 
  - Accuracy: **0.7483**
  - Macro-F1: **0.6124**
  - Best Epoch: **1** *(Bị ngắt sớm ở epoch 4 do cơ chế Overfitting Guard)*

**Đánh giá nhanh:**
Việc bê trực tiếp siêu tham số từ CIC-IDS2017 sang làm F1 giảm mạnh (từ 0.6679 xuống 0.6124). Nguyên nhân chính là việc để `Alpha=0.25` thay vì `class-balanced` khiến mô hình bỏ qua các class thiểu số. Bên cạnh đó, mô hình rơi vào trạng thái Overfit (Overfitting Guard kích hoạt) rất nhanh, một lần nữa khẳng định bài toán NSL-KDD (với zero-day attacks) có hành vi tối ưu hoàn toàn khác với CIC-IDS2017.
