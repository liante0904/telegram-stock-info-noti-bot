import os
import gc
import aiohttp
import asyncio
import re
from datetime import datetime
from loguru import logger

from bs4 import BeautifulSoup
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo

async def fetch_article(session, url, headers):
    async with session.get(url, headers=headers) as response:
        return await response.text()

async def Hanyang_checkNewArticle():
    SEC_FIRM_ORDER = 22
    ARTICLE_BOARD_ORDER = 0

    TARGET_URL_TUPLE = [
        "REMOVED",
        "REMOVED",
        "REMOVED"
    ]

    json_data_list = []

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_article(session, url, headers) for url in TARGET_URL_TUPLE]
        responses = await asyncio.gather(*tasks)
    
        for ARTICLE_BOARD_ORDER, (response, url) in enumerate(zip(responses, TARGET_URL_TUPLE)):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            logger.debug(f"Hanyang Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")
            
            soup = BeautifulSoup(response, "html.parser")
            table = soup.find("table", class_="board_list")

            if not table:
                logger.warning(f"Table not found in {url}")
                continue

            rows = table.select("tbody tr")
            logger.info(f"Hanyang Scraper: Found {len(rows)} rows in {firm_info.get_board_name()}")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue 

                article_link = cells[1].find("a")
                if not article_link:
                    continue

                ARTICLE_TITLE = article_link.get_text(strip=True)
                ARTICLE_URL = article_link['href']

                if ARTICLE_URL.startswith("/"):
                    ARTICLE_URL = f"https://www.hygood.co.kr{ARTICLE_URL}"

                REG_DT = cells[2].get_text(strip=True)

                attachment_cell = cells[3].find("a")
                ATTACH_URL = ""
                if attachment_cell:
                    ATTACH_URL = attachment_cell['href']
                    if ATTACH_URL.startswith("/"):
                        ATTACH_URL = f"https://www.hygood.co.kr{ATTACH_URL}"
                
                json_data_list.append({
                    "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                    "FIRM_NM":firm_info.get_firm_name(),
                    "REG_DT":re.sub(r"[-./]", "", REG_DT),
                    "ARTICLE_TITLE": ARTICLE_TITLE,
                    "ARTICLE_URL": ATTACH_URL,
                    "DOWNLOAD_URL": ATTACH_URL,
                    "TELEGRAM_URL": ATTACH_URL,
                    "PDF_URL": ATTACH_URL,
                    "SAVE_TIME": datetime.now().isoformat(),
                    "KEY": ATTACH_URL
                })

    gc.collect()
    return json_data_list

if __name__ == "__main__":
    articles = asyncio.run(Hanyang_checkNewArticle())
    logger.info(f"Total articles fetched: {len(articles)}")
    for article in articles:
        logger.debug(article)
