#!/bin/bash

# LS 리포트 URL 보정 스크립트 백그라운드 실행용 쉘
SCRIPT_NAME="run/fix_ls_db.py"
LOG_FILE="ls_fix_background.log"

echo "--------------------------------------------------"
echo "LS Stock Report Correction starting in background..."
echo "Script: $SCRIPT_NAME"
echo "Log: $LOG_FILE"
echo "--------------------------------------------------"

# 백그라운드 실행 (uv run 권장)
if command -v uv &> /dev/null
then
    nohup uv run python3 $SCRIPT_NAME > $LOG_FILE 2>&1 &
else
    nohup python3 $SCRIPT_NAME > $LOG_FILE 2>&1 &
fi

PID=$!
echo "Process started with PID: $PID"
echo "To check progress, run: tail -f $LOG_FILE"
echo "To stop process, run: kill $PID"
echo "--------------------------------------------------"
