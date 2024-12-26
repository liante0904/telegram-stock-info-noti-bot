# -*- coding:utf-8 -*- 
import gc
import requests
from datetime import datetime

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper

def Samsung_checkNewArticle():
    SEC_FIRM_ORDER      = 5
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 삼성증권 기업 분석
    TARGET_URL_0 =  'https://www.samsungpop.com/mbw/search/search.do?cmd=report_search&startCount=0&TOTALVIEWCOUNT=30&range=A&writer=&NUM=&GBNM=&GBNS=&JDATE=&JTIME=&COMPONENTCD=&moreCheck=N&GUBUN=company1&searchField=TITLE&periodType=1&query='
    # 삼성증권 산업 분석
    TARGET_URL_1 =  'https://www.samsungpop.com/mbw/search/search.do?cmd=report_search&startCount=0&TOTALVIEWCOUNT=30&range=A&writer=&NUM=&GBNM=&GBNS=&JDATE=&JTIME=&COMPONENTCD=&moreCheck=N&GUBUN=industry1&searchField=TITLE&periodType=1&query='
    # 삼성증권 해외 분석
    TARGET_URL_2 =  'https://www.samsungpop.com/mbw/search/search.do?cmd=report_search&startCount=0&TOTALVIEWCOUNT=30&range=A&writer=&NUM=&GBNM=&GBNS=&JDATE=&JTIME=&COMPONENTCD=&moreCheck=N&GUBUN=company2&searchField=TITLE&periodType=1&query='
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        soup = scraper.Get()

        soupList = soup.select('#content > section.bbsLstWrap > ul > li')
        # print(soupList)

        # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류

        nNewArticleCnt = 0
        
        for list in soupList:
            LIST_ARTICLE_TITLE = list.select_one('#content > section.bbsLstWrap > ul > li > a > dl > dt > strong').text
            
            a_href = list.select_one('#content > section.bbsLstWrap > ul > li > a').attrs['href']
            
            # 기존 URL 형식 유지
            a_href = a_href.replace('javascript:downloadPdf(', '').replace(';', '')
            a_href_parts = a_href.split("'")
            a_href_path = a_href_parts[1]  # PDF 파일 경로
            REG_DT = a_href_parts[3]       # REG_DT 값 추출

            LIST_ARTICLE_URL = 'https://www.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName=' + a_href_path + '&contentType=application/pdf&inlineYn=Y'

            # fileNameArray = a_href.split("/")
            # LIST_ATTACT_FILE_NAME = fileNameArray[1].strip()

            # 제목 가공
            LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("수정", "")
            LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find(")")+1:len(LIST_ARTICLE_TITLE)]
            DOWNLOAD_URL       = LIST_ARTICLE_URL
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":REG_DT,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "TELEGRAM_URL":LIST_ARTICLE_URL,
                "KEY":LIST_ARTICLE_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soup
    gc.collect()

    return json_data_list
