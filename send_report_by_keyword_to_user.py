import os
import sys
import json
import telegram
import asyncio
from datetime import datetime

# 프로젝트 내부 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from package.json_util import format_message, format_message_sql
from package.SecretKey import SecretKey
from package.json_to_sqlite import fetch_data, update_data, insert_data

# 비밀키 불러오기
SECRET_KEY = SecretKey()
SECRET_KEY.load_secrets()

# 텔레그램 메시지 발송 함수
async def sendMessage(sendMessageText, chat_id=None):
    if chat_id is None:
        return 

    bot = telegram.Bot(token=SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id=chat_id, text=sendMessageText, disable_web_page_preview=True, parse_mode="Markdown")

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

# # 경로 설정
# base_path = './json'
# main_file = os.path.join(base_path, 'data_main_daily_send.json')
# other_files = [
#     os.path.join(base_path, 'hankyungconsen_research.json'),
#     os.path.join(base_path, 'naver_research.json')
# ]

# # JSON 데이터 읽기
# main_data = read_json_file(main_file)
# other_data_sources = [read_json_file(filepath) for filepath in other_files]

# # 오늘 날짜의 데이터만 필터링
# main_data_today = filter_today_data(main_data)
# other_data_sources_today = [filter_today_data(data) for data in other_data_sources]

# # 중복 데이터 제거 및 병합
# merged_data = remove_duplicates(main_data_today, *other_data_sources_today)

insert_data()

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
            message = f"=====알림 키워드 : {entry['keyword']}=====\n"
            message += format_message_sql(r)
            print('여기==>', message)  # 메시지 발송 전에 출력 (디버깅 용도)

        # 전송할 메시지 생성 및 발송
        if message:
            asyncio.run(sendMessage(message, user_id_str))
            update_data(keyword=keyword, user_ids= user_id_str)

        # # 키워드로 필터링
        # keyword_filtered_data = filter_by_keyword(merged_data, keyword)

        # # 필터링 결과 출력(SEND_USER 필터 전)
        # print('======필터링 결과 출력(SEND_USER 필터 전)======')
        # print(keyword_filtered_data)

        # # SEND_USER로 필터링
        # send_user_filtered_data = filter_by_send_user(keyword_filtered_data, user_id_str)

        # # 필터링 결과 출력(SEND_USER 필터 후)
        # print('======필터링 결과 출력(SEND_USER 필터 후)======')
        # print(send_user_filtered_data)

        # # 전송할 메시지 생성 및 발송
        # if send_user_filtered_data:
        #     message = f"=====알림 키워드 : {entry['keyword']}=====\n\n"
        #     message += format_message(send_user_filtered_data)
        #     print('여기==>', message)  # 메시지 발송 전에 출력 (디버깅 용도)
        #     asyncio.run(sendMessage(message, user_id_str))
            
        #     # 발송된 항목에 대해서만 SEND_USER 업데이트
        #     for item in send_user_filtered_data:
        #         merged_data = update_send_user(merged_data, user_id_str)

        #     # 기존 main_data를 유지하면서 merged_data에서 SEND_USER 정보만 업데이트
        #     for item in main_data:
        #         for updated_item in merged_data:
        #             if item['FIRM_NM'] == updated_item['FIRM_NM']:
        #                 if 'SEND_USER' in updated_item:
        #                     item['SEND_USER'] = updated_item['SEND_USER']

# # 수정된 데이터를 저장
# with open(main_file, 'w', encoding='utf-8') as file:
#     json.dump(main_data, file, ensure_ascii=False, indent=4)