"""
BƯỚC 5 — Chia benign THẬT thành 3 phần CỐ ĐỊNH (seed 42) để tránh rò rỉ train/test.

Pool = benign_real (50,721) + benign_val (12,680) = 63,401 flow (cột CICFlowMeter thô).
Chia:  train-mix 40,000  |  val 11,700  |  test 11,701.
  - b5_benign_train.csv : TRỘN vào Combined_V8_5 lúc train (nhãn Benign).
  - b5_benign_val.csv   : tinh chỉnh / calibrate SAU Bước 5 (chọn ngưỡng, fit lại T).
  - b5_benign_test.csv  : ĐO FPR CUỐI — không đụng tới ở bất kỳ bước train/tune nào.

Chạy:  python training/split_benign_b5.py     (từ live_detection/)
"""
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
A = HERE / "data" / "analysis"
SEED = 42
N_TRAIN, N_VAL = 40_000, 11_700          # test = phần còn lại

frames = []
for f in ["benign_real.csv", "benign_val.csv"]:
    df = pd.read_csv(A / f, low_memory=False)
    df.columns = df.columns.str.strip()
    frames.append(df)
pool = pd.concat(frames, ignore_index=True)
pool = pool.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
print(f"[*] Pool benign thật: {len(pool):,} flow, {pool.shape[1]} cột")

train = pool.iloc[:N_TRAIN]
val = pool.iloc[N_TRAIN:N_TRAIN + N_VAL]
test = pool.iloc[N_TRAIN + N_VAL:]

for name, part in [("b5_benign_train", train), ("b5_benign_val", val), ("b5_benign_test", test)]:
    part.to_csv(A / f"{name}.csv", index=False)
    print(f"[+] {name}.csv: {len(part):,} flow -> {A / (name + '.csv')}")

# kiểm không trùng (đảm bảo test sạch)
assert len(train) + len(val) + len(test) == len(pool)
print("[✓] Chia xong. b5_benign_test KHÔNG được dùng cho train/tune.")
