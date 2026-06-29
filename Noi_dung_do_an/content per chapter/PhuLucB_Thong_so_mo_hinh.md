# Phụ lục B. Thông số mô hình và kết quả chi tiết

## B.1 Bảng siêu tham số tất cả các mô hình

### B.1.1 NSL-KDD — Stage 1: Autoencoder Anomaly Gate

| Tham số | Giá trị |
|---|---|
| Kiến trúc Encoder | 122 → 64 → 32 → 16 |
| Kiến trúc Decoder | 16 → 32 → 64 → 122 |
| Activation | ReLU |
| Optimizer | Adam (lr=0,001) |
| Epochs | 100 (Early Stopping patience=10) |
| Batch size | 256 |
| Reconstruction loss | MSE |
| Ngưỡng τ | 0,008481 (percentile 95 của Normal train errors) |
| Huấn luyện trên | Normal flows only (KDDTrain+) |

### B.1.2 NSL-KDD — Stage 2: FT-Transformer

| Tham số | Giá trị |
|---|---|
| d_model | 128 |
| n_heads | 8 |
| n_layers | 4 |
| d_ff (FFN) | 512 |
| Dropout | 0,1 |
| Activation | GELU |
| Normalization | Pre-LN |
| Loss | Focal Loss (γ=2) |
| Optimizer | AdamW (lr=1e-4, weight_decay=1e-5) |
| Scheduler | CosineAnnealingLR |
| Epochs | 50 (Early Stopping patience=5) |
| Batch size | 256 |
| Số features đầu vào | 122 (sau one-hot encoding 3 nominal features) |
| Số lớp đầu ra | 5 (Normal, DoS, Probe, R2L, U2R) |

### B.1.3 NSL-KDD — Stage 2: LightGBM

| Tham số | Giá trị |
|---|---|
| n_estimators | 1000 |
| max_leaves | 127 |
| learning_rate | 0,05 |
| min_child_samples | 20 |
| feature_fraction | 0,8 |
| bagging_fraction | 0,8 |
| bagging_freq | 5 |
| class_weight | inverse frequency |
| early_stopping_rounds | 50 |

### B.1.4 NSL-KDD — Stage 2: Meta Logistic Regression

| Tham số | Giá trị |
|---|---|
| Input dimension | 10 (5 xác suất × 2 base learners) |
| C (regularization) | 1,0 |
| max_iter | 1000 |
| solver | lbfgs |
| multi_class | multinomial |

### B.1.5 CIC-IDS-2017 — Stage 1: Gating Network (FT-Transformer)

| Tham số | Giá trị |
|---|---|
| d_model | 128 |
| n_heads | 8 |
| n_layers | 4 |
| d_ff (FFN) | 512 |
| Dropout | 0,2 |
| Activation | GELU |
| Loss | CB-Focal Loss (γ=2, alpha nghịch effective number) |
| Optimizer | AdamW (lr=1e-4) |
| Epochs | 30 (Early Stopping patience=5) |
| Batch size | 512 |
| Số features đầu vào | 77 |
| Số lớp đầu ra | 2 (Benign, Suspicious) |
| Ngưỡng phân loại | 0,85 (confidence Benign < 85% → Suspicious) |

### B.1.6 CIC-IDS-2017 — Stage 2: Expert Network (FT-Transformer)

| Tham số | Giá trị |
|---|---|
| d_model | 64 |
| n_heads | 4 |
| n_layers | 3 |
| d_ff (FFN) | 256 |
| Dropout | 0,2 |
| Activation | GELU |
| Loss | CB-Focal Loss (γ=1,5) + Hard Negative Mining (w_hard=2,0, 2 vòng) |
| Optimizer | AdamW (lr=5e-5) |
| Epochs | 50 (Early Stopping patience=7) |
| Batch size | 256 |
| Số features đầu vào | 34 (sau lọc correlation > 0,95) |
| Số lớp đầu ra | 9 (Benign + 8 nhóm tấn công) |

