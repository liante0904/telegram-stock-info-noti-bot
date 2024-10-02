def convert_sql_to_telegram_messages(fetched_rows):
    EMOJI_PICK = u'\U0001F449'  # 이모지 설정
    formatted_messages = []
    message_chunk = ""  # 현재 메시지 조각
    message_limit = 3500  # 텔레그램 메시지 제한

    # 특정 FIRM_NM을 제외할 리스트
    EXCLUDED_FIRMS = {"네이버", "조선비즈"}
    last_firm_nm = None  # 마지막으로 출력된 FIRM_NM을 저장하는 변수

    for row in fetched_rows:
        # 첫 번째 요소인 id는 무시하고, 나머지를 FIRM_NM, ARTICLE_TITLE, ARTICLE_URL, SAVE_TIME, SEND_USER로 할당
        id, FIRM_NM, ARTICLE_TITLE, ARTICLE_URL, SAVE_TIME, SEND_USER = row

        sendMessageText = ""

        # 'FIRM_NM'이 존재하는 경우에만 포함
        if FIRM_NM:
            if FIRM_NM not in EXCLUDED_FIRMS:
                if FIRM_NM != last_firm_nm:
                    # 메시지가 3500자를 넘으면 추가된 메시지들을 배열에 저장하고 새로 시작
                    if len(message_chunk) + len(sendMessageText) > message_limit:
                        formatted_messages.append(message_chunk.strip())
                        message_chunk = ""  # 새로 시작

                    # 새 메시지 조각의 첫 줄에 FIRM_NM 추가
                    message_chunk += "\n\n" + "●" + FIRM_NM + "\n"
                    last_firm_nm = FIRM_NM

        # 게시글 제목(굵게)
        sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
        # 원문 링크
        sendMessageText += EMOJI_PICK + "[링크]" + "(" + ARTICLE_URL + ")" + "\n"

        # 메시지가 3500자를 넘지 않도록 쌓음
        if len(message_chunk) + len(sendMessageText) > message_limit:
            # 이전 chunk를 저장하고 새로운 chunk 시작
            formatted_messages.append(message_chunk.strip())
            # 새 메시지 조각의 첫 줄에 FIRM_NM 추가
            message_chunk = "\n\n" + "●" + FIRM_NM + "\n" + sendMessageText
        else:
            message_chunk += sendMessageText

    # 마지막 남은 메시지도 저장
    if message_chunk:
        formatted_messages.append(message_chunk.strip())

    return formatted_messages
