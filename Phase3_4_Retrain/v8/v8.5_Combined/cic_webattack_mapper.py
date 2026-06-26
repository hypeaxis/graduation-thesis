"""
cic_webattack_mapper.py — V8.5
Map CIC-IDS-2017 Thursday WebAttacks → 80 features tương thích testbed.

Labels: "Web Attack – Brute Force", "Web Attack – XSS", "Web Attack – Sql Injection"
         → tất cả → "Web Attack"

Tổng CIC Thursday WebAttack: 2,180 flows (1507 + 652 + 21)
Lấy tất cả (không sample vì ít).

Chạy: python3 cic_webattack_mapper.py
Output: cic_webattack_mapped.csv
"""

import pandas as pd
import numpy as np

CIC_RAW_PATH = '/home/ning/Graduation-Thesis/CIC_IDS_2017_Workspace/data/raw/' \
               'Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv'
OUTPUT_PATH  = 'cic_webattack_mapped.csv'

# Thursday: columns KHÔNG có leading space — dùng clean keys
CIC_TO_TESTBED = {
    'Destination Port':             '_dst_port_tmp',
    'Flow Duration':                'Flow_Duration',
    'Total Fwd Packets':            'Total_Fwd_Packets',
    'Total Backward Packets':       'Total_Backward_Packets',
    'Total Length of Fwd Packets':  'Total_Length_of_Fwd_Packets',
    'Total Length of Bwd Packets':  'Total_Length_of_Bwd_Packets',
    'Fwd Packet Length Max':        'Fwd_Packet_Length_Max',
    'Fwd Packet Length Min':        'Fwd_Packet_Length_Min',
    'Fwd Packet Length Mean':       'Fwd_Packet_Length_Mean',
    'Fwd Packet Length Std':        'Fwd_Packet_Length_Std',
    'Bwd Packet Length Max':        'Bwd_Packet_Length_Max',
    'Bwd Packet Length Min':        'Bwd_Packet_Length_Min',
    'Bwd Packet Length Mean':       'Bwd_Packet_Length_Mean',
    'Bwd Packet Length Std':        'Bwd_Packet_Length_Std',
    'Flow Bytes/s':                 'Flow_Bytes_s',
    'Flow Packets/s':               'Flow_Packets_s',
    'Flow IAT Mean':                'Flow_IAT_Mean',
    'Flow IAT Std':                 'Flow_IAT_Std',
    'Flow IAT Max':                 'Flow_IAT_Max',
    'Flow IAT Min':                 'Flow_IAT_Min',
    'Fwd IAT Total':                'Fwd_IAT_Total',
    'Fwd IAT Mean':                 'Fwd_IAT_Mean',
    'Fwd IAT Std':                  'Fwd_IAT_Std',
    'Fwd IAT Max':                  'Fwd_IAT_Max',
    'Fwd IAT Min':                  'Fwd_IAT_Min',
    'Bwd IAT Total':                'Bwd_IAT_Total',
    'Bwd IAT Mean':                 'Bwd_IAT_Mean',
    'Bwd IAT Std':                  'Bwd_IAT_Std',
    'Bwd IAT Max':                  'Bwd_IAT_Max',
    'Bwd IAT Min':                  'Bwd_IAT_Min',
    'Fwd PSH Flags':                'Fwd_PSH_Flags',
    'Fwd URG Flags':                'Fwd_URG_Flags',
    'Fwd Header Length':            'Fwd_Header_Length',
    'Bwd Header Length':            'Bwd_Header_Length',
    'Fwd Packets/s':                'Fwd_Packets_s',
    'Bwd Packets/s':                'Bwd_Packets_s',
    'Min Packet Length':            'Min_Packet_Length',
    'Max Packet Length':            'Max_Packet_Length',
    'Packet Length Mean':           'Packet_Length_Mean',
    'Packet Length Std':            'Packet_Length_Std',
    'Packet Length Variance':       'Packet_Length_Variance',
    'FIN Flag Count':               'FIN_Flag_Count',
    'SYN Flag Count':               'SYN_Flag_Count',
    'RST Flag Count':               'RST_Flag_Count',
    'PSH Flag Count':               'PSH_Flag_Count',
    'ACK Flag Count':               'ACK_Flag_Count',
    'URG Flag Count':               'URG_Flag_Count',
    'CWE Flag Count':               'CWE_Flag_Count',
    'ECE Flag Count':               'ECE_Flag_Count',
    'Down/Up Ratio':                'Down_Up_Ratio',
    'Average Packet Size':          'Average_Packet_Size',
    'Avg Fwd Segment Size':         'Avg_Fwd_Segment_Size',
    'Avg Bwd Segment Size':         'Avg_Bwd_Segment_Size',
    'Subflow Fwd Packets':          'Subflow_Fwd_Packets',
    'Subflow Fwd Bytes':            'Subflow_Fwd_Bytes',
    'Subflow Bwd Packets':          'Subflow_Bwd_Packets',
    'Subflow Bwd Bytes':            'Subflow_Bwd_Bytes',
    'Init_Win_bytes_forward':       'Init_Win_bytes_forward',
    'Init_Win_bytes_backward':      'Init_Win_bytes_backward',
    'act_data_pkt_fwd':             'act_data_pkt_fwd',
    'min_seg_size_forward':         'min_seg_size_forward',
    'Active Mean':                  'Active_Mean',
    'Active Std':                   'Active_Std',
    'Active Max':                   'Active_Max',
    'Active Min':                   'Active_Min',
    'Idle Mean':                    'Idle_Mean',
    'Idle Std':                     'Idle_Std',
    'Idle Max':                     'Idle_Max',
    'Idle Min':                     'Idle_Min',
    'Label':                        'Label',
}

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

