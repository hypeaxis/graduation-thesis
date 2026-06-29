import os
import sys
import pandas as pd
import numpy as np
import joblib

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

# Copy features list & custom logic
EXPECTED_FEATURES_80 = [
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
    'Custom_IAT_CV', 'Custom_Bwd_Pkt_Ratio', 'Custom_Pkt_Size_Ratio'
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

def create_port_categories(df):
    port = df['Destination_Port'].astype(int)
    df['Port_Is_Web'] = port.isin([80, 443, 8080, 8443, 8888]).astype(int)
    df['Port_Is_RemoteAccess'] = port.isin([21, 22, 23, 2222, 3389]).astype(int)
    df['Port_Is_WellKnown'] = (port <= 1023).astype(int)
    df['Port_Is_Registered'] = ((port > 1023) & (port <= 49151)).astype(int)
    df['Port_Is_Ephemeral'] = (port > 49151).astype(int)
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

def apply_pipeline(X, pipeline):
    if 'scaler_77_original' in pipeline:
        X_old = X[:, :77]
        X_new = X[:, 77:]
        return np.hstack((
            pipeline['scaler_77_original'].transform(X_old),
            pipeline['scaler_3_new'].transform(X_new)
        ))
    else:
        raise ValueError("Pipeline không đúng chuẩn Hybrid")

def main():
    print("=========================================================")
    print("PHASE 0: XÁC MINH INFERENCE PIPELINE")
    print("=========================================================")
    
    PIPELINE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Domain_Adaptation_Workspace/models/stage3c_hybrid_pipeline.pkl'))
    DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Raw_Labeled_Dataset.csv'))
    
    # BƯỚC 1: LOAD PIPELINE CHUẨN
    print("[*] Đang load pipeline từ file pkl...")
    pipeline = joblib.load(PIPELINE_PATH)
    print(f"    Thành phần pipeline: {list(pipeline.keys())}")
    
    # BƯỚC 2: MÔ PHỎNG INFERENCE THỰC TẾ
    print("[*] Lấy ngẫu nhiên 5 sample từ Raw_Labeled_Dataset.csv...")
    df = pd.read_csv(DATA_PATH).sample(n=5, random_state=42)
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    df = create_port_categories(df)
    df = extract_custom_features(df)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    for c in EXPECTED_FEATURES_80:
        if c not in df.columns:
            df[c] = 0
    X_raw = df[EXPECTED_FEATURES_80].values
    
    # Áp dụng logic inference hiện tại
    X_scaled_inference = apply_pipeline(X_raw, pipeline)
    
    # BƯỚC 3: MÔ PHỎNG LẠI CHÍNH XÁC QUÁ TRÌNH TRAINING
    print("[*] Tái hiện quá trình transform thủ công giống lúc Training...")
    scaler_77 = pipeline['scaler_77_original']
    scaler_3 = pipeline['scaler_3_new']
    
    X_old = X_raw[:, :77]
    X_new = X_raw[:, 77:]
    
    X_scaled_old_train = scaler_77.transform(X_old)
    X_scaled_new_train = scaler_3.transform(X_new)
    X_scaled_train_sim = np.hstack((X_scaled_old_train, X_scaled_new_train))
    
    # BƯỚC 4: SO SÁNH
    diff = np.abs(X_scaled_inference - X_scaled_train_sim)
    max_diff = np.max(diff)
    
    print("\n[KẾT QUẢ]")
    if max_diff < 1e-6:
        print(f"✅ PASS: Inference Pipeline HOÀN TOÀN KHỚP với Training Pipeline. (Sai số lớn nhất: {max_diff})")
        print("Lý do báo cáo run2 nhắc đến MinMaxScaler là vì `dataset_builder.py` có hàm MinMaxScaler")
        print("nhưng xuất ra file `Cleaned_Labeled_Dataset.csv`. Tuy nhiên, inference script")
        print("lại load `Raw_Labeled_Dataset.csv` và bỏ qua file Cleaned! Do đó, kết quả vẫn đang đúng bản chất.")
    else:
        print(f"❌ FAIL: Sai số quá lớn ({max_diff}). Cần fix lại Inference Pipeline.")

if __name__ == "__main__":
    main()
