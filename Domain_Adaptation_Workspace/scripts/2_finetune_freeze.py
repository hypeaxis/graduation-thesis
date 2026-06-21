import os
import sys
import json
import datetime
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, balanced_accuracy_score, matthews_corrcoef, confusion_matrix, precision_recall_fscore_support
from imblearn.over_sampling import RandomOverSampler
import joblib
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

from models.phase2_ft_transformer_v2 import FTTransformer

# ----------------- FEATURE MAPPING FUNCTIONS -----------------
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

def load_and_preprocess_testbed(filepath):
    df = pd.read_csv(filepath)
    df = df[df['Label'].isin(['Malicious', 'Benign'])].copy()
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    df = create_port_categories(df)
    df = extract_custom_features(df)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    
    for c in EXPECTED_FEATURES:
        if c not in df.columns:
            df[c] = 0
            
    X = df[EXPECTED_FEATURES].values
    y = df['Label'].values
    return X, y

def load_and_preprocess_cic2017(filepath, sample_size=30000):
    df = pd.read_csv(filepath)
    if 'Label_Stage1' in df.columns:
        df['Label'] = df['Label_Stage1']
    elif 'Label' not in df.columns:
        df['Label'] = 'Benign' # Fallback
        
    df = df.sample(n=min(sample_size, len(df)), random_state=42)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    
    for c in EXPECTED_FEATURES:
        if c not in df.columns:
            df[c] = 0
            
    X = df[EXPECTED_FEATURES].values
    y = df['Label'].values
    return X, y

def compute_metrics(y_true, y_pred):
    acc = accuracy_score(y_true, y_pred)
    b_acc = balanced_accuracy_score(y_true, y_pred)
    mcc = matthews_corrcoef(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average=None, labels=['Benign', 'Malicious'])
    
    metrics = {
        'accuracy': acc,
        'balanced_accuracy': b_acc,
        'mcc': mcc,
        'recall_benign': recall[0] if len(recall) > 0 else 0,
        'recall_malicious': recall[1] if len(recall) > 1 else 0,
        'precision_benign': precision[0] if len(precision) > 0 else 0,
        'precision_malicious': precision[1] if len(precision) > 1 else 0,
        'f1_malicious': f1[1] if len(f1) > 1 else 0,
        'confusion_matrix': cm.tolist()
    }
    return metrics

def eval_model(model, X, y, encoder, batch_size=512, device='cuda'):
    model.eval()
    X_tensor = torch.FloatTensor(X).to(device)
    y_encoded = encoder.transform(y)
    all_preds = []
    
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                logits = model(batch)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            
    y_pred_labels = encoder.inverse_transform(all_preds)
    # Map back to binary string 'Benign'/'Malicious'
    y_pred_binary = ['Benign' if p == 'Benign' else 'Malicious' for p in y_pred_labels]
    y_true_binary = ['Benign' if l == 'Benign' else 'Malicious' for l in y]
    
    return compute_metrics(y_true_binary, y_pred_binary)

