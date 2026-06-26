import pandas as pd
import numpy as np
import argparse
import os
from tqdm import tqdm
from datetime import datetime

EXPECTED_FEATURES_81 = [
    'Flow_Duration', 'Total_Fwd_Packets', 'Total_Backward_Packets', 'Total_Length_of_Fwd_Packets',
    'Total_Length_of_Bwd_Packets', 'Fwd_Packet_Length_Max', 'Fwd_Packet_Length_Min', 'Fwd_Packet_Length_Mean',
    'Fwd_Packet_Length_Std', 'Bwd_Packet_Length_Max', 'Bwd_Packet_Length_Min', 'Bwd_Packet_Length_Mean',
    'Bwd_Packet_Length_Std', 'Flow_Bytes_s', 'Flow_Packets_s', 'Flow_IAT_Mean', 'Flow_IAT_Std', 'Flow_IAT_Max',
    'Flow_IAT_Min', 'Fwd_IAT_Total', 'Fwd_IAT_Mean', 'Fwd_IAT_Std', 'Fwd_IAT_Max', 'Fwd_IAT_Min', 'Bwd_IAT_Total',
    'Bwd_IAT_Mean', 'Bwd_IAT_Std', 'Bwd_IAT_Max', 'Bwd_IAT_Min', 'Fwd_PSH_Flags', 'Fwd_URG_Flags', 'Fwd_Header_Length',
    'Bwd_Header_Length', 'Fwd_Packets_s', 'Bwd_Packets_s', 'Min_Packet_Length', 'Max_Packet_Length', 'Packet_Length_Mean',
    'Packet_Length_Std', 'Packet_Length_Variance', 'FIN_Flag_Count', 'SYN_Flag_Count', 'RST_Flag_Count', 'PSH_Flag_Count',
    'ACK_Flag_Count', 'URG_Flag_Count', 'CWE_Flag_Count', 'ECE_Flag_Count', 'Down_Up_Ratio', 'Average_Packet_Size',
    'Avg_Fwd_Segment_Size', 'Avg_Bwd_Segment_Size', 'Subflow_Fwd_Packets', 'Subflow_Fwd_Bytes', 'Subflow_Bwd_Packets',
    'Subflow_Bwd_Bytes', 'Init_Win_bytes_forward', 'Init_Win_bytes_backward', 'act_data_pkt_fwd', 'min_seg_size_forward',
    'Active_Mean', 'Active_Std', 'Active_Max', 'Active_Min', 'Idle_Mean', 'Idle_Std', 'Idle_Max', 'Idle_Min',
    'Port_Is_Web', 'Port_Is_RemoteAccess', 'Port_Is_WellKnown', 'Port_Is_Registered', 'Port_Is_Ephemeral',
    'Custom_Fwd_Pkt_Rate', 'Custom_Slow_Index', 'Custom_Pkt_Var_Ratio', 'Custom_IAT_Anomaly',
    'Custom_IAT_CV', 'Custom_Bwd_Pkt_Ratio', 'Custom_Pkt_Size_Ratio',
    'Custom_PortScan_Intensity',  # Feature 81: unique dst ports/Src IP trong 2 giây
]

def map_cicflowmeter_v4_to_v3(df):
    mapping = {
        'Dst Port': 'Destination_Port', 'Flow Duration': 'Flow_Duration', 'Total Fwd Packet': 'Total_Fwd_Packets',
        'Total Bwd packets': 'Total_Backward_Packets', 'Total Length of Fwd Packet': 'Total_Length_of_Fwd_Packets',
        'Total Length of Bwd Packet': 'Total_Length_of_Bwd_Packets', 'Fwd Packet Length Max': 'Fwd_Packet_Length_Max',
        'Fwd Packet Length Min': 'Fwd_Packet_Length_Min', 'Fwd Packet Length Mean': 'Fwd_Packet_Length_Mean',
        'Fwd Packet Length Std': 'Fwd_Packet_Length_Std', 'Bwd Packet Length Max': 'Bwd_Packet_Length_Max',
        'Bwd Packet Length Min': 'Bwd_Packet_Length_Min', 'Bwd Packet Length Mean': 'Bwd_Packet_Length_Mean',
        'Bwd Packet Length Std': 'Bwd_Packet_Length_Std', 'Flow Bytes/s': 'Flow_Bytes_s', 'Flow Packets/s': 'Flow_Packets_s',
        'Flow IAT Mean': 'Flow_IAT_Mean', 'Flow IAT Std': 'Flow_IAT_Std', 'Flow IAT Max': 'Flow_IAT_Max', 'Flow IAT Min': 'Flow_IAT_Min',
        'Fwd IAT Total': 'Fwd_IAT_Total', 'Fwd IAT Mean': 'Fwd_IAT_Mean', 'Fwd IAT Std': 'Fwd_IAT_Std', 'Fwd IAT Max': 'Fwd_IAT_Max',
        'Fwd IAT Min': 'Fwd_IAT_Min', 'Bwd IAT Total': 'Bwd_IAT_Total', 'Bwd IAT Mean': 'Bwd_IAT_Mean', 'Bwd IAT Std': 'Bwd_IAT_Std',
        'Bwd IAT Max': 'Bwd_IAT_Max', 'Bwd IAT Min': 'Bwd_IAT_Min', 'Fwd PSH Flags': 'Fwd_PSH_Flags', 'Fwd URG Flags': 'Fwd_URG_Flags',
        'Fwd Header Length': 'Fwd_Header_Length', 'Bwd Header Length': 'Bwd_Header_Length', 'Fwd Packets/s': 'Fwd_Packets_s',
        'Bwd Packets/s': 'Bwd_Packets_s', 'Packet Length Min': 'Min_Packet_Length', 'Packet Length Max': 'Max_Packet_Length',
        'Packet Length Mean': 'Packet_Length_Mean', 'Packet Length Std': 'Packet_Length_Std', 'Packet Length Variance': 'Packet_Length_Variance',
        'FIN Flag Count': 'FIN_Flag_Count', 'SYN Flag Count': 'SYN_Flag_Count', 'RST Flag Count': 'RST_Flag_Count', 'PSH Flag Count': 'PSH_Flag_Count',
        'ACK Flag Count': 'ACK_Flag_Count', 'URG Flag Count': 'URG_Flag_Count', 'CWR Flag Count': 'CWE_Flag_Count', 'ECE Flag Count': 'ECE_Flag_Count',
        'Down/Up Ratio': 'Down_Up_Ratio', 'Average Packet Size': 'Average_Packet_Size', 'Fwd Segment Size Avg': 'Avg_Fwd_Segment_Size',
        'Bwd Segment Size Avg': 'Avg_Bwd_Segment_Size', 'Subflow Fwd Packets': 'Subflow_Fwd_Packets', 'Subflow Fwd Bytes': 'Subflow_Fwd_Bytes',
        'Subflow Bwd Packets': 'Subflow_Bwd_Packets', 'Subflow Bwd Bytes': 'Subflow_Bwd_Bytes', 'FWD Init Win Bytes': 'Init_Win_bytes_forward',
        'Bwd Init Win Bytes': 'Init_Win_bytes_backward', 'Fwd Act Data Pkts': 'act_data_pkt_fwd', 'Fwd Seg Size Min': 'min_seg_size_forward',
        'Active Mean': 'Active_Mean', 'Active Std': 'Active_Std', 'Active Max': 'Active_Max', 'Active Min': 'Active_Min', 'Idle Mean': 'Idle_Mean',
        'Idle Std': 'Idle_Std', 'Idle Max': 'Idle_Max', 'Idle Min': 'Idle_Min',
    }
    df.rename(columns=mapping, inplace=True)
    return df

