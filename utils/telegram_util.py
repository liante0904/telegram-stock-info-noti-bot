import time
import telegram

# 가공없이 텍스트를 발송합니다.
async def sendMarkDownText(token, chat_id, sendMessageText): 
    time.sleep(1)
    bot = telegram.Bot(token = token)
    await bot.sendMessage(chat_id = chat_id, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
