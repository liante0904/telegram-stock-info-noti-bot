import asyncio
import logging
import os
import sys

# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.SQLiteManager import SQLiteManager
from models.OracleManager import OracleManager
from models.OracleManagerSQL import OracleManagerSQL

class DataManager:
    def __init__(self):
        self.sqlite = SQLiteManager()
        self.oracle = OracleManager()         # 신규 테이블 (TB_SEC_REPORTS)
        self.oracle_old = OracleManagerSQL()  # 기존 테이블 (data_main_daily_send)
        self.logger = logging.getLogger("DataManager")

    async def insert_json_data_list(self, json_data_list, table_name='data_main_daily_send'):
        """SQLite에 저장하고 Oracle(신규/기존)에 동기화 시도"""
        # 1. SQLite 저장 (로컬 원장 우선)
        inserted_count, updated_count = self.sqlite.insert_json_data_list(json_data_list, table_name)
        
        # 2. Oracle 동기화 (비동기 처리)
        try:
            await self.oracle.insert_json_data_list(json_data_list)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Insert New): {str(e)}")

        try:
            self.oracle_old.insert_json_data_list(json_data_list, table_name)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Insert Old): {str(e)}")

        return inserted_count, updated_count

    async def daily_select_data(self, date_str=None, type=None):
        """데이터 조회 (현재 로컬 원장인 SQLite에서 조회)"""
        return await self.sqlite.daily_select_data(date_str, type)

    async def daily_update_data(self, date_str=None, fetched_rows=None, type=None):
        """상태 업데이트 (SQLite & Oracle 동시 업데이트)"""
        res = await self.sqlite.daily_update_data(date_str, fetched_rows, type)
        try:
            await self.oracle.daily_update_data(fetched_rows, type)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Update Status New): {str(e)}")
        try:
            await self.oracle_old.daily_update_data(date_str, fetched_rows, type)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Update Status Old): {str(e)}")
        return res

    async def update_telegram_url(self, record_id, telegram_url, article_title=None):
        """텔레그램 URL 및 제목 업데이트 (Dual-Write)"""
        res = await self.sqlite.update_telegram_url(record_id, telegram_url, article_title)
        try:
            await self.oracle.update_telegram_url(record_id, telegram_url, article_title)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Telegram URL New): {str(e)}")
        try:
            await self.oracle_old.update_telegram_url(record_id, telegram_url, article_title)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Telegram URL Old): {str(e)}")
        return res

    async def fetch_daily_articles_by_date(self, firm_info, date_str=None):
        """특정 날짜의 기사 조회 (SQLite 기준)"""
        return await self.sqlite.fetch_daily_articles_by_date(firm_info, date_str)

    async def update_report_summary(self, record_id, summary, model_name, telegram_url=None):
        """Gemini 요약 업데이트 (Triple-Write)
        telegram_url이 있으면 run_gemini 로직(URL 기준)으로 업데이트합니다.
        """
        # 1. SQLite 업데이트
        if telegram_url:
            await self.sqlite.update_report_summary_by_telegram_url(telegram_url, summary, model_name)
        else:
            await self.sqlite.update_report_summary(record_id, summary, model_name)
        
        # 2. 신규 Oracle 업데이트 (REPORT_ID 기준)
        try:
            await self.oracle.update_report_summary(record_id, summary, model_name)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Summary New): {str(e)}")

        # 3. 기존 Oracle 업데이트 (run_gemini 로직 - URL 기준 우선)
        try:
            if telegram_url:
                await self.oracle_old.update_report_summary_by_telegram_url(telegram_url, summary, model_name)
            else:
                await self.oracle_old.update_report_summary(record_id, summary, model_name)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Summary Old): {str(e)}")
            
        return True

    # 기타 SQLite 전용 메서드 브릿지
    def open_connection(self): self.sqlite.open_connection()
    def close_connection(self): self.sqlite.close_connection()
    async def execute_query(self, query, params=None): return await self.sqlite.execute_query(query, params)
