#!/bin/bash
# Chạy training V8.4 và ghi log để monitor theo dõi
# Cách dùng: ./run_train_v8_4.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/train_v8_4.log"

[ -f "$LOG" ] && rm "$LOG"

echo "======================================"
echo "  V8.4 — Bắt đầu training"
echo "  Base: v8_3_huong2_model.pt"
echo "  Log:  $LOG"
echo "  Monitor: python3 monitor_v8_4.py"
echo "======================================"
echo ""

cd "$SCRIPT_DIR"
python3 v8_4_train.py 2>&1 | tee "$LOG"
