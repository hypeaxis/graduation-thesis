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
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    precision_score, recall_score, accuracy_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from imblearn.over_sampling import SMOTE
from sklearn.utils.class_weight import compute_class_weight

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


# Hàm setup DataLoader và Preprocessing
def load_chunk_data(train_csv, val_csv, batch_size=256):
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
    
    print("Applying SMOTE to balance minority classes...")
    label_counts = pd.Series(y_train_raw).value_counts()
    max_count = label_counts.max()
    # Tăng tối thiểu lên 10,000 để SMOTE hoạt động hiệu quả mà không tốn RAM
    strategy = {label: max(10000, count) for label, count in label_counts.items()}
    strategy[label_counts.idxmax()] = max_count
    
    smote = SMOTE(sampling_strategy=strategy, random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_raw, y_train_raw)
    
    print("Scaling Features using StandardScaler (Crucial to prevent NaN loss)...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train_resampled)
    X_val_scaled = scaler.transform(X_val_raw)
    
    # Encoding Labels
    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_train_resampled)
    y_val = label_encoder.transform(y_val_raw)
    
    classes = label_encoder.classes_
    num_features = X_train_scaled.shape[1]
    
    print(f"\nDataset Info after SMOTE:")
    print(f"  Features: {num_features}")
    print(f"  Classes: {len(classes)} ({list(classes)})")
    print(f"  Train samples: {len(X_train_scaled):,}")
    print(f"  Val samples:   {len(X_val_scaled):,}")
    
    train_dataset = CICDataset(X_train_scaled, y_train)
    val_dataset = CICDataset(X_val_scaled, y_val)
    
    # Batch Size
    batch_size = 256
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)
    
    return train_loader, val_loader, label_encoder, classes, num_features, y_train


def train_epoch(model, train_loader, criterion, optimizer, device, scaler):
    model.train()
    total_loss = 0
    all_preds, all_labels = [], []
    
    pbar = tqdm(train_loader, desc="Training", leave=False)
    for features, labels in pbar:
        features, labels = features.to(device), labels.to(device)
        
        optimizer.zero_grad(set_to_none=True)
        
        # Sử dụng Automatic Mixed Precision (AMP) để tăng tốc x2
        with torch.cuda.amp.autocast():
            logits = model(features)
            loss = criterion(logits, labels)
            
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        # Gradient Clipping để chống nổ Gradient do LayerScale
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        scaler.step(optimizer)
        scaler.update()
        
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
            with torch.cuda.amp.autocast():
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
    
    # Chỉ định 10 Epochs theo yêu cầu để đạt metric tốt
    NUM_EPOCHS = 10
    LEARNING_RATE = 1e-4
    WEIGHT_DECAY = 1e-4
    PATIENCE = 5
    
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    train_loader, val_loader, encoder, class_names, num_features, y_train_full = load_chunk_data(TRAIN_CSV, VAL_CSV)
    
    print("\nInitializing FT-Transformer V2 (Enhanced)...")
    model = FTTransformer(
        num_features=num_features,
        num_classes=len(class_names),
        d_model=128,
        num_layers=4,
        num_heads=8,
        dropout=0.2,
        drop_path_rate=0.1 # 10% Stochastic Depth
    ).to(device)
    
    # Tính Class Weights tự động bằng sklearn
    c_weights = compute_class_weight('balanced', classes=np.unique(y_train_full), y=y_train_full)
    c_weights_tensor = torch.tensor(c_weights, dtype=torch.float32).to(device)
    
    # Sử dụng CrossEntropyLoss kết hợp Label Smoothing (0.1)
    criterion = nn.CrossEntropyLoss(weight=c_weights_tensor, label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=2)
    
    print(f"\nModel Params: {sum(p.numel() for p in model.parameters()):,}")
    print("\nREADY FOR TRAINING!")
    
    best_val_f1 = 0.0
    epochs_no_improve = 0
    
    # Tối ưu hóa backend cuDNN
    torch.backends.cudnn.benchmark = True
    scaler = torch.cuda.amp.GradScaler()
    
    for epoch in range(NUM_EPOCHS):
        print(f"\nEpoch {epoch+1}/{NUM_EPOCHS}")
        print("-" * 30)
        
        start_time = time.time()
        
        # Train
        train_loss, train_f1 = train_epoch(model, train_loader, criterion, optimizer, device, scaler)
        
        # Validate
        val_loss, val_f1 = validate(model, val_loader, criterion, device)
        
        # Learning Rate Schedule
        scheduler.step(val_f1)
        
        epoch_mins, epoch_secs = divmod(time.time() - start_time, 60)
        
        print(f"Time: {int(epoch_mins)}m {int(epoch_secs)}s")
        print(f"Train Loss: {train_loss:.4f} | Train Macro-F1: {train_f1:.4f}")
        print(f"Val Loss:   {val_loss:.4f} | Val Macro-F1:   {val_f1:.4f}")
        
        # Checkpointing
        if val_f1 > best_val_f1:
            print(f"🌟 Validation Macro-F1 improved from {best_val_f1:.4f} to {val_f1:.4f}. Saving model...")
            best_val_f1 = val_f1
            torch.save(model.state_dict(), os.path.join(SAVE_DIR, "best_model_v2.pt"))
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            print(f"⚠️ No improvement in Val F1. Early stopping counter: {epochs_no_improve}/{PATIENCE}")
            
        if epochs_no_improve >= PATIENCE:
            print("\n⏹️ Early Stopping Triggered! Training Halted.")
            break

    print(f"\n🎉 Training Complete! Best Validation Macro-F1: {best_val_f1:.4f}")
    print(f"Model saved at: {os.path.join(SAVE_DIR, 'best_model_v2.pt')}")

if __name__ == "__main__":
    main()
