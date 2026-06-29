#!/bin/bash
# ============================================================================
# run11_portscan_boost.sh — Thu thập PortScan thuần (50 round)
# ============================================================================
# Mục đích: Chạy 50 round PortScan liên tiếp, không benign, không attack khác
#           → ~350 PortScan flows sạch cho training V8.3 (Hướng 1)
#
# Cách chạy:
#   chmod +x run11_portscan_boost.sh
#   ./run11_portscan_boost.sh
#
# Yêu cầu:
#   - Chạy trên Máy 1 (Attacker — WSL Ubuntu Win10, 192.168.0.104)
#   - Máy 3 (Victim — WSL Ubuntu trên Máy 2 Win11, 192.168.0.102) đã bật:
#       sudo tcpdump -i eth0 -w ~/attack_capture_run11.pcap
#       sudo service apache2 start && sudo service ssh start && sudo service vsftpd start
#
# Ước tính thời gian: 50 round × ~35s = ~30 phút
# ============================================================================

set -e

echo "Vui lòng nhập mật khẩu sudo để chuẩn bị môi trường:"
sudo -v
(while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null) &

TARGET="192.168.0.102"
RUN_NAME="run11"
ROUNDS=50
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GT_FILE="$SCRIPT_DIR/../docs/ground_truth_log_${RUN_NAME}.csv"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         RUN11 — PortScan Boost (50 rounds)              ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Target:      $TARGET                              ║"
echo "║  Rounds:      $ROUNDS                                         ║"
echo "║  Ước tính:    ~30 phút                                  ║"
echo "║  Kỳ vọng:     ~350 PortScan flows sạch                  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================================
# Kiểm tra connectivity
# ============================================================================
echo -e "${YELLOW}[STEP 0] Kiểm tra kết nối tới victim...${NC}"
if ! ping -c 1 -W 2 $TARGET > /dev/null 2>&1; then
    echo -e "${RED}  ✗ Không thể ping $TARGET. Kiểm tra lại mạng!${NC}"
    exit 1
fi
echo -e "${GREEN}  ✓ Victim $TARGET reachable${NC}"

if curl -s -o /dev/null -w "%{http_code}" -m 3 http://$TARGET/ | grep -q "200\|301\|302"; then
    echo -e "${GREEN}  ✓ HTTP (port 80) đang mở${NC}"
else
    echo -e "${YELLOW}  ⚠ HTTP không phản hồi — port 80 đóng, sẽ ít flows hơn${NC}"
fi

# Xóa ground truth cũ nếu có để tránh append nhầm
if [ -f "$GT_FILE" ]; then
    echo -e "${YELLOW}  ⚠ Xóa ground truth cũ: $GT_FILE${NC}"
    rm "$GT_FILE"
fi

echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗"
echo -e "║  ⚠ Đảm bảo Máy 3 (Victim) đã chạy:                    ║"
echo -e "║  sudo tcpdump -i eth0 -w ~/attack_capture_run11.pcap    ║"
echo -e "║  sudo service apache2 start && sudo service ssh start   ║"
echo -e "║  sudo service vsftpd start                               ║"
echo -e "╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Nhấn Enter khi đã sẵn sàng (hoặc Ctrl+C để hủy)... "

START_TIME=$(date +%s)
echo -e "\n${GREEN}[*] Bắt đầu lúc: $(date '+%H:%M:%S')${NC}"
echo -e "${BLUE}[*] Ground truth sẽ lưu vào: $GT_FILE${NC}\n"

cd "$SCRIPT_DIR"

# ============================================================================
# VÒNG LẶP 50 ROUND PORTSCAN
# ============================================================================
for i in $(seq 1 $ROUNDS); do
    ELAPSED_NOW=$(( $(date +%s) - START_TIME ))
    ELAPSED_MIN=$((ELAPSED_NOW / 60))
    ELAPSED_SEC=$((ELAPSED_NOW % 60))

    echo -e "${RED}[Round $i/$ROUNDS] $(date '+%H:%M:%S') — đã chạy ${ELAPSED_MIN}m${ELAPSED_SEC}s${NC}"

    python3 auto_attack_v3.py \
        --target "$TARGET" \
        --run-name "$RUN_NAME" \
        --phase portscan \
        --skip-check

    # Đợi 10s giữa các round
    # Lý do: dataset_builder dùng cửa sổ ±5s; nếu round sau bắt đầu < 5s
    # sau khi round trước kết thúc, các flow có thể bị label overlap.
    if [ $i -lt $ROUNDS ]; then
        echo -e "${BLUE}  → Nghỉ 10s trước round tiếp theo...${NC}"
        sleep 10
    fi
done

# ============================================================================
# KẾT QUẢ
# ============================================================================
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

PS_COUNT=$(grep -c "PortScan" "$GT_FILE" 2>/dev/null || echo "0")

echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              RUN11 — HOÀN TẤT                          ║"
echo "╠══════════════════════════════════════════════════════════╣"
printf "║  Thời gian:  %d phút %d giây                              ║\n" $ELAPSED_MIN $ELAPSED_SEC
printf "║  Rounds:     %d/%d hoàn tất                              ║\n" $ROUNDS $ROUNDS
printf "║  GT events:  %s PortScan events                       ║\n" "$PS_COUNT"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  BƯỚC TIẾP THEO (trên Máy 3 - Victim):                  ║"
echo "║  1. Ctrl+C để dừng tcpdump                               ║"
echo "║  2. sudo ./cfm ~/attack_capture_run11.pcap ~/cicflow/    ║"
echo "║  3. Copy CSV về Máy 1 qua /mnt/c/Users/.../Desktop/     ║"
echo "║                                                          ║"
echo "║  BƯỚC TIẾP THEO (trên Máy 1 — máy này):                 ║"
echo "║  cp /mnt/c/.../attack_capture_run11.pcap_Flow.csv \\     ║"
echo "║     ~/Graduation-Thesis/docs/                            ║"
echo "║  python3 dataset_builder_v2.py \\                         ║"
echo "║    --csv .../attack_capture_run11.pcap_Flow.csv \\        ║"
echo "║    --ground-truth .../ground_truth_log_run11.csv         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
