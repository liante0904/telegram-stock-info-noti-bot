from loguru import logger
# -*- coding:utf-8 -*- 
import gc
import requests
import re
from datetime import datetime

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper
from models.ConfigManager import config

def TOSSinvest_checkNewArticle():
    sec_firm_order      = 15
    article_board_order = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()
 
    TARGET_URL_TUPLE = config.get_urls("TOSSinvest_15")
    
    for article_board_order, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=sec_firm_order,
            article_board_order=article_board_order
        )

        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.GetJson()
        
        # HTML parse
        soupList = jres['result']['list']
        
        # logger.debug('*' *40)
        # logger.debug(soupList)
        
        # logger.debug('*' *40)
        
        nNewArticleCnt = 0
        for list in soupList:
            LIST_ARTICLE_TITLE = list['title']
            LIST_ARTICLE_URL   =  list['files'][0]['filePath']
            reg_dt = list['createdAt'].split("T")[0]
            json_data_list.append({
                "sec_firm_order":sec_firm_order,
                "article_board_order":article_board_order,
                "firm_nm":firm_info.get_firm_name(),
                "reg_dt": re.sub(r"[-./]", "", reg_dt),
                "download_url": LIST_ARTICLE_URL,
                "telegram_url": LIST_ARTICLE_URL,
                "article_title":LIST_ARTICLE_TITLE,
                "key":LIST_ARTICLE_URL,
                "save_time": datetime.now().isoformat()
            })
            
    # 메모리 정리
    del jres, soupList
    gc.collect()

    return json_data_list
