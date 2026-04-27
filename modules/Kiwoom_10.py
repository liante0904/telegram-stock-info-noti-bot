# -*- coding:utf-8 -*- 
import os
import gc
import requests
import re
import asyncio
import datetime
from loguru import logger

import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper
from models.ConfigManager import config

def get_start_of_year():
    return datetime.datetime(datetime.datetime.now().year, 1, 1).strftime("%Y%m%d")

async def Kiwoom_checkNewArticle(stdate=None, eddate=None, page_size=100):
    if stdate is None:
        stdate = get_start_of_year()
    if eddate is None:
        KST = datetime.timezone(datetime.timedelta(hours=9))
        eddate = datetime.datetime.now(KST).strftime("%Y%m%d")

    sec_firm_order = 10
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = config.get_urls("Kiwoom_10")

    async def fetch_data(TARGET_URL, article_board_order):
        firm_info = FirmInfo(
            sec_firm_order=sec_firm_order,
            article_board_order=article_board_order
        )
        logger.debug(f"Kiwoom Scraper Start: {firm_info.get_firm_name()} Board {article_board_order}")

        payload = {
            "pageNo": 1,
            "pageSize": page_size,
            "stdate": stdate,
            "eddate": eddate,
            "f_keyField": '',
            "f_key": '',
            "_reqAgent": 'ajax',
            "dummyVal": 0
        }

        scraper = AsyncWebScraper(TARGET_URL)

        # HTML parse
        try:
            jres = await scraper.PostJson(params=payload)
            if not jres or jres.get('totalCount', 0) == 0:
                logger.info(f"Kiwoom Scraper: No articles for board {article_board_order}")
                return []

            soupList = jres.get('researchList', [])
            logger.info(f"Kiwoom Scraper: Found {len(soupList)} articles for board {article_board_order}")
            
            articles = []
            for list_item in soupList:
                LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}'
                LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(list_item['rMenuGb'], list_item['attaFile'], list_item['makeDt'])
                LIST_ARTICLE_TITLE = list_item['titl']

                WRITER = list_item['workId']
                articles.append({
                    "sec_firm_order": sec_firm_order,
                    "article_board_order": article_board_order,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", list_item['makeDt']),
                    "DOWNLOAD_URL": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "TELEGRAM_URL": LIST_ARTICLE_URL,
                    "PDF_URL": LIST_ARTICLE_URL,
                    "KEY": LIST_ARTICLE_URL,
                    "SAVE_TIME": datetime.datetime.now().isoformat()
                })
            return articles
        except Exception as e:
            logger.error(f"Error scraping Kiwoom board {article_board_order}: {e}")
            return []
        finally:
            gc.collect()

    tasks = [fetch_data(TARGET_URL, idx) for idx, TARGET_URL in enumerate(TARGET_URL_TUPLE)]
    results = await asyncio.gather(*tasks)

    for result in results:
        json_data_list.extend(result)

    logger.info(f"Kiwoom Scraper: Found {len(json_data_list)} total articles")
    return json_data_list

if __name__ == "__main__":
    result = asyncio.run(Kiwoom_checkNewArticle(page_size=50))
    logger.info(f"Total articles fetched: {len(result)}")
