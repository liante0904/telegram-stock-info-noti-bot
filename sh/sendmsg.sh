#!/bin/bash

# .env 파일 로드
source /home/ubuntu/dev/telegram-stock-info-noti-bot/.env

# 환경 변수 출력
echo "TELEGRAM_ADMIN_ID_DEV: $TELEGRAM_ADMIN_ID_DEV"
echo "TELEGRAM_TEST_TOKEN: $TELEGRAM_TEST_TOKEN"

# 긴 메시지를 전달받아 전송
MESSAGE="$1"

# 메시지 출력
echo "Sending message: $MESSAGE"

# 텔레그램 API로 메시지 전송
RESPONSE=$(curl -s -X POST https://api.telegram.org/bot$TELEGRAM_TEST_TOKEN/sendMessage \
     -d chat_id=$TELEGRAM_ADMIN_ID_DEV \
     -d text="$MESSAGE")

# 응답 출력
echo "Response: $RESPONSE"
