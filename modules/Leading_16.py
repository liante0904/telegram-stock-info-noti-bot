# -*- coding:utf-8 -*- 
import re
import gc
import aiohttp
import asyncio
from datetime import datetime
from loguru import logger

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper

async def Leading_checkNewArticle():
    SEC_FIRM_ORDER      = 16
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    # 리딩투자증권 
    TARGET_URL_0 = "REMOVED"
    TARGET_URL_TUPLE = (TARGET_URL_0, )

    async with aiohttp.ClientSession() as session:
        for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            logger.debug(f"Leading Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")
            
            scraper = AsyncWebScraper(TARGET_URL)
            soup = await scraper.Get(session=session)
            if not soup:
                logger.warning(f"No data found for {TARGET_URL}")
                continue

            # soupListHead에서 헤더 추출
            soupListHead = soup.select('#sub-container > div.table-wrap > table > thead > tr')
            if not soupListHead:
                logger.warning(f"Could not find table headers for {TARGET_URL}")
                continue
            headers = [th.text.strip() for th in soupListHead[0].find_all('th')]
            logger.debug(f"Leading Scraper Headers: {headers}")

            # soupList에서 데이터 추출
            soupList = soup.select('#sub-container > div.table-wrap > table > tbody > tr')
            logger.info(f"Leading Scraper: Found {len(soupList)} articles")

            parsed_data = []  # 데이터를 저장할 리스트
            for row in soupList:
                columns = []  # 한 행의 데이터 저장
                for idx, td in enumerate(row.find_all('td')):
                    if idx >= len(headers):
                        break
                    header = headers[idx]
                    if header == '첨부':
                        a_tag = td.find('a')
                        columns.append(a_tag.attrs.get('href', '').strip() if a_tag else '')
                    else:
                        columns.append(td.get_text(strip=True))

                if len(columns) < len(headers):
                    continue

                row_data = dict(zip(headers, columns))
                parsed_data.append(row_data)
                
            # soupList에서 게시물 정보 파싱
            for item in parsed_data:
                attachment_link = "없음"
                if item.get('첨부'):
                    attachment_link =  f"http://www.leading.co.kr{item['첨부']}"
                
                LIST_ARTICLE_TITLE = item.get('제목', 'No Title')
                LIST_ARTICLE_URL = attachment_link
                DOWNLOAD_URL     = attachment_link
                REG_DT = item.get('작성일', '')
                REG_DT = re.sub(r"[-./]", "", REG_DT)
                
                json_data_list.append({
                    "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                    "FIRM_NM":firm_info.get_firm_name(),
                    "REG_DT":REG_DT,
                    "ATTACH_URL":LIST_ARTICLE_URL,
                    "DOWNLOAD_URL": DOWNLOAD_URL,
                    "TELEGRAM_URL": DOWNLOAD_URL,
                    "PDF_URL": DOWNLOAD_URL,
                    "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                    "SAVE_TIME": datetime.now().isoformat(),
                    "KEY": attachment_link
                })
            
            
    # 메모리 정리
    gc.collect()
    return json_data_list

if __name__ == "__main__":
    asyncio.run(Leading_checkNewArticle())
