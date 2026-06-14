#!/bin/bash
# Script để theo dõi các tiến trình nền mới nhất (Data Pipeline / Model Training)
LOG_DIR="/home/ning/.gemini/antigravity-ide/brain/0164f7d5-ecb9-4b55-9043-62d368d690bf/.system_generated/tasks"

LATEST_LOG=$(ls -t "$LOG_DIR"/*.log 2>/dev/null | head -n 1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ Không tìm thấy tiến trình ngầm nào đang chạy."
    exit 1
fi

echo "============================================================"
echo "📡 ĐANG THEO DÕI TIẾN TRÌNH GẦN NHẤT: $(basename "$LATEST_LOG")"
echo "============================================================"
echo "Nhấn [Ctrl + C] để thoát khỏi màn hình theo dõi (Tiến trình vẫn tiếp tục chạy ngầm)."
echo ""
tail -f "$LATEST_LOG"
