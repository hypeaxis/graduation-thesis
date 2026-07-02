import os
import glob
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import PowerTransformer
from tqdm import tqdm

# ⚠️ Sửa cho khớp máy bạn, hoặc đặt biến môi trường CIC_RAW_DIR / CIC_PROCESSED_DIR
#    (xem ../../HUONG_DAN_CHAY.md). Mặc định trỏ tương đối vào data/ của GĐ2.
RAW_DATA_DIR = os.environ.get("CIC_RAW_DIR", "data/raw")
OUTPUT_DIR = os.environ.get("CIC_PROCESSED_DIR", "data/processed")

STAGE2_FEATURES = [
    'Port_Is_Web', 'Port_Is_RemoteAccess', 'Port_Is_WellKnown',
    'Port_Is_Registered', 'Port_Is_Ephemeral',
    'Flow_IAT_Max', 'Flow_IAT_Min', 'Flow_IAT_Mean', 'Flow_IAT_Std',
    'Fwd_IAT_Max', 'Fwd_IAT_Std',
    'Packet_Length_Variance', 'Packet_Length_Std', 'Packet_Length_Mean',
    'Average_Packet_Size', 'Fwd_Packet_Length_Max',
    'Flow_Duration', 'Flow_Bytes_s',
    'Custom_Pkt_Var_Ratio', 'Custom_IAT_Anomaly'
]

def clean_column_names(df):
    df.columns = [col.strip().replace(' ', '_').replace('/', '_') for col in df.columns]
    return df

def create_port_categories(df):
    print("  -> Extracting Port Categories...")
    if 'Destination_Port' not in df.columns:
        print("Cảnh báo: Không tìm thấy cột Destination_Port.")
        return df
        
    port = df['Destination_Port'].astype(int)
    
    df['Port_Is_Web'] = port.isin([80, 443, 8080, 8443, 8888]).astype(int)
    df['Port_Is_RemoteAccess'] = port.isin([21, 22, 23, 2222, 3389]).astype(int)
    df['Port_Is_WellKnown'] = (port <= 1023).astype(int)
    df['Port_Is_Registered'] = ((port > 1023) & (port <= 49151)).astype(int)
    df['Port_Is_Ephemeral'] = (port > 49151).astype(int)
    
    # Drop original port column to prevent memorization
    df.drop(columns=['Destination_Port'], inplace=True)
    return df

def extract_custom_features(df):
    print("  -> Extracting Flow-based Custom Features...")
    flow_duration = df['Flow_Duration'].astype(float).replace(0, 1)
    tot_fwd_pkts = df['Total_Fwd_Packets'].astype(float)
    
    df['Custom_Fwd_Pkt_Rate'] = (tot_fwd_pkts / (flow_duration / 1e6)).fillna(0)
    
    flow_iat_max = df['Flow_IAT_Max'].astype(float).replace(0, 1)
    df['Custom_Slow_Index'] = (flow_duration / flow_iat_max).fillna(0)
    
    if 'Packet_Length_Variance' in df.columns and 'Average_Packet_Size' in df.columns:
        pkt_len_var = df['Packet_Length_Variance'].astype(float).replace(0, 1)
        avg_pkt_size = df['Average_Packet_Size'].astype(float).replace(0, 1)
        df['Custom_Pkt_Var_Ratio'] = (pkt_len_var / avg_pkt_size).fillna(0)
    else:
        df['Custom_Pkt_Var_Ratio'] = 0
        
    if 'Fwd_IAT_Std' in df.columns:
        fwd_iat_std = df['Fwd_IAT_Std'].astype(float).replace(0, 1)
        df['Custom_IAT_Anomaly'] = (df['Flow_IAT_Max'].astype(float) / fwd_iat_std).fillna(0)
    else:
        df['Custom_IAT_Anomaly'] = 0
    
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)
    return df

