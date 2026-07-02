#!/usr/bin/env bash
# ============================================================================
# Live capture (WSL) cho live_detection — kien truc MICRO-BATCH.
#
#   tcpdump  -i <iface>  xoay pcap moi <CHUNK_SEC> giay
#        └─ (-z) goi extract_chunk.sh  ->  cfm (CICFlowMeter V4) offline
#              └─ *_Flow.csv  ->  DROP_DIR  (thu muc chia se WSL <-> Windows)
#
# Vi sao micro-batch (khong dung live-sniff cua cfm):
#   - cfm live (-i/eth0) khong on dinh tren WSL (blocker goc, xem walkthrough.md).
#   - cfm OFFLINE tren pcap = dung tool da tao dataset -> parity 84/84 cot, 0 domain shift.
#
# Chay:
#   bash capture_and_extract.sh                 # eth0, chunk 8s, drop mac dinh
#   IFACE=eth0 CHUNK_SEC=5 bash capture_and_extract.sh
#
# tcpdump can quyen bat goi. De KHOI go sudo moi lan, chay 1 lan:
#   sudo setcap cap_net_raw,cap_net_admin+eip "$(readlink -f "$(which tcpdump)")"
# ============================================================================
set -euo pipefail

IFACE="${IFACE:-eth0}"
CHUNK_SEC="${CHUNK_SEC:-8}"                 # do dai moi chunk = do tre near-real-time
CAP_DIR="${CAP_DIR:-/home/ning/live_cap/pcap}"   # noi tcpdump ghi pcap (ext4, nhanh)
DROP_DIR="${DROP_DIR:-/mnt/d/ĐỒ ÁN/graduation-thesis/live_detection/data/live}"
HERE="$(cd "$(dirname "$0")" && pwd)"
export DROP_DIR                            # extract_chunk.sh doc bien nay
export CFM_BIN="${CFM_BIN:-/home/ning/CICFlowMeter/build/distributions/CICFlowMeter-4.0/bin/cfm}"
BPF="${BPF:-ip and (tcp or udp)}"          # loc giong CICFlowMeter (bo goi khong phai tcp/udp)

mkdir -p "$CAP_DIR" "$DROP_DIR"

# --- kiem tra tien dieu kien ---
command -v tcpdump >/dev/null || { echo "[!] chua co tcpdump (sudo apt install tcpdump)"; exit 1; }
[ -x "$CFM_BIN" ] || { echo "[!] khong thay cfm: $CFM_BIN"; exit 1; }
if ! getcap "$(readlink -f "$(which tcpdump)")" 2>/dev/null | grep -q cap_net_raw; then
  echo "[cảnh báo] tcpdump chua co cap_net_raw -> co the phai chay bang sudo."
  echo "           Chay 1 lan de khoi sudo:"
  echo "           sudo setcap cap_net_raw,cap_net_admin+eip \"\$(readlink -f \"\$(which tcpdump)\")\""
fi

echo "[*] Interface : $IFACE"
echo "[*] Chunk     : ${CHUNK_SEC}s"
echo "[*] Pcap tmp  : $CAP_DIR"
echo "[*] Drop CSV  : $DROP_DIR"
echo "[*] cfm       : $CFM_BIN"
echo "[*] Bat dau bat goi... (Ctrl-C de dung)"

# -G <sec> -w <pattern strftime>  : xoay file theo thoi gian
# -z <cmd>                        : postrotate, tcpdump goi `<cmd> <file_vua_dong>`
# -Z root                         : giu quyen (khi chay sudo) - bo qua neu dung setcap
exec tcpdump -i "$IFACE" \
     -G "$CHUNK_SEC" \
     -w "$CAP_DIR/chunk_%Y%m%d_%H%M%S.pcap" \
     -z "$HERE/extract_chunk.sh" \
     $BPF