### B.1.7 CIC-IDS-2017 — Stage 2: Random Forest

| Tham số | Giá trị |
|---|---|
| n_estimators | 150 |
| max_depth | 25 |
| max_features | 20 |
| min_samples_split | 5 |
| min_samples_leaf | 2 |
| class_weight | balanced_subsample |
| random_state | 42 |

### B.1.8 CIC-IDS-2017 — Stage 2: KNN

| Tham số | Giá trị |
|---|---|
| K | 16 |
| weights | distance |
| metric | euclidean |
| algorithm | ball_tree |
| leaf_size | 30 |

### B.1.9 Testbed V8.5 — FT-Transformer

| Tham số | Giá trị |
|---|---|
| d_model | 128 |
| n_heads | 8 |
| n_layers | 4 |
| d_ff (FFN) | 512 |
| Dropout | 0,2 |
| Activation | GELU |
| Loss | CB-Focal Loss (γ=2) |
| Optimizer | AdamW (lr=1e-4) |
| Epochs | 50 (Early Stopping patience=7) |
| Batch size | 256 |
| Số features đầu vào | 80 (77 đặc trưng pipeline CIC + 3 đặc trưng Model Surgery) |
| Số lớp đầu ra | 5 (Benign, BruteForce, DoS, PortScan, WebAttack) |

**3 đặc trưng bổ sung cho môi trường NAT:**
- `IAT_CV` = std(IAT) / mean(IAT) — hệ số biến thiên inter-arrival time
- `Bwd_Pkt_Ratio` = Bwd_Packets / Total_Packets — tỷ lệ gói tin chiều ngược
- `Pkt_Size_Ratio` = Bwd_Pkt_Len_Mean / Fwd_Pkt_Len_Mean — tỷ lệ kích thước gói tin

---

## B.2 Kết quả đánh giá chi tiết

### B.2.1 NSL-KDD — Kết quả per-class trên KDDTest+

| Lớp | Precision | Recall | F1-score | Support |
|---|---|---|---|---|
| Normal | 0,7154 | 0,9682 | 0,8228 | 9.711 |
| DoS | 0,9630 | 0,8032 | 0,8759 | 7.458 |
| Probe | 0,8024 | 0,7852 | 0,7937 | 2.421 |
| R2L | 0,9681 | 0,2523 | 0,4003 | 2.885 |
| U2R | 0,5517 | 0,4776 | 0,5120 | 67 |
| **Macro avg** | **0,8001** | **0,6573** | **0,6809** | |
| **Macro F1** | | | **0,6809** | |

*Lưu ý:* Macro F1 = 0,6809 được tính theo giao thức train/val/test tách biệt hoàn toàn, không dùng KDDTest+ cho tuning.

### B.2.2 CIC-IDS-2017 — Kết quả Stage 1 Gating Network

| Chỉ số | Benign | Suspicious |
|---|---|---|
| Precision | 0,9997 | 0,9651 |
| Recall | 0,9982 | 0,9933 |
| F1 | 0,9989 | 0,9790 |

Tỷ lệ flow được route sang Stage 2: 17,3% (Suspicious)
False Negative Rate (tấn công bị gán Benign): 0,67%

### B.2.3 CIC-IDS-2017 — Kết quả so sánh kiến trúc

| Kiến trúc | Accuracy | Macro F1 |
|---|---|---|
| 1-Stage 9-class FTT | 98,21% | 0,7831 |
| Two-Stage (không HNM) | 99,55% | 0,8817 |
| Two-Stage + HNM 1 vòng | 99,58% | 0,9102 |
| Two-Stage + HNM 2 vòng | 99,60% | 0,9181 |
| Two-Stage + HNM + Majority Vote | 99,61% | 0,9247 |
| **Two-Stage + HNM + Asymmetric Vote** | **99,55%** | **0,9294** |

