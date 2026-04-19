import asyncio
import telegram
import os
import requests
from loguru import logger
from models.ConfigManager import config

# 가공없이 텍스트를 발송합니다.
async def sendMarkDownText(token, chat_id, sendMessageText): 
    await asyncio.sleep(1)
    bot = telegram.Bot(token = token)
    await bot.sendMessage(chat_id = chat_id, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

async def send_system_alert(message):
    """
    관리자에게 비동기 방식으로 시스템 경고를 전송합니다.
    """
    token = config.BOT_TOKEN
    # TELEGRAM_ADMIN_ID_DEV를 최우선으로 사용
    admin_id = config.get_secret("TELEGRAM_ADMIN_ID_DEV") or \
               config.get_secret("TELEGRAM_USER_ID_DEV") or \
               config.get_secret("TELEGRAM_ADMIN_CHAT_ID")
    
    if not token or not admin_id:
        logger.warning("System alert skipped: Missing BOT_TOKEN or TELEGRAM_ADMIN_ID_DEV")
        return
    
    try:
        bot = telegram.Bot(token=token)
        # Markdown 형식을 사용하여 메시지 발송
        await bot.sendMessage(chat_id=admin_id, text=f"🚨 **[시스템 알림]**\n\n{message}", parse_mode="Markdown")
        logger.info(f"System alert sent to admin: {admin_id}")
    except Exception as e:
        logger.error(f"Failed to send system alert: {e}")

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
