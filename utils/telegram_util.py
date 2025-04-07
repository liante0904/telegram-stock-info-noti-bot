# utils/telegram_util.py
import asyncio
from telegram import Bot

# Bot 객체 재사용을 위한 전역 변수
_bot_instance = None

def get_bot(token):
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=token)
    return _bot_instance

# 텍스트 발송 함수
async def sendMarkDownText(token, chat_id, sendMessageText): 
    await asyncio.sleep(1)  # 의도적인 지연 (필요 시 제거 가능)
    bot = get_bot(token)
    await bot.send_message(
        chat_id=chat_id,
        text=sendMessageText,
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )