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
            # 환경에 따라 instantclient 경로가 다를 수 있음
            lib_dir = "/opt/oracle/instantclient_19_10"
            if os.path.exists(lib_dir):
                oracledb.init_oracle_client(lib_dir=lib_dir)
            else:
                # 기본 경로 시도
                oracledb.init_oracle_client()
        except Exception:
            pass

    def _get_connection_sync(self):
        """동기 방식으로 연결 객체 생성 (검증된 방식)"""
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
            title = entry.get("ARTICLE_TITLE", "")
            mkt_tp = entry.get("MKT_TP", "KR")
            
            # SAVE_TIME 처리
            st = entry.get("SAVE_TIME", "")
            reg_dt = entry.get("REG_DT", "")
            if st.startswith("--T"):
                if len(reg_dt) == 8: st = f"{reg_dt[:4]}-{reg_dt[4:6]}-{reg_dt[6:8]}T{st[3:]}"
                else: st = f"2024-01-01T{st[3:]}"
            st = st.replace(" ", "T")
            if "T" in st and len(st) == 19: st = st + ".000000"
            elif len(st) == 8 and "-" not in st: st = f"{st[:4]}-{st[4:6]}-{st[6:8]}T00:00:00.000000"

            params_list.append({
                "REPORT_ID": entry.get("id"), # SQLite id -> Oracle REPORT_ID
                "SEC_FIRM_ORDER": entry.get("SEC_FIRM_ORDER"),
                "ARTICLE_BOARD_ORDER": entry.get("ARTICLE_BOARD_ORDER"),
                "FIRM_NM": entry.get("FIRM_NM"),
                "REG_DT": entry.get("REG_DT", ""),
                "ATTACH_URL": entry.get("ATTACH_URL", ""),
                "ARTICLE_TITLE": title[:1000],
                "ARTICLE_URL": entry.get("ARTICLE_URL"),
                "MAIN_CH_SEND_YN": entry.get("MAIN_CH_SEND_YN", "N"),
                "DOWNLOAD_URL": entry.get("DOWNLOAD_URL"),
                "TELEGRAM_URL": entry.get("TELEGRAM_URL", ""),
                "WRITER": entry.get("WRITER", ""),
                "MKT_TP": mkt_tp,
                "KEY": entry.get("KEY"), # SQLite KEY 원본 유지
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
        """비동기 인터페이스 유지 (내부는 안정적인 동기 로직 실행)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._insert_sync_process, json_data_list)

    async def bulk_insert(self, json_data_list):
        """[이관 전용] 대용량 고속 삽입을 위한 별도 함수"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._bulk_insert_sync, json_data_list)

    def _bulk_insert_sync(self, json_data_list):
        """[이관 전용] MERGE 없이 INSERT /*+ APPEND */를 사용하는 고속 동기 로직"""
        if not json_data_list:
            return 0
            
        conn = self._get_connection_sync()
        query = """
        INSERT /*+ APPEND */ INTO DATA_MAIN_DAILY_SEND (
            REPORT_ID, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT, ATTACH_URL, 
            ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, DOWNLOAD_URL, 
            TELEGRAM_URL, WRITER, MKT_TP, KEY, SAVE_TIME,
            GEMINI_SUMMARY, SUMMARY_TIME, SUMMARY_MODEL
        ) VALUES (
            :REPORT_ID, :SEC_FIRM_ORDER, :ARTICLE_BOARD_ORDER, :FIRM_NM, :REG_DT, :ATTACH_URL, 
            :ARTICLE_TITLE, :ARTICLE_URL, :MAIN_CH_SEND_YN, :DOWNLOAD_URL, 
            :TELEGRAM_URL, :WRITER, :MKT_TP, :KEY, TO_TIMESTAMP(:SAVE_TIME, 'YYYY-MM-DD HH24:MI:SS.FF'),
            :GEMINI_SUMMARY, :SUMMARY_TIME, :SUMMARY_MODEL
        )
        """
        
        params_list = []
        for entry in json_data_list:
            title = entry.get("ARTICLE_TITLE", "")
            st = str(entry.get("SAVE_TIME", "")).replace("T", " ")
            if len(st) == 19: st += ".000000"
            elif len(st) == 8 and "-" not in st: st = f"{st[:4]}-{st[4:6]}-{st[6:8]} 00:00:00.000000"

            params_list.append({
                "REPORT_ID": entry.get("id"), # SQLite id -> Oracle REPORT_ID
                "SEC_FIRM_ORDER": entry.get("SEC_FIRM_ORDER"),
                "ARTICLE_BOARD_ORDER": entry.get("ARTICLE_BOARD_ORDER"),
                "FIRM_NM": entry.get("FIRM_NM"),
                "REG_DT": entry.get("REG_DT", ""),
                "ATTACH_URL": entry.get("ATTACH_URL", ""),
                "ARTICLE_TITLE": title[:1000],
                "ARTICLE_URL": entry.get("ARTICLE_URL"),
                "MAIN_CH_SEND_YN": entry.get("MAIN_CH_SEND_YN", "N"),
                "DOWNLOAD_URL": entry.get("DOWNLOAD_URL"),
                "TELEGRAM_URL": entry.get("TELEGRAM_URL", ""),
                "WRITER": entry.get("WRITER", ""),
                "MKT_TP": entry.get("MKT_TP", "KR"),
                "KEY": entry.get("KEY"), # SQLite KEY 원본 유지
                "SAVE_TIME": st,
                "GEMINI_SUMMARY": entry.get("GEMINI_SUMMARY"),
                "SUMMARY_TIME": entry.get("SUMMARY_TIME"),
                "SUMMARY_MODEL": entry.get("SUMMARY_MODEL")
            })
            
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
            print(f"✅ Oracle Bulk Insert Success: {len(params_list)} rows.")
            return len(params_list)
        except Exception as e:
            print(f"❌ Oracle Bulk Insert Error: {e}")
            return 0
        finally:
            conn.close()

    def _execute_query_sync(self, query, params=None):
        """동기 쿼리 실행 로직"""
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
        """비동기 인터페이스 유지"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_query_sync, query, params)

    async def update_report_summary(self, record_id, summary, model_name):
        """Gemini 요약 결과 업데이트"""
        query = """
        UPDATE DATA_MAIN_DAILY_SEND
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :st, 
            SUMMARY_MODEL = :model
        WHERE REPORT_ID = :id
        """
        params = {
            "summary": summary,
            "st": datetime.now().isoformat(),
            "model": model_name,
            "id": record_id
        }
        return await self.execute_query(query, params)

    def truncate_table(self):
        """테이블의 모든 데이터 삭제 (TRUNCATE)"""
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE DATA_MAIN_DAILY_SEND")
                conn.commit()
            print("✅ Table DATA_MAIN_DAILY_SEND truncated successfully.")
            return True
        except Exception as e:
            print(f"❌ Truncate Error: {e}")
            return False
        finally:
            conn.close()

    async def full_sync_from_sqlite(self):
        """SQLite의 DATA_MAIN_DAILY_SEND 데이터를 Oracle의 DATA_MAIN_DAILY_SEND로 전체 동기화 (청크 방식)"""
        from models.SQLiteManager import SQLiteManager
        
        print("🚀 Starting full sync from SQLite to Oracle...")
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        
        # 전체 개수 확인
        sqlite_db.cursor.execute("SELECT count(*) as total FROM DATA_MAIN_DAILY_SEND")
        total_rows = sqlite_db.cursor.fetchone()[0]
        print(f"📊 Total rows to sync from SQLite: {total_rows}")
        
        if not total_rows:
            print("⚠️ No data found in SQLite to sync.")
            sqlite_db.close_connection()
            return 0
            
        print("📦 Truncating Oracle table...")
        self.truncate_table()
        
        chunk_size = 10000
        offset = 0
        total_synced = 0
        
        print(f"⚡ Performing high-speed bulk insert in chunks (Batch Size: {chunk_size})...")
        
        while offset < total_rows:
            # SQLite에서 청크 단위로 데이터 조회
            sqlite_db.cursor.execute(f"SELECT * FROM DATA_MAIN_DAILY_SEND LIMIT {chunk_size} OFFSET {offset}")
            rows = sqlite_db.cursor.fetchall()
            if not rows: break
            
            sqlite_data = [dict(row) for row in rows]
            
            # Oracle에 청크 인서트 (bulk_insert 호출)
            count = await self.bulk_insert(sqlite_data)
            total_synced += count
            offset += chunk_size
            
            print(f"✅ Progress: {min(offset, total_rows):,} / {total_rows:,} rows synced...")
            
        sqlite_db.close_connection()
        print(f"✨ Successfully synchronized total {total_synced:,} rows to Oracle.")
        return total_synced

if __name__ == "__main__":
    import sys
    async def main():
        om = OracleManager()
        if len(sys.argv) > 1 and sys.argv[1] == "full_insert":
            print("!!! FULL INSERT MODE !!!")
            count = await om.full_sync_from_sqlite()
            print(f"✨ Total {count} rows synchronized to Oracle.")
        else:
            res = await om.execute_query("SELECT count(*) FROM DATA_MAIN_DAILY_SEND")
            print(f"Test Result: {res}")
            
    asyncio.run(main())

    def truncate_table(self):
        """테이블의 모든 데이터 삭제 (TRUNCATE)"""
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE DATA_MAIN_DAILY_SEND")
                conn.commit()
            print("✅ Table DATA_MAIN_DAILY_SEND truncated successfully.")
            return True
        except Exception as e:
            print(f"❌ Truncate Error: {e}")
            return False
        finally:
            conn.close()

    async def full_sync_from_sqlite(self):
        """SQLite의 DATA_MAIN_DAILY_SEND 데이터를 Oracle의 DATA_MAIN_DAILY_SEND로 전체 동기화 (청크 방식)"""
        from models.SQLiteManager import SQLiteManager
        
        print("🚀 Starting full sync from SQLite to Oracle...")
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        
        # 전체 개수 확인
        sqlite_db.cursor.execute("SELECT count(*) as total FROM DATA_MAIN_DAILY_SEND")
        total_rows = sqlite_db.cursor.fetchone()[0]
        print(f"📊 Total rows to sync from SQLite: {total_rows}")
        
        if not total_rows:
            print("⚠️ No data found in SQLite to sync.")
            sqlite_db.close_connection()
            return 0
            
        print("📦 Truncating Oracle table...")
        self.truncate_table()
        
        chunk_size = 10000
        offset = 0
        total_synced = 0
        
        print(f"⚡ Performing high-speed bulk insert in chunks (Batch Size: {chunk_size})...")
        
        while offset < total_rows:
            # SQLite에서 청크 단위로 데이터 조회
            sqlite_db.cursor.execute(f"SELECT * FROM DATA_MAIN_DAILY_SEND LIMIT {chunk_size} OFFSET {offset}")
            rows = sqlite_db.cursor.fetchall()
            if not rows: break
            
            sqlite_data = [dict(row) for row in rows]
            
            # Oracle에 청크 인서트 (bulk_insert 호출)
            count = await self.bulk_insert(sqlite_data)
            total_synced += count
            offset += chunk_size
            
            print(f"✅ Progress: {min(offset, total_rows):,} / {total_rows:,} rows synced...")
            
        sqlite_db.close_connection()
        print(f"✨ Successfully synchronized total {total_synced:,} rows to Oracle.")
        return total_synced

if __name__ == "__main__":
    import sys
    async def main():
        om = OracleManager()
        if len(sys.argv) > 1 and sys.argv[1] == "full_insert":
            print("!!! FULL INSERT MODE !!!")
            count = await om.full_sync_from_sqlite()
            print(f"✨ Total {count} rows synchronized to Oracle.")
        else:
            res = await om.execute_query("SELECT count(*) FROM DATA_MAIN_DAILY_SEND")
            print(f"Test Result: {res}")
            
    asyncio.run(main())
