import os
import sys
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, recall_score, confusion_matrix
import joblib
import json
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

try:
    from models.phase2_ft_transformer_v2 import FTTransformer
except ImportError:
    print("Cannot import FTTransformer.")
    sys.exit(1)

from hybrid_feature_scaler import HybridFeatureScaler

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

def load_validation_data(filepath, encoder):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    for c in EXPECTED_FEATURES_80:
        if c not in df.columns:
            df[c] = 0
            
    X = df[EXPECTED_FEATURES_80].values
    y = df['Label'].values
    
    valid_mask = np.isin(y, encoder.classes_)
    X = X[valid_mask]
    y = y[valid_mask]
    
    # We must split exactly the same way as training script (seed=42)
    _, X_val, _, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
        
    return X_val, y_val

def main():
    print("=========================================================")
    print("5D. TÌM NGƯỠNG TỐI ƯU (THRESHOLD CALIBRATION)")
    print("=========================================================")

    DATA_PATH = '../data/Cleaned_Labeled_Dataset_run5.csv'
    SCALER_PATH = '../models/v5_hybrid_pipeline.pkl'
    MODEL_PATH = '../models/v5_focal_model.pt'
    ENCODER_PATH = '../models/v5_encoder.pkl'
    
    encoder = joblib.load(ENCODER_PATH)
    benign_idx = encoder.transform(['Benign'])[0]
    
    print("[*] Nạp Validation Data (run5 val split)...")
    X_val, y_val = load_validation_data(DATA_PATH, encoder)
    y_val_encoded = encoder.transform(y_val)
    print(f"    Tổng mẫu Validation: {len(X_val)}")
    
    print("[*] Transform Data...")
    scaler = HybridFeatureScaler.load(SCALER_PATH)
    X_val_scaled = scaler.transform(X_val)
    
    print("[*] Nạp Model V5...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
    model.to(device)
    model.eval()
    
    print("[*] Inference lấy Probabilities...")
    X_tensor = torch.FloatTensor(X_val_scaled).to(device)
    batch_size = 512
    all_probs = []
    
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                logits = model(batch)
                probs = torch.softmax(logits, dim=1)
            all_probs.append(probs.cpu().numpy())
            
    all_probs = np.vstack(all_probs)
    
    # Chuẩn bị nhãn nhị phân cho đánh giá (Benign=0, Attack=1)
    y_true_binary = (y_val_encoded != benign_idx).astype(int)
    
    print("\n[*] Đang dò Threshold (0.50 -> 0.99)...")
    thresholds = np.arange(0.50, 1.00, 0.01)
    
    results = []
    best_score = -1
    best_threshold = 0.50
    
    # Dự đoán lớp tấn công cao nhất (trường hợp không chọn Benign)
    non_benign_probs = all_probs.copy()
    non_benign_probs[:, benign_idx] = -1.0
    non_benign_preds = np.argmax(non_benign_probs, axis=1)
    
    for t in thresholds:
        # Nếu P(Benign) >= t => Benign. Else => Max của các class Attack
        final_preds_encoded = np.where(all_probs[:, benign_idx] >= t, benign_idx, non_benign_preds)
        
        # Đánh giá nhị phân
        preds_binary = (final_preds_encoded != benign_idx).astype(int)
        
        # Metrics nhị phân
        recall_mal = recall_score(y_true_binary, preds_binary, pos_label=1, zero_division=0)
        recall_ben = recall_score(y_true_binary, preds_binary, pos_label=0, zero_division=0)
        f1_mal = f1_score(y_true_binary, preds_binary, pos_label=1, zero_division=0)
        
        cm = confusion_matrix(y_true_binary, preds_binary)
        if cm.shape == (2, 2):
            fpr = cm[0, 1] / (cm[0, 0] + cm[0, 1])  # FP / Total Benign
        else:
            fpr = 0.0
            
        # Đánh giá Multi-class F1
        f1_macro = f1_score(y_val_encoded, final_preds_encoded, average='macro', zero_division=0)
        
        results.append({
            'threshold': t,
            'f1_macro': f1_macro,
            'recall_malicious': recall_mal,
            'recall_benign': recall_ben,
            'fpr': fpr
        })
        
        # Điều kiện tối ưu: Ưu tiên F1 Macro cao nhất, nhưng vẫn nên giữ FPR thấp
        if f1_macro > best_score:
            best_score = f1_macro
            best_threshold = t
            
    print(f"\n[+] Ngưỡng tối ưu tìm được: {best_threshold:.2f}")
    print(f"    Macro F1 tại ngưỡng này: {best_score:.4f}")
    
    # Lấy thông số tại best threshold
    best_res = [r for r in results if r['threshold'] == best_threshold][0]
    print(f"    Benign Recall:           {best_res['recall_benign']:.4f}")
    print(f"    Malicious Recall:        {best_res['recall_malicious']:.4f}")
    print(f"    False Positive Rate:     {best_res['fpr']:.4f}")
    
    # Lưu Threshold
    out_path = '../models/optimal_threshold.json'
    with open(out_path, 'w') as f:
        json.dump({'optimal_benign_threshold': best_threshold}, f)
    print(f"\n[+] Đã lưu cấu hình ngưỡng vào {out_path}")
    
    # Vẽ biểu đồ
    thresholds_arr = [r['threshold'] for r in results]
    f1_macro_arr = [r['f1_macro'] for r in results]
    rec_mal_arr = [r['recall_malicious'] for r in results]
    rec_ben_arr = [r['recall_benign'] for r in results]
    
    plt.figure(figsize=(10, 6))
    plt.plot(thresholds_arr, f1_macro_arr, label='Macro F1', linewidth=2, color='black')
    plt.plot(thresholds_arr, rec_mal_arr, label='Malicious Recall', linestyle='--')
    plt.plot(thresholds_arr, rec_ben_arr, label='Benign Recall', linestyle='--')
    plt.axvline(best_threshold, color='red', linestyle=':', label=f'Optimal ({best_threshold:.2f})')
    
    plt.title('Threshold Calibration - Trade-off Curves')
    plt.xlabel('Benign Confidence Threshold')
    plt.ylabel('Score')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    os.makedirs('../docs/figures', exist_ok=True)
    plt.savefig('../docs/figures/threshold_calibration.png')
    print("[+] Đã lưu biểu đồ tại: ../docs/figures/threshold_calibration.png")

if __name__ == "__main__":
    main()
