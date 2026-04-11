import asyncio
import telegram
import os
import requests
from loguru import logger

# 가공없이 텍스트를 발송합니다.
async def sendMarkDownText(token, chat_id, sendMessageText): 
    await asyncio.sleep(1)
    bot = telegram.Bot(token = token)
    await bot.sendMessage(chat_id = chat_id, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

def send_admin_alert_sync(message):
    """
    관리자에게 텔레그램으로 경고 메시지를 전송합니다 (동기 방식).
    """
    token = os.getenv('TELEGRAM_TEST_TOKEN')
    admin_id = os.getenv('TELEGRAM_ADMIN_ID_DEV')
    if not token or not admin_id:
        logger.info("Admin alert failed: Missing token or admin_id environment variables.")
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": admin_id,
        "text": message
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send admin alert: {e}")
