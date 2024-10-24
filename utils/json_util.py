import os
import json
from datetime import datetime, timedelta
import argparse

# 전역 변수로 필터링할 증권사 목록 정의
EXCLUDED_FORWARD_REPORT_FIRMS = {"하나증권", "신한투자증권", "이베스트증권","이베스트투자증권"}

def save_data_to_local_json(filename, sec_firm_order, article_board_order, firm_nm, attach_url, article_title, article_url=None, download_url=None, send_users=None, main_ch_send_yn="N"):
    directory = os.path.dirname(filename)

    # 디렉터리가 존재하는지 확인하고, 없으면 생성합니다.
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"\n디렉터리 '{directory}'를 생성했습니다.")

    # 현재 시간을 저장합니다.
    current_time = datetime.now().isoformat()
    
    # `send_users`가 None이면 빈 배열로 초기화합니다.
    if send_users is None:
        send_users = []
    # `article_url`가 None이면 attach_url로 대체합니다. (임시 추후변경)
    if article_url is None:
        article_url = attach_url
    if download_url is None:
        download_url = attach_url
        
    # 새 데이터를 딕셔너리로 저장합니다.
    new_data = {
        "SEC_FIRM_ORDER": sec_firm_order,
        "ARTICLE_BOARD_ORDER": article_board_order,
        "FIRM_NM": firm_nm,
        "ATTACH_URL": attach_url,
        "ARTICLE_TITLE": article_title,
        "ARTICLE_URL": article_url,
        "SEND_USER": send_users,
        "MAIN_CH_SEND_YN": main_ch_send_yn,
        "DOWNLOAD_URL":download_url,
        "SAVE_TIME": current_time
    }


    # 기존 데이터를 읽어옵니다.
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
    else:
        existing_data = []

    # 중복 체크 (FIRM_NM, ARTICLE_TITLE 중복 확인)
    is_duplicate = any(
        existing_item["FIRM_NM"] == new_data["FIRM_NM"] and
        existing_item["ARTICLE_TITLE"] == new_data["ARTICLE_TITLE"]
        for existing_item in existing_data
    )

    if not is_duplicate:
        existing_data.append(new_data)
        
        # 업데이트된 데이터를 JSON 파일로 저장합니다.
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(existing_data, json_file, ensure_ascii=False, indent=4)
        
        print(f"\n새 데이터가 {filename}에 성공적으로 저장되었습니다.")
        
        # 중복되지 않은 항목을 템플릿 형식으로 반환
        if '네이버'in firm_nm or '조선비즈' in firm_nm:
            return format_message(new_data) + '\n'
        else:
            return format_message(new_data)
    else:
        print("중복된 데이터가 발견되어 저장하지 않았습니다.")
        return ''

async def save_multiple_data_to_local_json(filename, news_data_list):
    directory = os.path.dirname(filename)

    # 디렉터리가 존재하는지 확인하고, 없으면 생성합니다.
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"\n디렉터리 '{directory}'를 생성했습니다.")

    # 기존 데이터를 읽어옵니다.
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
    else:
        existing_data = []

    # 중복 체크 및 데이터 추가
    for new_data in news_data_list:
        # 기존 데이터에서 중복 여부를 확인
        is_duplicate = any(
            existing_item.get("FIRM_NM") == new_data.get("firm_nm") and
            existing_item.get("ARTICLE_TITLE") == new_data.get("article_title")
            for existing_item in existing_data
        )

        if not is_duplicate:
            existing_data.append({
                "SEC_FIRM_ORDER": new_data.get("sec_firm_order"),
                "ARTICLE_BOARD_ORDER": new_data.get("article_board_order"),
                "FIRM_NM": new_data.get("firm_nm"),
                "ATTACH_URL": new_data.get("attach_url"),
                "ARTICLE_TITLE": new_data.get("article_title"),
                "SEND_USER": [],
                "MAIN_CH_SEND_YN": "N",
                "DOWNLOAD_URL": new_data.get("attach_url"),
                "SAVE_TIME": datetime.now().isoformat()
            })

    # 업데이트된 데이터를 JSON 파일로 저장합니다.
    with open(filename, 'w', encoding='utf-8') as json_file:
        json.dump(existing_data, json_file, ensure_ascii=False, indent=4)

    print(f"\n새 데이터가 {filename}에 성공적으로 저장되었습니다.")
    
    # existing_data가 비어 있지 않은 경우에만 마지막 데이터의 메시지를 생성합니다.
    if existing_data:
        return format_message(existing_data[-1]) + '\n'
    else:
        return ''

