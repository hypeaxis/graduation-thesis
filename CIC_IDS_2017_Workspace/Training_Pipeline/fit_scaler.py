import pandas as pd
import pickle
import os
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE

print("Loading train chunk...")
df = pd.read_csv('processed_data/cic_train_chunk.csv')
X = df.drop(columns=['Label']).values
y = df['Label'].values

print("Applying SMOTE strategy...")
label_counts = pd.Series(y).value_counts()
max_count = label_counts.max()
strategy = {label: max(50000, count) for label, count in label_counts.items()}
strategy[label_counts.idxmax()] = max_count

smote = SMOTE(sampling_strategy=strategy, random_state=42)
X_res, y_res = smote.fit_resample(X, y)

print("Fitting StandardScaler...")
scaler = StandardScaler()
scaler.fit(X_res)

os.makedirs('../Final_Product/models', exist_ok=True)
with open('../Final_Product/models/cic_scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)
print("Saved scaler to ../Final_Product/models/cic_scaler.pkl")
