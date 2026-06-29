import os
import sys
import numpy as np
import pandas as pd
import torch
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

try:
    from models.phase2_ft_transformer_v2 import FTTransformer
except ImportError:
    print("Cannot import FTTransformer.")

from hybrid_feature_scaler import HybridFeatureScaler

EXPECTED_FEATURES_80 = [
    'Flow_Duration', 'Total_Fwd_Packets', 'Total_Backward_Packets', 'Total_Length_of_Fwd_Packets', 
    'Total_Length_of_Bwd_Packets', 'Fwd_Packet_Length_Max', 'Fwd_Packet_Length_Min', 'Fwd_Packet_Length_Mean', 
    'Fwd_Packet_Length_Std', 'Bwd_Packet_Length_Max', 'Bwd_Packet_Length_Min', 'Bwd_Packet_Length_Mean', 
    'Bwd_Packet_Length_Std', 'Flow_Bytes_s', 'Flow_Packets_s', 'Flow_IAT_Mean', 'Flow_IAT_Std', 'Flow_IAT_Max', 
    'Flow_IAT_Min', 'Fwd_IAT_Total', 'Fwd_IAT_Mean', 'Fwd_IAT_Std', 'Fwd_IAT_Max', 'Fwd_IAT_Min', 'Bwd_IAT_Total', 
    'Bwd_IAT_Mean', 'Bwd_IAT_Std', 'Bwd_IAT_Max', 'Bwd_IAT_Min', 'Fwd_PSH_Flags', 'Fwd_URG_Flags', 'Fwd_Header_Length', 
    'Bwd_Header_Length', 'Fwd_Packets_s', 'Bwd_Packets_s', 'Min_Packet_Length', 'Max_Packet_Length', 'Packet_Length_Mean', 
    'Packet_Length_Std', 'Packet_Length_Variance', 'FIN_Flag_Count', 'SYN_Flag_Count', 'RST_Flag_Count', 'PSH_Flag_Count', 
    'ACK_Flag_Count', 'URG_Flag_Count', 'CWE_Flag_Count', 'ECE_Flag_Count', 'Down_Up_Ratio', 'Average_Packet_Size', 
    'Avg_Fwd_Segment_Size', 'Avg_Bwd_Segment_Size', 'Subflow_Fwd_Packets', 'Subflow_Fwd_Bytes', 'Subflow_Bwd_Packets', 
    'Subflow_Bwd_Bytes', 'Init_Win_bytes_forward', 'Init_Win_bytes_backward', 'act_data_pkt_fwd', 'min_seg_size_forward', 
    'Active_Mean', 'Active_Std', 'Active_Max', 'Active_Min', 'Idle_Mean', 'Idle_Std', 'Idle_Max', 'Idle_Min', 
    'Port_Is_Web', 'Port_Is_RemoteAccess', 'Port_Is_WellKnown', 'Port_Is_Registered', 'Port_Is_Ephemeral', 
    'Custom_Fwd_Pkt_Rate', 'Custom_Slow_Index', 'Custom_Pkt_Var_Ratio', 'Custom_IAT_Anomaly',
    'Custom_IAT_CV', 'Custom_Bwd_Pkt_Ratio', 'Custom_Pkt_Size_Ratio'
]

