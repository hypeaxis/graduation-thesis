"""
STAGE 3C: HYBRID PIPELINE (Sửa lỗi Stage 3B)
==============================================
Khác biệt so với Stage 3B:
- 77 features gốc: GIỮ NGUYÊN scaler cũ (PowerTransformer đã fit trên CIC-IDS-2017)
  → Vì 77 embedding bị FROZEN, chúng kỳ vọng dữ liệu theo đúng scale gốc.
- 3 features mới: fit PowerTransformer MỚI (cùng họ Yeo-Johnson) trên training data
  → Nhất quán về phương pháp, không dùng StandardScaler nữa.
- Đóng gói TẤT CẢ vào 1 pipeline dict → joblib.dump() 1 lần.
- Lưu training stats cho sanity-check lúc inference.
"""
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
from sklearn.preprocessing import PowerTransformer
from imblearn.over_sampling import RandomOverSampler
import joblib
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

# ====================== DATA LOADING ======================
def load_and_preprocess_testbed(filepath):
    df = pd.read_csv(filepath)
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
    X = df[EXPECTED_FEATURES_80].values
    y = df['Label'].values
    return X, y

def load_and_preprocess_cic2017(filepath, sample_size=30000):
    df = pd.read_csv(filepath)
    if 'Label_Stage1' in df.columns:
        df['Label'] = df['Label_Stage1']
    elif 'Label' not in df.columns:
        df['Label'] = 'Benign'
    df = df.sample(n=min(sample_size, len(df)), random_state=42)
    df = extract_custom_features(df)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    for c in EXPECTED_FEATURES_80:
        if c not in df.columns:
            df[c] = 0
    X = df[EXPECTED_FEATURES_80].values
    y = df['Label'].values
    return X, y

def apply_hybrid_pipeline(X, pipeline):
    """Áp dụng pipeline hybrid: scaler cũ cho 77 features, scaler mới cho 3 features."""
    X_old = X[:, :77]
    X_new = X[:, 77:]
    X_scaled_old = pipeline['scaler_77_original'].transform(X_old)
    X_scaled_new = pipeline['scaler_3_new'].transform(X_new)
    return np.hstack((X_scaled_old, X_scaled_new))

# ====================== METRICS ======================
def compute_metrics(y_true, y_pred):
    acc = accuracy_score(y_true, y_pred)
    b_acc = balanced_accuracy_score(y_true, y_pred)
    mcc = matthews_corrcoef(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average=None, labels=['Benign', 'Malicious'])
    return {
        'accuracy': acc, 'balanced_accuracy': b_acc, 'mcc': mcc,
        'recall_benign': recall[0] if len(recall) > 0 else 0,
        'recall_malicious': recall[1] if len(recall) > 1 else 0,
        'precision_benign': precision[0] if len(precision) > 0 else 0,
        'precision_malicious': precision[1] if len(precision) > 1 else 0,
        'f1_malicious': f1[1] if len(f1) > 1 else 0,
        'confusion_matrix': cm.tolist()
    }

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
    y_pred_binary = ['Benign' if p == 'Benign' else 'Malicious' for p in y_pred_labels]
    y_true_binary = ['Benign' if l == 'Benign' else 'Malicious' for l in y]
    return compute_metrics(y_true_binary, y_pred_binary)

