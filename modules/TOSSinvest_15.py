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

def TOSSinvest_checkNewArticle():
    SEC_FIRM_ORDER      = 15
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()
 
    # 다올투자증권 산업분석
    TARGET_URL_0  = 'https://docs-api.tossinvest.com/api/v1/post/search?categoryId=138&searchTitleKeyword=&page=0&size=10&type=INVESTMENT_INFO'

    TARGET_URL_TUPLE = (TARGET_URL_0,)
    
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.GetJson()
        
        # HTML parse
        soupList = jres['result']['list']
        
        # print('*' *40)
        # print(soupList)
        
        # print('*' *40)
        
        nNewArticleCnt = 0
        for list in soupList:
            LIST_ARTICLE_TITLE = list['title']
            LIST_ARTICLE_URL   =  list['files'][0]['filePath']
            REG_DT = list['createdAt'].split("T")[0]
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT": re.sub(r"[-./]", "", REG_DT),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": LIST_ARTICLE_URL,
                "TELEGRAM_URL": LIST_ARTICLE_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "KEY":LIST_ARTICLE_URL,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
    # 메모리 정리
    del jres, soupList
    gc.collect()

    return json_data_list
