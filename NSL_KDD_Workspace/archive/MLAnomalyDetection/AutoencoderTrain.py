import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, roc_curve
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.callbacks import EarlyStopping
import matplotlib.pyplot as plt

# === Load & prepare data ===
train_df = pd.read_csv("../cleaned5Grouped_v2_KddTrain+.csv")
test_df = pd.read_csv("../cleaned5Grouped_v2_KddTest+.csv")

# Binary labels: Normal = 0, Attack = 1
train_df['binary_label'] = train_df['label'].apply(lambda x: 0 if x == 0 else 1)
test_df['binary_label'] = test_df['label'].apply(lambda x: 0 if x == 0 else 1)

X_train_full = train_df.drop(['label', 'binary_label'], axis=1)
y_train_full = train_df['binary_label']

X_test_full = test_df.drop(['label', 'binary_label'], axis=1)
y_test = test_df['binary_label'].values

# Normalize
scaler = MinMaxScaler()
X_train_scaled = scaler.fit_transform(X_train_full)
X_test_scaled = scaler.transform(X_test_full)

# Use only Normal samples to train the Autoencoder
X_train = X_train_scaled[y_train_full == 0]

X_test_for_threshold = X_train_scaled
y_test_for_threshold = y_train_full.values

# Keep the entire test set
X_test = X_test_scaled

# === Build a deep Autoencoder ===
input_dim = X_train.shape[1]
input_layer = Input(shape=(input_dim,))

# Encoder (Deep)
encoded = Dense(128, activation='relu')(input_layer)
encoded = Dense(64, activation='relu')(encoded)
encoded = Dense(32, activation='relu')(encoded)

# Bottleneck
bottleneck = Dense(16, activation='relu')(encoded)

# Decoder (Deep)
decoded = Dense(32, activation='relu')(bottleneck)
decoded = Dense(64, activation='relu')(decoded)
decoded = Dense(128, activation='relu')(decoded)
decoded = Dense(input_dim, activation='sigmoid')(decoded)

autoencoder = Model(inputs=input_layer, outputs=decoded)
autoencoder.compile(optimizer='adam', loss='mse')

# === Train ===
early_stop = EarlyStopping(monitor='loss', patience=5, restore_best_weights=True)
history = autoencoder.fit(X_train, X_train,
                          epochs=100,
                          batch_size=256,
                          shuffle=True,
                          validation_split=0.1,
                          verbose=1,
                          callbacks=[early_stop])

# === Calculate reconstruction error on train set to find threshold ===
X_train_full_pred = autoencoder.predict(X_test_for_threshold)
mse_train = np.mean(np.power(X_test_for_threshold - X_train_full_pred, 2), axis=1)

# === Find the optimal threshold based on ROC ===
fpr_train, tpr_train, thresholds_train = roc_curve(y_test_for_threshold, mse_train)
optimal_idx = np.argmax(tpr_train - fpr_train)
optimal_threshold = thresholds_train[optimal_idx]
print(f"\nOptimal Threshold (from Train set) = {optimal_threshold:.6f}")

# === Calculate reconstruction error on Test set ===
X_test_pred = autoencoder.predict(X_test)
mse_test = np.mean(np.power(X_test - X_test_pred, 2), axis=1)

# === Classify based on the threshold ===
y_pred = (mse_test > optimal_threshold).astype(int)

# === Evaluation ===
print("\n=== Autoencoder Binary Classification Report (TEST SET) ===")
print(classification_report(y_test, y_pred))
print("AUC Score:", roc_auc_score(y_test, mse_test))

autoencoder.save("autoencoder_v2_best.h5")
print("Model saved to autoencoder_v2_best.h5")

# === (Optional) Plot ROC Curve ===
fpr, tpr, thresholds = roc_curve(y_test, mse_test)
plt.figure(figsize=(6, 5))
plt.plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_test, mse_test):.4f}")
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve - Autoencoder")
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()
