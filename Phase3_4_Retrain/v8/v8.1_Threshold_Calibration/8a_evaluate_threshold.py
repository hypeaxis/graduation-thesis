import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, confusion_matrix
import joblib

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)
PHASE_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
sys.path.append(PHASE_SRC_DIR)

try:
    from models.phase2_ft_transformer_v2 import FTTransformer
    from hybrid_feature_scaler import HybridFeatureScaler
except ImportError:
    print("Cannot import FTTransformer. Please check WORKSPACE_DIR.")
    sys.exit(1)

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

def load_and_preprocess(filepath, expected_features):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
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
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    for c in expected_features:
        if c not in df.columns:
            df[c] = 0
            
    X = df[expected_features].values
    y = df['Label'].values
    return X, y

def print_metrics(y_true, y_pred, encoder, title):
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    
    acc = accuracy_score(y_true, y_pred)
    b_acc = balanced_accuracy_score(y_true, y_pred)
    
    print(f"Overall Accuracy:  {acc:.4f}")
    print(f"Balanced Accuracy: {b_acc:.4f}")
    
    print("\n--- Detailed Classification Report ---")
    print(classification_report(y_true, y_pred, digits=4))
    
    print("--- Confusion Matrix Tuyệt Đối ---")
    cm = confusion_matrix(y_true, y_pred, labels=encoder.classes_)
    cm_df = pd.DataFrame(cm, index=[f"True_{c}" for c in encoder.classes_], 
                         columns=[f"Pred_{c}" for c in encoder.classes_])
    print(cm_df)

def eval_model_with_thresholds(model, X_scaled, y_true_labels, encoder, device='cuda'):
    model.eval()
    X_tensor = torch.FloatTensor(X_scaled).to(device)
    batch_size = 512
    
    all_probs = []
    
    print("[*] Inference trên Test Set...")
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                logits = model(batch)
                # Dùng softmax để chuyển logit thành xác suất (0-1)
                probs = torch.softmax(logits, dim=1).cpu().numpy()
            all_probs.append(probs)
            
    all_probs = np.vstack(all_probs)
    
    # Baseline: Ngưỡng mặc định (Argmax)
    default_preds = np.argmax(all_probs, axis=1)
    default_pred_labels = encoder.inverse_transform(default_preds)
    print_metrics(y_true_labels, default_pred_labels, encoder, "KẾT QUẢ V7 GỐC (DEFAULT ARGMAX)")
    
    portscan_idx = encoder.transform(['PortScan'])[0]
    
    # Thử nghiệm các ngưỡng nhạy cảm cho PortScan
    thresholds_to_try = [0.10, 0.15, 0.20, 0.30]
    
    for threshold in thresholds_to_try:
        custom_preds = []
        for prob in all_probs:
            # Nếu xác suất của PortScan lớn hơn ngưỡng -> Ép kết quả thành PortScan
            if prob[portscan_idx] > threshold:
                custom_preds.append(portscan_idx)
            else:
                custom_preds.append(np.argmax(prob))
                
        custom_pred_labels = encoder.inverse_transform(custom_preds)
        print_metrics(y_true_labels, custom_pred_labels, encoder, f"KẾT QUẢ V8.1 (PORTSCAN THRESHOLD = {threshold})")

def main():
    print("="*60)
    print("V8.1. ĐÁNH GIÁ THRESHOLD CALIBRATION")
    print("="*60)

    # Load từ V7 Archive
    DATA_TEST_PATH = '../../data/run7_test.csv'
    MODEL_PATH = '../../archive_v7_run7/models/v7_model.pt'
    ENCODER_PATH = '../../archive_v7_run7/models/v7_encoder.pkl'
    PIPELINE_PATH = '../../archive_v7_run7/models/v7_hybrid_pipeline.pkl'
    
    print(f"[*] Nạp Test Data: {DATA_TEST_PATH}...")
    X_test, y_test = load_and_preprocess(DATA_TEST_PATH, EXPECTED_FEATURES_80)
    
    print("[*] Load Encoder & Scaler từ V7...")
    encoder = joblib.load(ENCODER_PATH)
    scaler = HybridFeatureScaler.load(PIPELINE_PATH)
    X_test_scaled = scaler.transform(X_test)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = FTTransformer(num_features=80, num_classes=5, d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model = model.to(device)
    
    eval_model_with_thresholds(model, X_test_scaled, y_test, encoder, device)

if __name__ == "__main__":
    main()
