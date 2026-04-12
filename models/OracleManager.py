# -*- coding:utf-8 -*- 
import asyncio
import oracledb
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class OracleManager:
    def __init__(self):
        """Oracle 데이터베이스 연결 초기화 (Thin 모드 기반 비동기 최적화)"""
        load_dotenv(override=True)
        self.main_table_name = os.getenv("MAIN_TABLE_NAME", "data_main_daily_send").upper()
        
        # 환경 변수 로드
        self.wallet_location = os.path.expanduser(os.getenv('WALLET_LOCATION', ''))
        self.wallet_password = os.getenv('WALLET_PASSWORD')
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.db_dsn = os.getenv('DB_DSN') or os.getenv('DB_DSN_LOW')
        
        # Thick 모드 초기화 (필요한 경우에만 수행)
        self._init_thick_mode()

    def _init_thick_mode(self):
        """Thick 모드 초기화 시도 (Wallet 연동 안정성을 위해)"""
        try:
            lib_dir = "/opt/oracle/instantclient_19_10"
            if os.path.exists(lib_dir):
                oracledb.init_oracle_client(lib_dir=lib_dir)
            else:
                oracledb.init_oracle_client()
        except Exception:
            pass

    def _get_connection_sync(self):
        """동기 방식 연결 객체 생성 (Bulk/Sync 처리용)"""
        return oracledb.connect(
            user=self.db_user,
            password=self.db_password,
            dsn=self.db_dsn,
            config_dir=self.wallet_location,
            wallet_location=self.wallet_location,
            wallet_password=self.wallet_password
        )

    async def _get_connection_async(self):
        """비동기 방식 연결 객체 생성"""
        return await oracledb.connect_async(
            user=self.db_user,
            password=self.db_password,
            dsn=self.db_dsn,
            config_dir=self.wallet_location,
            wallet_location=self.wallet_location,
            wallet_password=self.wallet_password
        )

    async def execute_query(self, query, params=None):
        """비동기 일반 쿼리 실행 및 결과 변환"""
        try:
            async with await self._get_connection_async() as conn:
                async with conn.cursor() as cursor:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    
                    if query.strip().upper().startswith("SELECT"):
                        columns = [col[0].lower() for col in cursor.description]
                        res = await cursor.fetchall()
                        return [dict(zip(columns, row)) for row in res]
                    else:
                        await conn.commit()
                        return cursor.rowcount
        except Exception as e:
            logger.error(f"Oracle Query Error: {e}")
            return [] if query.strip().upper().startswith("SELECT") else 0

    async def insert_json_data_list(self, json_data_list):
        """데이터 삽입/업데이트 (MERGE 방식) - 비동기 호출 인터페이스"""
        if not json_data_list:
            return 0
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._insert_sync_process, json_data_list)

    def _insert_sync_process(self, json_data_list):
        """데이터 보호형 MERGE 프로세스 (안정적인 동기 방식)"""
        conn = self._get_connection_sync()
        # Oracle 스키마에 기반한 MERGE 쿼리 (TO_TIMESTAMP 적용)
        query = f"""
        MERGE INTO {self.main_table_name} t
        USING (SELECT :REPORT_ID as REPORT_ID, :SEC_FIRM_ORDER as SEC_FIRM_ORDER, 
                      :ARTICLE_BOARD_ORDER as ARTICLE_BOARD_ORDER, :FIRM_NM as FIRM_NM, 
                      :SEND_USER as SEND_USER, :MAIN_CH_SEND_YN as MAIN_CH_SEND_YN, 
                      :DOWNLOAD_STATUS_YN as DOWNLOAD_STATUS_YN, :SAVE_TIME_STR as SAVE_TIME_STR, 
                      :REG_DT as REG_DT, :WRITER as WRITER, :KEY as KEY, :MKT_TP as MKT_TP, 
                      :ATTACH_URL as ATTACH_URL, :ARTICLE_TITLE as ARTICLE_TITLE, 
                      :TELEGRAM_URL as TELEGRAM_URL, :ARTICLE_URL as ARTICLE_URL, 
                      :DOWNLOAD_URL as DOWNLOAD_URL FROM dual) s
        ON (t.KEY = s.KEY)
        WHEN MATCHED THEN
            UPDATE SET 
                t.SEC_FIRM_ORDER = NVL(s.SEC_FIRM_ORDER, t.SEC_FIRM_ORDER),
                t.ARTICLE_BOARD_ORDER = NVL(s.ARTICLE_BOARD_ORDER, t.ARTICLE_BOARD_ORDER),
                t.FIRM_NM = NVL(s.FIRM_NM, t.FIRM_NM),
                t.SEND_USER = NVL(s.SEND_USER, t.SEND_USER),
                t.MAIN_CH_SEND_YN = NVL(s.MAIN_CH_SEND_YN, t.MAIN_CH_SEND_YN),
                t.DOWNLOAD_STATUS_YN = NVL(s.DOWNLOAD_STATUS_YN, t.DOWNLOAD_STATUS_YN),
                t.SAVE_TIME = NVL(TO_TIMESTAMP(s.SAVE_TIME_STR, 'YYYY-MM-DD HH24:MI:SS.FF'), t.SAVE_TIME),
                t.REG_DT = NVL(s.REG_DT, t.REG_DT),
                t.WRITER = NVL(s.WRITER, t.WRITER),
                t.MKT_TP = NVL(s.MKT_TP, t.MKT_TP),
                t.ATTACH_URL = NVL(s.ATTACH_URL, t.ATTACH_URL),
                t.ARTICLE_TITLE = NVL(s.ARTICLE_TITLE, t.ARTICLE_TITLE),
                t.TELEGRAM_URL = NVL(s.TELEGRAM_URL, t.TELEGRAM_URL),
                t.ARTICLE_URL = NVL(s.ARTICLE_URL, t.ARTICLE_URL),
                t.DOWNLOAD_URL = NVL(s.DOWNLOAD_URL, t.DOWNLOAD_URL)
        WHEN NOT MATCHED THEN
            INSERT (REPORT_ID, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, SEND_USER,
                    MAIN_CH_SEND_YN, DOWNLOAD_STATUS_YN, SAVE_TIME, REG_DT, WRITER, 
                    KEY, MKT_TP, ATTACH_URL, ARTICLE_TITLE, TELEGRAM_URL, 
                    ARTICLE_URL, DOWNLOAD_URL)
            VALUES (s.REPORT_ID, s.SEC_FIRM_ORDER, s.ARTICLE_BOARD_ORDER, s.FIRM_NM, s.SEND_USER,
                    s.MAIN_CH_SEND_YN, s.DOWNLOAD_STATUS_YN, TO_TIMESTAMP(s.SAVE_TIME_STR, 'YYYY-MM-DD HH24:MI:SS.FF'), s.REG_DT, s.WRITER, 
                    s.KEY, s.MKT_TP, s.ATTACH_URL, s.ARTICLE_TITLE, s.TELEGRAM_URL, 
                    s.ARTICLE_URL, s.DOWNLOAD_URL)
        """
        params_list = []
        for entry in json_data_list:
            ci = {k.lower(): v for k, v in entry.items()}
            
            def get_str(key, max_len=None):
                val = ci.get(key.lower())
                if val is None or str(val).strip() == "": return None
                return str(val)[:max_len] if max_len else str(val)

            st_raw = ci.get("save_time")
            st_str = str(st_raw).replace('T', ' ') if st_raw else None

            params_list.append({
                "REPORT_ID": ci.get("report_id"),
                "SEC_FIRM_ORDER": ci.get("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": ci.get("article_board_order"),
                "FIRM_NM": get_str("firm_nm", 100),
                "SEND_USER": get_str("send_user", 100),
                "MAIN_CH_SEND_YN": get_str("main_ch_send_yn", 100),
                "DOWNLOAD_STATUS_YN": get_str("download_status_yn", 100),
                "SAVE_TIME_STR": st_str,
                "REG_DT": get_str("reg_dt", 100),
                "WRITER": get_str("writer", 100),
                "KEY": get_str("key", 4000),
                "MKT_TP": get_str("mkt_tp", 100),
                "ATTACH_URL": get_str("attach_url", 4000),
                "ARTICLE_TITLE": get_str("article_title", 1000),
                "TELEGRAM_URL": get_str("telegram_url", 4000),
                "ARTICLE_URL": get_str("article_url", 4000),
                "DOWNLOAD_URL": get_str("download_url", 4000)
            })
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
            logger.info(f"✅ Oracle Merge Success: {len(params_list)} rows processed.")
            return len(params_list)
        except Exception as e:
            logger.error(f"❌ Oracle Merge Error: {e}")
            return 0
        finally:
            conn.close()

    async def bulk_insert(self, json_data_list):
        """대량 데이터 고속 삽입 (APPEND 힌트 사용)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._bulk_insert_sync, json_data_list)

    def _bulk_insert_sync(self, json_data_list):
        if not json_data_list: return 0
        conn = self._get_connection_sync()
        query = f"""
        INSERT /*+ APPEND_VALUES */ INTO {self.main_table_name} (
            REPORT_ID, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT, ATTACH_URL, 
            ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, DOWNLOAD_URL, 
            TELEGRAM_URL, WRITER, MKT_TP, KEY, SAVE_TIME,
            GEMINI_SUMMARY, SUMMARY_TIME, SUMMARY_MODEL
        ) VALUES (
            :REPORT_ID, :SEC_FIRM_ORDER, :ARTICLE_BOARD_ORDER, :FIRM_NM, :REG_DT, :ATTACH_URL, 
            :ARTICLE_TITLE, :ARTICLE_URL, :MAIN_CH_SEND_YN, :DOWNLOAD_URL, 
            :TELEGRAM_URL, :WRITER, :MKT_TP, :KEY, :SAVE_TIME,
            :GEMINI_SUMMARY, :SUMMARY_TIME, :SUMMARY_MODEL
        )
        """
        
        def parse_dt(dt_str):
            if not dt_str or str(dt_str).strip() in ['', 'None']: return None
            dt_str = str(dt_str).replace('T', ' ').strip()
            formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y%m%d%H%M%S', '%Y-%m-%d', '%Y%m%d']
            for fmt in formats:
                try: return datetime.strptime(dt_str, fmt)
                except ValueError: continue
            return None

        params_list = []
        for entry in json_data_list:
            ci = {k.lower(): v for k, v in entry.items()}
            def get_str(key, max_len=1000):
                val = ci.get(key.lower())
                return str(val)[:max_len] if val and str(val).strip() != "" else None

            params_list.append({
                "REPORT_ID": ci.get("report_id"),
                "SEC_FIRM_ORDER": ci.get("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": ci.get("article_board_order"),
                "FIRM_NM": get_str("firm_nm", 300),
                "REG_DT": get_str("reg_dt", 20),
                "ATTACH_URL": get_str("attach_url", 1000),
                "ARTICLE_TITLE": get_str("article_title", 1000) or "No Title",
                "ARTICLE_URL": get_str("article_url", 1000),
                "MAIN_CH_SEND_YN": get_str("main_ch_send_yn", 1) or "N",
                "DOWNLOAD_URL": get_str("download_url", 1000), 
                "TELEGRAM_URL": get_str("telegram_url", 1000),
                "WRITER": get_str("writer", 200),
                "MKT_TP": get_str("mkt_tp", 10) or "KR",
                "KEY": get_str("key", 1000),
                "SAVE_TIME": parse_dt(ci.get("save_time")),
                "GEMINI_SUMMARY": ci.get("gemini_summary"),
                "SUMMARY_TIME": parse_dt(ci.get("summary_time")),
                "SUMMARY_MODEL": get_str("summary_model", 100)
            })
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
            return len(params_list)
        except Exception as e:
            logger.error(f"❌ Oracle Bulk Insert Error: {e}")
            return 0
        finally:
            conn.close()

    async def update_report_summary(self, record_id, summary, model_name):
        query = f"UPDATE {self.main_table_name} SET GEMINI_SUMMARY = :summary, SUMMARY_TIME = :st, SUMMARY_MODEL = :model WHERE REPORT_ID = :id"
        params = {"summary": summary, "st": datetime.now(), "model": model_name, "id": record_id}
        return await self.execute_query(query, params)

    async def update_report_summary_by_telegram_url(self, telegram_url, summary, model_name):
        query = f"""
        UPDATE {self.main_table_name} SET GEMINI_SUMMARY = :summary, SUMMARY_TIME = :st, SUMMARY_MODEL = :model
        WHERE TELEGRAM_URL = :url AND MAIN_CH_SEND_YN = 'Y'
          AND REPORT_ID = (SELECT MAX(REPORT_ID) FROM {self.main_table_name} WHERE TELEGRAM_URL = :url AND MAIN_CH_SEND_YN = 'Y')
        """
        params = {"summary": summary, "st": datetime.now(), "model": model_name, "url": telegram_url}
        return await self.execute_query(query, params)

    async def update_telegram_url(self, record_id, telegram_url, article_title=None, pdf_url=None):
        """텔레그램 URL 및 PDF 경로 업데이트 (호환성 유지)"""
        if article_title:
            query = f"UPDATE {self.main_table_name} SET TELEGRAM_URL = :t_url, ARTICLE_TITLE = :title, ATTACH_URL = NVL(:pdf, ATTACH_URL) WHERE REPORT_ID = :id"
            params = {"t_url": telegram_url, "title": article_title, "pdf": pdf_url, "id": record_id}
        else:
            query = f"UPDATE {self.main_table_name} SET TELEGRAM_URL = :t_url, ATTACH_URL = NVL(:pdf, ATTACH_URL) WHERE REPORT_ID = :id"
            params = {"t_url": telegram_url, "pdf": pdf_url, "id": record_id}
        return await self.execute_query(query, params)

    async def daily_select_data(self, date_str=None, type='send'):
        if date_str is None:
            q_date = datetime.now().strftime('%Y-%m-%d')
            base_dt = datetime.now()
        else:
            q_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            base_dt = datetime.strptime(date_str, '%Y%m%d')

        reg_dt_start = (base_dt - timedelta(days=3)).strftime('%Y%m%d')
        reg_dt_end = (base_dt + timedelta(days=2)).strftime('%Y%m%d')

        if type == 'send':
            cond = "(MAIN_CH_SEND_YN != 'Y' OR MAIN_CH_SEND_YN IS NULL) AND (SEC_FIRM_ORDER != 19 OR (SEC_FIRM_ORDER = 19 AND TELEGRAM_URL IS NOT NULL))"
        else:
            cond = "MAIN_CH_SEND_YN = 'Y' AND DOWNLOAD_STATUS_YN != 'Y'"
            
        query = f"""
        SELECT * FROM {self.main_table_name} 
        WHERE TO_CHAR(SAVE_TIME, 'YYYY-MM-DD') = :dt 
          AND REG_DT BETWEEN :r_start AND :r_end
          AND {cond}
        ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
        """
        return await self.execute_query(query, {"dt": q_date, "r_start": reg_dt_start, "r_end": reg_dt_end})

    async def daily_update_data(self, fetched_rows=None, type='send', date_str=None):
        if not fetched_rows: return 0
        if isinstance(fetched_rows, dict): fetched_rows = [fetched_rows]
        
        ids = [r.get('REPORT_ID') or r.get('report_id') for r in fetched_rows]
        col = "MAIN_CH_SEND_YN" if type == 'send' else "DOWNLOAD_STATUS_YN"
        query = f"UPDATE {self.main_table_name} SET {col} = 'Y' WHERE REPORT_ID = :id"
        
        async with await self._get_connection_async() as conn:
            async with conn.cursor() as cursor:
                params = [{"id": rid} for rid in ids]
                await cursor.executemany(query, params)
                await conn.commit()
                return cursor.rowcount

    async def fetch_daily_articles_by_date(self, firm_info, date_str=None):
        q_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        f_info = firm_info.get_state()
        
        query = f"""
        SELECT * FROM {self.main_table_name}
        WHERE REG_DT BETWEEN TO_CHAR(TO_DATE(:dt, 'YYYYMMDD') - 3, 'YYYYMMDD')
                         AND TO_CHAR(TO_DATE(:dt, 'YYYYMMDD') + 2, 'YYYYMMDD')
          AND SEC_FIRM_ORDER = :sfo
          AND KEY IS NOT NULL
          AND (TELEGRAM_URL IS NULL OR TELEGRAM_URL = '')
        ORDER BY SAVE_TIME
        """
        return await self.execute_query(query, {"dt": q_date, "sfo": f_info["SEC_FIRM_ORDER"]})

    def truncate_table(self, table_name=None):
        t_name = table_name or self.main_table_name
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(f"TRUNCATE TABLE {t_name}")
                except oracledb.DatabaseError as e:
                    if "ORA-00054" in str(e):
                        cursor.execute(f"DELETE FROM {t_name}")
                    else: raise e
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Truncate Error: {e}")
            return False
        finally:
            conn.close()

    async def full_sync_from_sqlite(self):
        """SQLite에서 Oracle로 전체 고속 동기화"""
        from models.SQLiteManager import SQLiteManager
        logger.info("🚀 Starting Optimized Bulk Sync to Oracle...")
        self.truncate_table()
        
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        sqlite_db.cursor.execute(f"SELECT count(*) FROM {sqlite_db.main_table_name}")
        total_rows = sqlite_db.cursor.fetchone()[0]
        
        if total_rows == 0:
            sqlite_db.close_connection()
            return 0
            
        chunk_size = 10000
        offset = 0
        total_synced = 0
        
        while offset < total_rows:
            sqlite_db.cursor.execute(f"SELECT * FROM {sqlite_db.main_table_name} LIMIT {chunk_size} OFFSET {offset}")
            rows = sqlite_db.cursor.fetchall()
            if not rows: break
            
            sqlite_data = [dict(row) for row in rows]
            count = await self.bulk_insert(sqlite_data)
            total_synced += count
            offset += chunk_size
            logger.info(f"✅ Syncing... {min(offset, total_rows)}/{total_rows}")
            
        sqlite_db.close_connection()
        return total_synced

    async def sync_recent_from_sqlite(self, hours=3):
        """최근 N시간 데이터를 SQLite에서 Oracle로 MERGE 동기화"""
        from models.SQLiteManager import SQLiteManager
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        query = f"SELECT * FROM {sqlite_db.main_table_name} WHERE SAVE_TIME >= datetime('now', '-{hours} hour', 'localtime')"
        sqlite_db.cursor.execute(query)
        rows = sqlite_db.cursor.fetchall()
        sqlite_data = [dict(row) for row in rows]
        sqlite_db.close_connection()
        
        if not sqlite_data: return 0
        return await self.insert_json_data_list(sqlite_data)

# 하위 호환성을 위한 별칭 설정
OracleManagerSQL = OracleManager

if __name__ == "__main__":
    async def main():
        om = OracleManager()
        res = await om.execute_query(f"SELECT count(*) as cnt FROM {om.main_table_name}")
        print(f"Current Oracle Row Count: {res[0]['cnt'] if res else 0}")
    asyncio.run(main())
