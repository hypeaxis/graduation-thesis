"""
build_dataset_v8_5.py — V8.5
Tổng hợp tốt nhất từ V8.3 + V8.4:

  BruteForce  : Run10 hydra 2,984  + CIC Patator 4,999 = 7,983  (mixed domain)
  PortScan    : CIC Friday  5,000                       = 5,000  (giữ từ V8.4)
  WebAttack   : Run10       24,887 + CIC Thursday 2,180 = 27,067 (thêm SQL/XSS)
  Benign      : Run10       51,994                      = 51,994
  DoS         : Run10       19,781                      = 19,781
  ─────────────────────────────────────────────────────────────────
  Tổng ước tính:                                        ~111,825 flows

Chạy: python3 build_dataset_v8_5.py
"""

import pandas as pd
import numpy as np
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Nguồn dữ liệu
H2_PATH        = os.path.join(SCRIPT_DIR,
    '../v8.3_Feature_Engineering/huong2_inject_cic_portscan/Combined_V8_3_Huong2.csv')
CIC_BF_PATH    = os.path.join(SCRIPT_DIR,
    '../v8.4_BruteForce_Fix/cic_bruteforce_mapped.csv')
CIC_WA_PATH    = os.path.join(SCRIPT_DIR, 'cic_webattack_mapped.csv')

OUTPUT_PATH    = os.path.join(SCRIPT_DIR, 'Combined_V8_5.csv')

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
COLS = EXPECTED_FEATURES_80 + ['Label']


def main():
    print("=" * 60)
    print("  Build Dataset V8.5 — Combined Best")
    print("=" * 60)

    # ── 1. Load H2 dataset (base testbed data) ──────────────────
    print(f"\n[*] Load H2 base dataset...")
    h2 = pd.read_csv(H2_PATH)
    print(f"    Shape: {h2.shape}")
    print(f"    Labels:\n{h2['Label'].value_counts().to_string()}")

    # Từ H2 lấy: Benign, DoS, WebAttack, PortScan (CIC), BruteForce (Run10 hydra)
    # Không bỏ BruteForce lần này — giữ Run10 hydra để mix
    benign    = h2[h2['Label'] == 'Benign'][COLS]
    dos       = h2[h2['Label'] == 'DoS'][COLS]
    wa_run10  = h2[h2['Label'] == 'Web Attack'][COLS]
    ps_cic    = h2[h2['Label'] == 'PortScan'][COLS]
    bf_run10  = h2[h2['Label'] == 'Brute Force'][COLS]

    print(f"\n    Benign (Run10)     : {len(benign):,}")
    print(f"    DoS (Run10)        : {len(dos):,}")
    print(f"    WebAttack (Run10)  : {len(wa_run10):,}")
    print(f"    PortScan (CIC)     : {len(ps_cic):,}")
    print(f"    BruteForce (Run10) : {len(bf_run10):,}  ← hydra, giữ lại để mix")

    # ── 2. Load CIC BruteForce (Patator FTP+SSH) ────────────────
    print(f"\n[*] Load CIC BruteForce (Patator)...")
    cic_bf = pd.read_csv(CIC_BF_PATH)
    print(f"    Shape: {cic_bf.shape} | Label: {cic_bf['Label'].unique()}")

    # ── 3. Load CIC WebAttack (Thursday) ────────────────────────
    print(f"\n[*] Load CIC WebAttack (Thursday)...")
    cic_wa = pd.read_csv(CIC_WA_PATH)
    print(f"    Shape: {cic_wa.shape} | Label: {cic_wa['Label'].unique()}")

    # ── 4. Merge ─────────────────────────────────────────────────
    print(f"\n[*] Ghép dataset...")
    parts = {
        'Benign (Run10)'        : benign,
        'DoS (Run10)'           : dos,
        'WebAttack (Run10)'     : wa_run10,
        'WebAttack (CIC Thu)'   : cic_wa[COLS],
        'PortScan (CIC Fri)'    : ps_cic,
        'BruteForce (Run10 hydra)' : bf_run10,
        'BruteForce (CIC Patator)' : cic_bf[COLS],
    }
    for name, df in parts.items():
        print(f"    + {name:<28}: {len(df):>6,} flows")

    combined = pd.concat(list(parts.values()), ignore_index=True)

    # Clean
    combined.replace([np.inf, -np.inf], np.nan, inplace=True)
    before = len(combined)
    combined.dropna(subset=EXPECTED_FEATURES_80, inplace=True)
    if before != len(combined):
        print(f"\n[*] Xoá {before - len(combined)} NaN/Inf rows")

    combined = combined.sample(frac=1, random_state=42).reset_index(drop=True)

    # ── 5. Kết quả ──────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  PHÂN BỐ DATASET V8.5 ({len(combined):,} flows)")
    print(f"{'='*60}")
    vc = combined['Label'].value_counts()
    for label, count in vc.items():
        pct = count / len(combined) * 100
        print(f"  {label:<15}: {count:>7,}  ({pct:.1f}%)")

    print(f"\n  So sánh BruteForce:")
    print(f"    V8.4 : 4,999 flows (CIC only)")
    print(f"    V8.5 : {vc.get('Brute Force', 0):,} flows (Run10 hydra + CIC Patator)")
    print(f"\n  So sánh WebAttack:")
    print(f"    V8.4 : 24,887 flows (Run10 only)")
    print(f"    V8.5 : {vc.get('Web Attack', 0):,} flows (Run10 + CIC XSS/SQLi/BF)")

    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\n[+] Saved: {OUTPUT_PATH}")
    print(f"    Shape: {combined.shape}")


if __name__ == '__main__':
    main()
