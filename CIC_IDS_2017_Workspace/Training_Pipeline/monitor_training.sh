#!/bin/bash
# Script để theo dõi trực tiếp quá trình huấn luyện của FT-Transformer V2 (10 Epochs)

LOG_FILE="/home/ning/.gemini/antigravity-ide/brain/e53301ef-8820-487b-b57d-6bc7e3489247/.system_generated/tasks/task-131.log"

if [ -f "$LOG_FILE" ]; then
    echo "============================================================"
    echo "📡 ĐANG TRUYỀN DỮ LIỆU TỪ TERMINAL HUẤN LUYỆN (DATA 300K - 10 EPOCHS)..."
    echo "============================================================"
    echo "Nhấn [Ctrl + C] để thoát khỏi màn hình theo dõi (Mô hình vẫn sẽ tiếp tục chạy ngầm)."
    echo ""
    tail -f "$LOG_FILE"
else
    echo "❌ Không tìm thấy file log. Có thể quá trình huấn luyện chưa bắt đầu hoặc đường dẫn đã thay đổi."
fi
