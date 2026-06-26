import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import os

def main():
    print("==================================================")
    print("CHUẨN BỊ DỮ LIỆU RUN 7 (80% TRAIN - 20% TEST)")
    print("==================================================")
    
    input_path = '../../docs/run7_dataset.csv'
    train_path = '../data/run7_train.csv'
    test_path = '../data/run7_test.csv'
    
    print(f"[*] Đọc file gốc từ {input_path}...")
    df = pd.read_csv(input_path)
    df.columns = df.columns.str.strip()
    
    classes = ['Benign', 'Brute Force', 'DoS', 'PortScan', 'Web Attack']
    df = df[df['Label'].isin(classes)]
    
    print(f"[*] Tổng số mẫu hợp lệ: {len(df)}")
    
    print("[*] Chia tập Train (80%) và Test (20%)...")
    df_train, df_test = train_test_split(df, test_size=0.2, random_state=42, stratify=df['Label'])
    
    os.makedirs('../data', exist_ok=True)
    
    print(f"[*] Lưu tập Train ({len(df_train)} mẫu) vào {train_path}...")
    df_train.to_csv(train_path, index=False)
    
    print(f"[*] Lưu tập Test ({len(df_test)} mẫu) vào {test_path}...")
    df_test.to_csv(test_path, index=False)
    
    print("\n--- PHÂN PHỐI TẬP TRAIN ---")
    print(df_train['Label'].value_counts())
    
    print("\n--- PHÂN PHỐI TẬP TEST ---")
    print(df_test['Label'].value_counts())
    
    print("\n[+] Hoàn thành phân chia dữ liệu!")

if __name__ == "__main__":
    main()