### B.2.4 CIC-IDS-2017 — Kết quả per-class cuối (Asymmetric Ensemble)

| Lớp | Precision | Recall | F1-score | Support |
|---|---|---|---|---|
| Benign | 0,9992 | 0,9953 | 0,9972 | 2.031.715 |
| DoS | 0,9683 | 0,9963 | 0,9821 | 225.024 |
| DDoS | 0,9984 | 0,9982 | 0,9983 | 114.453 |
| PortScan | 0,9936 | 0,9990 | 0,9963 | 142.079 |
| BruteForce | 0,9473 | 0,9989 | 0,9724 | 12.369 |
| Web Attack | 0,9084 | 0,9810 | 0,9433 | 1.950 |
| Botnet | 0,7947 | 0,6826 | 0,7344 | 1.758 |
| Infiltration | 0,9524 | 0,6061 | 0,7407 | 33 |
| Heartbleed | 1,0000 | 1,0000 | 1,0000 | 10 |
| **Macro avg** | | | **0,9294** | |

### B.2.5 Kết quả chẩn đoán covariate shift

| Thực nghiệm | Accuracy | MCC |
|---|---|---|
| CIC model trên CIC test (baseline) | 99,55% | 0,9941 |
| Direct transfer → Testbed WSL2 | 21,93% | -0,015 |
| Re-fit Scaler trên Testbed | 6,87% | -0,087 |

### B.2.6 Testbed V8.5 — Kết quả per-class (val set đa dạng miền)

| Lớp | Precision | Recall | F1-score | Support |
|---|---|---|---|---|
| Benign | 0,87 | 0,95 | 0,91 | 5.200 |
| BruteForce | 0,83 | 0,90 | 0,86 | 798 |
| DoS | 0,98 | 0,89 | 0,93 | 1.978 |
| PortScan | 1,00 | 1,00 | 1,00 | 500 |
| WebAttack | 0,96 | 0,81 | 0,88 | 2.707 |
| **Macro avg** | **0,93** | **0,91** | **0,917** | **11.183** |
| **Balanced Accuracy** | | | **91,1%** | |
| **MCC** | | | **0,865** | |

### B.2.7 So sánh val set đồng nhất vs đa dạng miền (V8.4 vs V8.5)

| Tập kiểm định | BruteForce F1 | DoS F1 | WebAttack F1 | Macro F1 |
|---|---|---|---|---|
| V8.4 — 100% CIC Patator | 1,000 | 0,95 | 0,90 | 0,970 |
| V8.5 — Mixed (CIC + hydra) | 0,860 | 0,93 | 0,88 | 0,916 |
| **Chênh lệch** | **-0,140** | -0,02 | -0,02 | **-0,054** |

---

## B.3 Cấu trúc thư mục mô hình

```
CIC_IDS_2017_Workspace/models/
├── v4_cascade/
│   ├── stage1/
│   │   ├── gating_ftt.pt          # Gating Network weights
│   │   └── gating_scaler.pkl      # PowerTransformer Stage 1
│   └── stage2/
│       ├── expert_ftt.pt          # Expert FTT weights
│       ├── expert_rf.pkl          # Random Forest pickle
│       ├── expert_knn.pkl         # KNN pickle
│       └── stage2_scaler.pkl      # PowerTransformer Stage 2

Custom_IDS_Testbed/models/
├── ftt_v85.pt                     # Testbed V8.5 FTT weights
├── testbed_v85_scaler.pkl         # PowerTransformer Testbed
└── feature_columns_v85.json       # Danh sách 80 features theo thứ tự

NSL_KDD_Workspace/models/
├── ae_gate.pt                     # Autoencoder weights
├── ftt_stage2.pt                  # FTT Stage 2 weights
├── lgbm_stage2.pkl                # LightGBM pickle
└── meta_lr.pkl                    # Meta Logistic Regression pickle
```
