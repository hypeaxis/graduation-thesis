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
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from tabular_transformer_41emb import FocalLoss, TabularTransformer41Emb


NUMERIC_COLUMNS = [
    'duration', 'src_bytes', 'dst_bytes', 'land', 'wrong_fragment', 'urgent', 'hot',
    'num_failed_logins', 'logged_in', 'num_compromised', 'root_shell', 'su_attempted',
    'num_root', 'num_file_creations', 'num_shells', 'num_access_files', 'num_outbound_cmds',
    'is_host_login', 'is_guest_login', 'count', 'srv_count', 'serror_rate',
    'srv_serror_rate', 'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate',
    'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate',
    'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate', 'dst_host_srv_diff_host_rate',
    'dst_host_serror_rate', 'dst_host_srv_serror_rate', 'dst_host_rerror_rate',
    'dst_host_srv_rerror_rate',
]

CATEGORICAL_COLUMNS = ['protocol_type', 'service', 'flag']


class MixedTabularDataset(Dataset):
    def __init__(self, numeric_features: np.ndarray, categorical_features: np.ndarray, labels: np.ndarray) -> None:
        self.numeric_features = torch.as_tensor(numeric_features, dtype=torch.float32)
        self.categorical_features = torch.as_tensor(categorical_features, dtype=torch.long)
        self.labels = torch.as_tensor(labels, dtype=torch.long)

    def __len__(self) -> int:
        return self.labels.shape[0]

    def __getitem__(self, index: int):
        return self.numeric_features[index], self.categorical_features[index], self.labels[index]


def parse_args():
    parser = ArgumentParser(description='Train Transformer with categorical embeddings on logical 41-feature NSL-KDD data')
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
    parser.add_argument('--seed', type=int, default=42)
    return parser.parse_args()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as file:
        return json.load(file)


def load_datasets(data_dir: Path, val_size: float, seed: int):
    train_path = data_dir / 'cleaned41emb_KddTrain+.csv'
    test_path = data_dir / 'cleaned41emb_KddTest+.csv'
    artifacts_dir = data_dir / 'artifacts_preprocess_41emb'

    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError('Preprocessed 41-feature files are missing. Run DataPreprocrss5ClassTrain_41emb.py and DataPreprocess5ClassTest_41emb.py first.')

    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)

    X_train_numeric = train_df[NUMERIC_COLUMNS].to_numpy(dtype=np.float32)
    X_train_categorical = train_df[CATEGORICAL_COLUMNS].to_numpy(dtype=np.int64)
    y_train = train_df['label'].to_numpy(dtype=np.int64)

    X_test_numeric = test_df[NUMERIC_COLUMNS].to_numpy(dtype=np.float32)
    X_test_categorical = test_df[CATEGORICAL_COLUMNS].to_numpy(dtype=np.int64)
    y_test = test_df['label'].to_numpy(dtype=np.int64)

    indices = np.arange(len(y_train))
    train_indices, val_indices = train_test_split(indices, test_size=val_size, stratify=y_train, random_state=seed)

    label_groups = load_json(artifacts_dir / 'label_groups.json')
    vocabularies = load_json(artifacts_dir / 'categorical_vocabularies.json')
    class_names = [name for _, name in sorted((index, name) for name, index in label_groups.items())]
    categorical_cardinalities = [len(vocabularies[column]) for column in CATEGORICAL_COLUMNS]

    return {
        'train': (X_train_numeric[train_indices], X_train_categorical[train_indices], y_train[train_indices]),
        'val': (X_train_numeric[val_indices], X_train_categorical[val_indices], y_train[val_indices]),
        'test': (X_test_numeric, X_test_categorical, y_test),
        'class_names': class_names,
        'categorical_cardinalities': categorical_cardinalities,
    }


def build_alpha(labels: np.ndarray, num_classes: int) -> list[float]:
    counts = np.bincount(labels, minlength=num_classes).astype(np.float64)
    counts[counts == 0] = 1.0
    weights = counts.sum() / (num_classes * counts)
    weights = weights / weights.mean()
    return weights.tolist()


