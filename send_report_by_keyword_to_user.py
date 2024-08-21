import os
import sys
import json
import telegram
import asyncio
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from package.json_util import format_message # import the function from json_util
from package.SecretKey import SecretKey

SECRET_KEY = SecretKey()
SECRET_KEY.load_secrets()

async def sendMessage(sendMessageText, chat_id=None): #실행시킬 함수명 임의지정
    # chat_id가 제공되지 않으면 기본값 사용
    if chat_id is None:
        return 

    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = chat_id, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")


def get_file_path(relative_path):
    """
    현재 작업 디렉토리를 기준으로 상위 폴더에서 파일 경로를 설정합니다.
    :param relative_path: 상위 폴더를 기준으로 한 상대 경로
    :return: 파일의 절대 경로
    """
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    print(f"Parent directory: {parent_dir}")
    file_path = os.path.join(parent_dir, relative_path)
    return file_path

def read_json_file(filepath):
    print(filepath)
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def remove_duplicates(main_data, *other_data_sources):
    unique_firm_names = set(item['FIRM_NM'] for item in main_data)
    filtered_data = []

    for data in other_data_sources:
        for item in data:
            if item['FIRM_NM'] not in unique_firm_names:
                filtered_data.append(item)
                unique_firm_names.add(item['FIRM_NM'])
    
    return main_data + filtered_data

def filter_today_data(data):
    today = datetime.now().strftime('%Y-%m-%d')
    return [item for item in data if item['SAVE_TIME'].startswith(today)]

def filter_by_keyword(data, keyword):
    if keyword:
        return [item for item in data if keyword in item['ARTICLE_TITLE']]
    return data

def filter_by_send_user(data, user_id):
    return [item for item in data if user_id not in item.get('SEND_USER', [])]

def update_send_user(data, user_id):
    for item in data:
        if 'SEND_USER' in item:
            if user_id not in item['SEND_USER']:
                item['SEND_USER'].append(user_id)
        else:
            item['SEND_USER'] = [user_id]
    return data

# 경로 설정
base_path = './json'
main_file = os.path.join(base_path, 'data_main_daily_send.json')
other_files = [
    os.path.join(base_path, 'hankyungconsen_research.json'),
    os.path.join(base_path, 'naver_research.json')
]

# JSON 데이터 읽기
main_data = read_json_file(main_file)
other_data_sources = [read_json_file(filepath) for filepath in other_files]

# 오늘 날짜의 데이터만 필터링
main_data_today = filter_today_data(main_data)
other_data_sources_today = [filter_today_data(data) for data in other_data_sources]

# 중복 데이터 제거 및 병합
merged_data = remove_duplicates(main_data_today, *other_data_sources_today)

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

        # 키워드로 필터링
        keyword_filtered_data = filter_by_keyword(merged_data, keyword)

        # 필터링 결과 출력(SEND_USER 필터 전)
        print('======필터링 결과 출력(SEND_USER 필터 전)======')
        print(keyword_filtered_data)

        # SEND_USER로 필터링
        send_user_filtered_data = filter_by_send_user(keyword_filtered_data, user_id_str)

        # 필터링 결과 출력(SEND_USER 필터 후)
        print('======필터링 결과 출력(SEND_USER 필터 후)======')
        print(send_user_filtered_data)

        message = f"=====알림 키워드 : {entry['keyword']}=====\n\n"
        if send_user_filtered_data:
            message += format_message(send_user_filtered_data)
            print('여기==>',message)  # 메시지 발송 전에 출력 (디버깅 용도)
            # 발송 코드 여기에 추가 (예: send_message(user_id_str, message))
            asyncio.run(sendMessage(message, user_id_str))
            # SEND_USER에 user_id 추가
            merged_data = update_send_user(merged_data, user_id_str)

# 수정된 데이터를 저장 (필요시)
with open(main_file, 'w', encoding='utf-8') as file:
    json.dump(merged_data, file, ensure_ascii=False, indent=4)
