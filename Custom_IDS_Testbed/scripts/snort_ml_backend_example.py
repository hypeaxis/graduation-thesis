import time
import os
import csv
import json

# Hàm giả lập dự đoán của Model ML v7 CIC-IDS-2017
def run_ml_model_prediction(features):
    print(f"[ML Model] Đang xử lý đặc trưng: {features}")
    # Đưa vào model thực tế: model.predict([features])
    # Tạm thời trả về True giả định đây là tấn công
    return True

# Hàm đọc liên tục file log (Tail -f)
def tail_snort_log(filepath):
    # Di chuyển con trỏ về cuối file để chỉ đọc cảnh báo MỚI NHẤT
    with open(filepath, 'r') as file:
        file.seek(0, os.SEEK_END)
        print(f"[*] Backend đang lắng nghe file {filepath} theo thời gian thực...")
        
        while True:
            line = file.readline()
            if not line:
                time.sleep(0.5) # Đợi log mới
                continue
                
            # Xử lý khi có dòng log mới
            print("\n[!] Có luồng traffic mới từ Snort!")
            process_alert(line.strip())

def process_alert(log_line):
    # Giả sử file alert_csv của Snort có dạng: timestamp,sig_id,msg,src_ip,dst_ip,src_port,dst_port
    try:
        # Nếu là CSV
        fields = log_line.split(',')
        if len(fields) >= 5:
            src_ip = fields[3]
            dst_ip = fields[4]
            msg = fields[2]
            
            # 1. Thu thập thêm các đặc trưng khác nếu cần từ CICFlowMeter (Flow Duration, Pkt Size...)
            extracted_features = [src_ip, dst_ip, msg, "thêm_đặc_trưng..."]
            
            # 2. Đưa qua Model
            is_attack = run_ml_model_prediction(extracted_features)
            
            if is_attack:
                # 3. Chuẩn bị gửi lên GUI (WebSocket)
                payload = {
                    "source": src_ip,
                    "target": dst_ip,
                    "attack_type": msg,
                    "status": "DANGER"
                }
                print(f"[WebSocket] Đẩy dữ liệu lên GUI vẽ đường mạng: {json.dumps(payload)}")
                # socket.emit("new_attack", payload)
    except Exception as e:
        print(f"Lỗi parse: {e}")

if __name__ == "__main__":
    # Thay đường dẫn này bằng đường dẫn tới file alert.csv hoặc alert.json của Snort
    LOG_FILE = "snort_dummy_alert.csv"
    
    # Tạo file dummy nếu chưa có để test script không bị crash
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()
        
    tail_snort_log(LOG_FILE)
