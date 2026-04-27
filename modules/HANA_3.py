import asyncio
import aiohttp
import gc
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os
import sys
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config

async def fetch(session, url):
    """비동기로 HTTP 요청을 보내는 함수"""
    async with session.get(url) as response:
        return await response.text()

def adjust_date(REG_DT, time_str):
    reg_date = datetime.strptime(REG_DT, "%Y%m%d")
    time_str = time_str.strip()

    match = re.match(r"(오전|오후)?\s*(\d{1,2}):(\d{2})(?::(\d{2}))?", time_str)
    if not match:
        raise ValueError(f"Invalid time format: {time_str}")

    period, hour, minute, second = match.groups()
    hour = int(hour)
    minute = int(minute)
    second = int(second) if second else 0

    if period:
        if period == "오후" and hour != 12:
            hour += 12
        elif period == "오전" and hour == 12:
            hour = 0
    elif 0 <= hour <= 23:
        pass
    else:
        raise ValueError(f"Invalid hour format: {hour}")

    current_time = reg_date + timedelta(hours=hour, minutes=minute, seconds=second)

    if current_time.hour >= 10:
        reg_date += timedelta(days=1)

    while reg_date.weekday() >= 5:
        reg_date += timedelta(days=1)

    return reg_date.strftime("%Y%m%d")


async def fetch_all_pages(session, base_url, sec_firm_order, article_board_order, max_pages=None):
    """모든 페이지 데이터를 순회하며 가져오는 함수"""
    json_data_list = []
    page = 1

    while True:
        if max_pages and page > max_pages:
            break

        target_url = f"{base_url}&curPage={page}"
        logger.debug(f"HANA Scraper: Fetching page {page} - {target_url}")

        try:
            html_content = await fetch(session, target_url)
        except Exception as e:
            logger.error(f"Error fetching URL {target_url}: {e}")
            break

        soup = BeautifulSoup(html_content, "html.parser")
        soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

        if not soupList:
            logger.info(f"HANA Scraper: No more articles on page {page}")
            break

        logger.info(f"HANA Scraper: Found {len(soupList)} articles on page {page}")

        for list_item in soupList:
            try:
                LIST_ARTICLE_TITLE = list_item.select_one('div.con > ul > li.mb4 > h3 > a').get_text()
                LIST_ARTICLE_URL = 'https://www.hanaw.com' + list_item.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
                REG_DT = list_item.select_one('div.con > ul > li.mb7.m-info.info > span:nth-child(3)').get_text()
                REG_DT = re.sub(r"[-./]", "", REG_DT)
                WRITER = list_item.select_one('div.con > ul > li.mb7.m-info.info > span.none.m-name').get_text()
                time_str = list_item.select_one('div.con > ul > li.mb7.m-info.info > span.hide-on-mobile.txtbasic.r-side-bar').get_text()

                market_type = 'GLOBAL' if article_board_order in (9, 10, 11) else 'KR'

                json_data_list.append({
                    "sec_firm_order": sec_firm_order,
                    "article_board_order": article_board_order,
                    "FIRM_NM": FirmInfo(sec_firm_order, article_board_order).get_firm_name(),
                    "REG_DT": adjust_date(REG_DT, time_str),
                    "DOWNLOAD_URL": LIST_ARTICLE_URL,
                    "TELEGRAM_URL": LIST_ARTICLE_URL,
                    "PDF_URL": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "KEY": LIST_ARTICLE_URL,
                    "SAVE_TIME": datetime.now().isoformat(),
                    "MKT_TP": market_type
                })
            except Exception as e:
                logger.error(f"Error parsing HANA article: {e}")
                continue

        page += 1

    return json_data_list


async def HANA_checkNewArticle(full_fetch=False):
    """하나금융 데이터 수집"""
    sec_firm_order = 3

    TARGET_URL_TUPLE = config.get_urls("HANA_3")

    max_pages = None if full_fetch else 3
    all_results = []
    
    async with aiohttp.ClientSession() as session:
        for article_board_order, base_url in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(sec_firm_order, article_board_order)
            logger.debug(f"HANA Scraper Start: {firm_info.get_firm_name()} Board {article_board_order}")
            results = await fetch_all_pages(session, base_url, sec_firm_order, article_board_order, max_pages)
            all_results.extend(results)

    gc.collect()
    logger.info(f"HANA Scraper: Found {len(all_results)} total articles")
    return all_results


async def main():
    result = await HANA_checkNewArticle(full_fetch=True)
    logger.info(f"Fetched {len(result)} articles from HANA.")

if __name__ == "__main__":
    asyncio.run(main())
