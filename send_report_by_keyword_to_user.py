import json
import sqlite3
import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# 로그 설정: 터미널에서 직접 실행(isatty)하면 DEBUG 레벨과 심플한 포맷 사용, 아니면 INFO 레벨과 상세 포맷 사용
is_manual = sys.stdout.isatty()
log_level = logging.DEBUG if is_manual else logging.INFO
log_format = '%(message)s' if is_manual else '%(asctime)s - %(levelname)s - %(message)s'

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.sqlite_util import format_message_sql
from utils.telegram_util import sendMarkDownText
from models.PostgreSQLManager import PostgreSQLManager

# 환경 변수 및 설정 로드
load_dotenv()
DB_PATH = os.getenv('DB_PATH', os.path.expanduser('~/sqlite3/telegram.db'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
# CONFIG_PATH는 더 이상 JSON 파일을 읽지 않으므로 필요 시 참고용으로만 남기거나 제거 가능
CONFIG_PATH = os.getenv('CONFIG_PATH', os.path.abspath(os.path.join(os.getcwd(), '..', 'telegram-stock-info-bot', 'report_alert_keyword.json')))
INTERVAL = int(os.getenv('INTERVAL', '1800')) # 기본 30분

# PostgreSQL 매니저 인스턴스 생성
pg_manager = PostgreSQLManager()

def parse_date(date_str):
    """날짜 형식을 YYYY-MM-DD로 통일하는 헬퍼 함수"""
    if date_str is None:
        return datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 이미 형식이 맞는 경우
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError:
        if len(date_str) == 8: # YYYYMMDD
            return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
        elif len(date_str) == 6: # YYMMDD
            return datetime.strptime(date_str, '%y%m%d').strftime('%Y-%m-%d')
        raise ValueError("Invalid date format. Use 'YYYYMMDD', 'YYMMDD', or 'YYYY-MM-DD'.")

def fetch_data(date=None, keyword=None, user_id=None):
    """여러 테이블에서 키워드에 맞는 미전송 데이터를 조회"""
    date = parse_date(date)
    # logger.debug(f"Searching for date: {date}")
    if not keyword:
        raise ValueError("keyword는 필수입니다.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 테이블 설정 (TELEGRAM_URL 컬럼 유무에 따른 분기)
    tables = [
        ('data_main_daily_send', 'COALESCE(TELEGRAM_URL, DOWNLOAD_URL, ATTACH_URL)'),
        ('hankyungconsen_research', 'COALESCE(DOWNLOAD_URL, ATTACH_URL)'),
        ('naver_research', 'COALESCE(DOWNLOAD_URL, ATTACH_URL)')
    ]
    
    query_parts = []
    params = []
    keyword_param = f"%{keyword}%"
    user_pattern = f'%"{user_id}"%'

    for table_name, url_col in tables:
        # 테이블 존재 여부 확인
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            continue

        query_parts.append(f"""
            SELECT FIRM_NM, ARTICLE_TITLE, {url_col} AS TELEGRAM_URL, SAVE_TIME, SEND_USER
            FROM {table_name}
            WHERE (ARTICLE_TITLE LIKE ? OR WRITER LIKE ?)
            AND DATE(SAVE_TIME) = ?
            AND (SEND_USER IS NULL OR SEND_USER NOT LIKE ?)
        """)
        params.extend([keyword_param, keyword_param, date, user_pattern])

    if not query_parts:
        conn.close()
        return []

    final_query = " UNION ".join(query_parts) + " ORDER BY SAVE_TIME ASC, FIRM_NM ASC"
    
    cursor.execute(final_query, params)
    results = cursor.fetchall()
    conn.close()
    return results

def update_data(date=None, keyword=None, user_id=None):
    """발송 완료한 사용자 ID를 SEND_USER 컬럼에 기록"""
    date = parse_date(date)
    user_id_json = json.dumps([user_id]) # 리스트 형태로 저장 (기존 호환성 유지)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    tables = ['data_main_daily_send', 'hankyungconsen_research', 'naver_research']

    for table in tables:
        # 테이블 존재 여부 확인
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone():
            continue

        update_query = f"""
            UPDATE {table}
            SET SEND_USER = ?
            WHERE (ARTICLE_TITLE LIKE ? OR WRITER LIKE ?)
            AND DATE(SAVE_TIME) = ?
        """
        keyword_param = f"%{keyword}%"
        cursor.execute(update_query, (user_id_json, keyword_param, keyword_param, date))
        if cursor.rowcount > 0:
            logger.info(f"[{table}] {cursor.rowcount} rows updated.")

    conn.commit()
    conn.close()

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

    for user_id, entries in user_keywords.items():
        user_id_str = str(user_id)
        logger.info(f">>> Processing User: {user_id_str} ({len(entries)} keywords)")
        
        for entry in entries:
            keyword = entry['keyword']
            logger.debug(f"  - Checking keyword: '{keyword}'...")
            try:
                found_reports = fetch_data(keyword=keyword, user_id=user_id_str)

                if found_reports:
                    logger.info(f"    * Found {len(found_reports)} reports for keyword: '{keyword}'")
                    message = f"===== 알림 키워드 : {keyword} =====\n"
                    message += format_message_sql(found_reports)
                    
                    await sendMarkDownText(token=TOKEN, chat_id=user_id_str, sendMessageText=message)
                    update_data(keyword=keyword, user_id=user_id_str)
                else:
                    logger.debug(f"    * No new reports found for keyword: '{keyword}'")
            except Exception as e:
                logger.error(f"Error processing keyword '{keyword}' for user {user_id_str}: {e}")

async def main():
    logger.info("Starting User Report Keyword Alert Service...")
    
    # RUN_ONCE 환경 변수가 설정되어 있으면 한 번만 실행
    if os.getenv('RUN_ONCE', 'false').lower() == 'true':
        logger.info("--- [Single Run Start] ---")
        await run_once()
        logger.info("--- [Single Run End] ---")
        return

    while True:
        now = datetime.now()
        logger.info(f"--- [Loop Start: {now.strftime('%Y-%m-%d %H:%M:%S')}] ---")
        try:
            await run_once()
        except Exception as e:
            logger.error(f"Error in run_once: {e}")
        
        logger.info(f"Waiting for {INTERVAL}s until next check...")
        await asyncio.sleep(INTERVAL)

if __name__ == '__main__':
    asyncio.run(main())
