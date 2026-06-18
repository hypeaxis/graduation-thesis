import time
import os
import csv
import json
import numpy as np

# Hàm giả lập dự đoán của Model ML v7 CIC-IDS-2017
def run_ml_model_prediction(features_array):
    print(f"[ML Model] Nhận {len(features_array)} đặc trưng thống kê. Đang xử lý...")
    # Thực tế: prediction = model.predict([features_array])
    # Tạm thời giả định là 'Malicious' để test GUI
    return "Malicious - DoS Slowloris"

def tail_cicflowmeter_csv(filepath):
    # Di chuyển con trỏ về cuối file để đọc flow MỚI NHẤT
    with open(filepath, 'r') as file:
        reader = csv.reader(file)
        
        # Đọc header để biết vị trí các cột
        file.seek(0)
        headers = next(reader, [])
        print(f"[*] Backend đang lắng nghe Flow mạng từ CICFlowMeter...")
        
        # Nhảy về cuối file
        file.seek(0, os.SEEK_END)
        
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.5) # Đợi luồng mạng kết thúc
                continue
                
            print("\n[!] Có flow mạng mới được trích xuất!")
            process_flow(line.strip(), headers)

def process_flow(csv_line, headers):
    try:
        fields = csv_line.split(',')
        
        # Giả định thứ tự cột của CICFlowMeter (bạn cần map lại cho khớp với lúc train model)
        # Các cột định danh (Flow ID, Src IP, Dst IP, Timestamp) không được đưa vào Model
        src_ip = fields[1]
        dst_ip = fields[3]
        
        # Lấy 78 cột thống kê làm đặc trưng cho Model (bỏ qua cột định danh)
        # Ví dụ: từ cột 7 đến cột 84
        try:
            statistical_features = [float(x) for x in fields[7:85]]
        except ValueError:
            print("Lỗi chuyển đổi dữ liệu đặc trưng. Đang bỏ qua flow này.")
            return

        # 1. Đưa 78 đặc trưng qua Model CIC-IDS-2017
        prediction_result = run_ml_model_prediction(statistical_features)
        
        # 2. Xử lý logic và đẩy lên GUI
        if prediction_result != "Benign":
            payload = {
                "source": src_ip,
                "target": dst_ip,
                "attack_type": prediction_result,
                "confidence": 0.95,
                "status": "DANGER",
                "flow_duration": fields[7] # Gửi kèm một số thống kê lên GUI cho sinh động
            }
            print(f"[WebSocket] Đẩy dữ liệu tấn công lên GUI: {json.dumps(payload)}")
            # socket.emit("new_attack", payload)
            
    except Exception as e:
        print(f"Lỗi parse flow: {e}")

if __name__ == "__main__":
    # Thay đường dẫn này bằng đường dẫn file output CSV của CICFlowMeter
    LOG_FILE = "cicflowmeter_dummy_flow.csv"
    
    # Tạo file dummy nếu chưa có để test
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w') as f:
            f.write("Flow ID,Src IP,Src Port,Dst IP,Dst Port,Protocol,Timestamp,Flow Duration,Total Fwd Packets,Total Backward Packets,...\n")
        
    tail_cicflowmeter_csv(LOG_FILE)
