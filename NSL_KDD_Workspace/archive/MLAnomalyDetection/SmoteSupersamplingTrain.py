import pandas as pd
from imblearn.over_sampling import SMOTE
from collections import Counter

# Load the preprocessed dataset with grouped labels
df = pd.read_csv("cleanedBinary_KddTrain+.csv")

# Separate features and label
X = df.drop('label', axis=1)
y = df['label']

# Check the initial class distribution
print("Initial class distribution:")
print(Counter(y))

# Select a suitable k based on the smallest class (SMOTE requires >= k+1 samples)
min_class_count = y.value_counts().min()
k_neighbors = min(min_class_count - 1, 5) if min_class_count > 1 else 1

# Apply SMOTE to balance the classes
print(f"\nUsing SMOTE with k_neighbors = {k_neighbors}")
smote = SMOTE(random_state=42, k_neighbors=k_neighbors)
X_resampled, y_resampled = smote.fit_resample(X, y)

# Combine back into a DataFrame
df_resampled = pd.DataFrame(X_resampled, columns=X.columns)
df_resampled['label'] = y_resampled

# Check the distribution after SMOTE
print("\nDistribution after SMOTE:")
print(Counter(y_resampled))

# Save the result to a new file
df_resampled.to_csv("cleanedBinary_KddTrain+_SMOTE.csv", index=False)
print("\nSaved: cleanedBinary_KddTrain+_SMOTE.csv")
