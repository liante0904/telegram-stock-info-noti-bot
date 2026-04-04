# -*- coding:utf-8 -*- 
import gc
import aiohttp
import asyncio
import re
from datetime import datetime
from loguru import logger

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper

async def TOSSinvest_checkNewArticle():
    SEC_FIRM_ORDER      = 15
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    # 토스증권 투자정보
    TARGET_URL_0  = 'REMOVED'

    TARGET_URL_TUPLE = (TARGET_URL_0,)
    
    async with aiohttp.ClientSession() as session:
        for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            logger.debug(f"TOSSinvest Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")

            scraper = AsyncWebScraper(TARGET_URL)
            
            # JSON parse
            jres = await scraper.GetJson(session=session)
            if not jres or 'result' not in jres or 'list' not in jres['result']:
                logger.warning(f"No data found for {TARGET_URL}")
                continue

            soupList = jres['result']['list']
            logger.info(f"TOSSinvest Scraper: Found {len(soupList)} articles")
            
            for item in soupList:
                LIST_ARTICLE_TITLE = item['title']
                LIST_ARTICLE_URL   =  item['files'][0]['filePath']
                REG_DT = item['createdAt'].split("T")[0]
                json_data_list.append({
                    "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                    "FIRM_NM":firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", REG_DT),
                    "ATTACH_URL":LIST_ARTICLE_URL,
                    "DOWNLOAD_URL": LIST_ARTICLE_URL,
                    "TELEGRAM_URL": LIST_ARTICLE_URL,
                    "PDF_URL": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                    "KEY":LIST_ARTICLE_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                })
            
    # 메모리 정리
    gc.collect()

    return json_data_list

if __name__ == "__main__":
    asyncio.run(TOSSinvest_checkNewArticle())
