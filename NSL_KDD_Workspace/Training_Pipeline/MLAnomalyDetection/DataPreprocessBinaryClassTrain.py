import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Define column names
columns = ['duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes',
    'land', 'wrong_fragment', 'urgent', 'hot', 'num_failed_logins', 'logged_in',
    'num_compromised', 'root_shell', 'su_attempted', 'num_root', 'num_file_creations',
    'num_shells', 'num_access_files', 'num_outbound_cmds', 'is_host_login',
    'is_guest_login', 'count', 'srv_count', 'serror_rate', 'srv_serror_rate',
    'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate',
    'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count',
    'dst_host_same_srv_rate', 'dst_host_diff_srv_rate',
    'dst_host_same_src_port_rate', 'dst_host_srv_diff_host_rate',
    'dst_host_serror_rate', 'dst_host_srv_serror_rate',
    'dst_host_rerror_rate', 'dst_host_srv_rerror_rate',
    'label', 'difficulty_level']

# Read data
df = pd.read_csv('./KDDTrain+.txt', names=columns)

# Basic preprocessing
df.dropna(inplace=True)
df.drop_duplicates(inplace=True)
df = df[df['duration'] >= 0]

# One-hot encoding for categorical columns
df = pd.get_dummies(df, columns=['protocol_type', 'service', 'flag'])

# Group labels into 2 categories: 0 = Normal, 1 = Attack
df['label'] = df['label'].apply(lambda x: 0 if x == 'normal' else 1)

# Separate and normalize data
X = df.drop(['label', 'difficulty_level'], axis=1)
y = df['label']

scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)
X = pd.DataFrame(X_scaled, columns=X.columns)

# Combine and save
df_cleaned = X.copy()
df_cleaned['label'] = y.values
df_cleaned.to_csv("cleanedBinary_KddTrain+.csv", index=False)

print("Saved cleanedBinary_KddTrain+.csv")
