import os
import sys
import json
import datetime
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, balanced_accuracy_score, matthews_corrcoef, confusion_matrix, precision_recall_fscore_support
import joblib
import warnings
warnings.filterwarnings('ignore')

# Gắn path vào Workspace cũ để xài chung file model
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

try:
    from models.phase2_ft_transformer_v2 import FTTransformer
except ImportError:
    print("Cannot import FTTransformer. Check path.")

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

def load_and_preprocess(filepath, expected_features):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    
    # Feature 80
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    for c in expected_features:
        if c not in df.columns:
            df[c] = 0
            
    X = df[expected_features].values
    y = df['Label'].values
    return X, y

def eval_model(model, X_scaled, y, encoder, batch_size=512, device='cuda'):
    model.eval()
    X_tensor = torch.FloatTensor(X_scaled).to(device)
    all_preds = []
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                logits = model(batch)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            
    y_pred_labels = encoder.inverse_transform(all_preds)
    
    # Đo multi-class evaluation
    b_acc = balanced_accuracy_score(y, y_pred_labels)
    acc = accuracy_score(y, y_pred_labels)
    cm = confusion_matrix(y, y_pred_labels, labels=encoder.classes_)
    
    return {
        'balanced_accuracy': b_acc,
        'accuracy': acc,
        'confusion_matrix': cm
    }

