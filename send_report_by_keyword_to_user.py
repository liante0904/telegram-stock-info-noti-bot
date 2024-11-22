import os
import sys
import json
import asyncio
from datetime import datetime

# 프로젝트 내부 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utils.sqlite_util import format_message_sql
from utils.telegram_util import sendMarkDownText
from models.SecretKey import SecretKey
from package.json_to_sqlite import fetch_data, update_data

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

async def main():
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