import aiosqlite
import json
import sqlite3
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
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
                    DOWNLOAD_URL, TELEGRAM_URL, WRITER, KEY, SAVE_TIME 
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(KEY) DO UPDATE SET
                    REG_DT = excluded.REG_DT,  -- 항상 갱신
                    WRITER = excluded.WRITER,  -- 항상 갱신
                    DOWNLOAD_URL = CASE 
                        WHEN excluded.DOWNLOAD_URL IS NOT NULL AND excluded.DOWNLOAD_URL != '' 
                        THEN excluded.DOWNLOAD_URL 
                        ELSE DOWNLOAD_URL -- 기존 값을 유지
                    END,
                    TELEGRAM_URL = CASE 
                        WHEN excluded.TELEGRAM_URL IS NOT NULL AND excluded.TELEGRAM_URL != '' 
                        THEN excluded.TELEGRAM_URL 
                        ELSE TELEGRAM_URL -- 기존 값을 유지
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
                entry.get("WRITER", ''),
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
            id, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, REG_DT,
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

    async def update_telegram_url(self, record_id, telegram_url, article_title=None):
        """id를 기준으로 TELEGRAM_URL 및 (옵션) ARTICLE_TITLE 컬럼을 비동기로 업데이트합니다."""
        async with aiosqlite.connect(self.db_path) as db:
            # 기본 쿼리 구성
            query = """
            UPDATE data_main_daily_send
            SET TELEGRAM_URL = ?
            WHERE id = ?
            """
            params = [telegram_url, record_id]  # 기본 매개변수

            # article_title이 주어진 경우 쿼리에 추가
            if article_title is not None:
                query = """
                UPDATE data_main_daily_send
                SET TELEGRAM_URL = ?, ARTICLE_TITLE = ?
                WHERE id = ?
                """
                params = [telegram_url, article_title, record_id]

            # 쿼리 실행 및 커밋
            await db.execute(query, params)
            await db.commit()

        return {
            "status": "success",
            "query": query,
            "record_id": record_id,
            "telegram_url": telegram_url,
            "article_title": article_title
        }
    
    def execute_query(self, query, params=None):
        """주어진 쿼리를 실행하고 결과를 반환합니다."""
        self.open_connection()
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            # SELECT 쿼리인 경우 fetch 결과 반환
            if query.strip().lower().startswith("select"):
                rows = self.cursor.fetchall()
                result = [dict(row) for row in rows]
            else:
                # INSERT, UPDATE, DELETE 쿼리인 경우 commit 후 영향받은 행 반환
                self.connection.commit()
                result = {"status": "success", "affected_rows": self.cursor.rowcount}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
        finally:
            self.close_connection()
        return result
# 메인 코드
if __name__ == "__main__":
    db_manager = SQLiteManager()
    db_manager.open_connection()

    json_files = {
        "hankyungconsen_research.json": "hankyungconsen_research",
        "naver_research.json": "naver_research"
    }

    for json_file, table_name in json_files.items():
        json_file_path = os.path.join(JSON_DIR, json_file)

        table_creation_result = db_manager.create_table(table_name, {
            'id': 'INTEGER PRIMARY KEY',
            'name': 'TEXT',
            'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
        })
        print(table_creation_result)

        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
                for item in data:
                    insertion_result = db_manager.insert_data(table_name, (item['id'], item['name']))
                    print(insertion_result)
        except FileNotFoundError:
            print(f"파일이 존재하지 않습니다: {json_file_path}")
        except json.JSONDecodeError:
            print(f"JSON 파일을 파싱하는 중 오류가 발생했습니다: {json_file_path}")
        except Exception as e:
            print(f"오류 발생: {str(e)}")

    for table_name in json_files.values():
        print(f"\nTable: {table_name}")
        records = db_manager.fetch_all(table_name)
        for record in records:
            print(record)

    db_manager.close_connection()
