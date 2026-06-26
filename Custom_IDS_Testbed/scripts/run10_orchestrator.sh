#!/bin/bash
# ============================================================================
# run10_orchestrator.sh — Thu thập dữ liệu Run10 (Clean PortScan Labels)
# ============================================================================
# Thay đổi so với run9:
#   - PortScan chạy TRƯỚC khi bật benign (tránh label contamination)
#   - Benign chỉ chạy trong giai đoạn BruteForce/WebAttack/DoS
#
# Cách chạy:
#   chmod +x run10_orchestrator.sh
#   ./run10_orchestrator.sh
#
# Yêu cầu:
#   - Chạy trên Máy 1 (Attacker — WSL Ubuntu trên Win10, 192.168.0.104)
#   - Máy 3 (Victim — WSL Ubuntu trên Máy 2 Win11, 192.168.0.102) đã bật:
#       tcpdump -i eth0 -w ~/attack_capture_run10.pcap
#       sudo service apache2 start && sudo service ssh start && sudo service vsftpd start
# ============================================================================

set -e

echo "Vui lòng nhập mật khẩu sudo để chuẩn bị môi trường:"
sudo -v
(while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null) &

ulimit -n 65535 || true

TARGET="192.168.0.102"
RUN_NAME="run10"
BENIGN_WORKERS=50
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../docs"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          RUN10 ORCHESTRATOR — Clean PortScan Data       ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Target:      $TARGET                              ║"
echo "║  Benign:      $BENIGN_WORKERS workers (chỉ sau PortScan)           ║"
echo "║  Thời gian:   ~70-80 phút                               ║"
echo "║  Mục tiêu:    PortScan SẠCH — 0% contamination          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================================
# BƯỚC 0: Kiểm tra connectivity
# ============================================================================
echo -e "${YELLOW}[STEP 0] Kiểm tra kết nối tới victim...${NC}"
if ping -c 1 -W 2 $TARGET > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Victim $TARGET reachable${NC}"
else
    echo -e "${RED}  ✗ Không thể ping $TARGET. Kiểm tra lại mạng!${NC}"
    exit 1
fi

if curl -s -o /dev/null -w "%{http_code}" -m 3 http://$TARGET/ | grep -q "200\|301\|302"; then
    echo -e "${GREEN}  ✓ HTTP service running${NC}"
else
    echo -e "${YELLOW}  ⚠ HTTP không trả 200 — kiểm tra Apache trên Victim${NC}"
fi

# Xóa ground truth log cũ nếu có (để tránh append nhầm từ run trước)
GT_FILE="$LOG_DIR/ground_truth_log_${RUN_NAME}.csv"
if [ -f "$GT_FILE" ]; then
    echo -e "${YELLOW}  ⚠ Xóa ground truth log cũ: $GT_FILE${NC}"
    rm "$GT_FILE"
fi

echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗"
echo -e "║  ⚠ QUAN TRỌNG: Đảm bảo trên Máy 3 (Victim) đã chạy:   ║"
echo -e "║                                                          ║"
echo -e "║  1. sudo tcpdump -i eth0 -w ~/attack_capture_run10.pcap ║"
echo -e "║  2. Apache/DVWA đang hoạt động (port 80)                ║"
echo -e "║  3. SSH (port 22) và FTP (port 21) đang chạy            ║"
echo -e "╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

read -p "Nhấn Enter khi đã sẵn sàng (hoặc Ctrl+C để hủy)... "

START_TIME=$(date +%s)
echo -e "\n${GREEN}[*] Bắt đầu lúc: $(date '+%H:%M:%S')${NC}\n"

cd "$SCRIPT_DIR"

# ============================================================================
# BƯỚC 1: PortScan — KHÔNG CÓ BENIGN
# (Benign chưa bật → 0% contamination trong ground truth window)
# ============================================================================
echo -e "${RED}[STEP 1] PortScan phase — benign chưa chạy (clean labels)...${NC}"
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase portscan --skip-check
echo -e "${GREEN}  ✓ PortScan hoàn tất${NC}"

