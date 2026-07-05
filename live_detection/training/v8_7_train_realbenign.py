"""
v8_5_train.py — V8.5: Combined Best + Anti-Overfit
Chiến lược:
  - Base:       v8_4_model.pt (Macro F1 94.95%)
  - Data:       Combined_V8_5.csv (mixed domain BF + WebAttack)
  - Layer-wise LR: backbone 1e-5 / mid-layers 1.5e-5 / classifier 3e-5
  - Regularization: dropout=0.15, drop_path=0.15, label_smooth=0.10, wd=2e-4
  - Epochs:     30
"""

import os, sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score
from sklearn.utils.class_weight import compute_class_weight

# === Bước 5 (fine-tune + benign THẬT): self-contained trong live_detection/ ===
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))     # live_detection/training/
LIVE_ROOT = os.path.dirname(WORKSPACE_DIR)                     # live_detection/
REPO_ROOT = os.path.dirname(LIVE_ROOT)                         # Graduation-Thesis/
sys.path.insert(0, LIVE_ROOT)                                  # ids_replay.features (FeatureExtractor)
sys.path.insert(0, os.path.join(LIVE_ROOT, 'model_defs'))     # phase2_ft_transformer_v2, hybrid_feature_scaler

# ============================================================================
# PATHS  (ĐỌC gốc read-only; GHI checkpoint v8_7 vào live_detection/models/)
# ============================================================================
DATA_PATH       = os.path.join(REPO_ROOT, 'Phase3_4_Retrain/v8/v8.5_Combined/Combined_V8_5.csv')
B5_BENIGN_TRAIN = os.path.join(LIVE_ROOT, 'data/analysis/b5_benign_train.csv')  # benign THẬT (40k)
# Bước 4 chứng minh KHÔNG đổi tiền xử lý -> fine-tune từ V8.5 (best), giữ HybridFeatureScaler.
BASE_MODEL_PATH = os.path.join(LIVE_ROOT, 'models', 'v8_5_model.pt')
SCALER_77_PATH  = os.path.join(REPO_ROOT, 'CIC_IDS_2017_Workspace/models/final_cic_ids_2017/scaler_stage1.pkl')

MODEL_SAVE_PATH   = os.path.join(LIVE_ROOT, 'models', 'v8_7_model.pt')
SCALER_SAVE_PATH  = os.path.join(LIVE_ROOT, 'models', 'v8_7_scaler.pkl')
ENCODER_SAVE_PATH = os.path.join(LIVE_ROOT, 'models', 'v8_7_encoder.pkl')

EPOCHS          = 25   # thêm vùng dữ liệu mới (benign thật) -> cần nhiều epoch hơn
EARLY_STOP_PAT  = 6
BATCH_SIZE      = 256

# Layer-wise learning rates
LR_BACKBONE    = 1e-5   # feature_embedding + transformer_blocks[0-1]
LR_MID         = 1.5e-5 # transformer_blocks[2-3] + norm
LR_HEAD        = 3e-5   # classifier

