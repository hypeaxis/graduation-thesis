"""
Phase 2 (V3): Training script for FT-Transformer Enhanced (CIC-IDS-2017)
Improvements over V2:
  - Cosine Annealing LR + Linear Warmup (3 epochs)
  - Aggressive SMOTE (50,000 min samples/class)
  - Reduced Label Smoothing (0.05)
  - 20 Epochs, Patience 6
  - Exponential Moving Average (EMA, decay=0.999)
  - Full Classification Report + Confusion Matrix at end
"""

import os
import copy
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import math
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score
)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
from imblearn.over_sampling import SMOTE

from phase2_ft_transformer_v2 import FTTransformer


# ───────────────────────────────────────────────────────────────────────────
# Dataset
# ───────────────────────────────────────────────────────────────────────────
class CICDataset(Dataset):
    """PyTorch Dataset for CIC-IDS-2017."""
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


# ───────────────────────────────────────────────────────────────────────────
# Cosine Annealing with Linear Warmup
# ───────────────────────────────────────────────────────────────────────────
class CosineAnnealingWarmup(torch.optim.lr_scheduler._LRScheduler):
    """
    Linear warmup cho warmup_epochs đầu tiên,
    sau đó Cosine Annealing giảm dần LR từ base_lr xuống min_lr.
    """
    def __init__(self, optimizer, warmup_epochs, total_epochs, min_lr=1e-6, last_epoch=-1):
        self.warmup_epochs = warmup_epochs
        self.total_epochs = total_epochs
        self.min_lr = min_lr
        super().__init__(optimizer, last_epoch)

    def get_lr(self):
        if self.last_epoch < self.warmup_epochs:
            # Linear warmup: 0 → base_lr
            warmup_factor = (self.last_epoch + 1) / self.warmup_epochs
            return [base_lr * warmup_factor for base_lr in self.base_lrs]
        else:
            # Cosine annealing: base_lr → min_lr
            progress = (self.last_epoch - self.warmup_epochs) / max(1, self.total_epochs - self.warmup_epochs)
            cosine_factor = 0.5 * (1.0 + math.cos(math.pi * progress))
            return [
                self.min_lr + (base_lr - self.min_lr) * cosine_factor
                for base_lr in self.base_lrs
            ]


# ───────────────────────────────────────────────────────────────────────────
# EMA (Exponential Moving Average)
# ───────────────────────────────────────────────────────────────────────────
class EMAModel:
    """
    Duy trì bản sao trung bình trượt của trọng số model.
    Bản sao EMA thường cho kết quả validation tốt hơn 1-3%.
    """
    def __init__(self, model, decay=0.999):
        self.decay = decay
        self.ema_model = copy.deepcopy(model)
        self.ema_model.eval()
        for p in self.ema_model.parameters():
            p.requires_grad_(False)

    @torch.no_grad()
    def update(self, model):
        for ema_param, param in zip(self.ema_model.parameters(), model.parameters()):
            ema_param.data.mul_(self.decay).add_(param.data, alpha=1.0 - self.decay)

    def state_dict(self):
        return self.ema_model.state_dict()

    def module(self):
        return self.ema_model


# ───────────────────────────────────────────────────────────────────────────
# Data Loading & Preprocessing
# ───────────────────────────────────────────────────────────────────────────
def load_chunk_data(train_csv, val_csv, batch_size=256):
    """Load Train và Val Chunk, áp dụng SMOTE aggressive (50k min)."""
    print("Loading Train Chunk...")
    df_train = pd.read_csv(train_csv)
    print("Loading Validation Chunk...")
    df_val = pd.read_csv(val_csv)

    label_col = 'Label'
    X_train_raw = df_train.drop(columns=[label_col]).values
    y_train_raw = df_train[label_col].values

    X_val_raw = df_val.drop(columns=[label_col]).values
    y_val_raw = df_val[label_col].values

    # ═══ SMOTE Aggressive: min 50,000 mẫu/class ═══
    print("Applying SMOTE (Aggressive: 50,000 min samples/class)...")
    label_counts = pd.Series(y_train_raw).value_counts()
    max_count = label_counts.max()
    strategy = {label: max(50000, count) for label, count in label_counts.items()}
    strategy[label_counts.idxmax()] = max_count

    print("  SMOTE Strategy:")
    for label, target in sorted(strategy.items(), key=lambda x: x[1], reverse=True):
        original = label_counts[label]
        print(f"    {label:15s}: {original:8,} → {target:8,} {'(+SMOTE)' if target > original else '(giữ nguyên)'}")

    smote = SMOTE(sampling_strategy=strategy, random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train_raw, y_train_raw)

    print("Scaling Features using StandardScaler...")
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

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4, pin_memory=True)

    return train_loader, val_loader, label_encoder, classes, num_features, y_train, scaler


