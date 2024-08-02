import json
import sqlite3
import os
import argparse

# 데이터베이스 파일 경로
db_path = os.path.expanduser('~/sqlite3/telegram.db')

# 현재 스크립트 파일의 디렉토리 경로
script_dir = os.path.dirname(os.path.abspath(__file__))

# JSON 파일 경로
json_dir = os.path.join(script_dir, 'json')

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
parser.add_argument('action', nargs='?', choices=['table', 'insert', 'select', 'keyword_select'], help="Action to perform")
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
        json_file_path = os.path.join(json_dir, json_file)
        print(json_file_path)
        with open(json_file_path, 'r', encoding='utf-8') as file:
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

def keyword_select(keyword):
    """특정 키워드가 포함된 기사 제목을 가진 데이터를 조회하고, 특정 조건에 따라 필터링합니다."""
    # 기준 테이블에서 키워드 포함 데이터 추출
    cursor.execute(f"""
        SELECT FIRM_NM, ARTICLE_TITLE, SAVE_TIME
        FROM data_main_daily_send
        WHERE ARTICLE_TITLE LIKE ?
    """, (f'%{keyword}%',))
    main_results = cursor.fetchall()
    main_firms = {row[0] for row in main_results}  # 기준 테이블의 증권사 목록

    print(f"\nResults from data_main_daily_send containing '{keyword}':")
    for result in main_results:
        print(result)

    # 다른 테이블에서 키워드 포함 데이터를 추출하며, 기준 테이블에 없는 증권사만 추출
    other_tables = [table for table in json_files.values() if table != 'data_main_daily_send']
    for table in other_tables:
        cursor.execute(f"""
            SELECT FIRM_NM, ARTICLE_TITLE, SAVE_TIME
            FROM {table}
            WHERE ARTICLE_TITLE LIKE ? AND FIRM_NM NOT IN ({', '.join('?'*len(main_firms))})
        """, (f'%{keyword}%', *main_firms))

        other_results = cursor.fetchall()
        
        print(f"\nResults from {table} containing '{keyword}':")
        for result in other_results:
            print(result)

# 명령 실행
if args.action == 'table' or args.action is None:
    print_tables()
elif args.action == 'insert':
    insert_data()
elif args.action == 'select':
    select_data(args.name)
elif args.action == 'keyword_select':
    if args.name:
        keyword_select(args.name)
    else:
        print("Error: 'keyword_select' action requires a keyword argument.")

# 연결 종료
conn.close()
