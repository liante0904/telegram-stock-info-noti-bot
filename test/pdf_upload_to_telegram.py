import telegram
from telegram import Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# 텔레그램 봇 토큰을 입력하세요
TELEGRAM_BOT_TOKEN = ''

# 업로드된 파일의 URL을 반환하는 함수
def get_file_url(file_id):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    file = bot.get_file(file_id)
    return file.file_path

# /start 명령어 처리 함수
def start(update, context):
    update.message.reply_text('PDF 파일을 업로드하세요.')

# 파일 메시지 처리 함수
def handle_file(update, context):
    file = update.message.document
    if file.mime_type == 'application/pdf':
        file_id = file.file_id
        file_url = get_file_url(file_id)
        update.message.reply_text(f'파일이 업로드되었습니다: {file_url}')
    else:
        update.message.reply_text('PDF 파일만 업로드 가능합니다.')

def main():
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # 핸들러 등록
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(MessageHandler(Filters.document.mime_type('application/pdf'), handle_file))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
