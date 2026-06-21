import pandas as pd
import numpy as np
import re
from datetime import datetime, timedelta
import argparse
import sys
from sklearn.preprocessing import MinMaxScaler
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

def determine_attack_class(msg):
    """
    Phân loại nhãn dựa trên thông điệp cảnh báo của Snort.
    Các lớp tấn công bao gồm: PortScan, Brute Force, Web Attack, DoS, Bot, Infiltration, Heartbleed, Suspicious.
    """
    msg = msg.lower()
    
    # 1. PortScan
    if any(keyword in msg for keyword in ['nmap', 'scan', 'probe', 'recon']):
        return 'PortScan'
    
    # 2. Brute Force (SSH, FTP, Web Login)
    if any(keyword in msg for keyword in ['brute force', 'hydra', 'ssh', 'ftp', 'login', 'authentication failed']):
        return 'Brute Force'
    
    # 3. Web Attack (SQLi, XSS)
    if any(keyword in msg for keyword in ['sql', 'injection', 'xss', 'web attack', 'directory traversal']):
        return 'Web Attack'
    
    # 4. DoS / DDoS (Hulk, Slowloris)
    if any(keyword in msg for keyword in ['dos', 'ddos', 'hulk', 'slowloris', 'flood', 'denial of service']):
        return 'DoS'
        
    # 5. Botnet
    if any(keyword in msg for keyword in ['bot', 'c2', 'command and control']):
        return 'Bot'
        
    # 6. Heartbleed
    if 'heartbleed' in msg:
        return 'Heartbleed'
        
    # 7. Infiltration
    if 'infiltration' in msg or 'backdoor' in msg:
        return 'Infiltration'
        
    # Mặc định nếu không rõ
    return 'Suspicious'

