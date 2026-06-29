"""
TESTBED INFERENCE STAGE 3C — HYBRID PIPELINE + SANITY-CHECK
============================================================
Hỗ trợ cả 2 dạng pipeline:
- Unified (1 scaler cho 80 features)
- Hybrid (scaler_77_original + scaler_3_new)
Tự động phát hiện loại pipeline và xử lý tương ứng.
"""
import os
import sys
import pandas as pd
import numpy as np
import torch
import joblib
from sklearn.metrics import classification_report, accuracy_score, balanced_accuracy_score, matthews_corrcoef
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

from models.phase2_ft_transformer_v2 import FTTransformer

# ====================== FEATURE ENGINEERING ======================
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

# ====================== PIPELINE TRANSFORM ======================
def apply_pipeline(X, pipeline):
    """Tự động phát hiện loại pipeline và transform tương ứng."""
    if 'scaler_77_original' in pipeline:
        # Hybrid pipeline
        X_old = X[:, :77]
        X_new = X[:, 77:]
        return np.hstack((
            pipeline['scaler_77_original'].transform(X_old),
            pipeline['scaler_3_new'].transform(X_new)
        ))
    elif 'scaler' in pipeline:
        # Unified pipeline
        return pipeline['scaler'].transform(X)
    else:
        raise ValueError("Pipeline không hợp lệ: thiếu key 'scaler' hoặc 'scaler_77_original'")

# ====================== SANITY-CHECK ======================
def sanity_check(X_raw, train_stats, verbose=True):
    train_mean = np.array(train_stats['raw_mean'])
    train_std = np.array(train_stats['raw_std'])
    threshold = train_stats.get('alert_threshold_std_multiplier', 3.0)
    feature_names = train_stats['feature_names']
    
    new_mean = X_raw.mean(axis=0)
    safe_train_std = np.where(train_std < 1e-10, 1.0, train_std)
    mean_shift = np.abs(new_mean - train_mean) / safe_train_std
    
    flagged = []
    for i in range(len(mean_shift)):
        if mean_shift[i] > threshold:
            flagged.append({
                'name': feature_names[i], 'shift': mean_shift[i],
                'train_mean': train_mean[i], 'new_mean': new_mean[i],
                'train_std': train_std[i], 'new_std': X_raw[:, i].std(),
            })
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"SANITY-CHECK: Phân phối dữ liệu mới vs huấn luyện")
        print(f"{'='*60}")
        print(f"  Ngưỡng: {threshold}σ | Features: {len(mean_shift)} | Lệch: {len(flagged)}")
        
        if flagged:
            print(f"\n  ⚠️  FEATURES BỊ LỆCH:")
            print(f"  {'Feature':<30} {'Shift(σ)':>9} {'Train μ':>12} {'New μ':>12}")
            print(f"  {'-'*65}")
            for f in sorted(flagged, key=lambda x: x['shift'], reverse=True)[:15]:
                print(f"  {f['name']:<30} {f['shift']:>9.2f} {f['train_mean']:>12.2f} {f['new_mean']:>12.2f}")
            print(f"\n  ⚠️  CẢNH BÁO: Domain shift phát hiện. KHÔNG fit scaler mới.")
        else:
            print(f"  ✓ Tất cả OK.")
    
    return len(flagged) == 0, flagged

# ====================== MAIN ======================
def main():
    print("="*60)
    print("TESTBED INFERENCE: STAGE 3C (HYBRID PIPELINE + SANITY-CHECK)")
    print("="*60)
    
    PIPELINE_PATH = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../../Domain_Adaptation_Workspace/models/stage3c_hybrid_pipeline.pkl'))
    MODEL_PATH = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../../Domain_Adaptation_Workspace/models/finetuned_stage3c_hybrid.pt'))
    ENCODER_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/encoder_stage1.pkl'))
    DATA_PATH = 'Raw_Labeled_Dataset.csv'
    
    # [1] Load Pipeline
    print("\n[1] Nạp Hybrid Pipeline...")
    if not os.path.exists(PIPELINE_PATH):
        print(f"[LỖI] Không tìm thấy: {PIPELINE_PATH}")
        print("       Chạy 3c_stage3_hybrid_pipeline.py trước!")
        return
    
    pipeline = joblib.load(PIPELINE_PATH)
    print(f"  Type: {pipeline['scaler_type']}")
    print(f"  Trained on: {pipeline['train_stats']['n_train_samples']} samples")
    
    # [2] Load Data
    print(f"\n[2] Nạp dữ liệu: {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    df = df[df['Label'].isin(['Malicious', 'Benign'])].copy()
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
    y_true = df['Label'].values
    print(f"  Mẫu: {len(X_raw)} (Mal: {sum(y_true=='Malicious')}, Ben: {sum(y_true=='Benign')})")
    
    # [3] Sanity-Check
    print("\n[3] Sanity-Check...")
    sanity_check(X_raw, pipeline['train_stats'])
    
    # [4] Transform (KHÔNG fit lại)
    print(f"\n[4] Transform bằng pipeline đã lưu...")
    X_scaled = apply_pipeline(X_raw, pipeline)
    
    # [5] Load Model
    print("\n[5] Nạp Model Stage 3C...")
    encoder = joblib.load(ENCODER_PATH)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2, drop_path_rate=0.1).to(device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.eval()
    
    # [6] Predict
    print("\n[6] Dự đoán...")
    X_tensor = torch.FloatTensor(X_scaled).to(device)
    all_preds = []
    with torch.no_grad():
        for i in range(0, len(X_tensor), 2048):
            batch = X_tensor[i:i+2048]
            with torch.cuda.amp.autocast():
                logits = model(batch)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
    
    predicted_labels = encoder.inverse_transform(all_preds)
    y_pred_binary = ['Benign' if p == 'Benign' else 'Malicious' for p in predicted_labels]
    
    # [7] Report
    print("\n" + "="*60)
    print("BÁO CÁO: STAGE 3C — HYBRID PIPELINE")
    print("="*60)
    acc = accuracy_score(y_true, y_pred_binary)
    b_acc = balanced_accuracy_score(y_true, y_pred_binary)
    mcc = matthews_corrcoef(y_true, y_pred_binary)
    print(f"Accuracy:          {acc*100:.2f}%")
    print(f"Balanced Accuracy: {b_acc*100:.2f}%")
    print(f"MCC:               {mcc:.4f}")
    print()
    print(classification_report(y_true, y_pred_binary, digits=4))

if __name__ == "__main__":
    main()
