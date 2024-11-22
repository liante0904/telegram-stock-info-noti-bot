import json
import sqlite3
import os
import argparse
from datetime import datetime, timedelta
import sys
import os
from dotenv import load_dotenv
# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가(package 폴더에 있으므로)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo  # 이미 정의된 FirmInfo 클래스

load_dotenv()  # .env 파일의 환경 변수를 로드합니다
env = os.getenv('ENV')
print(env)
if env == 'production':
    PROJECT_DIR = os.getenv('PROJECT_DIR')
    HOME_DIR    = os.getenv('HOME_DIR')
    JSON_DIR    = os.getenv('JSON_DIR')
else:
    PROJECT_DIR = os.getenv('PROJECT_DIR')
    HOME_DIR    = os.getenv('HOME_DIR')
    JSON_DIR    = os.getenv('JSON_DIR')


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
    
    # 조회할 테이블 목록과 TELEGRAM_URL 존재 여부
    tables = [
        {'name': 'data_main_daily_send', 'use_telegram_url': True},
        {'name': 'hankyungconsen_research', 'use_telegram_url': False},
        {'name': 'naver_research', 'use_telegram_url': False}
    ]
    query_parts = []

    for table in tables:
        if table['use_telegram_url']:
            # TELEGRAM_URL이 있는 테이블
            query_parts.append(f"""
                SELECT FIRM_NM, ARTICLE_TITLE, 
                    COALESCE(TELEGRAM_URL, DOWNLOAD_URL, ATTACH_URL) AS TELEGRAM_URL, 
                    SAVE_TIME, SEND_USER
                FROM {table['name']}
                WHERE ARTICLE_TITLE LIKE '%{keyword}%'
                AND DATE(SAVE_TIME) = '{date}'
                AND (SEND_USER IS NULL OR SEND_USER NOT LIKE '%"{user_id}"%')
            """)
        else:
            # TELEGRAM_URL이 없는 테이블
            query_parts.append(f"""
                SELECT FIRM_NM, ARTICLE_TITLE, 
                    COALESCE(DOWNLOAD_URL, ATTACH_URL) AS TELEGRAM_URL, 
                    SAVE_TIME, SEND_USER
                FROM {table['name']}
                WHERE ARTICLE_TITLE LIKE '%{keyword}%'
                AND DATE(SAVE_TIME) = '{date}'
                AND (SEND_USER IS NULL OR SEND_USER NOT LIKE '%"{user_id}"%')
            """)

    # 전체 쿼리 조합
    final_query = " UNION ".join(query_parts) + " ORDER BY SAVE_TIME ASC, FIRM_NM ASC"

    # 쿼리 출력
    print("Generated SQL Query:")
    print(final_query)

    # 쿼리 실행
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

async def daily_select_data(date_str=None, type=None):
    # SQLite 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    # 커서의 row_factory를 sqlite3.Row로 설정
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
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
        id,
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
    ORDER BY SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, SAVE_TIME
    """
    
    # SQL 쿼리 실행
    print('='*30)
    print(query)
    print('='*30)
    cursor.execute(query)
    rows = cursor.fetchall()
    # rows를 dict 형태로 변환
    rows = [dict(row) for row in rows]

    return rows


async def daily_update_data(date_str=None, fetched_rows=None, type=None):
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
    
    # SQLite 데이터베이스 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
        update_query = """
            UPDATE data_main_daily_send
            SET 
                MAIN_CH_SEND_YN = 'Y'
            WHERE 
                id = ?  -- id를 기준으로 업데이트
        """
        # 여러 건의 데이터를 업데이트
        for row in fetched_rows:
            print(f"Row data: {row}")
            
            # 쿼리와 파라미터를 출력
            print(f"Executing query: {update_query}")
            print(f"With parameters: {(row['id'],)}")
            
            # 업데이트 쿼리 실행
            cursor.execute(update_query, (row['id'],))

    # 'download' 타입에 대한 업데이트 처리
    elif type == 'download':
        update_query = """
            UPDATE data_main_daily_send
            SET 
                DOWNLOAD_STATUS_YN = 'Y'
            WHERE 
                id = ?  -- id를 기준으로 업데이트
        """
        # 단일 행 데이터 업데이트
        print(f"Single row for download: {fetched_rows}")
        
        # 쿼리와 파라미터를 출력합니다.
        print(f"Executing query: {update_query}")
        print(f"With parameters: {(fetched_rows['id'],)}")
        
        # 업데이트 쿼리 실행
        cursor.execute(update_query, (fetched_rows['id'],))

    # 변경 사항 저장 및 커넥션 닫기
    conn.commit()

def open_db_connection():
    """SQLite 데이터베이스에 연결하고 커서를 반환합니다."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    return conn, cursor

def close_db_connection(conn, cursor):
    """데이터베이스 연결과 커서를 종료합니다."""
    cursor.close()
    conn.close()

def main():

    # 명령행 인자 파서 설정
    parser = argparse.ArgumentParser(description="SQLite Database Management Script")
    parser.add_argument('action', nargs='?', choices=['table', 'insert', 'select', 'fetch', 'keyword_select', 'daily', 'save'], help="Action to perform")
    parser.add_argument('name', nargs='?', help="Table name for the action")
    args = parser.parse_args()

    if args.action == 'fetch':
        print(args.name)
        fetch_data(date='2024-08-21', keyword=args.name)
    elif args.action == 'daily':
        daily_select_data(args.name)


cursor.close()
conn.close()
        
if __name__ == "__main__":
    main()