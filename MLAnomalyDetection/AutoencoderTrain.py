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
df = pd.read_csv("cleaned5Grouped_KddTrain+.csv")

# Binary labels: Normal = 0, Attack = 1
df['binary_label'] = df['label'].apply(lambda x: 0 if x == 0 else 1)
X = df.drop(['label', 'binary_label'], axis=1)
y = df['binary_label']

# Normalize
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X)

# Use only Normal samples to train the Autoencoder
X_train = X_scaled[y == 0]

# Keep the entire test set
X_test = X_scaled
y_test = y.values

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

# === Save the trained model and scaler for future use ===
import pickle
autoencoder.save("autoencoder_model.h5")
with open("scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)
print("Model saved as 'autoencoder_model.h5' and scaler saved as 'scaler.pkl'")

# === Calculate reconstruction error ===
X_test_pred = autoencoder.predict(X_test)
mse = np.mean(np.power(X_test - X_test_pred, 2), axis=1)

# === Find the optimal threshold based on ROC ===
fpr, tpr, thresholds = roc_curve(y_test, mse)
optimal_idx = np.argmax(tpr - fpr)
optimal_threshold = thresholds[optimal_idx]
print(f"\nOptimal Threshold = {optimal_threshold:.6f}")

# === Classify based on the threshold ===
y_pred = (mse > optimal_threshold).astype(int)

# === Evaluation ===
print("\n=== Autoencoder Binary Classification Report ===")
print(classification_report(y_test, y_pred))
print("AUC Score:", roc_auc_score(y_test, mse))

# === (Optional) Plot ROC Curve ===
plt.figure(figsize=(6, 5))
plt.plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_test, mse):.4f}")
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve - Autoencoder")
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()
