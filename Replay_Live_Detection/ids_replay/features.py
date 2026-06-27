"""Trích đặc trưng + tiện ích flow — Single Responsibility: CSV CICFlowMeter → ma trận 80 feature."""
from __future__ import annotations

from datetime import datetime as _dt

import numpy as np
import pandas as pd

EXPECTED_FEATURES_80 = [
    'Flow_Duration', 'Total_Fwd_Packets', 'Total_Backward_Packets', 'Total_Length_of_Fwd_Packets', 'Total_Length_of_Bwd_Packets', 'Fwd_Packet_Length_Max', 'Fwd_Packet_Length_Min', 'Fwd_Packet_Length_Mean', 'Fwd_Packet_Length_Std', 'Bwd_Packet_Length_Max', 'Bwd_Packet_Length_Min', 'Bwd_Packet_Length_Mean', 'Bwd_Packet_Length_Std', 'Flow_Bytes_s', 'Flow_Packets_s', 'Flow_IAT_Mean', 'Flow_IAT_Std', 'Flow_IAT_Max', 'Flow_IAT_Min', 'Fwd_IAT_Total', 'Fwd_IAT_Mean', 'Fwd_IAT_Std', 'Fwd_IAT_Max', 'Fwd_IAT_Min', 'Bwd_IAT_Total', 'Bwd_IAT_Mean', 'Bwd_IAT_Std', 'Bwd_IAT_Max', 'Bwd_IAT_Min', 'Fwd_PSH_Flags', 'Fwd_URG_Flags', 'Fwd_Header_Length', 'Bwd_Header_Length', 'Fwd_Packets_s', 'Bwd_Packets_s', 'Min_Packet_Length', 'Max_Packet_Length', 'Packet_Length_Mean', 'Packet_Length_Std', 'Packet_Length_Variance', 'FIN_Flag_Count', 'SYN_Flag_Count', 'RST_Flag_Count', 'PSH_Flag_Count', 'ACK_Flag_Count', 'URG_Flag_Count', 'CWE_Flag_Count', 'ECE_Flag_Count', 'Down_Up_Ratio', 'Average_Packet_Size', 'Avg_Fwd_Segment_Size', 'Avg_Bwd_Segment_Size', 'Subflow_Fwd_Packets', 'Subflow_Fwd_Bytes', 'Subflow_Bwd_Packets', 'Subflow_Bwd_Bytes', 'Init_Win_bytes_forward', 'Init_Win_bytes_backward', 'act_data_pkt_fwd', 'min_seg_size_forward', 'Active_Mean', 'Active_Std', 'Active_Max', 'Active_Min', 'Idle_Mean', 'Idle_Std', 'Idle_Max', 'Idle_Min', 'Port_Is_Web', 'Port_Is_RemoteAccess', 'Port_Is_WellKnown', 'Port_Is_Registered', 'Port_Is_Ephemeral', 'Custom_Fwd_Pkt_Rate', 'Custom_Slow_Index', 'Custom_Pkt_Var_Ratio', 'Custom_IAT_Anomaly', 'Custom_IAT_CV', 'Custom_Bwd_Pkt_Ratio', 'Custom_Pkt_Size_Ratio',
]

CICFLOW_MAP = {
    'Dst Port': 'Destination_Port', 'Flow Duration': 'Flow_Duration', 'Total Fwd Packet': 'Total_Fwd_Packets', 'Total Bwd packets': 'Total_Backward_Packets', 'Total Length of Fwd Packet': 'Total_Length_of_Fwd_Packets', 'Total Length of Bwd Packet': 'Total_Length_of_Bwd_Packets', 'Fwd Packet Length Max': 'Fwd_Packet_Length_Max', 'Fwd Packet Length Min': 'Fwd_Packet_Length_Min', 'Fwd Packet Length Mean': 'Fwd_Packet_Length_Mean', 'Fwd Packet Length Std': 'Fwd_Packet_Length_Std', 'Bwd Packet Length Max': 'Bwd_Packet_Length_Max', 'Bwd Packet Length Min': 'Bwd_Packet_Length_Min', 'Bwd Packet Length Mean': 'Bwd_Packet_Length_Mean', 'Bwd Packet Length Std': 'Bwd_Packet_Length_Std', 'Flow Bytes/s': 'Flow_Bytes_s', 'Flow Packets/s': 'Flow_Packets_s', 'Flow IAT Mean': 'Flow_IAT_Mean', 'Flow IAT Std': 'Flow_IAT_Std', 'Flow IAT Max': 'Flow_IAT_Max', 'Flow IAT Min': 'Flow_IAT_Min', 'Fwd IAT Total': 'Fwd_IAT_Total', 'Fwd IAT Mean': 'Fwd_IAT_Mean', 'Fwd IAT Std': 'Fwd_IAT_Std', 'Fwd IAT Max': 'Fwd_IAT_Max', 'Fwd IAT Min': 'Fwd_IAT_Min', 'Bwd IAT Total': 'Bwd_IAT_Total', 'Bwd IAT Mean': 'Bwd_IAT_Mean', 'Bwd IAT Std': 'Bwd_IAT_Std', 'Bwd IAT Max': 'Bwd_IAT_Max', 'Bwd IAT Min': 'Bwd_IAT_Min', 'Fwd PSH Flags': 'Fwd_PSH_Flags', 'Fwd URG Flags': 'Fwd_URG_Flags', 'Fwd Header Length': 'Fwd_Header_Length', 'Bwd Header Length': 'Bwd_Header_Length', 'Fwd Packets/s': 'Fwd_Packets_s', 'Bwd Packets/s': 'Bwd_Packets_s', 'Packet Length Min': 'Min_Packet_Length', 'Packet Length Max': 'Max_Packet_Length', 'Packet Length Mean': 'Packet_Length_Mean', 'Packet Length Std': 'Packet_Length_Std', 'Packet Length Variance': 'Packet_Length_Variance', 'FIN Flag Count': 'FIN_Flag_Count', 'SYN Flag Count': 'SYN_Flag_Count', 'RST Flag Count': 'RST_Flag_Count', 'PSH Flag Count': 'PSH_Flag_Count', 'ACK Flag Count': 'ACK_Flag_Count', 'URG Flag Count': 'URG_Flag_Count', 'CWR Flag Count': 'CWE_Flag_Count', 'ECE Flag Count': 'ECE_Flag_Count', 'Down/Up Ratio': 'Down_Up_Ratio', 'Average Packet Size': 'Average_Packet_Size', 'Fwd Segment Size Avg': 'Avg_Fwd_Segment_Size', 'Bwd Segment Size Avg': 'Avg_Bwd_Segment_Size', 'Subflow Fwd Packets': 'Subflow_Fwd_Packets', 'Subflow Fwd Bytes': 'Subflow_Fwd_Bytes', 'Subflow Bwd Packets': 'Subflow_Bwd_Packets', 'Subflow Bwd Bytes': 'Subflow_Bwd_Bytes', 'FWD Init Win Bytes': 'Init_Win_bytes_forward', 'Bwd Init Win Bytes': 'Init_Win_bytes_backward', 'Fwd Act Data Pkts': 'act_data_pkt_fwd', 'Fwd Seg Size Min': 'min_seg_size_forward', 'Active Mean': 'Active_Mean', 'Active Std': 'Active_Std', 'Active Max': 'Active_Max', 'Active Min': 'Active_Min', 'Idle Mean': 'Idle_Mean', 'Idle Std': 'Idle_Std', 'Idle Max': 'Idle_Max', 'Idle Min': 'Idle_Min',
}


