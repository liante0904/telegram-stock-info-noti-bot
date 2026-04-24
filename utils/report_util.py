
import os
from dotenv import load_dotenv
from loguru import logger

# 각 유틸리티 임포트
from utils.sqlite_util import convert_sql_to_telegram_messages
from utils.PostgreSQL_util import convert_pg_rows_to_telegram_messages

load_dotenv()

def get_report_messages(rows):
    """
    DB_BACKEND 환경 변수에 따라 적절한 유틸리티를 선택하여 메시지를 생성합니다.
    """
    backend = os.getenv("DB_BACKEND", "sqlite").lower()
    
    if backend == "sqlite":
        logger.debug("Using SQLite backend for message conversion.")
        return convert_sql_to_telegram_messages(rows)
    else:
        logger.debug("Using PostgreSQL backend for message conversion.")
        return convert_pg_rows_to_telegram_messages(rows)
