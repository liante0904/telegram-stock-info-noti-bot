# json_util.py
import os
import json
import datetime

def save_data_to_local_json(filename, sec_firm_order, article_board_order, firm_nm, attach_url, article_title):
    directory = os.path.dirname(filename)

    # 디렉터리가 존재하는지 확인하고, 없으면 생성합니다.
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"디렉터리 '{directory}'를 생성했습니다.")

    # 현재 시간을 저장합니다.
    current_time = datetime.datetime.now().isoformat()
    
    # 새 데이터를 딕셔너리로 저장합니다.
    new_data = {
        "SEC_FIRM_ORDER": sec_firm_order,
        "ARTICLE_BOARD_ORDER": article_board_order,
        "FIRM_NM": firm_nm,
        "ATTACH_URL": attach_url,
        "ARTICLE_TITLE": article_title,
        "SAVE_TIME": current_time
    }

    # 기존 데이터를 읽어옵니다.
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as json_file:
            existing_data = json.load(json_file)
    else:
        existing_data = []

    # 중복 체크 (ATTACH_URL, FIRM_NM, ARTICLE_TITLE 중복 확인)
    is_duplicate = any(
        # existing_item["ATTACH_URL"] == new_data["ATTACH_URL"] and
        existing_item["FIRM_NM"] == new_data["FIRM_NM"] and
        existing_item["ARTICLE_TITLE"] == new_data["ARTICLE_TITLE"]
        for existing_item in existing_data
    )

    if not is_duplicate:
        existing_data.append(new_data)
        
        # 업데이트된 데이터를 JSON 파일로 저장합니다.
        with open(filename, 'w', encoding='utf-8') as json_file:
            json.dump(existing_data, json_file, ensure_ascii=False, indent=4)
        
        print(f"새 데이터가 {filename}에 성공적으로 저장되었습니다.")
        
        # 중복되지 않은 항목을 템플릿 형식으로 반환
        return format_message(new_data)
    else:
        print("중복된 데이터가 발견되어 저장하지 않았습니다.")
        return ''

def format_message(data):
    EMOJI_PICK = u'\U0001F449'  # 이모지 설정
    ARTICLE_TITLE = data['ARTICLE_TITLE']
    ARTICLE_URL = data['ATTACH_URL']
    
    sendMessageText = ""
    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")"  + "\n"
    
    return sendMessageText
