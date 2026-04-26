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

async def fetch(session, url, headers):
    """비동기로 HTTP 요청을 보내는 함수"""
    async with session.get(url, headers=headers) as response:
        raw_data = await response.read()
        try:
            return raw_data.decode('utf-8')
        except UnicodeDecodeError:
            return raw_data.decode('euc-kr')

def adjust_date(REG_DT, time_str):
    reg_date = datetime.strptime(REG_DT, "%Y-%m-%d")
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

    reg_date = reg_date + timedelta(hours=hour, minutes=minute, seconds=second)

    if reg_date.hour >= 16:
        reg_date += timedelta(days=1)

    while reg_date.weekday() >= 5:
        reg_date += timedelta(days=1)

    return reg_date.strftime("%Y%m%d")

async def fetch_all_pages(session, base_url, sec_firm_order, article_board_order, headers, max_pages=None):
    """모든 페이지 데이터를 순회하며 가져오는 함수"""
    json_data_list = []
    page = 1

    while True:
        if max_pages and page > max_pages:
            break

        target_url = f"{base_url}&pageNum={page}"
        logger.debug(f"Kyobo Scraper: Fetching page {page} - {target_url}")

        try:
            html_content = await fetch(session, target_url, headers)
        except Exception as e:
            logger.error(f"Error fetching URL {target_url}: {e}")
            break

        soup = BeautifulSoup(html_content, "html.parser")

        no_data_message = soup.select_one('table.pb_Gtable tbody tr td[colspan="8"]')
        if no_data_message and "등록된 글이 없습니다." in no_data_message.get_text(strip=True):
            logger.info(f"Kyobo Scraper: No more data on page {page}")
            break

        soupList = soup.select('table.pb_Gtable tbody tr')
        logger.info(f"Kyobo Scraper: Found {len(soupList)} articles on page {page}")

        for row in soupList:
            try:
                REG_DT = row.select_one('td:nth-child(1)').get_text(strip=True).replace("/", "")
                title_cell = row.select_one('td.tLeft a')
                if not title_cell: continue
                
                LIST_ARTICLE_TITLE = title_cell.get_text(strip=True)
                LIST_ARTICLE_URL = "https://www.iprovest.com" + title_cell['href']

                CATEGORY = row.select_one('td:nth-child(3)').get_text(strip=True)
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
                
                WRITER = row.select_one('td:nth-child(5) a').get_text(strip=True)

                attachment_tag = row.select_one('td:nth-child(7) a')
                ATTACH_URL = None
                if attachment_tag:
                    ATTACH_URL = "https://www.iprovest.com" + attachment_tag['href'].replace("javascript:fileDown('", "").replace("')", "").replace("weblogic/RSDownloadServlet?filePath=", "upload")
                
                json_data_list.append({
                    "SEC_FIRM_ORDER": sec_firm_order,
                    "ARTICLE_BOARD_ORDER": article_board_order,
                    "FIRM_NM": FirmInfo(sec_firm_order, article_board_order).get_firm_name(),
                    "REG_DT": REG_DT,
                    "DOWNLOAD_URL": ATTACH_URL,
                    "TELEGRAM_URL": ATTACH_URL,
                    "PDF_URL": ATTACH_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "CATEGORY": CATEGORY,
                    "WRITER": WRITER,
                    "KEY": ATTACH_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"Error parsing Kyobo article: {e}")
                continue

        page += 1

    return json_data_list

async def Kyobo_checkNewArticle(full_fetch=False):
    """교보증권 데이터 수집"""
    SEC_FIRM_ORDER = 24
    TARGET_URL_TUPLE = config.get_urls("Kyobo_24")

    max_pages = None if full_fetch else 3

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ko,en-US;q=0.9,en;q=0.8",
        "cache-control": "max-age=0",
        "connection": "keep-alive",
        "cookie": "JSESSIONID=eYlhpdwRSK32tbxaQZLH0LPcaiRI8--jqNMtMC8Glme6oUe6VdB0!-379202731",
        "host": "www.iprovest.com",
        "referer": "https://www.iprovest.com",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }

    all_results = []
    async with aiohttp.ClientSession() as session:
        for article_board_order, base_url in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(SEC_FIRM_ORDER, article_board_order)
            logger.debug(f"Kyobo Scraper Start: {firm_info.get_firm_name()}")
            results = await fetch_all_pages(session, base_url, SEC_FIRM_ORDER, article_board_order, headers, max_pages)
            all_results.extend(results)

    gc.collect()
    logger.info(f"Kyobo Scraper: Found {len(all_results)} total articles")
    return all_results

if __name__ == "__main__":
    result = asyncio.run(Kyobo_checkNewArticle(full_fetch=True))
    logger.info(f"Total articles fetched: {len(result)}")
