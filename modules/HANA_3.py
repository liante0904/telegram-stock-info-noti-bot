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

async def fetch(session, url):
    """비동기로 HTTP 요청을 보내는 함수"""
    async with session.get(url) as response:
        return await response.text()

def adjust_date(REG_DT, time_str):
    reg_date = datetime.strptime(REG_DT, "%Y%m%d")
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
    elif 0 <= hour <= 23:
        # 24시간제이므로 추가 처리 필요 없음
        pass
    else:
        raise ValueError(f"Invalid hour format: {hour}")

    # 시간 계산
    current_time = reg_date + timedelta(hours=hour, minutes=minute, seconds=second)

    # 오전 10시 이후는 다음날로 처리
    if current_time.hour >= 10:
        reg_date += timedelta(days=1)

    # 주말 처리 (토요일: 5, 일요일: 6)
    while reg_date.weekday() >= 5:  # 주말이면
        reg_date += timedelta(days=1)

    return reg_date.strftime("%Y%m%d")


async def fetch_all_pages(session, base_url, sec_firm_order, article_board_order, max_pages=None):
    """모든 페이지 데이터를 순회하며 가져오는 함수"""
    json_data_list = []
    page = 1

    while True:
        if max_pages and page > max_pages:  # 최대 페이지를 초과하면 종료
            break

        target_url = f"{base_url}&curPage={page}"
        print(f"Fetching: {target_url}")

        try:
            html_content = await fetch(session, target_url)
        except Exception as e:
            print(f"Error fetching URL {target_url}: {e}")
            break

        # HTML parse
        soup = BeautifulSoup(html_content, "html.parser")
        soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

        if not soupList:  # 더 이상 데이터가 없으면 종료
            break

        for list in soupList:
            try:
                LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').get_text()
                LIST_ARTICLE_URL = 'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
                REG_DT = list.select_one('div.con > ul > li.mb7.m-info.info > span:nth-child(3)').get_text()
                REG_DT = re.sub(r"[-./]", "", REG_DT)
                WRITER = list.select_one('div.con > ul > li.mb7.m-info.info > span.none.m-name').get_text()
                time_str = list.select_one('div.con > ul > li.mb7.m-info.info > span.hide-on-mobile.txtbasic.r-side-bar').get_text()

                json_data_list.append({
                    "SEC_FIRM_ORDER": sec_firm_order,
                    "ARTICLE_BOARD_ORDER": article_board_order,
                    "FIRM_NM": FirmInfo(sec_firm_order, article_board_order).get_firm_name(),
                    "REG_DT": adjust_date(REG_DT, time_str),
                    "ATTACH_URL": LIST_ARTICLE_URL,
                    "DOWNLOAD_URL": LIST_ARTICLE_URL,
                    "TELEGRAM_URL": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "KEY:": LIST_ARTICLE_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        page += 1  # 다음 페이지로 이동

    return json_data_list


async def HANA_checkNewArticle(full_fetch=False):
    """하나금융 데이터 수집"""
    SEC_FIRM_ORDER = 3

    TARGET_URL_TUPLE = [
        # 하나금융 Daily
        'https://www.hanaw.com/main/research/research/list.cmd?pid=4&cid=1',
        # 하나금융 산업 분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=1',
        # 하나금융 기업 분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=2',
        # 하나금융 주식 전략
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=1',
        # 하나금융 Small Cap
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=3',
        # 하나금융 기업 메모
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=4',
        # 하나금융 Quant
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=2',
        # 하나금융 포트폴리오
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=3',
        # 하나금융 투자정보
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=4',
        # 글로벌 투자전략
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=1',
        # 글로벌 산업분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=2',
        # 글로벌 기업분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=3'
    ]

    # full_fetch가 False이면 최대 3페이지까지만 조회
    max_pages = None if full_fetch else 3

    all_results = []
    async with aiohttp.ClientSession() as session:
        for article_board_order, base_url in enumerate(TARGET_URL_TUPLE):
            results = await fetch_all_pages(session, base_url, SEC_FIRM_ORDER, article_board_order, max_pages)
            all_results.extend(results)

    # 메모리 정리
    gc.collect()
    return all_results


async def main():
    result = await HANA_checkNewArticle(full_fetch=True)  # main에서는 모든 페이지 조회
    print(f"Fetched {len(result)} articles.")
    print(result)
    db = SQLiteManager()
    inserted_count = db.insert_json_data_list(result, 'data_main_daily_send')  # 모든 데이터를 한 번에 삽입
    print(inserted_count)


if __name__ == "__main__":
    asyncio.run(main())
