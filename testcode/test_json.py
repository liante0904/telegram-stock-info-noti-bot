import os
import json
import datetime

def load_from_local_json():
    directory = './json'
    filename = os.path.join(directory, 'naver_research.json')

    # 파일이 존재하는지 확인합니다.
    if not os.path.exists(filename):
        print(f"파일 '{filename}'이 존재하지 않습니다.")
        return []

    # JSON 파일에서 데이터를 읽어옵니다.
    with open(filename, 'r', encoding='utf-8') as json_file:
        existing_data = json.load(json_file)
    
    return existing_data

def filter_data(data, firm_name=None, sec_firm_order=None, article_board_order=None, target_date=None):
    if target_date is None:
        target_date = datetime.datetime.now().strftime('%Y-%m-%d')

    print(f"Target date: {target_date}")
    if firm_name:
        print(f"Firm name: {firm_name}")
    if sec_firm_order:
        print(f"SEC_FIRM_ORDER: {sec_firm_order}")
    if article_board_order:
        print(f"ARTICLE_BOARD_ORDER: {article_board_order}")
    
    filtered_data = []
    for item in data:
        save_time = item.get("SAVE_TIME", "")
        item_firm_name = item.get("FIRM_NM", "")
        item_sec_firm_order = item.get("SEC_FIRM_ORDER", None)
        item_article_board_order = item.get("ARTICLE_BOARD_ORDER", None)
        save_date = save_time.split('T')[0]  # SAVE_TIME에서 날짜 부분만 추출

        # 필터 조건을 모두 만족하는지 확인
        if (save_date == target_date and
            (firm_name is None or item_firm_name == firm_name) and
            (sec_firm_order is None or item_sec_firm_order == sec_firm_order) and
            (article_board_order is None or item_article_board_order == article_board_order)):
            filtered_data.append(item)
    
    return filtered_data

# 예시 호출
all_data = load_from_local_json()
print("All data:")
print(all_data)

# 필터 조건 설정
firm_name = 'IBK투자증권'
sec_firm_order = ''
article_board_order = ''
target_date = '2024-07-13'

# 특정 조건에 맞는 데이터를 필터링
filtered_data = filter_data(all_data, firm_name=firm_name, sec_firm_order=sec_firm_order, article_board_order=article_board_order, target_date=target_date)
print(f"\nFiltered data by target date {target_date}, FIRM_NM == '{firm_name}', SEC_FIRM_ORDER == {sec_firm_order}, and ARTICLE_BOARD_ORDER == {article_board_order}:")
print(filtered_data)

# 현재 일자와 특정 FIRM_NM에 맞는 데이터를 필터링
filtered_data_today = filter_data(all_data, firm_name=firm_name)
print(f"\nFiltered data by current date and FIRM_NM == '{firm_name}':")
print(filtered_data_today)