def format_message(data_list):
    EMOJI_PICK = u'\U0001F449'  # 이모지 설정
    formatted_messages = []

    # data_list가 단일 데이터 항목일 경우, 리스트로 감싸줍니다.
    if isinstance(data_list, dict):
        data_list = [data_list]

    last_firm_nm = None  # 마지막으로 출력된 FIRM_NM을 저장하는 변수

    for data in data_list:
        ARTICLE_TITLE = data.get('ARTICLE_TITLE','')
        ARTICLE_URL = data.get('ATTACH_URL','')
        
        sendMessageText = ""
        
        # 'FIRM_NM'이 존재하는 경우에만 포함
        if 'FIRM_NM' in data:
            FIRM_NM = data['FIRM_NM']
            # data_list가 단건인 경우, 회사명 출력을 생략
            if len(data_list) > 1:
                # 제외할 FIRM_NM이 아닌 경우에만 처리
                if '네이버' not in FIRM_NM or '조선비즈' not in FIRM_NM:
                    # 새로운 FIRM_NM이거나 첫 번째 데이터일 때만 FIRM_NM을 포함
                    if FIRM_NM != last_firm_nm:
                        sendMessageText += "\n\n" + "●" + FIRM_NM + "\n"
                        last_firm_nm = FIRM_NM
        

    # 게시글 제목이 유효한 값인지 확인
    if ARTICLE_TITLE:
        sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    else:
        sendMessageText += ""  # 제목이 없을 경우의 처리

    # 원문 링크가 유효한 값인지 확인
    if ARTICLE_URL:
        sendMessageText += EMOJI_PICK + "[링크]" + "(" + ARTICLE_URL + ")" + "\n"
    else:
        sendMessageText += ""  # 링크가 없을 경우의 처리

    formatted_messages.append(sendMessageText)
    # 모든 메시지를 하나의 문자열로 결합합니다.
    return "\n".join(formatted_messages)

def update_json_with_main_ch_send_yn(file_path):
    directory = os.path.dirname(file_path)

    # 디렉터리가 존재하는지 확인하고, 없으면 생성합니다.
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"\n디렉터리 '{directory}'를 생성했습니다.")
    
    if not os.path.exists(file_path):
        print(f"\n파일 경로 '{file_path}'가 존재하지 않습니다.")
        return

    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # 각 항목에 MAIN_CH_SEND_YN 키를 추가합니다.
    for item in data:
        item["MAIN_CH_SEND_YN"] = "N"
        
        # SAVE_TIME을 마지막에 유지하기 위해 삭제 후 다시 추가
        save_time = item.pop("SAVE_TIME", None)
        if save_time:
            item["SAVE_TIME"] = save_time

    # 업데이트된 데이터를 다시 JSON 파일로 저장합니다.
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    
    print(f"\n{file_path} 파일에 MAIN_CH_SEND_YN 키가 업데이트되었습니다.")

