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

def ShinHanInvest_checkNewArticle(cur_page=1, single_page_only=True):
    SEC_FIRM_ORDER = 1
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 신한증권 국내산업분석
    TARGET_URL_0 = 'giindustry'
    
    # 신한증권 국내기업분석
    TARGET_URL_1 = 'gicompanyanalyst'

    # 신한증권 국내스몰캡
    TARGET_URL_2 = 'giresearchIPO'
    
    # 신한증권 해외주식
    TARGET_URL_3 = 'foreignstock'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        # 변동되는 파라미터 
        board_name = TARGET_URL
        param1 = "Q1"
        param2 = "+"
        param3 = ""
        param5 = "Q"
        param6 = 99999
        param7 = ""
        type_param = "bbs2"
        base_url = "https://open2.shinhaninvest.com/phone/asset/module/getbbsdata.jsp"

        while True:
            # URL 구성
            TARGET_URL = (f"{base_url}?url=/mobile/json.list.do?boardName={board_name}&curPage={cur_page}"
                f"&param1={param1}&param2={param2}&param3={param3}&param4=/mobile/json.list.do?boardName={board_name}&curPage={cur_page}"
                f"&param5={param5}&param6={param6}&param7={param7}&type={type_param}")


            scraper = SyncWebScraper(TARGET_URL, firm_info)
            
            # HTML parse
            jres = scraper.GetJson()
            print(f"Calling URL: {TARGET_URL}")
            
            soupList = jres['list']
            if not soupList:
                break

            # JSON To List
            for list in soupList:
                REG_DT = list['f0']
                REG_DT = re.sub(r"[-./]", "", REG_DT)
                LIST_ARTICLE_TITLE = list['f1']
                LIST_ARTICLE_URL = list['f3']
                WRITER = list['f5']

                try:
                    LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('shinhaninvest.com', 'shinhansec.com')
                    LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('/board/message/file.do?', '/board/message/file.pdf.do?')
                except Exception as e:
                    print("에러 발생:", e)
                    LIST_ARTICLE_URL = list['f3']
                
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": REG_DT,
                    "ATTACH_URL": LIST_ARTICLE_URL,
                    "DOWNLOAD_URL": LIST_ARTICLE_URL,
                    "TELEGRAM_URL": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "KEY:": LIST_ARTICLE_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                })
                # print(json_data_list)

            # 다음 페이지로 이동
            if single_page_only:
                break
            cur_page += 1
        
        # 메모리 정리
        del scraper
        gc.collect()

    return json_data_list

if __name__ == "__main__":
    r = ShinHanInvest_checkNewArticle(cur_page=100, single_page_only=False)
    print(r)
