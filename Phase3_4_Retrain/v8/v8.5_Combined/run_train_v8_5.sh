#!/bin/bash
# Chạy training V8.5 và ghi log để monitor theo dõi
# Cách dùng: ./run_train_v8_5.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/train_v8_5.log"

[ -f "$LOG" ] && rm "$LOG"

echo "========================================"
echo "  V8.5 Combined Best — Bắt đầu training"
echo "  Base:    v8_4_model.pt"
echo "  Dataset: Combined_V8_5.csv (111,825 flows)
  Epochs:  max 15, early stop patience=5"
echo "  Log:     $LOG"
echo "  Monitor: python3 monitor_v8_5.py"
echo "========================================"
echo ""

cd "$SCRIPT_DIR"
python3 v8_5_train.py 2>&1 | tee "$LOG"