# Chờ 30 giây — cửa sổ ±5s của dataset_builder sẽ không overlap với benign
echo -e "\n${BLUE}[*] Chờ 30s trước khi bật benign (đảm bảo không overlap)...${NC}"
for i in $(seq 30 -5 0); do
    echo -ne "  ⏳ Còn ${i}s...\r"
    sleep 5 2>/dev/null || break
done
echo -e "  ✓ An toàn để bật benign                                   "

# ============================================================================
# BƯỚC 2: Bật Benign Traffic (background)
# ============================================================================
echo -e "\n${BLUE}[STEP 2] Bật benign traffic ($BENIGN_WORKERS workers)...${NC}"
python3 auto_benign_v2.py --target $TARGET --workers $BENIGN_WORKERS &
BENIGN_PID=$!
echo -e "${GREEN}  ✓ Benign PID: $BENIGN_PID${NC}"

# ============================================================================
# BƯỚC 3: Warm-up Benign 5 phút
# ============================================================================
echo -e "\n${BLUE}[STEP 3] Warm-up benign 5 phút...${NC}"
for i in $(seq 300 -30 0); do
    echo -ne "  ⏳ Còn ${i}s...\r"
    sleep 30 2>/dev/null || break
done
echo -e "  ✓ Warm-up hoàn tất                                        "

# ============================================================================
# BƯỚC 4: Brute Force (có benign chạy song song)
# ============================================================================
echo -e "\n${RED}[STEP 4] Brute Force phase...${NC}"
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase bruteforce --skip-check
echo -e "${GREEN}  ✓ Brute Force hoàn tất${NC}"

sleep 30

# ============================================================================
# BƯỚC 5: Web Attack (có benign chạy song song)
# ============================================================================
echo -e "\n${RED}[STEP 5] Web Attack phase...${NC}"
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase webattack --skip-check
echo -e "${GREEN}  ✓ Web Attack hoàn tất${NC}"

sleep 30

# ============================================================================
# BƯỚC 6: DoS (có benign chạy song song)
# ============================================================================
echo -e "\n${RED}[STEP 6] DoS phase...${NC}"
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME \
    --phase dos --skip-check
echo -e "${GREEN}  ✓ DoS hoàn tất${NC}"

# ============================================================================
# BƯỚC 7: Cool-down 10 phút
# ============================================================================
echo -e "\n${BLUE}[STEP 7] Cool-down: Benign chạy thêm 10 phút...${NC}"
for i in $(seq 600 -60 0); do
    echo -ne "  ⏳ Còn ${i}s...\r"
    sleep 60 2>/dev/null || break
done
echo -e "  ✓ Cool-down hoàn tất                                      "

# ============================================================================
# BƯỚC 8: Dừng Benign
# ============================================================================
echo -e "\n${BLUE}[STEP 8] Dừng benign traffic...${NC}"
if kill $BENIGN_PID 2>/dev/null; then
    echo -e "${GREEN}  ✓ Benign stopped (PID: $BENIGN_PID)${NC}"
else
    echo -e "${YELLOW}  ⚠ Benign đã dừng trước đó${NC}"
fi

# ============================================================================
# KẾT QUẢ
# ============================================================================
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))

echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║             RUN10 — HOÀN TẤT THU THẬP DỮ LIỆU         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Thời gian tổng: ${ELAPSED_MIN} phút ${ELAPSED_SEC} giây                          ║"
echo "║  Ground truth:   $LOG_DIR/ground_truth_log_${RUN_NAME}.csv ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  BƯỚC TIẾP THEO (trên Máy 3 - Victim):                  ║"
echo "║  1. Ctrl+C để dừng tcpdump                               ║"
echo "║  2. sudo ./cfm ~/attack_capture_run10.pcap ~/cicflow/    ║"
echo "║  3. Copy CSV về Máy 1 qua /mnt/c/Users/.../Desktop/     ║"
echo "║                                                          ║"
echo "║  BƯỚC TIẾP THEO (trên Máy 1):                           ║"
echo "║  cp /mnt/c/.../attack_capture_run10.pcap_Flow.csv \\     ║"
echo "║     ~/Graduation-Thesis/docs/                            ║"
echo "║  python3 dataset_builder_v2.py --csv ... --ground-truth  ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