def group_labels_stage1(df):
    mapping = {
        'BENIGN': 'Benign',
        'DoS Hulk': 'DoS', 'DoS GoldenEye': 'DoS',
        'DoS slowloris': 'DoS', 'DoS Slowhttptest': 'DoS',
        'DDoS': 'DDoS', 'PortScan': 'PortScan',
        'FTP-Patator': 'Brute Force', 'SSH-Patator': 'Brute Force',
        'Web Attack.*Brute Force': 'Suspicious',
        'Web Attack.*XSS': 'Suspicious',
        'Web Attack.*Sql Injection': 'Suspicious',
        'Web Attack': 'Suspicious',
        'Bot': 'Suspicious', 'Infiltration': 'Suspicious', 'Heartbleed': 'Suspicious'
    }
    df['Label_Stage1'] = df['Label'].replace({
        'Web Attack.*Brute Force': 'Suspicious',
        'Web Attack.*XSS': 'Suspicious',
        'Web Attack.*Sql Injection': 'Suspicious'
    }, regex=True)
    df['Label_Stage1'] = df['Label_Stage1'].map(mapping).fillna('Suspicious')
    return df

def group_labels_stage2(df):
    mapping = {
        'BENIGN': 'Benign',
        'Web Attack.*Brute Force': 'Web Attack',
        'Web Attack.*XSS': 'Web Attack',
        'Web Attack.*Sql Injection': 'Web Attack',
        'Web Attack': 'Web Attack',
        'Bot': 'Rare Attacks', 'Infiltration': 'Rare Attacks', 'Heartbleed': 'Rare Attacks'
    }
    df['Label_Stage2'] = df['Label'].replace({
        'Web Attack.*Brute Force': 'Web Attack',
        'Web Attack.*XSS': 'Web Attack',
        'Web Attack.*Sql Injection': 'Web Attack'
    }, regex=True)
    df['Label_Stage2'] = df['Label_Stage2'].map(mapping)
    return df

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_files = glob.glob(os.path.join(RAW_DATA_DIR, "*.csv"))
    
    if not csv_files:
        print(f"Không tìm thấy file CSV nào tại {RAW_DATA_DIR}")
        return

    print("="*60)
    print("1. ĐÁNH GIÁ VÀ XỬ LÝ DỮ LIỆU CIC-IDS-2017")
    print("="*60)
    
    dfs = []
    for f in tqdm(csv_files, desc="Đọc file CSV"):
        df_temp = pd.read_csv(f, encoding='cp1252', on_bad_lines='skip', low_memory=False)
        dfs.append(df_temp)
        
    full_df = pd.concat(dfs, ignore_index=True)
    full_df = clean_column_names(full_df)
    
    print("-> Xử lý các giá trị Infinity...")
    numeric_cols = full_df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if np.isinf(full_df[col]).any():
            max_finite = full_df.loc[np.isfinite(full_df[col]), col].max()
            if pd.isna(max_finite): max_finite = 0
            full_df[col].replace([np.inf, -np.inf], max_finite, inplace=True)
            
    full_df.dropna(inplace=True)
    
    print("-> Loại bỏ các đặc trưng rác (Zero Variance)...")
    stds = full_df[numeric_cols].std()
    zero_var_cols = stds[stds == 0].index.tolist()
    if zero_var_cols:
        full_df.drop(columns=zero_var_cols, inplace=True)
        
    # Tạo Port Categories trước khi loại bỏ Fwd_Header_Length.1
    full_df = create_port_categories(full_df)
    
    leakage_cols = ['Fwd_Header_Length.1']
    cols_to_drop = [c for c in leakage_cols if c in full_df.columns]
    if cols_to_drop:
        print(f"-> Loại bỏ các cột gây rò rỉ dữ liệu (Data Leakage): {cols_to_drop}")
        full_df.drop(columns=cols_to_drop, inplace=True)
        
    full_df = extract_custom_features(full_df)
    
    print(f"\nKích thước tập dữ liệu sau tiền xử lý: {full_df.shape[0]:,} dòng, {full_df.shape[1]} cột")
    
    label_col = 'Label'
    if label_col not in full_df.columns:
        print("Không tìm thấy cột Label!")
        return
        
    # Gán nhãn cho 2 stages
    full_df = group_labels_stage1(full_df)
    full_df = group_labels_stage2(full_df)
    
    print("\n" + "="*60)
    print("2. CHIA CHUNKS VÀ FIT POWER TRANSFORMER")
    print("="*60)
    
    print("Lấy mẫu Stratified (300,000 dòng Train)...")
    train_size_target = min(300000, int(len(full_df) * 0.8))
    
    train_indices = []
    test_pool_indices = []
    
    # Chia theo nhãn gốc để đảm bảo phân phối ban đầu
    labels_array = full_df['Label'].values
    unique_labels = np.unique(labels_array)
    
    np.random.seed(42)
    for label in unique_labels:
        group_indices = np.where(labels_array == label)[0]
        np.random.shuffle(group_indices)
        ratio = len(group_indices) / len(labels_array)
        n_train = max(1, int(train_size_target * ratio))
        train_indices.extend(group_indices[:n_train])
        test_pool_indices.extend(group_indices[n_train:])
        
    np.random.shuffle(train_indices)
    np.random.shuffle(test_pool_indices)
    train_indices = train_indices[:train_size_target]
    
    train_df = full_df.iloc[train_indices].copy()
    test_df = full_df.iloc[test_pool_indices].copy()
    
    # Lưu test chung (có Label gốc)
    test_path = os.path.join(OUTPUT_DIR, "cic_test_full.csv")
    test_df.to_csv(test_path, index=False)
    print(f"Đã lưu TEST chung: {test_path} ({len(test_df):,} dòng)")
    
    # --- STAGE 1 ---
    train_stage1 = train_df.drop(columns=['Label', 'Label_Stage2'])
    train_stage1.rename(columns={'Label_Stage1': 'Label'}, inplace=True)
    path_stage1 = os.path.join(OUTPUT_DIR, "cic_train_stage1.csv")
    train_stage1.to_csv(path_stage1, index=False)
    print(f"Đã lưu TRAIN Stage 1: {path_stage1} ({len(train_stage1):,} dòng)")
    
    feature_cols_stage1 = [c for c in train_stage1.columns if c != 'Label']
    print("Fitting PowerTransformer (Stage 1)...")
    pt_stage1 = PowerTransformer(method='yeo-johnson', standardize=True)
    pt_stage1.fit(train_stage1[feature_cols_stage1].values)
    joblib.dump(pt_stage1, os.path.join(OUTPUT_DIR, 'scaler_stage1.pkl'))
    
    # --- STAGE 2 ---
    stage2_mask = train_df['Label_Stage2'].notna()
    train_stage2 = train_df[stage2_mask].copy()
    train_stage2 = train_stage2[STAGE2_FEATURES + ['Label_Stage2']]
    train_stage2.rename(columns={'Label_Stage2': 'Label'}, inplace=True)
    path_stage2 = os.path.join(OUTPUT_DIR, "cic_train_stage2.csv")
    train_stage2.to_csv(path_stage2, index=False)
    print(f"Đã lưu TRAIN Stage 2: {path_stage2} ({len(train_stage2):,} dòng)")
    
    print("Fitting PowerTransformer (Stage 2)...")
    pt_stage2 = PowerTransformer(method='yeo-johnson', standardize=True)
    pt_stage2.fit(train_stage2[STAGE2_FEATURES].values)
    joblib.dump(pt_stage2, os.path.join(OUTPUT_DIR, 'scaler_stage2.pkl'))
    
    print("\nHOÀN TẤT XỬ LÝ DỮ LIỆU!")

if __name__ == "__main__":
    main()
