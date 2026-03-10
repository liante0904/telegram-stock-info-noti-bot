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
        """데이터 삽입을 수행하는 동기 메서드 (MERGE 방식)"""
        if not json_data_list:
            return 0
            
        conn = self._get_connection_sync()
        query = """
        MERGE INTO DATA_MAIN_DAILY_SEND t
        USING (SELECT :REPORT_ID as REPORT_ID, :SEC_FIRM_ORDER as SEC_FIRM_ORDER, :ARTICLE_BOARD_ORDER as ARTICLE_BOARD_ORDER, 
                      :FIRM_NM as FIRM_NM, :REG_DT as REG_DT, :ATTACH_URL as ATTACH_URL, 
                      :ARTICLE_TITLE as ARTICLE_TITLE, :ARTICLE_URL as ARTICLE_URL, 
                      :MAIN_CH_SEND_YN as MAIN_CH_SEND_YN, :DOWNLOAD_URL as DOWNLOAD_URL, 
                      :TELEGRAM_URL as TELEGRAM_URL, :WRITER as WRITER, :MKT_TP as MKT_TP, 
                      :KEY as KEY, TO_TIMESTAMP(:SAVE_TIME, 'YYYY-MM-DD"T"HH24:MI:SS.FF') as SAVE_TIME
               FROM DUAL) s
        ON (t.KEY = s.KEY)
        WHEN MATCHED THEN
            UPDATE SET 
                t.REG_DT = s.REG_DT,
                t.WRITER = s.WRITER,
                t.MKT_TP = s.MKT_TP,
                t.DOWNLOAD_URL = CASE WHEN s.DOWNLOAD_URL IS NOT NULL THEN s.DOWNLOAD_URL ELSE t.DOWNLOAD_URL END,
                t.TELEGRAM_URL = CASE WHEN s.TELEGRAM_URL IS NOT NULL AND s.TELEGRAM_URL != '' THEN s.TELEGRAM_URL ELSE t.TELEGRAM_URL END
        WHEN NOT MATCHED THEN
            INSERT (REPORT_ID, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT, ATTACH_URL, 
                    ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, DOWNLOAD_URL, 
                    TELEGRAM_URL, WRITER, MKT_TP, KEY, SAVE_TIME)
            VALUES (s.REPORT_ID, s.SEC_FIRM_ORDER, s.ARTICLE_BOARD_ORDER, s.FIRM_NM, s.REG_DT, s.ATTACH_URL, 
                    s.ARTICLE_TITLE, s.ARTICLE_URL, s.MAIN_CH_SEND_YN, s.DOWNLOAD_URL, 
                    s.TELEGRAM_URL, s.WRITER, s.MKT_TP, s.KEY, s.SAVE_TIME)
        """
        
        params_list = []
        for entry in json_data_list:
            title = entry.get("ARTICLE_TITLE") or ""
            st = str(entry.get("SAVE_TIME") or "").replace(" ", "T")
            if "T" in st and len(st) == 19: st = st + ".000000"
            elif len(st) == 8 and "-" not in st: st = f"{st[:4]}-{st[4:6]}-{st[6:8]}T00:00:00.000000"

            params_list.append({
                "REPORT_ID": entry.get("id"),
                "SEC_FIRM_ORDER": entry.get("SEC_FIRM_ORDER"),
                "ARTICLE_BOARD_ORDER": entry.get("ARTICLE_BOARD_ORDER"),
                "FIRM_NM": entry.get("FIRM_NM") or " ",
                "REG_DT": entry.get("REG_DT") or " ",
                "ATTACH_URL": entry.get("ATTACH_URL") or " ",
                "ARTICLE_TITLE": title[:1000],
                "ARTICLE_URL": entry.get("ARTICLE_URL") or " ",
                "MAIN_CH_SEND_YN": entry.get("MAIN_CH_SEND_YN") or "N",
                "DOWNLOAD_URL": entry.get("DOWNLOAD_URL") or " ",
                "TELEGRAM_URL": entry.get("TELEGRAM_URL") or " ",
                "WRITER": entry.get("WRITER") or " ",
                "MKT_TP": entry.get("MKT_TP") or "KR",
                "KEY": entry.get("KEY") or " ",
                "SAVE_TIME": st
            })
            
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
            print(f"✅ Oracle Sync Success: {len(params_list)} rows processed.")
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
            """날짜 문자열을 datetime 객체로 안전하게 변환"""
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
            # 안전한 추출을 위해 키를 소문자로 통일
            ci = {k.lower(): v for k, v in entry.items()}

            def get_val(key):
                return ci.get(key.lower())

            def get_str(key, max_len=1000, default_if_null=None):
                """원본 값 유지, 지정된 경우에만 널 방지"""
                val = ci.get(key.lower())
                if val is None or str(val).strip() == "":
                    return default_if_null
                return str(val)[:max_len]

            def get_num(key, default=None):
                """숫자 값 유지 (0 포함)"""
                val = ci.get(key.lower())
                if val is None or str(val).strip() == "":
                    return default
                try:
                    return int(val)
                except:
                    return default

            # ID 추출
            r_id = get_num("id")
            if r_id is None:
                r_id = get_num("report_id")

            # REG_DT 자동 보정
            reg_dt = get_str("reg_dt", 20)
            st_raw = get_val("save_time")
            if not reg_dt:
                if st_raw and "-" in str(st_raw):
                    reg_dt = str(st_raw).split('T')[0].replace('-', '')
                elif st_raw and len(str(st_raw)) >= 8:
                    reg_dt = str(st_raw)[:8]

            params_list.append({
                "REPORT_ID": r_id,
                "SEC_FIRM_ORDER": get_num("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": get_num("article_board_order"),
                "FIRM_NM": get_str("firm_nm", 300),
                "REG_DT": reg_dt,
                "ATTACH_URL": get_str("attach_url", 1000),
                "ARTICLE_TITLE": get_str("article_title", 1000),
                "ARTICLE_URL": get_str("article_url", 1000),
                "MAIN_CH_SEND_YN": get_str("main_ch_send_yn", 1, "N"),
                # Oracle NOT NULL 제약조건이 걸려있는 컬럼들만 최소한의 공백 우회
                "DOWNLOAD_URL": get_str("download_url", 1000, " "), 
                "TELEGRAM_URL": get_str("telegram_url", 1000),
                "WRITER": get_str("writer", 200),
                "MKT_TP": get_str("mkt_tp", 10, "KR"),
                "KEY": get_str("key", 1000, " "), # 필수 컬럼 우회
                "SAVE_TIME": parse_dt(st_raw),
                "GEMINI_SUMMARY": get_str("gemini_summary", 4000),
                "SUMMARY_TIME": parse_dt(get_val("summary_time")),
                "SUMMARY_MODEL": get_str("summary_model", 100)
            })
            
        try:
            with conn.cursor() as cursor:
                cursor.setinputsizes(
                    REPORT_ID=oracledb.DB_TYPE_NUMBER,
                    SEC_FIRM_ORDER=oracledb.DB_TYPE_NUMBER,
                    ARTICLE_BOARD_ORDER=oracledb.DB_TYPE_NUMBER,
                    SAVE_TIME=oracledb.DB_TYPE_TIMESTAMP,
                    SUMMARY_TIME=oracledb.DB_TYPE_TIMESTAMP,
                    GEMINI_SUMMARY=oracledb.DB_TYPE_CLOB
                )
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
        from models.SQLiteManager import SQLiteManager
        print("🚀 Starting full sync from SQLite to Oracle...")
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        sqlite_db.cursor.execute("SELECT count(*) FROM DATA_MAIN_DAILY_SEND")
        total_rows = sqlite_db.cursor.fetchone()[0]
        print(f"📊 Total rows to sync: {total_rows:,}")
        if total_rows == 0:
            print("⚠️ No data found in SQLite.")
            sqlite_db.close_connection()
            return 0
        self.truncate_table()
        chunk_size = 10000
        offset = 0
        total_synced = 0
        print(f"⚡ Bulk inserting in chunks of {chunk_size:,}...")
        while offset < total_rows:
            sqlite_db.cursor.execute(f"SELECT * FROM DATA_MAIN_DAILY_SEND LIMIT {chunk_size} OFFSET {offset}")
            rows = sqlite_db.cursor.fetchall()
            if not rows: break
            sqlite_data = [dict(row) for row in rows]
            count = await self.bulk_insert(sqlite_data)
            total_synced += count
            offset += chunk_size
            print(f"✅ Progress: {min(offset, total_rows):,} / {total_rows:,} rows synced...")
        sqlite_db.close_connection()
        print(f"✨ Successfully synced total {total_synced:,} rows.")
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
