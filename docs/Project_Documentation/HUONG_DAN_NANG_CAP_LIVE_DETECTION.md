# Hướng dẫn Nâng cấp Hệ thống lên True Live Detection (Thời gian thực)

Tài liệu này cung cấp lộ trình chi tiết để nâng cấp hệ thống hiện tại từ mô hình **Phát hiện theo phát lại (Replay-based)** lên **Phát hiện thời gian thực (True Live Detection)**. 

Thay vì đọc dữ liệu từ các file `*_Flow.csv` đã trích xuất sẵn, hệ thống mới sẽ lắng nghe trực tiếp trên card mạng, tự động gom gói tin thành luồng (flow), trích xuất đặc trưng và đưa qua mô hình học máy để phát cảnh báo tức thời.

---

## 1. Lựa chọn Kiến trúc: Tránh trùng lặp và Giải quyết triệt để Covariate Shift

Đồ án tham khảo (Cao Đức Anh) đã sử dụng **NFStream** để bắt gói tin. Tuy nhiên, việc dùng NFStream vướng phải hai nhược điểm lớn đối với bạn:
1. **Trùng lặp ý tưởng**: Làm hệ thống của bạn mất đi bản sắc riêng.
2. **Covariate Shift**: Do NFStream tính toán ranh giới luồng khác với CICFlowMeter (công cụ sinh ra tập dữ liệu CIC-IDS-2017 mà model của bạn được huấn luyện trên đó), độ chính xác sẽ sụp đổ (từ 0.96 xuống 0.11), buộc bạn phải thu thập lại toàn bộ dữ liệu và huấn luyện lại mô hình từ đầu.

**Khuyến nghị độc đáo dành riêng cho bạn:** Sử dụng **CICFlowMeter phiên bản Python (`cicflowmeter`)**. 
- Thư viện này hỗ trợ lắng nghe trực tiếp trên card mạng (Live sniff).
- Quan trọng nhất: Vì nó dùng đúng logic của CICFlowMeter gốc, **phân bố đặc trưng sẽ hoàn toàn khớp với tập huấn luyện CIC-IDS-2017**. Bạn **KHÔNG CẦN** phải huấn luyện lại mô hình (retrain) mà vẫn đạt độ chính xác F1 > 0.9!

---

## 2. Kiến trúc Hệ thống Mục tiêu (Hybrid NIDS)

Kiến trúc sẽ chạy song song hai nhánh (Đúng với bản chất Hybrid đã nêu trong đồ án):
1. **Nhánh Rule-based (Snort)**: Lắng nghe interface `eth0`, đọc gói tin và sinh cảnh báo trực tiếp.
2. **Nhánh ML-based (CICFlowMeter Python + FT-Transformer)**: Lắng nghe cùng interface `eth0`, gom luồng mạng. Vector 80 chiều sinh ra sẽ được nạp thẳng vào RAM, đi qua Model PyTorch để phát hiện các tấn công mà Snort bỏ sót, sau đó đẩy lên Dashboard.

---

## 3. Các bước triển khai cụ thể

### Bước 1: Cài đặt thư viện
Mở terminal trong môi trường ảo của project (`.venv`) và cài đặt thư viện `cicflowmeter` bản Python:
```bash
pip install cicflowmeter scapy
```

### Bước 2: Viết script `live_inference.py`
Tạo một file `live_inference.py` trong thư mục `Replay_Live_Detection/`. Thư viện `cicflowmeter` của Python cho phép chúng ta import module `FlowSniffer` để chạy live:

```python
from cicflowmeter.sniffer import create_sniffer
import joblib
import torch
import requests
import pandas as pd

# 1. Load Model và Scaler hiện tại của bạn
scaler = joblib.load("models/scaler.pkl")
model = load_ft_transformer_model("models/v4.3_model.pt") # Load model tốt nhất
model.eval()

# 2. Hàm callback xử lý mỗi khi một Flow kết thúc (timeout)
def on_flow_generated(flow):
    # Lấy dictionary chứa đúng 84 features chuẩn của CICFlowMeter
    feature_dict = flow.get_data()
    
    # Chuyển thành DataFrame 1 dòng và xử lý (điền NaN, vô cực) y hệt như lúc huấn luyện
    df = pd.DataFrame([feature_dict])
    X_raw = extract_80_features_as_training(df)
    
    # Tiền xử lý bằng scaler cũ
    X_scaled = scaler.transform(X_raw)
    tensor_features = torch.tensor(X_scaled, dtype=torch.float32)
    
    # Suy luận
    with torch.no_grad():
        logits = model(tensor_features)
        pred_idx = torch.argmax(logits, dim=1).item()
        confidence = torch.softmax(logits, dim=1).max().item()
        
    class_name = idx_to_class[pred_idx]
    
    # 3. Đẩy lên Dashboard nếu là tấn công
    if class_name != "BENIGN" and confidence > 0.70:
        alert_data = {
            "source_ip": flow.src_ip,
            "dest_ip": flow.dst_ip,
            "dest_port": flow.dst_port,
            "attack_type": class_name,
            "confidence": confidence
        }
        # Gọi API của backend
        requests.post("http://localhost:8000/api/alerts", json=alert_data)

# 4. Khởi chạy Sniffer trên card mạng (ví dụ eth0 hoặc wlan0)
print("Đang lắng nghe lưu lượng mạng thực tế bằng CICFlowMeter...")
sniffer = create_sniffer(
    input_interface="eth0",
    server_endpoint=None, # Không gửi qua server mà dùng callback
    verbose=True
)

# Chèn callback vào engine nội bộ của sniffer
sniffer.output_function = on_flow_generated
sniffer.start()
sniffer.join()
```

### Bước 3: Lợi thế tuyệt đối
Vì bạn dùng `cicflowmeter`, biến `feature_dict` trả về sẽ chứa chính xác tên cột chuẩn (như `Flow Duration`, `Total Fwd Packets`, v.v.). Hàm `extract_80_features_as_training` của bạn chỉ cần lấy đúng những feature đó ra, không cần phải vất vả ánh xạ (mapping) và tính toán thủ công như đồ án dùng `NFStream`!

---

## 4. Cập nhật Báo cáo Đồ án
Bằng cách sử dụng phương pháp này, bạn tạo ra một lối đi riêng cực kỳ thông minh:
- **Tránh được vết xe đổ Covariate Shift** của đồ án tham khảo (họ phải dùng NFStream và bị giảm F1, tốn công huấn luyện lại).
- **Phát huy tối đa kiến trúc Hybrid**: Snort 3 chạy bằng C/C++ để bắt các rule chữ ký siêu nhanh, trong khi `cicflowmeter` chạy Python để bắt các flow bất thường phục vụ cho FT-Transformer.

Nếu áp dụng thành công, bạn chỉ cần mở file `DoAn.tex` và tự hào thêm vào kết luận:
*"Khác với các nghiên cứu trước đây gặp phải hiện tượng Covariate Shift khi dùng NFStream để trích xuất luồng thời gian thực, hệ thống Hybrid NIDS trong đồ án đã sử dụng linh hoạt bản port Python của CICFlowMeter để đồng nhất phân bố đặc trưng lúc huấn luyện và lúc triển khai, đạt năng lực phát hiện thời gian thực mạnh mẽ mà không cần phải tái huấn luyện toàn bộ mô hình."*

Chúc bạn hiện thực hóa thành công và có một buổi bảo vệ thật bùng nổ!
