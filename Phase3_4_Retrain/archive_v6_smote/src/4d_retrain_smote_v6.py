import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix
import joblib
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE
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

class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, weight=None, label_smoothing=0.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.gamma = gamma
        self.weight = weight
        self.label_smoothing = label_smoothing
        self.reduction = reduction

    def forward(self, inputs, targets):
        ce_loss = nn.functional.cross_entropy(
            inputs, targets, 
            reduction='none', 
            weight=self.weight,
            label_smoothing=self.label_smoothing
        )
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

def load_and_preprocess(filepath, expected_features):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    
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
    print("GIAI ĐOẠN 4D: RETRAIN V6 (SMOTE + FULL UNFREEZE)")
    print("="*60)

    # PATHS
    DATA_TRAIN_PATH = '../data/Cleaned_Labeled_Dataset_run5.csv'
    BASE_MODEL_DIR = os.path.abspath(os.path.join(WORKSPACE_DIR, '../../Domain_Adaptation_Workspace/models'))
    BASE_MODEL_PATH = os.path.join(BASE_MODEL_DIR, 'finetuned_stage3c_hybrid.pt')
    SCALER_77_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/scaler_stage1.pkl'))
    
    SCALER_SAVE_PATH = '../models/v6_hybrid_pipeline.pkl'
    MODEL_SAVE_PATH = '../models/v6_smote_model.pt'
    ENCODER_SAVE_PATH = '../models/v6_encoder.pkl'
    
    os.makedirs('../models', exist_ok=True)
    
    # 1. TẠO ENCODER
    print("[*] Tạo Encoder 5 classes mới...")
    target_classes = ['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']
    encoder = LabelEncoder()
    encoder.fit(target_classes)
    joblib.dump(encoder, ENCODER_SAVE_PATH)
    print(f"    Classes: {encoder.classes_}")

    # 2. LOAD DATA
    print("\n[*] Nạp tập dữ liệu run5...")
    X_tb, y_tb = load_and_preprocess(DATA_TRAIN_PATH, EXPECTED_FEATURES_80)
    
    valid_mask = np.isin(y_tb, encoder.classes_)
    X_tb = X_tb[valid_mask]
    y_tb = y_tb[valid_mask]
    
    # 3. SPLIT & SCALE
    X_tb_train, X_tb_val, y_tb_train, y_tb_val = train_test_split(
        X_tb, y_tb, test_size=0.2, random_state=42, stratify=y_tb)
        
    print(f"    Train origin: {len(X_tb_train)}, Val: {len(X_tb_val)}")
    
    scaler = HybridFeatureScaler(scaler_77_path=SCALER_77_PATH)
    X_train_new = X_tb_train[:, 77:]
    scaler.fit_custom_scaler(X_train_new)
    scaler.save(SCALER_SAVE_PATH)
    
    X_train_scaled = scaler.transform(X_tb_train)
    X_val_scaled = scaler.transform(X_tb_val)
    
    # 4. SMOTE (OVERSAMPLING)
    print("\n[*] Áp dụng SMOTE lên tập Train...")
    y_train_encoded = encoder.transform(y_tb_train)
    
    # Chỉ định lượng up-sample cho 3 class thiểu số lên 15,000 mẫu
    target_smote = 15000
    smote_strategy = {}
    for cls_name in ['Brute Force', 'PortScan', 'Web Attack']:
        idx = encoder.transform([cls_name])[0]
        # Nếu số lượng hiện tại nhỏ hơn target_smote, nâng lên target_smote
        count = (y_train_encoded == idx).sum()
        if count < target_smote:
            smote_strategy[idx] = target_smote
            
    smote = SMOTE(sampling_strategy=smote_strategy, random_state=42, k_neighbors=3)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_scaled, y_train_encoded)
    
    print(f"    Train resampled: {len(X_train_resampled)}")
    counts = np.bincount(y_train_resampled)
    for i, count in enumerate(counts):
        print(f"      {encoder.inverse_transform([i])[0]}: {count}")
    
    # 5. NẠP MODEL & FULL UNFREEZE
    print("\n[*] Nạp Base Model và MỞ KHÓA TOÀN BỘ (Full Unfreeze)...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = FTTransformer(num_features=80, num_classes=5,
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    old_model = FTTransformer(num_features=80, num_classes=6,
                              d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    old_model.load_state_dict(torch.load(BASE_MODEL_PATH, map_location='cpu'))
    
    model_dict = model.state_dict()
    pretrained_dict = {k: v for k, v in old_model.state_dict().items() if 'classifier' not in k}
    model_dict.update(pretrained_dict)
    model.load_state_dict(model_dict)
    
    model = model.to(device)
    
    # TOÀN BỘ PARAMETERS ĐƯỢC TRAIN
    for param in model.parameters():
        param.requires_grad = True
        
    print("    Tất cả Transformer Blocks và Embeddings đã được mở khóa.")
    
    # 6. TRAINING SETUP
    print("\n[*] Chuẩn bị DataLoader và Optimizer...")
    X_tensor = torch.FloatTensor(X_train_resampled).to(device)
    y_tensor = torch.LongTensor(y_train_resampled).to(device)
    
    # Trọng số: Mọi class đều khỏe nhờ SMOTE, chỉ cần buff Benign nhẹ để né FP
    class_weights = np.ones(5, dtype=np.float32)
    benign_idx = encoder.transform(['Benign'])[0]
    class_weights[benign_idx] = 2.0  
    class_weights = torch.FloatTensor(class_weights).to(device)
    
    criterion = FocalLoss(gamma=2.0, weight=class_weights, label_smoothing=0.05)
    
    # Learning rate nhỏ hơn V5 vì unfreeze toàn bộ
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=15)
    
    dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=True)
    
    best_b_acc = -1
    epochs = 15
    
    print("\n[*] BẮT ĐẦU HUẤN LUYỆN (15 EPOCHS)...")
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
            
        scheduler.step()
            
        val_m = eval_model(model, X_val_scaled, y_tb_val, encoder, device=device)
        print(f"  Epoch {epoch+1:02d}/{epochs} | Loss: {total_loss/len(dataloader):.4f} | "
              f"Val Balanced Acc: {val_m['balanced_accuracy']:.4f} | "
              f"Val Acc: {val_m['accuracy']:.4f}")
              
        if val_m['balanced_accuracy'] > best_b_acc:
            best_b_acc = val_m['balanced_accuracy']
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"   -> Đã lưu checkpoint tốt nhất! (B-Acc: {best_b_acc:.4f})")
            
    print("\n[+] Đã hoàn thành quá trình Retrain V6!")
    print(f"  Model saved to: {MODEL_SAVE_PATH}")
    print(f"  Encoder saved to: {ENCODER_SAVE_PATH}")
    print(f"  Pipeline saved to: {SCALER_SAVE_PATH}")

if __name__ == "__main__":
    main()
