from __future__ import annotations

import json
import random
import time
from argparse import ArgumentParser
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from tqdm import tqdm

from phase2_ft_transformer import FTTransformer, FTTransformerV2, FocalLoss, LabelSmoothingFocalLoss


class TabularDataset(Dataset):
    def __init__(self, features: np.ndarray, labels: np.ndarray) -> None:
        self.features = torch.as_tensor(features, dtype=torch.float32)
        self.labels = torch.as_tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return self.labels.shape[0]

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.features[index], self.labels[index]


def parse_args() -> ArgumentParser:
    parser = ArgumentParser(description='Train FT-Transformer on NSL-KDD 5-class data')
    parser.add_argument('--epochs', type=int, default=40)
    parser.add_argument('--batch-size', type=int, default=256)
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--weight-decay', type=float, default=1e-4)
    parser.add_argument('--patience', type=int, default=8)
    parser.add_argument('--val-size', type=float, default=0.15)
    parser.add_argument('--d-model', type=int, default=128)
    parser.add_argument('--num-heads', type=int, default=8)
    parser.add_argument('--num-layers', type=int, default=4)
    parser.add_argument('--d-ff', type=int, default=512)
    parser.add_argument('--dropout', type=float, default=0.1)
    parser.add_argument('--gamma', type=float, default=2.0)
    parser.add_argument(
        '--focal-alpha',
        type=str,
        default='class-balanced',
        help='Scalar alpha, comma-separated per-class alpha list, or class-balanced.',
    )
    parser.add_argument('--class-balanced-beta', type=float, default=0.9999)
    parser.add_argument('--sampler', choices=['none', 'weighted'], default='weighted')
    parser.add_argument('--mixup-alpha', type=float, default=0.0, help='Beta(alpha, alpha) mixup strength. Set 0 to disable.')
    parser.add_argument(
        '--selection-gap-penalty',
        type=float,
        default=0.25,
        help='Penalty applied on (train_f1 - val_f1) when selecting the best checkpoint.',
    )
    parser.add_argument(
        '--max-train-val-gap',
        type=float,
        default=0.20,
        help='If train_f1 - val_f1 is above this for consecutive epochs, stop early. Set <0 to disable.',
    )
    parser.add_argument('--gap-patience', type=int, default=3, help='Consecutive epochs allowed above max-train-val-gap before early stop.')
    # --- v2 improvements ---
    parser.add_argument('--model-version', choices=['v1', 'v2'], default='v1', help='v1=original FTTransformer, v2=grouped embedding + deeper head')
    parser.add_argument('--label-smoothing', type=float, default=0.0, help='Label smoothing factor for focal loss. 0=disabled.')
    parser.add_argument('--scheduler', choices=['plateau', 'cosine'], default='plateau', help='LR scheduler type.')
    parser.add_argument('--smote-strategy', choices=['none', 'minority', 'auto', 'custom'], default='none', help='SMOTE oversampling strategy for minority classes.')
    parser.add_argument('--smote-k', type=int, default=5, help='k-neighbors for SMOTE.')
    parser.add_argument('--num-workers', type=int, default=0)
    parser.add_argument('--save-dir', type=str, default=None)
    parser.add_argument('--results-dir', type=str, default=None)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--use-selected-features', action='store_true', help='Use top features from selected_features.json')
    parser.add_argument('--task-type', choices=['5-class', '4-class-attack'], default='5-class', help='Task type for FT-Transformer')
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_class_names(artifacts_dir: Path) -> list[str]:
    label_groups_path = artifacts_dir / 'label_groups.json'
    if not label_groups_path.exists():
        return ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']

    with open(label_groups_path, 'r', encoding='utf-8') as file:
        label_groups = json.load(file)

    indexed = sorted(((int(index), name) for name, index in label_groups.items()), key=lambda item: item[0])
    return [name for _, name in indexed]


