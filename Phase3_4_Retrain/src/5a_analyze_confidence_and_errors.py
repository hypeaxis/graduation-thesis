import os
import sys
import numpy as np
import pandas as pd
import torch
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

try:
    from models.phase2_ft_transformer_v2 import FTTransformer
except ImportError:
    print("Cannot import FTTransformer.")

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

def main():
    print("=========================================================")
    print("5A. PHÂN TÍCH OVERCONFIDENCE VÀ FALSE POSITIVES")
    print("=========================================================")

    TEST_DATA_PATH = '../data/Cleaned_Labeled_Dataset_run5.csv'
    SCALER_PATH = '../models/v4_hybrid_pipeline.pkl'
    MODEL_PATH = '../models/v4_hybrid_model.pt'
    ENCODER_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/encoder_stage1.pkl'))
    
    # 1. NẠP DỮ LIỆU
    df_raw = pd.read_csv(TEST_DATA_PATH)
    df_raw.columns = df_raw.columns.str.strip()
    df_mapped = map_cicflowmeter_v4_to_v3(df_raw.copy())
    
    encoder = joblib.load(ENCODER_PATH)
    valid_mask = df_mapped['Label'].isin(encoder.classes_)
    df_valid = df_mapped[valid_mask].copy()
    
    from sklearn.model_selection import train_test_split
    _, df_val = train_test_split(df_valid, test_size=0.2, random_state=42, stratify=df_valid['Label'])
    df_valid = df_val.copy()
    
    df_valid.replace([np.inf, -np.inf], 0, inplace=True)
    df_valid.fillna(0, inplace=True)
    
    for c in EXPECTED_FEATURES_80:
        if c not in df_valid.columns:
            df_valid[c] = 0
            
    X_test = df_valid[EXPECTED_FEATURES_80].values
    y_test = df_valid['Label'].values
    
    print(f"Tổng số mẫu hợp lệ: {len(X_test)}")
    
    # 2. TRANSFORM
    scaler = HybridFeatureScaler.load(SCALER_PATH)
    X_scaled = scaler.transform(X_test)
    
    # 3. PREDICT (CÓ LẤY SOFTMAX PROBABILITY)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
    model.to(device)
    model.eval()
    
    X_tensor = torch.FloatTensor(X_scaled).to(device)
    batch_size = 512
    all_preds = []
    all_max_probs = []
    all_probs = []
    
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                logits = model(batch)
                probs = torch.softmax(logits, dim=1)
            
            max_probs, preds = torch.max(probs, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_max_probs.extend(max_probs.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            
    y_pred_labels = encoder.inverse_transform(all_preds)
    
    df_valid['Predicted_Label'] = y_pred_labels
    df_valid['Confidence'] = all_max_probs
    
    # 4. PLOT CONFIDENCE HISTOGRAM
    os.makedirs('../docs/figures', exist_ok=True)
    fig_path = '../docs/figures/confidence_histogram.png'
    plt.figure(figsize=(10, 6))
    sns.histplot(data=df_valid, x='Confidence', hue='Label', bins=20, multiple="stack")
    plt.title('Phân phối Confidence Score của Model (Giai đoạn 4)')
    plt.xlabel('Confidence (Max Softmax Probability)')
    plt.ylabel('Số lượng mẫu')
    plt.savefig(fig_path)
    print(f"\n[+] Đã lưu biểu đồ phân phối Confidence tại: {fig_path}")
    
    mean_conf = np.mean(all_max_probs)
    print(f"Confidence trung bình của model: {mean_conf:.4f}")
    
    # 5. PHÂN TÍCH FALSE POSITIVE (BENIGN -> BRUTE FORCE)
    print("\n[+] Phân tích các mẫu Benign bị nhận diện nhầm thành Brute Force:")
    fp_mask = (df_valid['Label'] == 'Benign') & (df_valid['Predicted_Label'] == 'Brute Force')
    df_fp = df_valid[fp_mask]
    
    print(f"  Số lượng Benign bị nhận nhầm thành Brute Force: {len(df_fp)}")
    if len(df_fp) > 0:
        print("  Confidence trung bình trên các mẫu nhận nhầm này: {:.4f}".format(df_fp['Confidence'].mean()))
        
        # In thử vài thông số của 5 mẫu FP đầu tiên
        print("\n  [Sample] 5 mẫu FP đầu tiên:")
        display_cols = ['Destination_Port', 'Flow_Duration', 'Total_Fwd_Packets', 'Total_Backward_Packets', 'Custom_Fwd_Pkt_Rate', 'Confidence']
        # Đảm bảo cột tồn tại
        display_cols = [c for c in display_cols if c in df_fp.columns]
        print(df_fp[display_cols].head(5).to_string())
        
        # So sánh đặc trưng của Brute Force thật và Benign (bị nhận nhầm)
        true_bf_mask = (df_valid['Label'] == 'Brute Force')
        df_true_bf = df_valid[true_bf_mask]
        
        print("\n  [So sánh] Giá trị trung bình của Brute Force thật vs. Benign bị nhận nhầm:")
        if len(df_true_bf) > 0:
            compare_df = pd.DataFrame({
                'True_Brute_Force': df_true_bf[display_cols].mean(),
                'False_Positive_Benign': df_fp[display_cols].mean()
            })
            print(compare_df.to_string())

if __name__ == "__main__":
    main()
