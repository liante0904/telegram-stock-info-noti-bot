import asyncio
import logging
import os
import sys

# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.SQLiteManager import SQLiteManager
from models.OracleManager import OracleManager

class DataManager:
    def __init__(self):
        self.sqlite = SQLiteManager()
        self.oracle = OracleManager()
        self.logger = logging.getLogger("DataManager")

    async def insert_json_data_list(self, json_data_list, table_name='data_main_daily_send'):
        """SQLite에 저장하고 Oracle(TB_SEC_REPORTS)에 동기화 시도"""
        # 1. SQLite 저장 (로컬 원장 우선)
        # SQLiteManager의 insert_json_data_list는 동기 함수이므로 그대로 호출
        inserted_count, updated_count = self.sqlite.insert_json_data_list(json_data_list, table_name)
        
        # 2. Oracle 동기화 (비동기 처리)
        try:
            # Oracle용 테이블명은 고정이므로 무시하고 OracleManager의 로직 사용
            await self.oracle.insert_json_data_list(json_data_list)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Insert): {str(e)}")
            print(f"⚠️ [Oracle Sync Error] 데이터 동기화 실패 (무시하고 진행): {e}")

        return inserted_count, updated_count

    async def daily_select_data(self, date_str=None, type=None):
        """데이터 조회 (현재 로컬 원장인 SQLite에서 조회)"""
        # 텔레그램 발송 등 실시간 처리는 로컬 원장을 기준으로 함
        return await self.sqlite.daily_select_data(date_str, type)

    async def daily_update_data(self, date_str=None, fetched_rows=None, type=None):
        """상태 업데이트 (SQLite & Oracle 동시 업데이트)"""
        # 1. SQLite 업데이트
        res = await self.sqlite.daily_update_data(date_str, fetched_rows, type)
        
        # 2. Oracle 업데이트 시도
        try:
            await self.oracle.daily_update_data(fetched_rows, type)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Update Status): {str(e)}")
            print(f"⚠️ [Oracle Sync Error] 상태 업데이트 동기화 실패: {e}")
            
        return res

    async def update_telegram_url(self, record_id, telegram_url, article_title=None):
        """텔레그램 URL 및 제목 업데이트 (Dual-Write)"""
        # 1. SQLite 업데이트
        res = await self.sqlite.update_telegram_url(record_id, telegram_url, article_title)
        
        # 2. Oracle 업데이트 시도
        try:
            # Oracle에서는 REPORT_ID를 기준으로 업데이트해야 함
            # SQLite의 record_id를 그대로 사용할 수 없는 경우(ID가 다른 경우) 
            # SQLite에서 해당 레코드의 KEY를 가져와서 Oracle에 적용하는 것이 더 정확함
            # 하지만 현재는 동일하다고 가정하거나, OracleManager 내부에서 KEY 기준 처리를 고민해야 함
            # 일단 id 기준으로 시도
            await self.oracle.update_telegram_url(record_id, telegram_url, article_title)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Telegram URL): {str(e)}")
            print(f"⚠️ [Oracle Sync Error] 텔레그램 URL 동기화 실패: {e}")
            
        return res

    async def fetch_daily_articles_by_date(self, firm_info, date_str=None):
        """특정 날짜의 기사 조회 (SQLite 기준)"""
        return await self.sqlite.fetch_daily_articles_by_date(firm_info, date_str)

    async def update_report_summary(self, record_id, summary, model_name):
        """Gemini 요약 업데이트 (Dual-Write)"""
        res = await self.sqlite.update_report_summary(record_id, summary, model_name)
        try:
            await self.oracle.update_report_summary(record_id, summary, model_name)
        except Exception as e:
            self.logger.error(f"Oracle Sync Error (Summary): {str(e)}")
            
        return res

    # 기타 SQLite 전용 메서드 브릿지
    def open_connection(self): self.sqlite.open_connection()
    def close_connection(self): self.sqlite.close_connection()
    async def execute_query(self, query, params=None): return await self.sqlite.execute_query(query, params)
