
from loguru import logger

def convert_pg_rows_to_telegram_messages(fetched_rows):
    """
    PostgreSQL에서 조회된 리포트 데이터를 텔레그램 메시지 형식으로 변환합니다.
    """
    if not fetched_rows:
        return []
    
    EMOJI_PICK = u'\U0001F449'
    formatted_messages = []
    message_chunk = ""
    message_limit = 3500

    EXCLUDED_FIRMS = {"네이버", "조선비즈"}
    last_firm_nm = None

    for row in fetched_rows:
        # 1. 증권사명 처리
        firm_nm = row.get('FIRM_NM')
        if firm_nm and firm_nm not in EXCLUDED_FIRMS:
            if firm_nm != last_firm_nm:
                if len(message_chunk) > message_limit - 500: # 여유 공간 확보
                    formatted_messages.append(message_chunk.strip())
                    message_chunk = ""
                
                message_chunk += f"\n\n●{firm_nm}\n"
                last_firm_nm = firm_nm

        # 2. 제목 처리
        title = row.get('ARTICLE_TITLE', '제목 없음').replace("_", " ").replace("*", "")
        item_text = f"*{title}*\n"

        # 3. URL 처리 (PostgreSQL 스키마 및 DS투자증권 특화 로직)
        sec_firm_order = row.get('SEC_FIRM_ORDER')
        tg_url = row.get('TELEGRAM_URL')
        pdf_url = row.get('PDF_URL')
        
        links_text = ""
        if sec_firm_order == 11: # DS투자증권
            if tg_url and pdf_url and tg_url != pdf_url:
                links_text = f"{EMOJI_PICK} [공유]({tg_url}), [원본]({pdf_url})\n"
            else:
                link = tg_url or pdf_url or row.get('ATTACH_URL') or "링크없음"
                links_text = f"{EMOJI_PICK} [링크]({link})\n" if link != "링크없음" else "링크없음\n"
        else:
            # 일반적인 우선순위: TELEGRAM_URL -> PDF_URL -> DOWNLOAD_URL -> ATTACH_URL
            link = tg_url or pdf_url or row.get('DOWNLOAD_URL') or row.get('ATTACH_URL') or row.get('ARTICLE_URL') or "링크없음"
            links_text = f"{EMOJI_PICK} [링크]({link})\n" if link != "링크없음" else "링크없음\n"

        item_text += links_text

        # 4. 청크 분할 체크
        if len(message_chunk) + len(item_text) > message_limit:
            formatted_messages.append(message_chunk.strip())
            message_chunk = f"\n\n●{firm_nm}\n{item_text}"
        else:
            message_chunk += item_text

    if message_chunk:
        formatted_messages.append(message_chunk.strip())

    return formatted_messages
