async def convert_oracle_to_telegram_messages(fetched_rows):
    """
    Converts fetched Oracle SQL rows into formatted Telegram messages.
    
    Args:
        fetched_rows (list of dict): Oracle DB에서 가져온 dict 형태의 데이터

    Returns:
        list of str: 텔레그램 메시지 리스트
    """
    if not fetched_rows:
        raise ValueError("Invalid fetched_rows.")

    EMOJI_PICK = u'\U0001F449'
    formatted_messages = []
    message_chunk = ""
    message_limit = 3500

    EXCLUDED_FIRMS = {"네이버", "조선비즈"}
    last_firm_nm = None

    for row in fetched_rows:
        firm_nm = row.get('firm_nm')
        article_title = row.get('article_title')
        telegram_url = row.get('telegram_url')
        attach_url = row.get('attach_url')
        download_url = row.get('download_url')
        article_url = row.get('article_url')

        sendMessageText = ""

        if firm_nm and firm_nm not in EXCLUDED_FIRMS:
            if firm_nm != last_firm_nm:
                if len(message_chunk) + len(sendMessageText) > message_limit:
                    formatted_messages.append(message_chunk.strip())
                    message_chunk = ""
                message_chunk += f"\n\n●{firm_nm}\n"
                last_firm_nm = firm_nm

        if article_title:
            sendMessageText += f"*{article_title.replace('_', ' ').replace('*', '')}*\n"

        if telegram_url:
            link_url = telegram_url
        elif attach_url:
            link_url = attach_url
        elif download_url:
            link_url = download_url
        elif article_url:
            link_url = article_url
        else:
            link_url = "링크없음"

        if link_url == "링크없음":
            sendMessageText += "링크없음\n"
        else:
            sendMessageText += f"{EMOJI_PICK}[링크]({link_url})\n"

        if len(message_chunk) + len(sendMessageText) > message_limit:
            formatted_messages.append(message_chunk.strip())
            message_chunk = f"\n\n●{firm_nm}\n" + sendMessageText
        else:
            message_chunk += sendMessageText

    if message_chunk:
        formatted_messages.append(message_chunk.strip())

    return formatted_messages