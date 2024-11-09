# -*- coding:utf-8 -*- 
import os
import gc
import requests
from datetime import datetime

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper

def Leading_checkNewArticle():
    SEC_FIRM_ORDER      = 16
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 리딩투자증권 
    TARGET_URL_0 =  "http://www.leading.co.kr/board/EquityResearch/list"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        
        scraper = SyncWebScraper(TARGET_URL, firm_info)
        soup = scraper.Get()
        soupList = soup.select('#sub-container > div.table-wrap > table > tbody > tr')
        print('='*50)
        nNewArticleCnt = 0
        # soupList에서 게시물 정보 파싱
        for list in soupList:
            title_element = list.select_one("td.align-left a")  # 제목이 들어 있는 a 태그 선택
            if not title_element:  # 제목 요소가 없는 경우
                continue  # 건너뜁니다.
            title = title_element.get_text(strip=True)  # 제목 텍스트 추출 (공백 제거)
            
            # 리서치 파일 첨부 링크 파싱
            attachment_element = list.select_one("td:nth-child(4) > a")  # 'file-icon' 클래스를 가진 a 태그 선택 (리서치 File)
            attachment_link = "없음"
            if attachment_element and 'href' in attachment_element.attrs:
                attachment_link =  f"http://www.leading.co.kr{attachment_element['href']}"  # 상대 경로를 절대 경로로 변환
            
            # 결과 출력
            # print("제목:", title)
            # print("첨부 파일:", attachment_link)
            print()
            LIST_ARTICLE_TITLE = title
            LIST_ARTICLE_URL = attachment_link
            DOWNLOAD_URL     = attachment_link
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                # # "REG_DT":REG_DT,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
            
    # 메모리 정리
    del soupList, list
    gc.collect()

    return json_data_list
