"""Gom CSV live (cfm) -> benign_real.csv + benign_val.csv, kiem chat luong.
Chay:  python training/consolidate_benign.py            (tu thu muc live_detection/)
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent          # = live_detection/
SRC_DIRS = [HERE / "data" / "live" / "processed", HERE / "data" / "live"]
OUT_DIR = HERE / "data" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)
VAL_FRAC = 0.20
SEED = 42
LABEL = "Benign"

# 1) gom moi *_Flow.csv (bo file .part dang ghi do)
files = []
for d in SRC_DIRS:
    if d.exists():
        files += [p for p in d.glob("*.csv") if not p.name.endswith(".part")]
if not files:
    sys.exit("[!] Khong tim thay CSV nao trong data/live/ hay data/live/processed/. Da chay capture chua?")

frames = []
for p in sorted(files):
    try:
        df = pd.read_csv(p, low_memory=False)
        df.columns = df.columns.str.strip()
        if not df.empty:
            frames.append(df)
    except Exception as e:
        print(f"  [bo qua] {p.name}: {e}")
big = pd.concat(frames, ignore_index=True)
print(f"[*] Gom {len(files)} file -> {len(big)} flow, {big.shape[1]} cot")

# 2) kiem chat luong
n_cols = big.shape[1]
print(f"[*] So cot: {n_cols} (dataset train chuan = 84)")
num = big.select_dtypes(include=[np.number])
n_nan = int(num.isna().sum().sum())
n_inf = int(np.isinf(num.to_numpy(dtype=float, na_value=0.0)).sum())
print(f"[*] NaN: {n_nan} | inf: {n_inf}  (feature extractor se nan_to_num, nhung nen biet)")

# 3) gan nhan Benign ca me
big["Label"] = LABEL

# 4) tach train/val (khong lam ban benign bang cach shuffle co seed)
big = big.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
n_val = int(len(big) * VAL_FRAC)
val, train = big.iloc[:n_val], big.iloc[n_val:]

train.to_csv(OUT_DIR / "benign_real.csv", index=False)
val.to_csv(OUT_DIR / "benign_val.csv", index=False)
print(f"[+] benign_real.csv: {len(train)} flow  ->  {OUT_DIR/'benign_real.csv'}")
print(f"[+] benign_val.csv : {len(val)} flow  (giu rieng cho Buoc 2 calibrate)")
if len(big) < 3000:
    print(f"[canh bao] Chi {len(big)} flow (<3000). Nen thu them de calibrate dang tin.")
