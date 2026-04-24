from loguru import logger


def build_sql_telegram_message_query(date_expr="CURRENT_DATE", only_sent=True):
    """
    SQL만으로 발송용 메시지 행을 만들고 싶을 때 쓰는 쿼리 생성기.

    이 함수는 현재 운영 SQL 포맷을 그대로 문자열로 반환한다.
    나중에 `cursor.execute(*build_sql_telegram_message_query())` 형태로
    바로 붙일 수 있도록 의도적으로 독립시켜 둔다.

    Args:
        date_expr: SQL WHERE 절에서 사용할 날짜 표현식.
        only_sent: True면 `MAIN_CH_SEND_YN = 'Y'` 조건을 포함한다.

    Returns:
        tuple[str, list]: (query, params)
    """
    sent_clause = 'AND "MAIN_CH_SEND_YN" = \'Y\'' if only_sent else ""

    query = f"""
WITH sent_rows AS (
    SELECT DISTINCT ON (
        CASE
            WHEN COALESCE("TELEGRAM_URL", '') = '' THEN report_id::text
            ELSE "TELEGRAM_URL"
        END
    )
        report_id,
        "SEC_FIRM_ORDER" AS sec_firm_order,
        "ARTICLE_BOARD_ORDER" AS article_board_order,
        "FIRM_NM" AS firm_nm,
        COALESCE("ARTICLE_TITLE", '제목 없음') AS article_title,
        COALESCE("TELEGRAM_URL", '') AS telegram_url,
        COALESCE("PDF_URL", '') AS pdf_url,
        COALESCE("DOWNLOAD_URL", '') AS download_url,
        COALESCE("ATTACH_URL", '') AS attach_url,
        COALESCE("ARTICLE_URL", '') AS article_url,
        "SAVE_TIME" AS save_time
    FROM "TB_SEC_REPORTS"
    WHERE DATE("SAVE_TIME") = {date_expr}
      {sent_clause}
    ORDER BY
        CASE
            WHEN COALESCE("TELEGRAM_URL", '') = '' THEN report_id::text
            ELSE "TELEGRAM_URL"
        END,
        "SEC_FIRM_ORDER", "ARTICLE_BOARD_ORDER", "SAVE_TIME"
), rendered AS (
    SELECT
        report_id,
        sec_firm_order,
        article_board_order,
        firm_nm,
        replace(replace(article_title, '_', ' '), '*', '') AS title_text,
        CASE
            WHEN COALESCE(telegram_url, '') <> '' THEN telegram_url
            WHEN COALESCE(pdf_url, '') <> '' THEN pdf_url
            WHEN COALESCE(download_url, '') <> '' THEN download_url
            WHEN COALESCE(attach_url, '') <> '' THEN attach_url
            WHEN COALESCE(article_url, '') <> '' THEN article_url
            ELSE ''
        END AS final_link,
        CASE
            WHEN lag(firm_nm) OVER (ORDER BY sec_firm_order, report_id) IS DISTINCT FROM firm_nm
                THEN E'\\n\\n●' || firm_nm || E'\\n'
            ELSE ''
        END AS firm_header
    FROM sent_rows
)
SELECT
    firm_header || title_text || E'\\n' ||
    CASE
        WHEN final_link <> '' THEN '👉 [링크](' || final_link || ')'
        ELSE '링크없음'
    END || E'\\n' AS message_line
FROM rendered
ORDER BY sec_firm_order, report_id;
"""
    return query, []


def convert_pg_sql_rows_to_telegram_messages(fetched_rows, message_limit=3500, header="[SQL]"):
    """
    SQL 결과(message_line)를 Telegram 발송 chunk로 묶는다.

    이 함수는 나중에 SQL 기반 발송으로 전환할 때 바로 붙일 수 있게
    현재 포맷을 최대한 단순하게 유지한다.
    - 청크가 잘리면 새 청크 첫 줄에 `header`를 다시 붙인다.
    - SQL 결과는 이미 회사 헤더/제목/링크까지 포함한 message_line이어야 한다.
    """
    if not fetched_rows:
        return []

    formatted_messages = []
    message_chunk = header

    for row in fetched_rows:
        line = row.get("message_line", "")
        if not line:
            continue

        if len(message_chunk) + len(line) > message_limit:
            formatted_messages.append(message_chunk.strip())
            message_chunk = f"{header}\n{line}"
        else:
            message_chunk += line

    if message_chunk.strip():
        formatted_messages.append(message_chunk.strip())

    return formatted_messages

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
