import os
import sys
# Để import được phase2_ft_transformer_v2 từ thư mục cha
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import copy
import time
import numpy as np
import pandas as pd
import joblib
import torch
import torch.nn as nn
import math
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder, PowerTransformer
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix, f1_score, recall_score
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from imblearn.combine import SMOTEENN
from imblearn.over_sampling import SMOTE



from phase2_ft_transformer_v2 import FTTransformer

class CICDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
    def __len__(self): return len(self.labels)
    def __getitem__(self, idx): return self.features[idx], self.labels[idx]

class FocalLoss(nn.Module):
    def __init__(self, weight=None, gamma=1.5, label_smoothing=0.0):
        super(FocalLoss, self).__init__()
        self.gamma = gamma
        self.ce = nn.CrossEntropyLoss(weight=weight, label_smoothing=label_smoothing, reduction='none')
    def forward(self, inputs, targets):
        ce_loss = self.ce(inputs, targets)
        pt = torch.exp(-ce_loss)
        return (((1 - pt) ** self.gamma) * ce_loss).mean()

class CosineAnnealingWarmup(torch.optim.lr_scheduler._LRScheduler):
    def __init__(self, optimizer, warmup_epochs, total_epochs, min_lr=1e-6, last_epoch=-1):
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs
        self.min_lr = min_lr
        super().__init__(optimizer, last_epoch)
    def get_lr(self):
        if self.last_epoch < self.warmup_epochs:
            warmup_factor = (self.last_epoch + 1) / self.warmup_epochs
            return [base_lr * warmup_factor for base_lr in self.base_lrs]
        else:
            progress = (self.last_epoch - self.warmup_epochs) / max(1, self.total_epochs - self.warmup_epochs)
            cosine_factor = 0.5 * (1.0 + math.cos(math.pi * progress))
            return [self.min_lr + (base_lr - self.min_lr) * cosine_factor for base_lr in self.base_lrs]

class EMAModel:
    def __init__(self, model, decay=0.999):
        self.decay = decay
        self.ema_model = copy.deepcopy(model)
        self.ema_model.eval()
        for p in self.ema_model.parameters(): p.requires_grad_(False)
    @torch.no_grad()
    def update(self, model):
        for ema_param, param in zip(self.ema_model.parameters(), model.parameters()):
            ema_param.data.mul_(self.decay).add_(param.data, alpha=1.0 - self.decay)
    def state_dict(self): return self.ema_model.state_dict()
    def module(self): return self.ema_model

# 34 Features (Added 2 Ratio Features)
STAGE2_FEATURES = [
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
    'Subflow_Fwd_Bytes', 'Subflow_Bwd_Bytes',
    'Bwd_Packet_Length_Std', 'Bwd_Packet_Length_Max', 'PSH_Flag_Count',
    'Flow_Bytes_Ratio', 'Flow_Pkts_Ratio'
]

