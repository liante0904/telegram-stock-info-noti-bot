import os
import sys
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from package.json_util import format_messages_batch # import the function from json_utiltest
 

def get_file_path(relative_path):
    """
    현재 작업 디렉토리를 기준으로 상위 폴더에서 파일 경로를 설정합니다.
    :param relative_path: 상위 폴더를 기준으로 한 상대 경로
    :return: 파일의 절대 경로
    """
    # 현재 작업 디렉토리 확인
    current_dir = os.getcwd()
    print(f"Current working directory: {current_dir}")
    
    # 현재 작업 디렉토리의 상위 폴더로 이동
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))
    print(f"Parent directory: {parent_dir}")
    
    # 상위 폴더를 기준으로 한 파일 경로
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
# print(merged_data)
# 키워드 필터링 (키워드를 넣지 않으면 전체 조회)
keyword = "SK"  # 예시로 빈 문자열을 사용. 키워드를 넣고 싶다면 여기서 지정
filtered_data = filter_by_keyword(merged_data, keyword)

# 시스템 일자 출력
system_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
print(f"시스템(조회) 일자: {system_date}")
print(f"검색 키워드: {keyword}")

# print(filtered_data)

# 상위 폴더 기준 파일 경로 설정
relative_path = 'telegram-stock-info-bot/report_alert_keyword.json'
file_path = get_file_path(relative_path)
data  = read_json_file(file_path)
# 사용자 ID를 기준으로 데이터를 순회
for user_id, keywords in data.items():
    print(f"User ID: {user_id}")
    for entry in keywords:
        print(f"알림 키워드 : {entry['keyword']}")
        print(filter_by_keyword(merged_data, entry['keyword']))
        print()
# print(format_messages_batch(keyword[keyword]))
# 결과 출력 (필요시)
# for item in filtered_data:
    # print(item)
