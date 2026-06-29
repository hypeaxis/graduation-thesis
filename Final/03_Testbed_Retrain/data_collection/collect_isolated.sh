#!/bin/bash
# ============================================================================
# collect_isolated.sh — Thu thập dữ liệu ISOLATED (1 loại / 1 phiên)
# ============================================================================
# Mục đích: Tạo corpus replay cho hệ thống replay-based live detection.
#           Mỗi loại tấn công thu trong MỘT phiên capture riêng → nhãn sạch
#           (gán theo IP attacker, không cần matcher time-window) → 0% ambiguous.
#
# Nguyên tắc isolation (khác hẳn run gộp run5-10):
#   - Mỗi loại 1 phiên tcpdump RIÊNG  → không flow-bleed giữa các loại.
#   - Khi thu ATTACK: KHÔNG bật benign (auto_benign). File chỉ chứa attacker→victim.
#   - Benign thu RIÊNG 1 phiên, KHÔNG chạy attack.
#   - Việc trộn "benign nền + attack" được làm lúc REPLAY, không phải lúc capture.
#
# Cách chạy (trên Máy 1 — Attacker):
#   chmod +x collect_isolated.sh
#   ./collect_isolated.sh --type bruteforce
#   ./collect_isolated.sh --type webattack
#   ./collect_isolated.sh --type dos
#   ./collect_isolated.sh --type benign --duration 600
#   ./collect_isolated.sh --type portscan          # chỉ thu lại nếu cần dài hơn run11
#
# Tham số:
#   --type      portscan | bruteforce | webattack | dos | benign   (bắt buộc)
#   --target    IP victim (mặc định 192.168.0.103)
#   --duration  Số giây chạy benign (chỉ dùng cho --type benign, mặc định 600)
#   --workers   Số worker benign (mặc định 50)
#   --skip-check  Bỏ qua kiểm tra công cụ của auto_attack_v3
# ============================================================================

set -e

# ----------------------------- Tham số mặc định -----------------------------
TARGET="192.168.0.103"
ATTACKER_HINT="192.168.0.106"   # IP Máy 1 — dùng để gán nhãn theo IP khi build corpus
TYPE=""
DURATION=600
WORKERS=50
SKIP_CHECK=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --type)      TYPE="$2"; shift 2;;
        --target)    TARGET="$2"; shift 2;;
        --duration)  DURATION="$2"; shift 2;;
        --workers)   WORKERS="$2"; shift 2;;
        --skip-check) SKIP_CHECK="--skip-check"; shift;;
        *) echo "Tham số không hợp lệ: $1"; exit 1;;
    esac
done

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/../docs"
cd "$SCRIPT_DIR"

# ----------------------------- Validate --type ------------------------------
case "$TYPE" in
    portscan|bruteforce|webattack|dos|benign) ;;
    *) echo -e "${RED}[!] --type phải là: portscan | bruteforce | webattack | dos | benign${NC}"
       echo "    Ví dụ: ./collect_isolated.sh --type bruteforce"
       exit 1;;
esac

RUN_NAME="${TYPE}_only"
PCAP_NAME="${TYPE}_only.pcap"
GT_FILE="$LOG_DIR/ground_truth_log_${RUN_NAME}.csv"

# ----------------------------- Sudo keep-alive ------------------------------
echo "Vui lòng nhập mật khẩu sudo để chuẩn bị môi trường:"
sudo -v
(while true; do sudo -n true; sleep 60; kill -0 "$$" || exit; done 2>/dev/null) &
ulimit -n 65535 || true

# ----------------------------- Banner ---------------------------------------
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         COLLECT ISOLATED — Thu 1 loại / 1 phiên          ║"
echo "╠══════════════════════════════════════════════════════════╣"
printf  "║  Loại:        %-43s║\n" "$TYPE"
printf  "║  Victim:      %-43s║\n" "$TARGET"
printf  "║  Attacker IP: %-43s║\n" "$ATTACKER_HINT (dùng gán nhãn)"
printf  "║  pcap victim: %-43s║\n" "~/$PCAP_NAME"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ----------------------------- Connectivity ---------------------------------
echo -e "${YELLOW}[STEP 0] Kiểm tra kết nối tới victim...${NC}"
if ping -c 1 -W 2 "$TARGET" > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Victim $TARGET reachable${NC}"
else
    echo -e "${RED}  ✗ Không ping được $TARGET. Kiểm tra mạng!${NC}"; exit 1
