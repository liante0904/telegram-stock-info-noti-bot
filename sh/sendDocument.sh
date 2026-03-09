#!/bin/bash

# .env 파일 로드
source /home/ubuntu/dev/telegram-stock-info-noti-bot/.env

# 폴더 경로
FOLDER_PATH="/home/ubuntu/dev/telegram-stock-info-bot"
SEND_FOLDER="$FOLDER_PATH/send"

# 최신 엑셀 파일 찾기 (KR_stock_screening_YYMMDD.xlsx 형식)
FILE_PATH=$(ls -t "$FOLDER_PATH"/KR_stock_screening_*.xlsx 2>/dev/null | head -n 1)

# 파일 존재 여부 확인
if [ -z "$FILE_PATH" ]; then
    echo "오류: 전송할 파일을 찾을 수 없습니다. ($FOLDER_PATH/KR_stock_screening_*.xlsx)"
    exit 1
fi

# 파일명 추출
FILE_NAME=$(basename "$FILE_PATH")

# 메시지 설정
MESSAGE="📊 주식 스크리닝 결과 파일 전송: $FILE_NAME"

# 파일 전송 요청
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN_PROD/sendDocument" \
     -F chat_id="$TELEGRAM_CHANNEL_ID_REPORT_ALARM" \
     -F document=@"$FILE_PATH" \
     -F caption="$MESSAGE")

# 응답 출력
echo "Response: $RESPONSE"

# send 폴더가 없으면 생성
mkdir -p "$SEND_FOLDER"

# 전송한 파일 이동
mv "$FILE_PATH" "$SEND_FOLDER/"

echo "파일이 전송 후 이동되었습니다: $SEND_FOLDER/$FILE_NAME"
