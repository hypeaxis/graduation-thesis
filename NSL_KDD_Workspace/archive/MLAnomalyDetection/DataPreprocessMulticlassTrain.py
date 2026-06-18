import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler

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

df = pd.read_csv('./KDDTrain+.txt', names = columns)

# Check for and drop null values
print(df.isnull().sum())
df.dropna(inplace=True)

# Delete duplicate rows
df.drop_duplicates(inplace=True)

# Check for abnormal values
print((df['duration'] < 0).sum())
df = df[df['duration'] >= 0]

# Convert categorical columns to numerical using One-Hot Encoding
categorical_cols = ['protocol_type', 'service', 'flag']
# One-Hot Encoding
df = pd.get_dummies(df, columns=categorical_cols)

# Drop label column for normalization
X = df.drop(['label', 'difficulty_level'], axis=1)
y = df['label']
# Normalization
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)
# Convert back to DataFrame
X = pd.DataFrame(X_scaled, columns=X.columns)

# Convert label column to multiclass classification
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Create a cleaned DataFrame with the processed features and multiclass labels
df_cleaned = X.copy()
df_cleaned['label'] = y_encoded

# Save the cleaned DataFrame to a new CSV file
df_cleaned.to_csv("cleanedMulticlass_KddTrain+.csv", index=False)

label_mapping = dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))
print("Label Mapping:", label_mapping)