# ───────────────────────────────────────────────────────────────────────────
# Training & Validation
# ───────────────────────────────────────────────────────────────────────────
def train_epoch(model, train_loader, criterion, optimizer, device, amp_scaler, ema):
    model.train()
    total_loss = 0
    all_preds, all_labels = [], []

    pbar = tqdm(train_loader, desc="Training", leave=False)
    for features, labels in pbar:
        features, labels = features.to(device), labels.to(device)

        optimizer.zero_grad(set_to_none=True)

        with torch.amp.autocast('cuda'):
            logits = model(features)
            loss = criterion(logits, labels)

        amp_scaler.scale(loss).backward()
        amp_scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        amp_scaler.step(optimizer)
        amp_scaler.update()

        # Cập nhật EMA sau mỗi step
        ema.update(model)

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
            with torch.amp.autocast('cuda'):
                logits = model(features)
                loss = criterion(logits, labels)

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(val_loader)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    return avg_loss, macro_f1, all_preds, all_labels


# ───────────────────────────────────────────────────────────────────────────
# Plotting Utilities
# ───────────────────────────────────────────────────────────────────────────
def plot_training_curves(history, save_dir):
    """Vẽ biểu đồ Loss và F1 qua các epochs."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    epochs = range(1, len(history['train_loss']) + 1)

    # Loss curve
    axes[0].plot(epochs, history['train_loss'], 'b-o', label='Train Loss', markersize=4)
    axes[0].plot(epochs, history['val_loss'], 'r-o', label='Val Loss', markersize=4)
    axes[0].set_title('Loss per Epoch', fontsize=14)
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # F1 curve
    axes[1].plot(epochs, history['train_f1'], 'b-o', label='Train Macro-F1', markersize=4)
    axes[1].plot(epochs, history['val_f1'], 'r-o', label='Val Macro-F1 (Model)', markersize=4)
    axes[1].plot(epochs, history['ema_val_f1'], 'g-s', label='Val Macro-F1 (EMA)', markersize=4)
    axes[1].set_title('Macro-F1 per Epoch', fontsize=14)
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Macro-F1')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'training_curves_v3.png'), dpi=150)
    plt.close()
    print(f"📊 Training curves saved to {save_dir}/training_curves_v3.png")


def plot_confusion_matrix(y_true, y_pred, class_names, save_dir, title="Confusion Matrix"):
    """Vẽ Confusion Matrix."""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title(title, fontsize=14)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'confusion_matrix_v3.png'), dpi=150)
    plt.close()
    print(f"📊 Confusion matrix saved to {save_dir}/confusion_matrix_v3.png")


# ───────────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────────
def main():
    # ═══ Hyperparameters V3 ═══
    TRAIN_CSV = 'processed_data/cic_train_chunk.csv'
    VAL_CSV = 'processed_data/cic_test_chunk_1.csv'
    SAVE_DIR = 'models/v3_improved'

    NUM_EPOCHS = 10
    LEARNING_RATE = 1e-4
    WEIGHT_DECAY = 1e-4
    PATIENCE = 6
    WARMUP_EPOCHS = 3
    EMA_DECAY = 0.999
    LABEL_SMOOTHING = 0.05  # Giảm từ 0.1 xuống 0.05

    os.makedirs(SAVE_DIR, exist_ok=True)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    print(f"\n{'='*60}")
    print(f"  FT-Transformer V3 - Improved Training")
    print(f"  Epochs: {NUM_EPOCHS} | Patience: {PATIENCE} | Warmup: {WARMUP_EPOCHS}")
    print(f"  LR: {LEARNING_RATE} | Label Smoothing: {LABEL_SMOOTHING}")
    print(f"  EMA Decay: {EMA_DECAY}")
    print(f"{'='*60}")

    # Load data
    train_loader, val_loader, encoder, class_names, num_features, y_train_full, scaler = \
        load_chunk_data(TRAIN_CSV, VAL_CSV)

    # Initialize model (giữ nguyên d_model=128 theo yêu cầu)
    print("\nInitializing FT-Transformer V3...")
    model = FTTransformer(
        num_features=num_features,
        num_classes=len(class_names),
        d_model=128,
        num_layers=4,
        num_heads=8,
        dropout=0.2,
        drop_path_rate=0.1
    ).to(device)

    # EMA
    ema = EMAModel(model, decay=EMA_DECAY)

    # Class Weights
    c_weights = compute_class_weight('balanced', classes=np.unique(y_train_full), y=y_train_full)
    c_weights_tensor = torch.tensor(c_weights, dtype=torch.float32).to(device)
    print(f"\nClass Weights: {c_weights_tensor.cpu().numpy().round(4)}")

    # Loss, Optimizer, Scheduler
    criterion = nn.CrossEntropyLoss(weight=c_weights_tensor, label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = CosineAnnealingWarmup(optimizer, warmup_epochs=WARMUP_EPOCHS, total_epochs=NUM_EPOCHS)

    print(f"\nModel Params: {sum(p.numel() for p in model.parameters()):,}")
    print("\n🚀 READY FOR TRAINING!\n")

    # Training history
    history = {'train_loss': [], 'val_loss': [], 'train_f1': [], 'val_f1': [], 'ema_val_f1': [], 'lr': []}
    best_val_f1 = 0.0
    best_ema_f1 = 0.0
    epochs_no_improve = 0

    torch.backends.cudnn.benchmark = True
    amp_scaler = torch.amp.GradScaler('cuda')

    for epoch in range(NUM_EPOCHS):
        current_lr = optimizer.param_groups[0]['lr']
        print(f"\nEpoch {epoch+1}/{NUM_EPOCHS} | LR: {current_lr:.6f}")
        print("-" * 50)

        start_time = time.time()

        # Train
        train_loss, train_f1 = train_epoch(model, train_loader, criterion, optimizer, device, amp_scaler, ema)

        # Validate (model gốc)
        val_loss, val_f1, val_preds, val_labels = validate(model, val_loader, criterion, device)

        # Validate (EMA model)
        _, ema_val_f1, ema_preds, ema_labels = validate(ema.module(), val_loader, criterion, device)

        # Step scheduler (sau mỗi epoch)
        scheduler.step()

        epoch_mins, epoch_secs = divmod(time.time() - start_time, 60)

        # Lưu history
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_f1'].append(train_f1)
        history['val_f1'].append(val_f1)
        history['ema_val_f1'].append(ema_val_f1)
        history['lr'].append(current_lr)

        print(f"Time: {int(epoch_mins)}m {int(epoch_secs)}s")
        print(f"Train Loss: {train_loss:.4f} | Train Macro-F1: {train_f1:.4f}")
        print(f"Val Loss:   {val_loss:.4f} | Val Macro-F1:   {val_f1:.4f}")
        print(f"EMA Val Macro-F1: {ema_val_f1:.4f}")

        # Lấy F1 tốt nhất giữa model gốc và EMA
        epoch_best_f1 = max(val_f1, ema_val_f1)
        use_ema = ema_val_f1 > val_f1

        # Checkpointing
        if epoch_best_f1 > best_val_f1:
            print(f"🌟 Best Macro-F1 improved: {best_val_f1:.4f} → {epoch_best_f1:.4f} "
                  f"({'EMA' if use_ema else 'Model'}). Saving...")
            best_val_f1 = epoch_best_f1
            # Lưu cả 2 versions
            torch.save(model.state_dict(), os.path.join(SAVE_DIR, "best_model_v3.pt"))
            torch.save(ema.state_dict(), os.path.join(SAVE_DIR, "best_model_v3_ema.pt"))
            # Lưu predictions tốt nhất để vẽ confusion matrix cuối cùng
            best_preds = ema_preds if use_ema else val_preds
            best_labels = ema_labels if use_ema else val_labels
            epochs_no_improve = 0
        else:
            epochs_no_improve += 1
            print(f"⚠️ No improvement. Early stopping counter: {epochs_no_improve}/{PATIENCE}")

        if epochs_no_improve >= PATIENCE:
            print("\n⏹️ Early Stopping Triggered!")
            break

    # ═══ Final Report ═══
    print(f"\n{'='*60}")
    print(f"  🎉 TRAINING COMPLETE!")
    print(f"  Best Validation Macro-F1: {best_val_f1:.4f}")
    print(f"{'='*60}")

    # Classification Report
    print("\n📋 Classification Report (Best Model):")
    print(classification_report(best_labels, best_preds, target_names=class_names, digits=4))

    # Plot training curves
    plot_training_curves(history, SAVE_DIR)

    # Plot confusion matrix
    plot_confusion_matrix(best_labels, best_preds, class_names, SAVE_DIR,
                          title=f"FT-Transformer V3 - Best Macro-F1: {best_val_f1:.4f}")

    # Save training history
    hist_df = pd.DataFrame(history)
    hist_df.to_csv(os.path.join(SAVE_DIR, 'training_history_v3.csv'), index=False)

    print(f"\nAll artifacts saved to: {SAVE_DIR}/")
    print(f"  - best_model_v3.pt (Model weights)")
    print(f"  - best_model_v3_ema.pt (EMA weights)")
    print(f"  - training_curves_v3.png")
    print(f"  - confusion_matrix_v3.png")
    print(f"  - training_history_v3.csv")


if __name__ == "__main__":
    main()
