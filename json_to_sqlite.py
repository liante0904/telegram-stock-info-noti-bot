import json
import sqlite3
import os
import argparse

# 데이터베이스 파일 경로
db_path = os.path.expanduser('~/sqlite3/telegram.db')

# SQLite 데이터베이스 연결
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# JSON 파일 리스트와 대응되는 테이블 이름
json_files = {
    "data_main_daily_send.json": "data_main_daily_send",
    "hankyungconsen_research.json": "hankyungconsen",
    "naver_research.json": "naver_research"
}

# 명령행 인자 파서 설정
parser = argparse.ArgumentParser(description="SQLite Database Management Script")
parser.add_argument('action', nargs='?', choices=['table', 'insert', 'select'], help="Action to perform")
parser.add_argument('name', nargs='?', help="Table name for the action")
args = parser.parse_args()

def print_tables():
    """데이터베이스에 존재하는 테이블 목록을 출력합니다."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    if tables:
        print("Tables in the database:")
        for table in tables:
            print(table[0])
    else:
        print("No tables found in the database.")

def insert_data():
    """JSON 파일의 데이터를 데이터베이스 테이블에 삽입합니다."""
    for json_file, table_name in json_files.items():
        with open(f'~/json/{json_file}', 'r', encoding='utf-8') as file:
            data = json.load(file)
            for entry in data:
                cursor.execute(f'''
                    INSERT OR IGNORE INTO {table_name} (
                        SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRM_NM, 
                        ATTACH_URL, ARTICLE_TITLE, SAVE_TIME
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    entry["SEC_FIRM_ORDER"],
                    entry["ARTICLE_BOARD_ORDER"],
                    entry["FIRM_NM"],
                    entry["ATTACH_URL"],
                    entry["ARTICLE_TITLE"],
                    entry["SAVE_TIME"]
                ))
    print("Data inserted successfully.")
    conn.commit()

def select_data(table=None):
    """특정 테이블 또는 모든 테이블의 데이터를 조회합니다."""
    if table:
        tables = [table]
    else:
        tables = json_files.values()
    
    for table_name in tables:
        print(f'\nContents of table {table_name}:')
        cursor.execute(f'SELECT * FROM {table_name}')
        rows = cursor.fetchall()
        for row in rows:
            print(row)

# 명령 실행
if args.action == 'table' or args.action is None:
    print_tables()
elif args.action == 'insert':
    insert_data()
elif args.action == 'select':
    select_data(args.name)

# 연결 종료
conn.close()