fi

# Xóa ground truth log cũ của riêng loại này (tránh append nhầm)
if [ -f "$GT_FILE" ]; then
    echo -e "${YELLOW}  ⚠ Xóa ground truth log cũ: $GT_FILE${NC}"
    rm "$GT_FILE"
fi

# ----------------------------- Nhắc bật tcpdump trên Victim ------------------
echo ""
echo -e "${YELLOW}╔══════════════════════════════════════════════════════════╗"
echo -e "║  ⚠ TRÊN MÁY 3 (VICTIM) — BẬT TCPDUMP RIÊNG CHO LOẠI NÀY: ║"
echo -e "║                                                          ║"
printf  "║   sudo tcpdump -i eth0 -w ~/%-30s║\n" "$PCAP_NAME"
echo -e "║                                                          ║"
if [ "$TYPE" = "benign" ]; then
echo -e "║  Và KHÔNG chạy bất kỳ tấn công nào trong phiên này.     ║"
else
echo -e "║  Và KHÔNG chạy auto_benign (giữ file thuần attack).     ║"
echo -e "║  Đảm bảo Apache/DVWA(80), SSH(22), FTP(21) đang chạy.   ║"
fi
echo -e "╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
read -p "Nhấn Enter khi tcpdump trên Victim đã chạy (hoặc Ctrl+C để hủy)... "

START_TIME=$(date +%s)
echo -e "\n${GREEN}[*] Bắt đầu lúc: $(date '+%H:%M:%S')${NC}\n"

# ----------------------------- Chạy đúng loại -------------------------------
if [ "$TYPE" = "benign" ]; then
    echo -e "${BLUE}[RUN] Benign traffic — ${DURATION}s, ${WORKERS} workers (KHÔNG attack)...${NC}"
    # timeout bảo hiểm: nếu --duration không tự thoát thì vẫn dừng
    timeout $((DURATION + 30))s python3 auto_benign_v2.py \
        --target "$TARGET" --workers "$WORKERS" --duration "$DURATION" || true
    echo -e "${GREEN}  ✓ Benign phase hoàn tất${NC}"
else
    echo -e "${RED}[RUN] Attack phase: $TYPE (thuần, không benign)...${NC}"
    # v4: có preflight firewall cho PortScan + cân bằng volume
    python3 auto_attack_v4.py --target "$TARGET" --run-name "$RUN_NAME" \
        --type "$TYPE" $SKIP_CHECK
    echo -e "${GREEN}  ✓ Attack phase '$TYPE' hoàn tất${NC}"
fi

# Cool-down ngắn để flow cuối cùng được CICFlowMeter đóng gọn
echo -e "\n${BLUE}[*] Cool-down 20s để flow cuối được flush...${NC}"
sleep 20 || true

# ----------------------------- Kết quả + bước tiếp --------------------------
END_TIME=$(date +%s); ELAPSED=$((END_TIME - START_TIME))
echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║              HOÀN TẤT THU LOẠI: $(printf '%-24s' "$TYPE")║"
echo "╠══════════════════════════════════════════════════════════╣"
printf  "║  Thời gian:   %-43s║\n" "$((ELAPSED/60)) phút $((ELAPSED%60)) giây"
if [ "$TYPE" != "benign" ]; then
printf  "║  Ground truth:%-43s║\n" " ${RUN_NAME}.csv"
fi
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  BƯỚC TIẾP (Máy 3 - Victim):                            ║"
echo "║   1. Ctrl+C để DỪNG tcpdump                              ║"
printf  "║   2. sudo ./cfm ~/%-39s║\n" "$PCAP_NAME ~/cicflow/"
echo "║   3. Copy *_Flow.csv sang Máy 1 (qua /mnt/c/.../Desktop)║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  BƯỚC TIẾP (Máy 1 - Attacker):                          ║"
printf  "║   cp .../%s_Flow.csv ~/Graduation-Thesis/docs/%*s║\n" "$PCAP_NAME" 8 ""
echo "║   → Gán nhãn theo IP attacker (xem HUONG_DAN_*.md)      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
