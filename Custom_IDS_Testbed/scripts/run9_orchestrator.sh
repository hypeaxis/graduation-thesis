#!/bin/bash
# ============================================================================
# run9_orchestrator.sh — Điều phối toàn bộ quá trình thu thập Run7
# ============================================================================
# Cách chạy:
#   chmod +x run9_orchestrator.sh
#   ./run9_orchestrator.sh
#
# Yêu cầu: 
#   - Chạy trên Máy 1 (Attacker - Ubuntu WSL)
#   - Victim (192.168.0.102) đã bật tcpdump/CICFlowMeter từ trước
#   - Tất cả tools đã cài (nmap, hydra, sqlmap, slowloris, curl)
# ============================================================================

set -e

# Yêu cầu quyền sudo ngay từ đầu để các lệnh bên trong không bị treo
echo "Vui lòng nhập mật khẩu sudo để chuẩn bị môi trường:"
sudo -v
# Giữ sudo session sống trong background
(while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null) &

# Tăng giới hạn file mở để tránh lỗi quá tải sockets với 50 workers
ulimit -n 65535 || true

TARGET="192.168.0.102"
RUN_NAME="run9"
BENIGN_WORKERS=50
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../docs"

# Màu sắc
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          RUN9 ORCHESTRATOR — Dataset Collection         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Target:      $TARGET                              ║"
echo "║  Benign:      $BENIGN_WORKERS workers                                  ║"
echo "║  Thời gian:   ~60-75 phút                               ║"
echo "║  Mục tiêu:    Benign 80% - Attack 20%                   ║"
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

# Kiểm tra HTTP
if curl -s -o /dev/null -w "%{http_code}" -m 3 http://$TARGET/ | grep -q "200\|301\|302"; then
    echo -e "${GREEN}  ✓ HTTP service running${NC}"
else
    echo -e "${YELLOW}  ⚠ HTTP không trả 200 — có thể ảnh hưởng web attack${NC}"
fi

echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗"
echo -e "║  ⚠ QUAN TRỌNG: Đảm bảo trên Victim đã chạy:           ║"
echo -e "║                                                          ║"
echo -e "║  1. tcpdump -i <interface> -w attack_run7.pcap           ║"
echo -e "║  2. Apache/DVWA đang hoạt động                          ║"
echo -e "║  3. SSH và FTP service đang chạy                         ║"
echo -e "╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

read -p "Nhấn Enter khi đã sẵn sàng (hoặc Ctrl+C để hủy)... "

START_TIME=$(date +%s)
echo -e "\n${GREEN}[*] Bắt đầu lúc: $(date '+%H:%M:%S')${NC}\n"

# ============================================================================
# BƯỚC 1: Khởi động Benign Traffic (background)
# ============================================================================
echo -e "${BLUE}[STEP 1] Khởi động benign traffic ($BENIGN_WORKERS workers)...${NC}"
cd "$SCRIPT_DIR"
python3 auto_benign_v2.py --target $TARGET --workers $BENIGN_WORKERS &
BENIGN_PID=$!
echo -e "${GREEN}  ✓ Benign PID: $BENIGN_PID${NC}"

# ============================================================================
# BƯỚC 2: Warm-up — Để benign chạy 5 phút trước
# ============================================================================
echo -e "\n${BLUE}[STEP 2] Warm-up: Để benign chạy 5 phút tạo baseline...${NC}"
for i in $(seq 300 -30 0); do
    echo -ne "  ⏳ Còn ${i}s...\r"
    sleep 30 2>/dev/null || break
done
echo -e "  ✓ Warm-up hoàn tất                                        "

# ============================================================================
# BƯỚC 3: Chạy Attack Script
# ============================================================================
echo -e "\n${RED}[STEP 3] Bắt đầu tấn công...${NC}"
cd "$SCRIPT_DIR"
python3 auto_attack_v3.py --target $TARGET --run-name $RUN_NAME --skip-check

# ============================================================================
# BƯỚC 4: Cool-down — Benign chạy thêm 10 phút
# ============================================================================
echo -e "\n${BLUE}[STEP 4] Cool-down: Benign chạy thêm 10 phút...${NC}"
for i in $(seq 600 -60 0); do
    echo -ne "  ⏳ Còn ${i}s...\r"
    sleep 60 2>/dev/null || break
done
echo -e "  ✓ Cool-down hoàn tất                                      "

# ============================================================================
# BƯỚC 5: Dừng Benign Traffic
# ============================================================================
echo -e "\n${BLUE}[STEP 5] Dừng benign traffic...${NC}"
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
echo "║              RUN9 — HOÀN TẤT THU THẬP DỮ LIỆU         ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Thời gian tổng: ${ELAPSED_MIN} phút ${ELAPSED_SEC} giây                          ║"
echo "║  Ground truth:   $LOG_DIR/ground_truth_log_${RUN_NAME}.csv  ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  BƯỚC TIẾP THEO:                                       ║"
echo "║  1. Dừng tcpdump trên Victim                            ║"
echo "║  2. Chạy CICFlowMeter trên file pcap                    ║"
echo "║  3. Copy file CSV về Máy 1                              ║"
echo "║  4. Chạy dataset_builder_v2.py để gán nhãn              ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
