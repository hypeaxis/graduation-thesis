# Kiến trúc hệ thống NSL-KDD

> Tổng hợp pipeline dữ liệu, mô hình, và inference của module phát hiện xâm nhập dựa trên NSL-KDD.

---

## 1. Data Pipeline

**File:** `src/data_processing/preprocessing_pipeline.py`

### Luồng xử lý

```
KDDTrain+.txt / KDDTest+.txt (41 raw features)
    ↓
[Clean] dropna, drop_duplicates, lọc duration ≥ 0
    ↓
[Label Mapping] 39 attack types → 5 nhóm
    ↓
[One-hot Encode] protocol_type, service, flag
    ↓
[MinMaxScaler] fit trên train, transform trên test
    ↓
122 features (CSV)
```

### Label Mapping

| Nhóm | ID | Các attack types |
|------|----|-----------------|
| Normal | 0 | normal |
| DoS | 1 | back, land, neptune, pod, smurf, teardrop, apache2, udpstorm, processtable, mailbomb |
| Probe | 2 | ipsweep, nmap, portsweep, satan, mscan, saint |
| R2L | 3 | ftp_write, guess_passwd, imap, multihop, phf, spy, warezclient, warezmaster, sendmail, named, snmpgetattack, snmpguess, xlock, xsnoop, httptunnel |
| U2R | 4 | buffer_overflow, loadmodule, perl, rootkit, ps, sqlattack, xterm |

### Layout 122 features

| Indices | Nhóm | Số chiều |
|---------|------|---------|
| 0 – 37 | Numeric features | 38 |
| 38 – 40 | protocol_type (one-hot) | 3 |
| 41 – 110 | service (one-hot) | 70 |
| 111 – 121 | flag (one-hot) | 11 |
| **Tổng** | | **122** |

### Artifacts xuất ra

| File | Mô tả |
|------|-------|
| `feature_columns.json` | Danh sách 122 feature theo thứ tự |
| `scaler.pkl` | MinMaxScaler đã fit trên train |
| `label_groups.json` | Mapping tên nhóm → ID số |
| `label_map.json` | Mapping attack name → tên nhóm |
| `train_stats.json` / `test_stats.json` | Thống kê sau xử lý |

---

## 2. Model Architecture

**File:** `src/models/phase2_ft_transformer.py`

### FTTransformer v1 (Production)

```
Input: (batch, 122)
    ↓
FeatureEmbedding
  122 × Linear(1 → 128) + CLS token
  Output: (batch, 123, 128)     ← attention matrix 123×123
    ↓
4 × TransformerBlock
  MultiHeadSelfAttention (8 heads, d_k=16)
  FFN: Linear(128→512) → GELU → Dropout → Linear(512→128)
  Pre-LN: LayerNorm trước attention và FFN
  Residual connection + Dropout(0.1)
    ↓
LayerNorm
    ↓
CLS token pooling → (batch, 128)
    ↓
Classifier Head
  Linear(128→128) → GELU → Dropout(0.1) → Linear(128→4)
    ↓
Output: logits (batch, 4)   [DoS, Probe, R2L, U2R]
```

**Hyperparameters mặc định:**

| Param | Giá trị |
|-------|---------|
| d_model | 128 |
| num_heads | 8 |
| num_layers | 4 |
| d_ff | 512 |
| dropout | 0.1 |
| num_features | 122 |
| num_classes | 4 |

---

### FTTransformerV2 (Experimental)

Cải tiến so với v1:

| Điểm | v1 | v2 |
|------|----|----|
| Embedding | 122 token riêng lẻ | 4 group token (attention 5×5) |
| d_model | 128 | 192 |
| Classifier | 2-layer linear | 3-layer + BatchNorm |
| Params | Nhiều hơn | Ít hơn (attention nhỏ hơn) |

```
Input: (batch, 122)
    ↓
FeatureGroupEmbedding
  Group 1 "numeric":  Linear(38→192) → LayerNorm → GELU
  Group 2 "protocol": Linear(3→192)  → LayerNorm → GELU
  Group 3 "service":  Linear(70→192) → LayerNorm → GELU
  Group 4 "flag":     Linear(11→192) → LayerNorm → GELU
  + CLS token
  Output: (batch, 5, 192)       ← attention matrix 5×5
    ↓
4 × TransformerBlock (d_model=192, 8 heads, d_ff=512)
    ↓
LayerNorm → CLS token pooling → (batch, 192)
    ↓
Classifier Head (deeper)
  Linear(192→192) → BN → GELU → Dropout(0.15)
  Linear(192→96)  → BN → GELU → Dropout(0.075)
  Linear(96→4)
    ↓
Output: logits (batch, 4)
```

