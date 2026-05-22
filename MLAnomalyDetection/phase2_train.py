"""
Phase 2: Training script for FT-Transformer with Focal Loss
Includes stratified sampling, evaluation metrics (Macro-F1), and model checkpointing.
"""

import os
import time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    precision_score, recall_score, accuracy_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm

from phase2_ft_transformer import FTTransformer, FocalLoss


class NetworkTrafficDataset(Dataset):
    """PyTorch Dataset for network traffic data."""
    
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
    
    def __len__(self):
        return len(self.labels)
    
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


def load_and_prepare_data(data_path, test_size=0.2, val_size=0.1, random_state=42):
    """
    Load augmented dataset and prepare train/val/test splits.
    
    Args:
        data_path: Path to augmented_dataset_shuffled.csv
        test_size: Fraction for test set
        val_size: Fraction of training set for validation
        random_state: Random seed for reproducibility
    
    Returns:
        Tuple of (train_loader, val_loader, test_loader, label_encoder, class_names, num_features)
    """
    print("Loading dataset...")
    df = pd.read_csv(data_path)
    print(f"Dataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Separate features and labels
    if 'Label' in df.columns:
        label_col = 'Label'
    elif ' Label' in df.columns:
        label_col = ' Label'
    else:
        raise ValueError("No 'Label' column found in dataset")
    
    X = df.drop(columns=[label_col]).values
    y = df[label_col].values
    
    # Remove any string whitespace from labels
    if y.dtype == 'object':
        y = np.array([str(label).strip() for label in y])
    
    # Encode labels
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y)
    
    num_features = X.shape[1]
    num_classes = len(label_encoder.classes_)
    class_names = label_encoder.classes_
    
    print(f"\nDataset Info:")
    print(f"  Features: {num_features}")
    print(f"  Classes: {num_classes}")
    print(f"  Total samples: {len(X):,}")
    
    # Class distribution
    unique, counts = np.unique(y_encoded, return_counts=True)
    print(f"\nClass Distribution:")
    for idx, count in zip(unique, counts):
        print(f"  {class_names[idx]:30s}: {count:8,} ({count/len(y_encoded)*100:5.2f}%)")
    
    # Stratified split: train+val / test
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y_encoded,
        test_size=test_size,
        stratify=y_encoded,
        random_state=random_state
    )
    
    # Stratified split: train / val
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val,
        test_size=val_size,
        stratify=y_train_val,
        random_state=random_state
    )
    
    print(f"\nSplit sizes:")
    print(f"  Train: {len(X_train):,} samples")
    print(f"  Val:   {len(X_val):,} samples")
    print(f"  Test:  {len(X_test):,} samples")
    
    # Create datasets and dataloaders
    train_dataset = NetworkTrafficDataset(X_train, y_train)
    val_dataset = NetworkTrafficDataset(X_val, y_val)
    test_dataset = NetworkTrafficDataset(X_test, y_test)
    
    # Use larger batch size for efficiency (but ensure minority classes appear)
    batch_size = 512
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=4,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True
    )
    
    return train_loader, val_loader, test_loader, label_encoder, class_names, num_features


