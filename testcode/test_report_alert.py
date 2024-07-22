import os
import sys
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
env = os.getenv('ENV')
token = os.getenv('TELEGRAM_STOCK_INFO_BOT')
application = ApplicationBuilder().token(token).build()
bot = application.bot

# 기본 날짜를 전역 변수로 설정
DEFAULT_DATE = datetime.now().strftime('%Y-%m-%d')

def get_file_path(relative_path):
    """
    현재 파일의 디렉토리를 기준으로 상대 경로를 설정합니다.
    :param relative_path: 현재 파일의 디렉토리를 기준으로 한 상대 경로
    :return: 파일의 절대 경로
    """
    project_root = get_project_root()
    file_path = os.path.join(project_root, relative_path)
    return file_path

def save_updated_data(data, filepath):
    directory = os.path.dirname(filepath)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

async def sendMessage(chat_id, sendMessageText):
    print(f"Sending message to chat_id {chat_id}: \n\n {sendMessageText}")
    return await bot.send_message(
        chat_id=chat_id,
        text=sendMessageText,
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )

def read_json_file(filepath):
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
    return [item for item in data if item['SAVE_TIME'].startswith(date)]

def filter_by_keyword(data, keyword):
    if keyword:
        return [item for item in data if keyword in item['ARTICLE_TITLE']]
    return data

def format_message(data):
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
    keyword = entry['keyword']
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
        await sendMessage(chat_id, full_message)
    else:
        for i in range(0, len(full_message), 3000):
            part = full_message[i:i + 3000]
            await sendMessage(chat_id, part)
    
    for item in filtered_data:
        if 'SEND_USER' in item:
            if chat_id not in item['SEND_USER']:
                item['SEND_USER'].append(chat_id)

async def main():
    base_path = 'json'
    main_file = os.path.join(base_path, 'data_main_daily_send.json')
    other_files = [
        os.path.join(base_path, 'hankyungconsen_research.json'),
        os.path.join(base_path, 'naver_research.json')
    ]

    main_data = read_json_file(get_file_path(main_file))
    other_data_sources = [read_json_file(get_file_path(filepath)) for filepath in other_files]

    main_data_today = filter_today_data(main_data)
    other_data_sources_today = [filter_today_data(data) for data in other_data_sources]

    global merged_data
    merged_data = remove_duplicates(main_data_today, *other_data_sources_today)

    print(f"시스템(조회) 일자: {DEFAULT_DATE}")

    relative_path = 'telegram-stock-info-bot/report_alert_keyword.json'
    file_path = get_file_path(relative_path)
    data = read_json_file(file_path)

    for user_id, keywords in data.items():
        for keyword_entry in keywords:
            await send_long_message(user_id, keyword_entry)

    updated_file_path = get_file_path('json/send_report_alert.json')
    save_updated_data(merged_data, updated_file_path)

if __name__ == "__main__":
    asyncio.run(main())