# ============================================================================
# FEATURES
# ============================================================================
EXPECTED_FEATURES_80 = [
    'Flow_Duration', 'Total_Fwd_Packets', 'Total_Backward_Packets', 'Total_Length_of_Fwd_Packets',
    'Total_Length_of_Bwd_Packets', 'Fwd_Packet_Length_Max', 'Fwd_Packet_Length_Min', 'Fwd_Packet_Length_Mean',
    'Fwd_Packet_Length_Std', 'Bwd_Packet_Length_Max', 'Bwd_Packet_Length_Min', 'Bwd_Packet_Length_Mean',
    'Bwd_Packet_Length_Std', 'Flow_Bytes_s', 'Flow_Packets_s', 'Flow_IAT_Mean', 'Flow_IAT_Std', 'Flow_IAT_Max',
    'Flow_IAT_Min', 'Fwd_IAT_Total', 'Fwd_IAT_Mean', 'Fwd_IAT_Std', 'Fwd_IAT_Max', 'Fwd_IAT_Min', 'Bwd_IAT_Total',
    'Bwd_IAT_Mean', 'Bwd_IAT_Std', 'Bwd_IAT_Max', 'Bwd_IAT_Min', 'Fwd_PSH_Flags', 'Fwd_URG_Flags',
    'Fwd_Header_Length', 'Bwd_Header_Length', 'Fwd_Packets_s', 'Bwd_Packets_s', 'Min_Packet_Length',
    'Max_Packet_Length', 'Packet_Length_Mean', 'Packet_Length_Std', 'Packet_Length_Variance', 'FIN_Flag_Count',
    'SYN_Flag_Count', 'RST_Flag_Count', 'PSH_Flag_Count', 'ACK_Flag_Count', 'URG_Flag_Count', 'CWE_Flag_Count',
    'ECE_Flag_Count', 'Down_Up_Ratio', 'Average_Packet_Size', 'Avg_Fwd_Segment_Size', 'Avg_Bwd_Segment_Size',
    'Subflow_Fwd_Packets', 'Subflow_Fwd_Bytes', 'Subflow_Bwd_Packets', 'Subflow_Bwd_Bytes',
    'Init_Win_bytes_forward', 'Init_Win_bytes_backward', 'act_data_pkt_fwd', 'min_seg_size_forward',
    'Active_Mean', 'Active_Std', 'Active_Max', 'Active_Min', 'Idle_Mean', 'Idle_Std', 'Idle_Max', 'Idle_Min',
    'Port_Is_Web', 'Port_Is_RemoteAccess', 'Port_Is_WellKnown', 'Port_Is_Registered', 'Port_Is_Ephemeral',
    'Custom_Fwd_Pkt_Rate', 'Custom_Slow_Index', 'Custom_Pkt_Var_Ratio', 'Custom_IAT_Anomaly',
    'Custom_IAT_CV', 'Custom_Bwd_Pkt_Ratio', 'Custom_Pkt_Size_Ratio',
]

from phase2_ft_transformer_v2 import FTTransformer


# ============================================================================
# FOCAL LOSS — label_smoothing tăng lên 0.10 để giảm overfit
# ============================================================================
class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, weight=None, label_smoothing=0.10):
        super().__init__()
        self.gamma = gamma
        self.weight = weight
        self.label_smoothing = label_smoothing

    def forward(self, inputs, targets):
        ce = nn.functional.cross_entropy(inputs, targets, reduction='none',
                                          weight=self.weight,
                                          label_smoothing=self.label_smoothing)
        pt = torch.exp(-ce)
        return (((1 - pt) ** self.gamma) * ce).mean()


# ============================================================================
# LAYER-WISE PARAM GROUPS
# ============================================================================
def make_param_groups(model):
    """
    3 nhóm LR:
      backbone : feature_embedding + transformer_blocks[0,1]  → LR_BACKBONE
      mid      : transformer_blocks[2,3] + norm               → LR_MID
      head     : classifier                                    → LR_HEAD
    """
    backbone_params, mid_params, head_params = [], [], []

    for name, param in model.named_parameters():
        if name.startswith('feature_embedding') or \
           name.startswith('transformer_blocks.0') or \
           name.startswith('transformer_blocks.1'):
            backbone_params.append(param)
        elif name.startswith('transformer_blocks.2') or \
             name.startswith('transformer_blocks.3') or \
             name.startswith('norm'):
            mid_params.append(param)
        else:  # classifier
            head_params.append(param)

    return [
        {'params': backbone_params, 'lr': LR_BACKBONE, 'name': 'backbone'},
        {'params': mid_params,      'lr': LR_MID,      'name': 'mid'},
        {'params': head_params,     'lr': LR_HEAD,     'name': 'head'},
    ]


# ============================================================================
# HELPERS
# ============================================================================
def load_data(path):
    df = pd.read_csv(path)
    missing = [f for f in EXPECTED_FEATURES_80 if f not in df.columns]
    if missing:
        raise ValueError(f"Thiếu features: {missing}")
    X = df[EXPECTED_FEATURES_80].values.astype(np.float32)
    y = df['Label'].values
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X, y


def load_real_benign(path):
    """benign THẬT (cột CICFlowMeter thô) -> 80 feature qua ĐÚNG FeatureExtractor của live (parity)."""
    from ids_replay.features import FeatureExtractor
    df = pd.read_csv(path, low_memory=False)
    X = FeatureExtractor().build(df)      # đã nan_to_num bên trong
    return X.astype(np.float32)


def fpr_on(model, X_benign, encoder, device, batch_size=1024):
    """FPR = tỉ lệ flow benign bị dự đoán KHÁC Benign."""
    model.eval()
    preds = []
    with torch.no_grad():
        for i in range(0, len(X_benign), batch_size):
            xb = torch.FloatTensor(X_benign[i:i + batch_size]).to(device)
            preds.extend(model(xb).argmax(dim=1).cpu().numpy())
    labels = encoder.inverse_transform(preds)
    return float((labels != 'Benign').mean())


