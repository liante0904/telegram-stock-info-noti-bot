from loguru import logger
import os
import gc
import aiohttp
import asyncio
import re
from datetime import datetime

from bs4 import BeautifulSoup
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper
from models.ConfigManager import config

async def BNK_checkNewArticle():
    try:
        return await _BNK_checkNewArticle_impl()
    except Exception as e:
        logger.debug(f"BNK connection error (suppressed): {e}")
        return []

async def _BNK_checkNewArticle_impl():
    sec_firm_order = 23

    TARGET_URL_TUPLE = config.get_urls("BNKfn_23")

    json_data_list = []

    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }

    async with aiohttp.ClientSession() as session:
        tasks = [
            AsyncWebScraper(url, headers=headers).Get(session=session, retries=5, silent_retries=5)
            for url in TARGET_URL_TUPLE
        ]
        soups = await asyncio.gather(*tasks, return_exceptions=True)

        for article_board_order, (soup, url) in enumerate(zip(soups, TARGET_URL_TUPLE)):
            if isinstance(soup, Exception):
                logger.debug(f"BNK request final failure for {url}: {soup}")
                continue
            if soup is None:
                continue

            firm_info = FirmInfo(
                sec_firm_order=sec_firm_order,
                article_board_order=article_board_order
            )
            table = soup.find("table", class_="table01")

            if not table:
                logger.warning(f"Table not found in {url}")
                continue

            rows = table.select("tbody tr")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue  # Skip rows with insufficient data

                # article_title 및 article_url 추출
                article_link = cells[1].find("a")
                writer = cells[2].get_text(strip=True)
                if not article_link:
                    continue

                article_title = article_link.get_text(strip=True)

                # onclick에서 첨부파일 URL 추출
                onclick_attr = article_link.get("onclick", "")
                match = re.search(r"viewAction\(this, '\d+', '(/uploads/[^']+)', '([^']+)'\);", onclick_attr)
                article_url = ""
                if match:
                    base_path = match.group(1)
                    file_name = match.group(2)
                    article_url = f"https://www.bnkfn.co.kr{base_path}/{file_name}"

                reg_dt = cells[4].get_text(strip=True)

                json_data_list.append({
                    "sec_firm_order": sec_firm_order,
                    "article_board_order": article_board_order,
                    "firm_nm": firm_info.get_firm_name(),
                    "reg_dt": re.sub(r"[-./]", "", reg_dt),
                    "article_title": article_title,
                    "article_url": article_url,
                    "download_url": article_url,
                    "telegram_url": article_url,
                    "writer": writer,
                    "save_time": datetime.now().isoformat(),
                    "key": article_url
                })

        # 메모리 정리
        gc.collect()

    return json_data_list

# 비동기 함수 실행
if __name__ == "__main__":
    articles = asyncio.run(BNK_checkNewArticle())
    for article in articles:
        logger.debug(article)
