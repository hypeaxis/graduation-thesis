import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
import matplotlib.pyplot as plt

# Load preprocessed 5-class data
train_df = pd.read_csv('cleaned5Grouped_KddTrain+_SMOTE.csv')
test_df = pd.read_csv('cleaned5Grouped_KddTest+.csv')

# Separate features and labels
X_train = train_df.drop('label', axis=1)
y_train = train_df['label']
X_test = test_df.drop('label', axis=1)
y_test = test_df['label']

# Remove rows with missing labels
nan_mask = y_test.isnull()
if nan_mask.any():
    print(f"Found and dropping {nan_mask.sum()} rows with NaN labels in test data.")
    y_test = y_test.dropna()
    X_test = X_test.loc[y_test.index]

# Synchronize columns between training and testing sets
train_columns = X_train.columns
missing_cols = set(train_columns) - set(X_test.columns)
for col in missing_cols:
    X_test[col] = 0
X_test = X_test[train_columns]

# === Find optimal k using macro F1-score ===
print("Finding optimal K using macro F1-score...")

f1_scores_macro = []
k_range = range(1, 50)
for k in k_range:
    print(f"Testing k = {k}")
    knn = KNeighborsClassifier(n_neighbors=k)
    knn.fit(X_train, y_train)
    y_pred_k = knn.predict(X_test)
    f1_macro = f1_score(y_test, y_pred_k, average='macro', zero_division=0)
    f1_scores_macro.append(f1_macro)

# Select optimal k
optimal_k = k_range[f1_scores_macro.index(max(f1_scores_macro))]
print(f"\nOptimal k: {optimal_k} with macro F1-score: {max(f1_scores_macro):.4f}")

# Plot macro F1-score vs k
plt.figure(figsize=(10, 6))
plt.plot(k_range, f1_scores_macro, marker='o', linestyle='-')
plt.title("Macro F1-score by k Value (5-class classification)")
plt.xlabel('k Value')
plt.ylabel('Macro F1-score')
plt.xticks(k_range)
plt.grid(True)
plt.tight_layout()
plt.show()

# === Train final model with optimal k ===
knn_final = KNeighborsClassifier(n_neighbors=optimal_k)
knn_final.fit(X_train, y_train)
y_pred = knn_final.predict(X_test)

# Evaluation
print("\n=== Final Classification Results (5 classes) ===")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred))
print("\nClassification Report:\n", classification_report(
    y_test, y_pred, target_names=["Normal (0)", "DoS (1)", "Probe (2)", "R2L (3)", "U2R (4)"]))
