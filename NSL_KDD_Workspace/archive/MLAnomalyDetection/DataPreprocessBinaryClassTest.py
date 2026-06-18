import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

# Load the binary training set to synchronize columns (if any)
train_df = pd.read_csv("cleanedBinary_KddTrain+.csv")
expected_columns = set(train_df.columns) - {"label"}


# Original column names
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

# Read the original test set
df = pd.read_csv('./KDDTest+.txt', names=columns)

# Basic processing
df.dropna(inplace=True)
df.drop_duplicates(inplace=True)
df = df[df['duration'] >= 0]

# One-hot encoding for categorical columns
df = pd.get_dummies(df, columns=['protocol_type', 'service', 'flag'])

# Group labels into 2 categories: 0 = Normal, 1 = Attack
df['label'] = df['label'].apply(lambda x: 0 if x == 'normal' else 1)

# Separate features and labels
X = df.drop(['label', 'difficulty_level'], axis=1)
y = df['label']

# Normalization
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)
X = pd.DataFrame(X_scaled, columns=X.columns)

# Synchronize columns if necessary (compared to the binary training set)
if expected_columns:
    missing_cols = expected_columns - set(X.columns)
    for col in missing_cols:
        X[col] = 0

    extra_cols = set(X.columns) - expected_columns
    X = X.drop(columns=extra_cols)

    X = X[sorted(expected_columns)]  # Sắp xếp theo train

# Combine and save
df_cleaned = X.copy()
df_cleaned['label'] = y
df_cleaned.to_csv("cleanedBinary_KddTest+.csv", index=False)

print("Saved cleanedBinary_KddTest+.csv")
