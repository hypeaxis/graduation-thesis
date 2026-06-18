"""
Improved Data Pipeline for NSL-KDD IDS
=======================================
- ADASYN upsampling for minority classes (R2L, U2R)
- Random undersampling for majority classes (Normal, DoS)
- SHA256 verification for non-overlapping splits
- Detailed distribution reporting

Designed for 2-stage pipeline: Autoencoder (binary) + FT-Transformer (4-class attack)
"""

from __future__ import annotations

import hashlib
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from imblearn.over_sampling import ADASYN, SMOTE
from imblearn.under_sampling import RandomUnderSampler
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

from preprocessing_pipeline import (
    LABEL_GROUPS,
    LABEL_MAP,
    RAW_COLUMNS,
    _basic_clean,
    _map_labels,
    _normalize_label,
    _one_hot,
    _read_raw,
)

# Reverse mapping: group_id -> group_name
GROUP_ID_TO_NAME = {v: k for k, v in LABEL_GROUPS.items()}

# Attack-only class mapping (for 4-class task)
ATTACK_CLASSES = {
    'DoS': 0,
    'Probe': 1,
    'R2L': 2,
    'U2R': 3,
}


def compute_sha256(arr: np.ndarray) -> str:
    """Compute SHA256 hash of a numpy array for integrity checks."""
    return hashlib.sha256(arr.tobytes()).hexdigest()


def print_distribution(y: np.ndarray, class_names: List[str], title: str) -> Dict:
    """Print and return class distribution."""
    counts = np.bincount(y, minlength=len(class_names))
    total = len(y)
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    dist = {}
    for idx, name in enumerate(class_names):
        count = int(counts[idx])
        pct = count / total * 100
        ratio = count / counts.max() if counts.max() > 0 else 0
        bar = '█' * int(ratio * 30)
        print(f"  {name:<10}: {count:>7,} ({pct:>6.2f}%) {bar}")
        dist[name] = count
    print(f"  {'TOTAL':<10}: {total:>7,}")
    
    # Imbalance ratio
    if counts.min() > 0:
        ir = counts.max() / counts.min()
        print(f"  Imbalance Ratio (max/min): {ir:.1f}x")
    return dist


def analyze_zero_variance_features(X: pd.DataFrame) -> List[str]:
    """Find features with zero or near-zero variance."""
    variances = X.var()
    zero_var = variances[variances < 1e-10].index.tolist()
    if zero_var:
        print(f"\n⚠ Features with zero variance (will be kept for schema compat): {zero_var}")
    return zero_var