# ====================== MAIN ======================
def main():
    print("="*60)
    print("STAGE 3C: HYBRID PIPELINE")
    print("  77 features → scaler gốc (PowerTransformer CIC-IDS)")
    print("  3 features  → scaler mới (PowerTransformer, cùng họ)")
    print("="*60)

    MODEL_DIR = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017'))
    CIC_TRAIN_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../data/processed/cic_train_full.csv'))
    CIC_TEST_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../data/processed/cic_test_full.csv'))
    TESTBED_PATH = '../data/Raw_Labeled_Dataset.csv'
    PIPELINE_SAVE_PATH = '../models/stage3c_hybrid_pipeline.pkl'
    MODEL_SAVE_PATH = '../models/finetuned_stage3c_hybrid.pt'
    
    # ============================================================
    # BƯỚC 1: NẠP DỮ LIỆU
    # ============================================================
    print("\n[BƯỚC 1] Nạp dữ liệu huấn luyện...")
    X_tb, y_tb = load_and_preprocess_testbed(TESTBED_PATH)
    X_tb_train, X_tb_val, y_tb_train, y_tb_val = train_test_split(
        X_tb, y_tb, test_size=0.2, random_state=42, stratify=y_tb)
    print(f"  Testbed train: {len(X_tb_train)}, val: {len(X_tb_val)}")
    
    X_cic, y_cic = load_and_preprocess_cic2017(CIC_TRAIN_PATH, sample_size=30000)
    print(f"  CIC-IDS sample: {len(X_cic)}")
    
    y_tb_train_mapped = np.array(['DoS' if y == 'Malicious' else 'Benign' for y in y_tb_train])
    y_tb_val_mapped = np.array(['DoS' if y == 'Malicious' else 'Benign' for y in y_tb_val])
    
    X_mixed = np.vstack((X_tb_train, X_cic))
    y_mixed = np.concatenate((y_tb_train_mapped, y_cic))
    print(f"  Mixed training set: {len(X_mixed)}")

    # ============================================================
    # BƯỚC 2: HYBRID SCALER
    # ============================================================
    print("\n[BƯỚC 2] Xây dựng Hybrid Pipeline...")
    
    # 2a. Scaler GỐC cho 77 features (KHÔNG fit lại, giữ nguyên)
    scaler_77 = joblib.load(os.path.join(MODEL_DIR, 'scaler_stage1.pkl'))
    print(f"  77 features: {type(scaler_77).__name__} (giữ nguyên từ CIC-IDS-2017)")
    
    # 2b. Scaler MỚI cho 3 features (cùng họ PowerTransformer, fit trên training data)
    X_mixed_new = X_mixed[:, 77:]  # 3 features mới
    scaler_3 = PowerTransformer(method='yeo-johnson', standardize=True)
    scaler_3.fit(X_mixed_new)
    print(f"  3 features:  {type(scaler_3).__name__} (fit trên mixed training data)")
    
    # 2c. Transform
    X_mixed_old = X_mixed[:, :77]
    X_mixed_scaled = np.hstack((scaler_77.transform(X_mixed_old), scaler_3.transform(X_mixed_new)))
    X_tb_val_scaled = np.hstack((
        scaler_77.transform(X_tb_val[:, :77]),
        scaler_3.transform(X_tb_val[:, 77:])
    ))
    
    # 2d. Tính training stats (trên dữ liệu RAW, trước khi scale)
    train_stats = {
        'raw_mean': X_mixed.mean(axis=0).tolist(),
        'raw_std': X_mixed.std(axis=0).tolist(),
        'raw_min': X_mixed.min(axis=0).tolist(),
        'raw_max': X_mixed.max(axis=0).tolist(),
        'n_train_samples': len(X_mixed),
        'feature_names': EXPECTED_FEATURES_80,
        'alert_threshold_std_multiplier': 3.0,
    }

    # ============================================================
    # BƯỚC 3: LƯU PIPELINE
    # ============================================================
    print("\n[BƯỚC 3] Lưu Hybrid Pipeline...")
    pipeline = {
        'scaler_77_original': scaler_77,
        'scaler_3_new': scaler_3,
        'train_stats': train_stats,
        'feature_names': EXPECTED_FEATURES_80,
        'n_features': 80,
        'n_old_features': 77,
        'n_new_features': 3,
        'scaler_type': 'Hybrid(PowerTransformer_77_original + PowerTransformer_3_new)',
        'created_at': str(datetime.datetime.now()),
        'description': (
            'Hybrid pipeline: 77 features dùng scaler gốc CIC-IDS-2017 (khớp frozen embeddings), '
            '3 features mới dùng PowerTransformer riêng (cùng họ Yeo-Johnson, fit trên mixed training data).'
        )
    }
    os.makedirs(os.path.dirname(PIPELINE_SAVE_PATH), exist_ok=True)
    joblib.dump(pipeline, PIPELINE_SAVE_PATH)
    print(f"  ✓ Đã lưu: {PIPELINE_SAVE_PATH}")
    
    # ============================================================
    # BƯỚC 4: MODEL SURGERY + FINE-TUNING
    # ============================================================
    print("\n[BƯỚC 4] Model Surgery: 77→80 features...")
    encoder = joblib.load(os.path.join(MODEL_DIR, 'encoder_stage1.pkl'))
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    model_old = FTTransformer(num_features=77, num_classes=len(encoder.classes_),
                              d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    model_old.load_state_dict(torch.load(os.path.join(MODEL_DIR, 'best_stage1_model.pt'), map_location='cpu'))
    
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    
    for i in range(77):
        model.feature_embedding.feature_embeddings[i].load_state_dict(
            model_old.feature_embedding.feature_embeddings[i].state_dict())
    model.feature_embedding.cls_token.data.copy_(model_old.feature_embedding.cls_token.data)
    model.transformer_blocks.load_state_dict(model_old.transformer_blocks.state_dict())
    model.norm.load_state_dict(model_old.norm.state_dict())
    model.classifier.load_state_dict(model_old.classifier.state_dict())
    model = model.to(device)
    
    # Freeze
    for i in range(77):
        for param in model.feature_embedding.feature_embeddings[i].parameters():
            param.requires_grad = False
    for param in model.transformer_blocks[0].parameters():
        param.requires_grad = False
    for param in model.transformer_blocks[1].parameters():
        param.requires_grad = False
    for i in range(77, 80):
        for param in model.feature_embedding.feature_embeddings[i].parameters():
            param.requires_grad = True
    
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  Trainable: {trainable:,} / {total:,} ({trainable/total*100:.1f}%)")
    
    # ============================================================
    # BƯỚC 5: TRAINING
    # ============================================================
    print("\n[BƯỚC 5] Cân bằng lớp + Fine-Tuning...")
    ros = RandomOverSampler(random_state=42)
    X_res, y_res = ros.fit_resample(X_mixed_scaled, y_mixed)
    
    y_encoded = torch.LongTensor(encoder.transform(y_res)).to(device)
    X_tensor = torch.FloatTensor(X_res).to(device)
    
    class_counts = np.bincount(y_encoded.cpu().numpy(), minlength=len(encoder.classes_))
    class_counts = np.where(class_counts == 0, 1, class_counts)
    class_weights = len(y_encoded) / (len(encoder.classes_) * class_counts)
    class_weights = torch.FloatTensor(class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()), lr=1e-5, weight_decay=1e-4)
    
    dataset = torch.utils.data.TensorDataset(X_tensor, y_encoded)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=True)
    
    best_b_acc = -1
    epochs = 10
    
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
        
        val_m = eval_model(model, X_tb_val_scaled, y_tb_val, encoder, device=device)
        print(f"  Epoch {epoch+1}/{epochs} | Loss: {total_loss/len(dataloader):.4f} | "
              f"B-Acc: {val_m['balanced_accuracy']:.4f} | "
              f"R(Mal): {val_m['recall_malicious']:.4f} | R(Ben): {val_m['recall_benign']:.4f}")
        
        if val_m['balanced_accuracy'] > best_b_acc:
            best_b_acc = val_m['balanced_accuracy']
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"   → Checkpoint! (B-Acc: {best_b_acc:.4f})")
    
    # ============================================================
    # BƯỚC 6: ĐÁNH GIÁ
    # ============================================================
    print("\n[BƯỚC 6] Đánh giá mô hình tốt nhất...")
    model.load_state_dict(torch.load(MODEL_SAVE_PATH))
    
    print("  1. Testbed Validation Set:")
    tb_m = eval_model(model, X_tb_val_scaled, y_tb_val, encoder, device=device)
    print(f"     Accuracy:          {tb_m['accuracy']:.4f}")
    print(f"     Balanced Acc:      {tb_m['balanced_accuracy']:.4f}")
    print(f"     MCC:               {tb_m['mcc']:.4f}")
    print(f"     Recall(Benign):    {tb_m['recall_benign']:.4f}")
    print(f"     Recall(Malicious): {tb_m['recall_malicious']:.4f}")
    
    print("  2. Catastrophic Forgetting Check (CIC-IDS-2017):")
    X_cic_test, y_cic_test = load_and_preprocess_cic2017(CIC_TEST_PATH, sample_size=50000)
    X_cic_test_scaled = apply_hybrid_pipeline(X_cic_test, pipeline)
    cic_m = eval_model(model, X_cic_test_scaled, y_cic_test, encoder, device=device)
    print(f"     Accuracy:          {cic_m['accuracy']:.4f}")
    print(f"     Recall(Malicious): {cic_m['recall_malicious']:.4f}")
    
    # ============================================================
    # BƯỚC 7: LƯU KẾT QUẢ
    # ============================================================
    log_data = {
        "timestamp": str(datetime.datetime.now()),
        "config": {
            "strategy": "Stage 3C (Hybrid Pipeline: Original PT77 + New PT3, Model Surgery)",
            "learning_rate": 1e-5,
            "oversampler": "RandomOverSampler",
            "scaler": "Hybrid(PowerTransformer_77_original + PowerTransformer_3_new)"
        },
        "metrics_testbed": tb_m,
        "metrics_cic_2017": cic_m
    }
    with open('../results/exp3c_hybrid_pipeline.json', 'w') as f:
        json.dump(log_data, f, indent=4)
    
    print(f"\n  ✓ Pipeline: {PIPELINE_SAVE_PATH}")
    print(f"  ✓ Model:    {MODEL_SAVE_PATH}")
    print(f"  ✓ Results:  results/exp3c_hybrid_pipeline.json")

if __name__ == "__main__":
    main()