def map_cicflowmeter_v4_to_v3(df):
    mapping = {
        'Dst Port': 'Destination_Port', 'Flow Duration': 'Flow_Duration', 'Total Fwd Packet': 'Total_Fwd_Packets',
        'Total Bwd packets': 'Total_Backward_Packets', 'Total Length of Fwd Packet': 'Total_Length_of_Fwd_Packets',
        'Total Length of Bwd Packet': 'Total_Length_of_Bwd_Packets', 'Fwd Packet Length Max': 'Fwd_Packet_Length_Max',
        'Fwd Packet Length Min': 'Fwd_Packet_Length_Min', 'Fwd Packet Length Mean': 'Fwd_Packet_Length_Mean',
        'Fwd Packet Length Std': 'Fwd_Packet_Length_Std', 'Bwd Packet Length Max': 'Bwd_Packet_Length_Max',
        'Bwd Packet Length Min': 'Bwd_Packet_Length_Min', 'Bwd Packet Length Mean': 'Bwd_Packet_Length_Mean',
        'Bwd Packet Length Std': 'Bwd_Packet_Length_Std', 'Flow Bytes/s': 'Flow_Bytes_s', 'Flow Packets/s': 'Flow_Packets_s',
        'Flow IAT Mean': 'Flow_IAT_Mean', 'Flow IAT Std': 'Flow_IAT_Std', 'Flow IAT Max': 'Flow_IAT_Max', 'Flow IAT Min': 'Flow_IAT_Min',
        'Fwd IAT Total': 'Fwd_IAT_Total', 'Fwd IAT Mean': 'Fwd_IAT_Mean', 'Fwd IAT Std': 'Fwd_IAT_Std', 'Fwd IAT Max': 'Fwd_IAT_Max',
        'Fwd IAT Min': 'Fwd_IAT_Min', 'Bwd IAT Total': 'Bwd_IAT_Total', 'Bwd IAT Mean': 'Bwd_IAT_Mean', 'Bwd IAT Std': 'Bwd_IAT_Std',
        'Bwd IAT Max': 'Bwd_IAT_Max', 'Bwd IAT Min': 'Bwd_IAT_Min', 'Fwd PSH Flags': 'Fwd_PSH_Flags', 'Fwd URG Flags': 'Fwd_URG_Flags',
        'Fwd Header Length': 'Fwd_Header_Length', 'Bwd Header Length': 'Bwd_Header_Length', 'Fwd Packets/s': 'Fwd_Packets_s',
        'Bwd Packets/s': 'Bwd_Packets_s', 'Packet Length Min': 'Min_Packet_Length', 'Packet Length Max': 'Max_Packet_Length',
        'Packet Length Mean': 'Packet_Length_Mean', 'Packet Length Std': 'Packet_Length_Std', 'Packet Length Variance': 'Packet_Length_Variance',
        'FIN Flag Count': 'FIN_Flag_Count', 'SYN Flag Count': 'SYN_Flag_Count', 'RST Flag Count': 'RST_Flag_Count', 'PSH Flag Count': 'PSH_Flag_Count',
        'ACK Flag Count': 'ACK_Flag_Count', 'URG Flag Count': 'URG_Flag_Count', 'CWR Flag Count': 'CWE_Flag_Count', 'ECE Flag Count': 'ECE_Flag_Count',
        'Down/Up Ratio': 'Down_Up_Ratio', 'Average Packet Size': 'Average_Packet_Size', 'Fwd Segment Size Avg': 'Avg_Fwd_Segment_Size',
        'Bwd Segment Size Avg': 'Avg_Bwd_Segment_Size', 'Subflow Fwd Packets': 'Subflow_Fwd_Packets', 'Subflow Fwd Bytes': 'Subflow_Fwd_Bytes',
        'Subflow Bwd Packets': 'Subflow_Bwd_Packets', 'Subflow Bwd Bytes': 'Subflow_Bwd_Bytes', 'FWD Init Win Bytes': 'Init_Win_bytes_forward',
        'Bwd Init Win Bytes': 'Init_Win_bytes_backward', 'Fwd Act Data Pkts': 'act_data_pkt_fwd', 'Fwd Seg Size Min': 'min_seg_size_forward',
        'Active Mean': 'Active_Mean', 'Active Std': 'Active_Std', 'Active Max': 'Active_Max', 'Active Min': 'Active_Min', 'Idle Mean': 'Idle_Mean',
        'Idle Std': 'Idle_Std', 'Idle Max': 'Idle_Max', 'Idle Min': 'Idle_Min',
    }
    df.rename(columns=mapping, inplace=True)
    return df

def get_embeddings(model, X_scaled, device, batch_size=512):
    """
    Trích xuất embedding từ FTTransformer (tương tự như get_embeddings trong phase2_ft_transformer_v2.py)
    """
    model.eval()
    X_tensor = torch.FloatTensor(X_scaled).to(device)
    all_emb = []
    
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                # Lấy đầu ra của embedding layer + class token
                x = model.feature_embedding(batch)
                # Đưa qua các block transformer
                for block in model.transformer_blocks:
                    x = block(x)
                # Lấy riêng embedding của CLS token (chiều 0)
                cls_embedding = x[:, 0, :]
                cls_embedding = model.norm(cls_embedding)
            all_emb.append(cls_embedding.cpu().numpy())
            
    return np.vstack(all_emb)

