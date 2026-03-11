import asyncio
import oracledb
import os
import sys
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class OracleManager:
    def __init__(self):
        """Oracle 데이터베이스 연결 초기화 (안정적인 동기 방식 기반)"""
        load_dotenv(override=True)
        self._init_thick_mode()

    def _init_thick_mode(self):
        """Thick 모드 초기화 시도 (Wallet 연동을 위해 필요한 경우)"""
        try:
            lib_dir = "/opt/oracle/instantclient_19_10"
            if os.path.exists(lib_dir):
                oracledb.init_oracle_client(lib_dir=lib_dir)
            else:
                oracledb.init_oracle_client()
        except Exception:
            pass

    def _get_connection_sync(self):
        """동기 방식으로 연결 객체 생성"""
        wl = os.path.expanduser(os.getenv('WALLET_LOCATION'))
        return oracledb.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            dsn=os.getenv('DB_DSN'),
            config_dir=wl,
            wallet_location=wl,
            wallet_password=os.getenv('WALLET_PASSWORD')
        )

    def _insert_sync_process(self, json_data_list):
        """데이터 삽입/업데이트를 수행하는 동기 메서드 (데이터 보호형 MERGE)"""
        if not json_data_list:
            return 0
            
        conn = self._get_connection_sync()
        # Oracle 스키마에 기반한 MERGE 쿼리
        # NVL(s.COL, t.COL)을 사용하여 소스 데이터가 빈 값(NULL)일 경우 기존 오라클 데이터를 유지함
        query = """
        MERGE INTO DATA_MAIN_DAILY_SEND t
        USING (SELECT :REPORT_ID as REPORT_ID, :SEC_FIRM_ORDER as SEC_FIRM_ORDER, 
                      :ARTICLE_BOARD_ORDER as ARTICLE_BOARD_ORDER, :FIRM_NM as FIRM_NM, 
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
                t.SEC_FIRM_ORDER = NVL(s.SEC_FIRM_ORDER, t.SEC_FIRM_ORDER),
                t.ARTICLE_BOARD_ORDER = NVL(s.ARTICLE_BOARD_ORDER, t.ARTICLE_BOARD_ORDER),
                t.FIRM_NM = NVL(s.FIRM_NM, t.FIRM_NM),
                t.SEND_USER = NVL(s.SEND_USER, t.SEND_USER),
                t.MAIN_CH_SEND_YN = NVL(s.MAIN_CH_SEND_YN, t.MAIN_CH_SEND_YN),
                t.DOWNLOAD_STATUS_YN = NVL(s.DOWNLOAD_STATUS_YN, t.DOWNLOAD_STATUS_YN),
                t.SAVE_TIME = NVL(s.SAVE_TIME_STR, t.SAVE_TIME),
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
            INSERT (REPORT_ID, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, SEND_USER,
                    MAIN_CH_SEND_YN, DOWNLOAD_STATUS_YN, SAVE_TIME, REG_DT, WRITER, 
                    KEY, MKT_TP, ATTACH_URL, ARTICLE_TITLE, TELEGRAM_URL, 
                    ARTICLE_URL, DOWNLOAD_URL)
            VALUES (s.REPORT_ID, s.SEC_FIRM_ORDER, s.ARTICLE_BOARD_ORDER, s.FIRM_NM, s.SEND_USER,
                    s.MAIN_CH_SEND_YN, s.DOWNLOAD_STATUS_YN, s.SAVE_TIME_STR, s.REG_DT, s.WRITER, 
                    s.KEY, s.MKT_TP, s.ATTACH_URL, s.ARTICLE_TITLE, s.TELEGRAM_URL, 
                    s.ARTICLE_URL, s.DOWNLOAD_URL)
        """
        
        params_list = []
        for entry in json_data_list:
            # 키 소문자 대응 및 널 처리 최적화
            ci = {k.lower(): v for k, v in entry.items()}
            
            def get_val(key, max_len=None):
                val = ci.get(key.lower())
                if val is None or str(val).strip() == "":
                    return None # 오라클에서 NULL로 인식됨
                return str(val)[:max_len] if max_len else str(val)

            # SQLite의 id 또는 report_id를 Oracle의 REPORT_ID로 매핑
            r_id = ci.get("report_id") or ci.get("id")
            
            params_list.append({
                "REPORT_ID": r_id,
                "SEC_FIRM_ORDER": ci.get("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": ci.get("article_board_order"),
                "FIRM_NM": get_val("firm_nm", 100),
                "SEND_USER": get_val("send_user", 100),
                "MAIN_CH_SEND_YN": get_val("main_ch_send_yn", 100),
                "DOWNLOAD_STATUS_YN": get_val("download_status_yn", 100),
                "SAVE_TIME_STR": get_val("save_time", 100),
                "REG_DT": get_val("reg_dt", 100),
                "WRITER": get_val("writer", 100),
                "KEY": get_val("key", 4000),
                "MKT_TP": get_val("mkt_tp", 100),
                "ATTACH_URL": get_val("attach_url", 4000),
                "ARTICLE_TITLE": get_val("article_title", 4000),
                "TELEGRAM_URL": get_val("telegram_url", 4000),
                "ARTICLE_URL": get_val("article_url", 4000),
                "DOWNLOAD_URL": get_val("download_url", 4000)
            })
            
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
            print(f"✅ Oracle Merge Success: {len(params_list)} rows processed.")
            return len(params_list)
        except Exception as e:
            print(f"❌ Oracle Merge Error: {e}")
            return 0
        finally:
            conn.close()

    async def insert_json_data_list(self, json_data_list):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._insert_sync_process, json_data_list)

    async def bulk_insert(self, json_data_list):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._bulk_insert_sync, json_data_list)

    def _bulk_insert_sync(self, json_data_list):
        if not json_data_list:
            return 0
            
        conn = self._get_connection_sync()
        query = """
        INSERT /*+ APPEND_VALUES */ INTO DATA_MAIN_DAILY_SEND (
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
            if not dt_str or str(dt_str).strip() in ['', 'None']:
                return None
            dt_str = str(dt_str).replace('T', ' ').strip()
            formats = ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y%m%d%H%M%S', '%Y-%m-%d', '%Y%m%d']
            for fmt in formats:
                try:
                    return datetime.strptime(dt_str, fmt)
                except ValueError:
                    continue
            return None

        params_list = []
        for entry in json_data_list:
            ci = {k.lower(): v for k, v in entry.items()}
            def get_str(key, max_len=1000):
                val = ci.get(key.lower())
                if val is None or str(val).strip() == "":
                    return None # 공백 대신 실제 NULL 전달
                return str(val)[:max_len]

            params_list.append({
                "REPORT_ID": ci.get("report_id") or ci.get("id"),
                "SEC_FIRM_ORDER": ci.get("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": ci.get("article_board_order"),
                "FIRM_NM": get_str("firm_nm", 300),
                "REG_DT": get_str("reg_dt", 20),
                "ATTACH_URL": get_str("attach_url", 1000),
                "ARTICLE_TITLE": get_str("article_title", 1000),
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
            print(f"❌ Oracle Bulk Insert Error: {e}")
            return 0
        finally:
            conn.close()

    def _execute_query_sync(self, query, params=None):
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                if params: cursor.execute(query, params)
                else: cursor.execute(query)
                if query.strip().upper().startswith("SELECT"):
                    columns = [col[0] for col in cursor.description]
                    res = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in res]
                else:
                    conn.commit()
                    return cursor.rowcount
        except Exception as e:
            print(f"❌ Oracle Query Error: {e}")
            return []
        finally:
            conn.close()

    async def execute_query(self, query, params=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_query_sync, query, params)

    async def update_report_summary(self, record_id, summary, model_name):
        query = """
        UPDATE DATA_MAIN_DAILY_SEND
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :st, 
            SUMMARY_MODEL = :model
        WHERE REPORT_ID = :id
        """
        params = {"summary": summary, "st": datetime.now().isoformat(), "model": model_name, "id": record_id}
        return await self.execute_query(query, params)

    def truncate_table(self):
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute("TRUNCATE TABLE DATA_MAIN_DAILY_SEND")
                    print("✅ Table DATA_MAIN_DAILY_SEND truncated successfully.")
                except oracledb.DatabaseError as e:
                    if "ORA-00054" in str(e):
                        print("⚠️ Resource busy, using DELETE instead...")
                        cursor.execute("DELETE FROM DATA_MAIN_DAILY_SEND")
                        print("✅ Table DATA_MAIN_DAILY_SEND deleted successfully.")
                    else: raise e
                conn.commit()
            return True
        except Exception as e:
            print(f"❌ Clean Table Error: {e}")
            return False
        finally:
            conn.close()

    async def full_sync_from_sqlite(self):
        """오라클을 비우고(Truncate) SQLite 전체 데이터를 단 한 번의 네트워크 왕복으로 일괄 삽입"""
        from models.SQLiteManager import SQLiteManager
        print("🚀 Starting High-Speed Batch Sync (All-at-once) from SQLite to Oracle ATP...")
        
        # 1. 오라클 테이블 초기화 (데이터 변조 및 불안정성 제거)
        self.truncate_table()
        
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        
        # 2. SQLite 모든 데이터 한 번에 로드 (네트워크 왕복 최소화를 위해 일괄 추출)
        sqlite_db.cursor.execute("SELECT * FROM DATA_MAIN_DAILY_SEND")
        rows = sqlite_db.cursor.fetchall()
        
        if not rows:
            print("⚠️ No data found in SQLite.")
            sqlite_db.close_connection()
            return 0
            
        total_rows = len(rows)
        sqlite_data = [dict(row) for row in rows]
        print(f"📊 Total {total_rows:,} rows loaded from SQLite. Sending in ONE batch...")
        
        # 3. 최고속 일괄 삽입 (Single exec_many 호출로 네트워크 Latency 극복)
        # APPEND_VALUES 힌트와 Single Round-trip으로 성능 최적화
        total_synced = await self.bulk_insert(sqlite_data)
        
        sqlite_db.close_connection()
        print(f"✨ Successfully synced total {total_synced:,} rows to Oracle ATP in one go.")
        return total_synced

if __name__ == "__main__":
    import sys
    async def main():
        om = OracleManager()
        if len(sys.argv) > 1 and sys.argv[1] == "full_insert":
            print("!!! FULL INSERT MODE !!!")
            await om.full_sync_from_sqlite()
        else:
            res = await om.execute_query("SELECT count(*) FROM DATA_MAIN_DAILY_SEND")
            print(f"Test Result: {res}")
    asyncio.run(main())