def main():
    print("="*60)
    print("GIAI ĐOẠN 1: LAYER FREEZING FINE-TUNING")
    print("="*60)

    # 1. ĐƯỜNG DẪN DỮ LIỆU VÀ MODEL
    MODEL_DIR = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017'))
    CIC_TRAIN_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../data/processed/cic_train_full.csv'))
    CIC_TEST_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../data/processed/cic_test_full.csv'))
    TESTBED_PATH = '../data/Raw_Labeled_Dataset.csv'
    
    # 2. LOAD VÀ SPLIT DATA
    print("[*] Nạp Testbed Data...")
    X_tb, y_tb = load_and_preprocess_testbed(TESTBED_PATH)
    X_tb_train, X_tb_val, y_tb_train, y_tb_val = train_test_split(X_tb, y_tb, test_size=0.2, random_state=42, stratify=y_tb)
    
    print("[*] Nạp CIC-IDS-2017 Sample Data...")
    X_cic, y_cic = load_and_preprocess_cic2017(CIC_TRAIN_PATH, sample_size=30000)
    
    # Map Testbed 'Malicious' to 'DoS' to match original taxonomy
    y_tb_train = np.array(['DoS' if y == 'Malicious' else 'Benign' for y in y_tb_train])
    y_tb_val = np.array(['DoS' if y == 'Malicious' else 'Benign' for y in y_tb_val])
    
    # Gom Mixed-Domain
    X_mixed_train = np.vstack((X_tb_train, X_cic))
    y_mixed_train = np.concatenate((y_tb_train, y_cic))
    
    # 3. ÁP DỤNG SCALER GỐC (KHÔNG RE-FIT)
    print("[*] Áp dụng Scaler gốc từ CIC-IDS-2017...")
    scaler = joblib.load(os.path.join(MODEL_DIR, 'scaler_stage1.pkl'))
    X_mixed_scaled = scaler.transform(X_mixed_train)
    X_tb_val_scaled = scaler.transform(X_tb_val)
    
    # 4. CÂN BẰNG LỚP (OVERSAMPLING)
    print("[*] Cân bằng lớp Mixed-Domain bằng RandomOverSampler...")
    ros = RandomOverSampler(random_state=42)
    X_mixed_res, y_mixed_res = ros.fit_resample(X_mixed_scaled, y_mixed_train)
    
    # 5. KHỞI TẠO MÔ HÌNH VÀ ENCODER
    encoder = joblib.load(os.path.join(MODEL_DIR, 'encoder_stage1.pkl'))
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model = FTTransformer(num_features=77, num_classes=len(encoder.classes_), 
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2).to(device)
    model.load_state_dict(torch.load(os.path.join(MODEL_DIR, 'best_stage1_model.pt'), map_location=device))
    
    # 6. LAYER FREEZING
    print("[*] Đóng băng (Freeze) lớp Embedding và 2 khối Attention đầu...")
    for param in model.feature_embedding.parameters():
        param.requires_grad = False
    for param in model.transformer_blocks[0].parameters():
        param.requires_grad = False
    for param in model.transformer_blocks[1].parameters():
        param.requires_grad = False
        
    # Unfreeze 2 khối cuối và classifier (mặc định đã True, confirm lại)
    for param in model.transformer_blocks[2].parameters():
        param.requires_grad = True
    for param in model.transformer_blocks[3].parameters():
        param.requires_grad = True
    for param in model.classifier.parameters():
        param.requires_grad = True
        
    # 7. TRAINING SETUP
    # Encoding target
    y_mixed_encoded = torch.LongTensor(encoder.transform(y_mixed_res)).to(device)
    X_mixed_tensor = torch.FloatTensor(X_mixed_res).to(device)
    
    # Tính Class Weights cho CrossEntropyLoss (Dù đã Oversample nhưng tính thêm để bù đắp khác biệt)
    class_counts = np.bincount(y_mixed_encoded.cpu().numpy(), minlength=len(encoder.classes_))
    class_counts = np.where(class_counts == 0, 1, class_counts)
    class_weights = len(y_mixed_encoded) / (len(encoder.classes_) * class_counts)
    class_weights = torch.FloatTensor(class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    # Optimizer LR giảm 10 lần
    optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=1e-5, weight_decay=1e-4)
    
    dataset = torch.utils.data.TensorDataset(X_mixed_tensor, y_mixed_encoded)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=True)
    
    # 8. TRAINING LOOP
    print("[*] Bắt đầu Fine-Tuning...")
    best_b_acc = -1
    best_model_path = '../models/finetuned_stage1_freeze.pt'
    
    epochs = 10
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        for batch_x, batch_y in dataloader:
            optimizer.zero_grad()
            with torch.cuda.amp.autocast():
                logits = model(batch_x)
                loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        # Eval Testbed Val
        val_metrics = eval_model(model, X_tb_val_scaled, y_tb_val, encoder, device=device)
        print(f"Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(dataloader):.4f} | Val B-Acc: {val_metrics['balanced_accuracy']:.4f} | Recall(Malicious): {val_metrics['recall_malicious']:.4f}")
        
        if val_metrics['balanced_accuracy'] > best_b_acc:
            best_b_acc = val_metrics['balanced_accuracy']
            torch.save(model.state_dict(), best_model_path)
            print(f"   -> Lưu checkpoint tốt nhất! (B-Acc: {best_b_acc:.4f})")
            
    # 9. EVALUATION (Forgetting Check & Final Testbed)
    print("\n[*] Đánh giá Mô hình tốt nhất...")
    model.load_state_dict(torch.load(best_model_path))
    
    print("   1. Trên Testbed Validation Set:")
    final_tb_metrics = eval_model(model, X_tb_val_scaled, y_tb_val, encoder, device=device)
    print(f"      Accuracy: {final_tb_metrics['accuracy']:.4f}")
    print(f"      Balanced Acc: {final_tb_metrics['balanced_accuracy']:.4f}")
    print(f"      MCC: {final_tb_metrics['mcc']:.4f}")
    print(f"      Recall(Benign): {final_tb_metrics['recall_benign']:.4f}")
    print(f"      Recall(Malicious): {final_tb_metrics['recall_malicious']:.4f}")
    print(f"      Confusion Matrix:\n{np.array(final_tb_metrics['confusion_matrix'])}")
    
    print("   2. Kiểm tra Catastrophic Forgetting (CIC-IDS-2017 Test Set)...")
    X_cic_test, y_cic_test = load_and_preprocess_cic2017(CIC_TEST_PATH, sample_size=50000) # Lấy 50k mẫu test
    X_cic_test_scaled = scaler.transform(X_cic_test)
    cic_test_metrics = eval_model(model, X_cic_test_scaled, y_cic_test, encoder, device=device)
    print(f"      Accuracy: {cic_test_metrics['accuracy']:.4f} (Baseline gốc ~99.9%)")
    print(f"      Recall(Malicious): {cic_test_metrics['recall_malicious']:.4f}")
    
    # 10. LƯU LOG RESULTS
    log_data = {
        "timestamp": str(datetime.datetime.now()),
        "config": {
            "strategy": "Layer Freezing (Embed, Block 0, 1)",
            "learning_rate": 1e-5,
            "oversampler": "RandomOverSampler",
            "scaler": "Original CIC-IDS-2017"
        },
        "metrics_testbed": final_tb_metrics,
        "metrics_cic_2017": cic_test_metrics
    }
    
    with open('../results/exp2_finetune_freeze.json', 'w') as f:
        json.dump(log_data, f, indent=4)
    print("\n[*] Đã lưu kết quả vào results/exp2_finetune_freeze.json")

if __name__ == "__main__":
    main()
