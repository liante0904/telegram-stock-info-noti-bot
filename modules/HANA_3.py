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


async def fetch(session, url):
    """비동기로 HTTP 요청을 보내는 함수"""
    async with session.get(url) as response:
        return await response.text()


async def HANA_checkNewArticle():
    SEC_FIRM_ORDER = 3
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

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

    async with aiohttp.ClientSession() as session:
        for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            try:
                html_content = await fetch(session, TARGET_URL)
            except Exception as e:
                print(f"Error fetching URL {TARGET_URL}: {e}")
                continue

            # HTML parse
            soup = BeautifulSoup(html_content, "html.parser")
            soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

            for list in soupList:
                try:
                    LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').get_text()
                    LIST_ARTICLE_URL = 'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
                    REG_DT = list.select_one('div.con > ul > li.mb7.m-info.info > span:nth-child(3)').get_text()
                    REG_DT = re.sub(r"[-./]", "", REG_DT)
                    WRITER = list.select_one('div.con > ul > li.mb7.m-info.info > span.none.m-name').get_text()
                    time_str = list.select_one('div.con > ul > li.mb7.m-info.info > span.hide-on-mobile.txtbasic.r-side-bar').get_text()

                    json_data_list.append({
                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                        "FIRM_NM": firm_info.get_firm_name(),
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

            # 메모리 정리
            gc.collect()
    return json_data_list


def adjust_date(REG_DT, time_str):
    reg_date = datetime.strptime(REG_DT, "%Y%m%d")
    time_str = time_str.strip()
    match = re.match(r"(오전|오후)\s*(\d{1,2}):(\d{2})(?::(\d{2}))?", time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    period, hour, minute, second = match.groups()
    hour = int(hour)
    minute = int(minute)
    second = int(second) if second else 0

    if period == "오후" and hour != 12:
        hour += 12
    elif period == "오전" and hour == 12:
        hour = 0

    current_time = reg_date + timedelta(hours=hour, minutes=minute, seconds=second)

    if current_time.hour >= 10:
        reg_date += timedelta(days=1)

    while reg_date.weekday() >= 5:
        reg_date += timedelta(days=1)

    return reg_date.strftime("%Y%m%d")


async def main():
    result = await HANA_checkNewArticle()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