def main():
    print("="*60)
    print("GIAI ĐOẠN 4: REFIT & RETRAIN VỚI DỮ LIỆU RUN5")
    print("="*60)

    # PATHS
    DATA_TRAIN_PATH = '../data/Cleaned_Labeled_Dataset_run5.csv'
    CIC_TRAIN_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../data/processed/cic_train_full.csv'))
    BASE_MODEL_DIR = os.path.abspath(os.path.join(WORKSPACE_DIR, '../../Domain_Adaptation_Workspace/models'))
    BASE_MODEL_PATH = os.path.join(BASE_MODEL_DIR, 'finetuned_stage3c_hybrid.pt')
    SCALER_77_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/scaler_stage1.pkl'))
    ENCODER_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/encoder_stage1.pkl'))
    
    SCALER_SAVE_PATH = '../models/v4_hybrid_pipeline.pkl'
    MODEL_SAVE_PATH = '../models/v4_hybrid_model.pt'
    
    os.makedirs('../models', exist_ok=True)
    
    encoder = joblib.load(ENCODER_PATH)

    # 1. LOAD DATA
    print("[*] Nạp tập dữ liệu run5...")
    X_tb, y_tb = load_and_preprocess(DATA_TRAIN_PATH, EXPECTED_FEATURES_80)
    
    # Map testbed labels to standard ones if needed. 
    # run5 uses ['Benign', 'DoS', 'PortScan', 'Brute Force', 'Web Attack']
    # Let's map everything to uppercase/standardized if needed, but CIC-IDS uses ['Benign', 'Bot', 'Brute Force', 'DoS', 'Infiltration', 'PortScan', 'Web Attack']
    
    # Tách train/val
    X_tb_train, X_tb_val, y_tb_train, y_tb_val = train_test_split(
        X_tb, y_tb, test_size=0.2, random_state=42, stratify=y_tb)
        
    print(f"    Train size: {len(X_tb_train)}, Val size: {len(X_tb_val)}")
    
    print("[*] Nạp CIC-IDS-2017 (Mixed Train Data)...")
    # Tương tự như 3c_stage3, load tập CIC-IDS
    df_cic = pd.read_csv(CIC_TRAIN_PATH)
    if 'Label_Stage1' in df_cic.columns:
        df_cic['Label'] = df_cic['Label_Stage1']
    df_cic = df_cic.sample(n=30000, random_state=42)
    # Lọc các cột bị thiếu
    for c in EXPECTED_FEATURES_80:
        if c not in df_cic.columns:
            df_cic[c] = 0
    X_cic = df_cic[EXPECTED_FEATURES_80].values
    y_cic = df_cic['Label'].values
    
    # Ghép 2 tập (Testbed run5 + CIC-IDS)
    X_mixed = np.vstack((X_tb_train, X_cic))
    y_mixed = np.concatenate((y_tb_train, y_cic))
    print(f"    Mixed training set size: {len(X_mixed)}")
    
    # 2. FIT SCALER
    print("[*] Khởi tạo HybridFeatureScaler...")
    scaler = HybridFeatureScaler(scaler_77_path=SCALER_77_PATH)
    
    print("[*] Fit scaler 3 custom feature trên Mixed Data...")
    X_mixed_new = X_mixed[:, 77:]
    scaler.fit_custom_scaler(X_mixed_new)
    
    # Save scaler
    scaler.save(SCALER_SAVE_PATH)
    
    # Transform
    X_mixed_scaled = scaler.transform(X_mixed)
    X_val_scaled = scaler.transform(X_tb_val)
    
    # 3. MODEL SURGERY
    print("\n[*] Nạp Base Model và thực hiện Model Surgery...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    model.load_state_dict(torch.load(BASE_MODEL_PATH, map_location='cpu'))
    model = model.to(device)
    
    # Freeze 77 embeddings, train 3 embeddings
    for i in range(77):
        for param in model.feature_embedding.feature_embeddings[i].parameters():
            param.requires_grad = False
    
    # Tương tự như stage 3c, cho phép train classifier và vài block cuối nếu cần.
    # Ở đây freeze cả transformer block 0,1 để tránh mất biểu diễn cốt lõi.
    for param in model.transformer_blocks[0].parameters():
        param.requires_grad = False
    for param in model.transformer_blocks[1].parameters():
        param.requires_grad = False
        
    for i in range(77, 80):
        for param in model.feature_embedding.feature_embeddings[i].parameters():
            param.requires_grad = True
            
    # 4. TRAINING
    print("\n[*] Tính Class Weights và chuẩn bị Data Loader...")
    # Loại bỏ các mẫu có nhãn không có trong encoder
    valid_mask = np.isin(y_mixed, encoder.classes_)
    X_train_clean = X_mixed_scaled[valid_mask]
    y_train_clean = y_mixed[valid_mask]
    
    y_encoded = torch.LongTensor(encoder.transform(y_train_clean)).to(device)
    X_tensor = torch.FloatTensor(X_train_clean).to(device)
    
    class_counts = np.bincount(y_encoded.cpu().numpy(), minlength=len(encoder.classes_))
    # Chặn việc chia cho 0
    class_counts = np.where(class_counts == 0, 1e6, class_counts)
    class_weights = len(y_encoded) / (len(encoder.classes_) * class_counts)
    
    # Điều chỉnh class weights: Brute Force và Web Attack quá ít mẫu, tăng cường mạnh.
    # (Do Testbed run5 có Brute Force và Web Attack rất ít)
    # class_weights[encoder.transform(['Brute Force'])[0]] *= 5.0
    
    class_weights = torch.FloatTensor(class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()), lr=1e-5, weight_decay=1e-4)
    
    dataset = torch.utils.data.TensorDataset(X_tensor, y_encoded)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=True)
    
    best_b_acc = -1
    epochs = 15
    
    val_valid_mask = np.isin(y_tb_val, encoder.classes_)
    X_val_clean = X_val_scaled[val_valid_mask]
    y_val_clean = y_tb_val[val_valid_mask]
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for bx, by in dataloader:
            optimizer.zero_grad()
            with torch.cuda.amp.autocast():
                logits = model(bx)
                loss = criterion(logits, by)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        # Eval multi-class
        val_m = eval_model(model, X_val_clean, y_val_clean, encoder, device=device)
        print(f"  Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(dataloader):.4f} | "
              f"Val Balanced Acc: {val_m['balanced_accuracy']:.4f} | "
              f"Val Acc: {val_m['accuracy']:.4f}")
              
        if val_m['balanced_accuracy'] > best_b_acc:
            best_b_acc = val_m['balanced_accuracy']
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"   -> Đã lưu checkpoint tốt nhất! (B-Acc: {best_b_acc:.4f})")
            
    print("\n[+] Đã hoàn thành quá trình Retrain!")
    print(f"  Model saved to: {MODEL_SAVE_PATH}")
    print(f"  Pipeline saved to: {SCALER_SAVE_PATH}")

if __name__ == "__main__":
    main()
