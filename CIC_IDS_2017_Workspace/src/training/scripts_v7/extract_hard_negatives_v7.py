import os
import sys
# Để import được phase2_ft_transformer_v2 từ thư mục cha
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import joblib
import pandas as pd
import numpy as np
from torch.utils.data import DataLoader, Dataset
from phase2_ft_transformer_v2 import FTTransformer
from tqdm import tqdm
import json

class InferenceDataset(Dataset):
    def __init__(self, features):
        self.features = torch.FloatTensor(features)
    def __len__(self): return len(self.features)
    def __getitem__(self, idx): return self.features[idx]

def map_stage2_v7(label):
    if type(label) != str: return None
    if 'Web Attack' in label: return 'Web Attack'
    if label in ['Bot', 'Infiltration', 'Heartbleed', 'BENIGN']: return label.replace('BENIGN', 'Benign')
    return None

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print("Loading Stage 1 Scaler and Encoder...")
    scaler1 = joblib.load('models/v4_cascade/stage1/scaler_stage1.pkl')
    encoder1 = joblib.load('models/v4_cascade/stage1/encoder_stage1.pkl')
    
    print("Loading Stage 2 V5 Scaler and Encoder...")
    scaler2 = joblib.load('models/v5_cascade/stage2/scaler_stage2.pkl')
    encoder2 = joblib.load('models/v5_cascade/stage2/encoder_stage2.pkl')
    
    suspicious_idx = list(encoder1.classes_).index('Suspicious')
    
    print("Loading Full Train Data...")
    df_full = pd.read_csv('data/processed/cic_train_full.csv')
    for col in df_full.select_dtypes(include=['float64']).columns: df_full[col] = df_full[col].astype('float32')
    for col in df_full.select_dtypes(include=['int64']).columns: df_full[col] = df_full[col].astype('int32')
    
    df_full['Label_Stage2_V7'] = df_full['Label'].apply(map_stage2_v7)
    # Lọc ra nhóm nhãn thuộc thẩm quyền xử lý của Stage 2
    df_full = df_full[df_full['Label_Stage2_V7'].notna()].copy()
    
    print("Computing V7 Ratio Features...")
    df_full['Flow_Bytes_Ratio'] = df_full['Total_Length_of_Fwd_Packets'] / (df_full['Total_Length_of_Bwd_Packets'].replace(0, 1))
    df_full['Flow_Pkts_Ratio'] = df_full['Total_Fwd_Packets'] / (df_full['Total_Backward_Packets'].replace(0, 1))
    df_full['Flow_Bytes_Ratio'] = df_full['Flow_Bytes_Ratio'].replace([np.inf, -np.inf], 0).fillna(0)
    df_full['Flow_Pkts_Ratio'] = df_full['Flow_Pkts_Ratio'].replace([np.inf, -np.inf], 0).fillna(0)
    
    cols_to_drop = ['Label', 'Label_Stage1', 'Label_Stage2', 'Label_Stage2_V7', 'Flow_Bytes_Ratio', 'Flow_Pkts_Ratio']
    feature_cols_s1 = [c for c in df_full.columns if c not in cols_to_drop]
    
    print("Extracting and Scaling features for Stage 1...")
    X_s1_raw = df_full[feature_cols_s1].values
    X_s1_scaled = scaler1.transform(X_s1_raw)
    
    print("Loading Stage 1 Model...")
    model1 = FTTransformer(num_features=X_s1_scaled.shape[1], num_classes=len(encoder1.classes_), 
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2, drop_path_rate=0.1).to(device)
    model1.load_state_dict(torch.load('models/v4_cascade/stage1/best_stage1_model.pt', map_location=device))
    model1.eval()
    
    dataset1 = InferenceDataset(X_s1_scaled)
    loader1 = DataLoader(dataset1, batch_size=2048, shuffle=False, num_workers=4)
    
    preds1 = []
    print("Running Inference on Train Set (Stage 1)...")
    with torch.no_grad():
        for features in tqdm(loader1, desc="Predicting Stage 1"):
            features = features.to(device)
            with torch.cuda.amp.autocast():
                logits = model1(features)
            preds1.extend(torch.argmax(logits, dim=1).cpu().numpy())
            
    df_full['Pred_Stage1'] = np.array(preds1)
    
    # Những mẫu bị Stage 1 coi là Suspicious (bao gồm cả True Positive và Hard Negative của Stage 1)
    df_stage1_suspicious = df_full[df_full['Pred_Stage1'] == suspicious_idx].copy()
    print(f"\nStage 1 forwarded {len(df_stage1_suspicious)} samples to Stage 2 (out of {len(df_full)} possible).")
    
    # ------------------------------------------------------------------------------------------------
    # THỰC THI CHIẾN DỊCH 2: DOUBLE HARD NEGATIVE MINING CHO BOTNET
    # Chạy Stage 2 V5 model trên tập `df_stage1_suspicious` để tìm các mẫu Benign bị nhầm thành Botnet
    # ------------------------------------------------------------------------------------------------
    STAGE2_FEATURES_V5 = [
        'Port_Is_Web', 'Port_Is_RemoteAccess', 'Port_Is_WellKnown',
        'Port_Is_Registered', 'Port_Is_Ephemeral',
        'Flow_IAT_Max', 'Flow_IAT_Min', 'Flow_IAT_Mean', 'Flow_IAT_Std',
        'Fwd_IAT_Max', 'Fwd_IAT_Std',
        'Packet_Length_Variance', 'Packet_Length_Std', 'Packet_Length_Mean',
        'Average_Packet_Size', 'Fwd_Packet_Length_Max',
        'Flow_Duration', 'Flow_Bytes_s',
        'Custom_Pkt_Var_Ratio', 'Custom_IAT_Anomaly',
        'Fwd_Header_Length', 'Bwd_Header_Length', 
        'Avg_Fwd_Segment_Size', 'Avg_Bwd_Segment_Size', 'min_seg_size_forward',
        'Init_Win_bytes_forward', 'Init_Win_bytes_backward',
        'Subflow_Fwd_Bytes', 'Subflow_Bwd_Bytes'
    ]
    
    X_s2_raw = df_stage1_suspicious[STAGE2_FEATURES_V5].values
    X_s2_scaled = scaler2.transform(X_s2_raw)
    
    print("\nLoading Stage 2 V5 Model for Botnet Hard Negative Mining...")
    model2 = FTTransformer(num_features=29, num_classes=len(encoder2.classes_), 
                          d_model=64, num_layers=3, num_heads=4, dropout=0.2, drop_path_rate=0.1).to(device)
    model2.load_state_dict(torch.load('models/v5_cascade/stage2/best_stage2_model.pt', map_location=device))
    model2.eval()
    
    dataset2 = InferenceDataset(X_s2_scaled)
    loader2 = DataLoader(dataset2, batch_size=2048, shuffle=False, num_workers=4)
    
    preds2 = []
    print("Running Inference on Stage 1 Suspicious Set (Stage 2 V5)...")
    with torch.no_grad():
        for features in tqdm(loader2, desc="Predicting Stage 2"):
            features = features.to(device)
            with torch.cuda.amp.autocast():
                logits = model2(features)
            preds2.extend(torch.argmax(logits, dim=1).cpu().numpy())
            
    df_stage1_suspicious['Pred_Stage2_Idx'] = np.array(preds2)
    df_stage1_suspicious['Pred_Stage2_Label'] = encoder2.inverse_transform(df_stage1_suspicious['Pred_Stage2_Idx'])
    
    # Tìm tập Botnet FP: Label thực tế là Benign, nhưng Stage 2 V5 dự đoán là Bot
    df_botnet_fp = df_stage1_suspicious[(df_stage1_suspicious['Label_Stage2_V7'] == 'Benign') & 
                                        (df_stage1_suspicious['Pred_Stage2_Label'] == 'Bot')].copy()
    
    print(f"\n=> FOUND {len(df_botnet_fp)} Botnet False Positive samples! Amplifying them...")
    
    # ------------------------------------------------------------------------------------------------
    # TỔNG HỢP DỮ LIỆU
    # ------------------------------------------------------------------------------------------------
    # Lấy thêm Easy Benign
    df_easy_benign = df_full[(df_full['Pred_Stage1'] != suspicious_idx) & (df_full['Label_Stage2_V7'] == 'Benign')]
    num_easy = min(50000, len(df_easy_benign))
    print(f"Sampling {num_easy} easy Benign samples to maintain distribution...")
    df_easy_benign = df_easy_benign.sample(n=num_easy, random_state=42)
    
    # Gộp tất cả lại (Bơm thêm trọng số bằng cách nhân bản df_botnet_fp 10 lần)
    df_stage2_combined = pd.concat([
        df_stage1_suspicious, 
        df_easy_benign,
        *[df_botnet_fp] * 10  # Nhân bản 10 lần Botnet FP
    ], ignore_index=True)
    
    df_stage2_combined = df_stage2_combined.sample(frac=1.0, random_state=42).reset_index(drop=True)
    
    # ------------------------------------------------------------------------------------------------
    # THỰC THI CHIẾN DỊCH 1: BỔ SUNG ĐẶC TRƯNG CHO INFILTRATION
    # ------------------------------------------------------------------------------------------------
    STAGE2_FEATURES_V7 = STAGE2_FEATURES_V5 + [
        'Bwd_Packet_Length_Std', 
        'Bwd_Packet_Length_Max', 
        'PSH_Flag_Count',
        'Flow_Bytes_Ratio',
        'Flow_Pkts_Ratio'
    ]
    
    print(f"\nNew Feature Space length for V7: {len(STAGE2_FEATURES_V7)} features.")
    
    df_stage2_final = df_stage2_combined[STAGE2_FEATURES_V7 + ['Label_Stage2_V7']].copy()
    df_stage2_final.rename(columns={'Label_Stage2_V7': 'Label'}, inplace=True)
    
    out_path = 'data/processed/cic_train_stage2_v7_hard.csv'
    df_stage2_final.to_csv(out_path, index=False)
    print(f"\nSaved Hard Negative dataset (V7) to {out_path} ({len(df_stage2_final)} rows)")

if __name__ == "__main__":
    main()
