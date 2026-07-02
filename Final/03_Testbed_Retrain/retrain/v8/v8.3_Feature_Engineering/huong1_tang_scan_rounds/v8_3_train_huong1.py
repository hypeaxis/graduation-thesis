"""
v8_3_train_huong1.py — V8.3 Hướng 1: Fine-tune V7 model với CIC PortScan injected data
Dựa trên 4e_retrain_run7_v7.py, thay đổi:
  - Data: Combined_V8_3_Huong1.csv (run10 Benign/BF/WebAtk/DoS + CIC PortScan 5k) — đặt env DATA_PATH nếu để nơi khác
  - Base model: v7_model.pt (đã có 5 class, 80 features — không cần model surgery)
  - lr: 3e-5 (thấp hơn v7 do domain shift CIC→testbed)
  - Epochs: 20 (nhiều hơn để học PortScan pattern)
  - Features: EXPECTED_FEATURES_80 (80 features, không dùng Custom_PortScan_Intensity)
"""

import os
import sys
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, balanced_accuracy_score

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(WORKSPACE_DIR, '../../../src'))
sys.path.insert(0, os.path.join(WORKSPACE_DIR, '../../../../CIC_IDS_2017_Workspace/src/models'))

# ============================================================================
# PATHS
# ============================================================================
# ⚠️ Sửa cho khớp dataset bạn tự dựng, hoặc đặt env DATA_PATH (xem ../../../../HUONG_DAN_CHAY.md).
#    Mặc định: file Combined_V8_3_Huong1.csv cùng thư mục script.
DATA_PATH       = os.environ.get('DATA_PATH', os.path.join(WORKSPACE_DIR, 'Combined_V8_3_Huong1.csv'))
BASE_MODEL_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../../../archive_v7_run7/models/v7_model.pt'))
SCALER_77_PATH  = os.path.abspath(os.path.join(
    WORKSPACE_DIR, '../../../../CIC_IDS_2017_Workspace/models/final_cic_ids_2017/scaler_stage1.pkl'))

MODEL_SAVE_PATH   = os.path.join(WORKSPACE_DIR, 'v8_3_huong1_model.pt')
SCALER_SAVE_PATH  = os.path.join(WORKSPACE_DIR, 'v8_3_huong1_scaler.pkl')
ENCODER_SAVE_PATH = os.path.join(WORKSPACE_DIR, 'v8_3_huong1_encoder.pkl')

# ============================================================================
# FEATURES — 80 features (KHÔNG dùng Custom_PortScan_Intensity)
# Khớp với v7_model.pt
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


# Import kiến trúc gốc từ phase2_ft_transformer_v2.py (cùng weights với v7_model.pt)
from phase2_ft_transformer_v2 import FTTransformer


# ============================================================================
# FOCAL LOSS
# ============================================================================
class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, weight=None, label_smoothing=0.05):
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