def train_epoch(model, train_loader, criterion, optimizer, device):
    """Train for one epoch."""
    model.train()
    total_loss = 0
    all_preds = []
    all_labels = []
    
    pbar = tqdm(train_loader, desc="Training", leave=False)
    for features, labels in pbar:
        features, labels = features.to(device), labels.to(device)
        
        # Forward pass
        optimizer.zero_grad()
        logits = model(features)
        loss = criterion(logits, labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        
        # Track metrics
        total_loss += loss.item()
        preds = torch.argmax(logits, dim=1)
        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
        
        pbar.set_postfix({'loss': f'{loss.item():.4f}'})
    
    avg_loss = total_loss / len(train_loader)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    
    return avg_loss, macro_f1


def validate(model, val_loader, criterion, device):
    """Validate the model."""
    model.eval()
    total_loss = 0
    all_preds = []
    all_labels = []
    
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


def evaluate_model(model, test_loader, class_names, device, save_dir='results'):
    """
    Comprehensive evaluation with per-class metrics.
    
    Returns detailed classification report and confusion matrix.
    """
    model.eval()
    all_preds = []
    all_labels = []
    
    print("\nEvaluating on test set...")
    with torch.no_grad():
        for features, labels in tqdm(test_loader, desc="Testing"):
            features = features.to(device)
            logits = model(features)
            preds = torch.argmax(logits, dim=1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    
    # Convert to numpy
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    
    # Calculate metrics
    accuracy = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    weighted_f1 = f1_score(all_labels, all_preds, average='weighted', zero_division=0)
    macro_precision = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    macro_recall = recall_score(all_labels, all_preds, average='macro', zero_division=0)
    
    print("\n" + "="*80)
    print("EVALUATION RESULTS")
    print("="*80)
    print(f"Accuracy:           {accuracy:.4f}")
    print(f"Macro-F1 Score:     {macro_f1:.4f}  ← PRIMARY METRIC")
    print(f"Weighted-F1 Score:  {weighted_f1:.4f}")
    print(f"Macro Precision:    {macro_precision:.4f}")
    print(f"Macro Recall:       {macro_recall:.4f}")
    
    # Detailed classification report
    print("\n" + "="*80)
    print("PER-CLASS METRICS")
    print("="*80)
    report = classification_report(
        all_labels, all_preds,
        target_names=class_names,
        digits=4,
        zero_division=0
    )
    print(report)
    
    # Confusion matrix
    cm = confusion_matrix(all_labels, all_preds)
    
    # Create results directory
    os.makedirs(save_dir, exist_ok=True)
    
    # Save confusion matrix plot
    plt.figure(figsize=(16, 14))
    sns.heatmap(
        cm, annot=True, fmt='d', cmap='Blues',
        xticklabels=class_names, yticklabels=class_names
    )
    plt.title('Confusion Matrix - FT-Transformer with Focal Loss')
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(f'{save_dir}/confusion_matrix.png', dpi=300, bbox_inches='tight')
    print(f"\nConfusion matrix saved to {save_dir}/confusion_matrix.png")
    
    # Save detailed metrics to CSV
    per_class_metrics = classification_report(
        all_labels, all_preds,
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )
    
    metrics_df = pd.DataFrame(per_class_metrics).transpose()
    metrics_df.to_csv(f'{save_dir}/per_class_metrics.csv')
    print(f"Per-class metrics saved to {save_dir}/per_class_metrics.csv")
    
    # Highlight minority classes
    print("\n" + "="*80)
    print("MINORITY CLASS PERFORMANCE (Previously Augmented Classes)")
    print("="*80)
    minority_classes = [
        'Infiltration', 'Web Attack � Sql Injection', 'Heartbleed',
        'Bot', 'Web Attack � Brute Force', 'Web Attack � XSS'
    ]
    
    for cls in minority_classes:
        if cls in per_class_metrics:
            metrics = per_class_metrics[cls]
            print(f"{cls:35s}: F1={metrics['f1-score']:.4f}, "
                  f"Precision={metrics['precision']:.4f}, "
                  f"Recall={metrics['recall']:.4f}, "
                  f"Support={int(metrics['support'])}")
    
    return {
        'accuracy': accuracy,
        'macro_f1': macro_f1,
        'weighted_f1': weighted_f1,
        'macro_precision': macro_precision,
        'macro_recall': macro_recall,
        'confusion_matrix': cm,
        'per_class_metrics': per_class_metrics
    }


def train_model(
    model, train_loader, val_loader, criterion, optimizer, scheduler,
    num_epochs, device, save_dir='models', patience=5
):
    """
    Train the model with early stopping and checkpointing.
    """
    os.makedirs(save_dir, exist_ok=True)
    
    best_val_f1 = 0
    patience_counter = 0
    history = {
        'train_loss': [], 'train_f1': [],
        'val_loss': [], 'val_f1': []
    }
    
    print("\n" + "="*80)
    print("TRAINING FT-TRANSFORMER WITH FOCAL LOSS")
    print("="*80)
    
    for epoch in range(num_epochs):
        start_time = time.time()
        
        # Train
        train_loss, train_f1 = train_epoch(model, train_loader, criterion, optimizer, device)
        
        # Validate
        val_loss, val_f1 = validate(model, val_loader, criterion, device)
        
        # Update learning rate
        scheduler.step(val_f1)
        
        # Track history
        history['train_loss'].append(train_loss)
        history['train_f1'].append(train_f1)
        history['val_loss'].append(val_loss)
        history['val_f1'].append(val_f1)
        
        epoch_time = time.time() - start_time
        
        print(f"\nEpoch {epoch+1}/{num_epochs} ({epoch_time:.1f}s)")
        print(f"  Train - Loss: {train_loss:.4f}, Macro-F1: {train_f1:.4f}")
        print(f"  Val   - Loss: {val_loss:.4f}, Macro-F1: {val_f1:.4f}")
        print(f"  LR: {optimizer.param_groups[0]['lr']:.6f}")
        
        # Save best model
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': val_f1,
                'val_loss': val_loss,
            }, f'{save_dir}/best_model.pt')
            print(f"  ✓ New best model saved! (Macro-F1: {val_f1:.4f})")
        else:
            patience_counter += 1
            print(f"  No improvement ({patience_counter}/{patience})")
        
        # Early stopping
        if patience_counter >= patience:
            print(f"\nEarly stopping triggered after {epoch+1} epochs")
            break
    
    # Plot training history
    plot_training_history(history, save_dir)
    
    return history


