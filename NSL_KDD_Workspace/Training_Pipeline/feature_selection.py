import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier

def main():
    base_dir = Path(__file__).resolve().parent
    data_path = base_dir / 'cleaned5Grouped_v2_KddTrain+.csv'
    artifacts_dir = base_dir / 'artifacts_preprocess'
    feature_columns_path = artifacts_dir / 'feature_columns.json'
    
    if not data_path.exists():
        print(f"Data file not found at {data_path}")
        return
        
    print("Loading training data...")
    df = pd.read_csv(data_path)
    
    X = df.drop(columns=['label']).to_numpy()
    y = df['label'].to_numpy()
    
    with open(feature_columns_path, 'r', encoding='utf-8') as f:
        feature_names = json.load(f)
        
    print(f"Training RandomForest on {X.shape[0]} samples with {X.shape[1]} features...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    
    importances = rf.feature_importances_
    
    # Sort features by importance
    indices = np.argsort(importances)[::-1]
    sorted_features = [feature_names[i] for i in indices]
    sorted_importances = importances[indices]
    
    # We want to select the top 90 features
    top_n = 90
    selected_features = sorted_features[:top_n]
    dropped_features = sorted_features[top_n:]
    
    print(f"\nTop 10 features:")
    for i in range(10):
        print(f"{i+1}. {sorted_features[i]} ({sorted_importances[i]:.4f})")
        
    print(f"\nDropped {len(dropped_features)} features. Below are some dropped features:")
    for i in range(min(10, len(dropped_features))):
        print(f"- {dropped_features[i]}")
    
    # Save selected features to JSON
    out_path = artifacts_dir / 'selected_features.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(selected_features, f, indent=2)
        
    print(f"\nSelected features saved to {out_path}")
    
    # Plot feature importances (top 30 and bottom 30)
    plt.figure(figsize=(15, 10))
    
    plt.subplot(1, 2, 1)
    plt.barh(range(30), sorted_importances[:30][::-1])
    plt.yticks(range(30), sorted_features[:30][::-1])
    plt.title('Top 30 Feature Importances')
    
    plt.subplot(1, 2, 2)
    plt.barh(range(30), sorted_importances[-30:][::-1])
    plt.yticks(range(30), sorted_features[-30:][::-1])
    plt.title('Bottom 30 Feature Importances')
    
    plt.tight_layout()
    plot_path = artifacts_dir / 'feature_importances.png'
    plt.savefig(plot_path, dpi=300)
    print(f"Plot saved to {plot_path}")

if __name__ == '__main__':
    main()