def create_loaders(dataset_bundle: dict, batch_size: int, device: torch.device):
    pin_memory = device.type == 'cuda'
    return {
        'train': DataLoader(MixedTabularDataset(*dataset_bundle['train']), batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=pin_memory),
        'val': DataLoader(MixedTabularDataset(*dataset_bundle['val']), batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=pin_memory),
        'test': DataLoader(MixedTabularDataset(*dataset_bundle['test']), batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=pin_memory),
    }


def run_epoch(model, loader, criterion, optimizer, device: torch.device, train: bool):
    model.train(mode=train)
    total_loss = 0.0
    predictions = []
    labels_all = []

    context = torch.enable_grad() if train else torch.no_grad()
    with context:
        for x_numeric, x_categorical, labels in tqdm(loader, desc='Train' if train else 'Val', leave=False):
            x_numeric = x_numeric.to(device)
            x_categorical = x_categorical.to(device)
            labels = labels.to(device)

            if train:
                optimizer.zero_grad()

            logits = model(x_numeric, x_categorical)
            loss = criterion(logits, labels)

            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)
            predictions.extend(preds.detach().cpu().tolist())
            labels_all.extend(labels.detach().cpu().tolist())

    avg_loss = total_loss / max(len(loader), 1)
    macro_f1 = f1_score(labels_all, predictions, average='macro', zero_division=0)
    accuracy = accuracy_score(labels_all, predictions)
    return avg_loss, macro_f1, accuracy


def evaluate(model, loader, class_names, device: torch.device, output_dir: Path):
    model.eval()
    predictions = []
    labels_all = []

    with torch.no_grad():
        for x_numeric, x_categorical, labels in tqdm(loader, desc='Test', leave=False):
            logits = model(x_numeric.to(device), x_categorical.to(device))
            preds = torch.argmax(logits, dim=1)
            predictions.extend(preds.cpu().tolist())
            labels_all.extend(labels.cpu().tolist())

    accuracy = accuracy_score(labels_all, predictions)
    macro_f1 = f1_score(labels_all, predictions, average='macro', zero_division=0)
    weighted_f1 = f1_score(labels_all, predictions, average='weighted', zero_division=0)
    macro_precision = precision_score(labels_all, predictions, average='macro', zero_division=0)
    macro_recall = recall_score(labels_all, predictions, average='macro', zero_division=0)
    report_dict = classification_report(labels_all, predictions, target_names=class_names, output_dict=True, zero_division=0)
    report_text = classification_report(labels_all, predictions, target_names=class_names, digits=4, zero_division=0)
    matrix = confusion_matrix(labels_all, predictions)

    pd.DataFrame(report_dict).transpose().to_csv(output_dir / 'per_class_metrics.csv')
    with open(output_dir / 'classification_report.txt', 'w', encoding='utf-8') as file:
        file.write(report_text)

    plt.figure(figsize=(10, 8))
    sns.heatmap(matrix, annot=True, fmt='d', cmap='Blues', xticklabels=class_names, yticklabels=class_names)
    plt.title('NSL-KDD 41-Feature Transformer Confusion Matrix')
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
    }


