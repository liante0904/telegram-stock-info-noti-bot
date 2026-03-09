# -*- coding:utf-8 -*- 
import gc
import requests
import re
from datetime import datetime
import os
import sys
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper
from models.SQLiteManager import SQLiteManager

def ShinHanInvest_checkNewArticle_back(cur_page=1, single_page_only=True):
    SEC_FIRM_ORDER = 1
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    if cur_page is None:
        cur_page = 1
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
            # print(jres)
            print(f"Calling URL: {TARGET_URL}")
            
            # title_map에서 동적으로 키 매핑
            title_map = {v: k for k, v in jres['title'].items()}  # 키-값을 역으로 매핑
            print(title_map)
            reg_dt_key = title_map.get('등록일', '')  # 등록일 키
            title_key = title_map.get('제목', '')  # 제목 키
            url_key = title_map.get('파일명', '')  # 파일명 키
            

            # 작성자 또는 애널리스트 키 매핑
            writer_key = title_map.get('작성자', '') or title_map.get('애널리스트', '')  # 작성자 또는 애널리스트 키

            soupList = jres['list']
            if not soupList:
                break

            # JSON To List
            for item in soupList:
                REG_DT = item.get(reg_dt_key, '')  # 등록일
                if REG_DT:
                    REG_DT = re.sub(r"[-./]", "", REG_DT).replace(";", "")
                LIST_ARTICLE_TITLE = item.get(title_key, '')  # 제목
                LIST_ARTICLE_URL = item.get(url_key, '')  # 파일명
                WRITER = item.get(writer_key, '')  # 작성자

                try:
                    LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('shinhaninvest.com', 'shinhansec.com')
                    LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('/board/message/file.do?', '/board/message/file.pdf.do?')
                except Exception as e:
                    print("에러 발생:", e)
                    LIST_ARTICLE_URL = item.get(url_key, '')
                
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": REG_DT,
                    "ATTACH_URL": ' ',
                    "DOWNLOAD_URL": LIST_ARTICLE_URL,
                    "TELEGRAM_URL": LIST_ARTICLE_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "WRITER": WRITER,
                    "KEY:": LIST_ARTICLE_URL,
                    "SAVE_TIME": datetime.now().isoformat()
                })

            # 다음 페이지로 이동
            if single_page_only:
                break
            cur_page += 1
        
        # 메모리 정리
        del scraper
        gc.collect()

    return json_data_list


board_map = {
    'giindustry': 0,        # 산업분석
    'gicompanyanalyst': 1,  # 기업분석
    'giresearchIPO': 2,     # 스몰캡
    'foreignstock': 3,      # 해외 주식
    'alternative': 4,       # 대체투자
    'foreignbond': 5,       # 해외 채권
    'gibond': 6,            # 채권/신용분석
    'gicomment': 7,         # 주식전략/시황
    'gieconomy': 8,         # 경제
    'gifuture': 9,          # 기술적분석/파생시황
    'gigoodpolio': 10,      # 주식 포트폴리오
    'giperiodicaldaily': 11,# Daily 신한생각
    'issuebroker': 12,      # 의무리포트
    'shinhannews': 13,      # 신한 속보
}

def ShinHanInvest_checkNewArticle():
    SEC_FIRM_ORDER = 1
    json_data_list = []
    
    url = "https://www.shinhansec.com/siw/etc/browse/search05/data.do?v=1759052893640"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Priority": "u=0",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    data = {
        "header": {
            "TCD": "S",
            "SDT": datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3],
            "SVW": "/siw/insights/research/list/view-popup.do"
        },
        "body": {
            "startCount": 0,
            "listCount": 10000,
            "query": "",
            "searchType": "A",
            "boardCode": ""
        }
    }

    with requests.Session() as session:
        response = session.post(url, headers=headers, data=json.dumps(data))

        if response.ok:
            result = response.json()
            
            firm_info = FirmInfo(sec_firm_order=SEC_FIRM_ORDER, article_board_order=0) # Dummy board order

            collectionList = result.get('body', {}).get('collectionList', [])
            for collection in collectionList:
                # print(collection)
                itemList = collection.get('itemList', [])
                for item in itemList:
                    board_name = item.get('BOARD_NAME', '')
                    
                    article_board_order = board_map.get(board_name, 99)

                    reg_dt = item.get('REG_DT', '')[0:8]
                    if reg_dt:
                        reg_dt = re.sub(r"[-./]", "", reg_dt)

                    attachment_id = item.get('ATTACHMENT_ID', '')
                    
                    download_url = f"https://bbs2.shinhansec.com/board/message/file.pdf.do?attachmentId={attachment_id}"
                                    
                    json_data_list.append({
                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER": article_board_order,
                        "FIRM_NM": firm_info.get_firm_name(),
                        "REG_DT": reg_dt,
                        "ATTACH_URL": ' ',
                        "DOWNLOAD_URL": download_url,
                        "TELEGRAM_URL": download_url,
                        "ARTICLE_TITLE": item.get('TITLE', ''),
                        "WRITER": item.get('REGISTER_NICKNAME', ''),
                        "KEY": download_url,
                        "SAVE_TIME": datetime.now().isoformat()
                    })
            return json_data_list
        else:
            print("Request failed:", response.status_code)
            return []

def get_shinhan_board_info():
    """
    Fetches data from Shinhan Invest API and prints a unique list of
    BOARD_NAME and BOARD_TITLE pairs.
    """
    url = "https://www.shinhansec.com/siw/etc/browse/search05/data.do?v=1759052893640"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:142.0) Gecko/20100101 Firefox/142.0",
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Priority": "u=0",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    data = {
        "header": {
            "TCD": "S",
            "SDT": datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3],
            "SVW": "/siw/insights/research/list/view-popup.do"
        },
        "body": {
            "startCount": 0,
            "listCount": 10000,
            "query": "",
            "searchType": "A",
            "boardCode": ""
        }
    }

    board_info = set()

    with requests.Session() as session:
        response = session.post(url, headers=headers, data=json.dumps(data))

        if response.ok:
            result = response.json()
            
            collectionList = result.get('body', {}).get('collectionList', [])
            for collection in collectionList:
                itemList = collection.get('itemList', [])
                for item in itemList:
                    board_name = item.get('BOARD_NAME', 'N/A')
                    board_title = item.get('BOARD_TITLE', 'N/A')
                    board_info.add((board_name, board_title))
            
            print("Found Board Information:")
            for name, title in sorted(list(board_info)):
                print(f'BOARD_NAME: "{name}", BOARD_TITLE: "{title}"')

        else:
            print("Request failed:", response.status_code)

if __name__ == "__main__":
    firm_info = FirmInfo(sec_firm_order=1, article_board_order=0)
    # results = ShinHanInvest_checkNewArticle(cur_page=1, single_page_only=True)
    results = ShinHanInvest_checkNewArticle()
    # print(results)
    print(f"Fetched {len(results)} articles from .", firm_info.get_firm_name())
    # print(results)

    db = SQLiteManager()
    inserted_count_results = db.insert_json_data_list(results, 'data_main_daily_send')

    print(f"Articles Inserted: {inserted_count_results}")

