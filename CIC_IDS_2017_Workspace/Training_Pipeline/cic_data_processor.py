import os
import glob
import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedKFold, train_test_split
from tqdm import tqdm

# Đường dẫn tới thư mục chứa các file pcap_ISCX.csv gốc
RAW_DATA_DIR = "/home/ning/Graduation-Thesis/CIC_IDS_2017_Workspace/Training_Pipeline/raw_data"
OUTPUT_DIR = "/home/ning/Graduation-Thesis/CIC_IDS_2017_Workspace/Training_Pipeline/processed_data"

def clean_column_names(df):
    """Xóa khoảng trắng thừa và ký tự đặc biệt ở tên cột."""
    df.columns = [col.strip().replace(' ', '_').replace('/', '_') for col in df.columns]
    return df

def extract_custom_slow_attack_features(df):
    """
    Thêm các Feature đặc chế dành riêng cho Tấn công chậm (Slow attacks: Slowloris, Slowhttptest).
    Tấn công chậm có đặc điểm: Thời gian kết nối (Flow Duration) rất dài, nhưng tốc độ gửi (Packet Rate) cực thấp.
    """
    print("  -> Đang tính toán Custom Features cho Slow Attacks...")
    
    # Ép kiểu an toàn để tránh chia cho 0
    flow_duration = df['Flow_Duration'].astype(float).replace(0, 1)
    tot_fwd_pkts = df['Total_Fwd_Packets'].astype(float)
    
    # 1. Tốc độ gửi gói tin (Packets per second thực tế của Fwd)
    df['Custom_Fwd_Pkt_Rate'] = (tot_fwd_pkts / (flow_duration / 1e6)).fillna(0)
    
    # 2. Tỷ lệ Packet rate trên IAT Max (Chỉ số nhạy cảm với Slowloris)
    # Slowloris thường giữ IAT (Inter-Arrival Time) rất cao nhưng không để rớt kết nối.
    flow_iat_max = df['Flow_IAT_Max'].astype(float).replace(0, 1)
    df['Custom_Slow_Index'] = (flow_duration / flow_iat_max).fillna(0)
    
    # Xử lý các giá trị vô cực sinh ra do tính toán
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.fillna(0, inplace=True)
    
    return df

