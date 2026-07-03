"""Gom CSV live (cfm) cua PHIEN TAN CONG -> <attack>_real.csv, nhan sach theo IP + thoi gian.

Nguyen tac: phien tan cong la phien RIENG (Phien 2). Chi flow co Src IP == attacker_ip
moi la tan cong; gan nhan theo cua so thoi gian de tach PortScan / DoS / ...

Chay:  python training/consolidate_attack.py            (tu thu muc live_detection/)

Cau hinh o duoi (WINDOWS):
  - De TRONG  -> moi flow co Src IP == attacker_ip nhan DEFAULT_LABEL (phien 1 loai tan cong).
  - Co WINDOWS -> gan nhan theo tung cua so thoi gian; flow attacker ngoai moi cua so bi bo.
Timestamp trong window ghi dang "YYYY-MM-DD HH:MM:SS" (gio local, cung mui voi may capture).
"""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent          # = live_detection/
SRC_DIRS = [HERE / "data" / "live" / "processed", HERE / "data" / "live"]
OUT_DIR = HERE / "data" / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# --- attacker_ip: lay tu replay_config.json (nguon chan ly), cho phep override ---
ATTACKER_IP = None
cfg = HERE / "replay_config.json"
if cfg.exists():
    ATTACKER_IP = json.loads(cfg.read_text()).get("attacker_ip")
ATTACKER_IP = ATTACKER_IP or "192.168.0.106"

DEFAULT_LABEL = "PortScan"     # dung khi WINDOWS de trong

# Moi dong: (nhan, bat_dau, ket_thuc) HOAC (nhan, bat_dau, ket_thuc, dst_port).
#   - dst_port (tuy chon): chi gan nhan cho flow co Dst Port == so nay -> tach sach 2 loai
#     tan cong chay sat gio nhau (vd DoS chi danh 1 cong, PortScan trai nhieu cong).
#   - Xu ly theo THU TU: dong sau ghi de dong truoc o phan trung -> dat loai "hep cong" sau cung.
# Vi du (phien PortScan p1-2000 + DoS flood cong 445, chay sat nhau):
# WINDOWS = [
#     ("PortScan", "2026-07-03 16:59:40", "2026-07-03 17:00:35"),         # ca dai gio, moi cong
#     ("DoS",      "2026-07-03 16:59:40", "2026-07-03 17:00:35", 445),    # cung gio nhung chi cong 445
# ]
WINDOWS = []

# --- ten cot co the khac hoa/khoang trang; chuan hoa de tim ---
def pick(cols, *cands):
    low = {c.lower().strip(): c for c in cols}
    for cand in cands:
        if cand in low:
            return low[cand]
    return None

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

# 2) loc theo attacker_ip (nhan sach: chi flow xuat phat tu may tan cong)
src_col = pick(big.columns, "src ip", "source ip", "src_ip")
ts_col = pick(big.columns, "timestamp", "time stamp")
if src_col is None:
    sys.exit(f"[!] Khong thay cot Src IP trong CSV. Cot hien co: {list(big.columns)[:12]} ...")
print(f"[*] Cot IP nguon: '{src_col}' | cot thoi gian: '{ts_col}'")

atk = big[big[src_col].astype(str).str.strip() == ATTACKER_IP].copy()
print(f"[*] attacker_ip = {ATTACKER_IP}  ->  {len(atk)} flow tan cong (trong tong {len(big)})")
if atk.empty:
    ips = big[src_col].astype(str).str.strip().value_counts().head(8)
    sys.exit(f"[!] 0 flow tu {ATTACKER_IP}. Src IP hay gap:\n{ips}\n"
             f"    -> Kiem attacker_ip trong replay_config.json / IP victim thay sau NAT.")

# 3) gan nhan
if WINDOWS:
    if ts_col is None:
        sys.exit("[!] Co WINDOWS nhung CSV khong co cot Timestamp -> khong the gan nhan theo thoi gian.")
    t = pd.to_datetime(atk[ts_col], errors="coerce", dayfirst=False)
    if t.isna().mean() > 0.5:                         # thu lai dayfirst (cfm co the dd/mm/yyyy)
        t = pd.to_datetime(atk[ts_col], errors="coerce", dayfirst=True)
    dport_col = pick(atk.columns, "dst port", "destination port", "dst_port")
    atk["Label"] = pd.NA
    for entry in WINDOWS:
        name, start, end = entry[0], entry[1], entry[2]
        dport = entry[3] if len(entry) > 3 else None
        m = (t >= pd.Timestamp(start)) & (t <= pd.Timestamp(end))
        if dport is not None:
            if dport_col is None:
                sys.exit("[!] WINDOWS co dst_port nhung CSV khong co cot Dst Port.")
            m &= pd.to_numeric(atk[dport_col], errors="coerce") == int(dport)
        atk.loc[m, "Label"] = name
        tail = f" cong {dport}" if dport is not None else ""
        print(f"    [{name}] {start} -> {end}{tail}: {int(m.sum())} flow")
    n_drop = int(atk["Label"].isna().sum())
    if n_drop:
        print(f"    [bo] {n_drop} flow attacker ngoai moi cua so thoi gian")
    atk = atk[atk["Label"].notna()].copy()
else:
    atk["Label"] = DEFAULT_LABEL
    print(f"[*] WINDOWS trong -> gan het nhan '{DEFAULT_LABEL}'")

if atk.empty:
    sys.exit("[!] Sau khi gan nhan con 0 flow. Kiem lai moc gio trong WINDOWS.")

# 4) kiem chat luong
n_cols = atk.shape[1] - 1                              # tru cot Label vua them
print(f"[*] So cot (khong tinh Label): {n_cols} (dataset train chuan = 84)")
num = atk.select_dtypes(include=[np.number])
n_nan = int(num.isna().sum().sum())
n_inf = int(np.isinf(num.to_numpy(dtype=float, na_value=0.0)).sum())
print(f"[*] NaN: {n_nan} | inf: {n_inf}  (feature extractor se nan_to_num, nhung nen biet)")

# 5) xuat moi nhan ra 1 file <attack>_real.csv
for name, grp in atk.groupby("Label"):
    slug = str(name).lower().replace(" ", "_")
    out = OUT_DIR / f"{slug}_real.csv"
    grp.to_csv(out, index=False)
    print(f"[+] {out.name}: {len(grp)} flow  ->  {out}")

print("[i] Xong. Dung cho Buoc 3 (kiem chung) + Buoc 5 (fine-tune).")