class FeatureExtractor:
    """Chuyển DataFrame CICFlowMeter (raw) → ma trận 80 feature đúng thứ tự model cần."""

    features = EXPECTED_FEATURES_80

    def build(self, df: pd.DataFrame) -> np.ndarray:
        df = df.copy()
        df.columns = df.columns.str.strip()
        df.rename(columns=CICFLOW_MAP, inplace=True)
        p = df['Destination_Port'].astype(int)
        df['Port_Is_Web'] = p.isin([80, 443, 8080, 8443, 8888]).astype(int)
        df['Port_Is_RemoteAccess'] = p.isin([21, 22, 23, 2222, 3389]).astype(int)
        df['Port_Is_WellKnown'] = (p <= 1023).astype(int)
        df['Port_Is_Registered'] = ((p > 1023) & (p <= 49151)).astype(int)
        df['Port_Is_Ephemeral'] = (p > 49151).astype(int)
        fd = df['Flow_Duration'].astype(float).replace(0, 1)
        df['Custom_Fwd_Pkt_Rate'] = (df['Total_Fwd_Packets'].astype(float) / (fd / 1e6)).fillna(0)
        df['Custom_Slow_Index'] = (fd / df['Flow_IAT_Max'].astype(float).replace(0, 1)).fillna(0)
        df['Custom_Pkt_Var_Ratio'] = (df['Packet_Length_Variance'].astype(float).replace(0, 1) /
                                      df['Average_Packet_Size'].astype(float).replace(0, 1)).fillna(0)
        df['Custom_IAT_Anomaly'] = (df['Flow_IAT_Max'].astype(float) /
                                    df['Fwd_IAT_Std'].astype(float).replace(0, 1)).fillna(0)
        df['Custom_IAT_CV'] = (df['Flow_IAT_Std'].astype(float) /
                               (df['Flow_IAT_Mean'].astype(float) + 1e-6)).fillna(0)
        df['Custom_Bwd_Pkt_Ratio'] = (df['Total_Backward_Packets'].astype(float) /
                                      (df['Total_Fwd_Packets'].astype(float) + 1e-6)).fillna(0)
        df['Custom_Pkt_Size_Ratio'] = (df['Min_Packet_Length'].astype(float) /
                                       (df['Max_Packet_Length'].astype(float) + 1e-6)).fillna(0)
        for c in EXPECTED_FEATURES_80:
            if c not in df.columns:
                df[c] = 0
        X = df[EXPECTED_FEATURES_80].values.astype(np.float32)
        return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


def col(df: pd.DataFrame, name: str, default="") -> pd.Series:
    return df[name] if name in df.columns else pd.Series([default] * len(df))


def parse_ts(s) -> float:
    """Timestamp CICFlowMeter → ms epoch (0 nếu lỗi)."""
    s = str(s).strip()
    for fmt in ("%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
        try:
            return _dt.strptime(s, fmt).timestamp() * 1000.0
        except Exception:
            pass
    return 0.0


def port_spread(src_arr, dport_arr, ts_arr, window_ms) -> np.ndarray:
    """Số cổng đích DUY NHẤT theo (src, bucket thời gian) — đặc trưng PortScan."""
    from collections import defaultdict
    n = len(src_arr)
    bucket = (ts_arr // max(window_ms, 1)).astype(np.int64)
    ports = defaultdict(set)
    for i in range(n):
        ports[(src_arr[i], bucket[i])].add(int(dport_arr[i]))
    return np.array([len(ports[(src_arr[i], bucket[i])]) for i in range(n)], dtype=np.int32)
