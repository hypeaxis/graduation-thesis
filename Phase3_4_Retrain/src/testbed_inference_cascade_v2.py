"""
TESTBED INFERENCE CASCADE V2
============================================================
Thực hiện inference kết hợp:
- Stage 1: v4_hybrid_model.pt (Testbed Finetuned trên run5) - 80 features
- Stage 2: v7_cascade Stage 2 (RF, KNN, FT-Transformer gốc của CIC-IDS) - 78 features
Mục tiêu: Dùng Stage 2 để khắc phục lỗi Overconfidence (Benign bị nhận nhầm thành Attack) của Stage 1.
"""
import os
import sys
import pandas as pd
import numpy as np
import torch
import joblib
import json
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score, matthews_corrcoef, accuracy_score
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

from models.phase2_ft_transformer_v2 import FTTransformer
from hybrid_feature_scaler import HybridFeatureScaler

# ====================== FEATURE ENGINEERING ======================
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

# ALL 9 CLASSES OF CASCADE SYSTEM
ALL_9_CLASSES = [
    'Benign', 'Bot', 'Brute Force', 'DDoS', 'DoS', 'Heartbleed', 'Infiltration', 'PortScan', 'Web Attack'
]

# ====================== MAIN ======================
def main():
    print("="*60)
    print("TESTBED INFERENCE CASCADE V2 (FULL 9-CLASS EVALUATION)")
    print("="*60)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # ----------------------------------------------------
    # LOAD STAGE 1 (TESTBED FINETUNED V4)
    # ----------------------------------------------------
    print("\n[1] Nạp Stage 1 (Mô hình Testbed v4 - 80 features)...")
    SCALER_PATH_S1 = '../models/v4_hybrid_pipeline.pkl'
    MODEL_PATH_S1 = '../models/v4_hybrid_model.pt'
    ENCODER_PATH_S1 = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/encoder_stage1.pkl'))
    
    scaler_s1 = HybridFeatureScaler.load(SCALER_PATH_S1)
    encoder_s1 = joblib.load(ENCODER_PATH_S1)
    
    model_s1 = FTTransformer(num_features=80, num_classes=len(encoder_s1.classes_),
                             d_model=128, num_layers=4, num_heads=8, dropout=0.2).to(device)
    model_s1.load_state_dict(torch.load(MODEL_PATH_S1, map_location=device))
    model_s1.eval()
    
    # ----------------------------------------------------
    # LOAD STAGE 2 (ORIGINAL CIC-IDS V7)
    # ----------------------------------------------------
    print("\n[2] Nạp Stage 2 (Mô hình gốc CIC-IDS-2017 v7_cascade)...")
    STAGE2_DIR = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/v7_cascade/stage2'))
    scaler_s2 = joblib.load(os.path.join(STAGE2_DIR, 'scaler_stage2.pkl'))
    encoder_s2 = joblib.load(os.path.join(STAGE2_DIR, 'encoder_stage2.pkl'))
    
    with open(os.path.join(STAGE2_DIR, 'stage2_features.json'), 'r') as f:
        STAGE2_FEATURES_V7 = json.load(f)
        
    num_features_s2 = len(STAGE2_FEATURES_V7)
    model_s2_ft = FTTransformer(num_features=num_features_s2, num_classes=len(encoder_s2.classes_), 
                                d_model=64, num_layers=3, num_heads=4, dropout=0.2, drop_path_rate=0.1).to(device)
    model_s2_ft.load_state_dict(torch.load(os.path.join(STAGE2_DIR, 'best_stage2_ema.pt'), map_location=device))
    model_s2_ft.eval()
    
    rf_model = joblib.load(os.path.join(STAGE2_DIR, 'best_rf_model.pkl'))
    knn_model = joblib.load(os.path.join(STAGE2_DIR, 'best_knn_model.pkl'))
    
    # ----------------------------------------------------
    # LOAD & PROCESS DATA
    # ----------------------------------------------------
    # Dùng RUN6 cho test thực chiến
    DATA_PATH = '../data/Cleaned_Labeled_Dataset_run6.csv'
    print(f"\n[3] Nạp tập dữ liệu thực chiến: {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    
    # Lọc mẫu hợp lệ (chỉ test trên các lớp đã biết)
    valid_mask = df['Label'].isin(encoder_s1.classes_)
    df = df[valid_mask].copy()
    
    # Tính features phụ cho Stage 2 (như trong CIC-IDS v7)
    df['Flow_Bytes_Ratio'] = df['Total_Length_of_Fwd_Packets'] / (df['Total_Length_of_Bwd_Packets'].replace(0, 1))
    df['Flow_Pkts_Ratio'] = df['Total_Fwd_Packets'] / (df['Total_Backward_Packets'].replace(0, 1))
    
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    
    for c in EXPECTED_FEATURES_80:
        if c not in df.columns:
            df[c] = 0
            
    X_raw_s1 = df[EXPECTED_FEATURES_80].values
    y_true = df['Label'].values
    
    # ----------------------------------------------------
    # PREDICT STAGE 1
    # ----------------------------------------------------
    print(f"\n[4] Dự đoán Stage 1 (Mô hình Testbed 80 features)...")
    X_scaled_s1 = scaler_s1.transform(X_raw_s1)
    
    X_tensor_s1 = torch.FloatTensor(X_scaled_s1).to(device)
    s1_preds_idx = []
    
    with torch.no_grad():
        for i in range(0, len(X_tensor_s1), 2048):
            batch = X_tensor_s1[i:i+2048]
            with torch.cuda.amp.autocast():
                logits = model_s1(batch)
            s1_preds_idx.extend(torch.argmax(logits, dim=1).cpu().numpy())
            
    s1_preds_idx = np.array(s1_preds_idx)
    s1_preds_label = encoder_s1.inverse_transform(s1_preds_idx)
    
    # ----------------------------------------------------
    # PREDICT STAGE 2 & ENSEMBLE
    # ----------------------------------------------------
    print(f"\n[5] Phân giải Stage 2 (Loại bỏ False Positives) và Gộp nhãn...")
    
    final_preds = np.empty(len(df), dtype=object)
    
    # Điều kiện để chuyển vào Stage 2: 
    # Nếu Stage 1 không dự đoán Benign, ta coi đó là "Suspicious" và đẩy qua Stage 2
    mask_stage2 = (s1_preds_label != 'Benign')
    
    # Xử lý các mẫu được Stage 1 dự đoán là Benign (Không vào Stage 2)
    final_preds[~mask_stage2] = 'Benign'
    
    if mask_stage2.sum() > 0:
        print(f"  → Chuyển {mask_stage2.sum()} mẫu nhận diện là Attack (Suspicious) vào Stage 2...")
        df_s2 = df[mask_stage2].copy()
        
        for f in STAGE2_FEATURES_V7:
            if f not in df_s2.columns:
                df_s2[f] = 0
                
        X_s2_raw = df_s2[STAGE2_FEATURES_V7].values
        X_s2_scaled = scaler_s2.transform(X_s2_raw)
        
        # FT-Transformer Stage 2
        X_tensor_s2 = torch.FloatTensor(X_s2_scaled).to(device)
        ft_preds_idx = []
        ft_probs_max = []
        with torch.no_grad():
            for i in range(0, len(X_tensor_s2), 2048):
                batch = X_tensor_s2[i:i+2048]
                with torch.cuda.amp.autocast():
                    logits = model_s2_ft(batch)
                    probs = torch.softmax(logits, dim=1)
                max_probs, preds = torch.max(probs, dim=1)
                ft_preds_idx.extend(preds.cpu().numpy())
                ft_probs_max.extend(max_probs.cpu().numpy())
                
        ft_preds_label = encoder_s2.inverse_transform(ft_preds_idx)
        
        # RF & KNN Stage 2
        rf_preds_idx = rf_model.predict(X_s2_scaled)
        knn_preds_idx = knn_model.predict(X_s2_scaled)
        rf_preds_label = encoder_s2.inverse_transform(rf_preds_idx)
        knn_preds_label = encoder_s2.inverse_transform(knn_preds_idx)
        
        # Ensemble Logic
        inf_thresh = 0.68
        stage2_final = np.empty(len(ft_preds_label), dtype=object)
        
        # Lưu lại nhãn dự đoán của Stage 1 để tham chiếu (vd: nếu S2 không sure, giữ nguyên S1)
        s1_original_preds = s1_preds_label[mask_stage2]
        
        for j in range(len(ft_preds_label)):
            ft_l = ft_preds_label[j]
            rf_l = rf_preds_label[j]
            knn_l = knn_preds_label[j]
            prob = ft_probs_max[j]
            s1_l = s1_original_preds[j]
            
            # Nếu FT-Transformer nói là Benign -> Chắc chắn là Benign (Khắc phục False Positive)
            if ft_l == 'Benign':
                stage2_final[j] = 'Benign'
            else:
                # Nếu các model truyền thống đồng thuận nó là Attack, tin theo FT-Transformer S2
                if rf_l != 'Benign' or knn_l != 'Benign':
                    stage2_final[j] = ft_l
                # Nếu RF/KNN cho là Benign nhưng FT tự tin cao
                elif prob >= 0.75:
                    stage2_final[j] = ft_l
                else:
                    stage2_final[j] = 'Benign'
                    
        final_preds[mask_stage2] = stage2_final
    else:
        print("  → Không có mẫu nào thỏa mãn ngưỡng Suspicious để vào Stage 2.")

    # ----------------------------------------------------
    # EVALUATION
    # ----------------------------------------------------
    print("\n" + "="*60)
    print("BÁO CÁO PHÂN LỚP ĐẦY ĐỦ 9 CLASS (CASCADE SYSTEM - RUN6)")
    print("="*60)
    
    b_acc = balanced_accuracy_score(y_true, final_preds)
    acc = accuracy_score(y_true, final_preds)
    mcc = matthews_corrcoef(y_true, final_preds)
    
    print(f"Accuracy:          {acc:.4f}")
    print(f"Balanced Accuracy: {b_acc:.4f}")
    print(f"MCC:               {mcc:.4f}\n")
    
    print("\n" + classification_report(y_true, final_preds, labels=ALL_9_CLASSES, digits=4, zero_division=0))
    
    print("\nMA TRẬN NHẦM LẪN CHI TIẾT (Confusion Matrix):")
    # Tự động trích xuất các label có support > 0 trong run6 + Benign
    active_labels = np.unique(y_true)
    cm = confusion_matrix(y_true, final_preds, labels=active_labels)
    cm_df = pd.DataFrame(cm, index=[f"True_{l}" for l in active_labels], 
                         columns=[f"Pred_{l}" for l in active_labels])
    print(cm_df.to_string())

if __name__ == "__main__":
    main()