def apply_smote(X: np.ndarray, y: np.ndarray, strategy: str, k_neighbors: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Apply SMOTE oversampling to minority classes."""
    if strategy == 'none':
        return X, y

    from imblearn.over_sampling import SMOTE

    class_counts = np.bincount(y)
    print(f'  Pre-SMOTE class distribution: {dict(enumerate(class_counts.tolist()))}')

    if strategy == 'custom':
        # Custom: boost R2L to ~5000, U2R to ~1000, leave others unchanged
        sampling_strategy = {}
        for cls_idx, count in enumerate(class_counts):
            if cls_idx == 3:  # R2L
                sampling_strategy[cls_idx] = max(count, 5000)
            elif cls_idx == 4:  # U2R
                sampling_strategy[cls_idx] = max(count, 1000)
        if not sampling_strategy:
            return X, y
    elif strategy == 'auto':
        sampling_strategy = 'auto'
    elif strategy == 'minority':
        sampling_strategy = 'minority'
    else:
        return X, y

    # Adjust k_neighbors if any class has fewer samples
    min_class_count = class_counts[class_counts > 0].min()
    effective_k = min(k_neighbors, min_class_count - 1)
    effective_k = max(effective_k, 1)

    smote = SMOTE(
        sampling_strategy=sampling_strategy,
        k_neighbors=effective_k,
        random_state=seed,
    )
    X_resampled, y_resampled = smote.fit_resample(X, y)

    new_counts = np.bincount(y_resampled)
    print(f'  Post-SMOTE class distribution: {dict(enumerate(new_counts.tolist()))}')
    print(f'  Samples added: {len(y_resampled) - len(y)}')

    return X_resampled.astype(np.float32), y_resampled.astype(np.int64)


def load_datasets(data_dir: Path, val_size: float, seed: int, smote_strategy: str = 'none', smote_k: int = 5, use_selected_features: bool = False, task_type: str = '5-class'):
    train_path = data_dir / 'data/processed/cleaned5Grouped_v2_KddTrain+.csv'
    test_path = data_dir / 'data/processed/cleaned5Grouped_v2_KddTest+.csv'
    artifacts_dir = data_dir / 'models'

    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError('Preprocessed NSL-KDD CSV files are missing. Run DataPreprocrss5ClassTrain.py and DataPreprocess5ClassTest.py first.')

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    if task_type == '4-class-attack':
        print("Task Type is 4-class-attack: Filtering out Normal traffic (label 0)")
        train_df = train_df[train_df['label'] != 0].copy()
        test_df = test_df[test_df['label'] != 0].copy()
        train_df['label'] = train_df['label'] - 1
        test_df['label'] = test_df['label'] - 1

    if use_selected_features:
        selected_features_path = artifacts_dir / 'selected_features.json'
        with open(selected_features_path, 'r', encoding='utf-8') as f:
            selected_features = json.load(f)
        print(f"Using {len(selected_features)} selected features out of 122.")
        train_df = train_df[selected_features + ['label']]
        test_df = test_df[selected_features + ['label']]

    X_train_full = train_df.drop(columns=['label']).to_numpy(dtype=np.float32)
    y_train_full = train_df['label'].to_numpy(dtype=np.int64)
    X_test = test_df.drop(columns=['label']).to_numpy(dtype=np.float32)
    y_test = test_df['label'].to_numpy(dtype=np.int64)

    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full,
        y_train_full,
        test_size=val_size,
        stratify=y_train_full,
        random_state=seed,
    )

    # Apply SMOTE on train set only (never on val/test)
    if smote_strategy != 'none':
        print(f'Applying SMOTE (strategy={smote_strategy}, k={smote_k}) ...')
        X_train, y_train = apply_smote(X_train, y_train, smote_strategy, smote_k, seed)

    class_names = load_class_names(artifacts_dir)
    if task_type == '4-class-attack':
        class_names = ['DoS', 'Probe', 'R2L', 'U2R']

    return {
        'train': (X_train, y_train),
        'val': (X_val, y_val),
        'test': (X_test, y_test),
        'class_names': class_names,
        'num_features': X_train.shape[1],
        'num_classes': len(class_names),
    }


def build_train_sampler(train_targets: np.ndarray, strategy: str, seed: int):
    if strategy == 'none':
        return None
    if strategy != 'weighted':
        raise ValueError(f'Unsupported sampler strategy: {strategy}')

    class_counts = np.bincount(train_targets)
    class_weights = np.zeros_like(class_counts, dtype=np.float64)
    nonzero_mask = class_counts > 0
    class_weights[nonzero_mask] = 1.0 / class_counts[nonzero_mask]
    sample_weights = class_weights[train_targets]

    generator = torch.Generator()
    generator.manual_seed(seed)
    return WeightedRandomSampler(
        weights=torch.as_tensor(sample_weights, dtype=torch.double),
        num_samples=len(sample_weights),
        replacement=True,
        generator=generator,
    )


def resolve_focal_alpha(alpha_arg: str, train_targets: np.ndarray, num_classes: int, beta: float):
    alpha_arg = str(alpha_arg).strip()

    if alpha_arg.lower() == 'class-balanced':
        class_counts = np.bincount(train_targets, minlength=num_classes).astype(np.float64)
        effective_num = np.ones_like(class_counts)
        nonzero_mask = class_counts > 0
        effective_num[nonzero_mask] = 1.0 - np.power(beta, class_counts[nonzero_mask])

        alpha = np.zeros_like(class_counts, dtype=np.float64)
        alpha[nonzero_mask] = (1.0 - beta) / np.clip(effective_num[nonzero_mask], 1e-12, None)
        alpha[nonzero_mask] = alpha[nonzero_mask] / alpha[nonzero_mask].sum() * nonzero_mask.sum()
        return alpha.astype(np.float32).tolist(), 'class-balanced'

    if ',' in alpha_arg:
        values = [float(item.strip()) for item in alpha_arg.split(',') if item.strip()]
        if len(values) != num_classes:
            raise ValueError(f'Expected {num_classes} alpha values, got {len(values)}')
        return values, 'per-class'

    return float(alpha_arg), 'scalar'


def create_loaders(dataset_bundle: dict, batch_size: int, device: torch.device, sampler_strategy: str, seed: int, num_workers: int):
    pin_memory = device.type == 'cuda'
    train_dataset = TabularDataset(*dataset_bundle['train'])
    val_dataset = TabularDataset(*dataset_bundle['val'])
    test_dataset = TabularDataset(*dataset_bundle['test'])

    train_sampler = build_train_sampler(dataset_bundle['train'][1], sampler_strategy, seed)

    return {
        'train': DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=train_sampler is None,
            sampler=train_sampler,
            num_workers=num_workers,
            pin_memory=pin_memory,
        ),
        'val': DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=pin_memory),
        'test': DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=pin_memory),
    }


def _mixup_batch(features: torch.Tensor, labels: torch.Tensor, alpha: float) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    if alpha <= 0.0:
        return features, labels, labels, 1.0

    lam = float(np.random.beta(alpha, alpha))
    indices = torch.randperm(features.size(0), device=features.device)
    mixed_features = lam * features + (1.0 - lam) * features[indices]
    labels_a = labels
    labels_b = labels[indices]
    return mixed_features, labels_a, labels_b, lam


def _soft_focal_loss(logits: torch.Tensor, soft_targets: torch.Tensor, criterion: FocalLoss) -> torch.Tensor:
    log_probs = torch.log_softmax(logits, dim=1)
    probs = log_probs.exp()

    pt = (soft_targets * probs).sum(dim=1).clamp(min=1e-8, max=1.0)
    log_pt = (soft_targets * log_probs).sum(dim=1)

    alpha = criterion.alpha.to(logits.device)
    alpha_t = (soft_targets * alpha.unsqueeze(0)).sum(dim=1)
    loss = -alpha_t * torch.pow(1.0 - pt, criterion.gamma) * log_pt
    return loss.mean()


def run_epoch(model, loader, criterion, optimizer, device: torch.device, train: bool, mixup_alpha: float, num_classes: int):
    model.train(mode=train)
    total_loss = 0.0
    all_preds: list[int] = []
    all_labels: list[int] = []
    desc = 'Train' if train else 'Val'

    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for features, labels in tqdm(loader, desc=desc, leave=False):
            features = features.to(device)
            labels = labels.to(device)
            labels_for_metrics = labels

            if train:
                optimizer.zero_grad()
                if mixup_alpha > 0.0:
                    features, labels_a, labels_b, lam = _mixup_batch(features, labels, mixup_alpha)

            logits = model(features)
            if train and mixup_alpha > 0.0:
                targets_a = torch.nn.functional.one_hot(labels_a, num_classes=num_classes).float()
                targets_b = torch.nn.functional.one_hot(labels_b, num_classes=num_classes).float()
                soft_targets = lam * targets_a + (1.0 - lam) * targets_b
                loss = _soft_focal_loss(logits, soft_targets, criterion)
            else:
                loss = criterion(logits, labels)

            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.detach().cpu().tolist())
            all_labels.extend(labels_for_metrics.detach().cpu().tolist())

    avg_loss = total_loss / max(len(loader), 1)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    accuracy = accuracy_score(all_labels, all_preds)
    return avg_loss, macro_f1, accuracy


def evaluate(model, loader, class_names: list[str], device: torch.device, output_dir: Path) -> dict:
    model.eval()
    all_preds: list[int] = []
    all_labels: list[int] = []

    with torch.no_grad():
        for features, labels in tqdm(loader, desc='Test', leave=False):
            logits = model(features.to(device))
            preds = torch.argmax(logits, dim=1)
            all_preds.extend(preds.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    accuracy = accuracy_score(all_labels, all_preds)
    macro_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=0)
    weighted_f1 = f1_score(all_labels, all_preds, average='weighted', zero_division=0)
    macro_precision = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    macro_recall = recall_score(all_labels, all_preds, average='macro', zero_division=0)
    report_dict = classification_report(
        all_labels,
        all_preds,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    report_text = classification_report(
        all_labels,
        all_preds,
        target_names=class_names,
        digits=4,
        zero_division=0,
    )
    matrix = confusion_matrix(all_labels, all_preds)

    pd.DataFrame(report_dict).transpose().to_csv(output_dir / 'per_class_metrics.csv')
    with open(output_dir / 'classification_report.txt', 'w', encoding='utf-8') as file:
        file.write(report_text)

    plt.figure(figsize=(10, 8))
    sns.heatmap(matrix, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)
    plt.title('NSL-KDD FT-Transformer Confusion Matrix')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.tight_layout()
    plt.savefig(output_dir / 'confusion_matrix.png', dpi=300, bbox_inches='tight')
    plt.close()

    return {
        'accuracy': accuracy,
        'macro_f1': macro_f1,
        'weighted_f1': weighted_f1,
        'macro_precision': macro_precision,
        'macro_recall': macro_recall,
        'report_dict': report_dict,
        'report_text': report_text,
    }


def plot_history(history: dict[str, list[float]], output_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(history['train_loss'], label='Train Loss', marker='o')
    axes[0].plot(history['val_loss'], label='Val Loss', marker='s')
    axes[0].set_title('Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(history['train_f1'], label='Train Macro-F1', marker='o')
    axes[1].plot(history['val_f1'], label='Val Macro-F1', marker='s')
    axes[1].set_title('Macro-F1')
    axes[1].set_xlabel('Epoch')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'training_history.png', dpi=300, bbox_inches='tight')
    plt.close(fig)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    base_dir = Path(__file__).resolve().parent
    default_output_dir = base_dir / 'models/weights' / 'ft_transformer_nslkdd'
    model_dir = Path(args.save_dir) if args.save_dir else default_output_dir / 'models'
    results_dir = Path(args.results_dir) if args.results_dir else default_output_dir / 'results'
    output_dir = model_dir.parent
    model_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')

    dataset_bundle = load_datasets(base_dir, args.val_size, args.seed, args.smote_strategy, args.smote_k, args.use_selected_features, args.task_type)
    loaders = create_loaders(
        dataset_bundle,
        args.batch_size,
        device,
        args.sampler,
        args.seed,
        args.num_workers,
    )
    class_names = dataset_bundle['class_names']
    num_classes = dataset_bundle['num_classes']
    num_features = dataset_bundle['num_features']

    alpha, focal_alpha_mode = resolve_focal_alpha(
        args.focal_alpha,
        dataset_bundle['train'][1],
        num_classes,
        args.class_balanced_beta,
    )

    # Model version selection
    if args.model_version == 'v2':
        model = FTTransformerV2(
            num_features=num_features,
            num_classes=num_classes,
            d_model=args.d_model,
            num_heads=args.num_heads,
            num_layers=args.num_layers,
            d_ff=args.d_ff,
            dropout=args.dropout,
            use_grouped_embedding=True,
        ).to(device)
    else:
        model = FTTransformer(
            num_features=num_features,
            num_classes=num_classes,
            d_model=args.d_model,
            num_heads=args.num_heads,
            num_layers=args.num_layers,
            d_ff=args.d_ff,
            dropout=args.dropout,
        ).to(device)

    # Loss function selection
    if args.label_smoothing > 0.0:
        criterion = LabelSmoothingFocalLoss(
            gamma=args.gamma, alpha=alpha, num_classes=num_classes, smoothing=args.label_smoothing,
        )
    else:
        criterion = FocalLoss(gamma=args.gamma, alpha=alpha, num_classes=num_classes)

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)

    # Scheduler selection
    if args.scheduler == 'cosine':
        scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer, T_0=max(args.epochs // 3, 5), T_mult=1, eta_min=args.lr * 0.01,
        )
    else:
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=3)

    history = {
        'train_loss': [],
        'val_loss': [],
        'train_f1': [],
        'val_f1': [],
        'train_val_f1_gap': [],
        'selection_score': [],
    }

    best_val_f1 = -1.0
    best_selection_score = -1.0
    best_epoch = 0
    patience_counter = 0
    gap_counter = 0

    print(f'Using device: {device}')
    print(f'Model version: {args.model_version}')
    print(f'Num features: {num_features}, Num classes: {num_classes}')
    print(f'Class names: {class_names}')
    print(f'Focal alpha mode: {focal_alpha_mode}')
    if isinstance(alpha, list):
        print(f'Focal alpha: {[round(value, 4) for value in alpha]}')
    else:
        print(f'Focal alpha: {alpha}')
    print(f'Label smoothing: {args.label_smoothing}')
    print(f'Sampler: {args.sampler}')
    print(f'SMOTE strategy: {args.smote_strategy}')
    print(f'Scheduler: {args.scheduler}')
    print(f'Mixup alpha: {args.mixup_alpha}')
    print(f'Selection gap penalty: {args.selection_gap_penalty}')
    print(f'Max train-val gap: {args.max_train_val_gap} (patience={args.gap_patience})')
    print(f'Total params: {sum(p.numel() for p in model.parameters()):,}')
    print(f'Train/Val/Test sizes: {len(dataset_bundle["train"][1])}/{len(dataset_bundle["val"][1])}/{len(dataset_bundle["test"][1])}')

    for epoch in range(1, args.epochs + 1):
        start = time.time()
        train_loss, train_f1, train_acc = run_epoch(
            model,
            loaders['train'],
            criterion,
            optimizer,
            device,
            train=True,
            mixup_alpha=args.mixup_alpha,
            num_classes=num_classes,
        )
        val_loss, val_f1, val_acc = run_epoch(
            model,
            loaders['val'],
            criterion,
            optimizer,
            device,
            train=False,
            mixup_alpha=0.0,
            num_classes=num_classes,
        )
        if args.scheduler == 'cosine':
            scheduler.step(epoch)
        else:
            scheduler.step(val_f1)

        train_val_gap = max(train_f1 - val_f1, 0.0)
        selection_score = val_f1 - args.selection_gap_penalty * train_val_gap

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_f1'].append(train_f1)
        history['val_f1'].append(val_f1)
        history['train_val_f1_gap'].append(train_val_gap)
        history['selection_score'].append(selection_score)

        print(
            f'Epoch {epoch:02d}/{args.epochs} '
            f'| train_loss={train_loss:.4f} train_f1={train_f1:.4f} train_acc={train_acc:.4f} '
            f'| val_loss={val_loss:.4f} val_f1={val_f1:.4f} val_acc={val_acc:.4f} '
            f'| gap={train_val_gap:.4f} sel_score={selection_score:.4f} '
            f'| lr={optimizer.param_groups[0]["lr"]:.6f} | time={time.time() - start:.1f}s'
        )

        if args.max_train_val_gap >= 0.0 and train_val_gap > args.max_train_val_gap:
            gap_counter += 1
        else:
            gap_counter = 0

        if selection_score > best_selection_score:
            best_selection_score = selection_score

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            patience_counter = 0
            torch.save(
                {
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'val_f1': val_f1,
                    'selection_score': selection_score,
                    'train_val_f1_gap': train_val_gap,
                    'config': vars(args),
                    'class_names': class_names,
                    'num_features': num_features,
                },
                model_dir / 'best_model.pt',
            )
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f'Early stopping triggered at epoch {epoch}')
                break

        if gap_counter >= args.gap_patience:
            print(
                f'Early stopping by overfitting guard at epoch {epoch} '
                f'(train-val gap > {args.max_train_val_gap} for {args.gap_patience} epochs)'
            )
            break

    checkpoint = torch.load(model_dir / 'best_model.pt', map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])

    metrics = evaluate(model, loaders['test'], class_names, device, results_dir)
    plot_history(history, results_dir)

    summary = {
        'model': f'FT-Transformer-{args.model_version}',
        'model_version': args.model_version,
        'best_epoch': best_epoch,
        'best_val_macro_f1': best_val_f1,
        'best_selection_score': best_selection_score,
        'last_train_val_f1_gap': history['train_val_f1_gap'][-1] if history['train_val_f1_gap'] else None,
        'test_accuracy': metrics['accuracy'],
        'test_macro_f1': metrics['macro_f1'],
        'test_weighted_f1': metrics['weighted_f1'],
        'test_macro_precision': metrics['macro_precision'],
        'test_macro_recall': metrics['macro_recall'],
        'focal_alpha_mode': focal_alpha_mode,
        'label_smoothing': args.label_smoothing,
        'smote_strategy': args.smote_strategy,
        'scheduler': args.scheduler,
        'task_type': args.task_type,
        'num_features': num_features,
        'num_classes': num_classes,
        'total_params': sum(parameter.numel() for parameter in model.parameters()),
        'trainable_params': sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad),
        'class_names': class_names,
        'config': vars(args),
    }

    inference_config = {
        'checkpoint_path': str(model_dir / 'best_model.pt'),
        'class_names': class_names,
        'num_features': num_features,
        'num_classes': num_classes,
        'model_kwargs': {
            'num_features': num_features,
            'num_classes': num_classes,
            'd_model': args.d_model,
            'num_heads': args.num_heads,
            'num_layers': args.num_layers,
            'd_ff': args.d_ff,
            'dropout': args.dropout,
        },
        'feature_columns_path': str(base_dir / 'models' / 'selected_features.json') if args.use_selected_features else str(base_dir / 'models' / 'feature_columns.json'),
        'default_snort_feature_csv': str(base_dir.parent / 'final' / 'snort_features_122.csv'),
        'default_snort_prediction_csv': str(base_dir.parent / 'final' / 'snort_ft_transformer_predictions.csv'),
    }

    with open(results_dir / 'training_summary.json', 'w', encoding='utf-8') as file:
        json.dump(summary, file, ensure_ascii=True, indent=2)

    with open(model_dir / 'inference_config.json', 'w', encoding='utf-8') as file:
        json.dump(inference_config, file, ensure_ascii=True, indent=2)

    pd.DataFrame([summary]).drop(columns=['class_names', 'config']).to_csv(results_dir / 'training_summary.csv', index=False)

    print('\nTraining complete')
    print(f'Best validation Macro-F1: {best_val_f1:.4f} at epoch {best_epoch}')
    print(f'Test Macro-F1: {metrics["macro_f1"]:.4f}')
    print(f'Artifacts saved to: {output_dir}')


if __name__ == '__main__':
    main()