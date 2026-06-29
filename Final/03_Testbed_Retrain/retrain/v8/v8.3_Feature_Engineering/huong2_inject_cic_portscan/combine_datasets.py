"""
combine_datasets.py — Hướng 2 V8.3
Kết hợp:
  - Run10 testbed (Benign + BruteForce + WebAttack + DoS) — lấy từ Cleaned_Labeled_Dataset_run10.csv
  - CIC-IDS-2017 PortScan — lấy từ cic_portscan_mapped.csv (output của feature_mapper.py)

Output:
  - Combined_V8_3_Huong2.csv  (dùng để train V8.3 Hướng 2)

Chạy: python3 combine_datasets.py
"""

import pandas as pd
import numpy as np

SCRIPTS_DIR  = '/home/ning/Graduation-Thesis/Custom_IDS_Testbed/scripts'
RUN10_PATH   = f'{SCRIPTS_DIR}/Cleaned_Labeled_Dataset_run10.csv'
CIC_PS_PATH  = 'cic_portscan_mapped.csv'
OUTPUT_PATH  = 'Combined_V8_3_Huong2.csv'

# Số PortScan flows từ CIC đưa vào — 5000 để cân bằng với các class nhỏ
CIC_PS_SAMPLE = 5000

EXPECTED_FEATURES_81 = [
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
    'Custom_PortScan_Intensity',
]


def load_and_check(path, name):
    print(f"[*] Loading {name}: {path}")
    df = pd.read_csv(path)
    print(f"    Shape: {df.shape}")
    print(f"    Labels: {df['Label'].value_counts().to_dict()}")
    return df


def align_features(df, source_name):
    """Giữ đúng 81 features + Label, điền 0 nếu thiếu."""
    missing = [f for f in EXPECTED_FEATURES_81 if f not in df.columns]
    if missing:
        print(f"    [!] {source_name} thiếu {len(missing)} features — điền 0: {missing}")
        for f in missing:
            df[f] = 0.0
    extra = [c for c in df.columns if c not in EXPECTED_FEATURES_81 and c != 'Label']
    if extra:
        print(f"    [*] {source_name} bỏ {len(extra)} cột thừa")
        df = df.drop(columns=extra)
    return df[EXPECTED_FEATURES_81 + ['Label']]


def main():
    # --- Load run10 ---
    run10 = load_and_check(RUN10_PATH, 'Run10 testbed')

    # Bỏ PortScan testbed (chỉ 7 flows, không đủ đại diện)
    run10_base = run10[run10['Label'] != 'PortScan'].copy()
    print(f"\n[*] Run10 sau khi bỏ PortScan: {len(run10_base):,} rows")

    # --- Load CIC PortScan ---
    cic_ps = load_and_check(CIC_PS_PATH, 'CIC-IDS-2017 PortScan')

    # Downsample CIC PortScan để không lấn át các class nhỏ (BruteForce ~3k)
    if len(cic_ps) > CIC_PS_SAMPLE:
        cic_ps = cic_ps.sample(n=CIC_PS_SAMPLE, random_state=42)
        print(f"[*] CIC PortScan downsampled → {len(cic_ps):,} rows")

    # --- Align features ---
    print("\n[*] Aligning features...")
    run10_base = align_features(run10_base, 'Run10')
    cic_ps     = align_features(cic_ps,     'CIC PortScan')

    # --- Combine ---
    combined = pd.concat([run10_base, cic_ps], ignore_index=True)
    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"\n[+] Combined dataset: {len(combined):,} rows")
    print("    Distribution:")
    vc = combined['Label'].value_counts()
    for label, count in vc.items():
        pct = count / len(combined) * 100
        print(f"      {label:<15}: {count:>6,}  ({pct:.1f}%)")

    # --- Kiểm tra feature phân biệt ---
    print("\n=== Flow_Duration theo Label (μs) ===")
    print(combined.groupby('Label')['Flow_Duration'].agg(['mean', 'median']).round(0).to_string())

    print("\n=== RST_Flag_Count theo Label ===")
    print(combined.groupby('Label')['RST_Flag_Count'].mean().round(3).to_string())

    # --- Lưu ---
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\n[+] Saved: {OUTPUT_PATH}")
    print(f"    Columns: {len(combined.columns)} (81 features + Label)")


if __name__ == '__main__':
    main()
