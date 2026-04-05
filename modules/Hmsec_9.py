# -*- coding:utf-8 -*- 
import os
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


async def Hmsec_checkNewArticle():
    SEC_FIRM_ORDER      = 9
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    # 현대차증권 투자전략
    TARGET_URL_0 =  'REMOVED'

    # 현대차증권 Report & Note 
    TARGET_URL_1 =  'REMOVED'

    # 현대차증권 해외주식
    TARGET_URL_2 =  'REMOVED'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    async with aiohttp.ClientSession() as session:
        for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            logger.debug(f"Hmsec Scraper Start: {firm_info.get_firm_name()} Board {ARTICLE_BOARD_ORDER}")

            payload = {"curPage":1}

            scraper = AsyncWebScraper(TARGET_URL)

            # HTML parse
            jres = await scraper.PostJson(session=session, params=payload)
            if not jres or 'data_list' not in jres:
                logger.warning(f"No data found for {TARGET_URL}")
                continue

            soupList = jres['data_list']
            logger.info(f"Hmsec Scraper: Found {len(soupList)} articles")

            # JSON To List
            for item in soupList:
                DOWNLOAD_URL = 'https://www.hmsec.com/documents/research/{}' 
                DOWNLOAD_URL = DOWNLOAD_URL.format(item['UPLOAD_FILE1'])

                LIST_ARTICLE_URL = 'https://docs.hmsec.com/SynapDocViewServer/job?fid={}&sync=true&fileType=URL&filePath={}' 
                LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(DOWNLOAD_URL, DOWNLOAD_URL)

                LIST_ARTICLE_TITLE = item['SUBJECT']

                REG_DT = item['REG_DATE'].strip()
                WRITER = (item.get('NAME') or '').strip()

                json_data_list.append({
                    "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                    "FIRM_NM":firm_info.get_firm_name(),
                    "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                    "REG_DT":REG_DT,
                    "ATTACH_URL":LIST_ARTICLE_URL,
                    "ARTICLE_URL":LIST_ARTICLE_URL,
                    "DOWNLOAD_URL": DOWNLOAD_URL,
                    "TELEGRAM_URL": LIST_ARTICLE_URL,
                    "PDF_URL": DOWNLOAD_URL,
                    "KEY": LIST_ARTICLE_URL,
                    "WRITER": WRITER,
                    "SAVE_TIME": datetime.now().isoformat()
                })


    # 메모리 정리
    gc.collect()
    return json_data_list

if __name__ == '__main__':
    asyncio.run(Hmsec_checkNewArticle())