#!/usr/bin/env bash
# Postrotate helper cho tcpdump: nhận 1 file pcap vừa đóng, chạy CICFlowMeter V4 (cfm)
# offline để trích đặc trưng, rồi đẩy CSV sang thư mục drop (chia sẻ WSL <-> Windows).
#
# Được tcpdump gọi qua "-z": tcpdump chạy `extract_chunk.sh <pcap_vừa_xoay>`.
# Ghi CSV ra tên tạm ".part" rồi mv (rename cùng thư mục) -> watcher phía Windows
# chỉ đọc *.csv nên không bao giờ đọc file ghi dở.
set -euo pipefail

PCAP="${1:?can duong dan pcap}"

# --- cau hinh (co the override bang bien moi truong) ---
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_LIVE="$(cd "$HERE/.." && pwd)"        # = .../live_detection (ban repo chua script)
CFM_BIN="${CFM_BIN:-/home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm}"
# DROP_DIR thuong duoc capture_and_extract.sh export sang; neu goi doc lap thi mac dinh = data/live cua chinh repo nay.
DROP_DIR="${DROP_DIR:-$REPO_LIVE/data/live}"
WORK_DIR="${WORK_DIR:-/home/ning/live_cap/work}"   # noi cfm ghi tam (ext4, nhanh)

mkdir -p "$WORK_DIR" "$DROP_DIR"

base="$(basename "$PCAP")"                 # vd chunk_20260702_101530.pcap
csv_name="${base}_Flow.csv"                # cfm dat ten: <pcap>_Flow.csv

# 1) cfm trich feature -> WORK_DIR/<base>_Flow.csv
"$CFM_BIN" "$PCAP" "$WORK_DIR" >/dev/null 2>&1 || {
  echo "[extract_chunk] cfm loi tren $base" >&2
  rm -f "$PCAP"; exit 0
}

src_csv="$WORK_DIR/$csv_name"
if [ ! -s "$src_csv" ]; then
  # khong co flow (chunk rong) -> bo qua, don dep
  rm -f "$PCAP" "$src_csv" 2>/dev/null || true
  exit 0
fi

# 2) day sang DROP_DIR theo kieu atomic: copy ra .part roi rename
cp "$src_csv" "$DROP_DIR/$csv_name.part"
mv "$DROP_DIR/$csv_name.part" "$DROP_DIR/$csv_name"

# 3) don dep pcap + csv tam
rm -f "$PCAP" "$src_csv" 2>/dev/null || true

echo "[extract_chunk] OK -> $DROP_DIR/$csv_name"
