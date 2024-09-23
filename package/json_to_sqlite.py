import json
import sqlite3
import os
import argparse
from datetime import datetime
import sys
import os
# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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
    "hankyungconsen_research.json": "hankyungconsen_research",
    "naver_research.json": "naver_research"
}

# 명령행 인자 파서 설정
parser = argparse.ArgumentParser(description="SQLite Database Management Script")
parser.add_argument('action', nargs='?', choices=['table', 'insert', 'select', 'fetch', 'keyword_select', 'daily'], help="Action to perform")
parser.add_argument('name', nargs='?', help="Table name for the action")
args = parser.parse_args()


def fetch_data(date=None, keyword=None, user_id=None):
    """특정 테이블에서 데이터를 조회하고, 파라미터가 포함된 실제 쿼리를 출력합니다.

    :param date: 조회일자. 'YYYYMMDD' 또는 'YYMMDD' 형식도 지원하며, 없을 경우 오늘 날짜를 사용합니다.
    :param keyword: 필수 파라미터로, ARTICLE_TITLE을 검색합니다.
    :param user_id: 조회 시 제외할 사용자 ID.
    :return: 조회된 데이터의 리스트
    """
    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    else:
        # 날짜가 이미 'YYYY-MM-DD' 형식인지 확인
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            # 날짜 형식 변환 (YYYYMMDD 또는 YYMMDD → YYYY-MM-DD)
            if len(date) == 8:  # YYYYMMDD
                date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')
            elif len(date) == 6:  # YYMMDD
                date = datetime.strptime(date, '%y%m%d').strftime('%Y-%m-%d')
            else:
                raise ValueError("Invalid date format. Use 'YYYYMMDD', 'YYMMDD', or 'YYYY-MM-DD'.")

    if keyword is None:
        raise ValueError("keyword 파라미터는 필수입니다.")
    
    # 조회할 테이블 목록
    tables = ['data_main_daily_send', 'hankyungconsen_research', 'naver_research']
    query_parts = []

    for table in tables:
        query_parts.append(f"""
            SELECT FIRM_NM, ARTICLE_TITLE, ATTACH_URL AS ARTICLE_URL, SAVE_TIME, SEND_USER
            FROM {table}
            WHERE ARTICLE_TITLE LIKE '%{keyword}%' 
              AND DATE(SAVE_TIME) = '{date}'
              AND (SEND_USER IS NULL OR SEND_USER NOT LIKE '%"{user_id}"%')
        """)

    # 전체 쿼리 조합
    final_query = " UNION ".join(query_parts) + " ORDER BY SAVE_TIME ASC, FIRM_NM ASC"

    # 쿼리 출력
    print("Generated SQL Query:")
    print(final_query)

    cursor.execute(final_query)
    results = cursor.fetchall()

    # 조회된 데이터 출력
    print("\nFetched Data:")
    for row in results:
        print(row)

    conn.close()
    return results

def update_data(date=None, keyword=None, user_ids=None):
    """특정 키워드와 날짜를 기준으로 여러 테이블의 데이터를 업데이트하며, 파라미터가 포함된 실제 쿼리를 출력합니다.
    
    :param date: 조회일자. 'YYYYMMDD' 또는 'YYMMDD' 형식도 지원하며, 없을 경우 오늘 날짜를 사용합니다.
    :param keyword: 필수 파라미터로, ARTICLE_TITLE을 검색합니다.
    :param user_ids: 필수 파라미터로, SEND_USER 컬럼에 저장할 사용자 ID 리스트. 문자열 형태로 저장됩니다.
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    else:
        # 날짜 형식 변환 (YYYYMMDD 또는 YYMMDD → YYYY-MM-DD)
        if len(date) == 8:  # YYYYMMDD
            date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')
        elif len(date) == 6:  # YYMMDD
            date = datetime.strptime(date, '%y%m%d').strftime('%Y-%m-%d')
        else:
            raise ValueError("Invalid date format. Use 'YYYYMMDD', 'YYMMDD', or 'YYYY-MM-DD'.")

    if keyword is None:
        raise ValueError("keyword 파라미터는 필수입니다.")

    if user_ids is None:
        raise ValueError("user_ids 파라미터는 필수입니다.")

    # 사용자 ID를 JSON 문자열로 변환
    user_ids_json = json.dumps(user_ids)

    # 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 업데이트할 테이블 목록
    tables = ['data_main_daily_send', 'hankyungconsen_research', 'naver_research']

    for table in tables:
        # 데이터 업데이트 쿼리
        update_query = f"""
            UPDATE {table}
            SET SEND_USER = '{user_ids_json}'
            WHERE ARTICLE_TITLE LIKE '%{keyword}%' AND DATE(SAVE_TIME) = '{date}'
        """

        # 쿼리 출력
        print(f"Generated SQL Query for {table}:")
        print(update_query)

        cursor.execute(update_query)
        
        # 업데이트된 행 수 출력
        print(f"{cursor.rowcount} rows updated in {table}.")

    conn.commit()
    conn.close()

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

def daily_select_data(date_str=None):
    """data_main_daily_send 테이블에서 지정된 날짜 또는 당일 데이터를 조회합니다。"""
    if date_str is None:
        # date_str가 없으면 현재 날짜 사용
        query_date = datetime.now().strftime('%Y-%m-%d')
    else:
        # yyyymmdd 형식의 날짜를 yyyy-mm-dd로 변환
        query_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    # SQL 쿼리 실행
    # SQL 쿼리 문자열을 읽기 쉽도록 포맷팅
    query = f"""
    SELECT 
        id,
        FIRM_NM, 
        ARTICLE_TITLE, 
        ATTACH_URL AS ARTICLE_URL, 
        SAVE_TIME, 
        SEND_USER 
    FROM 
        data_main_daily_send 
    WHERE 
        DATE(SAVE_TIME) = '{query_date}'
    ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME    
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    return rows

# 명령 실행
if args.action == 'table' or args.action is None:
    print_tables()
elif args.action == 'insert':
    insert_data()
elif args.action == 'select':
    select_data(args.name)
elif args.action == 'fetch':
    print(args.name)
    fetch_data(date='2024-08-21', keyword=args.name)
elif args.action == 'keyword_select':
    if args.name:
        keyword_select(args.name)
    else:
        print("Error: 'keyword_select' action requires a keyword argument.")

elif args.action == 'daily':
    daily_select_data(args.name)
# 연결 종료
conn.close()