def plot_history(history, output_dir: Path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    axes[0].plot(history['train_loss'], label='Train Loss', marker='o')
    axes[0].plot(history['val_loss'], label='Val Loss', marker='s')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title('Loss')
    axes[1].plot(history['train_f1'], label='Train Macro-F1', marker='o')
    axes[1].plot(history['val_f1'], label='Val Macro-F1', marker='s')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title('Macro-F1')
    plt.tight_layout()
    plt.savefig(output_dir / 'training_history.png', dpi=300, bbox_inches='tight')
    plt.close(fig)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)

    base_dir = Path(__file__).resolve().parent
    output_dir = base_dir / 'outputs' / 'tabular_transformer_41emb'
    model_dir = output_dir / 'models'
    results_dir = output_dir / 'results'
    model_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')

    dataset_bundle = load_datasets(base_dir, args.val_size, args.seed)
    class_names = dataset_bundle['class_names']
    num_classes = len(class_names)
    loaders = create_loaders(dataset_bundle, args.batch_size, device)
    alpha = build_alpha(dataset_bundle['train'][2], num_classes)

    model = TabularTransformer41Emb(
        num_numeric_features=len(NUMERIC_COLUMNS),
        categorical_cardinalities=dataset_bundle['categorical_cardinalities'],
        num_classes=num_classes,
        d_model=args.d_model,
        num_heads=args.num_heads,
        num_layers=args.num_layers,
        d_ff=args.d_ff,
        dropout=args.dropout,
    ).to(device)

    criterion = FocalLoss(gamma=args.gamma, alpha=alpha, num_classes=num_classes)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=3)

    history = {'train_loss': [], 'val_loss': [], 'train_f1': [], 'val_f1': []}
    best_val_f1 = -1.0
    best_epoch = 0
    patience_counter = 0

    for epoch in range(1, args.epochs + 1):
        start = time.time()
        train_loss, train_f1, train_acc = run_epoch(model, loaders['train'], criterion, optimizer, device, train=True)
        val_loss, val_f1, val_acc = run_epoch(model, loaders['val'], criterion, optimizer, device, train=False)
        scheduler.step(val_f1)

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        history['train_f1'].append(train_f1)
        history['val_f1'].append(val_f1)

        print(
            f'Epoch {epoch:02d}/{args.epochs} '
            f'| train_loss={train_loss:.4f} train_f1={train_f1:.4f} train_acc={train_acc:.4f} '
            f'| val_loss={val_loss:.4f} val_f1={val_f1:.4f} val_acc={val_acc:.4f} '
            f'| lr={optimizer.param_groups[0]["lr"]:.6f} | time={time.time() - start:.1f}s'
        )

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch
            patience_counter = 0
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_f1': val_f1,
                'config': vars(args),
                'class_names': class_names,
                'num_numeric_features': len(NUMERIC_COLUMNS),
                'categorical_columns': CATEGORICAL_COLUMNS,
                'categorical_cardinalities': dataset_bundle['categorical_cardinalities'],
            }, model_dir / 'best_model.pt')
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f'Early stopping triggered at epoch {epoch}')
                break

    checkpoint = torch.load(model_dir / 'best_model.pt', map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    metrics = evaluate(model, loaders['test'], class_names, device, results_dir)
    plot_history(history, results_dir)

    summary = {
        'model': 'TabularTransformer41Emb',
        'best_epoch': best_epoch,
        'best_val_macro_f1': best_val_f1,
        'test_accuracy': metrics['accuracy'],
        'test_macro_f1': metrics['macro_f1'],
        'test_weighted_f1': metrics['weighted_f1'],
        'test_macro_precision': metrics['macro_precision'],
        'test_macro_recall': metrics['macro_recall'],
        'num_numeric_features': len(NUMERIC_COLUMNS),
        'num_categorical_features': len(CATEGORICAL_COLUMNS),
        'total_logical_features': len(NUMERIC_COLUMNS) + len(CATEGORICAL_COLUMNS),
        'class_names': class_names,
        'config': vars(args),
    }

    inference_config = {
        'checkpoint_path': str(model_dir / 'best_model.pt'),
        'class_names': class_names,
        'num_numeric_features': len(NUMERIC_COLUMNS),
        'categorical_columns': CATEGORICAL_COLUMNS,
        'categorical_cardinalities': dataset_bundle['categorical_cardinalities'],
        'model_kwargs': {
            'num_numeric_features': len(NUMERIC_COLUMNS),
            'categorical_cardinalities': dataset_bundle['categorical_cardinalities'],
            'num_classes': num_classes,
            'd_model': args.d_model,
            'num_heads': args.num_heads,
            'num_layers': args.num_layers,
            'd_ff': args.d_ff,
            'dropout': args.dropout,
        },
        'numeric_columns_path': str(base_dir / 'artifacts_preprocess_41emb' / 'numeric_columns.json'),
        'categorical_vocabularies_path': str(base_dir / 'artifacts_preprocess_41emb' / 'categorical_vocabularies.json'),
        'numeric_scaler_path': str(base_dir / 'artifacts_preprocess_41emb' / 'numeric_scaler.pkl'),
        'default_snort_feature_csv': str(base_dir.parent / 'final' / 'snort_features_41emb.csv'),
        'default_prediction_csv': str(base_dir.parent / 'final' / 'snort_tabular_transformer_41emb_predictions.csv'),
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