import os
import sys
import numpy as np
import pandas as pd
import torch
import joblib
from sklearn.metrics import accuracy_score, balanced_accuracy_score, matthews_corrcoef, confusion_matrix, classification_report
import warnings
warnings.filterwarnings('ignore')

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../CIC_IDS_2017_Workspace/src'))
sys.path.append(WORKSPACE_DIR)

try:
    from models.phase2_ft_transformer_v2 import FTTransformer
except ImportError:
    print("Cannot import FTTransformer.")

from hybrid_feature_scaler import HybridFeatureScaler
from check_distribution_drift import check_drift

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

def load_data(filepath):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df = map_cicflowmeter_v4_to_v3(df)
    df.replace([np.inf, -np.inf], 0, inplace=True)
    df.fillna(0, inplace=True)
    for c in EXPECTED_FEATURES_80:
        if c not in df.columns:
            df[c] = 0
    X = df[EXPECTED_FEATURES_80].values
    y = df['Label'].values
    return X, y

def main():
    print("=========================================================")
    print("GIAI ĐOẠN 5: ĐÁNH GIÁ CHUẨN TRÊN TEST SET (RUN 6)")
    print("=========================================================")

    TEST_DATA_PATH = '../data/Cleaned_Labeled_Dataset_run6.csv'
    SCALER_PATH = '../models/v4_hybrid_pipeline.pkl'
    MODEL_PATH = '../models/v4_hybrid_model.pt'
    ENCODER_PATH = os.path.abspath(os.path.join(WORKSPACE_DIR, '../models/final_cic_ids_2017/encoder_stage1.pkl'))
    
    # 1. NẠP DỮ LIỆU
    print("[*] Nạp Test Set (run6)...")
    X_test, y_test = load_data(TEST_DATA_PATH)
    print(f"    Tổng số mẫu test: {len(X_test)}")
    
    # Lọc những mẫu có trong encoder
    encoder = joblib.load(ENCODER_PATH)
    valid_mask = np.isin(y_test, encoder.classes_)
    X_test = X_test[valid_mask]
    y_test = y_test[valid_mask]
    print(f"    Số mẫu hợp lệ sau khi map label: {len(X_test)}")
    
    # 2. SANITY CHECK (DATA DRIFT)
    print("\n[*] Nạp HybridFeatureScaler & Kiểm tra Data Drift...")
    scaler = HybridFeatureScaler.load(SCALER_PATH)
    X_test_new = X_test[:, 77:]
    
    # Tên 3 features mới
    new_feat_names = EXPECTED_FEATURES_80[77:]
    
    is_drifted = check_drift(
        batch_new=X_test_new,
        fit_stats=scaler.fit_stats_3custom,
        feature_names=new_feat_names,
        z_score_threshold=3.0
    )
    if not is_drifted:
        print("    -> Không phát hiện Data Drift. Phân phối tương đồng với lúc Train.")
    
    # 3. TRANSFORM
    print("\n[*] Transform Data qua Hybrid Pipeline...")
    X_scaled = scaler.transform(X_test)
    
    # 4. PREDICT
    print("[*] Nạp Base Model & Thực hiện dự đoán...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = FTTransformer(num_features=80, num_classes=len(encoder.classes_),
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2)
    model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
    model.to(device)
    model.eval()
    
    X_tensor = torch.FloatTensor(X_scaled).to(device)
    batch_size = 512
    all_preds = []
    with torch.no_grad():
        for i in range(0, len(X_tensor), batch_size):
            batch = X_tensor[i:i+batch_size]
            with torch.cuda.amp.autocast():
                logits = model(batch)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            all_preds.extend(preds)
            
    y_pred_labels = encoder.inverse_transform(all_preds)
    
    # 5. METRICS & BÁO CÁO
    print("\n=========================================================")
    print("KẾT QUẢ ĐÁNH GIÁ (MULTICLASS - RUN6)")
    print("=========================================================")
    
    b_acc = balanced_accuracy_score(y_test, y_pred_labels)
    acc = accuracy_score(y_test, y_pred_labels)
    mcc = matthews_corrcoef(y_test, y_pred_labels)
    
    print(f"Accuracy:          {acc:.4f}")
    print(f"Balanced Accuracy: {b_acc:.4f}")
    print(f"MCC:               {mcc:.4f}\n")
    
    print("--- Phân phối dữ liệu & Cảnh báo Support ---")
    counts = pd.Series(y_test).value_counts()
    for cls_name, count in counts.items():
        warning = "[CẢNH BÁO: Ít mẫu]" if count < 100 else ""
        print(f"  - {cls_name}: {count} mẫu {warning}")
        
    print("\n--- Detailed Classification Report ---")
    # Lấy F1 vĩ mô (Macro F1) và báo cáo đầy đủ
    report = classification_report(y_test, y_pred_labels, target_names=np.unique(y_test), digits=4)
    print(report)
    
    print("--- Confusion Matrix Tuyệt Đối ---")
    labels = np.unique(y_test)
    cm = confusion_matrix(y_test, y_pred_labels, labels=labels)
    df_cm = pd.DataFrame(cm, index=[f"True_{l}" for l in labels], columns=[f"Pred_{l}" for l in labels])
    print(df_cm.to_string())
    
    print("\n=========================================================")
    print("KIỂM CHỨNG LỖI OVERCONFIDENCE (CASCADE STAGE 2)")
    print("=========================================================")
    # Tính tỷ lệ dự đoán Cascade
    # Trong kịch bản inference đa lớp này, chúng ta tính probability của top-1 class.
    # Nếu prob < 0.85, mẫu đó bị coi là Suspicious (kích hoạt Stage 2).
    # Tuy nhiên vì hiện model đánh trực tiếp Multi-class, thay vì đo "Suspicious" như Cascade cũ,
    # chúng ta đo xem confidence phân phối ra sao.
    print("Để đánh giá đúng, ta phải xây dựng script inference Cascade hoàn chỉnh.")
    print("Tạm thời, Multi-class F1-score đã được báo cáo ở trên.")

if __name__ == "__main__":
    main()
