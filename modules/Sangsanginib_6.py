# -*- coding:utf-8 -*- 
import os
import gc
import requests
import json
import re
from datetime import datetime

from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo

def Sangsanginib_checkNewArticle():
    SEC_FIRM_ORDER      = 6
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 상상인증권 투자전략
    TARGET_URL_0 =  "https://www.sangsanginib.com/notice/getNoticeList"
    # 상상인증권 산업 리포트
    TARGET_URL_1 =  TARGET_URL_0
    # 상상인증권 기업 리포트
    TARGET_URL_2 =  TARGET_URL_0
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        jres = ''
        # 요청 헤더 설정
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ko",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.sangsanginib.com",
            "Referer": "https://www.sangsanginib.com",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        }

        cmsCd = ["CM0078","CM0338","CM0079"]
        
        data = {
            "pageNum": "1",
            "src": "all",
            "cmsCd": cmsCd[ARTICLE_BOARD_ORDER],
            "rowNum": "10",
            "startRow": "0",
            "sdt": "",
            "edt": ""
        }
        # 쿠키 설정 (사전 형태로 쿠키 추가)
        cookies = {
            "SSISTOCK_JSESSIONID": "F63EB7BB0166E9ECA5988FF541287E07",
            "_ga": "GA1.1.467249692.1728208332",
            "_ga_BTXL5GSB67": "GS1.1.1728208331.1.1.1728208338.53.0.0"
        }
        # 세션 객체 생성
        session = requests.Session()

        # Retry 설정 (5번까지 재시도, backoff_factor는 재시도 간 대기 시간을 설정)
        retries = Retry(total=10, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])

        # HTTPAdapter에 Retry 설정 적용
        adapter = HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        try:
            response = session.post(TARGET_URL, headers=headers, data=data, timeout=2, cookies=cookies)
            # print(response.text)
            jres = json.loads(response.text)
            # print(jres)
        except requests.exceptions.RequestException as e:
            print(f"재시도 후에도 에러가 발생했습니다: {e}")
            return 0
        
        soupList = jres[0]['getNoticeList']
        
        nNewArticleCnt = 0
        
        # JSON To List
        for list in soupList:
            # {
            #     "REGDT": "2024.10.14",
            #     "STOCK_NM": "팬오션",
            #     "FILE_YN": "Y",
            #     "NM": "리서치센터",
            #     "NT_NO": 3683,
            #     "HIT": 42,
            #     "STAR_YN": "N",
            #     "STOCK_CD": "028670",
            #     "TITLE": "팬오션(028670):인내가 필요한 시기"
            # }
            
            #  URL 예제 : https://www.sangsanginib.com/_upload/attFile/CM0079/CM0079_3680_1.pdf
            # LIST_ARTICLE_URL = Sangsanginib_detail(NT_NO=list['NT_NO'], CMS_CD=cmsCd[ARTICLE_BOARD_ORDER])
            REG_DT              = re.sub(r"[-./]", "", list['REGDT'])
            LIST_ARTICLE_URL = f"https://www.sangsanginib.com/_upload/attFile/{cmsCd[ARTICLE_BOARD_ORDER]}/{cmsCd[ARTICLE_BOARD_ORDER]}_{list['NT_NO']}_1.pdf"
            LIST_ARTICLE_TITLE = list['TITLE']
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":REG_DT,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": LIST_ARTICLE_URL,
                "KEY":LIST_ARTICLE_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soupList
    del response
    gc.collect()

    return json_data_list
