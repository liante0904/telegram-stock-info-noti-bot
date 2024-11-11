# -*- coding:utf-8 -*- 
import os
import gc
import requests
import re
import asyncio
from datetime import datetime

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper  # Assuming there is an async version of the scraper
from models.SQLiteManager import SQLiteManager
from utils.date_util import GetCurrentDate

def get_start_of_year():
    return datetime(datetime.now().year, 1, 1).strftime("%Y%m%d")

async def Kiwoom_checkNewArticle(stdate=None, eddate=None, page_size=100):
    if stdate is None:
        stdate = get_start_of_year()
    if eddate is None:
        eddate = GetCurrentDate("yyyymmdd")

    SEC_FIRM_ORDER = 10
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # Kiwoom Securities analysis URLs
    TARGET_URL_0 = 'https://bbn.kiwoom.com/research/SResearchCRListAjax'
    TARGET_URL_1 = 'https://bbn.kiwoom.com/research/SResearchCIListAjax'
    TARGET_URL_2 = 'https://bbn.kiwoom.com/research/SResearchSNListAjax'
    TARGET_URL_3 = 'https://bbn.kiwoom.com/research/SResearchCCListAjax'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3)

    async def fetch_data(TARGET_URL, ARTICLE_BOARD_ORDER):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

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
        jres = await scraper.PostJson(params=payload)

        if jres['totalCount'] == 0:
            return []

        soupList = jres['researchList']
        articles = []

        # JSON To List
        for list_item in soupList:
            LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}'
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(list_item['rMenuGb'], list_item['attaFile'], list_item['makeDt'])
            LIST_ARTICLE_TITLE = list_item['titl']

            WRITER = list_item['workId']
            articles.append({
                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                "FIRM_NM": firm_info.get_firm_name(),
                "REG_DT": re.sub(r"[-./]", "", list_item['makeDt']),
                "ATTACH_URL": LIST_ARTICLE_URL,
                "DOWNLOAD_URL": LIST_ARTICLE_URL,
                "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                "WRITER": WRITER,
                "TELEGRAM_URL": LIST_ARTICLE_URL,
                "SAVE_TIME": datetime.now().isoformat()
            })

        # Clean up memory
        del soupList
        gc.collect()

        return articles

    tasks = [fetch_data(TARGET_URL, ARTICLE_BOARD_ORDER) for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE)]
    results = await asyncio.gather(*tasks)

    for result in results:
        json_data_list.extend(result)

    return json_data_list

if __name__ == "__main__":
    # Main function to set parameters
    stdate = None  # Default to system year start if None
    eddate = None  # Default to system date if None
    page_size = 100000  # Default value

    # Run the async function with specified parameters
    result = asyncio.run(Kiwoom_checkNewArticle(stdate, eddate, page_size))
    print(result)
    
    if not result:
        print("No articles found.")
    else:
        db = SQLiteManager()
        inserted_count = db.insert_json_data_list(result, 'data_main_daily_send')
        print(f"Inserted {inserted_count} articles.")
