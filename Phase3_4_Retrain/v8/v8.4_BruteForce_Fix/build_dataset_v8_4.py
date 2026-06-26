"""
build_dataset_v8_4.py — V8.4
Xây dataset từ H2 base + thay Run10 BruteForce bằng CIC BruteForce.

Công thức:
  Combined_V8_4 = H2_dataset (bỏ Run10 BF 2,984 flows)
                + CIC BruteForce 4,999 flows (FTP-Patator + SSH-Patator)

Tổng ước tính: ~107,000 flows

Chạy:
    python3 build_dataset_v8_4.py
"""

import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

H2_DATASET_PATH = os.path.join(
    SCRIPT_DIR, '../v8.3_Feature_Engineering/huong2_inject_cic_portscan/Combined_V8_3_Huong2.csv')
CIC_BF_PATH     = os.path.join(SCRIPT_DIR, 'cic_bruteforce_mapped.csv')
OUTPUT_PATH     = os.path.join(SCRIPT_DIR, 'Combined_V8_4.csv')

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


def main():
    print("=" * 55)
    print("  Build Dataset V8.4")
    print("=" * 55)

    # --- Load H2 base dataset ---
    print(f"\n[*] Load H2 dataset: {H2_DATASET_PATH}")
    h2 = pd.read_csv(H2_DATASET_PATH)
    print(f"    H2 shape: {h2.shape}")
    print(f"    H2 labels:\n{h2['Label'].value_counts().to_string()}")

    # Bỏ Run10 Brute Force (2,984 flows) khỏi H2
    h2_no_bf = h2[h2['Label'] != 'Brute Force'].copy()
    n_removed = len(h2) - len(h2_no_bf)
    print(f"\n[*] Đã loại {n_removed:,} Run10 Brute Force flows")

    # --- Load CIC BruteForce ---
    print(f"\n[*] Load CIC BruteForce: {CIC_BF_PATH}")
    cic_bf = pd.read_csv(CIC_BF_PATH)
    print(f"    CIC BF shape: {cic_bf.shape}")
    print(f"    Labels: {cic_bf['Label'].value_counts().to_dict()}")

    # Kiểm tra feature compatibility
    common_features = EXPECTED_FEATURES_80 + ['Label']
    missing_h2  = [f for f in common_features if f not in h2_no_bf.columns]
    missing_cic = [f for f in common_features if f not in cic_bf.columns]
    if missing_h2:
        print(f"[!] H2 thiếu features: {missing_h2}")
    if missing_cic:
        print(f"[!] CIC BF thiếu features: {missing_cic}")
    if not missing_h2 and not missing_cic:
        print("[+] Feature compatibility OK ✓")

    # --- Merge ---
    combined = pd.concat([
        h2_no_bf[common_features],
        cic_bf[common_features]
    ], ignore_index=True)

    # Clean
    combined.replace([np.inf, -np.inf], np.nan, inplace=True)
    before = len(combined)
    combined.dropna(subset=EXPECTED_FEATURES_80, inplace=True)
    if before != len(combined):
        print(f"[*] Đã xoá {before - len(combined)} NaN/Inf rows")

    # Shuffle
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"\n{'='*55}")
    print(f"  PHÂN BỐ DATASET V8.4 ({len(combined):,} flows)")
    print(f"{'='*55}")
    vc = combined['Label'].value_counts()
    for label, count in vc.items():
        pct = count / len(combined) * 100
        print(f"  {label:<15}: {count:>6,}  ({pct:.1f}%)")

    # So sánh với H2
    print(f"\n  So sánh Brute Force:")
    print(f"  H2:  {h2['Label'].eq('Brute Force').sum():,} flows (Run10 testbed)")
    print(f"  V8.4: {vc.get('Brute Force', 0):,} flows (CIC FTP+SSH Patator)")

    # Lưu
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\n[+] Saved: {OUTPUT_PATH}")
    print(f"    Shape: {combined.shape}")


if __name__ == '__main__':
    main()
