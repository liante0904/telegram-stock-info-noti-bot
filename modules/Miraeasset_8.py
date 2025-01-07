# -*- coding:utf-8 -*- 
import os
import gc
import requests
import re
from datetime import datetime

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper

def Miraeasset_checkNewArticle():
    SEC_FIRM_ORDER      = 8
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 미래에셋 Daily
    TARGET_URL_0 =  "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        
        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        soup = scraper.Get()

        # 첫 번째 레코드의 제목을 바로 담습니다.
        soupList = soup.select("tbody tr")[2:]  # 타이틀 제거

        for list in soupList:
            # print(list)
            # print(list.select_one("td:nth-child(1)").get_text(strip=True))
            # print(list.select_one("td:nth-child(2)").get_text(strip=True))
            # print(list.select_one("td:nth-child(3)").get_text(strip=True))
            # print(list.select_one("td:nth-child(4)").get_text(strip=True))
            
            REG_DT = list.select_one("td:nth-child(1)").get_text(strip=True) # 날짜
            REG_DT = re.sub(r"[-./]", "", REG_DT) # 날짜 포맷 정리
            
            LIST_ARTICLE_TITLE = list.select_one("td:nth-child(2)").get_text(strip=True) # 제목
            WRITER = list.select_one("td:nth-child(4)").get_text(strip=True) # 작성자
            
            LIST_ARTICLE_URL = "없음"
            DOWNLOAD_URL = "없음"  # 기본값 설정
            attachment_element = list.select_one(".bbsList_layer_icon a")
            if attachment_element:
                LIST_ARTICLE_URL = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"]).group(1)
                # ATTACH_URL = LIST_ARTICLE_URL
                LIST_ARTICLE_TITLE = list.select_one(".subject a").find_all(string=True)
                LIST_ARTICLE_TITLE = " : ".join(LIST_ARTICLE_TITLE)
                DOWNLOAD_URL = LIST_ARTICLE_URL  # attachment_element가 있을 때만 갱신


            json_data_list.append({
                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                "FIRM_NM": firm_info.get_firm_name(),
                "REG_DT": REG_DT,
                "WRITER": WRITER,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "TELEGRAM_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            # print(json_data_list)

            

    # 메모리 정리
    del soup
    gc.collect()

    return json_data_list
Miraeasset_checkNewArticle()