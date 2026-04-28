from loguru import logger
def convert_sql_to_telegram_messages(fetched_rows):
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
                                     - 'firm_nm' (str): The name of the firm.
                                     - 'article_title' (str): The title of the article.
                                     - 'article_url' (str): The URL of the article.
                                     - 'save_time' (str): The save timestamp.
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
            {"id": 1, "firm_nm": "삼성전자", "article_title": "삼성 신제품 발표", 
             "article_url": "https://example.com/article/1", "save_time": "2024-09-27", 
             "SEND_USER": "user1"},
            {"id": 2, "firm_nm": "LG전자", "article_title": "LG OLED TV", 
             "article_url": "https://example.com/article/2", "save_time": "2024-09-27", 
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
        # 첫 번째 요소인 id는 무시하고, 나머지를 firm_nm, article_title, article_url, save_time, SEND_USER로 할당
        # id, fetched_row['firm_nm'], fetched_row['article_title'], fetched_row['article_url'], save_time, SEND_USER = fetched_row

        sendMessageText = ""

        # 'firm_nm'이 존재하는 경우에만 포함
        if row['firm_nm']:
            if row['firm_nm'] not in EXCLUDED_FIRMS:
                if row['firm_nm'] != last_firm_nm:
                    # 메시지가 3500자를 넘으면 추가된 메시지들을 배열에 저장하고 새로 시작
                    if len(message_chunk) + len(sendMessageText) > message_limit:
                        formatted_messages.append(message_chunk.strip())
                        message_chunk = ""  # 새로 시작

                    # 새 메시지 조각의 첫 줄에 firm_nm 추가
                    message_chunk += "\n\n" + "●" + row['firm_nm'] + "\n"
                    last_firm_nm = row['firm_nm']

        # 게시글 제목(굵게)
        sendMessageText += "*" + row['article_title'].replace("_", " ").replace("*", "") + "*" + "\n"

        # URL 우선순위 설정
        if row.get('sec_firm_order') == 11:
            # DS투자의 경우, 트리거에 의해 생성된 TELEGRAM_URL이 최우선이며, 
            # 만약 비어있다면 아직 생성 전이므로 링크없음으로 처리하여 잘못된 링크 발송 방지
            link_url = row.get('telegram_url') if row.get('telegram_url') else "링크없음"
        link_url = row.get('telegram_url') or row.get('download_url') or row.get('article_url') or ""
        
        # 원문 링크 추가
        if link_url == "링크없음":
            sendMessageText += "링크없음\n"
        else:
            sendMessageText += EMOJI_PICK + "[링크]" + "(" + link_url + ")" + "\n"

        # 메시지가 3500자를 넘지 않도록 쌓음
        if len(message_chunk) + len(sendMessageText) > message_limit:
            # 이전 chunk를 저장하고 새로운 chunk 시작
            formatted_messages.append(message_chunk.strip())
            # 새 메시지 조각의 첫 줄에 firm_nm 추가
            message_chunk = "\n\n" + "●" + row['firm_nm'] + "\n" + sendMessageText
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
        # fetch_keyword_reports 등에서 넘어오는 데이터 순서: report_id, firm_nm, article_title, telegram_url, save_time
        if len(data) == 5:
            _, firm_nm, article_title, telegram_url, save_time = data
        else:
            # 기존 4개 컬럼(firm_nm, article_title, telegram_url, save_time) 대응
            firm_nm, article_title, telegram_url, save_time = data[:4]

        sendMessageText = ""
        
        # 'firm_nm'이 존재하는 경우에만 포함
        if firm_nm:
            if firm_nm not in EXCLUDED_FIRMS:
                if firm_nm != last_firm_nm:
                    sendMessageText += "\n\n" + "●" + firm_nm + "\n"
                    last_firm_nm = firm_nm
        
        # 게시글 제목(굵게)
        sendMessageText += "*" + article_title.replace("_", " ").replace("*", "") + "*" + "\n"
        # 원문 링크
        sendMessageText += EMOJI_PICK + "[링크]" + "(" + telegram_url + ")" + "\n"

        # SEND_USER 값을 표시하고 싶다면 여기에 추가
        # sendMessageText += "발송 사용자: " + SEND_USER + "\n"

        formatted_messages.append(sendMessageText)
    
    # 모든 메시지를 하나의 문자열로 결합
    return "\n".join(formatted_messages)