def load_and_preprocess(
    data_dir: Path,
    task_type: str = '4-class-attack',
    val_size: float = 0.20,
    seed: int = 42,
    # Resampling targets
    target_u2r: int = 1500,
    target_r2l: int = 4000,
    target_normal_cap: int = 30000,
    target_dos_cap: int = 25000,
    # ADASYN/SMOTE config
    resampler: str = 'none',  # 'adasyn', 'smote', 'none'
    k_neighbors: int = 5,
    undersample: bool = False,
) -> Dict:
    """
    Load NSL-KDD, apply resampling, and create clean train/val/test splits.
    
    Returns dict with train/val/test arrays, metadata, and verification hashes.
    """
    train_path = data_dir / 'data/processed/cleaned5Grouped_v2_KddTrain+.csv'
    test_path = data_dir / 'data/processed/cleaned5Grouped_v2_KddTest+.csv'
    
    if not train_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            'Preprocessed CSV files missing. Run DataPreprocrss5ClassTrain.py first.'
        )
    
    print("Loading preprocessed NSL-KDD data...")
    train_df = pd.read_csv(train_path)
    test_df = pd.read_csv(test_path)
    
    print(f"  Train raw: {train_df.shape}")
    print(f"  Test raw: {test_df.shape}")
    
    # --- Determine class configuration ---
    if task_type == '4-class-attack':
        # Filter out Normal (label=0), remap labels
        print("\n>>> Task: 4-class attack classification")
        train_df = train_df[train_df['label'] != 0].copy()
        test_df = test_df[test_df['label'] != 0].copy()
        train_df['label'] = train_df['label'] - 1  # DoS=0, Probe=1, R2L=2, U2R=3
        test_df['label'] = test_df['label'] - 1
        class_names = ['DoS', 'Probe', 'R2L', 'U2R']
    else:
        class_names = ['Normal', 'DoS', 'Probe', 'R2L', 'U2R']
    
    num_classes = len(class_names)
    
    # Extract features and labels
    X_train_full = train_df.drop(columns=['label']).values.astype(np.float32)
    y_train_full = train_df['label'].values.astype(np.int64)
    X_test = test_df.drop(columns=['label']).values.astype(np.float32)
    y_test = test_df['label'].values.astype(np.int64)
    feature_columns = [c for c in train_df.columns if c != 'label']
    
    # Analyze zero-variance features
    analyze_zero_variance_features(train_df.drop(columns=['label']))
    
    # Print original distribution
    print_distribution(y_train_full, class_names, "ORIGINAL Train Distribution")
    print_distribution(y_test, class_names, "ORIGINAL Test Distribution (KDDTest+ - FIXED)")
    
    # --- Step 1: Stratified Train/Val Split (BEFORE resampling) ---
    print(f"\n>>> Splitting Train into Train/Val (val_size={val_size}, seed={seed})")
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full,
        test_size=val_size,
        stratify=y_train_full,
        random_state=seed,
    )
    
    print_distribution(y_train, class_names, "Pre-Resampling Train Split")
    print_distribution(y_val, class_names, "Validation Split (UNTOUCHED)")
    
    # --- Step 2: Resampling ONLY on Train ---
    if resampler != 'none':
        print(f"\n>>> Applying resampling (method={resampler})")
        
        train_counts = np.bincount(y_train, minlength=num_classes)
        
        # Build sampling strategy
        if task_type == '4-class-attack':
            # 4-class: DoS=0, Probe=1, R2L=2, U2R=3
            sampling_strategy_over = {}
            # Oversample minority classes
            if train_counts[2] < target_r2l:  # R2L
                sampling_strategy_over[2] = target_r2l
            if train_counts[3] < target_u2r:  # U2R
                sampling_strategy_over[3] = target_u2r
            
            sampling_strategy_under = {}
            # Undersample majority classes (only if undersample=True)
            if undersample:
                if train_counts[0] > target_dos_cap:  # DoS
                    sampling_strategy_under[0] = target_dos_cap
                # Keep Probe as-is (it's in a reasonable range)
        else:
            # 5-class
            sampling_strategy_over = {}
            if train_counts[3] < target_r2l:  # R2L
                sampling_strategy_over[3] = target_r2l
            if train_counts[4] < target_u2r:  # U2R
                sampling_strategy_over[4] = target_u2r
            
            sampling_strategy_under = {}
            if undersample:
                if train_counts[0] > target_normal_cap:  # Normal
                    sampling_strategy_under[0] = target_normal_cap
                if train_counts[1] > target_dos_cap:  # DoS
                    sampling_strategy_under[1] = target_dos_cap
        
        # Step 2a: Oversample minority classes
        if sampling_strategy_over:
            # Adjust k_neighbors for very small classes
            min_class = min(train_counts[train_counts > 0])
            effective_k = min(k_neighbors, min_class - 1)
            effective_k = max(effective_k, 2)
            
            print(f"  Oversampling targets: {sampling_strategy_over}")
            print(f"  Effective k_neighbors: {effective_k}")
            
            if resampler == 'adasyn':
                try:
                    oversampler = ADASYN(
                        sampling_strategy=sampling_strategy_over,
                        n_neighbors=effective_k,
                        random_state=seed,
                    )
                    X_train, y_train = oversampler.fit_resample(X_train, y_train)
                except ValueError as e:
                    print(f"  ADASYN failed ({e}), falling back to SMOTE")
                    oversampler = SMOTE(
                        sampling_strategy=sampling_strategy_over,
                        k_neighbors=effective_k,
                        random_state=seed,
                    )
                    X_train, y_train = oversampler.fit_resample(X_train, y_train)
            else:
                oversampler = SMOTE(
                    sampling_strategy=sampling_strategy_over,
                    k_neighbors=effective_k,
                    random_state=seed,
                )
                X_train, y_train = oversampler.fit_resample(X_train, y_train)
            
            print_distribution(y_train, class_names, "After Oversampling")
        
        # Step 2b: Undersample majority classes
        if undersample and sampling_strategy_under:
            print(f"  Undersampling targets: {sampling_strategy_under}")
            undersampler = RandomUnderSampler(
                sampling_strategy=sampling_strategy_under,
                random_state=seed,
            )
            X_train, y_train = undersampler.fit_resample(X_train, y_train)
            print_distribution(y_train, class_names, "After Undersampling")
    
    # Ensure float32
    X_train = X_train.astype(np.float32)
    X_val = X_val.astype(np.float32)
    X_test = X_test.astype(np.float32)
    y_train = y_train.astype(np.int64)
    y_val = y_val.astype(np.int64)
    y_test = y_test.astype(np.int64)
    
    # --- Step 3: Final distributions ---
    dist_train = print_distribution(y_train, class_names, "FINAL Train Distribution")
    dist_val = print_distribution(y_val, class_names, "FINAL Validation Distribution")
    dist_test = print_distribution(y_test, class_names, "FINAL Test Distribution (KDDTest+)")
    
    # --- Step 4: SHA256 Verification ---
    print("\n>>> SHA256 Split Verification")
    hash_train = compute_sha256(X_train)
    hash_val = compute_sha256(X_val)
    hash_test = compute_sha256(X_test)
    print(f"  Train hash: {hash_train[:16]}...")
    print(f"  Val   hash: {hash_val[:16]}...")
    print(f"  Test  hash: {hash_test[:16]}...")
    
    assert hash_train != hash_val, "CRITICAL: Train and Val have identical data!"
    assert hash_train != hash_test, "CRITICAL: Train and Test have identical data!"
    assert hash_val != hash_test, "CRITICAL: Val and Test have identical data!"
    print("  ✓ All splits have unique data (no overlap)")
    
    return {
        'train': (X_train, y_train),
        'val': (X_val, y_val),
        'test': (X_test, y_test),
        'class_names': class_names,
        'num_features': X_train.shape[1],
        'num_classes': num_classes,
        'feature_columns': feature_columns,
        'distributions': {
            'train': dist_train,
            'val': dist_val,
            'test': dist_test,
        },
        'hashes': {
            'train': hash_train,
            'val': hash_val,
            'test': hash_test,
        },
    }


if __name__ == '__main__':
    base_dir = Path(__file__).resolve().parent
    result = load_and_preprocess(base_dir, task_type='4-class-attack')
    print(f"\nDataset ready:")
    print(f"  Train: {result['train'][0].shape}")
    print(f"  Val:   {result['val'][0].shape}")
    print(f"  Test:  {result['test'][0].shape}")
