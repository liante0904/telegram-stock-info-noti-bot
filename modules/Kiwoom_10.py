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
from utils.date_util import GetCurrentDate

def Kiwoom_checkNewArticle():
    SEC_FIRM_ORDER      = 10
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 키움증권 기업 분석
    TARGET_URL_0 =  'https://bbn.kiwoom.com/research/SResearchCRListAjax'
    # 키움증권 산업 분석
    TARGET_URL_1 =  'https://bbn.kiwoom.com/research/SResearchCIListAjax'
    # 키움증권 스팟 노트
    TARGET_URL_2 =  'https://bbn.kiwoom.com/research/SResearchSNListAjax'
    # 키움증권 미국/선진국
    TARGET_URL_3 =  'https://bbn.kiwoom.com/research/SResearchCCListAjax'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1,TARGET_URL_2, TARGET_URL_3)

    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        payload = {
            "pageNo": 1,
            "pageSize": 10,
            "stdate": '20231023',
            "eddate": GetCurrentDate("yyyymmdd"),
            "f_keyField": '', 
            "f_key": '',
            "_reqAgent": 'ajax',
            "dummyVal": 0
        }

        scraper = SyncWebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.PostJson(params=payload)
            
        if jres['totalCount'] == 0 : return 0

        # print(jres['researchList'])
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        
        soupList = jres['researchList']

        nNewArticleCnt = 0
        
        # JSON To List
        for list in soupList:
            # {'pageNo': None, 'pageSize': 15, 'totalCount': None, 'startRow': None, 'endRow': None, 'f_key': None, 'f_keyField': None, 'rnum': 0, 'sqno': 5153, 'titl': '키움 음식료 Weekly (10/21)', 'expl': '위클리', 'workId': '박상준 외1명', 'workEmail': None, 'readCnt': 320, 'makeDt': '2024.10.21', 'attaFile': '1729407876549.pdf', 'attaFileName': 'Kiwoom FB Weekly_241021.pdf', 'ivstOpin': None, 'wingsSqno': None, 'relItemList': None, 'tpobNm': '음식료', 'contL': None, 'itemNm': None, 'fseCdList': None, 'workIdList': None, 'today': None, 'stdate': None, 'eddate': None, 'isNew': 'N', 'brodId': None, 'fnGb': None, 'isScrap': 'N', 'prevSqno': 0, 'nextSqno': 0, 'prevTitl': None, 'nextTitl': None, 'prevMakeDt': None, 'nextMakeDt': None, 'no': 9, 'rSqno': 4147159, 'rMenuGb': 'CI', 'rMenuGbNm': '산업분석'}

            # print(list)
            # 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb=CR&attaFile=1650493541463.pdf&makeDt=2022.04.21'
            LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}' 
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(list['rMenuGb'],  list['attaFile'], list['makeDt'])
            LIST_ARTICLE_TITLE = list['titl']

            WRITER = list['workId']
            # print(list)
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", list['makeDt']),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": LIST_ARTICLE_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "WRITER": WRITER,
                "TELEGRAM_URL": LIST_ARTICLE_URL,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soupList
    gc.collect()

    return json_data_list
