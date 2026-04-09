import asyncio
import oracledb
import os
import sys
import hashlib
from datetime import datetime, timedelta
from dotenv import load_dotenv
from loguru import logger

# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class OracleManager:
    def __init__(self):
        """Oracle 데이터베이스 연결 초기화 (Thin 모드 우선)"""
        load_dotenv(override=True)
        self.main_table_name = os.getenv("MAIN_TABLE_NAME", "data_main_daily_send").upper()
        # Thick 모드 초기화는 지갑 연동이 꼭 필요한 경우에만 사용하므로 주석 처리
        # self._init_thick_mode()

    def _get_connection_sync(self):
        """동기 방식으로 연결 객체 생성 (Thin 모드 방식)"""
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        # DB_DSN이 없으면 DB_DSN_LOW를 기본값으로 사용
        dsn = os.getenv('DB_DSN') or os.getenv('DB_DSN_LOW')
        # Thin 모드에서도 TNS 별칭(oracledb_low 등)을 쓰려면 config_dir 지정이 필요함
        config_dir = os.path.expanduser(os.getenv('WALLET_LOCATION'))
        
        dsn_info = dsn[:50] if dsn else "N/A"
        logger.debug(f"🔗 Attempting Oracle Connection (Thin Mode) -> USER: {user}, DSN: {dsn_info}, Config: {config_dir}...")
        
        return oracledb.connect(
            user=user,
            password=password,
            dsn=dsn,
            config_dir=config_dir
        )

    def _insert_sync_process(self, json_data_list):
        """데이터 삽입/업데이트를 수행하는 동기 메서드 (데이터 보호형 MERGE)"""
        if not json_data_list:
            return 0
            
        conn = self._get_connection_sync()
        # Oracle 스키마에 기반한 MERGE 쿼리
        # NVL(s.COL, t.COL)을 사용하여 소스 데이터가 빈 값(NULL)일 경우 기존 오라클 데이터를 유지함
        query = f"""
        MERGE INTO {self.main_table_name} t
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
            ci = {k.lower(): v for k, v in entry.items()}
            
            def get_str(key, max_len=None):
                val = ci.get(key.lower())
                if val is None or str(val).strip() == "":
                    return None
                return str(val)[:max_len] if max_len else str(val)

            def get_url_val(key, max_len=4000):
                """URL 컬럼 유효성 체크 및 Fallback 로직: 원본 -> TELEGRAM_URL -> KEY"""
                val = get_str(key, max_len)
                if val: return val
                
                tg_url = get_str("telegram_url", max_len)
                if tg_url: return tg_url
                
                key_val = get_str("key", max_len)
                return key_val if key_val else "N/A"

            r_id = ci.get("report_id")
            
            params_list.append({
                "REPORT_ID": r_id,
                "SEC_FIRM_ORDER": ci.get("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": ci.get("article_board_order"),
                "FIRM_NM": get_str("firm_nm", 100),
                "SEND_USER": get_str("send_user", 100),
                "MAIN_CH_SEND_YN": get_str("main_ch_send_yn", 100),
                "DOWNLOAD_STATUS_YN": get_str("download_status_yn", 100),
                "SAVE_TIME_STR": get_str("save_time", 100),
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
            logger.info(f"✅ Oracle Merge Success: {len(params_list)} rows processed.")
            return len(params_list)
        except Exception as e:
            logger.error(f"❌ Oracle Merge Error: {e}")
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
                    return None
                return str(val)[:max_len]

            def get_url_val(key, max_len=4000):
                """URL 컬럼 유효성 체크 및 Fallback 로직: 원본 -> TELEGRAM_URL -> KEY"""
                val = get_str(key, max_len)
                if val: return val
                
                tg_url = get_str("telegram_url", max_len)
                if tg_url: return tg_url
                
                key_val = get_str("key", max_len)
                return key_val if key_val else "N/A"

            params_list.append({
                "REPORT_ID": ci.get("report_id"),
                "SEC_FIRM_ORDER": ci.get("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": ci.get("article_board_order"),
                "FIRM_NM": get_str("firm_nm", 300),
                "REG_DT": get_str("reg_dt", 20),
                "ATTACH_URL": get_url_val("attach_url", 1000),
                "ARTICLE_TITLE": get_str("article_title", 1000) or "No Title",
                "ARTICLE_URL": get_url_val("article_url", 1000),
                "MAIN_CH_SEND_YN": get_str("main_ch_send_yn", 1) or "N",
                "DOWNLOAD_URL": get_url_val("download_url", 1000), 
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
            logger.error(f"❌ Oracle Bulk Insert Error: {e}")
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
            logger.error(f"❌ Oracle Query Error: {e}")
            return []
        finally:
            conn.close()

    async def execute_query(self, query, params=None):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_query_sync, query, params)

    async def update_report_summary(self, record_id, summary, model_name):
        query = f"""
        UPDATE {self.main_table_name}
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :st, 
            SUMMARY_MODEL = :model
        WHERE REPORT_ID = :id
        """
        params = {"summary": summary, "st": datetime.now(), "model": model_name, "id": record_id}
        return await self.execute_query(query, params)

    async def update_report_summary_by_telegram_url(self, telegram_url, summary, model_name):
        """TELEGRAM_URL 기준 요약 업데이트 (발송 완료된 최신 건 우선)"""
        query = f"""
        UPDATE {self.main_table_name}
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :st, 
            SUMMARY_MODEL = :model
        WHERE TELEGRAM_URL = :url
          AND MAIN_CH_SEND_YN = 'Y'
          AND REPORT_ID = (
              SELECT MAX(REPORT_ID) FROM {self.main_table_name} 
              WHERE TELEGRAM_URL = :url AND MAIN_CH_SEND_YN = 'Y'
          )
        """
        params = {"summary": summary, "st": datetime.now(), "model": model_name, "url": telegram_url}
        return await self.execute_query(query, params)

    async def update_telegram_url(self, record_id, telegram_url, article_title=None, pdf_url=None):
        """텔레그램 URL 및 PDF 경로 업데이트"""
        if article_title:
            query = f"""
            UPDATE {self.main_table_name} 
            SET TELEGRAM_URL = :t_url, ARTICLE_TITLE = :title, ATTACH_URL = NVL(:pdf, ATTACH_URL) 
            WHERE REPORT_ID = :id
            """
            params = {"t_url": telegram_url, "title": article_title, "pdf": pdf_url, "id": record_id}
        else:
            query = f"""
            UPDATE {self.main_table_name} 
            SET TELEGRAM_URL = :t_url, ATTACH_URL = NVL(:pdf, ATTACH_URL) 
            WHERE REPORT_ID = :id
            """
            params = {"t_url": telegram_url, "pdf": pdf_url, "id": record_id}
        return await self.execute_query(query, params)

    async def daily_select_data(self, date_str=None, type='send'):
        """일자별 발송/다운로드 대상 조회"""
        if date_str is None:
            q_date = datetime.now().strftime('%Y-%m-%d')
        else:
            q_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            
        if type == 'send':
            cond = "(MAIN_CH_SEND_YN != 'Y' OR MAIN_CH_SEND_YN IS NULL)"
        else:
            cond = "MAIN_CH_SEND_YN = 'Y' AND DOWNLOAD_STATUS_YN != 'Y'"
            
        query = f"""
        SELECT * FROM {self.main_table_name} 
        WHERE TO_CHAR(SAVE_TIME, 'YYYY-MM-DD') = :dt AND {cond}
        ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
        """
        return await self.execute_query(query, {"dt": q_date})

    async def daily_update_data(self, fetched_rows=None, type='send'):
        """발송/다운로드 상태 일괄 업데이트"""
        if not fetched_rows: return 0
        
        ids = []
        if isinstance(fetched_rows, list):
            # Oracle은 REPORT_ID(대문자), SQLite는 report_id(소문자)를 사용하므로 둘 다 체크
            ids = [r.get('REPORT_ID') or r.get('report_id') for r in fetched_rows]
        else:
            ids = [fetched_rows.get('REPORT_ID') or fetched_rows.get('report_id')]
            
        col = "MAIN_CH_SEND_YN" if type == 'send' else "DOWNLOAD_STATUS_YN"
        query = f"UPDATE {self.main_table_name} SET {col} = 'Y' WHERE REPORT_ID = :id"
        
        # executemany 스타일로 처리하기 위해 execute_query 확장 필요할 수 있으나 
        # 일단 루프로 처리 (데이터 건수가 작음)
        count = 0
        for rid in ids:
            await self.execute_query(query, {"id": rid})
            count += 1
        return count

    async def fetch_daily_articles_by_date(self, firm_info, date_str=None):
        """특정 회사의 텔레그램 URL 미지정 기사 조회"""
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

    def truncate_table(self):
        conn = self._get_connection_sync()
        try:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(f"TRUNCATE TABLE {self.main_table_name}")
                    logger.info(f"✅ Table {self.main_table_name} truncated successfully.")
                except oracledb.DatabaseError as e:
                    if "ORA-00054" in str(e):
                        logger.warning("⚠️ Resource busy, using DELETE instead...")
                        cursor.execute(f"DELETE FROM {self.main_table_name}")
                        logger.info(f"✅ Table {self.main_table_name} deleted successfully.")
                    else: raise e
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Clean Table Error: {e}")
            return False
        finally:
            conn.close()

    async def full_sync_from_sqlite(self):
        """오라클을 비우고(Truncate) 안정적인 청크 단위로 고속 일괄 삽입"""
        from models.SQLiteManager import SQLiteManager
        logger.info("🚀 Starting Optimized Chunked Sync (10k Batch) to Oracle ATP...")
        
        # 1. 오라클 테이블 초기화 (데이터 변조 및 불안정성 제거)
        self.truncate_table()
        
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        
        # 2. 전체 데이터 건수 확인
        sqlite_db.cursor.execute(f"SELECT count(*) FROM {sqlite_db.main_table_name}")
        total_rows = sqlite_db.cursor.fetchone()[0]
        
        if total_rows == 0:
            logger.warning("⚠️ No data found in SQLite.")
            sqlite_db.close_connection()
            return 0
            
        logger.info(f"📊 Total {total_rows:,} rows to sync. Processing in 10,000 unit chunks...")
        
        # 3. 10,000건씩 끊어서 처리 (메모리 및 오라클 부하 방지)
        chunk_size = 10000
        offset = 0
        total_synced = 0
        
        while offset < total_rows:
            sqlite_db.cursor.execute(f"SELECT * FROM {sqlite_db.main_table_name} LIMIT {chunk_size} OFFSET {offset}")
            rows = sqlite_db.cursor.fetchall()
            if not rows: break
            
            sqlite_data = [dict(row) for row in rows]
            # 개선된 bulk_insert 호출 (executemany + commit)
            count = await self.bulk_insert(sqlite_data)
            total_synced += count
            offset += chunk_size
            logger.info(f"✅ Progress: {min(offset, total_rows):,}/{total_rows:,} rows synced (Batch OK)")
            
        sqlite_db.close_connection()
        logger.success(f"✨ Successfully synced total {total_synced:,} rows to Oracle ATP.")
        return total_synced

# 하위 호환성을 위한 별칭 설정
OracleManagerSQL = OracleManager

if __name__ == "__main__":
    import sys
    async def main():
        om = OracleManager()
        if len(sys.argv) > 1 and sys.argv[1] == "full_insert":
            logger.info("!!! FULL INSERT MODE !!!")
            await om.full_sync_from_sqlite()
        else:
            res = await om.execute_query(f"SELECT count(*) FROM {om.main_table_name}")
            logger.info(f"Test Result: {res}")
    asyncio.run(main())