def load_chunk_data(train_csv, val_csv, batch_size=256):
    import gc
    print(f"Loading Train Stage 2 from {train_csv}...")
    df_train = pd.read_csv(train_csv)
    for col in df_train.select_dtypes(include=['float64']).columns: df_train[col] = df_train[col].astype('float32')
    for col in df_train.select_dtypes(include=['int64']).columns: df_train[col] = df_train[col].astype('int32')

    print(f"Loading Val Full (Filtering for Stage 2 evaluation)...")
    val_usecols = STAGE2_FEATURES + ['Label']
    df_val = pd.read_csv(val_csv, usecols=val_usecols)
    
    
    
    
    df_val = df_val[STAGE2_FEATURES + ['Label']]
    for col in df_val.select_dtypes(include=['float64']).columns: df_val[col] = df_val[col].astype('float32')
    for col in df_val.select_dtypes(include=['int64']).columns: df_val[col] = df_val[col].astype('int32')

    # Smart Stratified Sampling
    df_val = df_val.groupby('Label', group_keys=False).apply(lambda x: x.sample(frac=0.2, random_state=42) if len(x) > 1000 else x)
    print(f"Validation set downsampled to {len(df_val)} rows.")
    
    def map_stage2_label(l):
        if not isinstance(l, str): return None
        if 'Web Attack' in l: return 'Web Attack'
        if l in ['Bot', 'Infiltration', 'Heartbleed']: return l
        if l == 'BENIGN': return 'Benign'
        return None
    df_val['Label_Stage2'] = df_val['Label'].apply(map_stage2_label)
    df_val = df_val[df_val['Label_Stage2'].notna()]
    
    y_val_raw = df_val['Label_Stage2'].values
    X_val_raw = df_val[STAGE2_FEATURES].values
    del df_val
    gc.collect()
    
    X_train_raw = df_train[STAGE2_FEATURES].values
    y_train_raw = df_train['Label'].values
    del df_train
    gc.collect()
    
    print("Applying SMOTE-ENN (min 30,000 samples)...")
    
    # Fix for SMOTE requiring >= 6 samples
    X_list = list(X_train_raw)
    y_list = list(y_train_raw)
    label_counts_raw = pd.Series(y_list).value_counts()
    for label, count in label_counts_raw.items():
        if count < 6:
            print(f"Duplicating {label} (count={count}) to reach 6 samples for SMOTE.")
            idx = [i for i, l in enumerate(y_list) if l == label]
            while len(idx) < 6:
                X_list.append(X_list[idx[0]])
                y_list.append(label)
                idx.append(len(y_list)-1)
                
    X_train_raw = np.array(X_list)
    y_train_raw = np.array(y_list)
    
    label_counts = pd.Series(y_train_raw).value_counts()
    strategy = {label: max(30000, count) for label, count in label_counts.items()}
    strategy[label_counts.idxmax()] = label_counts.max()
    
    smote_enn = SMOTEENN(
        smote=SMOTE(sampling_strategy=strategy, random_state=42, k_neighbors=5),
        random_state=42
    )
    X_train_resampled, y_train_resampled = smote_enn.fit_resample(X_train_raw, y_train_raw)
    
    print("Scaling Features using PowerTransformer...")
    scaler = PowerTransformer(method='yeo-johnson', standardize=True)
    X_train_scaled = scaler.fit_transform(X_train_resampled)
    X_val_scaled = scaler.transform(X_val_raw)
    
    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_train_resampled)
    y_val = label_encoder.transform(y_val_raw)
    
    train_loader = DataLoader(CICDataset(X_train_scaled, y_train), batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(CICDataset(X_val_scaled, y_val), batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)
    return train_loader, val_loader, label_encoder, label_encoder.classes_, X_train_scaled.shape[1], y_train, scaler

def train_epoch(model, train_loader, criterion, optimizer, device, amp_scaler, ema):
    model.train()
    total_loss = 0
    all_preds, all_labels = [], []
    for features, labels in tqdm(train_loader, desc="Training", leave=False):
        features, labels = features.to(device), labels.to(device)
        optimizer.zero_grad(set_to_none=True)
        with torch.cuda.amp.autocast():
            logits = model(features)
            loss = criterion(logits, labels)
        amp_scaler.scale(loss).backward()
        amp_scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        amp_scaler.step(optimizer)
        amp_scaler.update()
        ema.update(model)
        total_loss += loss.item()
        preds = torch.argmax(logits, dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
    return total_loss / len(train_loader), f1_score(all_labels, all_preds, average='macro', zero_division=0)

def validate(model, val_loader, criterion, device):
    model.eval()
    total_loss = 0
    all_preds, all_labels = [], []
    with torch.no_grad():
        for features, labels in tqdm(val_loader, desc="Validating", leave=False):
            features, labels = features.to(device), labels.to(device)
            with torch.cuda.amp.autocast():
                logits = model(features)
                loss = criterion(logits, labels)
            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    avg_loss = total_loss / len(val_loader)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    per_class_recall = recall_score(all_labels, all_preds, average=None, zero_division=0)
    g_mean = float(np.prod(per_class_recall) ** (1.0 / len(per_class_recall)))
    return avg_loss, macro_f1, g_mean, all_preds, all_labels

def main():
    TRAIN_CSV = 'processed_data/cic_train_stage2_v6_hard.csv'
    VAL_CSV = 'processed_data/cic_test_full.csv'
    SAVE_DIR = 'models/v7_cascade/stage2'
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    NUM_EPOCHS = 20
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    train_loader, val_loader, encoder, class_names, num_features, y_train_full, scaler = load_chunk_data(TRAIN_CSV, VAL_CSV)
    
    print("\n" + "="*50)
    print("1. TRAINING RANDOM FOREST & KNN")
    print("="*50)
    
    # We extract data from the DataLoader to train RF and KNN.
    # Note: the dataset inside train_loader is scaled.
    X_train_np = train_loader.dataset.features.numpy()
    y_train_np = train_loader.dataset.labels.numpy()
    
    print("Training Random Forest...")
    rf_model = RandomForestClassifier(n_estimators=150, max_features=20, max_depth=25, random_state=42, n_jobs=-1, class_weight='balanced')
    rf_model.fit(X_train_np, y_train_np)
    joblib.dump(rf_model, os.path.join(SAVE_DIR, 'best_rf_model.pkl'))
    
    print("Training KNN...")
    knn_model = KNeighborsClassifier(n_neighbors=16, n_jobs=-1)
    knn_model.fit(X_train_np, y_train_np)
    joblib.dump(knn_model, os.path.join(SAVE_DIR, 'best_knn_model.pkl'))
    
    print("\n" + "="*50)
    print("2. TRAINING FT-TRANSFORMER")
    print("="*50)
    
    model = FTTransformer(num_features=num_features, num_classes=len(class_names), d_model=64, num_layers=3, num_heads=4, dropout=0.2, drop_path_rate=0.1).to(device)
    ema = EMAModel(model, decay=0.999)
    
    c_weights = compute_class_weight('balanced', classes=np.unique(y_train_full), y=y_train_full)
    for cls_name in ['Web Attack', 'Infiltration', 'Heartbleed']:
        if cls_name in encoder.classes_:
            idx = list(encoder.classes_).index(cls_name)
            c_weights[idx] *= 1.5
            
    criterion = FocalLoss(weight=torch.tensor(c_weights, dtype=torch.float32).to(device), gamma=1.5, label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    scheduler = CosineAnnealingWarmup(optimizer, warmup_epochs=3, total_epochs=NUM_EPOCHS)
    
    best_val_f1 = 0.0
    amp_scaler = torch.cuda.amp.GradScaler()
    
    for epoch in range(NUM_EPOCHS):
        print(f"\nEpoch {epoch+1}/{NUM_EPOCHS}")
        train_loss, train_f1 = train_epoch(model, train_loader, criterion, optimizer, device, amp_scaler, ema)
        val_loss, val_f1, g_mean, val_preds, val_labels = validate(model, val_loader, criterion, device)
        _, ema_val_f1, ema_g_mean, ema_preds, ema_labels = validate(ema.module(), val_loader, criterion, device)
        scheduler.step()
        
        print(f"Train Loss: {train_loss:.4f} | Val F1: {val_f1:.4f} | Val G-Mean: {g_mean:.4f} | EMA F1: {ema_val_f1:.4f}")
        epoch_best_f1 = max(val_f1, ema_val_f1)
        if epoch_best_f1 > best_val_f1:
            best_val_f1 = epoch_best_f1
            torch.save(model.state_dict(), os.path.join(SAVE_DIR, "best_stage2_model.pt"))
            torch.save(ema.state_dict(), os.path.join(SAVE_DIR, "best_stage2_ema.pt"))
            
    joblib.dump(scaler, os.path.join(SAVE_DIR, 'scaler_stage2.pkl'))
    joblib.dump(encoder, os.path.join(SAVE_DIR, 'encoder_stage2.pkl'))
    
    import json
    with open(os.path.join(SAVE_DIR, 'stage2_features.json'), 'w') as f:
        json.dump(STAGE2_FEATURES, f)
        
    print("Hoàn tất Stage 2 V7 Ensemble Training!")

if __name__ == "__main__":
    main()
