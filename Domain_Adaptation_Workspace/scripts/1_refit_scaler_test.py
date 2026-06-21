import os
import sys
import pandas as pd
import numpy as np
import torch
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import PowerTransformer
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

from models.phase2_ft_transformer_v2 import FTTransformer

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
        
    return df

def create_port_categories(df):
    port = df['Destination_Port'].astype(int)
    df['Port_Is_Web'] = port.isin([80, 443, 8080, 8443, 8888]).astype(int)
    df['Port_Is_RemoteAccess'] = port.isin([21, 22, 23, 2222, 3389]).astype(int)
    df['Port_Is_WellKnown'] = (port <= 1023).astype(int)
    df['Port_Is_Registered'] = ((port > 1023) & (port <= 49151)).astype(int)
    df['Port_Is_Ephemeral'] = (port > 49151).astype(int)
    return df

def map_cicflowmeter_v4_to_v3(df):
    mapping = {
        'Dst Port': 'Destination_Port',
        'Flow Duration': 'Flow_Duration',
        'Total Fwd Packet': 'Total_Fwd_Packets',
        'Total Bwd packets': 'Total_Backward_Packets',
        'Total Length of Fwd Packet': 'Total_Length_of_Fwd_Packets',
        'Total Length of Bwd Packet': 'Total_Length_of_Bwd_Packets',
        'Fwd Packet Length Max': 'Fwd_Packet_Length_Max',
        'Fwd Packet Length Min': 'Fwd_Packet_Length_Min',
        'Fwd Packet Length Mean': 'Fwd_Packet_Length_Mean',
        'Fwd Packet Length Std': 'Fwd_Packet_Length_Std',
        'Bwd Packet Length Max': 'Bwd_Packet_Length_Max',
        'Bwd Packet Length Min': 'Bwd_Packet_Length_Min',
        'Bwd Packet Length Mean': 'Bwd_Packet_Length_Mean',
        'Bwd Packet Length Std': 'Bwd_Packet_Length_Std',
        'Flow Bytes/s': 'Flow_Bytes_s',
        'Flow Packets/s': 'Flow_Packets_s',
        'Flow IAT Mean': 'Flow_IAT_Mean',
        'Flow IAT Std': 'Flow_IAT_Std',
        'Flow IAT Max': 'Flow_IAT_Max',
        'Flow IAT Min': 'Flow_IAT_Min',
        'Fwd IAT Total': 'Fwd_IAT_Total',
        'Fwd IAT Mean': 'Fwd_IAT_Mean',
        'Fwd IAT Std': 'Fwd_IAT_Std',
        'Fwd IAT Max': 'Fwd_IAT_Max',
        'Fwd IAT Min': 'Fwd_IAT_Min',
        'Bwd IAT Total': 'Bwd_IAT_Total',
        'Bwd IAT Mean': 'Bwd_IAT_Mean',
        'Bwd IAT Std': 'Bwd_IAT_Std',
        'Bwd IAT Max': 'Bwd_IAT_Max',
        'Bwd IAT Min': 'Bwd_IAT_Min',
        'Fwd PSH Flags': 'Fwd_PSH_Flags',
        'Fwd URG Flags': 'Fwd_URG_Flags',
        'Fwd Header Length': 'Fwd_Header_Length',
        'Bwd Header Length': 'Bwd_Header_Length',
        'Fwd Packets/s': 'Fwd_Packets_s',
        'Bwd Packets/s': 'Bwd_Packets_s',
        'Packet Length Min': 'Min_Packet_Length',
        'Packet Length Max': 'Max_Packet_Length',
        'Packet Length Mean': 'Packet_Length_Mean',
        'Packet Length Std': 'Packet_Length_Std',
        'Packet Length Variance': 'Packet_Length_Variance',
        'FIN Flag Count': 'FIN_Flag_Count',
        'SYN Flag Count': 'SYN_Flag_Count',
        'RST Flag Count': 'RST_Flag_Count',
        'PSH Flag Count': 'PSH_Flag_Count',
        'ACK Flag Count': 'ACK_Flag_Count',
        'URG Flag Count': 'URG_Flag_Count',
        'CWR Flag Count': 'CWE_Flag_Count',
        'ECE Flag Count': 'ECE_Flag_Count',
        'Down/Up Ratio': 'Down_Up_Ratio',
        'Average Packet Size': 'Average_Packet_Size',
        'Fwd Segment Size Avg': 'Avg_Fwd_Segment_Size',
        'Bwd Segment Size Avg': 'Avg_Bwd_Segment_Size',
        'Subflow Fwd Packets': 'Subflow_Fwd_Packets',
        'Subflow Fwd Bytes': 'Subflow_Fwd_Bytes',
        'Subflow Bwd Packets': 'Subflow_Bwd_Packets',
        'Subflow Bwd Bytes': 'Subflow_Bwd_Bytes',
        'FWD Init Win Bytes': 'Init_Win_bytes_forward',
        'Bwd Init Win Bytes': 'Init_Win_bytes_backward',
        'Fwd Act Data Pkts': 'act_data_pkt_fwd',
        'Fwd Seg Size Min': 'min_seg_size_forward',
        'Active Mean': 'Active_Mean',
        'Active Std': 'Active_Std',
        'Active Max': 'Active_Max',
        'Active Min': 'Active_Min',
        'Idle Mean': 'Idle_Mean',
        'Idle Std': 'Idle_Std',
        'Idle Max': 'Idle_Max',
        'Idle Min': 'Idle_Min',
    }
    df.rename(columns=mapping, inplace=True)
    return df