def evaluate(model, X, y_labels, encoder, device, batch_size=512):
    model.eval()
    all_preds = []
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            xb = torch.FloatTensor(X[i:i + batch_size]).to(device)
            all_preds.extend(model(xb).argmax(dim=1).cpu().numpy())
    y_pred   = encoder.inverse_transform(all_preds)
    report   = classification_report(y_labels, y_pred, zero_division=0, output_dict=True)
    b_acc    = balanced_accuracy_score(y_labels, y_pred)
    macro_f1 = report['macro avg']['f1-score']
    return b_acc, macro_f1, y_pred, report


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 60)
    print("V8.5: Combined Best — Anti-Overfit Fine-tune")
    print("=" * 60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[*] Device: {device}")

    # --- Encoder ---
    target_classes = ['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']
    encoder = LabelEncoder()
    encoder.fit(target_classes)
    joblib.dump(encoder, ENCODER_SAVE_PATH)
    print(f"[*] Encoder: {encoder.classes_}")

    # --- Data: CIC (Combined_V8_5) tách train/val trước; benign THẬT chỉ THÊM vào TRAIN ---
    print(f"\n[*] Nạp CIC: {DATA_PATH}")
    Xc, yc_str = load_data(DATA_PATH)
    yc = encoder.transform(yc_str)
    print(f"    CIC: {len(Xc):,} flows")
    for c in target_classes:
        print(f"    {c:<15}: {(yc_str == c).sum():>7,}")

    # val = 10% CIC (giữ nguyên để đo Macro-F1 CIC — chống catastrophic forgetting)
    X_train, X_val, y_train, y_val = train_test_split(
        Xc, yc, test_size=0.1, random_state=42, stratify=yc)

    # THÊM benign thật (40k) vào TRAIN (không vào val CIC)
    print(f"\n[*] Nạp benign THẬT (train-mix): {B5_BENIGN_TRAIN}")
    Xrb = load_real_benign(B5_BENIGN_TRAIN)
    yrb = np.full(len(Xrb), encoder.transform(['Benign'])[0])
    X_train = np.vstack([X_train, Xrb]).astype(np.float32)
    y_train = np.concatenate([y_train, yrb])
    print(f"    + {len(Xrb):,} benign thật -> Train: {len(X_train):,} | Val(CIC): {len(X_val):,}")

    # benign THẬT held-out (val) để theo dõi FPR mỗi epoch (KHÔNG train trên nó)
    from ids_replay.features import FeatureExtractor as _FE
    X_bval = _FE().build(pd.read_csv(os.path.join(LIVE_ROOT, 'data/analysis/b5_benign_val.csv'),
                                     low_memory=False)).astype(np.float32)
    print(f"    benign thật val (theo dõi FPR): {len(X_bval):,} flow")

    # --- Val set composition (để biết mix ratio) ---
    y_val_labels = encoder.inverse_transform(y_val)
    print(f"\n    Val set distribution:")
    for c in target_classes:
        n = (y_val_labels == c).sum()
        print(f"    {c:<15}: {n:>5,}")

    # --- Scaler ---
    print("\n[*] Khởi tạo HybridFeatureScaler...")
    from hybrid_feature_scaler import HybridFeatureScaler
    scaler = HybridFeatureScaler(scaler_77_path=SCALER_77_PATH)
    scaler.fit_custom_scaler(X_train[:, 77:])
    scaler.save(SCALER_SAVE_PATH)
    X_train_s = scaler.transform(X_train)
    X_val_s   = scaler.transform(X_val)
    X_bval_s  = scaler.transform(X_bval)          # benign thật held-out (theo dõi FPR)

    # --- Load model nền (V8.5 — Bước 5 fine-tune từ best) ---
    print(f"\n[*] Nạp model nền: {BASE_MODEL_PATH}")
    # dropout + drop_path_rate tăng so với V8.4 để giảm overfit
    model = FTTransformer(num_features=80, num_classes=5,
                          d_model=128, num_heads=8, num_layers=4,
                          d_ff=512, dropout=0.15, drop_path_rate=0.15)
    state = torch.load(BASE_MODEL_PATH, map_location='cpu', weights_only=False)
    model.load_state_dict(state)
    model = model.to(device)
    for p in model.parameters():
        p.requires_grad = True
    print("    V8.4 model loaded (Macro F1 94.95%) — full unfreeze.")

    # --- Class weights: sqrt-balanced, clip [0.5, 2.0] ---
    cw_balanced = compute_class_weight('balanced', classes=np.arange(5), y=y_train)
    cw_sqrt     = np.sqrt(cw_balanced)
    cw_clipped  = np.clip(cw_sqrt, 0.5, 2.0)
    cw_norm     = cw_clipped / cw_clipped.mean()
    cw          = torch.FloatTensor(cw_norm).to(device)
    print(f"\n[*] Class weights (sqrt-balanced, clip[0.5,2.0], normalized):")
    for cls, w in zip(encoder.classes_, cw_norm):
        print(f"    {cls:<15}: {w:.3f}")

    # --- Layer-wise LR ---
    param_groups = make_param_groups(model)
    print(f"\n[*] Layer-wise LR:")
    for g in param_groups:
        n_params = sum(p.numel() for p in g['params'])
        print(f"    {g['name']:<10}: lr={g['lr']:.0e}  ({n_params:,} params)")

    criterion = FocalLoss(gamma=2.0, weight=cw, label_smoothing=0.10)
    optimizer = torch.optim.AdamW(param_groups, weight_decay=2e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    X_t = torch.FloatTensor(X_train_s).to(device)
    y_t = torch.LongTensor(y_train).to(device)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(X_t, y_t),
        batch_size=BATCH_SIZE, shuffle=True)

    # --- Training ---
    # Checkpoint theo score = Macro-F1(CIC) - FPR(benign thật): tối ưu đúng mục tiêu Bước 5
    # (hạ FPR benign thật mà KHÔNG làm sập CIC). FPR đo trên benign thật held-out (không train).
    print(f"\n[*] Bắt đầu training (max {EPOCHS} epochs, early stop patience={EARLY_STOP_PAT})...")
    print(f"    Tiêu chí checkpoint: score = Macro-F1(CIC) - FPR(benign thật val)")
    best_score     = -1e9
    no_improve_cnt = 0

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for bx, by in loader:
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()

        b_acc, macro_f1, y_pred, report = evaluate(
            model, X_val_s, y_val_labels, encoder, device)
        fpr = fpr_on(model, X_bval_s, encoder, device)      # FPR benign thật held-out
        score = macro_f1 - fpr

        bf_r  = report.get('Brute Force', {}).get('recall', 0)
        dos_r = report.get('DoS', {}).get('recall', 0)
        wa_r  = report.get('Web Attack', {}).get('recall', 0)
        ps_r  = report.get('PortScan', {}).get('recall', 0)

        print(f"  Epoch {epoch+1:02d}/{EPOCHS} | Loss: {total_loss/len(loader):.4f} | "
              f"MacroF1(CIC): {macro_f1:.4f} | FPR(real): {fpr*100:5.2f}% | score: {score:.4f} | "
              f"recall DoS {dos_r:.2f}/BF {bf_r:.2f}/WA {wa_r:.2f}/PS {ps_r:.2f}")

        if score > best_score:
            best_score     = score
            no_improve_cnt = 0
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"   -> Checkpoint saved (score {best_score:.4f} | MacroF1 {macro_f1:.4f} | FPR {fpr*100:.2f}%)")
        else:
            no_improve_cnt += 1
            if no_improve_cnt >= EARLY_STOP_PAT:
                print(f"\n[!] Early stop tại epoch {epoch+1} "
                      f"(score không cải thiện {EARLY_STOP_PAT} epoch liên tiếp)")
                break

    # --- Final Report ---
    print("\n" + "=" * 60)
    print("KẾT QUẢ CUỐI CÙNG (Val set — best checkpoint)")
    print("=" * 60)
    model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=device, weights_only=False))
    b_acc, macro_f1, y_pred, report = evaluate(
        model, X_val_s, y_val_labels, encoder, device)

    print(classification_report(y_val_labels, y_pred, zero_division=0))
    print(f"Balanced Accuracy : {b_acc:.4f}")
    print(f"Macro F1          : {macro_f1:.4f}")

    cm = confusion_matrix(y_val_labels, y_pred, labels=target_classes)
    print("\nConfusion Matrix:")
    print(pd.DataFrame(cm, index=target_classes, columns=target_classes).to_string())

    print(f"\n[+] Model  : {MODEL_SAVE_PATH}")
    print(f"[+] Scaler : {SCALER_SAVE_PATH}")
    print(f"[+] Encoder: {ENCODER_SAVE_PATH}")


if __name__ == '__main__':
    main()