WEB_ATTACK_LABELS = {
    'Web Attack \x96 Brute Force',
    'Web Attack \xef\xbf\xbd Brute Force',
    'Web Attack – Brute Force',
    'Web Attack \x96 XSS',
    'Web Attack \xef\xbf\xbd XSS',
    'Web Attack – XSS',
    'Web Attack \x96 Sql Injection',
    'Web Attack \xef\xbf\xbd Sql Injection',
    'Web Attack – Sql Injection',
}


def compute_port_categories(df):
    port = df['_dst_port_tmp'].astype(float).fillna(0).astype(int)
    df['Port_Is_Web']          = port.isin([80, 443, 8080, 8443, 8888]).astype(int)
    df['Port_Is_RemoteAccess'] = port.isin([21, 22, 23, 2222, 3389]).astype(int)
    df['Port_Is_WellKnown']    = (port <= 1023).astype(int)
    df['Port_Is_Registered']   = ((port > 1023) & (port <= 49151)).astype(int)
    df['Port_Is_Ephemeral']    = (port > 49151).astype(int)
    return df


def compute_custom_features(df):
    flow_duration = df['Flow_Duration'].astype(float).replace(0, 1)
    tot_fwd_pkts  = df['Total_Fwd_Packets'].astype(float)

    df['Custom_Fwd_Pkt_Rate']  = (tot_fwd_pkts / (flow_duration / 1e6)).fillna(0)
    flow_iat_max = df['Flow_IAT_Max'].astype(float).replace(0, 1)
    df['Custom_Slow_Index']    = (flow_duration / flow_iat_max).fillna(0)
    pkt_len_var  = df['Packet_Length_Variance'].astype(float).replace(0, 1)
    avg_pkt_size = df['Average_Packet_Size'].astype(float).replace(0, 1)
    df['Custom_Pkt_Var_Ratio'] = (pkt_len_var / avg_pkt_size).fillna(0)
    fwd_iat_std  = df['Fwd_IAT_Std'].astype(float).replace(0, 1)
    df['Custom_IAT_Anomaly']   = (df['Flow_IAT_Max'].astype(float) / fwd_iat_std).fillna(0)
    df['Custom_IAT_CV']        = (df['Flow_IAT_Std'].astype(float) /
                                   (df['Flow_IAT_Mean'].astype(float) + 1e-6)).fillna(0)
    tot_bwd_pkts = df['Total_Backward_Packets'].astype(float)
    df['Custom_Bwd_Pkt_Ratio'] = (tot_bwd_pkts / (tot_fwd_pkts + 1e-6)).fillna(0)
    min_pkt = df['Min_Packet_Length'].astype(float)
    max_pkt = df['Max_Packet_Length'].astype(float).replace(0, 1)
    df['Custom_Pkt_Size_Ratio'] = (min_pkt / (max_pkt + 1e-6)).fillna(0)
    return df


