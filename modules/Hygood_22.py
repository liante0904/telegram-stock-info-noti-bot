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
from models.ConfigManager import config

async def fetch_article(session, url, headers):
    async with session.get(url, headers=headers) as response:
        return await response.text()

async def Hanyang_checkNewArticle():
    sec_firm_order = 22
    article_board_order = 0

    TARGET_URL_TUPLE = config.get_urls("Hygood_22")

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
    
        for article_board_order, (response, url) in enumerate(zip(responses, TARGET_URL_TUPLE)):
            firm_info = FirmInfo(
                sec_firm_order=sec_firm_order,
                article_board_order=article_board_order
            )
            logger.debug(f"Hanyang Scraper Start: {firm_info.get_firm_name()} Board {article_board_order}")
            
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

                article_title = article_link.get_text(strip=True)
                article_url = article_link['href']

                if article_url.startswith("/"):
                    article_url = f"https://www.hygood.co.kr{article_url}"

                reg_dt = cells[2].get_text(strip=True)

                attachment_cell = cells[3].find("a")
                attach_url = ""
                if attachment_cell:
                    attach_url = attachment_cell['href']
                    if attach_url.startswith("/"):
                        attach_url = f"https://www.hygood.co.kr{attach_url}"
                
                json_data_list.append({
                    "sec_firm_order":sec_firm_order,
                    "article_board_order":article_board_order,
                    "firm_nm":firm_info.get_firm_name(),
                    "reg_dt":re.sub(r"[-./]", "", reg_dt),
                    "article_title": article_title,
                    "article_url": attach_url,
                    "download_url": attach_url,
                    "telegram_url": attach_url,
                    "pdf_url": attach_url,
                    "save_time": datetime.now().isoformat(),
                    "key": attach_url
                })

    gc.collect()
    return json_data_list

if __name__ == "__main__":
    articles = asyncio.run(Hanyang_checkNewArticle())
    logger.info(f"Total articles fetched: {len(articles)}")
    for article in articles:
        logger.debug(article)