def evaluate(model, X, y_labels, encoder, device, batch_size=512):
    model.eval()
    all_preds = []
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            xb = torch.FloatTensor(X[i:i+batch_size]).to(device)
            logits = model(xb)
            all_preds.extend(logits.argmax(dim=1).cpu().numpy())
    y_pred = encoder.inverse_transform(all_preds)
    report = classification_report(y_labels, y_pred, zero_division=0, output_dict=True)
    b_acc = balanced_accuracy_score(y_labels, y_pred)
    macro_f1 = report['macro avg']['f1-score']
    return b_acc, macro_f1, y_pred, report


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("=" * 60)
    print("V8.3 HƯỚNG 1: Fine-tune V7 + CIC PortScan Injection")
    print("=" * 60)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"[*] Device: {device}")

    # --- Encoder ---
    target_classes = ['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']
    encoder = LabelEncoder()
    encoder.fit(target_classes)
    joblib.dump(encoder, ENCODER_SAVE_PATH)
    print(f"[*] Encoder: {encoder.classes_}")

    # --- Data ---
    print(f"\n[*] Nạp dữ liệu: {DATA_PATH}")
    X, y_str = load_data(DATA_PATH)
    y = encoder.transform(y_str)

    print(f"    Tổng: {len(X):,} flows")
    for c in target_classes:
        n = (y_str == c).sum()
        print(f"    {c:<15}: {n:>6,}")

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.1, random_state=42, stratify=y)
    print(f"\n    Train: {len(X_train):,} | Val: {len(X_val):,}")

    # --- Scaler ---
    print("\n[*] Khởi tạo HybridFeatureScaler...")
    from hybrid_feature_scaler import HybridFeatureScaler
    scaler = HybridFeatureScaler(scaler_77_path=SCALER_77_PATH)
    scaler.fit_custom_scaler(X_train[:, 77:])
    scaler.save(SCALER_SAVE_PATH)
    X_train_s = scaler.transform(X_train)
    X_val_s   = scaler.transform(X_val)

    # --- Model: load v7 trực tiếp (đã có 5 class, 80 features) ---
    print(f"\n[*] Nạp V7 model: {BASE_MODEL_PATH}")
    model = FTTransformer(num_features=80, num_classes=5,
                          d_model=128, num_heads=8, num_layers=4,
                          d_ff=512, dropout=0.1, drop_path_rate=0.1)
    state = torch.load(BASE_MODEL_PATH, map_location='cpu')
    model.load_state_dict(state)
    model = model.to(device)
    for p in model.parameters():
        p.requires_grad = True
    print("    V7 model loaded — full unfreeze.")

    # --- Loss & Optimizer ---
    # Balanced class weights (inverse sqrt frequency) — PortScan chỉ 2% data
    from sklearn.utils.class_weight import compute_class_weight
    cw_np = compute_class_weight('balanced', classes=np.arange(5), y=y_train)
    cw_np = np.sqrt(cw_np)          # sqrt để tránh quá extreme
    cw_np = cw_np / cw_np.mean()    # normalize quanh 1.0
    cw = torch.FloatTensor(cw_np).to(device)
    print(f"[*] Class weights: {dict(zip(encoder.classes_, cw_np.round(3)))}")
    criterion = FocalLoss(gamma=2.0, weight=cw, label_smoothing=0.05)
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=20)

    X_t = torch.FloatTensor(X_train_s).to(device)
    y_t = torch.LongTensor(y_train).to(device)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(X_t, y_t),
        batch_size=256, shuffle=True)

    # --- Training ---
    print("\n[*] Bắt đầu training (20 epochs)...")
    best_macro_f1 = -1
    y_val_labels = encoder.inverse_transform(y_val)

    for epoch in range(20):
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

        ps_f1 = report.get('PortScan', {}).get('f1-score', 0)
        print(f"  Epoch {epoch+1:02d}/20 | Loss: {total_loss/len(loader):.4f} | "
              f"B-Acc: {b_acc:.4f} | Macro F1: {macro_f1:.4f} | PortScan F1: {ps_f1:.4f}")

        if macro_f1 > best_macro_f1:
            best_macro_f1 = macro_f1
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print(f"   -> Checkpoint saved (Macro F1: {best_macro_f1:.4f})")

    # --- Final Report ---
    print("\n" + "=" * 60)
    print("KẾT QUẢ CUỐI CÙNG (Val set — best checkpoint)")
    print("=" * 60)
    model.load_state_dict(torch.load(MODEL_SAVE_PATH, map_location=device))
    b_acc, macro_f1, y_pred, report = evaluate(
        model, X_val_s, y_val_labels, encoder, device)

    print(classification_report(y_val_labels, y_pred, zero_division=0))
    print(f"Balanced Accuracy : {b_acc:.4f}")
    print(f"Macro F1          : {macro_f1:.4f}")

    cm = confusion_matrix(y_val_labels, y_pred, labels=target_classes)
    print("\nConfusion Matrix:")
    print(pd.DataFrame(cm, index=target_classes, columns=target_classes).to_string())

    print(f"\n[+] Model saved: {MODEL_SAVE_PATH}")
    print(f"[+] Scaler saved: {SCALER_SAVE_PATH}")
    print(f"[+] Encoder saved: {ENCODER_SAVE_PATH}")


if __name__ == '__main__':
    main()
