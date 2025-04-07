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
        """JSON 데이터 리스트를 Oracle DB에 삽입 (중복 키 처리 및 삽입/업데이트 건수 계산)"""
        print(f"json_data_list: {json_data_list}")
        self.open_connection()

        # 중복 KEY 제거
        unique_data = {}
        for entry in json_data_list:
            key_val = entry.get("KEY") or entry.get("ATTACH_URL", " ")
            if not key_val.strip():
                print(f"Skipping empty KEY for {entry['ARTICLE_TITLE']}")
                continue
            if key_val in unique_data:
                if entry["SAVE_TIME"] > unique_data[key_val]["SAVE_TIME"]:
                    unique_data[key_val] = entry
            else:
                unique_data[key_val] = entry
        json_data_list = list(unique_data.values())

        inserted_count = 0
        updated_count = 0

        query = f"""
        MERGE INTO {table_name} tgt
        USING (
            SELECT
                :SEC_FIRM_ORDER AS SEC_FIRM_ORDER,
                :ARTICLE_BOARD_ORDER AS ARTICLE_BOARD_ORDER,
                :FIRM_NM AS FIRM_NM,
                :REG_DT AS REG_DT,
                :ATTACH_URL AS ATTACH_URL,
                :ARTICLE_TITLE AS ARTICLE_TITLE,
                :ARTICLE_URL AS ARTICLE_URL,
                :MAIN_CH_SEND_YN AS MAIN_CH_SEND_YN,
                :DOWNLOAD_URL AS DOWNLOAD_URL,
                :TELEGRAM_URL AS TELEGRAM_URL,
                :WRITER AS WRITER,
                :MKT_TP AS MKT_TP,
                :KEY AS KEY,
                :SAVE_TIME AS SAVE_TIME
            FROM DUAL
        ) src
        ON (tgt.KEY = src.KEY)
        WHEN MATCHED THEN
            UPDATE SET
                REG_DT = src.REG_DT,
                WRITER = src.WRITER,
                MKT_TP = src.MKT_TP,
                DOWNLOAD_URL = CASE
                    WHEN src.DOWNLOAD_URL IS NOT NULL AND src.DOWNLOAD_URL != ' '
                    THEN src.DOWNLOAD_URL
                    ELSE tgt.DOWNLOAD_URL
                END,
                TELEGRAM_URL = CASE
                    WHEN src.TELEGRAM_URL IS NOT NULL AND src.TELEGRAM_URL != ' '
                    THEN src.TELEGRAM_URL
                    ELSE tgt.TELEGRAM_URL
                END,
                ARTICLE_TITLE = src.ARTICLE_TITLE,
                ATTACH_URL = src.ATTACH_URL,
                ARTICLE_URL = src.ARTICLE_URL,
                MAIN_CH_SEND_YN = src.MAIN_CH_SEND_YN,
                SEC_FIRM_ORDER = src.SEC_FIRM_ORDER,
                ARTICLE_BOARD_ORDER = src.ARTICLE_BOARD_ORDER,
                FIRM_NM = src.FIRM_NM,
                SAVE_TIME = src.SAVE_TIME
        WHEN NOT MATCHED THEN
            INSERT (
                REPORT_ID, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN,
                DOWNLOAD_URL, TELEGRAM_URL, WRITER, MKT_TP, KEY, SAVE_TIME,
                SEND_USER, DOWNLOAD_STATUS_YN
            ) VALUES (
                SEQ_REPORT_ID.NEXTVAL, src.SEC_FIRM_ORDER, src.ARTICLE_BOARD_ORDER, src.FIRM_NM, src.REG_DT,
                src.ATTACH_URL, src.ARTICLE_TITLE, src.ARTICLE_URL, src.MAIN_CH_SEND_YN,
                src.DOWNLOAD_URL, src.TELEGRAM_URL, src.WRITER, src.MKT_TP, src.KEY, src.SAVE_TIME,
                ' ', ' '
            )
        """

        for entry in json_data_list:
            key_val = entry.get("KEY") or entry.get("ATTACH_URL", " ")
            if not key_val.strip():
                continue
            params = {
                "SEC_FIRM_ORDER": entry["SEC_FIRM_ORDER"],
                "ARTICLE_BOARD_ORDER": entry["ARTICLE_BOARD_ORDER"],
                "FIRM_NM": entry["FIRM_NM"],
                "REG_DT": entry.get("REG_DT", " "),
                "ATTACH_URL": entry.get("ATTACH_URL", " "),
                "ARTICLE_TITLE": entry["ARTICLE_TITLE"],
                "ARTICLE_URL": entry.get("ARTICLE_URL", " "),
                "MAIN_CH_SEND_YN": entry.get("MAIN_CH_SEND_YN", "N"),
                "DOWNLOAD_URL": entry.get("DOWNLOAD_URL", " "),
                "TELEGRAM_URL": entry.get("TELEGRAM_URL", " "),
                "WRITER": entry.get("WRITER", " "),
                "MKT_TP": entry.get("MKT_TP", "KR"),
                "KEY": key_val,
                "SAVE_TIME": entry["SAVE_TIME"]
            }

            try:
                self.cursor.execute(query, params)
                if self.cursor.rowcount == 1:
                    inserted_count += 1
                elif self.cursor.rowcount == 0:
                    updated_count += 1
                self.conn.commit()
            except oracledb.DatabaseError as e:
                print(f"Error processing {key_val}: {e}")
                continue

        print(f"Data inserted successfully: {inserted_count} rows.")
        print(f"Data updated successfully: {updated_count} rows.")
        self.close_connection()
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
                    report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
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
        try:
            # 단일 비동기 연결 사용
            conn = await oracledb.connect_async(
                user=DB_USER,
                password=DB_PASSWORD,
                dsn=DB_DSN,
                config_dir=WALLET_LOCATION,
                wallet_location=WALLET_LOCATION,
                wallet_password=WALLET_PASSWORD
            )
            async with conn.cursor() as cursor:
                print(f"date_str: {date_str}, type: {type}")
                if type not in ['send', 'download']:
                    raise ValueError("Invalid type. Must be 'send' or 'download'.")

                # 날짜 처리
                if date_str is None:
                    base_date = datetime.now()
                    base_date = datetime.now()
                else:
                    base_date = datetime.strptime(date_str, '%Y%m%d')

                query_date = base_date.strftime('%Y-%m-%d')
                three_days_ago = (base_date - timedelta(days=3)).strftime('%Y%m%d')
                query_reg_dt = (base_date + timedelta(days=2)).strftime('%Y%m%d')

                query_condition = "(MAIN_CH_SEND_YN != 'Y' OR MAIN_CH_SEND_YN IS NULL) AND (SEC_FIRM_ORDER != 19 OR (SEC_FIRM_ORDER = 19 AND TELEGRAM_URL <> ' '))" if type == 'send' else "MAIN_CH_SEND_YN = 'Y' AND DOWNLOAD_STATUS_YN != 'Y'"

                # SQL 쿼리 작성
                query = f"""
                SELECT 
                    report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                    report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                    ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, 
                    DOWNLOAD_URL, WRITER, SAVE_TIME, TELEGRAM_URL
                FROM 
                    data_main_daily_send 
                WHERE 
                    SUBSTR(SAVE_TIME, 1, 10) = :query_date
                    AND REG_DT >= :three_days_ago
                    AND REG_DT <= :query_reg_dt
                    AND {query_condition}
                ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
                """
                print('=' * 30)
                print('=' * 30)
                print(query)
                print('=' * 30)
                await cursor.execute(query, {
                    "query_date": query_date,
                    "three_days_ago": three_days_ago,
                    "query_reg_dt": query_reg_dt
                })
                rows = await cursor.fetchall()
                columns = [desc[0].lower() for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
        except oracledb.DatabaseError as e:
            print(f"Database error: {e}")
            return []
        except Exception as e:
            print(f"Unexpected error: {e}")
            return []
        finally:
            if 'conn' in locals():
                await conn.close()



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
                    WHERE report_id = :report_id
                    WHERE report_id = :report_id
                    """
                    for row in fetched_rows:
                        print(f"Row data: {row}")
                        print(f"Executing query: {update_query}")
                        print(f"With parameters: {{'report_id': {row['report_id']}}}")
                        await cursor.execute(update_query, {"report_id": row["report_id"]})
                        print(f"With parameters: {{'report_id': {row['report_id']}}}")
                        await cursor.execute(update_query, {"report_id": row["report_id"]})
                elif type == 'download':
                    update_query = """
                    UPDATE data_main_daily_send
                    SET DOWNLOAD_STATUS_YN = 'Y'
                    WHERE report_id = :report_id
                    WHERE report_id = :report_id
                    """
                    print(f"Single row for download: {fetched_rows}")
                    print(f"Executing query: {update_query}")
                    print(f"With parameters: {{'report_id': {fetched_rows['report_id']}}}")
                    await cursor.execute(update_query, {"report_id": fetched_rows["report_id"]})
                    print(f"With parameters: {{'report_id': {fetched_rows['report_id']}}}")
                    await cursor.execute(update_query, {"report_id": fetched_rows["report_id"]})

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