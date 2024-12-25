import asyncio
import aiohttp
import gc
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager

async def fetch(session, url, headers):
    """비동기로 HTTP 요청을 보내는 함수"""
    async with session.get(url, headers=headers) as response:
        raw_data = await response.read()  # 응답 데이터를 바이너리로 읽음
        # 서버의 인코딩이 UTF-8이 아니면 EUC-KR로 디코딩 시도
        try:
            return raw_data.decode('utf-8')  # UTF-8 시도
        except UnicodeDecodeError:
            return raw_data.decode('euc-kr')  # EUC-KR 시도

def adjust_date(REG_DT, time_str):
    reg_date = datetime.strptime(REG_DT, "%Y-%m-%d")
    time_str = time_str.strip()

    # "오전/오후" 형식 또는 24시간제 형식 모두 지원
    match = re.match(r"(오전|오후)?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?", time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    period, hour, minute, second = match.groups()
    hour = int(hour)
    minute = int(minute)
    second = int(second) if second else 0

    # "오전/오후"가 없는 경우: 24시간제로 처리
    if period:
        if period == "오후" and hour != 12:
            hour += 12
        elif period == "오전" and hour == 12:  # 오전 12시는 자정
            hour = 0

    reg_date = reg_date + timedelta(hours=hour, minutes=minute, seconds=second)

    # 오전 10시 이후는 다음날로 처리
    if reg_date.hour >= 10:
        reg_date += timedelta(days=1)

    # 주말 처리 (토요일: 5, 일요일: 6)
    while reg_date.weekday() >= 5:
        reg_date += timedelta(days=1)

    return reg_date.strftime("%Y%m%d")


async def fetch_all_pages(session, base_url, sec_firm_order, article_board_order, headers, max_pages=None):
    """모든 페이지 데이터를 순회하며 가져오는 함수"""
    json_data_list = []
    page = 1

    while True:
        if max_pages and page > max_pages:  # 최대 페이지를 초과하면 종료
            break

        target_url = f"{base_url}&pageNum={page}"
        print(f"Fetching: {target_url}")

        try:
            html_content = await fetch(session, target_url, headers)
        except Exception as e:
            print(f"Error fetching URL {target_url}: {e}")
            break

        # HTML parse
        soup = BeautifulSoup(html_content, "html.parser")
        soupList = soup.select('table.pb_Gtable tbody tr')

        if not soupList:  # 더 이상 데이터가 없으면 종료
            break

        for row in soupList:
            try:
                # 일자
                REG_DT = row.select_one('td:nth-child(1)').get_text(strip=True).replace("/", "-")

                # 제목 및 상세 URL
                title_cell = row.select_one('td.tLeft a')
                LIST_ARTICLE_TITLE = title_cell.get_text(strip=True)
                LIST_ARTICLE_URL = "https://www.iprovest.com" + title_cell['href']

                # 종목/업종
                CATEGORY = row.select_one('td:nth-child(3)').get_text(strip=True)

                # 구분
                ANALYSIS_TYPE = row.select_one('td:nth-child(4)').get_text(strip=True)
                if ANALYSIS_TYPE == "기업분석":
                    article_board_order = 0
                    LIST_ARTICLE_TITLE = f"{CATEGORY} : {LIST_ARTICLE_TITLE}"
                elif ANALYSIS_TYPE == "산업분석":
                    article_board_order = 1
                    LIST_ARTICLE_TITLE = f"{CATEGORY} : {LIST_ARTICLE_TITLE}"
                elif ANALYSIS_TYPE == "투자전략":
                    article_board_order = 2
                elif ANALYSIS_TYPE == "채권전략":
                    article_board_order = 3
                else:
                    article_board_order = 4
                # 작성자
                WRITER = row.select_one('td:nth-child(5) a').get_text(strip=True)

                # 첨부파일 (다운로드 URL)
                attachment_tag = row.select_one('td:nth-child(7) a')
                ATTACH_URL = None
                if attachment_tag:
                    ATTACH_URL = "https://www.iprovest.com" + attachment_tag['href'].replace("javascript:fileDown('", "").replace("')", "").replace("weblogic/RSDownloadServlet?filePath=", "upload")

                # 시간은 기본값으로 10:00 설정
                time_str = "10:00"

                # JSON 데이터 생성
                json_data_list.append({
                    "SEC_FIRM_ORDER": sec_firm_order,
                    "ARTICLE_BOARD_ORDER": article_board_order,
                    "FIRM_NM": FirmInfo(sec_firm_order, article_board_order).get_firm_name(),
                    "REG_DT": adjust_date(REG_DT, time_str),
                    "ATTACH_URL": ATTACH_URL,
                    "DOWNLOAD_URL": ATTACH_URL,
                    "TELEGRAM_URL": ATTACH_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "CATEGORY": CATEGORY,
                    "WRITER": WRITER,
                    "KEY": LIST_ARTICLE_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        page += 1  # 다음 페이지로 이동

    return json_data_list



async def Kyobo_checkNewArticle(full_fetch=False):
    """교보증권 데이터 수집"""
    SEC_FIRM_ORDER = 24

    TARGET_URL_TUPLE = [
        # 교보증권 리서치 데이터 URL
        'https://www.iprovest.com/weblogic/RSReportServlet?scr_id=10&menuCode=1&srch_db=0&QU=&DT1=&DT2=&provestz='
    ]

    # full_fetch가 False이면 최대 3페이지까지만 조회
    max_pages = None if full_fetch else 3

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ko,en-US;q=0.9,en;q=0.8",
        "cache-control": "max-age=0",
        "connection": "keep-alive",
        "cookie": "JSESSIONID=eYlhpdwRSK32tbxaQZLH0LPcaiRI8--jqNMtMC8Glme6oUe6VdB0!-379202731",  # 유효한 쿠키 값 필요
        "host": "www.iprovest.com",
        "referer": "https://www.iprovest.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }

    all_results = []
    async with aiohttp.ClientSession() as session:
        for article_board_order, base_url in enumerate(TARGET_URL_TUPLE):
            results = await fetch_all_pages(session, base_url, SEC_FIRM_ORDER, article_board_order, headers, max_pages)
            all_results.extend(results)

    # 메모리 정리
    gc.collect()
    return all_results


async def main():
    result = await Kyobo_checkNewArticle(full_fetch=True)  # main에서는 모든 페이지 조회
    print(f"Fetched {len(result)} articles.")
    print(result)
    db = SQLiteManager()
    inserted_count = db.insert_json_data_list(result, 'data_main_daily_send')  # 모든 데이터를 한 번에 삽입
    print(inserted_count)


if __name__ == "__main__":
    asyncio.run(main())
