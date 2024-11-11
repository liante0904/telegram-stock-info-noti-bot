# -*- coding:utf-8 -*- 
import os
import gc
import requests
import urllib.parse as urlparse
from datetime import datetime

from bs4 import BeautifulSoup
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from utils.date_util import GetCurrentDate

def DAOL_checkNewArticle():
    SEC_FIRM_ORDER      = 14
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()
 
    # 다올투자증권 산업분석
    TARGET_URL_0  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I01&web=0'
    TARGET_URL_1  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I02&web=0'  
    TARGET_URL_2  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I03&web=0'  
    TARGET_URL_3  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I04&web=0'  
    TARGET_URL_4  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I05&web=0'  
    TARGET_URL_5  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I06&web=0'  
    TARGET_URL_6  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I07&web=0'  
    TARGET_URL_7  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I08&web=0' 
    TARGET_URL_8  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=S01&sctrGubun=S02&web=0' 
    TARGET_URL_9  = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=S01&sctrGubun=S03&web=0' 
    TARGET_URL_10 = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=S01&sctrGubun=S04&web=0' 
    TARGET_URL_11 = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=S01&sctrGubun=S05&web=0' 
    TARGET_URL_12 = 'https://www.daolsecurities.com/research/article/common.jspx?rGubun=S01&sctrGubun=S06&web=0' 

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6
                        , TARGET_URL_7, TARGET_URL_8, TARGET_URL_9, TARGET_URL_10, TARGET_URL_11,TARGET_URL_12)
    
    
    
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        # URL GET
        # URL을 파싱하여 주소와 쿼리 파라미터를 추출
        parsed_url = urlparse.urlparse(TARGET_URL)

        # 쿼리 파라미터를 딕셔너리로 파싱
        query_params = urlparse.parse_qs(parsed_url.query)

        BASE_URL = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path 
        TARGET_URL = BASE_URL + '?cmd=list&templet-bypass=true'
        # print('parsed_url:', parsed_url)
        # print('BASE_URL:', BASE_URL)
        # print('TARGET_URL:',TARGET_URL)
        # # 파라미터 출력
        # print("rGubun:", query_params.get('rGubun'))
        # print("sctrGubun:", query_params.get('sctrGubun'))
        # print("web:", query_params.get('web'))

        # 헤더 설정
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Host': 'www.daolsecurities.com',
            'Origin': 'https://www.daolsecurities.com',
            'Referer': BASE_URL,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }

        # form data 설정
        form_data = {
            'curPage': '1',
            'bbSeq': '',
            'rGubun': query_params.get('rGubun'),
            'sctrGubun': query_params.get('sctrGubun'),
            'web': query_params.get('web'),
            'hts':'',
            'filepath':'',
            'attaFileNm':'',
            'startDate': '2024/01/01',
            'endDate': GetCurrentDate("yyyy/mm/dd"),
            'searchSelect': '0',
            'searchNm1': '',
            'searchNm2': query_params.get('rGubun')
        }

        # POST 요청 보내기
        response = requests.post(TARGET_URL, data=form_data, headers=headers)
        # HTML parse
        soup = BeautifulSoup(response.content, "html.parser")
        soupList = soup.select('tr')        
        
        # print('*' *40)

        # 응답 처리
        if response.status_code != 200:
            print("요청이 실패했습니다.")
            print("상태 코드:", response.status_code)
        
        nNewArticleCnt = 0
        
        for list in soupList:
            cells = list.select('td')
            if len(cells) < 3:
                continue  # 필요한 데이터가 없는 경우 무시

            # REG_DT 추출 및 변환
            reg_date = cells[0].get_text(strip=True)
            REG_DT = reg_date.replace('/', '')  # YYYYMMDD 형식으로 변환

            # 작성자 정보
            WRITER = cells[4].get_text(strip=True)

            # ARTICLE_TITLE 및 ARTICLE_URL 추출
            article_link = cells[1].select_one('a.del_w')
            if not article_link:
                continue  # 링크가 없는 경우 무시

            LIST_ARTICLE_TITLE = article_link['title']
            if "Coverage 제외" in LIST_ARTICLE_TITLE:
                print("Coverage 제외는 발송 제외")
                continue
                
            LIST_ARTICLE_URL = article_link['href']

            # URL 분할
            parts = LIST_ARTICLE_URL.split(',')
            if len(parts) != 3:
                print("잘못된 입력 형식입니다.")
                continue

            path = parts[0].split("'")[1]
            filename = parts[1].split("'")[1]
            research_id = parts[2].split(")")[0]

            LIST_ARTICLE_URL = f"https://www.ktb.co.kr/common/download.jspx?cmd=viewPDF&path={path}/{filename}"
            DOWNLOAD_URL = LIST_ARTICLE_URL

            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":REG_DT,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": LIST_ARTICLE_URL,
                "TELEGRAM_URL": LIST_ARTICLE_URL,
                "KEY": LIST_ARTICLE_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "WRITER": WRITER,
                "SAVE_TIME": datetime.now().isoformat()
            })

    # 메모리 정리
    del soup, soupList
    del response
    gc.collect()

    return json_data_list