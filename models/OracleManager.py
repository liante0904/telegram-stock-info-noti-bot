import asyncio
import oracledb
import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class OracleManager:
    def __init__(self):
        """Oracle 데이터베이스 연결 초기화 및 설정 로드"""
        load_dotenv(override=True)
        self.logger = logging.getLogger("OracleManager")
        
        # 환경 변수 로드
        self.wallet_location = os.path.expanduser(os.getenv('WALLET_LOCATION', ''))
        self.wallet_password = os.getenv('WALLET_PASSWORD')
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.db_dsn = os.getenv('DB_DSN')
        
        self._init_thick_mode()

    def _init_thick_mode(self):
        """Thick 모드 초기화 (필요한 경우)"""
        try:
            lib_dir = "/opt/oracle/instantclient_19_10"
            if os.path.exists(lib_dir):
                oracledb.init_oracle_client(lib_dir=lib_dir)
            else:
                oracledb.init_oracle_client()
        except Exception:
            pass

    def _get_connection_sync(self):
        """동기 방식 연결 객체 생성"""
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
        """비동기 일반 쿼리 실행"""
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
            self.logger.error(f"Oracle Query Error: {e}")
            return [] if query.strip().upper().startswith("SELECT") else 0

    async def insert_json_data_list(self, json_data_list, table_name='DATA_MAIN_DAILY_SEND'):
        """데이터 삽입/업데이트 (MERGE 방식)"""
        if not json_data_list:
            return 0
            
        # 동기 메서드를 executor에서 실행하여 성능 확보
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._insert_sync_process, json_data_list, table_name)

    def _insert_sync_process(self, json_data_list, table_name='DATA_MAIN_DAILY_SEND'):
        """MERGE 쿼리를 사용한 동기 삽입 프로세스"""
        conn = self._get_connection_sync()
        query = f"""
        MERGE INTO {table_name} t
        USING (SELECT :REPORT_ID as REPORT_ID, :sec_firm_order as sec_firm_order, 
                      :article_board_order as article_board_order, :FIRM_NM as FIRM_NM, 
                      :SEND_USER as SEND_USER, :MAIN_CH_SEND_YN as MAIN_CH_SEND_YN, 
                      :DOWNLOAD_STATUS_YN as DOWNLOAD_STATUS_YN, :SAVE_TIME_STR as SAVE_TIME_STR,
                      :REG_DT as REG_DT, :WRITER as WRITER, :KEY as KEY, :MKT_TP as MKT_TP, 
                      :ATTACH_URL as ATTACH_URL, :ARTICLE_TITLE as ARTICLE_TITLE, 
                      :TELEGRAM_URL as TELEGRAM_URL, :ARTICLE_URL as ARTICLE_URL, 
                      :DOWNLOAD_URL as DOWNLOAD_URL
               FROM DUAL) s
        ON (t.REPORT_ID = s.REPORT_ID)
        WHEN MATCHED THEN
            UPDATE SET 
                t.sec_firm_order = NVL(s.sec_firm_order, t.sec_firm_order),
                t.article_board_order = NVL(s.article_board_order, t.article_board_order),
                t.FIRM_NM = NVL(s.FIRM_NM, t.FIRM_NM),
                t.SEND_USER = NVL(s.SEND_USER, t.SEND_USER),
                t.MAIN_CH_SEND_YN = NVL(s.MAIN_CH_SEND_YN, t.MAIN_CH_SEND_YN),
                t.DOWNLOAD_STATUS_YN = NVL(s.DOWNLOAD_STATUS_YN, t.DOWNLOAD_STATUS_YN),
                t.SAVE_TIME = NVL(TO_TIMESTAMP(s.SAVE_TIME_STR, 'YYYY-MM-DD HH24:MI:SS.FF'), t.SAVE_TIME),
                t.REG_DT = NVL(s.REG_DT, t.REG_DT),
                t.WRITER = NVL(s.WRITER, t.WRITER),
                t.KEY = NVL(s.KEY, t.KEY),
                t.MKT_TP = NVL(s.MKT_TP, t.MKT_TP),
                t.TELEGRAM_URL = NVL(s.TELEGRAM_URL, t.TELEGRAM_URL),
                t.ATTACH_URL = NVL(s.ATTACH_URL, t.ATTACH_URL),
                t.ARTICLE_TITLE = NVL(s.ARTICLE_TITLE, t.ARTICLE_TITLE),
                t.ARTICLE_URL = NVL(s.ARTICLE_URL, t.ARTICLE_URL),
                t.DOWNLOAD_URL = NVL(s.DOWNLOAD_URL, t.DOWNLOAD_URL)
        WHEN NOT MATCHED THEN
            INSERT (REPORT_ID, sec_firm_order, article_board_order, FIRM_NM, SEND_USER,
                    MAIN_CH_SEND_YN, DOWNLOAD_STATUS_YN, SAVE_TIME, REG_DT, WRITER, 
                    KEY, MKT_TP, ATTACH_URL, ARTICLE_TITLE, TELEGRAM_URL, 
                    ARTICLE_URL, DOWNLOAD_URL)
            VALUES (s.REPORT_ID, s.sec_firm_order, s.article_board_order, s.FIRM_NM, s.SEND_USER,
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

            def get_url_val(key, max_len=4000):
                val = get_str(key, max_len)
                if val: return val
                tg_url = get_str("telegram_url", max_len)
                if tg_url: return tg_url
                key_val = get_str("key", max_len)
                return key_val if key_val else "N/A"

            # SAVE_TIME 포맷 정규화
            st_raw = ci.get("save_time")
            st_str = str(st_raw).replace('T', ' ') if st_raw else None

            params_list.append({
                "REPORT_ID": ci.get("report_id"),
                "sec_firm_order": ci.get("sec_firm_order"),
                "article_board_order": ci.get("article_board_order"),
                "FIRM_NM": get_str("firm_nm", 100),
                "SEND_USER": get_str("send_user", 100),
                "MAIN_CH_SEND_YN": get_str("main_ch_send_yn", 100),
                "DOWNLOAD_STATUS_YN": get_str("download_status_yn", 100),
                "SAVE_TIME_STR": st_str,
                "REG_DT": get_str("reg_dt", 100),
                "WRITER": get_str("writer", 100),
                "KEY": get_str("key", 4000),
                "MKT_TP": get_str("mkt_tp", 100),
                "ATTACH_URL": get_url_val("attach_url", 4000),
                "ARTICLE_TITLE": get_str("article_title", 4000) or "No Title",
                "TELEGRAM_URL": get_str("telegram_url", 4000),
                "ARTICLE_URL": get_url_val("article_url", 4000),
                "DOWNLOAD_URL": get_url_val("download_url", 4000)
            })
            
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
            return len(params_list)
        except Exception as e:
            self.logger.error(f"Oracle Merge Error: {e}")
            return 0
        finally:
            conn.close()

    async def bulk_insert(self, json_data_list, table_name='DATA_MAIN_DAILY_SEND'):
        """대량 데이터 고속 삽입 (APPEND 힌트 사용)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._bulk_insert_sync, json_data_list, table_name)

    def _bulk_insert_sync(self, json_data_list, table_name='DATA_MAIN_DAILY_SEND'):
        if not json_data_list: return 0
        conn = self._get_connection_sync()
        query = f"""
        INSERT /*+ APPEND_VALUES */ INTO {table_name} (
            REPORT_ID, sec_firm_order, article_board_order, FIRM_NM, REG_DT, ATTACH_URL, 
            ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, DOWNLOAD_URL, 
            TELEGRAM_URL, WRITER, MKT_TP, KEY, SAVE_TIME,
            GEMINI_SUMMARY, SUMMARY_TIME, SUMMARY_MODEL
        ) VALUES (
            :REPORT_ID, :sec_firm_order, :article_board_order, :FIRM_NM, :REG_DT, :ATTACH_URL, 
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
                "sec_firm_order": ci.get("sec_firm_order"),
                "article_board_order": ci.get("article_board_order"),
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
                "GEMINI_SUMMARY": get_str("gemini_summary", 4000),
                "SUMMARY_TIME": parse_dt(ci.get("summary_time")),
                "SUMMARY_MODEL": get_str("summary_model", 100)
            })
            
        try:
            with conn.cursor() as cursor:
                cursor.setinputsizes(GEMINI_SUMMARY=oracledb.DB_TYPE_CLOB)
                cursor.executemany(query, params_list)
                conn.commit()
            return len(params_list)
        except Exception as e:
            self.logger.error(f"Oracle Bulk Insert Error: {e}")
            return 0
        finally:
            conn.close()

    async def update_report_summary(self, record_id, summary, model_name):
        """REPORT_ID 기준 요약 정보 업데이트"""
        query = """
        UPDATE DATA_MAIN_DAILY_SEND
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :st, 
            SUMMARY_MODEL = :model
        WHERE REPORT_ID = :id
        """
        params = {"summary": summary, "st": datetime.now(), "model": model_name, "id": record_id}
        return await self.execute_query(query, params)

    async def update_report_summary_by_telegram_url(self, telegram_url, summary, model_name):
        """TELEGRAM_URL 기준 최신 레코드 요약 정보 업데이트"""
        query = """
        UPDATE DATA_MAIN_DAILY_SEND
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :st, 
            SUMMARY_MODEL = :model
        WHERE TELEGRAM_URL = :url
          AND MAIN_CH_SEND_YN = 'Y'
          AND REPORT_ID = (
              SELECT MAX(REPORT_ID) FROM DATA_MAIN_DAILY_SEND 
              WHERE TELEGRAM_URL = :url AND MAIN_CH_SEND_YN = 'Y'
          )
        """
        params = {"summary": summary, "st": datetime.now(), "model": model_name, "url": telegram_url}
        return await self.execute_query(query, params)

    async def update_telegram_url(self, record_id, telegram_url, article_title=None, pdf_url=None):
        """텔레그램 URL, PDF URL 및 선택적 제목 업데이트"""
        if pdf_url is None:
            pdf_url = telegram_url
        if article_title:
            query = "UPDATE DATA_MAIN_DAILY_SEND SET TELEGRAM_URL = :url, PDF_URL = :pdf_url, ARTICLE_TITLE = :title WHERE REPORT_ID = :id"
            params = {"url": telegram_url, "pdf_url": pdf_url, "title": article_title, "id": record_id}
        else:
            query = "UPDATE DATA_MAIN_DAILY_SEND SET TELEGRAM_URL = :url, PDF_URL = :pdf_url WHERE REPORT_ID = :id"
            params = {"url": telegram_url, "pdf_url": pdf_url, "id": record_id}
        return await self.execute_query(query, params)

    async def daily_select_data(self, date_str=None, type=None):
        """날짜별 전송/다운로드 대상 데이터 조회"""
        if type not in ['send', 'download']:
            raise ValueError("Type must be 'send' or 'download'")

        today = datetime.now()
        if date_str:
            q_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            base_dt = datetime.strptime(date_str, '%Y%m%d')
        else:
            q_date = today.strftime('%Y-%m-%d')
            base_dt = today

        reg_dt_start = (base_dt - timedelta(days=3)).strftime('%Y%m%d')
        reg_dt_end = (base_dt + timedelta(days=2)).strftime('%Y%m%d')

        condition = "MAIN_CH_SEND_YN = 'Y' AND DOWNLOAD_STATUS_YN != 'Y'" if type == 'download' else \
                    "(MAIN_CH_SEND_YN != 'Y' OR MAIN_CH_SEND_YN IS NULL) AND (sec_firm_order != 19 OR (sec_firm_order = 19 AND TELEGRAM_URL IS NOT NULL))"

        query = f"""
        SELECT * FROM DATA_MAIN_DAILY_SEND 
        WHERE TO_CHAR(SAVE_TIME, 'YYYY-MM-DD') = '{q_date}'
          AND REG_DT BETWEEN '{reg_dt_start}' AND '{reg_dt_end}'
          AND {condition}
        ORDER BY sec_firm_order, article_board_order, SAVE_TIME
        """
        return await self.execute_query(query)

    async def daily_update_data(self, fetched_rows=None, type=None, date_str=None):
        """상태 업데이트 (fetched_rows가 리스트 또는 단일 딕셔너리일 수 있음)"""
        if not fetched_rows: return 0
        if isinstance(fetched_rows, dict): fetched_rows = [fetched_rows]
        
        col = "DOWNLOAD_STATUS_YN" if type == "download" else "MAIN_CH_SEND_YN"
        query = f"UPDATE DATA_MAIN_DAILY_SEND SET {col} = 'Y' WHERE REPORT_ID = :id"
        
        async with await self._get_connection_async() as conn:
            async with conn.cursor() as cursor:
                params = [{"id": row.get("report_id")} for row in fetched_rows]
                await cursor.executemany(query, params)
                await conn.commit()
                return cursor.rowcount

    async def fetch_daily_articles_by_date(self, firm_info, date_str=None):
        """텔레그램 URL 갱신이 필요한 데이터 조회"""
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        sec_firm_order = firm_info.get_state()["sec_firm_order"]
        
        query = f"""
        SELECT * FROM DATA_MAIN_DAILY_SEND
        WHERE REG_DT BETWEEN TO_CHAR(TO_DATE('{query_date}', 'YYYYMMDD') - 3, 'YYYYMMDD')
                        AND TO_CHAR(TO_DATE('{query_date}', 'YYYYMMDD') + 2, 'YYYYMMDD')
          AND sec_firm_order = :sec_order
          AND KEY IS NOT NULL
          AND TELEGRAM_URL IS NULL
        ORDER BY sec_firm_order, article_board_order, SAVE_TIME
        """
        return await self.execute_query(query, {"sec_order": sec_firm_order})

    def truncate_table(self, table_name='DATA_MAIN_DAILY_SEND'):
        """테이블 초기화"""
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(f"TRUNCATE TABLE {table_name}")
                except oracledb.DatabaseError as e:
                    if "ORA-00054" in str(e):
                        cursor.execute(f"DELETE FROM {table_name}")
                    else: raise e
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"Truncate Error: {e}")
            return False
        finally:
            conn.close()

    async def full_sync_from_sqlite(self):
        """SQLite 데이터를 Oracle로 고속 전체 동기화"""
        from models.SQLiteManager import SQLiteManager
        self.truncate_table()
        
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        sqlite_db.cursor.execute("SELECT count(*) FROM DATA_MAIN_DAILY_SEND")
        total_rows = sqlite_db.cursor.fetchone()[0]
        
        if total_rows == 0:
            sqlite_db.close_connection()
            return 0
            
        chunk_size = 10000
        offset = 0
        total_synced = 0
        
        while offset < total_rows:
            sqlite_db.cursor.execute(f"SELECT * FROM DATA_MAIN_DAILY_SEND LIMIT {chunk_size} OFFSET {offset}")
            rows = sqlite_db.cursor.fetchall()
            if not rows: break
            
            sqlite_data = [dict(row) for row in rows]
            count = await self.bulk_insert(sqlite_data)
            total_synced += count
            offset += chunk_size
            print(f"✅ Syncing... {min(offset, total_rows)}/{total_rows}")
            
        sqlite_db.close_connection()
        return total_synced

    async def sync_recent_from_sqlite(self, hours=3):
        """최근 N시간 데이터를 SQLite에서 Oracle로 MERGE 동기화"""
        from models.SQLiteManager import SQLiteManager
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        query = f"SELECT * FROM DATA_MAIN_DAILY_SEND WHERE SAVE_TIME >= datetime('now', '-{hours} hour', 'localtime')"
        sqlite_db.cursor.execute(query)
        rows = sqlite_db.cursor.fetchall()
        sqlite_data = [dict(row) for row in rows]
        sqlite_db.close_connection()
        
        if not sqlite_data: return 0
        return await self.insert_json_data_list(sqlite_data)

    async def sync_all_from_sqlite(self):
        """전체 데이터를 SQLite에서 Oracle로 MERGE 동기화 (기존 데이터 보존)"""
        from models.SQLiteManager import SQLiteManager
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        sqlite_db.cursor.execute("SELECT * FROM DATA_MAIN_DAILY_SEND")
        rows = sqlite_db.cursor.fetchall()
        sqlite_data = [dict(row) for row in rows]
        sqlite_db.close_connection()
        
        if not sqlite_data: return 0
        
        chunk_size = 10000
        total = 0
        for i in range(0, len(sqlite_data), chunk_size):
            chunk = sqlite_data[i:i + chunk_size]
            count = await self.insert_json_data_list(chunk)
            total += count
            print(f"✅ Merging... {total}/{len(sqlite_data)}")
        return total

if __name__ == "__main__":
    import sys
    async def main():
        om = OracleManager()
        if len(sys.argv) > 1:
            cmd = sys.argv[1]
            if cmd == "full_insert": await om.full_sync_from_sqlite()
            elif cmd == "sync_all": await om.sync_all_from_sqlite()
            elif cmd == "sync_recent":
                hours = int(sys.argv[2]) if len(sys.argv) > 2 else 3
                await om.sync_recent_from_sqlite(hours)
        else:
            res = await om.execute_query("SELECT count(*) as cnt FROM DATA_MAIN_DAILY_SEND")
            print(f"Current Oracle Row Count: {res[0]['cnt'] if res else 0}")

    asyncio.run(main())
