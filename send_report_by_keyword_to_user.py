import json
import sqlite3
import os
import sys
import asyncio
import argparse
from datetime import datetime
from dotenv import load_dotenv
# 현재 스크립트의 상위 디렉터리를 모듈 경로에 추가(package 폴더에 있으므로)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo  # 이미 정의된 FirmInfo 클래스

# 프로젝트 내부 모듈 경로 추가
from utils.sqlite_util import format_message_sql
from utils.telegram_util import sendMarkDownText
from models.SecretKey import SecretKey


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



# 현재 스크립트 파일의 디렉토리 경로
script_dir = os.path.dirname(os.path.abspath(__file__))

# JSON 파일 경로
json_dir = os.path.join(script_dir, 'json')

# 데이터베이스 파일 경로
db_path = os.path.expanduser('~/sqlite3/telegram.db')



# 비밀키 불러오기
SECRET_KEY = SecretKey()
token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET

# 파일 경로를 현재 디렉토리 기준으로 얻는 함수
def get_file_path(relative_path):
    current_dir = os.getcwd()
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    return os.path.join(parent_dir, relative_path)

# JSON 파일 읽기 함수
def read_json_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

# 중복 데이터 제거 및 병합 함수
def remove_duplicates(main_data, *other_data_sources):
    unique_firm_names = set(item['FIRM_NM'] for item in main_data)
    filtered_data = []

    for data in other_data_sources:
        for item in data:
            if item['FIRM_NM'] not in unique_firm_names:
                filtered_data.append(item)
                unique_firm_names.add(item['FIRM_NM'])
    
    return main_data + filtered_data

# 오늘 날짜 데이터 필터링 함수
def filter_today_data(data):
    today = datetime.now().strftime('%Y-%m-%d')
    return [item for item in data if item['SAVE_TIME'].startswith(today)]

# 키워드로 데이터 필터링 함수
def filter_by_keyword(data, keyword):
    if keyword:
        return [item for item in data if keyword in item['ARTICLE_TITLE']]
    return data

# SEND_USER로 데이터 필터링 함수
def filter_by_send_user(data, user_id):
    return [item for item in data if user_id not in item.get('SEND_USER', [])]

# SEND_USER 업데이트 함수
def update_send_user(data, user_id):
    for item in data:
        if 'SEND_USER' in item:
            if user_id not in item['SEND_USER']:
                item['SEND_USER'].append(user_id)
        else:
            item['SEND_USER'] = [user_id]
    return data

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
    conn.close()

async def main():
    # # 명령행 인자 파서 설정
    # parser = argparse.ArgumentParser(description="SQLite Database Management Script")
    # parser.add_argument('action', nargs='?', choices=['table', 'insert', 'select', 'fetch', 'keyword_select', 'daily', 'save'], help="Action to perform")
    # parser.add_argument('name', nargs='?', help="Table name for the action")
    # args = parser.parse_args()

    # 상위 폴더 기준 파일 경로 설정
    relative_path = 'telegram-stock-info-bot/report_alert_keyword.json'
    file_path = get_file_path(relative_path)
    data = read_json_file(file_path)

    # 사용자 ID를 기준으로 데이터를 순회
    for user_id, keywords in data.items():
        user_id_str = str(user_id)  # 사용자 ID를 문자열로 변환
        print(f"User ID: {user_id_str}")
        for entry in keywords:
            keyword = entry['keyword']
            print(f"알림 키워드 : {keyword}")
            r = fetch_data(keyword=keyword, user_id=user_id_str)
            print('===>',r)

            message = ''
            # # 전송할 메시지 생성 및 발송
            if r:
                message = f"=====알림 키워드 : {entry['keyword']}====="
                message += format_message_sql(r)
                print('여기==>', message)  # 메시지 발송 전에 출력 (디버깅 용도)

            # 전송할 메시지 생성 및 발송
            if message:
                # asyncio.run(sendMessage(message, user_id_str))
                await sendMarkDownText(token=token,
                chat_id=user_id_str,
                sendMessageText=message)
                update_data(keyword=keyword, user_ids= user_id_str)

if __name__ == '__main__':
    asyncio.run(main())