def get_unsent_main_ch_data_to_local_json(filename):
    directory = os.path.dirname(filename)
    
    # 디렉터리가 존재하는지 확인하고, 없으면 생성합니다.
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        print(f"\n디렉터리 '{directory}'를 생성했습니다.")
    
    # 현재 날짜를 가져옵니다.
    today_str = datetime.now().strftime("%Y-%m-%d")

    # json 파일을 읽어옵니다.
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        with open(filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
    else:
        print(f"\n파일 경로 '{filename}'가 존재하지 않습니다.")
        return ''

    # 중복 확인을 위해 json/data_main_daily_send.json의 FIRM_NM 목록을 가져옵니다.
    main_daily_send_path = 'json/data_main_daily_send.json'
    if os.path.exists(main_daily_send_path) and os.path.getsize(main_daily_send_path) > 0:
        with open(main_daily_send_path, 'r', encoding='utf-8') as json_file:
            main_daily_data = json.load(json_file)
            sent_firms = {item["FIRM_NM"] for item in main_daily_data}
            print(f"\n중복 확인을 위해 로드된 FIRM_NM 목록: {sent_firms}")  # 디버깅 로그 추가
    else:
        sent_firms = set()

    # EXCLUDED_FORWARD_REPORT_FIRMS를 sent_firms에 합치기
    sent_firms.update(EXCLUDED_FORWARD_REPORT_FIRMS)
    print(f"\n수기 EXCLUDED_FORWARD_REPORT_FIRMS 추가 목록(제외할 증권사 포함): {sent_firms}")  # 디버깅 로그 추가

    additional_firms = set()

    # 추가된 목록을 sent_firms에 합치기
    sent_firms.update(additional_firms)
    print(f"\n최종 FIRM_NM 목록: {sent_firms}")  # 디버깅 로그 추가

    # 조건에 맞는 데이터를 필터링합니다.
    unsent_data = [
        item for item in data
        if item["SAVE_TIME"].startswith(today_str) and item["MAIN_CH_SEND_YN"] == "N" and item["FIRM_NM"] not in sent_firms
    ]

    # 디버깅 로그 추가
    print(f"\n필터링된 unsent_data: {unsent_data}")

    messages = []
    current_message = ""
    previous_firm_nm = None
    first_record = True  # 첫 번째 레코드인지 여부를 추적

    for item in unsent_data:
        firm_nm = item['FIRM_NM']
        message_part = format_message(item)

        # 첫 번째 레코드 처리
        if first_record:
            current_message += f"●{firm_nm}\n"
            first_record = False
            previous_firm_nm = firm_nm
        elif firm_nm != previous_firm_nm:
            if previous_firm_nm is not None:
                current_message += "\n"
            current_message += f"\n●{firm_nm}\n"
            previous_firm_nm = firm_nm

        # 메시지의 길이가 3000자를 넘으면 분리
        if len(current_message) + len(message_part) > 3000:
            messages.append(current_message)
            current_message = message_part
        else:
            current_message += message_part

    if current_message:
        messages.append(current_message)

    return messages

def update_main_ch_send_yn_to_y(file_path, target_date=None):
    directory = os.path.dirname(file_path)

    # 디렉터리가 존재하는지 확인하고, 없으면 생성합니다.
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"\n디렉터리 '{directory}'를 생성했습니다.")
    
    if not os.path.exists(file_path):
        print(f"\n파일 경로 '{file_path}'가 존재하지 않습니다.")
        return

    # 대상 날짜를 설정합니다. 날짜를 받지 않은 경우 오늘 날짜로 설정합니다.
    if target_date is None:
        target_date = datetime.now().strftime("%Y-%m-%d")

    with open(file_path, 'r', encoding='utf-8') as json_file:
        data = json.load(json_file)

    # 대상 날짜의 항목들에 대해 MAIN_CH_SEND_YN 값을 Y로 설정합니다.
    for item in data:
        if item["SAVE_TIME"].startswith(target_date):
            item["MAIN_CH_SEND_YN"] = "Y"

    # 업데이트된 데이터를 다시 JSON 파일로 저장합니다.
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    
    print(f"\n{file_path} 파일의 {target_date} 날짜 항목에 대해 MAIN_CH_SEND_YN 키가 Y로 업데이트되었습니다.")


def filter_news_by_save_time(filename):
    # 파일에서 JSON 데이터 읽기
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 오늘 날짜
    today = datetime.now()

    # 1주일 이내 날짜 계산
    one_week_ago = today - timedelta(days=1)

    # 뉴스 리스트 필터링
    filtered_news_list = [
        news for news in data
        if datetime.fromisoformat(news['SAVE_TIME']) >= one_week_ago
    ]

    # 필터링된 데이터를 다시 JSON 파일로 저장
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(filtered_news_list, f, ensure_ascii=False, indent=4)


def filter_data_by_save_time(filename):
    # 파일에서 JSON 데이터 읽기
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 오늘 날짜
    today = datetime.now()

    # 1달 이내 날짜 계산
    one_week_ago = today - timedelta(days=30)

    # 뉴스 리스트 필터링
    filtered_news_list = [
        news for news in data
        if datetime.fromisoformat(news['SAVE_TIME']) >= one_week_ago
    ]

    # 필터링된 데이터를 다시 JSON 파일로 저장
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(filtered_news_list, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process JSON files with specified action.')
    parser.add_argument('action', choices=['update', 'send'], help='Action to perform: update or send')
    parser.add_argument('file_path', type=str, help='Path to the JSON file to process')

    args = parser.parse_args()

    if args.action == 'update':
        update_json_with_main_ch_send_yn(args.file_path)
    elif args.action == 'send':
        results = get_unsent_main_ch_data_to_local_json(args.file_path)
        for result in results:
            print(result)
            print("\n" + "="*50 + "\n")  # 구분선 추가
