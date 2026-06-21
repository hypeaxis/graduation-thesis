#!/bin/bash
# Script để theo dõi live output của các tác vụ chạy ngầm (Background Tasks)

LOG_DIR="/home/ning/.gemini/antigravity-ide/brain/383d0d50-8eec-4e02-ae81-cad1abd29464/.system_generated/tasks/"

# Tìm file log python được tạo ra gần nhất
LATEST_LOG=$(grep -l "python" "$LOG_DIR"/*.log 2>/dev/null | xargs ls -t 2>/dev/null | head -n 1)

if [ -z "$LATEST_LOG" ]; then
    echo "Chưa có file log nào được tạo ra."
    exit 1
fi

echo "========================================================="
echo " Đang theo dõi tiến trình mới nhất: $(basename "$LATEST_LOG")"
echo " (Bấm Ctrl+C để thoát chế độ theo dõi)"
echo "========================================================="
echo ""

tail -f "$LATEST_LOG"
