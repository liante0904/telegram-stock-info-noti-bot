import os
import telegram
from dotenv import load_dotenv

load_dotenv()  # .env 파일의 환경 변수를 로드합니다
env = os.getenv('ENV')
print(env)

if env == 'production':
    TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
    TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
    
else:
    TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
    TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')


async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
