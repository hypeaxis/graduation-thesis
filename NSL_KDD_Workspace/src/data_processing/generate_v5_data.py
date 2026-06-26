"""Generate v5 preprocessed data: v2 base + drift-invariant features.

New features (computed on raw values BEFORE scaling):
  no_data_transfer   = (dst_bytes < 2000)  -- fires 99% guess_passwd, 10% warezmaster
  failed_login_ratio = num_failed_logins / count.clip(1)

Output:
  data/processed/cleaned5Grouped_v5_KddTrain+.csv  (124 features + label)
  data/processed/cleaned5Grouped_v5_KddTest+.csv
  models/artifacts_preprocess_v5/  (scaler, feature_columns, label_groups)
"""

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(WORKSPACE / 'src' / 'data_processing'))

from preprocessing_pipeline import (  # noqa: E402
    fit_train_preprocessor,
    run_schema_sanity_checks,
    transform_test_with_preprocessor,
)

TRAIN_TXT   = WORKSPACE / 'data/raw/KDDTrain+.txt'
TEST_TXT    = WORKSPACE / 'data/raw/KDDTest+.txt'
TRAIN_V5    = WORKSPACE / 'data/processed/cleaned5Grouped_v5_KddTrain+.csv'
TEST_V5     = WORKSPACE / 'data/processed/cleaned5Grouped_v5_KddTest+.csv'
ARTIFACTS   = WORKSPACE / 'models/artifacts_preprocess_v5'


def main():
    print('=== Generating v5 data (drift-invariant features) ===\n')
    print('Features added: no_data_transfer, failed_login_ratio\n')

    print('[1/3] Fitting on train...')
    fit_train_preprocessor(str(TRAIN_TXT), str(TRAIN_V5), str(ARTIFACTS), data_version='v5')

    print('\n[2/3] Transforming test...')
    transform_test_with_preprocessor(str(TEST_TXT), str(TEST_V5), str(ARTIFACTS), data_version='v5')

    print('\n[3/3] Schema sanity check...')
    run_schema_sanity_checks(str(TRAIN_V5), str(TEST_V5))

    # Quick feature verification
    import pandas as pd
    tr = pd.read_csv(TRAIN_V5)
    te = pd.read_csv(TEST_V5)
    print(f'\nFeatures added: {[c for c in tr.columns if c in ("no_data_transfer","failed_login_ratio")]}')
    print(f'Train shape: {tr.shape}   Test shape: {te.shape}')
    # Check R2L class
    tr_r2l = tr[tr['label'] == 3]
    te_r2l = te[te['label'] == 3]
    print(f'\nno_data_transfer:')
    print(f'  train R2L mean = {tr_r2l["no_data_transfer"].mean():.4f}')
    print(f'  test  R2L mean = {te_r2l["no_data_transfer"].mean():.4f}')
    print(f'failed_login_ratio:')
    print(f'  train R2L mean = {tr_r2l["failed_login_ratio"].mean():.4f}')
    print(f'  test  R2L mean = {te_r2l["failed_login_ratio"].mean():.4f}')
    print('\nDone.')


if __name__ == '__main__':
    main()
