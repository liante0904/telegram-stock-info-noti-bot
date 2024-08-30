import os
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import ApplicationBuilder

# 현재 파일의 디렉토리를 기준으로 절대 경로를 설정합니다.
def get_project_root():
    return os.path.dirname(os.path.abspath(__file__))

# 환경 변수 로드
load_dotenv()
token = os.getenv('TELEGRAM_STOCK_INFO_BOT')
application = ApplicationBuilder().token(token).build()
bot = application.bot

# 기본 날짜를 전역 변수로 설정
DEFAULT_DATE = datetime.now().strftime('%Y-%m-%d')

def get_file_path(relative_path):
    """
    현재 파일의 디렉토리를 기준으로 상대 경로를 절대 경로로 변환합니다.
    :param relative_path: 현재 파일의 디렉토리를 기준으로 한 상대 경로
    :return: 파일의 절대 경로
    """
    project_root = get_project_root()
    file_path = os.path.join(project_root, relative_path)
    print(f"Resolved file path: {file_path}")  # Debug print to verify the path
    return file_path

def save_updated_data(data, filepath):
    """
    업데이트된 데이터를 JSON 파일로 저장합니다.
    :param data: 저장할 데이터
    :param filepath: 저장할 파일의 경로
    """
    directory = os.path.dirname(filepath)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

async def send_message(chat_id, send_message_text):
    """
    지정된 채팅 ID로 메시지를 전송합니다.
    :param chat_id: 메시지를 받을 채팅 ID
    :param send_message_text: 전송할 메시지
    :return: Telegram 메시지 전송 결과
    """
    print(f"Sending message to chat_id {chat_id}: \n\n {send_message_text}")
    return await bot.send_message(
        chat_id=chat_id,
        text=send_message_text,
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )

def read_json_file(filepath):
    """
    JSON 파일을 읽어들입니다.
    :param filepath: 읽어들일 파일의 경로
    :return: JSON 데이터
    """
    if not os.path.exists(filepath):
        print(f"경고: 파일이 존재하지 않습니다 - {filepath}")
        return []
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def remove_duplicates(main_data, *other_data_sources):
    """
    중복된 항목을 제거합니다.
    :param main_data: 메인 데이터
    :param other_data_sources: 다른 데이터 소스
    :return: 중복이 제거된 데이터
    """
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
    지정된 날짜의 데이터를 필터링합니다.
    :param data: 필터링할 데이터
    :param date: 필터링할 날짜
    :return: 지정된 날짜의 데이터
    """
    return [item for item in data if item['SAVE_TIME'].startswith(date)]

def filter_by_keyword(data, keyword):
    """
    데이터에서 지정된 키워드를 포함한 항목만 필터링합니다.
    :param data: 필터링할 데이터
    :param keyword: 필터링할 키워드
    :return: 키워드가 포함된 데이터
    """
    if keyword:
        return [item for item in data if keyword in item['ARTICLE_TITLE']]
    return data

def format_message(data):
    """
    데이터를 메시지 형식으로 변환합니다.
    :param data: 형식화할 데이터
    :return: 형식화된 메시지
    """
    if not data:
        return ""

    firm_messages = []
    current_firm = None
    current_message = ""

    for item in data:
        firm_nm = item["FIRM_NM"]
        article_title = item["ARTICLE_TITLE"]
        attach_url = item["ATTACH_URL"]

        if firm_nm != current_firm:
            if current_message:
                firm_messages.append(current_message)
            current_message = f"*●{firm_nm}*\n"
            current_firm = firm_nm

        current_message += f"{article_title}\n👉[링크]({attach_url})\n\n"

    if current_message:
        firm_messages.append(current_message)

    return "\n".join(firm_messages)

async def send_long_message(chat_id, entry):
    """
    긴 메시지를 여러 부분으로 나누어 전송합니다.
    :param chat_id: 메시지를 받을 채팅 ID
    :param entry: 메시지 항목
    """
    keyword = entry.get('keyword', '')
    filtered_data = filter_by_keyword(merged_data, keyword)
    message = format_message(filtered_data)
    full_message = ''

    if not message.strip():
        no_message = f"===========알림 키워드 : * [{keyword}] *===========\n\n해당 키워드의 레포트는 없습니다."
        full_message += no_message
    else:
        keyword_line = f"===========알림 키워드 : * [{keyword}] *===========\n\n"
        full_message += keyword_line + message

    if len(full_message) <= 3000:
        await send_message(chat_id, full_message)
    else:
        for i in range(0, len(full_message), 3000):
            part = full_message[i:i + 3000]
            await send_message(chat_id, part)
    
    for item in filtered_data:
        if 'SEND_USER' in item:
            if chat_id not in item['SEND_USER']:
                item['SEND_USER'].append(chat_id)

async def main():
    """
    메인 함수: 데이터를 읽고 필터링하며 메시지를 전송합니다.
    """
    base_path = 'json'
    main_file = os.path.join(base_path, 'data_main_daily_send.json')
    other_files = [
        os.path.join(base_path, 'hankyungconsen_research.json'),
        os.path.join(base_path, 'naver_research.json')
    ]

    # 파일 경로를 절대 경로로 변환
    main_file_path = get_file_path(main_file)
    other_file_paths = [get_file_path(filepath) for filepath in other_files]

    # JSON 파일 읽기
    main_data = read_json_file(main_file_path)
    other_data_sources = [read_json_file(filepath) for filepath in other_file_paths]

    # 데이터 필터링
    main_data_today = filter_today_data(main_data)
    other_data_sources_today = [filter_today_data(data) for data in other_data_sources]

    global merged_data
    merged_data = remove_duplicates(main_data_today, *other_data_sources_today)

    print(f"시스템(조회) 일자: {DEFAULT_DATE}")

    # 알림 키워드 JSON 파일 경로
    relative_path = os.path.join(os.path.dirname(get_project_root()), 'telegram-ebestnotibot/json')
    relative_path = os.path.join(relative_path, 'data_main_daily_send.json')
    file_path = get_file_path(relative_path)
    data = read_json_file(file_path)

    # 로그 추가: data 구조 확인
    print('Data structure:', type(data))
    if not isinstance(data, list):
        print('Error: Expected data to be a list.')
        return

    # 메시지 전송
    for keyword_entry in data:
        if not isinstance(keyword_entry, dict):
            print(f"Error: Keyword entry is not a dict: {keyword_entry}")
            continue

        user_id = keyword_entry.get('user_id', 'default_user_id')
        await send_long_message(user_id, keyword_entry)

    # 업데이트된 데이터 저장
    updated_file_path = get_file_path('json/send_report_alert.json')
    save_updated_data(merged_data, updated_file_path)

if __name__ == "__main__":
    asyncio.run(main())
