import asyncio
import aiosqlite
import sqlite3
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv
# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가(package 폴더에 있으므로)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo  # 이미 정의된 FirmInfo 클래스
# 환경 변수 로드
load_dotenv()
env = os.getenv('ENV')

if env == 'production':
    PROJECT_DIR = os.getenv('PROJECT_DIR')
    HOME_DIR = os.getenv('HOME_DIR')
    JSON_DIR = os.getenv('JSON_DIR')
else:
    PROJECT_DIR = os.getenv('PROJECT_DIR')
    HOME_DIR = os.getenv('HOME_DIR')
    JSON_DIR = os.getenv('JSON_DIR')

# 데이터베이스 파일 경로
db_path = os.path.expanduser('~/sqlite3/telegram.db')

class SQLiteManager:
    def __init__(self, db_path=None):
        self.db_path = db_path if db_path else globals()['db_path']
        self.connection = None
        self.cursor = None

    def open_connection(self):
        """데이터베이스 연결 설정"""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

        # PRAGMA journal_mode=WAL 설정 적용
        self.cursor.execute("PRAGMA journal_mode=WAL;")
        self.connection.commit()  # 변경사항 반영
        
    def close_connection(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            try:
                self.cursor.close()
            except sqlite3.ProgrammingError:
                print("Cursor is already closed.")
        if self.connection:
            try:
                self.connection.close()
            except sqlite3.ProgrammingError:
                print("Connection is already closed.")

    def create_table(self, table_name, columns):
        """테이블 생성"""
        columns_str = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        self.cursor.execute(query)
        self.connection.commit()
        return {"status": "success", "query": query}

    def insert_data(self, table_name, data):
        """데이터 삽입"""
        placeholders = ', '.join('?' for _ in data)
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        self.cursor.execute(query, data)
        self.connection.commit()
        return {"status": "success", "query": query, "data": data}

    def fetch_all(self, table_name):
        """모든 데이터 조회"""
        query = f"SELECT * FROM {table_name}"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def insert_json_data_list(self, json_data_list, table_name):
        """JSON 형태의 리스트 데이터를 데이터베이스 테이블에 삽입하며, 삽입 성공 및 업데이트된 건수를 출력합니다."""
        self.open_connection()  # 데이터베이스 연결 열기

        # 삽입 및 업데이트 건수 초기화
        inserted_count = 0
        updated_count = 0

        # 데이터 삽입 및 업데이트 시도
        for entry in json_data_list:
            self.cursor.execute(f'''
                INSERT INTO {table_name} (
                    SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
                    ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, 
                    DOWNLOAD_URL, TELEGRAM_URL, PDF_URL, WRITER, MKT_TP, KEY, SAVE_TIME 
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(KEY) DO UPDATE SET
                    REG_DT = excluded.REG_DT,  -- 항상 갱신
                    WRITER = excluded.WRITER,  -- 항상 갱신
                    MKT_TP = excluded.MKT_TP,  -- 항상 갱신
                    DOWNLOAD_URL = CASE 
                        WHEN excluded.DOWNLOAD_URL IS NOT NULL AND excluded.DOWNLOAD_URL != '' 
                        THEN excluded.DOWNLOAD_URL 
                        ELSE DOWNLOAD_URL -- 기존 값을 유지
                    END,
                    TELEGRAM_URL = CASE 
                        WHEN excluded.TELEGRAM_URL IS NOT NULL AND excluded.TELEGRAM_URL != '' 
                        THEN excluded.TELEGRAM_URL 
                        ELSE TELEGRAM_URL -- 기존 값을 유지
                    END,
                    PDF_URL = CASE 
                        WHEN excluded.PDF_URL IS NOT NULL AND excluded.PDF_URL != '' 
                        THEN excluded.PDF_URL 
                        ELSE PDF_URL -- 기존 값을 유지
                    END
            ''', (
                entry["SEC_FIRM_ORDER"],
                entry["ARTICLE_BOARD_ORDER"],
                entry["FIRM_NM"],
                entry.get("REG_DT", ''),
                entry.get("ATTACH_URL", ''),
                entry["ARTICLE_TITLE"],
                entry.get("ARTICLE_URL", None),  # ARTICLE_URL이 없으면 NULL을 넣음
                entry.get("MAIN_CH_SEND_YN", 'N'),  # 기본값 'N'
                entry.get("DOWNLOAD_URL", None),  # DOWNLOAD_URL이 없으면 NULL을 넣음
                entry.get("TELEGRAM_URL", None),  # TELEGRAM_URL이 없으면 NULL을 넣음
                entry.get("PDF_URL") or entry.get("TELEGRAM_URL", None),  # PDF_URL이 없으면 TELEGRAM_URL을 넣음
                entry.get("WRITER", ''),
                entry.get("MKT_TP", "KR"),  # MKT_TP가 빈값이면 KR을 넣음
                entry.get("KEY") or entry.get("ATTACH_URL", ''),  # KEY가 없거나 빈 값일 때 ATTACH_URL을 사용
                entry["SAVE_TIME"]
            ))

            # 삽입 또는 업데이트 확인
            if self.cursor.rowcount == 1:
                inserted_count += 1  # 새로 삽입된 경우
            else:
                updated_count += 1  # 업데이트된 경우

        # 커밋하고 결과 출력
        self.connection.commit()
        print(f"Data inserted successfully: {inserted_count} rows.")
        print(f"Data updated successfully: {updated_count} rows.")
        
        self.close_connection()  # 데이터베이스 연결 닫기
        return inserted_count, updated_count

    async def fetch_daily_articles_by_date(self, firm_info: FirmInfo, date_str=None):
        """
        TELEGRAM_URL 갱신이 필요한 레코드를 조회합니다.
        
        Args:
            firm_info (FirmInfo): SEC_FIRM_ORDER와 ARTICLE_BOARD_ORDER 속성을 포함한 FirmInfo 인스턴스.
            date_str (str, optional): 조회할 날짜 (형식: 'YYYYMMDD'). 지정하지 않으면 오늘 날짜로 설정됩니다.
        
        Returns:
            list[dict]: 조회된 기사 목록
        """
        self.open_connection()
        query_date = date_str if date_str else datetime.now().strftime('%Y%m%d')
        firmInfo = firm_info.get_state()
        print(firmInfo["SEC_FIRM_ORDER"])
        query = f"""
        SELECT 
            report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
            ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, 
            DOWNLOAD_URL, WRITER, SAVE_TIME, MAIN_CH_SEND_YN, TELEGRAM_URL, KEY
        FROM 
            data_main_daily_send
        WHERE 
            REG_DT BETWEEN strftime('%Y%m%d', date(substr('{query_date}', 1, 4) || '-' || substr('{query_date}', 5, 2) || '-' || substr('{query_date}', 7, 2), '-3 days'))
                    AND strftime('%Y%m%d', date(substr('{query_date}', 1, 4) || '-' || substr('{query_date}', 5, 2) || '-' || substr('{query_date}', 7, 2), '+2 days'))
            AND SEC_FIRM_ORDER = '{firmInfo["SEC_FIRM_ORDER"]}'
            AND KEY IS NOT NULL
            AND TELEGRAM_URL  = ''
        ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
        """



        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        self.close_connection()
        
        return [dict(row) for row in rows]

    async def fetch_all_empty_telegram_url_articles(self, firm_info: FirmInfo, days_limit: int = None):
        """
        TELEGRAM_URL 갱신이 필요한 전체 레코드를 조회합니다.
        
        Args:
            firm_info (FirmInfo): SEC_FIRM_ORDER와 ARTICLE_BOARD_ORDER 속성을 포함한 FirmInfo 인스턴스.
            days_limit (int, optional): 최근 며칠 이내의 데이터를 조회할지 여부.
        
        Returns:
            list[dict]: 조회된 기사 목록
        """
        self.open_connection()
        firmInfo = firm_info.get_state()
        print(f"Fetching articles for firm order: {firmInfo['SEC_FIRM_ORDER']}")
        
        query = f"""
        SELECT 
            report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
            ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, 
            DOWNLOAD_URL, WRITER, SAVE_TIME, MAIN_CH_SEND_YN, TELEGRAM_URL, KEY
        FROM 
            data_main_daily_send
        WHERE 
            SEC_FIRM_ORDER = '{firmInfo["SEC_FIRM_ORDER"]}'
            AND KEY IS NOT NULL
            AND (TELEGRAM_URL IS NULL OR TELEGRAM_URL = '')
        """
        
        if days_limit:
            # SAVE_TIME 또는 REG_DT를 기준으로 필터링할 수 있음. 
            # REG_DT는 YYYYMMDD 형식이므로 이를 사용하거나 SAVE_TIME(YYYY-MM-DD HH:MM:SS)을 사용.
            # 여기서는 SAVE_TIME을 기준으로 처리
            query += f" AND SAVE_TIME >= datetime('now', '-{days_limit} days', 'localtime')"

        query += " ORDER BY REG_DT DESC, SAVE_TIME DESC"

        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        self.close_connection()
        
        return [dict(row) for row in rows]

    async def fetch_ls_detail_targets(self):
        """
        LS증권(SEC_FIRM_ORDER=0) 레포트 중 TELEGRAM_URL이 .pdf로 끝나지 않는 대상을 조회합니다.
        """
        query = """
        SELECT 
            report_id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
            ATTACH_URL, ARTICLE_TITLE, ARTICLE_URL, MAIN_CH_SEND_YN, 
            DOWNLOAD_URL, WRITER, SAVE_TIME, TELEGRAM_URL, KEY
        FROM 
            data_main_daily_send
        WHERE 
            SEC_FIRM_ORDER = 0
            AND (TELEGRAM_URL NOT LIKE '%.pdf' OR TELEGRAM_URL IS NULL OR TELEGRAM_URL = '')
        """
        return await self.execute_query(query)

    async def update_telegram_url(self, record_id, telegram_url, article_title=None, pdf_url=None):
        """report_id를 기준으로 TELEGRAM_URL 및 (옵션) ARTICLE_TITLE 컬럼을 비동기로 업데이트합니다."""
        async with aiosqlite.connect(self.db_path) as db:
            # pdf_url이 없으면 telegram_url을 기본값으로 사용
            if pdf_url is None:
                pdf_url = telegram_url

            # 기본 쿼리 구성
            query = """
            UPDATE data_main_daily_send
            SET TELEGRAM_URL = ?, PDF_URL = ?
            WHERE report_id = ?
            """
            params = [telegram_url, pdf_url, record_id]  # 기본 매개변수

            # article_title이 주어진 경우 쿼리에 추가
            if article_title is not None:
                query = """
                UPDATE data_main_daily_send
                SET TELEGRAM_URL = ?, PDF_URL = ?, ARTICLE_TITLE = ?
                WHERE report_id = ?
                """
                params = [telegram_url, pdf_url, article_title, record_id]

            # 쿼리 실행 및 커밋
            await db.execute(query, params)
            await db.commit()

        return {
            "status": "success",
            "query": query,
            "record_id": record_id,
            "telegram_url": telegram_url,
            "pdf_url": pdf_url,
            "article_title": article_title
        }
    
    async def execute_query(self, query, params=None, close=False):
        """주어진 쿼리를 실행하고 결과를 반환합니다. 필요 시 커넥션을 종료합니다."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.cursor() as cursor:
                try:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    
                    # SELECT 쿼리인 경우 fetch 결과 반환
                    if query.strip().lower().startswith("select"):
                        rows = await cursor.fetchall()
                        result = [dict(row) for row in rows]
                    else:
                        # INSERT, UPDATE, DELETE 쿼리인 경우 commit 후 영향받은 행 반환
                        await conn.commit()
                        result = {"status": "success", "affected_rows": cursor.rowcount}
                except Exception as e:
                    result = {"status": "error", "error": str(e)}
                finally:
                    if close:  # close가 True일 경우 커넥션을 종료
                        await conn.close()
        return result
    
    async def daily_select_data(self, date_str=None, type=None):
        print(f"date_str: {date_str}, type: {type}")
        """data_main_daily_send 테이블에서 지정된 날짜 또는 당일 데이터를 조회합니다."""
        
        # 'type' 파라미터가 필수임을 확인
        if type not in ['send', 'download']:
            raise ValueError("Invalid type. Must be 'send' or 'download'.")

        if date_str is None:
            # date_str가 없으면 현재 날짜 사용
            query_date = datetime.now().strftime('%Y-%m-%d')
            query_reg_dt = (datetime.now() + timedelta(days=2)).strftime('%Y%m%d')  # 2일 추가
        else:
            # yyyymmdd 형식의 날짜를 yyyy-mm-dd로 변환
            query_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
            query_reg_dt = (datetime.strptime(date_str, '%Y%m%d') + timedelta(days=2)).strftime('%Y%m%d')  # 2일 추가

        # 쿼리 타입에 따라 조건을 다르게 설정
        if type == 'send':
            query_condition = "(MAIN_CH_SEND_YN != 'Y' OR MAIN_CH_SEND_YN IS NULL)"
            query_condition += "AND (SEC_FIRM_ORDER != 19 OR (SEC_FIRM_ORDER = 19 AND TELEGRAM_URL <> ''))"
        elif type == 'download':
            query_condition = "MAIN_CH_SEND_YN = 'Y' AND DOWNLOAD_STATUS_YN != 'Y'"

        # 3일 이내 조건 추가
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y%m%d')

        # SQL 쿼리 문자열을 읽기 쉽도록 포맷팅
        query = f"""
        SELECT 
            report_id,
            SEC_FIRM_ORDER, 
            ARTICLE_BOARD_ORDER, 
            FIRM_NM, 
            REG_DT,
            ATTACH_URL, 
            ARTICLE_TITLE, 
            ARTICLE_URL, 
            MAIN_CH_SEND_YN, 
            DOWNLOAD_URL, 
            WRITER, 
            SAVE_TIME,
            TELEGRAM_URL,
            MAIN_CH_SEND_YN
        FROM 
            data_main_daily_send 
        WHERE 
            DATE(SAVE_TIME) = '{query_date}'
            AND REG_DT >= '{three_days_ago}'
            AND REG_DT <= '{query_reg_dt}'
            AND {query_condition}
        GROUP BY (CASE WHEN TELEGRAM_URL IS NULL OR TELEGRAM_URL = '' THEN report_id ELSE TELEGRAM_URL END)
        ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
        """
        
        # SQL 쿼리 실행
        print('='*30)
        print(query)
        print('='*30)
        rows = await self.execute_query(query)
        # rows = cursor.fetchall()
        # # rows를 dict 형태로 변환
        # rows = [dict(row) for row in rows]

        return rows

    async def daily_update_data(self, date_str=None, fetched_rows=None, type=None):
        """
        데이터베이스의 데이터를 업데이트하는 함수입니다.
        
        Args:
            fetched_rows (list[dict] or dict): 'send' 타입일 경우에는 업데이트할 여러 행의 리스트를 전달하고, 
                                            'download' 타입일 경우에는 단일 행의 딕셔너리를 전달합니다.
            type (str): 업데이트 유형을 지정합니다. 'send' 또는 'download' 중 하나를 선택해야 합니다.
                        'send'는 여러 행을 업데이트하고, 'download'는 단일 행을 업데이트합니다.
        
        Raises:
            ValueError: 'type'이 'send' 또는 'download'가 아닌 경우 예외를 발생시킵니다.
        
        """
        
        """데이터를 업데이트합니다. type에 따라 업데이트 쿼리가 달라집니다."""
        
        if date_str is None:
            # date_str가 없으면 현재 날짜 사용
            query_date = datetime.now().strftime('%Y-%m-%d')
        else:
            # yyyymmdd 형식의 날짜를 yyyy-mm-dd로 변환
            query_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

        # 'type' 파라미터가 필수임을 확인
        if type not in ['send', 'download']:
            raise ValueError("Invalid type. Must be 'send' or 'download'.")

        # 'send' 타입에 대한 업데이트 처리
        if type == 'send':
            # 여러 건의 데이터를 업데이트
            for row in fetched_rows:
                telegram_url = row.get('TELEGRAM_URL')
                
                if telegram_url:
                    update_query = """
                        UPDATE data_main_daily_send
                        SET MAIN_CH_SEND_YN = 'Y'
                        WHERE TELEGRAM_URL = ?
                    """
                    param = (telegram_url,)
                else:
                    update_query = """
                        UPDATE data_main_daily_send
                        SET MAIN_CH_SEND_YN = 'Y'
                        WHERE report_id = ?
                    """
                    param = (row['report_id'],)

                print(f"Row data: {row}")
                print(f"Executing query: {update_query}")
                print(f"With parameters: {param}")
                
                # 업데이트 쿼리 실행
                rows = await self.execute_query(update_query, param)

        # 'download' 타입에 대한 업데이트 처리
        elif type == 'download':
            update_query = """
                UPDATE data_main_daily_send
                SET 
                    DOWNLOAD_STATUS_YN = 'Y'
                WHERE 
                    report_id = ?  -- report_id를 기준으로 업데이트
            """
            # 단일 행 데이터 업데이트
            print(f"Single row for download: {fetched_rows}")
            
            # 쿼리와 파라미터를 출력합니다.
            print(f"Executing query: {update_query}")
            print(f"With parameters: {(fetched_rows['report_id'],)}")
            
            # 업데이트 쿼리 실행
            rows = await self.execute_query(update_query, (fetched_rows['report_id'],))
        return rows

    async def update_report_summary_by_telegram_url(self, telegram_url, summary, model_name):
        """TELEGRAM_URL이 일치하고 발송완료(MAIN_CH_SEND_YN='Y')된 레코드 중 report_id가 가장 큰 최신 레코드에 요약 정보를 업데이트합니다."""
        query = """
        UPDATE data_main_daily_send
        SET GEMINI_SUMMARY = ?, 
            SUMMARY_TIME = ?, 
            SUMMARY_MODEL = ?
        WHERE TELEGRAM_URL = ?
          AND MAIN_CH_SEND_YN = 'Y'
          AND report_id = (
              SELECT MAX(report_id) 
              FROM data_main_daily_send 
              WHERE TELEGRAM_URL = ? 
                AND MAIN_CH_SEND_YN = 'Y'
          )
        """
        now = datetime.now().isoformat()
        params = (summary, now, model_name, telegram_url, telegram_url)
        return await self.execute_query(query, params)

    async def update_report_summary(self, record_id, summary, model_name):
        """data_main_daily_send 테이블의 특정 report_id 레코드에 제미나이 요약 내용을 업데이트합니다."""
        query = """
        UPDATE data_main_daily_send
        SET GEMINI_SUMMARY = ?, 
            SUMMARY_TIME = ?, 
            SUMMARY_MODEL = ?
        WHERE report_id = ?
        """
        now = datetime.now().isoformat()
        params = (summary, now, model_name, record_id)
        
        return await self.execute_query(query, params)

    async def fetch_pending_summary_reports(self, limit=10):
        """요약이 아직 생성되지 않은 최근 레포트 목록을 조회합니다. (보안 PDF 증권사 등은 제외)"""
        # 제외 대상: 19(DB금융투자)
        exclude_firms = (19,) 
        
        query = """
        SELECT *
        FROM data_main_daily_send
        WHERE (GEMINI_SUMMARY IS NULL OR GEMINI_SUMMARY = '')
        AND (ATTACH_URL IS NOT NULL AND ATTACH_URL != '')
        AND SEC_FIRM_ORDER NOT IN ({})
        ORDER BY SAVE_TIME DESC
        LIMIT ?
        """.format(", ".join(map(str, exclude_firms)))
        
        return await self.execute_query(query, (limit,))

async def main():
    db_manager = SQLiteManager()
    rows = await db_manager.daily_select_data(date_str='20241230', type='send')
    # 쿼리 실행
    query_result = db_manager.execute_query("SELECT * FROM data_main_daily_send", close=True)
    print(query_result)

# 예시 사용법
if __name__ == "__main__":
    async def main():
        db = SQLiteManager()
        rows = await db.daily_select_data(type='send')
        print(rows)
        if rows:
            r = await db.daily_update_data(fetched_rows=rows, type='send')
            print(r)

    asyncio.run(main())