def main():
    print("="*60)
    print("THỬ NGHIỆM 1: RE-FIT SCALER TRÊN DOMAIN MỚI")
    print("="*60)

    # 1. Load Data
    print("[*] Đang nạp Testbed Data...")
    df = pd.read_csv('../data/Raw_Labeled_Dataset.csv')
    df = df[df['Label'].isin(['Malicious', 'Benign'])].copy()
    
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    df = create_port_categories(df)
    df = extract_custom_features(df)
    
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)

    EXPECTED_FEATURES = [
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
        'Custom_Fwd_Pkt_Rate', 'Custom_Slow_Index', 'Custom_Pkt_Var_Ratio', 'Custom_IAT_Anomaly'
    ]

    for c in EXPECTED_FEATURES:
        if c not in df.columns:
            df[c] = 0
            
    X_raw = df[EXPECTED_FEATURES].values
    y_true = df['Label'].values

    # 2. RE-FIT SCALER
    print("[*] Re-fitting PowerTransformer trên Testbed Data...")
    scaler = PowerTransformer(method='yeo-johnson', standardize=True)
    X_scaled = scaler.fit_transform(X_raw)

    # 3. Load Model
    print("[*] Đang nạp Model gốc (Final CIC-IDS-2017)...")
    MODEL_DIR = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017'))
    
    import joblib
    encoder1 = joblib.load(os.path.join(MODEL_DIR, 'encoder_stage1.pkl'))

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model1 = FTTransformer(num_features=77, num_classes=len(encoder1.classes_), 
                           d_model=128, num_layers=4, num_heads=8, dropout=0.2, drop_path_rate=0.1).to(device)
    
    model_path = os.path.join(MODEL_DIR, 'best_stage1_model.pt')
    model1.load_state_dict(torch.load(model_path, map_location=device))
    model1.eval()

    # 4. Transform & Predict
    print("[*] Đang chạy dự đoán (Inference)...")
    X_tensor = torch.FloatTensor(X_scaled).to(device)
    
    batch_size = 2048
    all_preds = []
    
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                logits = model1(batch)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            
    predicted_labels = encoder1.inverse_transform(all_preds)
    
    y_pred_binary = []
    for p in predicted_labels:
        if p == 'Benign':
            y_pred_binary.append('Benign')
        else:
            y_pred_binary.append('Malicious')
            
    print("\n" + "="*60)
    print("KẾT QUẢ SAU KHI RE-FIT SCALER")
    print("="*60)
    
    acc = accuracy_score(y_true, y_pred_binary)
    print(f"Độ chính xác (Accuracy): {acc*100:.2f}%\n")
    print(classification_report(y_true, y_pred_binary, digits=4))

    # Log metrics for aggregator
    from sklearn.metrics import balanced_accuracy_score, matthews_corrcoef, precision_recall_fscore_support
    b_acc = balanced_accuracy_score(y_true, y_pred_binary)
    mcc = matthews_corrcoef(y_true, y_pred_binary)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred_binary, average=None, labels=['Benign', 'Malicious'])
    
    import datetime, json
    log_data = {
        "timestamp": str(datetime.datetime.now()),
        "config": {
            "strategy": "Re-fit Scaler Only",
            "learning_rate": "N/A",
            "oversampler": "N/A",
            "scaler": "Re-fitted PowerTransformer"
        },
        "metrics_testbed": {
            "accuracy": acc,
            "balanced_accuracy": b_acc,
            "mcc": mcc,
            "recall_benign": recall[0],
            "recall_malicious": recall[1],
            "precision_benign": precision[0],
            "precision_malicious": precision[1],
            "f1_malicious": f1[1]
        },
        "metrics_cic_2017": {
            "accuracy": 0,
            "recall_malicious": 0
        }
    }
    with open('../results/exp1_refit_scaler.json', 'w') as f:
        json.dump(log_data, f, indent=4)
        
if __name__ == "__main__":
    main()
