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

def main():

    # 명령행 인자 파서 설정
    parser = argparse.ArgumentParser(description="SQLite Database Management Script")
    parser.add_argument('action', nargs='?', choices=['table', 'insert', 'select', 'fetch', 'keyword_select', 'daily', 'save'], help="Action to perform")
    parser.add_argument('name', nargs='?', help="Table name for the action")
    args = parser.parse_args()

    if args.action == 'fetch':
        print(args.name)
        fetch_data(date='2024-08-21', keyword=args.name)

cursor.close()
conn.close()
        
if __name__ == "__main__":
    main()