"""
Improved FT-Transformer Training for NSL-KDD IDS (Two-Stage, 4-class attack)
==============================================================================
Anti-overfitting features:
  - Label smoothing focal loss
  - Increased dropout (0.2) + weight decay (5e-4)
  - Mixup augmentation
  - CosineAnnealingWarmRestarts scheduler
  - Overfitting guard (train-val gap monitoring)
  - Gradient clipping (max_norm=1.0)

Produces detailed log reports for each run.
"""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
import torch.nn as nn
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from tqdm import tqdm

# Local imports
from phase2_ft_transformer import FTTransformer, FocalLoss, LabelSmoothingFocalLoss
from improved_data_pipeline import load_and_preprocess

# ──────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────

class Config:
    # Task
    TASK_TYPE = '4-class-attack'
    SEED = 42

    # Data
    VAL_SIZE = 0.20
    RESAMPLER = 'none'
    TARGET_U2R = 1500
    TARGET_R2L = 4000
    TARGET_DOS_CAP = 25000
    TARGET_NORMAL_CAP = 30000
    UNDERSAMPLE = False
    K_NEIGHBORS = 5

    # Model architecture (same as deployed model for compat)
    D_MODEL = 128
    NUM_HEADS = 8
    NUM_LAYERS = 4
    D_FF = 512

    # Anti-overfitting
    DROPOUT = 0.20          # Increased from 0.1
    WEIGHT_DECAY = 1e-3     # Increased from 1e-4 to 1e-3
    LABEL_SMOOTHING = 0.0   # Disabled for sharper boundaries
    MIXUP_ALPHA = 0.0       # Disabled to avoid excessive noise
    GRADIENT_CLIP = 1.0     # Gradient clipping

    # Training
    NUM_EPOCHS = 30
    BATCH_SIZE = 256        # Fine for GTX 1050 4GB
    LEARNING_RATE = 1e-4
    PATIENCE = 8            # Early stopping patience

    # Focal Loss
    FOCAL_GAMMA = 3.0       # Increased from 2.0 to focus heavily on hard misclassified examples
    CLASS_BALANCED_BETA = 0.999 # Smoother alpha weights

    # Scheduler
    SCHEDULER = 'cosine'    # 'cosine' or 'plateau'
    COSINE_T0 = 10
    COSINE_T_MULT = 2
    COSINE_ETA_MIN = 1e-6

    # Overfitting guard
    SELECTION_GAP_PENALTY = 0.3
    MAX_TRAIN_VAL_GAP = 0.15
    GAP_PATIENCE = 4

    # Sampler
    SAMPLER = 'weighted_sqrt'


# ──────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────