def plot_training_history(history, save_dir):
    """Plot and save training history."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
    
    # Loss plot
    ax1.plot(history['train_loss'], label='Train Loss', marker='o')
    ax1.plot(history['val_loss'], label='Val Loss', marker='s')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Validation Loss')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # F1 plot
    ax2.plot(history['train_f1'], label='Train Macro-F1', marker='o')
    ax2.plot(history['val_f1'], label='Val Macro-F1', marker='s')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Macro-F1 Score')
    ax2.set_title('Training and Validation Macro-F1')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{save_dir}/training_history.png', dpi=300, bbox_inches='tight')
    print(f"\nTraining history saved to {save_dir}/training_history.png")


def main():
    # Configuration
    DATA_PATH = 'data/augmented/augmented_dataset_shuffled.csv'
    SAVE_DIR = 'models/phase2'
    RESULTS_DIR = 'results/phase2'
    
    # Hyperparameters (based on research recommendations)
    NUM_EPOCHS = 50
    LEARNING_RATE = 1e-4
    WEIGHT_DECAY = 1e-5
    PATIENCE = 7
    
    # Model architecture
    D_MODEL = 128
    NUM_HEADS = 8
    NUM_LAYERS = 4
    D_FF = 512
    DROPOUT = 0.1
    
    # Focal Loss parameters
    FOCAL_GAMMA = 2.0
    FOCAL_ALPHA = 0.25
    
    # Set device (priority: CUDA -> MPS -> CPU)
    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')
    print(f"\nUsing device: {device}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    
    # Load data
    train_loader, val_loader, test_loader, label_encoder, class_names, num_features = \
        load_and_prepare_data(DATA_PATH)
    
    num_classes = len(class_names)
    
    # Create model
    print(f"\nInitializing FT-Transformer...")
    print(f"  Input features: {num_features}")
    print(f"  Output classes: {num_classes}")
    print(f"  d_model: {D_MODEL}, num_heads: {NUM_HEADS}, num_layers: {NUM_LAYERS}")
    
    model = FTTransformer(
        num_features=num_features,
        num_classes=num_classes,
        d_model=D_MODEL,
        num_heads=NUM_HEADS,
        num_layers=NUM_LAYERS,
        d_ff=D_FF,
        dropout=DROPOUT
    ).to(device)
    
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Total parameters: {total_params:,}")
    print(f"  Trainable parameters: {trainable_params:,}")
    
    # Loss function (Focal Loss)
    criterion = FocalLoss(gamma=FOCAL_GAMMA, alpha=FOCAL_ALPHA, num_classes=num_classes)
    print(f"\nUsing Focal Loss (γ={FOCAL_GAMMA}, α={FOCAL_ALPHA})")
    
    # Optimizer and scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='max', factor=0.5, patience=3
    )
    
    # Train
    history = train_model(
        model, train_loader, val_loader, criterion, optimizer, scheduler,
        NUM_EPOCHS, device, SAVE_DIR, PATIENCE
    )
    
    # Load best model for evaluation
    print("\nLoading best model for final evaluation...")
    checkpoint = torch.load(f'{SAVE_DIR}/best_model.pt')
    model.load_state_dict(checkpoint['model_state_dict'])
    print(f"Best model from epoch {checkpoint['epoch']+1}")
    print(f"Validation Macro-F1: {checkpoint['val_f1']:.4f}")
    
    # Final evaluation on test set
    test_metrics = evaluate_model(model, test_loader, class_names, device, RESULTS_DIR)
    
    # Save final summary
    summary = {
        'model': 'FT-Transformer',
        'focal_loss_gamma': FOCAL_GAMMA,
        'focal_loss_alpha': FOCAL_ALPHA,
        'num_epochs_trained': len(history['train_loss']),
        'best_epoch': checkpoint['epoch'] + 1,
        'best_val_macro_f1': checkpoint['val_f1'],
        'test_macro_f1': test_metrics['macro_f1'],
        'test_accuracy': test_metrics['accuracy'],
        'test_weighted_f1': test_metrics['weighted_f1'],
    }
    
    summary_df = pd.DataFrame([summary])
    summary_df.to_csv(f'{RESULTS_DIR}/training_summary.csv', index=False)
    
    print("\n" + "="*80)
    print("TRAINING COMPLETE!")
    print("="*80)
    print(f"Best Validation Macro-F1: {checkpoint['val_f1']:.4f}")
    print(f"Test Macro-F1:            {test_metrics['macro_f1']:.4f}")
    print(f"Test Accuracy:            {test_metrics['accuracy']:.4f}")
    print(f"\nResults saved to: {RESULTS_DIR}/")
    print(f"Model saved to:   {SAVE_DIR}/best_model.pt")
    print("="*80)


if __name__ == "__main__":
    main()
