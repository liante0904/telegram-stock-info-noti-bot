import os
import asyncio
import argparse
import telegram.error
from loguru import logger
from utils.sqlite_util import convert_sql_to_telegram_messages
from utils.telegram_util import sendMarkDownText
from utils.file_util import download_file_wget
from models.SQLiteManager import SQLiteManager
from dotenv import load_dotenv

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
chat_id = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')


def format_date(date_str):
    if len(date_str) == 8 and date_str.isdigit():  # 20241012 형태인지 확인
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    return date_str  # 이미 'YYYY-MM-DD'인 경우 그대로 반환

async def daily_report(report_type, date_str=None):
    db = SQLiteManager()
    if report_type == 'send':
        rows = await db.daily_select_data(date_str=date_str, type=report_type)
        if rows:
            formatted_messages = await convert_sql_to_telegram_messages(rows)
            logger.info(f"Prepared {len(formatted_messages)} messages to send.")

            # 메시지 발송
            send_success = True  # 모든 메시지가 성공했는지 여부를 추적
            for sendMessageText in formatted_messages:
                try:
                    logger.debug(f"Sending message: {sendMessageText[:50]}...")
                    await sendMarkDownText(token=token,
                                           chat_id=chat_id,
                                           sendMessageText=sendMessageText)
                except telegram.error.TelegramError as e:
                    logger.error(f"Telegram API Error: {e} | Message: {sendMessageText[:50]}")
                    send_success = False
                except Exception as e:
                    logger.exception(f"Unexpected error while sending message: {e}")
                    send_success = False

            # 모든 메시지가 성공적으로 전송된 경우에만 데이터 업데이트
            if send_success:
                r = await db.daily_update_data(date_str=date_str, fetched_rows=rows, type=report_type)
                if r:
                    logger.info('DB daily_update_data successful.')
            else:
                logger.warning('Some messages failed to send. DB update skipped.')

    elif report_type == 'download':
        rows = await db.daily_select_data(date_str=date_str, type='download')
        if rows:
            logger.info(f"Starting download for {len(rows)} files.")
            for row in rows:
                download_success = await download_file_wget(report_info_row=row)
                if download_success:
                    await db.daily_update_data(date_str=date_str, fetched_rows=row, type='download')
                    logger.debug(f"Downloaded and updated DB for: {row.get('ARTICLE_TITLE', 'Unknown')}")
                else:
                    logger.error(f"Failed to download file: {row.get('ARTICLE_TITLE', 'Unknown')}")


async def main(date_str=None):
    logger.info('=================== scrap_send_main START ===================')
    await daily_report(report_type='send', date_str=date_str)
    # await daily_report(report_type='download', date_str=date_str)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Daily report script.')
    parser.add_argument('date', type=str, nargs='?', default=None, help='Date in YYYY-MM-DD format.')

    args = parser.parse_args()
    asyncio.run(main(date_str=args.date))