def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def setup_logging(output_dir: Path) -> logging.Logger:
    """Create logger that writes to both file and console."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = output_dir / f'training_log_{timestamp}.txt'

    logger = logging.getLogger('IDS_Training')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f'Log file: {log_file}')
    return logger


def pick_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device('cuda')
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


# ──────────────────────────────────────────────────────────────────
# Dataset & DataLoader
# ──────────────────────────────────────────────────────────────────

class TabularDataset(Dataset):
    def __init__(self, features: np.ndarray, labels: np.ndarray) -> None:
        self.features = torch.as_tensor(features, dtype=torch.float32)
        self.labels = torch.as_tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return self.labels.shape[0]

    def __getitem__(self, index: int):
        return self.features[index], self.labels[index]


def build_weighted_sampler(targets: np.ndarray, seed: int) -> WeightedRandomSampler:
    class_counts = np.bincount(targets)
    class_weights = np.zeros_like(class_counts, dtype=np.float64)
    nonzero = class_counts > 0
    # Use smoothed inverse frequency (sqrt) to prevent extreme weighting of U2R
    class_weights[nonzero] = 1.0 / np.sqrt(class_counts[nonzero])
    sample_weights = class_weights[targets]

    generator = torch.Generator()
    generator.manual_seed(seed)
    return WeightedRandomSampler(
        weights=torch.as_tensor(sample_weights, dtype=torch.double),
        num_samples=len(sample_weights),
        replacement=True,
        generator=generator,
    )


def create_loaders(data_bundle: dict, cfg: Config, device: torch.device) -> dict:
    pin = device.type == 'cuda'
    train_ds = TabularDataset(*data_bundle['train'])
    val_ds = TabularDataset(*data_bundle['val'])
    test_ds = TabularDataset(*data_bundle['test'])

    sampler = None
    shuffle = True
    if cfg.SAMPLER.startswith('weighted'):
        sampler = build_weighted_sampler(data_bundle['train'][1], cfg.SEED)
        shuffle = False

    return {
        'train': DataLoader(train_ds, batch_size=cfg.BATCH_SIZE, shuffle=shuffle,
                            sampler=sampler, num_workers=0, pin_memory=pin),
        'val': DataLoader(val_ds, batch_size=cfg.BATCH_SIZE, shuffle=False,
                          num_workers=0, pin_memory=pin),
        'test': DataLoader(test_ds, batch_size=cfg.BATCH_SIZE, shuffle=False,
                           num_workers=0, pin_memory=pin),
    }


# ──────────────────────────────────────────────────────────────────
# Focal alpha
# ──────────────────────────────────────────────────────────────────

def compute_class_balanced_alpha(targets: np.ndarray, num_classes: int,
                                  beta: float) -> list:
    counts = np.bincount(targets, minlength=num_classes).astype(np.float64)
    eff = np.ones_like(counts)
    nz = counts > 0
    eff[nz] = 1.0 - np.power(beta, counts[nz])
    alpha = np.zeros_like(counts, dtype=np.float64)
    alpha[nz] = (1.0 - beta) / np.clip(eff[nz], 1e-12, None)
    alpha[nz] = alpha[nz] / alpha[nz].sum() * nz.sum()
    return alpha.astype(np.float32).tolist()


# ──────────────────────────────────────────────────────────────────
# Mixup
# ──────────────────────────────────────────────────────────────────

def mixup_batch(features, labels, alpha, num_classes):
    if alpha <= 0:
        return features, labels, labels, 1.0
    lam = float(np.random.beta(alpha, alpha))
    idx = torch.randperm(features.size(0), device=features.device)
    mixed = lam * features + (1 - lam) * features[idx]
    return mixed, labels, labels[idx], lam


def soft_focal_loss(logits, soft_targets, criterion):
    log_probs = torch.log_softmax(logits, dim=1)
    probs = log_probs.exp()
    pt = (soft_targets * probs).sum(dim=1).clamp(1e-8, 1.0)
    log_pt = (soft_targets * log_probs).sum(dim=1)
    alpha = criterion.alpha.to(logits.device)
    alpha_t = (soft_targets * alpha.unsqueeze(0)).sum(dim=1)
    loss = -alpha_t * torch.pow(1.0 - pt, criterion.gamma) * log_pt
    return loss.mean()


# ──────────────────────────────────────────────────────────────────
# Training & Evaluation
# ──────────────────────────────────────────────────────────────────

def run_epoch(model, loader, criterion, optimizer, device, train: bool,
              mixup_alpha: float, num_classes: int, grad_clip: float):
    model.train(mode=train)
    total_loss = 0.0
    all_preds = []
    all_labels = []

    ctx = torch.enable_grad() if train else torch.no_grad()
    with ctx:
        for features, labels in tqdm(loader, desc='Train' if train else 'Val',
                                     leave=False):
            features = features.to(device)
            labels = labels.to(device)
            labels_for_metrics = labels

            if train:
                optimizer.zero_grad()
                if mixup_alpha > 0:
                    features, la, lb, lam = mixup_batch(
                        features, labels, mixup_alpha, num_classes)

            logits = model(features)

            if train and mixup_alpha > 0:
                ta = nn.functional.one_hot(la, num_classes).float()
                tb = nn.functional.one_hot(lb, num_classes).float()
                soft = lam * ta + (1 - lam) * tb
                loss = soft_focal_loss(logits, soft, criterion)
            else:
                loss = criterion(logits, labels)

            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=grad_clip)
                optimizer.step()

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.detach().cpu().tolist())
            all_labels.extend(labels_for_metrics.detach().cpu().tolist())

    avg_loss = total_loss / max(len(loader), 1)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    acc = accuracy_score(all_labels, all_preds)
    return avg_loss, macro_f1, acc


def evaluate_full(model, loader, class_names, device, output_dir: Path,
                  logger: logging.Logger) -> dict:
    """Full evaluation with per-class metrics, confusion matrix, and report."""
    model.eval()
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for features, labels in tqdm(loader, desc='Test', leave=False):
            logits = model(features.to(device))
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    acc = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    weighted_f1 = f1_score(all_labels, all_preds, average='weighted', zero_division=0)
    macro_prec = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    macro_rec = recall_score(all_labels, all_preds, average='macro', zero_division=0)

    report_dict = classification_report(
        all_labels, all_preds, target_names=class_names,
        output_dict=True, zero_division=0)
    report_text = classification_report(
        all_labels, all_preds, target_names=class_names,
        digits=4, zero_division=0)
    cm = confusion_matrix(all_labels, all_preds)

    logger.info('\n' + '=' * 70)
    logger.info('TEST EVALUATION RESULTS')
    logger.info('=' * 70)
    logger.info(f'Accuracy:           {acc:.4f}')
    logger.info(f'Macro-F1 Score:     {macro_f1:.4f}  ← PRIMARY METRIC')
    logger.info(f'Weighted-F1 Score:  {weighted_f1:.4f}')
    logger.info(f'Macro Precision:    {macro_prec:.4f}')
    logger.info(f'Macro Recall:       {macro_rec:.4f}')
    logger.info('\nPER-CLASS METRICS:')
    logger.info(report_text)

    # Save artifacts
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(report_dict).transpose().to_csv(output_dir / 'per_class_metrics.csv')
    with open(output_dir / 'classification_report.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)

    # Confusion matrix
    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix - Improved FT-Transformer')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.tight_layout()
    plt.savefig(output_dir / 'confusion_matrix.png', dpi=200, bbox_inches='tight')
    plt.close()

    return {
        'accuracy': acc, 'macro_f1': macro_f1, 'weighted_f1': weighted_f1,
        'macro_precision': macro_prec, 'macro_recall': macro_rec,
        'report_dict': report_dict, 'confusion_matrix': cm.tolist(),
    }


def plot_history(history: dict, output_dir: Path):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Loss
    axes[0].plot(history['train_loss'], label='Train', marker='o', markersize=3)
    axes[0].plot(history['val_loss'], label='Val', marker='s', markersize=3)
    axes[0].set_title('Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Macro-F1
    axes[1].plot(history['train_f1'], label='Train F1', marker='o', markersize=3)
    axes[1].plot(history['val_f1'], label='Val F1', marker='s', markersize=3)
    axes[1].set_title('Macro-F1')
    axes[1].set_xlabel('Epoch')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Train-Val Gap
    axes[2].plot(history['gap'], label='Train-Val F1 Gap', marker='d',
                 markersize=3, color='red')
    axes[2].axhline(y=0.15, color='orange', linestyle='--', label='Gap threshold')
    axes[2].set_title('Overfitting Monitor')
    axes[2].set_xlabel('Epoch')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'training_history.png', dpi=200, bbox_inches='tight')
    plt.close(fig)


# ──────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────

def main():
    cfg = Config()
    set_seed(cfg.SEED)

    base_dir = Path(__file__).resolve().parent
    run_name = f'improved_4class_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    output_dir = base_dir / 'outputs' / 'improved_runs' / run_name
    model_dir = output_dir / 'models'
    results_dir = output_dir / 'results'
    model_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    logger = setup_logging(output_dir)
    device = pick_device()
    logger.info(f'Device: {device}')
    if device.type == 'cuda':
        logger.info(f'GPU: {torch.cuda.get_device_name(0)}')

    # ── Load & resample data ──
    logger.info('\n' + '=' * 70)
    logger.info('PHASE 1: DATA LOADING & RESAMPLING')
    logger.info('=' * 70)

    data = load_and_preprocess(
        data_dir=base_dir,
        task_type=cfg.TASK_TYPE,
        val_size=cfg.VAL_SIZE,
        seed=cfg.SEED,
        target_u2r=cfg.TARGET_U2R,
        target_r2l=cfg.TARGET_R2L,
        target_normal_cap=cfg.TARGET_NORMAL_CAP,
        target_dos_cap=cfg.TARGET_DOS_CAP,
        resampler=cfg.RESAMPLER,
        k_neighbors=cfg.K_NEIGHBORS,
        undersample=cfg.UNDERSAMPLE,
    )

    class_names = data['class_names']
    num_classes = data['num_classes']
    num_features = data['num_features']

    logger.info(f'Features: {num_features}, Classes: {num_classes}')
    logger.info(f'Class names: {class_names}')
    logger.info(f'Train: {data["train"][0].shape}, Val: {data["val"][0].shape}, '
                f'Test: {data["test"][0].shape}')

    # Save data info
    with open(output_dir / 'data_info.json', 'w', encoding='utf-8') as f:
        json.dump({
            'distributions': data['distributions'],
            'hashes': data['hashes'],
            'num_features': num_features,
            'num_classes': num_classes,
            'class_names': class_names,
            'train_shape': list(data['train'][0].shape),
            'val_shape': list(data['val'][0].shape),
            'test_shape': list(data['test'][0].shape),
        }, f, indent=2)

    # ── Build loaders ──
    loaders = create_loaders(data, cfg, device)

    # ── Model ──
    logger.info('\n' + '=' * 70)
    logger.info('PHASE 2: MODEL SETUP')
    logger.info('=' * 70)

    model = FTTransformer(
        num_features=num_features,
        num_classes=num_classes,
        d_model=cfg.D_MODEL,
        num_heads=cfg.NUM_HEADS,
        num_layers=cfg.NUM_LAYERS,
        d_ff=cfg.D_FF,
        dropout=cfg.DROPOUT,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f'Model: FTTransformer v1')
    logger.info(f'  d_model={cfg.D_MODEL}, heads={cfg.NUM_HEADS}, '
                f'layers={cfg.NUM_LAYERS}, d_ff={cfg.D_FF}')
    logger.info(f'  Dropout: {cfg.DROPOUT}')
    logger.info(f'  Total params: {total_params:,}')

    # ── Loss ──
    alpha = compute_class_balanced_alpha(
        data['train'][1], num_classes, cfg.CLASS_BALANCED_BETA)
    logger.info(f'  Class-balanced alpha: {[round(a, 4) for a in alpha]}')

    if cfg.LABEL_SMOOTHING > 0:
        criterion = LabelSmoothingFocalLoss(
            gamma=cfg.FOCAL_GAMMA, alpha=alpha,
            num_classes=num_classes, smoothing=cfg.LABEL_SMOOTHING)
        logger.info(f'  Loss: LabelSmoothingFocalLoss '
                    f'(γ={cfg.FOCAL_GAMMA}, smoothing={cfg.LABEL_SMOOTHING})')
    else:
        criterion = FocalLoss(gamma=cfg.FOCAL_GAMMA, alpha=alpha,
                              num_classes=num_classes)
        logger.info(f'  Loss: FocalLoss (γ={cfg.FOCAL_GAMMA})')

    # ── Optimizer & Scheduler ──
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.LEARNING_RATE, weight_decay=cfg.WEIGHT_DECAY)
    logger.info(f'  Optimizer: AdamW (lr={cfg.LEARNING_RATE}, wd={cfg.WEIGHT_DECAY})')
    logger.info(f'  Mixup alpha: {cfg.MIXUP_ALPHA}')
    logger.info(f'  Gradient clip: {cfg.GRADIENT_CLIP}')

    if cfg.SCHEDULER == 'cosine':
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=cfg.COSINE_T0, T_mult=cfg.COSINE_T_MULT,
            eta_min=cfg.COSINE_ETA_MIN)
        logger.info(f'  Scheduler: CosineAnnealingWarmRestarts '
                    f'(T0={cfg.COSINE_T0}, Tmult={cfg.COSINE_T_MULT})')
    else:
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='max', factor=0.5, patience=3)
        logger.info(f'  Scheduler: ReduceLROnPlateau')

    # ── Training loop ──
    logger.info('\n' + '=' * 70)
    logger.info(f'PHASE 3: TRAINING ({cfg.NUM_EPOCHS} epochs)')
    logger.info('=' * 70)

    history = {
        'train_loss': [], 'val_loss': [],
        'train_f1': [], 'val_f1': [],
        'gap': [], 'selection_score': [], 'lr': [],
    }

    best_val_f1 = -1.0
    best_selection_score = -1.0
    best_epoch = 0
    patience_counter = 0
    gap_counter = 0

    for epoch in range(1, cfg.NUM_EPOCHS + 1):
        t0 = time.time()

        train_loss, train_f1, train_acc = run_epoch(
            model, loaders['train'], criterion, optimizer, device,
            train=True, mixup_alpha=cfg.MIXUP_ALPHA,
            num_classes=num_classes, grad_clip=cfg.GRADIENT_CLIP)

        val_loss, val_f1, val_acc = run_epoch(
            model, loaders['val'], criterion, optimizer, device,
            train=False, mixup_alpha=0.0,
            num_classes=num_classes, grad_clip=cfg.GRADIENT_CLIP)

        # Scheduler step
        if cfg.SCHEDULER == 'cosine':
            scheduler.step(epoch)
        else:
            scheduler.step(val_f1)

        gap = max(train_f1 - val_f1, 0.0)
        sel_score = val_f1 - cfg.SELECTION_GAP_PENALTY * gap
        lr = optimizer.param_groups[0]['lr']

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_f1'].append(train_f1)
        history['val_f1'].append(val_f1)
        history['gap'].append(gap)
        history['selection_score'].append(sel_score)
        history['lr'].append(lr)

        elapsed = time.time() - t0
        logger.info(
            f'Epoch {epoch:02d}/{cfg.NUM_EPOCHS} '
            f'| train_loss={train_loss:.4f} train_f1={train_f1:.4f} '
            f'| val_loss={val_loss:.4f} val_f1={val_f1:.4f} '
            f'| gap={gap:.4f} sel={sel_score:.4f} '
            f'| lr={lr:.6f} | {elapsed:.1f}s'
        )

        # Overfitting gap check
        if cfg.MAX_TRAIN_VAL_GAP >= 0 and gap > cfg.MAX_TRAIN_VAL_GAP:
            gap_counter += 1
        else:
            gap_counter = 0

        # Best model checkpoint
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': val_f1,
                'selection_score': sel_score,
                'train_val_f1_gap': gap,
                'config': {
                    'num_features': num_features,
                    'num_classes': num_classes,
                    'd_model': cfg.D_MODEL,
                    'num_heads': cfg.NUM_HEADS,
                    'num_layers': cfg.NUM_LAYERS,
                    'd_ff': cfg.D_FF,
                    'dropout': cfg.DROPOUT,
                },
                'class_names': class_names,
                'num_features': num_features,
            }, model_dir / 'best_model.pt')
            logger.info(f'  ✓ New best model saved (val_f1={val_f1:.4f})')
        else:
            patience_counter += 1

        if sel_score > best_selection_score:
            best_selection_score = sel_score

        # Early stopping
        if patience_counter >= cfg.PATIENCE:
            logger.info(f'Early stopping (no improvement for {cfg.PATIENCE} epochs)')
            break

        if gap_counter >= cfg.GAP_PATIENCE:
            logger.info(
                f'Overfitting guard triggered (gap>{cfg.MAX_TRAIN_VAL_GAP} '
                f'for {cfg.GAP_PATIENCE} consecutive epochs)')
            break

    # ── Evaluation ──
    logger.info('\n' + '=' * 70)
    logger.info('PHASE 4: FINAL EVALUATION ON KDDTest+')
    logger.info('=' * 70)

    checkpoint = torch.load(model_dir / 'best_model.pt', map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    logger.info(f'Loaded best model from epoch {checkpoint["epoch"]} '
                f'(val_f1={checkpoint["val_f1"]:.4f})')

    metrics = evaluate_full(model, loaders['test'], class_names, device,
                            results_dir, logger)

    # ── Save plots & summary ──
    plot_history(history, results_dir)

    summary = {
        'run_name': run_name,
        'model': 'FT-Transformer-v1-improved',
        'task_type': cfg.TASK_TYPE,
        'best_epoch': best_epoch,
        'best_val_macro_f1': best_val_f1,
        'best_selection_score': best_selection_score,
        'last_train_val_gap': history['gap'][-1],
        'test_accuracy': metrics['accuracy'],
        'test_macro_f1': metrics['macro_f1'],
        'test_weighted_f1': metrics['weighted_f1'],
        'test_macro_precision': metrics['macro_precision'],
        'test_macro_recall': metrics['macro_recall'],
        'per_class_f1': {
            name: metrics['report_dict'].get(name, {}).get('f1-score', 0)
            for name in class_names
        },
        'config': {
            'epochs': cfg.NUM_EPOCHS,
            'batch_size': cfg.BATCH_SIZE,
            'lr': cfg.LEARNING_RATE,
            'weight_decay': cfg.WEIGHT_DECAY,
            'dropout': cfg.DROPOUT,
            'label_smoothing': cfg.LABEL_SMOOTHING,
            'mixup_alpha': cfg.MIXUP_ALPHA,
            'scheduler': cfg.SCHEDULER,
            'resampler': cfg.RESAMPLER,
            'sampler': cfg.SAMPLER,
            'focal_gamma': cfg.FOCAL_GAMMA,
            'gradient_clip': cfg.GRADIENT_CLIP,
            'target_u2r': cfg.TARGET_U2R,
            'target_r2l': cfg.TARGET_R2L,
            'undersample': cfg.UNDERSAMPLE,
        },
        'data': {
            'distributions': data['distributions'],
            'hashes': data['hashes'],
        },
        'num_features': num_features,
        'num_classes': num_classes,
        'class_names': class_names,
        'total_params': total_params,
    }

    with open(results_dir / 'training_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Also save inference config for deployment
    inference_config = {
        'checkpoint_path': str(model_dir / 'best_model.pt'),
        'class_names': class_names,
        'num_features': num_features,
        'num_classes': num_classes,
        'model_kwargs': {
            'num_features': num_features,
            'num_classes': num_classes,
            'd_model': cfg.D_MODEL,
            'num_heads': cfg.NUM_HEADS,
            'num_layers': cfg.NUM_LAYERS,
            'd_ff': cfg.D_FF,
            'dropout': cfg.DROPOUT,
        },
    }
    with open(model_dir / 'inference_config.json', 'w', encoding='utf-8') as f:
        json.dump(inference_config, f, indent=2)

    # ── Final report ──
    logger.info('\n' + '=' * 70)
    logger.info('TRAINING COMPLETE - SUMMARY')
    logger.info('=' * 70)
    logger.info(f'Run name:          {run_name}')
    logger.info(f'Best epoch:        {best_epoch}')
    logger.info(f'Best val F1:       {best_val_f1:.4f}')
    logger.info(f'Test Macro-F1:     {metrics["macro_f1"]:.4f}')
    logger.info(f'Test Accuracy:     {metrics["accuracy"]:.4f}')
    for cls_name in class_names:
        f1 = metrics['report_dict'].get(cls_name, {}).get('f1-score', 0)
        logger.info(f'  {cls_name:<10} F1: {f1:.4f}')
    logger.info(f'\nArtifacts saved to: {output_dir}')
    logger.info('=' * 70)

    return metrics


if __name__ == '__main__':
    main()