---

## 3. Loss Functions

### FocalLoss

```
FL(p_t) = -α_t · (1 - p_t)^γ · log(p_t)
```

- `gamma = 2.0` — giảm trọng số mẫu dễ phân loại
- `alpha` — class-balanced (công thức CB-loss với beta=0.9999) hoặc per-class list

### LabelSmoothingFocalLoss

Kết hợp focal loss với label smoothing để giảm overconfidence:

- `smoothing = 0.1` — phân phối target: `(1 - ε)` tại class đúng, `ε / (C-1)` tại các class còn lại

---

## 4. Training

**File:** `src/training/train_ft_transformer_nslkdd.py`

### Chiến lược xử lý imbalance

| Kỹ thuật | Mô tả |
|----------|-------|
| WeightedRandomSampler | Oversample minority classes trong DataLoader |
| SMOTE | Synthetic Minority Oversampling (optional, `--smote-strategy`) |
| Class-balanced alpha | Focal loss alpha tỉ lệ nghịch với tần suất class |

### Augmentation

- **Mixup** (`--mixup-alpha`): blend 2 sample với hệ số Beta(α, α). Disabled mặc định.

### Early Stopping

- `patience = 8` epoch không cải thiện val macro-F1
- **Gap penalty**: penalize checkpoint có `train_f1 - val_f1 > 0.20` liên tiếp 3 epoch → tránh overfitting

### Scheduler

- `ReduceLROnPlateau` (default) hoặc `CosineAnnealingLR`

---

## 5. Inference Pipeline (2-stage)

**Files:** `Final_Product/inference/`, `Final_Product/backend/`

```
Network Traffic / Feature CSV (122 features)
            │
            ▼
    ┌───────────────────────────────┐
    │  Stage 1: Autoencoder Gate    │
    │  Model: autoencoder_v2.h5     │
    │  Input: 12 statistical feats  │
    │  threshold = 0.008481         │
    └───────────────────────────────┘
            │                │
    recon > threshold    recon ≤ threshold
            │                │
            ▼                ▼
    ┌──────────────┐    [NORMAL — STOP]
    │  Stage 2:    │
    │  FT-Trans v1 │
    │  best_model  │
    │  .pt         │
    │  4 classes   │
    └──────────────┘
            │
            ▼
    DoS / Probe / R2L / U2R
```

### Các ngưỡng quyết định (inference_config.json)

| Config | Giá trị | Ý nghĩa |
|--------|---------|---------|
| `autoencoder_threshold` | 0.008481 | Ngưỡng reconstruction error (Stage 1) |
| `threshold_calibration_quantile` | 0.99 | Quantile dùng để calibrate ngưỡng |
| `high_confidence_threshold` | 0.95 | Softmax prob > 0.95 → high-confidence alert |
| `stage1_normal_gate_override_threshold` | 0.985 | Override Stage 1 nếu FT-Trans rất tự tin |
| `slow_attack_ratio_override_threshold` | 0.35 | Override gate cho slow attack detection |
| `slow_attack_score_override_threshold` | 0.65 | Score threshold cho slow attack |
| `slow_attack_override_min_rows` | 4 | Số flow tối thiểu để kích hoạt slow attack override |

---

## 6. Cấu trúc thư mục

```
NSL_KDD_Workspace/
├── src/
│   ├── data_processing/
│   │   ├── preprocessing_pipeline.py   # Fit + transform pipeline
│   │   └── improved_data_pipeline.py
│   ├── models/
│   │   ├── phase2_ft_transformer.py    # FTTransformer v1 & v2, Loss functions
│   │   └── feature_selection.py
│   └── training/
│       ├── train_ft_transformer_nslkdd.py   # Training script chính
│       ├── train_improved.py
│       └── run_nslkdd_ft_experiments.py
├── Final_Product/
│   ├── models/
│   │   ├── best_model.pt               # FT-Transformer v1 checkpoint
│   │   ├── autoencoder_v2_best.h5      # Keras autoencoder
│   │   ├── feature_columns.json        # 122 feature names
│   │   ├── scaler.pkl                  # MinMaxScaler
│   │   └── inference_config.json       # Tất cả ngưỡng và paths
│   ├── backend/                        # API server
│   ├── inference/                      # Inference scripts
│   └── FINAL_PRODUCT_REPORT.md
├── data/                               # Raw NSL-KDD files
├── docs/
│   └── NSL_KDD_Architecture.md        # File này
└── archive/                            # Các version cũ
```
