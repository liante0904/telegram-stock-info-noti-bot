# -*- coding:utf-8 -*- 
import json
import sqlite3
import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# 프로젝트 루트 경로 추가 (run 폴더의 상위 경로)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.logger_util import setup_logger
setup_logger("send_report_by_keyword_to_user")

from utils.sqlite_util import format_message_sql
from utils.telegram_util import sendMarkDownText
from models.PostgreSQLManager import PostgreSQLManager

# 환경 변수 및 설정 로드
load_dotenv()
# SQLITE_DB_PATH 환경 변수를 최우선으로 사용
DB_PATH = os.getenv('SQLITE_DB_PATH', os.path.expanduser('~/sqlite3/telegram.db'))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
INTERVAL = int(os.getenv('INTERVAL', '1800')) # 기본 30분

# PostgreSQL 매니저 인스턴스 생성
pg_manager = PostgreSQLManager()

def parse_date(date_str):
    """날짜 형식을 YYYY-MM-DD로 통일하는 헬퍼 함수"""
    if date_str is None:
        return datetime.now().strftime('%Y-%m-%d')
    
    try:
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
    user_id_str = str(user_id)

    for table_name, url_col in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone(): continue

        query_parts.append(f"""
            SELECT FIRM_NM, ARTICLE_TITLE, {url_col} AS TELEGRAM_URL, SAVE_TIME, SEND_USER
            FROM {table_name}
            WHERE (ARTICLE_TITLE LIKE ? OR WRITER LIKE ?)
            AND DATE(SAVE_TIME) = ?
            AND NOT EXISTS (
                SELECT 1 FROM json_each(COALESCE(SEND_USER, '[]')) WHERE value = ?
            )
        """)
        params.extend([keyword_param, keyword_param, date, user_id_str])

    if not query_parts:
        conn.close()
        return []

    final_query = " UNION ".join(query_parts) + " ORDER BY SAVE_TIME ASC, FIRM_NM ASC"
    cursor.execute(final_query, params)
    results = cursor.fetchall()
    conn.close()
    return results

def update_data(date=None, keyword=None, user_id=None):
    """발송 완료한 사용자 ID를 SEND_USER JSON 배열에 추가 (중복 방지)"""
    date = parse_date(date)
    user_id_str = str(user_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    tables = ['data_main_daily_send', 'hankyungconsen_research', 'naver_research']

    for table in tables:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor.fetchone(): continue

        update_query = f"""
            UPDATE {table}
            SET SEND_USER = json_insert(COALESCE(SEND_USER, '[]'), '$[#]', ?)
            WHERE (ARTICLE_TITLE LIKE ? OR WRITER LIKE ?)
            AND DATE(SAVE_TIME) = ?
            AND NOT EXISTS (
                SELECT 1 FROM json_each(COALESCE(SEND_USER, '[]')) WHERE value = ?
            )
        """
        keyword_param = f"%{keyword}%"
        cursor.execute(update_query, (user_id_str, keyword_param, keyword_param, date, user_id_str))
        if cursor.rowcount > 0:
            logger.info(f"[{table}] {cursor.rowcount} rows updated for user {user_id}.")

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
        for entry in entries:
            keyword = entry['keyword']
            try:
                found_reports = fetch_data(keyword=keyword, user_id=user_id_str)
                if found_reports:
                    logger.success(f"[{user_id_str}] Found {len(found_reports)} reports for '{keyword}'")
                    message = f"===== 알림 키워드 : {keyword} =====\n"
                    message += format_message_sql(found_reports)
                    await sendMarkDownText(token=TOKEN, chat_id=user_id_str, sendMessageText=message)
                    update_data(keyword=keyword, user_id=user_id_str)
            except Exception as e:
                logger.error(f"Error processing '{keyword}' for {user_id_str}: {e}")

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
