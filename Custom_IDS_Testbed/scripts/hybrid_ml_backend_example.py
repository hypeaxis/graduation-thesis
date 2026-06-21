import time
import os
import csv
import json
import numpy as np
import sys
import argparse

# Hàm giả lập dự đoán của Model ML v7 CIC-IDS-2017
def run_ml_model_prediction(features_array):
    # Thực tế: prediction = model.predict([features_array])
    # Tạm thời giả định là 'Benign' cho đa số, random 'Malicious' để test
    import random
    if random.random() < 0.001: # Giả lập 0.1% là tấn công
        return "Malicious - DoS Slowloris"
    return "Benign"

def process_cicflowmeter_csv(filepath):
    print(f"[*] Backend đang đọc dữ liệu Flow từ file: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        # Đọc header
        headers = next(reader, [])
        
        count = 0
        for line in file:
            line = line.strip()
            if not line:
                continue
                
            if count % 5000 == 0:
                print(f"[Tiến độ] Đã xử lý {count} flows...")
                
            process_flow(line, headers)
            count += 1
            
        print(f"[*] Hoàn tất xử lý {count} flows từ {filepath}.")

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
    parser = argparse.ArgumentParser(description='Hybrid ML Backend Simulator')
    parser.add_argument('--csv', required=True, help='Path to CICFlowMeter CSV file')
    parser.add_argument('--snort-alert', required=False, help='Path to Snort alert file')
    args = parser.parse_args()
    
    if not os.path.exists(args.csv):
        print(f"[LỖI] Không tìm thấy file CSV: {args.csv}")
        sys.exit(1)
        
    process_cicflowmeter_csv(args.csv)
