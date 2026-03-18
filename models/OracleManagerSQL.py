import asyncio
import oracledb
import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta
# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가(package 폴더에 있으므로)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo  # FirmInfo 클래스 가져오기

# 환경 변수 로드
load_dotenv()

# Oracle 설정
WALLET_LOCATION = os.getenv('WALLET_LOCATION')
WALLET_PASSWORD = os.getenv('WALLET_PASSWORD')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DSN = os.getenv('DB_DSN')

class OracleManagerSQL:
    def __init__(self):
        """Oracle 데이터베이스 연결 초기화"""
        self.conn = None
        self.cursor = None

    def open_connection(self):
        """데이터베이스 연결 열기"""
        if self.conn is None:
            print("Opening Oracle connection...")
            self.conn = oracledb.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                dsn=DB_DSN,
                config_dir=WALLET_LOCATION,
                wallet_location=WALLET_LOCATION,
                wallet_password=WALLET_PASSWORD
            )
            self.cursor = self.conn.cursor()
            print("Oracle connection opened successfully.")
        elif self._is_connection_closed():
            print("Reopening closed Oracle connection...")
            self.close_connection()
            self.open_connection()

    def _is_connection_closed(self):
        """연결이 닫혔는지 확인하는 헬퍼 메서드"""
        try:
            # 간단한 쿼리 실행으로 연결 상태 확인
            self.cursor.execute("SELECT 1 FROM dual")
            return False
        except (oracledb.InterfaceError, oracledb.DatabaseError):
            return True

    def close_connection(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None
        print("Oracle connection closed.")

    def create_table(self, table_name, columns):
        """테이블 생성 (Oracle 방식)"""
        self.open_connection()
        columns_str = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
        query = f"CREATE TABLE {table_name} ({columns_str})"
        try:
            self.cursor.execute(query)
            self.conn.commit()
            result = {"status": "success", "query": query}
        except oracledb.DatabaseError as e:
            result = {"status": "error", "error": str(e), "query": query}
        self.close_connection()
        return result

    def insert_data(self, table_name, data):
        """단일 데이터 삽입"""
        self.open_connection()
        placeholders = ', '.join(f':{i+1}' for i in range(len(data)))
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        try:
            self.cursor.execute(query, data)
            self.conn.commit()
            result = {"status": "success", "query": query, "data": data}
        except oracledb.DatabaseError as e:
            result = {"status": "error", "error": str(e), "query": query}
        self.close_connection()
        return result

    def fetch_all(self, table_name):
        """모든 데이터 조회"""
        self.open_connection()
        query = f"SELECT * FROM {table_name}"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        columns = [desc[0].lower() for desc in self.cursor.description]
        result = [dict(zip(columns, row)) for row in rows]
        self.close_connection()
        return result

    def truncate_table(self, table_name):
        """테이블의 모든 데이터 삭제 (TRUNCATE)"""
        self.open_connection()
        query = f"TRUNCATE TABLE {table_name}"
        try:
            self.cursor.execute(query)
            self.conn.commit()
            print(f"Table {table_name} truncated successfully.")
            return {"status": "success", "query": query}
        except oracledb.DatabaseError as e:
            print(f"Error truncating table {table_name}: {e}")
            return {"status": "error", "error": str(e), "query": query}
        finally:
            self.close_connection()

    def insert_json_data_list(self, json_data_list, table_name, full_insert=False):
        """JSON 데이터 리스트를 Oracle DB에 삽입 (중복 키 무시 또는 전체 삭제 후 삽입)"""
        if full_insert:
            print(f"Full insert requested. Truncating {table_name}...")
            self.truncate_table(table_name)

        self.open_connection()
        
        # full_insert가 True이면 중복 무시 힌트 제외 (이미 TRUNCATE 했으므로)
        hint = "" if full_insert else f"/*+ ignore_row_on_dupkey_index({table_name}, KEY) */"
        
        query = f"""
        INSERT {hint}
        INTO {table_name} (
            SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
            ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN,
            DOWNLOAD_URL, TELEGRAM_URL, WRITER, MKT_TP, KEY, SAVE_TIME,
            GEMINI_SUMMARY, SUMMARY_TIME, SUMMARY_MODEL
        ) VALUES (
            :SEC_FIRM_ORDER, :ARTICLE_BOARD_ORDER, :FIRM_NM, :REG_DT,
            :ATTACH_URL, :ARTICLE_TITLE, :ARTICLE_URL, :MAIN_CH_SEND_YN,
            :DOWNLOAD_URL, :TELEGRAM_URL, :WRITER, :MKT_TP, :KEY, :SAVE_TIME,
            :GEMINI_SUMMARY, :SUMMARY_TIME, :SUMMARY_MODEL
        )"""
        params_list = []
        for entry in json_data_list:
            key_val = entry.get("KEY") or entry.get("ATTACH_URL", "")
            params_list.append({
                "SEC_FIRM_ORDER": entry.get("SEC_FIRM_ORDER"),
                "ARTICLE_BOARD_ORDER": entry.get("ARTICLE_BOARD_ORDER"),
                "FIRM_NM": entry.get("FIRM_NM"),
                "REG_DT": entry.get("REG_DT", ""),
                "ATTACH_URL": entry.get("ATTACH_URL", ""),
                "ARTICLE_TITLE": entry.get("ARTICLE_TITLE"),
                "ARTICLE_URL": entry.get("ARTICLE_URL"),
                "MAIN_CH_SEND_YN": entry.get("MAIN_CH_SEND_YN", "N"),
                "DOWNLOAD_URL": entry.get("DOWNLOAD_URL"),
                "TELEGRAM_URL": entry.get("TELEGRAM_URL"),
                "WRITER": entry.get("WRITER", ""),
                "MKT_TP": entry.get("MKT_TP", "KR"),
                "KEY": key_val,
                "SAVE_TIME": entry.get("SAVE_TIME"),
                "GEMINI_SUMMARY": entry.get("GEMINI_SUMMARY"),
                "SUMMARY_TIME": entry.get("SUMMARY_TIME"),
                "SUMMARY_MODEL": entry.get("SUMMARY_MODEL")
            })
        try:
            self.cursor.executemany(query, params_list)
            self.conn.commit()
            print(f"Inserted {len(params_list)} rows into {table_name}.")
        except oracledb.DatabaseError as e:
            print(f"Error during insert into {table_name}: {e}")
        finally:
            self.close_connection()
        return len(params_list)

    async def full_sync_from_sqlite(self):
        """SQLite의 DATA_MAIN_DAILY_SEND 테이블 데이터를 Oracle로 전체 동기화"""
        from models.SQLiteManager import SQLiteManager
        
        print("Starting full sync from SQLite to Oracle...")
        sqlite_db = SQLiteManager()
        sqlite_db.open_connection()
        # 모든 데이터 조회
        sqlite_db.cursor.execute("SELECT * FROM DATA_MAIN_DAILY_SEND")
        rows = sqlite_db.cursor.fetchall()
        sqlite_data = [dict(row) for row in rows]
        sqlite_db.close_connection()
        
        if not sqlite_data:
            print("No data found in SQLite to sync.")
            return 0
            
        print(f"Fetched {len(sqlite_data)} rows from SQLite. Performing full insert to Oracle...")
        return self.insert_json_data_list(sqlite_data, 'DATA_MAIN_DAILY_SEND', full_insert=True)


    async def fetch_daily_articles_by_date(self, firm_info: FirmInfo, date_str=None):
        """TELEGRAM_URL 갱신이 필요한 레코드 비동기 조회"""
        async with await oracledb.connect_async(
            user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN,
            config_dir=WALLET_LOCATION, wallet_location=WALLET_LOCATION, wallet_password=WALLET_PASSWORD
        ) as conn:
            async with conn.cursor() as cursor:
                query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
                firmInfo = firm_info.get_state()
                query = f"""
                SELECT 
                    report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                    ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, 
                    DOWNLOAD_URL, WRITER, SAVE_TIME, MAIN_CH_SEND_YN, TELEGRAM_URL, KEY
                FROM 
                    data_main_daily_send
                WHERE 
                    REG_DT BETWEEN TO_CHAR(TO_DATE('{query_date}', 'YYYYMMDD') - 3, 'YYYYMMDD')
                        AND TO_CHAR(TO_DATE('{query_date}', 'YYYYMMDD') + 2, 'YYYYMMDD')
                    AND SEC_FIRM_ORDER = :sec_firm_order
                    AND KEY IS NOT NULL
                    AND TELEGRAM_URL = ''
                ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
                """
                await cursor.execute(query, {"sec_firm_order": firmInfo["SEC_FIRM_ORDER"]})
                rows = await cursor.fetchall()
                columns = [desc[0].lower() for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    async def update_telegram_url(self, record_id, telegram_url, article_title=None):
        """TELEGRAM_URL 비동기 업데이트"""
        async with await oracledb.connect_async(
            user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN,
            config_dir=WALLET_LOCATION, wallet_location=WALLET_LOCATION, wallet_password=WALLET_PASSWORD
        ) as conn:
            async with conn.cursor() as cursor:
                if article_title is not None:
                    query = """
                    UPDATE data_main_daily_send
                    SET TELEGRAM_URL = :telegram_url, ARTICLE_TITLE = :article_title
                    WHERE report_id = :record_id
                    """
                    params = {"telegram_url": telegram_url, "article_title": article_title, "record_id": record_id}
                else:
                    query = """
                    UPDATE data_main_daily_send
                    SET TELEGRAM_URL = :telegram_url
                    WHERE report_id = :record_id
                    """
                    params = {"telegram_url": telegram_url, "record_id": record_id}
                await cursor.execute(query, params)
                await conn.commit()
            return {"status": "success", "query": query, "record_id": record_id, "telegram_url": telegram_url, "article_title": article_title}

    async def update_report_summary_by_telegram_url(self, telegram_url, summary, model_name):
        """TELEGRAM_URL이 일치하고 발송완료(MAIN_CH_SEND_YN='Y')된 레코드 중 report_id가 가장 큰 최신 레코드에 요약 정보를 업데이트합니다."""
        query = """
        UPDATE data_main_daily_send
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :summary_time, 
            SUMMARY_MODEL = :model_name
        WHERE TELEGRAM_URL = :telegram_url
          AND MAIN_CH_SEND_YN = 'Y'
          AND report_id = (
              SELECT MAX(report_id) 
              FROM data_main_daily_send 
              WHERE TELEGRAM_URL = :telegram_url 
                AND MAIN_CH_SEND_YN = 'Y'
          )
        """
        now = datetime.now()
        params = {
            "summary": summary,
            "summary_time": now,
            "model_name": model_name,
            "telegram_url": telegram_url
        }
        return await self.execute_query(query, params)

    async def update_report_summary(self, record_id, summary, model_name):
        """data_main_daily_send 테이블의 특정 report_id 레코드에 제미나이 요약 내용을 업데이트합니다."""
        query = """
        UPDATE data_main_daily_send
        SET GEMINI_SUMMARY = :summary, 
            SUMMARY_TIME = :summary_time, 
            SUMMARY_MODEL = :model_name
        WHERE report_id = :record_id
        """
        now = datetime.now()
        params = {
            "summary": summary,
            "summary_time": now,
            "model_name": model_name,
            "record_id": record_id
        }
        return await self.execute_query(query, params)

    async def execute_query(self, query, params=None, close=False):
        """비동기 쿼리 실행"""
        async with await oracledb.connect_async(
            user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN,
            config_dir=WALLET_LOCATION, wallet_location=WALLET_LOCATION, wallet_password=WALLET_PASSWORD
        ) as conn:
            async with conn.cursor() as cursor:
                try:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    if query.strip().lower().startswith("select"):
                        rows = await cursor.fetchall()
                        columns = [desc[0].lower() for desc in cursor.description]
                        result = [dict(zip(columns, row)) for row in rows]
                    else:
                        await conn.commit()
                        result = {"status": "success", "affected_rows": cursor.rowcount}
                except oracledb.DatabaseError as e:
                    result = {"status": "error", "error": str(e)}
                return result

    async def daily_select_data(self, date_str=None, type=None):
        """지정된 날짜 데이터 비동기 조회"""
        async with await oracledb.connect_async(
            user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN,
            config_dir=WALLET_LOCATION, wallet_location=WALLET_LOCATION, wallet_password=WALLET_PASSWORD
        ) as conn:
            async with conn.cursor() as cursor:
                print(f"date_str: {date_str}, type: {type}")
                if type not in ['send', 'download']:
                    raise ValueError("Invalid type. Must be 'send' or 'download'.")

                if date_str is None:
                    query_date = datetime.now().strftime('%Y-%m-%d')
                    query_reg_dt = (datetime.now() + timedelta(days=2)).strftime('%Y%m%d')
                else:
                    query_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
                    query_reg_dt = (datetime.strptime(date_str, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')

                three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')
                if type == 'send':
                    query_condition = "(MAIN_CH_SEND_YN != 'Y' OR MAIN_CH_SEND_YN IS NULL) AND (SEC_FIRM_ORDER != 19 OR (SEC_FIRM_ORDER = 19 AND TELEGRAM_URL <> ''))"
                elif type == 'download':
                    query_condition = "MAIN_CH_SEND_YN = 'Y' AND DOWNLOAD_STATUS_YN != 'Y'"

                query = f"""
                SELECT 
                    report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                    ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, 
                    DOWNLOAD_URL, WRITER, SAVE_TIME, TELEGRAM_URL, MAIN_CH_SEND_YN
                FROM 
                    data_main_daily_send 
                WHERE 
                    TO_CHAR(SAVE_TIME, 'YYYY-MM-DD') = '{query_date}'
                    AND REG_DT >= '{three_days_ago}'
                    AND REG_DT <= '{query_reg_dt}'
                    AND {query_condition}
                ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
                """
                print('='*30)
                print(query)
                print('='*30)
                await cursor.execute(query)
                rows = await cursor.fetchall()
                columns = [desc[0].lower() for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    async def daily_update_data(self, date_str=None, fetched_rows=None, type=None):
        """데이터 비동기 업데이트"""
        async with await oracledb.connect_async(
            user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN,
            config_dir=WALLET_LOCATION, wallet_location=WALLET_LOCATION, wallet_password=WALLET_PASSWORD
        ) as conn:
            async with conn.cursor() as cursor:
                if date_str is None:
                    query_date = datetime.now().strftime('%Y-%m-%d')
                else:
                    query_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

                if type not in ['send', 'download']:
                    raise ValueError("Invalid type. Must be 'send' or 'download'.")

                if type == 'send':
                    update_query = """
                    UPDATE data_main_daily_send
                    SET MAIN_CH_SEND_YN = 'Y'
                    WHERE report_id = :id
                    """
                    for row in fetched_rows:
                        print(f"Row data: {row}")
                        print(f"Executing query: {update_query}")
                        print(f"With parameters: {{'id': {row['report_id']}}}")
                        await cursor.execute(update_query, {"id": row["report_id"]})
                elif type == 'download':
                    update_query = """
                    UPDATE data_main_daily_send
                    SET DOWNLOAD_STATUS_YN = 'Y'
                    WHERE report_id = :id
                    """
                    print(f"Single row for download: {fetched_rows}")
                    print(f"Executing query: {update_query}")
                    print(f"With parameters: {{'id': {fetched_rows['report_id']}}}")
                    await cursor.execute(update_query, {"id": fetched_rows["report_id"]})

                await conn.commit()
                return {"status": "success", "affected_rows": cursor.rowcount}

# 예시 사용법
async def main():
    db = OracleManagerSQL()
    db.open_connection()
    rows = db.fetch_all('data_main_daily_send')
    print(rows)
    db.close_connection()

if __name__ == "__main__":
    asyncio.run(main())