def parse_time(time_str):
    try:
        # 07/06/2024 10:20:30 AM
        return int(datetime.strptime(time_str, "%d/%m/%Y %I:%M:%S %p").timestamp() * 1000)
    except:
        pass
    try:
        # 2024-06-07 10:20:30
        return int(datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
    except:
        return 0

def compute_portscan_intensity(df, window_sec=2.0):
    """Đếm số Destination_Port duy nhất mà cùng Src IP kết nối trong cửa sổ ±window_sec.
    Feature này phân biệt nmap -sT (nhiều unique port) với Benign (ít port/2sec).
    Yêu cầu: df phải còn cột 'Src IP', 'Destination_Port', 'Timestamp_ms'.
    """
    if 'Src IP' not in df.columns or 'Timestamp_ms' not in df.columns:
        df['Custom_PortScan_Intensity'] = 0
        return df

    window_ms = int(window_sec * 1000)
    src_ips = df['Src IP'].values
    dst_ports = df['Destination_Port'].astype(int).values
    timestamps = df['Timestamp_ms'].values.astype(np.int64)

    intensity = np.zeros(len(df), dtype=np.float32)

    # Xử lý từng Src IP riêng để tránh O(n²) toàn cục
    for ip in pd.unique(src_ips):
        mask = src_ips == ip
        idx = np.where(mask)[0]
        ts_ip = timestamps[idx]
        dp_ip = dst_ports[idx]
        sort_order = np.argsort(ts_ip)
        ts_sorted = ts_ip[sort_order]
        dp_sorted = dp_ip[sort_order]
        for i, orig_i in enumerate(sort_order):
            t0 = ts_sorted[i]
            in_window = (ts_sorted >= t0 - window_ms) & (ts_sorted <= t0 + window_ms)
            intensity[idx[orig_i]] = len(np.unique(dp_sorted[in_window]))

    df['Custom_PortScan_Intensity'] = intensity
    return df

def extract_custom_features(df):
    flow_duration = df['Flow_Duration'].astype(float).replace(0, 1)
    tot_fwd_pkts = df['Total_Fwd_Packets'].astype(float)
    df['Custom_Fwd_Pkt_Rate'] = (tot_fwd_pkts / (flow_duration / 1e6)).fillna(0)
    flow_iat_max = df['Flow_IAT_Max'].astype(float).replace(0, 1)
    df['Custom_Slow_Index'] = (flow_duration / flow_iat_max).fillna(0)
    
    if 'Packet_Length_Variance' in df.columns and 'Average_Packet_Size' in df.columns:
        pkt_len_var = df['Packet_Length_Variance'].astype(float).replace(0, 1)
        avg_pkt_size = df['Average_Packet_Size'].astype(float).replace(0, 1)
        df['Custom_Pkt_Var_Ratio'] = (pkt_len_var / avg_pkt_size).fillna(0)
    else:
        df['Custom_Pkt_Var_Ratio'] = 0
        
    if 'Fwd_IAT_Std' in df.columns:
        fwd_iat_std = df['Fwd_IAT_Std'].astype(float).replace(0, 1)
        df['Custom_IAT_Anomaly'] = (df['Flow_IAT_Max'].astype(float) / fwd_iat_std).fillna(0)
    else:
        df['Custom_IAT_Anomaly'] = 0

    if 'Flow_IAT_Std' in df.columns and 'Flow_IAT_Mean' in df.columns:
        df['Custom_IAT_CV'] = (df['Flow_IAT_Std'].astype(float) / (df['Flow_IAT_Mean'].astype(float) + 1e-6)).fillna(0)
    else:
        df['Custom_IAT_CV'] = 0
        
    if 'Total_Backward_Packets' in df.columns and 'Total_Fwd_Packets' in df.columns:
        df['Custom_Bwd_Pkt_Ratio'] = (df['Total_Backward_Packets'].astype(float) / (df['Total_Fwd_Packets'].astype(float) + 1e-6)).fillna(0)
    else:
        df['Custom_Bwd_Pkt_Ratio'] = 0
        
    if 'Min_Packet_Length' in df.columns and 'Max_Packet_Length' in df.columns:
        df['Custom_Pkt_Size_Ratio'] = (df['Min_Packet_Length'].astype(float) / (df['Max_Packet_Length'].astype(float) + 1e-6)).fillna(0)
    else:
        df['Custom_Pkt_Size_Ratio'] = 0
        
    return df

def create_port_categories(df):
    port = df['Destination_Port'].astype(int)
    df['Port_Is_Web'] = port.isin([80, 443, 8080, 8443, 8888]).astype(int)
    df['Port_Is_RemoteAccess'] = port.isin([21, 22, 23, 2222, 3389]).astype(int)
    df['Port_Is_WellKnown'] = (port <= 1023).astype(int)
    df['Port_Is_Registered'] = ((port > 1023) & (port <= 49151)).astype(int)
    df['Port_Is_Ephemeral'] = (port > 49151).astype(int)
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Đường dẫn file CSV sinh từ CICFlowMeter")
    parser.add_argument("--ground-truth", required=True, help="Đường dẫn file Ground Truth log (CSV)")
    args = parser.parse_args()

    print(f"[*] Đang nạp CICFlowMeter CSV: {args.csv}")
    df_flow = pd.read_csv(args.csv)
    df_flow.columns = df_flow.columns.str.strip()
    df_flow = map_cicflowmeter_v4_to_v3(df_flow)

    print(f"[*] Đang nạp Ground Truth Log: {args.ground_truth}")
    df_gt = pd.read_csv(args.ground_truth)
    
    # 1. Chuyển thời gian CICFlowMeter sang millisecond
    print("[*] Chuyển đổi timestamp...")
    df_flow['Timestamp_ms'] = df_flow['Timestamp'].apply(parse_time)
    df_flow = df_flow[df_flow['Timestamp_ms'] > 0].copy()

    # 2. Xây dựng cấu trúc Interval cho Ground Truth
    gt_intervals = []
    for _, row in df_gt.iterrows():
        gt_intervals.append({
            'start': int(row['start_time_ms']),
            'end': int(row['end_time_ms']),
            'label': row['attack_type'],
            'dst_ip': row['dst_ip'],
            'dst_port': str(row['dst_port'])
        })

    # 3. Gán nhãn đa lớp (KHÔNG ƯU TIÊN, CHO PHÉP AMBIGUOUS)
    print("[*] Đang gán nhãn đa lớp dựa trên Ground Truth...")
    labels = []
    
    for idx, row in tqdm(df_flow.iterrows(), total=len(df_flow)):
        t = row['Timestamp_ms']
        dip = str(row.get('Dst IP', row.get('Destination IP', '')))
        dport = str(int(row.get('Destination_Port', row.get('Dst Port', 0))))
        
        matched_labels = set()
        
        for gt in gt_intervals:
            # Cộng trừ 5 giây (5000ms) bù trễ mạng thay vì 120s như trước
            if gt['start'] - 5000 <= t <= gt['end'] + 5000:
                if dip == gt['dst_ip'] or gt['dst_ip'] == 'Multiple':
                    if gt['dst_port'] == 'Multiple' or gt['dst_port'] == dport:
                        matched_labels.add(gt['label'])
                        
        if len(matched_labels) == 1:
            labels.append(list(matched_labels)[0])
        elif len(matched_labels) > 1:
            labels.append('Ambiguous')
        else:
            labels.append('Benign')

    df_flow['Label'] = labels
    
    # Báo cáo
    counts = df_flow['Label'].value_counts()
    print("\n[-] Thống kê gán nhãn (Ground Truth Based):")
    for k, v in counts.items():
        print(f"      - {k}: {v} dòng")

    # 4. Tiền xử lý các đặc trưng
    print("\n[*] Đang tính Custom_PortScan_Intensity (cần Src IP + Timestamp_ms)...")
    df_flow = compute_portscan_intensity(df_flow, window_sec=2.0)

    print("[*] Đang trích xuất Custom Features...")
    df_flow = extract_custom_features(df_flow)
    df_flow = create_port_categories(df_flow)

    print("[*] Đang làm sạch dữ liệu (Xóa lỗi Infinity, NaN)...")
    df_flow.replace([np.inf, -np.inf], np.nan, inplace=True)
    df_flow.dropna(inplace=True)

    # 5. Lưu Raw Labeled (Chưa filter ambiguous)
    raw_path = 'Raw_Labeled_Dataset.csv'
    df_flow.to_csv(raw_path, index=False)
    print(f"[+] Đã lưu file Raw (có Ambiguous): {raw_path}")

    # 6. Loại bỏ Ambiguous và các cột định danh
    print("[*] Loại bỏ các mẫu Ambiguous và cột định danh (IP, Port)...")
    df_clean = df_flow[df_flow['Label'] != 'Ambiguous'].copy()
    
    drop_cols = ['Flow ID', 'Src IP', 'Dst IP', 'Source IP', 'Destination IP', 
                 'Src Port', 'Dst Port', 'Source Port', 'Destination_Port', 'Timestamp', 'Timestamp_ms']
    for c in drop_cols:
        if c in df_clean.columns:
            df_clean.drop(columns=[c], inplace=True)

    # Note: Không gọi MinMaxScaler ở đây nữa vì đã được nhắc trong Roadmap là lỗi!
    # Quá trình Scale sẽ do `HybridFeatureScaler` đảm nhận ở Phase 3.
    
    # Đảm bảo đủ 81 đặc trưng
    for c in EXPECTED_FEATURES_81:
        if c not in df_clean.columns:
            df_clean[c] = 0

    clean_path = 'Cleaned_Labeled_Dataset.csv'
    df_clean.to_csv(clean_path, index=False)
    print(f"[+] Đã lưu Dataset cuối cùng (Dùng để Train): {clean_path}")

    # 7. Sinh báo cáo chất lượng
    report_path = f"label_quality_report.md"
    total_flows = len(df_flow)
    ambiguous_flows = len(df_flow[df_flow['Label'] == 'Ambiguous'])
    ambiguous_pct = (ambiguous_flows / total_flows) * 100 if total_flows > 0 else 0
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Báo Cáo Chất Lượng Gán Nhãn\n\n")
        f.write(f"**Nguồn CSV:** `{args.csv}`\n")
        f.write(f"**Nguồn Ground Truth:** `{args.ground_truth}`\n\n")
        f.write(f"## 1. Thống kê tổng quan\n")
        f.write(f"- Tổng số flow đã xử lý: **{total_flows}**\n")
        f.write(f"- Số flow Ambiguous (loại bỏ do chồng lấn nhãn): **{ambiguous_flows}** ({ambiguous_pct:.2f}%)\n\n")
        f.write(f"## 2. Chi tiết phân bổ nhãn (Dữ liệu sạch)\n")
        for k, v in counts.items():
            if k != 'Ambiguous':
                f.write(f"- **{k}**: {v} dòng ({(v/total_flows)*100:.2f}%)\n")
        f.write("\n## 3. Đối chiếu Snort\n")
        f.write("> *Tính năng này chỉ khả dụng nếu log Snort được tích hợp. Hiện tại: Không cung cấp dữ liệu Snort.*\n")
    print(f"[+] Đã sinh báo cáo: {report_path}")

if __name__ == "__main__":
    main()
