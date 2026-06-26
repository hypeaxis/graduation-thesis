#!/bin/bash
# Chạy training V8.3 Hướng 2 và ghi log để monitor theo dõi
# Cách dùng: ./run_train_huong2.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/train_huong2.log"

# Xóa log cũ nếu có
[ -f "$LOG" ] && rm "$LOG"

echo "======================================"
echo "  V8.3 Hướng 2 — Bắt đầu training"
echo "  Log: $LOG"
echo "  Monitor: python3 monitor_huong2.py"
echo "======================================"
echo ""

cd "$SCRIPT_DIR"
python3 v8_3_train_huong2.py 2>&1 | tee "$LOG"
