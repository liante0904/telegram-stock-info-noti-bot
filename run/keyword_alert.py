# -*- coding:utf-8 -*-
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger_util import setup_logger
setup_logger("send_report_by_keyword_to_user")

from utils.sqlite_util import convert_sql_to_telegram_messages
from utils.telegram_util import sendMarkDownText
from models.PostgreSQLManager import PostgreSQLManager

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
INTERVAL = int(os.getenv('INTERVAL', '1800'))

pg_manager = PostgreSQLManager()

async def run_once():
    logger.info("Fetching keywords from PostgreSQL...")
    try:
        user_keywords = pg_manager.load_keywords_from_db()
    except Exception as e:
        logger.error(f"Failed to load keywords from DB: {e}")
        return

    if not user_keywords:
        logger.info("No active keywords found in DB.")
        return

    logger.info(f"Loaded {len(user_keywords)} users from DB.")
    today = datetime.now().strftime('%Y-%m-%d')

    for user_id, entries in user_keywords.items():
        for entry in entries:
            keyword = entry['keyword']
            try:
                found_reports = pg_manager.fetch_keyword_reports(date=today, keyword=keyword, user_id=user_id)
                if found_reports:
                    logger.success(f"[{user_id}] Found {len(found_reports)} reports for '{keyword}'")
                    header = f"===== 알림 키워드 : {keyword} =====\n"
                    chunks = convert_sql_to_telegram_messages(found_reports)
                    for i, chunk in enumerate(chunks):
                        msg = (header if i == 0 else "") + chunk
                        await sendMarkDownText(token=TOKEN, chat_id=user_id, sendMessageText=msg)
                    pg_manager.update_keyword_send_user(date=today, keyword=keyword, user_id=user_id)
            except Exception as e:
                logger.error(f"Error processing '{keyword}' for {user_id}: {e}")

async def main():
    logger.info("Starting User Report Keyword Alert Service...")
    if os.getenv('RUN_ONCE', 'false').lower() == 'true':
        await run_once()
    else:
        while True:
            await run_once()
            logger.info(f"Waiting for {INTERVAL}s until next check...")
            await asyncio.sleep(INTERVAL)

if __name__ == '__main__':
    asyncio.run(main())
