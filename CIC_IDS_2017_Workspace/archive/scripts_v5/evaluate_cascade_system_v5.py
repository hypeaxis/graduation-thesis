import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from torch.utils.data import DataLoader, Dataset
from phase2_ft_transformer_v2 import FTTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report
from tqdm import tqdm

class InferenceDataset(Dataset):
    def __init__(self, features):
        self.features = torch.FloatTensor(features)
    def __len__(self): return len(self.features)
    def __getitem__(self, idx): return self.features[idx]

def map_terminal_label(l):
    if not isinstance(l, str): return l
    if 'Web Attack' in l: return 'Web Attack'
    if 'BENIGN' in l: return 'Benign'
    if 'DoS Hulk' in l or 'DoS GoldenEye' in l or 'DoS slowloris' in l or 'DoS Slowhttptest' in l: return 'DoS'
    if 'DDoS' in l: return 'DDoS'
    if 'PortScan' in l: return 'PortScan'
    if 'FTP-Patator' in l or 'SSH-Patator' in l: return 'Brute Force'
    if l in ['Bot', 'Infiltration', 'Heartbleed']: return l
    return l

def main():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    print("Loading Stage 1 Scaler and Encoder...")
    scaler1 = joblib.load('models/v4_cascade/stage1/scaler_stage1.pkl')
    encoder1 = joblib.load('models/v4_cascade/stage1/encoder_stage1.pkl')
    suspicious_idx = list(encoder1.classes_).index('Suspicious')
    
    print("Loading Stage 1 Model...")
    model1 = FTTransformer(num_features=77, num_classes=len(encoder1.classes_), 
                          d_model=128, num_layers=4, num_heads=8, dropout=0.2, drop_path_rate=0.1).to(device)
    model1.load_state_dict(torch.load('models/v4_cascade/stage1/best_stage1_model.pt', map_location=device))
    model1.eval()
    
    print("Loading Stage 2 V7 Ensemble Models...")
    STAGE2_DIR = 'models/v7_cascade/stage2'
    scaler2 = joblib.load(os.path.join(STAGE2_DIR, 'scaler_stage2.pkl'))
    encoder2 = joblib.load(os.path.join(STAGE2_DIR, 'encoder_stage2.pkl'))

    import json
    with open(os.path.join(STAGE2_DIR, 'stage2_features.json'), 'r') as f:
        STAGE2_FEATURES_V7 = json.load(f)

    num_features_s2 = len(STAGE2_FEATURES_V7)
    model2 = FTTransformer(num_features=num_features_s2, num_classes=len(encoder2.classes_), d_model=64, num_layers=3, num_heads=4, dropout=0.2, drop_path_rate=0.1).to(device)
    model2.load_state_dict(torch.load(os.path.join(STAGE2_DIR, 'best_stage2_ema.pt'), map_location=device))
    model2.eval()

    rf_model = joblib.load(os.path.join(STAGE2_DIR, 'best_rf_model.pkl'))
    knn_model = joblib.load(os.path.join(STAGE2_DIR, 'best_knn_model.pkl'))
    
    chunk_size = 200000
    all_y_true = []
    
    all_s1_preds = []
    all_s1_probs = []
    all_mask_stage2 = []
    
    all_ft_preds = []
    all_rf_preds = []
    all_knn_preds = []
    all_ft_probs_max = []
    
    THRESHOLD = 0.85
    
    print("Processing Data in Chunks for Inference...")
    chunk_iter = pd.read_csv('processed_data/cic_test_full.csv', chunksize=chunk_size)
    for i, chunk in enumerate(chunk_iter):
        print(f"\n--- Processing Chunk {i+1} ---")
        chunk.columns = chunk.columns.str.strip()
        chunk.replace([np.inf, -np.inf], 0, inplace=True)
        chunk.fillna(0, inplace=True)
        
        # COMPUTE RATIO FEATURES V7
        chunk['Flow_Bytes_Ratio'] = chunk['Total_Length_of_Fwd_Packets'] / (chunk['Total_Length_of_Bwd_Packets'].replace(0, 1))
        chunk['Flow_Pkts_Ratio'] = chunk['Total_Fwd_Packets'] / (chunk['Total_Backward_Packets'].replace(0, 1))
        chunk['Flow_Bytes_Ratio'] = chunk['Flow_Bytes_Ratio'].replace([np.inf, -np.inf], 0).fillna(0)
        chunk['Flow_Pkts_Ratio'] = chunk['Flow_Pkts_Ratio'].replace([np.inf, -np.inf], 0).fillna(0)
        
        y_true = chunk['Label'].apply(map_terminal_label).values
        all_y_true.extend(y_true)
        
        cols_to_drop = ['Label', 'Label_Stage1', 'Label_Stage2', 'Flow_Bytes_Ratio', 'Flow_Pkts_Ratio']
        feature_cols_s1 = [c for c in chunk.columns if c not in cols_to_drop]
        X_s1_raw = chunk[feature_cols_s1].values
        X_s1_scaled = scaler1.transform(X_s1_raw)
        
        loader1 = DataLoader(InferenceDataset(X_s1_scaled), batch_size=2048, shuffle=False, num_workers=2)
        
        s1_preds = []
        s1_probs = []
        with torch.no_grad():
            for features in loader1:
                features = features.to(device)
                with torch.cuda.amp.autocast():
                    logits = model1(features)
                    probs = torch.softmax(logits, dim=1)
                s1_preds.extend(torch.argmax(logits, dim=1).cpu().numpy())
                s1_probs.extend(probs[:, suspicious_idx].cpu().numpy())
                
        s1_preds = np.array(s1_preds)
        s1_probs = np.array(s1_probs)
        all_s1_preds.append(s1_preds)
        all_s1_probs.append(s1_probs)
        
        mask_stage2 = (s1_preds == suspicious_idx) & (s1_probs >= THRESHOLD)
        all_mask_stage2.append(mask_stage2)
        
        if mask_stage2.sum() > 0:
            df_s2 = chunk[mask_stage2].copy()
            X_s2_raw = df_s2[STAGE2_FEATURES_V7].values
            X_s2_scaled = scaler2.transform(X_s2_raw)
            
            # FT-Transformer
            loader2 = DataLoader(InferenceDataset(X_s2_scaled), batch_size=2048, shuffle=False, num_workers=2)
            ft_preds_idx = []
            ft_probs_max = []
            with torch.no_grad():
                for features in loader2:
                    features = features.to(device)
                    with torch.cuda.amp.autocast():
                        logits = model2(features)
                        probs = torch.softmax(logits, dim=1)
                    max_probs, preds = torch.max(probs, dim=1)
                    ft_preds_idx.extend(preds.cpu().numpy())
                    ft_probs_max.extend(max_probs.cpu().numpy())
                    
            ft_preds_label = encoder2.inverse_transform(ft_preds_idx)
            
            # RF and KNN
            rf_preds_idx = rf_model.predict(X_s2_scaled)
            knn_preds_idx = knn_model.predict(X_s2_scaled)
            rf_preds_label = encoder2.inverse_transform(rf_preds_idx)
            knn_preds_label = encoder2.inverse_transform(knn_preds_idx)
            
            all_ft_preds.append(ft_preds_label)
            all_ft_probs_max.append(np.array(ft_probs_max))
            all_rf_preds.append(rf_preds_label)
            all_knn_preds.append(knn_preds_label)
        else:
            all_ft_preds.append(np.array([]))
            all_ft_probs_max.append(np.array([]))
            all_rf_preds.append(np.array([]))
            all_knn_preds.append(np.array([]))

    print("\nInference Complete! Applying Rule-based Ensemble Voting...")
    
    infiltration_thresholds = [0.65, 0.68, 0.70]
    
    for inf_thresh in infiltration_thresholds:
        all_y_pred_thresh = []
        for i in range(len(all_s1_preds)):
            s1_preds = all_s1_preds[i]
            s1_probs = all_s1_probs[i]
            mask_stage2 = all_mask_stage2[i]
            
            final_preds_chunk = np.empty(len(s1_preds), dtype=object)
            
            mask_not_suspicious = (s1_preds != suspicious_idx)
            final_preds_chunk[mask_not_suspicious] = encoder1.inverse_transform(s1_preds[mask_not_suspicious])
            
            mask_low_prob = (s1_preds == suspicious_idx) & (s1_probs < THRESHOLD)
            final_preds_chunk[mask_low_prob] = 'Benign'
            
            if mask_stage2.sum() > 0:
                ft = all_ft_preds[i]
                rf = all_rf_preds[i]
                knn = all_knn_preds[i]
                ft_prob = all_ft_probs_max[i]
                
                stage2_final = np.empty(len(ft), dtype=object)
                for j in range(len(ft)):
                    if ft[j] == 'Benign':
                        stage2_final[j] = 'Benign'
                    else:
                        # ENSEMBLE RULES
                        # 1. Infiltration Priority
                        if rf[j] == 'Infiltration' or knn[j] == 'Infiltration' or (ft[j] == 'Infiltration' and ft_prob[j] >= inf_thresh):
                            stage2_final[j] = 'Infiltration'
                        # 2. Botnet Consensus (Reduce False Positives)
                        elif ft[j] == 'Bot' and (rf[j] == 'Benign' or knn[j] == 'Benign'):
                            stage2_final[j] = 'Benign'
                        # 3. Soft Threshold check for others
                        elif ft_prob[j] >= 0.65:
                            stage2_final[j] = ft[j]
                        else:
                            stage2_final[j] = 'Benign'
                            
                final_preds_chunk[mask_stage2] = stage2_final
                
            all_y_pred_thresh.extend(final_preds_chunk)
            
        print("\n" + "="*60)
        print(f"EVALUATION AT INFILTRATION THRESHOLD: {inf_thresh}")
        print("="*60)
        report = classification_report(all_y_true, all_y_pred_thresh, digits=4)
        print(report)

        with open(f"final_v7_report_thresh_{inf_thresh}.txt", "w") as f:
            f.write(f"Infiltration Threshold: {inf_thresh}\n\n")
            f.write(report)

if __name__ == "__main__":
    main()
