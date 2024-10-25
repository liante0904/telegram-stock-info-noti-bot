async def convert_sql_to_telegram_messages(fetched_rows):
    """
    Converts fetched SQL rows into formatted Telegram messages.
    
    This function processes a list of rows fetched from an SQL database and
    formats them into Telegram message chunks. The function ensures that each
    message chunk does not exceed the Telegram message limit of 3500 characters.
    
    The function also skips messages from specific firms and ensures the same firm
    name is not repeated consecutively.

    Args:
        fetched_rows (list of dict): A list where each element is a dictionary containing 
                                     the following keys:
                                     - 'id' (int): The ID of the row.
                                     - 'FIRM_NM' (str): The name of the firm.
                                     - 'ARTICLE_TITLE' (str): The title of the article.
                                     - 'ARTICLE_URL' (str): The URL of the article.
                                     - 'SAVE_TIME' (str): The save timestamp.
                                     - 'SEND_USER' (str): The user who sent the message.

    Returns:
        list of str: A list of formatted Telegram messages, where each message chunk 
                     is under the 3500 character limit.
    
    Notes:
        - Excludes rows from firms listed in `EXCLUDED_FIRMS` (e.g., "네이버", "조선비즈").
        - Adds a bullet point "●" and the firm name when switching to a new firm.
        - Ensures article titles are bold, and URLs are clickable using Markdown formatting.
    
    Example:
        fetched_rows = [
            {"id": 1, "FIRM_NM": "삼성전자", "ARTICLE_TITLE": "삼성 신제품 발표", 
             "ARTICLE_URL": "https://example.com/article/1", "SAVE_TIME": "2024-09-27", 
             "SEND_USER": "user1"},
            {"id": 2, "FIRM_NM": "LG전자", "ARTICLE_TITLE": "LG OLED TV", 
             "ARTICLE_URL": "https://example.com/article/2", "SAVE_TIME": "2024-09-27", 
             "SEND_USER": "user2"}
        ]
        
        formatted_messages = convert_sql_to_telegram_messages(fetched_rows)
        # formatted_messages will be a list of formatted strings ready for Telegram
    """

    # 'type' 파라미터가 필수임을 확인
    if not fetched_rows :
        raise ValueError("Invalid fetched_rows.")
    
    EMOJI_PICK = u'\U0001F449'  # 이모지 설정
    formatted_messages = []
    message_chunk = ""  # 현재 메시지 조각
    message_limit = 3500  # 텔레그램 메시지 제한

    # 특정 FIRM_NM을 제외할 리스트
    EXCLUDED_FIRMS = {"네이버", "조선비즈"}
    last_firm_nm = None  # 마지막으로 출력된 FIRM_NM을 저장하는 변수

    for row in fetched_rows:
        # 첫 번째 요소인 id는 무시하고, 나머지를 FIRM_NM, ARTICLE_TITLE, ARTICLE_URL, SAVE_TIME, SEND_USER로 할당
        # id, fetched_row['FIRM_NM'], fetched_row['ARTICLE_TITLE'], fetched_row['ARTICLE_URL'], SAVE_TIME, SEND_USER = fetched_row

        sendMessageText = ""

        # 'FIRM_NM'이 존재하는 경우에만 포함
        if row['FIRM_NM']:
            if row['FIRM_NM'] not in EXCLUDED_FIRMS:
                if row['FIRM_NM'] != last_firm_nm:
                    # 메시지가 3500자를 넘으면 추가된 메시지들을 배열에 저장하고 새로 시작
                    if len(message_chunk) + len(sendMessageText) > message_limit:
                        formatted_messages.append(message_chunk.strip())
                        message_chunk = ""  # 새로 시작

                    # 새 메시지 조각의 첫 줄에 FIRM_NM 추가
                    message_chunk += "\n\n" + "●" + row['FIRM_NM'] + "\n"
                    last_firm_nm = row['FIRM_NM']

        # 게시글 제목(굵게)
        sendMessageText += "*" + row['ARTICLE_TITLE'].replace("_", " ").replace("*", "") + "*" + "\n"

        # URL 우선순위 설정
        if row.get('ATTACH_URL'):
            link_url = row['ATTACH_URL']
        elif row.get('DOWNLOAD_URL'):
            link_url = row['DOWNLOAD_URL']
        elif row.get('ARTICLE_URL'):
            link_url = row['ARTICLE_URL']
        else:
            link_url = "링크없음"

        # 원문 링크 추가
        if link_url == "링크없음":
            sendMessageText += "링크없음\n"
        else:
            sendMessageText += EMOJI_PICK + "[링크]" + "(" + link_url + ")" + "\n"

        # 메시지가 3500자를 넘지 않도록 쌓음
        if len(message_chunk) + len(sendMessageText) > message_limit:
            # 이전 chunk를 저장하고 새로운 chunk 시작
            formatted_messages.append(message_chunk.strip())
            # 새 메시지 조각의 첫 줄에 FIRM_NM 추가
            message_chunk = "\n\n" + "●" + row['FIRM_NM'] + "\n" + sendMessageText
        else:
            message_chunk += sendMessageText

    # 마지막 남은 메시지도 저장
    if message_chunk:
        formatted_messages.append(message_chunk.strip())

    return formatted_messages

def format_message_sql(data_list): 
    EMOJI_PICK = u'\U0001F449'  # 이모지 설정
    formatted_messages = []

    # 특정 FIRM_NM을 제외할 리스트
    EXCLUDED_FIRMS = {"네이버", "조선비즈"}

    last_firm_nm = None  # 마지막으로 출력된 FIRM_NM을 저장하는 변수

    for data in data_list:
        FIRM_NM, ARTICLE_TITLE, ARTICLE_URL, SAVE_TIME, SEND_USER = data

        sendMessageText = ""
        
        # 'FIRM_NM'이 존재하는 경우에만 포함
        if FIRM_NM:
            if FIRM_NM not in EXCLUDED_FIRMS:
                if FIRM_NM != last_firm_nm:
                    sendMessageText += "\n\n" + "●" + FIRM_NM + "\n"
                    last_firm_nm = FIRM_NM
        
        # 게시글 제목(굵게)
        sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
        # 원문 링크
        sendMessageText += EMOJI_PICK + "[링크]" + "(" + ARTICLE_URL + ")" + "\n"

        # SEND_USER 값을 표시하고 싶다면 여기에 추가
        # sendMessageText += "발송 사용자: " + SEND_USER + "\n"

        formatted_messages.append(sendMessageText)
    
    # 모든 메시지를 하나의 문자열로 결합
    return "\n".join(formatted_messages)