def group_labels(df):
    """
    Nhóm 15 nhãn của CIC-IDS-2017 thành 7 nhóm cốt lõi để giải quyết
    vấn đề mất cân bằng dữ liệu cực đoan và cải thiện Macro-F1.
    """
    mapping = {
        'BENIGN': 'Benign',
        'DoS Hulk': 'DoS',
        'DoS GoldenEye': 'DoS',
        'DoS slowloris': 'DoS',
        'DoS Slowhttptest': 'DoS',
        'DDoS': 'DDoS',
        'PortScan': 'PortScan',
        'FTP-Patator': 'Brute Force',
        'SSH-Patator': 'Brute Force',
        'Web Attack \uFFFD Brute Force': 'Web Attack',
        'Web Attack \uFFFD XSS': 'Web Attack',
        'Web Attack \uFFFD Sql Injection': 'Web Attack',
        'Bot': 'Rare Attacks',
        'Infiltration': 'Rare Attacks',
        'Heartbleed': 'Rare Attacks'
    }
    
    # Handle the weird encoding chars in Web Attack if any
    df['Label'] = df['Label'].replace({
        'Web Attack.*Brute Force': 'Web Attack',
        'Web Attack.*XSS': 'Web Attack',
        'Web Attack.*Sql Injection': 'Web Attack'
    }, regex=True)
    
    df['Label'] = df['Label'].map(mapping).fillna('Rare Attacks')
    return df

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    csv_files = glob.glob(os.path.join(RAW_DATA_DIR, "*.csv"))
    
    if not csv_files:
        print(f"Không tìm thấy file CSV nào tại {RAW_DATA_DIR}")
        return

    print("="*60)
    print("1. ĐÁNH GIÁ VÀ GỘP TOÀN BỘ TẬP DỮ LIỆU CIC-IDS-2017")
    print("="*60)
    
    dfs = []
    for f in tqdm(csv_files, desc="Đọc file CSV"):
        # Đọc dữ liệu, bỏ qua các dòng lỗi (engine='python' hoặc on_bad_lines)
        df_temp = pd.read_csv(f, encoding='cp1252', on_bad_lines='skip', low_memory=False)
        dfs.append(df_temp)
        
    full_df = pd.concat(dfs, ignore_index=True)
    full_df = clean_column_names(full_df)
    
    # Xử lý các giá trị Infinity bằng cách gán bằng max_finite của cột thay vì drop
    print("-> Đang xử lý các giá trị Infinity...")
    numeric_cols = full_df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if np.isinf(full_df[col]).any():
            max_finite = full_df.loc[np.isfinite(full_df[col]), col].max()
            if pd.isna(max_finite):
                max_finite = 0
            full_df[col].replace([np.inf, -np.inf], max_finite, inplace=True)
            
    full_df.dropna(inplace=True)
    
    # Loại bỏ các đặc trưng rác (Zero Variance)
    print("-> Loại bỏ các đặc trưng rác (Zero Variance)...")
    stds = full_df[numeric_cols].std()
    zero_var_cols = stds[stds == 0].index.tolist()
    if zero_var_cols:
        print(f"Loại bỏ {len(zero_var_cols)} cột Zero Variance: {zero_var_cols}")
        full_df.drop(columns=zero_var_cols, inplace=True)
    
    print(f"\nKích thước tập dữ liệu gốc: {full_df.shape[0]:,} dòng, {full_df.shape[1]} cột")
    
    # Chuẩn hóa nhãn (Label)
    label_col = 'Label'
    if label_col not in full_df.columns:
        print("Không tìm thấy cột Label!")
        return
        
    print("\nPhân phối các nhãn gốc (Top 10):")
    print(full_df[label_col].value_counts().head(10))
    
    print("\n-> Đang nhóm nhãn (Label Grouping) thành 7 lớp cốt lõi...")
    full_df = group_labels(full_df)
    print("Phân phối sau khi nhóm:")
    print(full_df[label_col].value_counts())

    print("\n" + "="*60)
    print("2. THÊM CUSTOM FEATURES CHO CÁC LỚP ĐẶC BIỆT")
    print("="*60)
    full_df = extract_custom_slow_attack_features(full_df)
    print(f"Số lượng features sau khi thêm: {full_df.shape[1]}")
    
    print("\n" + "="*60)
    print("3. CHIẾN LƯỢC CHUNKING (TÁCH DỮ LIỆU TRAIN / TEST)")
    print("="*60)
    
    # Lấy ra 500,000 dòng cho Train (Sử dụng index shuffling thay vì train_test_split để tránh OOM RAM)
    print("\nTrộn ngẫu nhiên dữ liệu để chia Chunk...")
    
    # Shuffle toàn bộ index
    indices = np.arange(len(full_df))
    np.random.seed(42)
    np.random.shuffle(indices)
    
    # Cắt xuống còn 300,000 dòng theo yêu cầu để train siêu nhanh
    train_size = min(300000, int(len(full_df) * 0.8))
    train_indices = indices[:train_size]
    test_pool_indices = indices[train_size:]
    
    # Lưu tập Train trực tiếp
    train_path = os.path.join(OUTPUT_DIR, "cic_train_chunk.csv")
    full_df.iloc[train_indices].to_csv(train_path, index=False)
    print(f"Đã lưu tập TRAIN: {train_path} ({len(train_indices):,} dòng)")
    
    # Chia phần Test Pool thành 3 Chunk
    print("\nChia Test Pool thành 3 Chunks hoàn toàn không trùng lặp...")
    num_test_chunks = 3
    chunk_size = len(test_pool_indices) // num_test_chunks
    
    for i in range(num_test_chunks):
        start_idx = i * chunk_size
        end_idx = (i + 1) * chunk_size if i < num_test_chunks - 1 else len(test_pool_indices)
        
        chunk_indices = test_pool_indices[start_idx:end_idx]
        chunk_path = os.path.join(OUTPUT_DIR, f"cic_test_chunk_{i+1}.csv")
        full_df.iloc[chunk_indices].to_csv(chunk_path, index=False)
        print(f"Đã lưu tập TEST CHUNK {i+1}: {chunk_path} ({len(chunk_indices):,} dòng)")
        
    print("\nHOÀN TẤT! Dữ liệu đã sẵn sàng cho Model mới.")

if __name__ == "__main__":
    main()
