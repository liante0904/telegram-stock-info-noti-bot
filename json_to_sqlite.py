import json
import sqlite3
import os
import argparse
from datetime import datetime

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

def format_message(data_list):
    """데이터를 포맷팅하여 문자열로 반환합니다."""
    EMOJI_PICK = u'\U0001F449'  # 이모지 설정
    formatted_messages = []

    # 특정 FIRM_NM을 제외할 리스트
    EXCLUDED_FIRMS = {"네이버", "조선비즈"}

    # data_list가 단일 데이터 항목일 경우, 리스트로 감싸줍니다.
    if isinstance(data_list, tuple):
        data_list = [data_list]

    last_firm_nm = None  # 마지막으로 출력된 FIRM_NM을 저장하는 변수

    for data in data_list:
        # 데이터 항목을 사전으로 변환
        data_dict = {
            'FIRM_NM': data[0],
            'ARTICLE_TITLE': data[1],
            'ATTACH_URL': data[2],
            'SAVE_TIME': data[3]
        }
        
        ARTICLE_TITLE = data_dict['ARTICLE_TITLE']
        ARTICLE_URL = data_dict['ATTACH_URL']
        
        sendMessageText = ""
        
        # 'FIRM_NM'이 존재하는 경우에만 포함
        if 'FIRM_NM' in data_dict:
            FIRM_NM = data_dict['FIRM_NM']
            # data_list가 단건인 경우, 회사명 출력을 생략
            if len(data_list) > 1:
                # 제외할 FIRM_NM이 아닌 경우에만 처리
                if '네이버' not in FIRM_NM and '조선비즈' not in FIRM_NM:
                    # 새로운 FIRM_NM이거나 첫 번째 데이터일 때만 FIRM_NM을 포함
                    if FIRM_NM != last_firm_nm:
                        sendMessageText += "\n\n" + "●" + FIRM_NM + "\n"
                        last_firm_nm = FIRM_NM
        
        # 게시글 제목(굵게)
        sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
        # 원문 링크
        sendMessageText += EMOJI_PICK + "[링크]" + "(" + ARTICLE_URL + ")" + "\n"
        formatted_messages.append(sendMessageText)
    
    # 모든 메시지를 하나의 문자열로 결합합니다.
    return "\n".join(formatted_messages)

def keyword_select(keyword):
    """특정 키워드가 포함된 기사 제목을 가진 데이터를 조회하고, 특정 조건에 따라 필터링합니다."""
    today = datetime.now().strftime('%Y-%m-%d')  # 오늘 날짜를 'YYYY-MM-DD' 형식으로 저장

    # 기준 테이블에서 키워드 포함 데이터 추출
    cursor.execute(f"""
        SELECT FIRM_NM, ARTICLE_TITLE, ATTACH_URL AS ARTICLE_URL, SAVE_TIME
        FROM data_main_daily_send
        WHERE ARTICLE_TITLE LIKE ? AND DATE(SAVE_TIME) = ?
    """, (f'%{keyword}%', today))
    main_results = cursor.fetchall()
    main_firms = {row[0] for row in main_results}  # 기준 테이블의 증권사 목록

    print(f"\nResults containing '{keyword}' on {today}:")
    for result in main_results:
        print(result)

    # 다른 테이블에서 키워드 포함 데이터를 추출하며, 기준 테이블에 없는 증권사만 추출
    query_parts = [
        f"""
        SELECT FIRM_NM, ARTICLE_TITLE, ATTACH_URL AS ARTICLE_URL, SAVE_TIME
        FROM {table}
        WHERE ARTICLE_TITLE LIKE ? AND DATE(SAVE_TIME) = ? AND FIRM_NM NOT IN ({','.join('?'*len(main_firms))})
        """
        for table in json_files.values()
        if table != 'data_main_daily_send'
    ]

    # 전체 쿼리 조합
    union_query = " UNION ".join(query_parts)
    params = [f'%{keyword}%', today] * (len(json_files) - 1) + list(main_firms) * (len(json_files) - 1)

    # `ORDER BY` 추가: SAVE_TIME과 FIRM_NM으로 정렬
    final_query = f"""
    {union_query}
    ORDER BY SAVE_TIME ASC, FIRM_NM ASC
    """
    cursor.execute(final_query, params)

    other_results = cursor.fetchall()
    formatted_message = format_message(main_results + other_results)
    print(formatted_message)
    return formatted_message

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
