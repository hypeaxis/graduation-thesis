#!/bin/bash
# Find the latest training log file
LATEST_LOG=$(ls -t /home/ning/Graduation-Thesis/MLAnomalyDetection/outputs/improved_runs/*/training_log_*.txt 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "No training log found yet."
    exit 1
fi

echo "=========================================================="
echo "Monitoring latest training log:"
echo "$LATEST_LOG"
echo "Press Ctrl+C to stop monitoring (training will keep running in background)."
echo "=========================================================="
echo ""

# Tail the log file and the task log to see both the python print outputs and the tqdm progress bars
# The tqdm progress bar is stored in the system task log
TASK_LOG="/home/ning/.gemini/antigravity-ide/brain/21c278b2-ef13-4fa1-bc78-82a392c71780/.system_generated/tasks/task-167.log"

tail -f "$TASK_LOG"
