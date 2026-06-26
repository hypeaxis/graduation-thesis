"""Generate data v4: v2 (122 features) + AE reconstruction error (1 feature) = 123 features.

The autoencoder is trained on normal-only traffic to detect anomalies.
Instead of using it as a hard gate, we append its reconstruction error
as an input feature so the FT-Transformer can weigh it itself.

This lifts the recall ceiling imposed by the hard gate: R2L/U2R samples
that look "normal" to the AE (low MSE) previously got blocked; now the
FT-Transformer sees that low-MSE signal alongside the other features and
can still classify them correctly if other features are discriminative.
"""

import json
import pickle
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

WORKSPACE = Path(__file__).resolve().parent.parent.parent
AE_PATH    = WORKSPACE / 'Final_Product' / 'models' / 'autoencoder_v2_best.h5'
V2_TRAIN   = WORKSPACE / 'data' / 'processed' / 'cleaned5Grouped_v2_KddTrain+.csv'
V2_TEST    = WORKSPACE / 'data' / 'processed' / 'cleaned5Grouped_v2_KddTest+.csv'
ARTIFACTS_V2 = WORKSPACE / 'models' / 'artifacts_preprocess'
ARTIFACTS_V4 = WORKSPACE / 'models' / 'artifacts_preprocess_v4'
V4_TRAIN   = WORKSPACE / 'data' / 'processed' / 'cleaned5Grouped_v4_KddTrain+.csv'
V4_TEST    = WORKSPACE / 'data' / 'processed' / 'cleaned5Grouped_v4_KddTest+.csv'
AE_FEATURE_NAME = 'ae_recon_error'


def compute_ae_mse(ae: tf.keras.Model, X: np.ndarray) -> np.ndarray:
    X_pred = ae.predict(X, batch_size=2048, verbose=0)
    return np.mean(np.power(X.astype(np.float32) - X_pred, 2), axis=1)


def main() -> None:
    print('Loading AE model...')
    ae = tf.keras.models.load_model(str(AE_PATH), compile=False)
    print(f'  AE input dim: {ae.input_shape[1]}')

    with open(ARTIFACTS_V2 / 'feature_columns.json') as f:
        feature_cols = json.load(f)

    assert len(feature_cols) == ae.input_shape[1], (
        f'Feature count mismatch: {len(feature_cols)} vs AE input {ae.input_shape[1]}'
    )

    for split, in_path, out_path in [
        ('train', V2_TRAIN, V4_TRAIN),
        ('test',  V2_TEST,  V4_TEST),
    ]:
        print(f'\nProcessing {split}...')
        df = pd.read_csv(in_path)
        X = df[feature_cols].values.astype(np.float32)
        mse = compute_ae_mse(ae, X)

        df_out = df.copy()
        label_col = df_out.pop('label')
        df_out[AE_FEATURE_NAME] = mse.astype(np.float32)
        df_out['label'] = label_col

        df_out.to_csv(out_path, index=False)
        print(f'  Saved {out_path.name}: shape={df_out.shape}')
        print(f'  ae_recon_error  min={mse.min():.6f}  median={np.median(mse):.6f}  max={mse.max():.6f}')

    # Save artifacts_v4: copy v2 artifacts and update feature_columns.json
    ARTIFACTS_V4.mkdir(parents=True, exist_ok=True)
    for fname in ('scaler.pkl', 'label_groups.json', 'label_map.json'):
        shutil.copy2(ARTIFACTS_V2 / fname, ARTIFACTS_V4 / fname)

    feature_cols_v4 = feature_cols + [AE_FEATURE_NAME]
    with open(ARTIFACTS_V4 / 'feature_columns.json', 'w') as f:
        json.dump(feature_cols_v4, f, indent=2)

    print(f'\nArtifacts saved to {ARTIFACTS_V4}')
    print(f'Total features: {len(feature_cols_v4)} (122 original + 1 ae_recon_error)')


if __name__ == '__main__':
    main()
