import os
import json
import torch
import joblib
import argparse
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from phase2_ft_transformer_v2 import FTTransformer

class CascadeNIDS:
    def __init__(self, stage1_dir, stage2_dir, device='cpu'):
        self.device = device
        print("Loading Stage 1 (General Model)...")
        self.scaler1 = joblib.load(os.path.join(stage1_dir, 'scaler_stage1.pkl'))
        self.encoder1 = joblib.load(os.path.join(stage1_dir, 'encoder_stage1.pkl'))
        num_features_s1 = len(self.scaler1.scale_)
        self.stage1 = FTTransformer(num_features=num_features_s1, num_classes=len(self.encoder1.classes_), d_model=128, num_layers=4, num_heads=8).to(device)
        self.stage1.load_state_dict(torch.load(os.path.join(stage1_dir, 'best_stage1_ema.pt'), map_location=device))
        self.stage1.eval()
        
        print("Loading Stage 2 (Expert Model)...")
        self.scaler2 = joblib.load(os.path.join(stage2_dir, 'scaler_stage2.pkl'))
        self.encoder2 = joblib.load(os.path.join(stage2_dir, 'encoder_stage2.pkl'))
        with open(os.path.join(stage2_dir, 'stage2_features.json'), 'r') as f:
            self.stage2_features = json.load(f)
        
        num_features_s2 = len(self.stage2_features)
        self.stage2 = FTTransformer(num_features=num_features_s2, num_classes=len(self.encoder2.classes_), d_model=64, num_layers=3, num_heads=4).to(device)
        self.stage2.load_state_dict(torch.load(os.path.join(stage2_dir, 'best_stage2_ema.pt'), map_location=device))
        self.stage2.eval()
        
    def predict(self, X_raw: np.ndarray, feature_names: list, batch_size=256):
        results = np.empty(len(X_raw), dtype=object)
        
        # --- STAGE 1 ---
        print("Running Stage 1...")
        X_s1 = self.scaler1.transform(X_raw)
        preds_s1_idx = []
        with torch.no_grad():
            for i in range(0, len(X_s1), batch_size):
                batch = torch.FloatTensor(X_s1[i:i+batch_size]).to(self.device)
                logits = self.stage1(batch)
                preds_s1_idx.extend(torch.argmax(logits, dim=1).cpu().numpy())
        labels_s1 = self.encoder1.inverse_transform(preds_s1_idx)
        
        suspicious_mask = (labels_s1 == 'Suspicious')
        
        # Gán nhãn cho các mẫu rõ ràng
        for i in range(len(results)):
            if not suspicious_mask[i]:
                results[i] = labels_s1[i]
                
        # --- STAGE 2 ---
        if suspicious_mask.any():
            print(f"Running Stage 2 for {suspicious_mask.sum()} suspicious samples...")
            sus_idx = np.where(suspicious_mask)[0]
            feat_idx = [feature_names.index(f) for f in self.stage2_features]
            X_sus = X_raw[sus_idx][:, feat_idx]
            X_s2 = self.scaler2.transform(X_sus)
            
            preds_s2_idx = []
            with torch.no_grad():
                for i in range(0, len(X_s2), batch_size):
                    batch = torch.FloatTensor(X_s2[i:i+batch_size]).to(self.device)
                    logits = self.stage2(batch)
                    preds_s2_idx.extend(torch.argmax(logits, dim=1).cpu().numpy())
            labels_s2 = self.encoder2.inverse_transform(preds_s2_idx)
            
            for i, idx in enumerate(sus_idx):
                results[idx] = labels_s2[i]
                
        return results

def evaluate(test_csv):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print("Initializing Cascade NIDS...")
    nids = CascadeNIDS('models/v4_cascade/stage1', 'models/v4_cascade/stage2', device=device)
    
    print(f"Loading Test Data: {test_csv}")
    df_test = pd.read_csv(test_csv)
    y_true_raw = df_test['Label'].values
    
    mapping = {
        'BENIGN': 'Benign', 'DoS Hulk': 'DoS', 'DoS GoldenEye': 'DoS', 'DoS slowloris': 'DoS', 'DoS Slowhttptest': 'DoS',
        'DDoS': 'DDoS', 'PortScan': 'PortScan', 'FTP-Patator': 'Brute Force', 'SSH-Patator': 'Brute Force',
        'Web Attack.*Brute Force': 'Web Attack', 'Web Attack.*XSS': 'Web Attack', 'Web Attack.*Sql Injection': 'Web Attack',
        'Web Attack': 'Web Attack', 'Bot': 'Rare Attacks', 'Infiltration': 'Rare Attacks', 'Heartbleed': 'Rare Attacks'
    }
    y_true = pd.Series(y_true_raw).replace({'Web Attack.*': 'Web Attack'}, regex=True).map(mapping).values
    
    feature_names = df_test.drop(columns=['Label']).columns.tolist()
    X_raw = df_test.drop(columns=['Label']).values
    
    print("Predicting...")
    y_pred = nids.predict(X_raw, feature_names)
    
    print("\n" + "="*60)
    print(" CASCADE EVALUATION RESULTS")
    print("="*60)
    print(classification_report(y_true, y_pred, digits=4))
    macro_f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
    print(f"Overall Macro-F1: {macro_f1:.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluate', action='store_true')
    parser.add_argument('--test-csv', type=str, default='processed_data/cic_test_full.csv')
    args = parser.parse_args()
    
    if args.evaluate:
        evaluate(args.test_csv)