def main():
    print("=" * 55)
    print("  CIC WebAttack Mapper — V8.5")
    print("=" * 55)

    print(f"\n[*] Đọc CIC Thursday file...")
    df = pd.read_csv(CIC_RAW_PATH)
    # Thursday: strip để đồng nhất
    df.columns = df.columns.str.strip()
    print(f"    Tổng rows: {len(df):,} | Columns: {len(df.columns)}")

    print(f"\n[*] Label distribution gốc:")
    label_col = [c for c in df.columns if c.lower() == 'label'][0]
    print(df[label_col].value_counts().to_string())

    # Rename
    df.rename(columns={k: v for k, v in CIC_TO_TESTBED.items() if k in df.columns},
              inplace=True)

    # Chuẩn hoá label — CIC Thursday có ký tự đặc biệt trong dấu "–"
    df['Label'] = df['Label'].str.strip()

    # Lọc tất cả Web Attack (bất kể sub-type)
    is_web_attack = df['Label'].str.contains('Web Attack', case=False, na=False)
    df_wa = df[is_web_attack].copy()
    print(f"\n[*] Tổng WebAttack flows: {len(df_wa):,}")
    print(df_wa['Label'].value_counts().to_string())

    # Chuẩn hoá nhãn → "Web Attack"
    df_wa['Label'] = 'Web Attack'

    # Port categories
    if '_dst_port_tmp' in df_wa.columns:
        df_wa = compute_port_categories(df_wa)
        df_wa.drop(columns=['_dst_port_tmp'], inplace=True)
    else:
        print("    [!] Không tìm thấy Destination Port — Port_Is_* = 0")
        for col in ['Port_Is_Web','Port_Is_RemoteAccess','Port_Is_WellKnown',
                    'Port_Is_Registered','Port_Is_Ephemeral']:
            df_wa[col] = 0

    # Custom features
    df_wa = compute_custom_features(df_wa)

    # Clean
    df_wa.replace([np.inf, -np.inf], np.nan, inplace=True)
    before = len(df_wa)
    df_wa.dropna(subset=EXPECTED_FEATURES_80, inplace=True)
    if before != len(df_wa):
        print(f"[*] Xoá {before - len(df_wa)} NaN/Inf rows → còn {len(df_wa):,}")

    # Verify features
    missing = [f for f in EXPECTED_FEATURES_80 if f not in df_wa.columns]
    if missing:
        print(f"[!] Thiếu {len(missing)} features: {missing}")
        for f in missing:
            df_wa[f] = 0.0
    else:
        print(f"[+] Đủ 80 features ✓")

    # Save
    output_cols = EXPECTED_FEATURES_80 + ['Label']
    df_wa[output_cols].to_csv(OUTPUT_PATH, index=False)
    print(f"\n[+] Saved: {OUTPUT_PATH} ({len(df_wa):,} rows)")

    print("\n=== Verify ===")
    print(f"Label: {df_wa['Label'].value_counts().to_dict()}")
    print(f"Port_Is_Web mean     : {df_wa['Port_Is_Web'].mean():.3f} (kỳ vọng cao — HTTP/HTTPS)")
    print(f"Flow_Duration mean   : {df_wa['Flow_Duration'].mean():.0f} μs")
    print(f"PSH_Flag_Count mean  : {df_wa['PSH_Flag_Count'].mean():.2f}")


if __name__ == '__main__':
    main()