def main():
    print("=========================================================")
    print("5B. VISUALIZE EMBEDDING (T-SNE) CHO DOMAIN ALIGNMENT")
    print("=========================================================")

    TESTBED_DATA_PATH = '../data/Cleaned_Labeled_Dataset_run5.csv'
    CIC_DATA_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../data/processed/cic_test_full.csv'))
    
    SCALER_PATH = '../models/v4_hybrid_pipeline.pkl'
    MODEL_PATH = '../models/v4_hybrid_model.pt'
    ENCODER_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/encoder_stage1.pkl'))
    
    # 1. NẠP VÀ LẤY MẪU
    encoder = joblib.load(ENCODER_PATH)
    
    print("[*] Nạp Testbed run5 (validation split)...")
    df_tb = pd.read_csv(TESTBED_DATA_PATH)
    df_tb.columns = df_tb.columns.str.strip()
    df_tb = map_cicflowmeter_v4_to_v3(df_tb)
    df_tb = df_tb[df_tb['Label'].isin(encoder.classes_)]
    
    from sklearn.model_selection import train_test_split
    _, df_tb_val = train_test_split(df_tb, test_size=0.2, random_state=42, stratify=df_tb['Label'])
    
    # Lấy 15k mẫu từ Testbed (giữ nguyên phân phối để thực tế)
    df_tb_sample = df_tb_val.sample(n=min(15000, len(df_tb_val)), random_state=42)
    df_tb_sample['Domain'] = 'Testbed_Run5_Val'
    
    print("[*] Nạp CIC-IDS-2017 test...")
    df_cic = pd.read_csv(CIC_DATA_PATH)
    if 'Label_Stage1' in df_cic.columns:
        df_cic['Label'] = df_cic['Label_Stage1']
    elif 'Label' not in df_cic.columns:
        df_cic['Label'] = 'Benign'
        
    df_cic = df_cic[df_cic['Label'].isin(encoder.classes_)]
    
    # Tính 3 feature mới cho CIC (vì file cic_test_full có thể chưa có)
    # Rút gọn vì 3 feature đã được tính trong 3_feature_engineering_v2.py
    # Nhưng nếu thiếu thì gán 0
    df_cic.replace([np.inf, -np.inf], 0, inplace=True)
    df_cic.fillna(0, inplace=True)
    
    # Lấy 15k mẫu từ CIC
    df_cic_sample = df_cic.sample(n=min(15000, len(df_cic)), random_state=42)
    df_cic_sample['Domain'] = 'CIC_IDS_2017'
    
    # Gộp chung
    df_combined = pd.concat([df_tb_sample, df_cic_sample], ignore_index=True)
    df_combined.replace([np.inf, -np.inf], 0, inplace=True)
    df_combined.fillna(0, inplace=True)
    
    for c in EXPECTED_FEATURES_80:
        if c not in df_combined.columns:
            df_combined[c] = 0
            
    X_raw = df_combined[EXPECTED_FEATURES_80].values
    y_labels = df_combined['Label'].values
    domains = df_combined['Domain'].values
    
    # 2. TRANSFORM
    print("[*] Transform dữ liệu...")
    scaler = HybridFeatureScaler.load(SCALER_PATH)
    X_scaled = scaler.transform(X_raw)
    
    # 3. TRÍCH XUẤT EMBEDDING
    print("[*] Lấy Embeddings từ model...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
    model.to(device)
    
    embeddings = get_embeddings(model, X_scaled, device=device)
    
    # 4. T-SNE
    print(f"[*] Chạy t-SNE trên {len(embeddings)} mẫu (sẽ mất khoảng 1-2 phút)...")
    tsne = TSNE(n_components=2, random_state=42, n_iter=1000, init='pca', n_jobs=-1)
    tsne_results = tsne.fit_transform(embeddings)
    
    # 5. VISUALIZE
    print("[*] Vẽ biểu đồ...")
    df_tsne = pd.DataFrame({
        'TSNE_1': tsne_results[:, 0],
        'TSNE_2': tsne_results[:, 1],
        'Label': y_labels,
        'Domain': domains
    })
    
    os.makedirs('../docs/figures', exist_ok=True)
    
    # Plot 1: Tô màu theo Label
    plt.figure(figsize=(12, 8))
    sns.scatterplot(
        x='TSNE_1', y='TSNE_2',
        hue='Label',
        style='Domain',
        data=df_tsne,
        alpha=0.6,
        s=20
    )
    plt.title('t-SNE Visualization: Model Embeddings (Colored by Attack Label)')
    plt.savefig('../docs/figures/tsne_labels.png')
    plt.close()
    
    # Plot 2: Tô màu theo Domain
    plt.figure(figsize=(12, 8))
    sns.scatterplot(
        x='TSNE_1', y='TSNE_2',
        hue='Domain',
        data=df_tsne,
        palette=['blue', 'red'],
        alpha=0.5,
        s=15
    )
    plt.title('t-SNE Visualization: Domain Alignment (CIC-IDS vs Testbed)')
    plt.savefig('../docs/figures/tsne_domains.png')
    plt.close()
    
    print("[+] Hoàn thành! Đã lưu biểu đồ tại '../docs/figures/tsne_labels.png' và 'tsne_domains.png'")

if __name__ == "__main__":
    main()
