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

    def insert_json_data_list(self, json_data_list, table_name):
        """JSON 데이터 리스트 삽입 및 업데이트 (MERGE 사용)"""
        self.open_connection()
        inserted_count = 0
        updated_count = 0
        for entry in json_data_list:
            merge_query = f"""
            MERGE INTO {table_name} t
            USING (SELECT :key AS KEY FROM dual) s
            ON (t.KEY = s.KEY)
            WHEN MATCHED THEN
                UPDATE SET
                    REG_DT = :reg_dt,
                    WRITER = :writer,
                    MKT_TP = :mkt_tp,
                    DOWNLOAD_URL = CASE 
                        WHEN :download_url IS NOT NULL AND :download_url != '' 
                        THEN :download_url 
                        ELSE t.DOWNLOAD_URL 
                    END,
                    TELEGRAM_URL = CASE 
                        WHEN :telegram_url IS NOT NULL AND :telegram_url != '' 
                        THEN :telegram_url 
                        ELSE t.TELEGRAM_URL 
                    END
            WHEN NOT MATCHED THEN
                INSERT (
                    SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                    ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN,
                    DOWNLOAD_URL, TELEGRAM_URL, WRITER, MKT_TP, KEY, SAVE_TIME
                )
                VALUES (
                    :sec_firm_order, :article_board_order, :firm_nm, :reg_dt,
                    :attach_url, :article_title, :article_url, :main_ch_send_yn,
                    :download_url, :telegram_url, :writer, :mkt_tp, :key, :save_time
                )
            """
            params = {
                "sec_firm_order": entry["SEC_FIRM_ORDER"],
                "article_board_order": entry["ARTICLE_BOARD_ORDER"],
                "firm_nm": entry["FIRM_NM"],
                "reg_dt": entry.get("REG_DT", ""),
                "attach_url": entry.get("ATTACH_URL", ""),
                "article_title": entry["ARTICLE_TITLE"],
                "article_url": entry.get("ARTICLE_URL", None),
                "main_ch_send_yn": entry.get("MAIN_CH_SEND_YN", "N"),
                "download_url": entry.get("DOWNLOAD_URL", None),
                "telegram_url": entry.get("TELEGRAM_URL", None),
                "writer": entry.get("WRITER", ""),
                "mkt_tp": entry.get("MKT_TP", "KR"),
                "key": entry.get("KEY") or entry.get("ATTACH_URL", ""),
                "save_time": entry["SAVE_TIME"]
            }
            self.cursor.execute(merge_query, params)
            if self.cursor.rowcount > 0:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE KEY = :key", {"key": params["key"]})
                if self.cursor.fetchone()[0] == 1:
                    inserted_count += 1
                else:
                    updated_count += 1
        self.conn.commit()
        self.close_connection()
        print(f"Oracle: Data inserted successfully: {inserted_count} rows.")
        print(f"Oracle: Data updated successfully: {updated_count} rows.")
        return inserted_count, updated_count

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
                    id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
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
                    WHERE id = :record_id
                    """
                    params = {"telegram_url": telegram_url, "article_title": article_title, "record_id": record_id}
                else:
                    query = """
                    UPDATE data_main_daily_send
                    SET TELEGRAM_URL = :telegram_url
                    WHERE id = :record_id
                    """
                    params = {"telegram_url": telegram_url, "record_id": record_id}
                await cursor.execute(query, params)
                await conn.commit()
            return {"status": "success", "query": query, "record_id": record_id, "telegram_url": telegram_url, "article_title": article_title}

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
                    id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
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
                    WHERE id = :id
                    """
                    for row in fetched_rows:
                        print(f"Row data: {row}")
                        print(f"Executing query: {update_query}")
                        print(f"With parameters: {{'id': {row['id']}}}")
                        await cursor.execute(update_query, {"id": row["id"]})
                elif type == 'download':
                    update_query = """
                    UPDATE data_main_daily_send
                    SET DOWNLOAD_STATUS_YN = 'Y'
                    WHERE id = :id
                    """
                    print(f"Single row for download: {fetched_rows}")
                    print(f"Executing query: {update_query}")
                    print(f"With parameters: {{'id': {fetched_rows['id']}}}")
                    await cursor.execute(update_query, {"id": fetched_rows["id"]})

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