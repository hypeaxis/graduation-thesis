import os
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
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from imblearn.combine import SMOTEENN
from imblearn.over_sampling import BorderlineSMOTE

from phase2_ft_transformer_v2 import FTTransformer

class CICDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
    def __len__(self): return len(self.labels)
    def __getitem__(self, idx): return self.features[idx], self.labels[idx]

class FocalLoss(nn.Module):
    def __init__(self, weight=None, gamma=2.0, label_smoothing=0.0):
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

def load_chunk_data(train_csv, val_csv, batch_size=256):
    print("Loading Train Stage 1...")
    df_train = pd.read_csv(train_csv)
    print("Loading Val Full (only extracting Stage 1 labels)...")
    df_val = pd.read_csv(val_csv)
    
    # Map label for val
    mapping = {
        'BENIGN': 'Benign', 'DoS Hulk': 'DoS', 'DoS GoldenEye': 'DoS', 'DoS slowloris': 'DoS', 'DoS Slowhttptest': 'DoS',
        'DDoS': 'DDoS', 'PortScan': 'PortScan', 'FTP-Patator': 'Brute Force', 'SSH-Patator': 'Brute Force'
    }
    df_val['Label_Stage1'] = df_val['Label'].replace({'Web Attack.*': 'Suspicious'}, regex=True)
    df_val['Label_Stage1'] = df_val['Label_Stage1'].map(mapping).fillna('Suspicious')
    
    # Drop Label columns from val to match features
    y_val_raw = df_val['Label_Stage1'].values
    df_val = df_val[df_train.drop(columns=['Label']).columns] # Align columns
    X_val_raw = df_val.values
    
    X_train_raw = df_train.drop(columns=['Label']).values
    y_train_raw = df_train['Label'].values
    
    print("Applying SMOTE-ENN (Borderline-SMOTE + ENN Cleaning)...")
    label_counts = pd.Series(y_train_raw).value_counts()
    strategy = {label: max(30000, count) for label, count in label_counts.items()}
    strategy[label_counts.idxmax()] = label_counts.max()
    
    smote_enn = SMOTEENN(
        smote=BorderlineSMOTE(sampling_strategy=strategy, random_state=42, k_neighbors=5),
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
    TRAIN_CSV = 'processed_data/cic_train_stage1.csv'
    VAL_CSV = 'processed_data/cic_test_full.csv'
    SAVE_DIR = 'models/v4_cascade/stage1'
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    NUM_EPOCHS = 15
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    train_loader, val_loader, encoder, class_names, num_features, y_train_full, scaler = load_chunk_data(TRAIN_CSV, VAL_CSV)
    
    model = FTTransformer(num_features=num_features, num_classes=len(class_names), d_model=128, num_layers=4, num_heads=8, dropout=0.2, drop_path_rate=0.1).to(device)
    ema = EMAModel(model, decay=0.999)
    
    c_weights = compute_class_weight('balanced', classes=np.unique(y_train_full), y=y_train_full)
    criterion = FocalLoss(weight=torch.tensor(c_weights, dtype=torch.float32).to(device), gamma=2.0, label_smoothing=0.05)
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
            torch.save(model.state_dict(), os.path.join(SAVE_DIR, "best_stage1_model.pt"))
            torch.save(ema.state_dict(), os.path.join(SAVE_DIR, "best_stage1_ema.pt"))
            
    joblib.dump(scaler, os.path.join(SAVE_DIR, 'scaler_stage1.pkl'))
    joblib.dump(encoder, os.path.join(SAVE_DIR, 'encoder_stage1.pkl'))
    print("Hoàn tất Stage 1 Training!")

if __name__ == "__main__":
    main()
