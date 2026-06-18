import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# 1. Load datasets (preprocessed and normalized)
train_df = pd.read_csv("cleanedBinary_KddTrain+.csv")
test_df = pd.read_csv("cleanedBinary_KddTest+.csv")

# 2. Split features and labels
X_train = train_df.drop('label', axis=1)
y_train = train_df['label']
X_test = test_df.drop('label', axis=1)
y_test = test_df['label']

# Drop rows with NaN in y_test and corresponding rows in X_test
nan_mask = y_test.isnull()
if nan_mask.any():
    print(f"Found and dropping {nan_mask.sum()} rows with NaN labels in test data.")
    y_test = y_test.dropna()
    X_test = X_test.loc[y_test.index]

# 3. Ensure test set has same columns as training set
train_columns = X_train.columns
missing_cols = set(train_columns) - set(X_test.columns)
for col in missing_cols:
    X_test[col] = 0
X_test = X_test[train_columns]

# 4. Train Random Forest with class weights
rf = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    class_weight='balanced' 
)
rf.fit(X_train, y_train)

# 5. Predict and evaluate
y_pred = rf.predict(X_test)

print("=== Accuracy ===")
print(accuracy_score(y_test, y_pred))

print("\n=== Confusion Matrix ===")
print(confusion_matrix(y_test, y_pred))

print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred, zero_division=0))
