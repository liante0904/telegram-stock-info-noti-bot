import os
import sys
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import ApplicationBuilder

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from package.json_util import format_message  # import the function from json_utiltest

# 환경 변수 로드
load_dotenv()  # .env 파일의 환경 변수를 로드합니다
env = os.getenv('ENV')
print(env)
if env == 'production':
    token = os.getenv('TELEGRAM_STOCK_INFO_BOT')
else:
    token = os.getenv('TELEGRAM_STOCK_INFO_BOT')
print(token)

application = ApplicationBuilder().token(token).build()
bot = application.bot

# 기본 날짜를 전역 변수로 설정
DEFAULT_DATE = '2024-07-21'#datetime.now().strftime('%Y-%m-%d')

async def sendMessage(chat_id, sendMessageText):
    print(f"Sending message to chat_id {chat_id}: \n\n {sendMessageText}")
    print('=' * 80)
    return await bot.send_message(
        chat_id=chat_id,
        text=sendMessageText,
        disable_web_page_preview = True,
        parse_mode="Markdown"
    )

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

def filter_today_data(data, date=DEFAULT_DATE):
    """
    주어진 날짜에 해당하는 데이터만 필터링합니다.
    :param data: 필터링할 데이터 리스트
    :param date: 필터링할 날짜 (형식: 'YYYY-MM-DD'). 기본값은 현재 날짜
    :return: 필터링된 데이터 리스트
    """
    return [item for item in data if item['SAVE_TIME'].startswith(date)]

def filter_by_keyword(data, keyword):
    if keyword:
        return [item for item in data if keyword in item['ARTICLE_TITLE']]
    return data

async def send_long_message(chat_id, entry):
    message = format_message(filter_by_keyword(merged_data, entry['keyword']))
    keyword_line = f"*===========알림 키워드 : [{entry['keyword']}]===========*\n\n"
    
    if len(message) > 3000:
        # 메시지를 3000자씩 나누어 보냄
        for i in range(0, len(message), 3000):
            part = message[i:i + 3000]
            await sendMessage(chat_id, keyword_line + part)
    else:
        # 메시지가 3000자 이하면 한 번에 전송
        await sendMessage(chat_id, keyword_line + message)

async def main():
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
    global merged_data
    merged_data = remove_duplicates(main_data_today, *other_data_sources_today)

    # 시스템 일자 출력
    print(f"시스템(조회) 일자: {DEFAULT_DATE}")

    # 상위 폴더 기준 파일 경로 설정
    relative_path = 'telegram-stock-info-bot/report_alert_keyword.json'
    file_path = get_file_path(relative_path)
    data = read_json_file(file_path)

    # 사용자 ID를 기준으로 데이터를 순회
    for user_id, keywords in data.items():
        print(f"User ID: {user_id}")
        for keyword in keywords:
            # print(f"알림 키워드 : {keyword}")
            await send_long_message(user_id, keyword)

if __name__ == "__main__":
    asyncio.run(main())
