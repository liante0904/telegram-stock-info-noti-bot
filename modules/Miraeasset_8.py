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

        # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류

        # 게시물 정보 파싱
        for index, post in enumerate(soupList):
            #contents > table > tbody > tr:nth-child(2) > 
            

            if index == 0:  # 첫 번째 레코드는 이미 처리했으므로 건너뜁니다.
                continue
            title_element = post.select_one(".subject a")
            if not title_element:  # 제목 요소가 없는 경우
                continue  # 건너뜁니다.
            title = title_element.get_text()  # strip 제거
            attachment_element = post.select_one(".bbsList_layer_icon a")
            attachment_link = "없음"
            if attachment_element:
                attachment_link = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"]).group(1)
            # print("제목:", title)
            # print("첨부 파일:", attachment_link)
            # print()



        nNewArticleCnt = 0
        for list in soupList:

            LIST_ARTICLE_TITLE = list.select_one(".subject a").text
            LIST_ARTICLE_URL = "없음"
            DOWNLOAD_URL = "없음"  # 기본값 설정
            attachment_element = list.select_one(".bbsList_layer_icon a")
            if attachment_element:
                LIST_ARTICLE_URL = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"]).group(1)
                # ATTACH_URL = LIST_ARTICLE_URL
                LIST_ARTICLE_TITLE = list.select_one(".subject a").find_all(string=True)
                LIST_ARTICLE_TITLE = " : ".join(LIST_ARTICLE_TITLE)
                DOWNLOAD_URL = LIST_ARTICLE_URL  # attachment_element가 있을 때만 갱신

            REG_DT = list.select_one("td:nth-child(1)").get_text(strip=True)
            REG_DT = re.sub(r"[-./]", "", REG_DT)
            json_data_list.append({
                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                "FIRM_NM": firm_info.get_firm_name(),
                "REG_DT": REG_DT,
                "ATTACH_URL": LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "TELEGRAM_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })

            

    # 메모리 정리
    del soup
    gc.collect()

    return json_data_list
Miraeasset_checkNewArticle()