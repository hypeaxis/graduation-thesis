import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline

# === Load preprocessed data with 5 labels ===
train_df = pd.read_csv("cleaned5Grouped_KddTrain+.csv")  # Not oversampled
test_df = pd.read_csv("cleaned5Grouped_KddTest+.csv")

# Separate features and labels
X_train = train_df.drop("label", axis=1)
y_train = train_df["label"]
X_test = test_df.drop("label", axis=1)
y_test = test_df["label"]

# Synchronize columns between train and test sets
missing_cols = set(X_train.columns) - set(X_test.columns)
for col in missing_cols:
    X_test[col] = 0
extra_cols = set(X_test.columns) - set(X_train.columns)
X_test = X_test.drop(columns=extra_cols)
X_test = X_test[X_train.columns]

# Drop NaN labels in the test set
nan_mask = y_test.isnull()
if nan_mask.any():
    print(f"Found and dropping {nan_mask.sum()} rows with NaN labels in test data.")
    y_test = y_test.dropna()
    X_test = X_test.loc[y_test.index]

# === Phase 1: Classify Normal (0) vs Attack (1) ===
y_train_phase1 = (y_train != 0).astype(int)
y_test_phase1 = (y_test != 0).astype(int)

print("\nPhase 1: Resampling & training binary classifier (Normal vs Attack)...")

# SMOTE for phase 1
smote_phase1 = SMOTE(random_state=42)
X_train_p1, y_train_p1 = smote_phase1.fit_resample(X_train, y_train_phase1)

# Train XGBoost for Phase 1
xgb_phase1 = XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss')
xgb_phase1.fit(X_train_p1, y_train_p1)

# Predict for phase 1
y_pred_phase1 = xgb_phase1.predict(X_test)
print(f"{np.sum(y_pred_phase1 == 1)} samples predicted as Attack and passed to Phase 2")

# === Phase 2: Predict only on samples predicted as attack ===
print("\nPhase 2: Resampling & training multiclass classifier for attack types...")

X_train_phase2 = X_train[y_train != 0]
y_train_phase2 = y_train[y_train != 0]

X_test_phase2 = X_test[y_pred_phase1 == 1]
y_test_phase2_true = y_test[y_pred_phase1 == 1]

# Shift attack labels: 1->0, 2->1, 3->2, 4->3
y_train_phase2_shifted = y_train_phase2 - 1

# Resampling for Phase 2: SMOTE + Undersampling
oversample = SMOTE(random_state=42)
undersample = RandomUnderSampler(random_state=42)
pipeline = Pipeline(steps=[('o', oversample), ('u', undersample)])
X_train_p2, y_train_p2 = pipeline.fit_resample(X_train_phase2, y_train_phase2_shifted)

# Train XGBoost for Phase 2
xgb_phase2 = XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='mlogloss')
xgb_phase2.fit(X_train_p2, y_train_p2)

# Predict Phase 2
y_pred_phase2_shifted = xgb_phase2.predict(X_test_phase2)
y_pred_phase2 = y_pred_phase2_shifted + 1

# === Combine results ===
final_preds = []
i_attack = 0
for i in range(len(y_pred_phase1)):
    if y_pred_phase1[i] == 0:
        final_preds.append(0)
    else:
        final_preds.append(y_pred_phase2[i_attack])
        i_attack += 1

# === Evaluation ===
print("\n=== Final Hierarchical Classification Evaluation ===")
print(f"Accuracy: {accuracy_score(y_test, final_preds):.4f}")
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, final_preds))
print("\nClassification Report:")
print(classification_report(y_test, final_preds, target_names=[
    "Normal (0)", "DoS (1)", "Probe (2)", "R2L (3)", "U2R (4)"
]))
