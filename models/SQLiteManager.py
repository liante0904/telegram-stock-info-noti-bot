import json
import sqlite3
import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv() # .env 파일의 환경 변수를 로드합니다
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
    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None
        self.cursor = None

    def open_connection(self):
        """SQLite 데이터베이스에 연결합니다."""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()

    def close_connection(self):
        """데이터베이스 연결과 커서를 종료합니다."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()

    def create_table(self, table_name, columns):
        """테이블을 생성합니다."""
        columns_str = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        self.cursor.execute(query)
        self.connection.commit()

    def insert_data(self, table_name, data):
        """데이터를 삽입합니다."""
        placeholders = ', '.join('?' for _ in data)
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"
        self.cursor.execute(query, data)
        self.connection.commit()

    def fetch_all(self, table_name):
        """테이블의 모든 데이터를 가져옵니다."""
        query = f"SELECT * FROM {table_name}"
        self.cursor.execute(query)
        return self.cursor.fetchall()

# 테스트 코드 및 메인 코드
if __name__ == "__main__":
    # SQLiteManager 인스턴스 생성
    db_manager = SQLiteManager(db_path)

    # 데이터베이스 연결
    db_manager.open_connection()

    # JSON 파일 리스트와 대응되는 테이블 이름
    json_files = {
        "data_main_daily_send.json": "data_main_daily_send",
        "hankyungconsen_research.json": "hankyungconsen_research",
        "naver_research.json": "naver_research"
    }

    # 각 JSON 파일에 대해 테이블 생성 및 데이터 삽입
    for json_file, table_name in json_files.items():
        # JSON 파일 경로 설정
        json_file_path = os.path.join(JSON_DIR, json_file)

        # 테이블 생성 (예: id, name, created_at 컬럼)
        db_manager.create_table(table_name, {
            'id': 'INTEGER PRIMARY KEY',
            'name': 'TEXT',
            'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
        })

        # JSON 파일에서 데이터 읽기
        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)

                # 데이터 삽입 (여기서는 data의 구조에 맞춰 조정해야 함)
                for item in data:
                    db_manager.insert_data(table_name, (item['id'], item['name']))

        except FileNotFoundError:
            print(f"파일이 존재하지 않습니다: {json_file_path}")
        except json.JSONDecodeError:
            print(f"JSON 파일을 파싱하는 중 오류가 발생했습니다: {json_file_path}")
        except Exception as e:
            print(f"오류 발생: {str(e)}")

    # 데이터 조회 예시
    for table_name in json_files.values():
        print(f"\nTable: {table_name}")
        records = db_manager.fetch_all(table_name)
        for record in records:
            print(record)

    # 데이터베이스 연결 종료
    db_manager.close_connection()
