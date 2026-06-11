"""
Phase 2 (V2): Training script for FT-Transformer Enhanced (CIC-IDS-2017)
Includes dynamic Focal Loss alpha calculation, LayerScale, and DropPath.
"""

import os
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    precision_score, recall_score, accuracy_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

from phase2_ft_transformer_v2 import FTTransformer, FocalLoss


class CICDataset(Dataset):
    """PyTorch Dataset for CIC-IDS-2017."""
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
    
    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


def compute_dynamic_alpha(y_encoded, num_classes):
    """
    Tính toán trọng số Focal Loss (Alpha) động dựa trên phân phối thực tế.
    Class nào càng ít xuất hiện -> Trọng số càng cao.
    """
    print("Calculating Dynamic Focal Loss Alpha...")
    class_counts = np.bincount(y_encoded, minlength=num_classes)
    total_samples = len(y_encoded)
    
    # Tính nghịch đảo tần suất (Inverse Frequency)
    # Thêm epsilon để tránh chia cho 0
    alpha = total_samples / (num_classes * (class_counts + 1e-5))
    
    # Chuẩn hóa để tổng alpha = 1.0 (hoặc giữ nguyên tỉ lệ tùy ý, ở đây chuẩn hóa mảng)
    alpha = alpha / np.sum(alpha)
    
    for i, count in enumerate(class_counts):
        print(f"  Class {i}: {count:8d} samples -> Alpha weight: {alpha[i]:.4f}")
        
    return torch.tensor(alpha, dtype=torch.float32)


def load_chunk_data(train_csv, val_csv):
    """Load Train và Val Chunk riêng biệt thay vì train_test_split."""
    print("Loading Train Chunk...")
    df_train = pd.read_csv(train_csv)
    print("Loading Validation Chunk...")
    df_val = pd.read_csv(val_csv)
    
    label_col = 'Label'
    X_train_raw = df_train.drop(columns=[label_col]).values
    y_train_raw = df_train[label_col].values
    
    X_val_raw = df_val.drop(columns=[label_col]).values
    y_val_raw = df_val[label_col].values
    
    # Encoding Labels (Khớp cả 2 tập để tránh mismatch)
    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_train_raw)
    
    # Có thể có những nhãn trong Val không có trong Train (hiếm), cần xử lý an toàn
    # Tạm thời bỏ qua bằng cách ép biến các nhãn lạ thành -1 hoặc lọc bỏ. 
    # Nhưng vì đây là CIC-IDS chia Stratified nên khả năng rất thấp.
    classes = list(label_encoder.classes_)
    y_val = np.array([classes.index(l) if l in classes else 0 for l in y_val_raw])
    
    num_features = X_train_raw.shape[1]
    num_classes = len(classes)
    
    print(f"\nDataset Info:")
    print(f"  Features: {num_features}")
    print(f"  Classes: {num_classes}")
    print(f"  Train samples: {len(X_train_raw):,}")
    print(f"  Val samples:   {len(X_val_raw):,}")
    
    dynamic_alpha = compute_dynamic_alpha(y_train, num_classes)
    
    train_dataset = CICDataset(X_train_raw, y_train)
    val_dataset = CICDataset(X_val_raw, y_val)
    
    # Batch size cực lớn cho Transformer để tận dụng GPU
    batch_size = 1024
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)
    
    return train_loader, val_loader, label_encoder, classes, num_features, dynamic_alpha


def train_epoch(model, train_loader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    all_preds, all_labels = [], []
    
    pbar = tqdm(train_loader, desc="Training", leave=False)
    for features, labels in pbar:
        features, labels = features.to(device), labels.to(device)
        
        optimizer.zero_grad()
        logits = model(features)
        loss = criterion(logits, labels)
        
        loss.backward()
        # Gradient Clipping để chống nổ Gradient do LayerScale
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        total_loss += loss.item()
        preds = torch.argmax(logits, dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
        
        pbar.set_postfix({'loss': f'{loss.item():.4f}'})
    
    avg_loss = total_loss / len(train_loader)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    return avg_loss, macro_f1


def validate(model, val_loader, criterion, device):
    model.eval()
    total_loss = 0
    all_preds, all_labels = [], []
    
    with torch.no_grad():
        for features, labels in tqdm(val_loader, desc="Validating", leave=False):
            features, labels = features.to(device), labels.to(device)
            logits = model(features)
            loss = criterion(logits, labels)
            
            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
    avg_loss = total_loss / len(val_loader)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    return avg_loss, macro_f1


def main():
    TRAIN_CSV = 'processed_data/cic_train_chunk.csv'
    VAL_CSV = 'processed_data/cic_test_chunk_1.csv'
    SAVE_DIR = 'models/v2_enhanced'
    
    NUM_EPOCHS = 30
    LEARNING_RATE = 1e-4
    WEIGHT_DECAY = 1e-4
    PATIENCE = 5
    
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    train_loader, val_loader, encoder, class_names, num_features, alpha = load_chunk_data(TRAIN_CSV, VAL_CSV)
    
    print("\nInitializing FT-Transformer V2 (Enhanced)...")
    model = FTTransformer(
        num_features=num_features,
        num_classes=len(class_names),
        d_model=128,
        num_heads=8,
        num_layers=4,
        d_ff=512,
        dropout=0.1,
        drop_path_rate=0.1 # 10% Stochastic Depth
    ).to(device)
    
    criterion = FocalLoss(gamma=3.0, alpha=alpha, num_classes=len(class_names))
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2)
    
    print(f"\nModel Params: {sum(p.numel() for p in model.parameters()):,}")
    print("READY FOR TRAINING!")
    # model training loop logic goes here...

if __name__ == "__main__":
    main()