def parse_snort_alerts(alert_file, year):
    # Trả về list các cảnh báo gồm (timestamp, attack_class, src_ip, dst_ip)
    alerts = []
    # Regex bắt chi tiết: Thời gian | Message | Src IP | Dst IP
    # VD: 06/20-10:17:51.807743  [**] [1:1000001:1] ET SCAN Nmap [**] [Priority: 3] {TCP} 192.168.1.1:5000 -> 192.168.1.2:80
    regex_pattern = r'^(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})\.\d+\s+\[\*\*\]\s+(?:\[\d+:\d+:\d+\]\s+)?(.*?)\s+\[\*\*\]\s+.*?(?:\{\w+\})?\s*([\d\.]+)\s*(?:\:\d+)?\s*->\s*([\d\.]+)'
    
    with open(alert_file, 'r') as f:
        for line in f:
            match = re.match(regex_pattern, line)
            if match:
                time_str = match.group(1) # MM/DD-HH:MM:SS
                msg = match.group(2).strip()
                src_ip = match.group(3)
                dst_ip = match.group(4)
                
                attack_class = determine_attack_class(msg)
                
                # Snort thiếu năm, ta bổ sung
                time_str_full = f"{year}/{time_str}"
                try:
                    dt = datetime.strptime(time_str_full, "%Y/%m/%d-%H:%M:%S")
                    alerts.append({
                        "time": dt,
                        "attack_class": attack_class,
                        "src_ip": src_ip,
                        "dst_ip": dst_ip
                    })
                except Exception as e:
                    pass
    return alerts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True, help='Đường dẫn tới file CSV của CICFlowMeter')
    parser.add_argument('--alert', required=True, help='Đường dẫn tới file alert của Snort')
    args = parser.parse_args()

    print("[*] Đang đọc file dữ liệu CICFlowMeter CSV...")
    try:
        df = pd.read_csv(args.csv, encoding='utf-8')
    except Exception as e:
        print(f"Lỗi đọc CSV: {e}")
        sys.exit(1)
        
    print(f"[-] Tổng số dòng ban đầu: {len(df)}")
    df.columns = df.columns.str.strip()
    
    # 1. Parse Alert
    print("[*] Đang đọc cảnh báo Snort...")
    first_time = str(df['Timestamp'].iloc[0]).strip()
    try:
        year = datetime.strptime(first_time, "%d/%m/%Y %I:%M:%S %p").year
    except:
        year = datetime.now().year
        
    alerts = parse_snort_alerts(args.alert, year)
    print(f"[-] Lấy được {len(alerts)} cảnh báo từ Snort.")
    
    # Thống kê sơ bộ các loại tấn công bắt được
    attack_counts = {}
    for a in alerts:
        cls = a['attack_class']
        attack_counts[cls] = attack_counts.get(cls, 0) + 1
    print("    Chi tiết cảnh báo Snort:")
    for cls, count in attack_counts.items():
        print(f"      - {cls}: {count} alerts")
    
    # 2. Xử lý thời gian của CSV
    print("\n[*] Chuyển đổi định dạng thời gian trong CSV...")
    df['parsed_time'] = pd.to_datetime(df['Timestamp'], format="%d/%m/%Y %I:%M:%S %p", errors='coerce')
    original_len = len(df)
    df = df.dropna(subset=['parsed_time'])
    print(f"[-] Đã gỡ bỏ {original_len - len(df)} dòng không chứa định dạng thời gian hợp lệ.")
    
    # 3. Đồng bộ Nhãn (Label Synchronization)
    import bisect
    print("\n[*] Đang đồng bộ Nhãn (Đa Lớp) bằng Binary Search (± 120s)...")
    
    alert_map = {}
    for a in alerts:
        key = (a['src_ip'], a['dst_ip'])
        if key not in alert_map:
            alert_map[key] = {'raw': []}
        alert_map[key]['raw'].append((a['time'], a['attack_class']))
        
    for key in alert_map:
        alert_map[key]['raw'].sort(key=lambda x: x[0])
        alert_map[key]['times'] = [x[0] for x in alert_map[key]['raw']]
        alert_map[key]['classes'] = [x[1] for x in alert_map[key]['raw']]
        
    def check_attack_class(row):
        flow_time = row['parsed_time']
        src = str(row['Src IP']).strip()
        dst = str(row['Dst IP']).strip()
        
        key = (src, dst)
        detected_classes = []
        if key in alert_map:
            start_time = flow_time - pd.Timedelta(seconds=120)
            end_time = flow_time + pd.Timedelta(seconds=120)
            times = alert_map[key]['times']
            classes = alert_map[key]['classes']
            left_idx = bisect.bisect_left(times, start_time)
            right_idx = bisect.bisect_right(times, end_time)
            detected_classes = classes[left_idx:right_idx]
        
        if detected_classes:
            # Ưu tiên các nhãn cụ thể hơn (trường hợp dính nhiều loại tấn công cùng lúc)
            if 'DoS' in detected_classes: return 'DoS'
            if 'Web Attack' in detected_classes: return 'Web Attack'
            if 'Brute Force' in detected_classes: return 'Brute Force'
            if 'PortScan' in detected_classes: return 'PortScan'
            return detected_classes[0]
            
        return 'Benign'
        
    tqdm.pandas(desc="Đang gán nhãn đa lớp")
    df['Label'] = df.progress_apply(check_attack_class, axis=1)
    
    print("[-] Kết quả đồng bộ nhãn đa lớp:")
    label_counts = df['Label'].value_counts()
    for lbl, count in label_counts.items():
        print(f"      - {lbl}: {count} dòng")
    
    # 4. Làm sạch dữ liệu (Data Cleaning)
    print("\n[*] Đang làm sạch dữ liệu (Xóa lỗi Infinity, NaN)...")
    df = df.replace([np.inf, -np.inf], np.nan)
    cols_to_drop = ['Flow ID', 'Src IP', 'Src Port', 'Dst IP', 'Dst Port', 'Protocol', 'Timestamp', 'parsed_time']
    features = df.columns.drop(cols_to_drop + ['Label'], errors='ignore')
    
    for col in features:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    original_len = len(df)
    df = df.dropna()
    print(f"[-] Số dòng còn lại sau khi làm sạch: {len(df)} (Đã xóa {original_len - len(df)} dòng lỗi).")
    
    raw_output_file = 'Raw_Labeled_Dataset.csv'
    df.to_csv(raw_output_file, index=False)
    print(f"[+] Đã lưu file Raw (đầy đủ các cột): {raw_output_file}")
    
    # 5. Xóa các cột định danh mạng
    print("[*] Xóa các cột không dùng cho học máy (IP, Port, ID)...")
    cols_to_drop = [c for c in cols_to_drop if c in df.columns]
    df = df.drop(columns=cols_to_drop)
    
    # 6. Chuẩn hóa đặc trưng (MinMaxScaler)
    print("[*] Chuẩn hóa 77 giá trị đặc trưng bằng MinMaxScaler...")
    scaler = MinMaxScaler()
    df[features] = scaler.fit_transform(df[features])
    
    # 7. Lưu file
    output_file = 'Cleaned_Labeled_Dataset.csv'
    df.to_csv(output_file, index=False)
    print(f"[+] Đã hoàn thành! Dataset được lưu tại: {output_file}")
    print(f"    Tổng số dòng: {len(df)}, Tổng số cột: {len(df.columns)}")

if __name__ == "__main__":
    main()
