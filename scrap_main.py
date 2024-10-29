# -*- coding:utf-8 -*- 
import os
import gc
import logging
import requests
import time
import json
import re
import urllib.parse as urlparse
import urllib.request
import base64
import asyncio
import aiohttp
from datetime import datetime, timedelta, date

from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

from models.FirmInfo import FirmInfo
from models.WebScraper import WebScraper
from modules.imfnsec_18 import imfnsec_checkNewArticle
from package.json_to_sqlite import insert_json_data_list
from utils.date_util import GetCurrentDate, GetCurrentDate_NH

# selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import scrap_send_main
import scrap_upload_pdf
#################### global 변수 정리 ###################################
############공용 상수############

json_data_list = []

# 연속키용 상수
FIRST_ARTICLE_INDEX = 0
#################### global 변수 정리 끝###################################

def LS_checkNewArticle():
    SEC_FIRM_ORDER = 0
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 이슈브리프
    TARGET_URL_0 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=146'
    # 기업분석 게시판
    TARGET_URL_1 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=36'
    # 산업분석
    TARGET_URL_2 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=37'
    # 투자전략
    TARGET_URL_3 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=38'
    # Quant
    TARGET_URL_4 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=147'
    # Macro
    TARGET_URL_5 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=39'
    # FI/ Credit
    TARGET_URL_6 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=183'
    # Commodity
    TARGET_URL_7 = 'https://www.ls-sec.co.kr/EtwFrontBoard/List.jsp?board_no=145'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        scraper = WebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        soup = scraper.Get()

        soupList = soup.select('#contents > table > tbody > tr')
        
        # 현재 날짜
        today = date.today()
        # 7일 전 날짜 계산
        seven_days_ago = today - timedelta(days=7)

        nNewArticleCnt = 0        
        for list in soupList:
            # print(list)
            # 모든 td 태그 선택
            td_elements = list.select('td')
            # 작성자
            WRITER = td_elements[2].get_text().strip()
            # POST_DATE: 인덱스 3의 td 태그에서 날짜 추출
            REG_DT = td_elements[3].get_text().strip()
            # LIST_ARTICLE_TITLE 및 LIST_ARTICLE_URL: 인덱스 1의 td 태그에서 제목과 URL 추출
            link_tag = td_elements[1].select_one('a')  # 첫 번째 a 태그 선택
            if link_tag:
                LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + link_tag['href'].replace("amp;", "")
                LIST_ARTICLE_TITLE = link_tag.get_text().strip()
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]") + 1:].strip()  # 불필요한 부분 제거

            # 추출된 정보 출력 (또는 필요한 방식으로 활용)
            # print("URL:", LIST_ARTICLE_URL)
            # print("Title:", LIST_ARTICLE_TITLE)
            # print("Date:", REG_DT)
            # print('POST_DATE',POST_DATE)

            # POST_DATE를 datetime 형식으로 변환 (형식: yyyy.mm.dd)
            try:
                post_date_obj = datetime.strptime(REG_DT, '%Y.%m.%d').date()
            except ValueError as e:
                print(f"날짜 형식 오류: {REG_DT}, 오류: {e}")
                continue
            
            # REG_DT = post_date_obj.strftime('%Y%m%d')
            # print('post_date_obj',post_date_obj)
            # print('REG_DT:', REG_DT)
            # 7일 이내의 게시물만 처리
            if post_date_obj < seven_days_ago:
                print(f"게시물 날짜 {REG_DT}가 7일 이전이므로 중단합니다.")
                break
            
            
            item = LS_detail(LIST_ARTICLE_URL, REG_DT, firm_info)
            # print(item)
            if item:
                LIST_ARTICLE_URL = item['LIST_ARTICLE_URL']
                DOWNLOAD_URL     = item['LIST_ARTICLE_URL']
                LIST_ARTICLE_TITLE = item['LIST_ARTICLE_TITLE']
            
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", REG_DT),
                "WRITER": WRITER,
                "ARTICLE_URL":DOWNLOAD_URL,
                "ATTACH_URL":DOWNLOAD_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
            
    # 메모리 정리
    del soup
    gc.collect()
    return nNewArticleCnt

def LS_detail(TARGET_URL, str_date, firm_info):
    TARGET_URL = TARGET_URL.replace('&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1', '')
    item = {}  # 빈 딕셔너리로 초기화
    time.sleep(0.1)

    scraper = WebScraper(TARGET_URL, firm_info)
    
    # HTML parse
    soup = scraper.Get()

    # 게시글 제목
    trs = soup.select('tr')
    item['LIST_ARTICLE_TITLE'] = trs[0].select_one('td').text
    
    # 첨부파일 이름
    item['LIST_ARTICLE_FILE_NAME'] = soup.select_one('.attach > a').get_text()
    
    # 첨부파일 URL 조립 예시  
    # => https://www.ls-sec.co.kr/upload/EtwBoardData/B202410/20241002_한국 9월 소비자물가.pdf
    
    # B포스팅 월
    URL_PARAM = str_date
    URL_PARAM = URL_PARAM.split('.')
    URL_PARAM_0 = 'B' + URL_PARAM[0] + URL_PARAM[1]

    ATTACH_FILE_NAME = soup.select_one('.attach > a').get_text()
    ATTACH_URL_FILE_NAME = ATTACH_FILE_NAME.replace(' ', "%20").replace('[', '%5B').replace(']', '%5D').replace('%25', '%') 
    URL_PARAM_1 = urllib.parse.unquote(ATTACH_URL_FILE_NAME)

    
    ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
    ATTACH_URL = ATTACH_URL.format(URL_PARAM_0, URL_PARAM_1)
    
    # URL 인코딩 => 사파리 한글처리 
    item['LIST_ARTICLE_URL'] = urllib.parse.quote(ATTACH_URL, safe=':/')
    
    # item['LIST_ARTICLE_URL'] = ATTACH_URL
    # item['LIST_ARTICLE_FILE_NAME'] = LIST_ARTICLE_FILE_NAME
    # item['LIST_ARTICLE_TITLE'] = LIST_ARTICLE_TITLE
    # print(item)
    # print('*********확인용**************')
    return item
    

def ShinHanInvest_checkNewArticle():
    SEC_FIRM_ORDER      = 1
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 신한증권 국내산업분석
    TARGET_URL_0 = 'giindustry'
    
    # 신한증권 국내기업분석
    TARGET_URL_1 = 'gicompanyanalyst'

    # 신한증권 국내스몰캡
    TARGET_URL_2 = 'giresearchIPO'
    
    # 신한증권 해외주식
    TARGET_URL_3 = 'foreignstock'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1,TARGET_URL_2,TARGET_URL_3)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        # 변동되는 파라미터 
        board_name = TARGET_URL
        # 고정된 파라미터
        cur_page = 1
        param1 = "Q1"
        param2 = "+"
        param3 = ""
        param4 = f"/mobile/json.list.do?boardName={board_name}&curPage={cur_page}"
        param5 = "Q"
        param6 = 99999
        param7 = ""
        type_param = "bbs2"

        # URL 구성
        base_url = "https://open2.shinhaninvest.com/phone/asset/module/getbbsdata.jsp"
        TARGET_URL = (f"{base_url}?url=/mobile/json.list.do?boardName={board_name}&curPage={cur_page}"
            f"&param1={param1}&param2={param2}&param3={param3}&param4={param4}&param5={param5}"
            f"&param6={param6}&param7={param7}&type={type_param}")

        scraper = WebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.GetJson()

        soupList = jres['list']

        # JSON To List
        for list in soupList:
            # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
            # print(list)

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
            
            DOWNLOAD_URL = LIST_ARTICLE_URL
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":REG_DT,
                "WRITER":WRITER,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
    # 메모리 정리
    del scraper
    gc.collect()

    return json_data_list

def NHQV_checkNewArticle():
    SEC_FIRM_ORDER = 2
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # TARGET_URL =  'https://m.nhqv.com/research/newestBoardList'
    # NH투자증권 오늘의 레포트
    TARGET_URL =  'https://m.nhqv.com/research/commonTr.json'
    
    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    
    payload = {
        "trName": "H3211",
        "rshPprDruTmSt": "00000000",
        "rshPprDruDtSt": GetCurrentDate_NH(),
        "rshPprDruDtEd": GetCurrentDate_NH(),
        "rshPprNo": ""
    }
    
    r = ""
    i = 1
    listR = []
    while True:
        
        try:
            response = requests.post(TARGET_URL,
                                    headers={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                                             'Accept':'application/json, text/javascript, */*; q=0.01'},
                                    data=payload)
            # print(response.text)
            jres = json.loads(response.text)
            # print(jres)
            
        except:
            return 0
        
        nNewArticleCnt = int(jres['H3211']['H3211OutBlock1'][0]['iqrCnt'])
        if nNewArticleCnt == 0: return nNewArticleCnt
        strList = jres['H3211']['H3211OutBlock2']
        listR = listR + strList
        
        if nNewArticleCnt == 11: # 연속키 있음
            payload['rshPprNo'] = jres['H3211']['H3211OutBlock2'][nNewArticleCnt-1]['rshPprNo']
        
        if nNewArticleCnt < 11: break
        i = i +1
    # 크롤링 종료

    # 중복제거
    r = []
    for t in listR:
        if t not in r:
            r.append(t)
    
    soupList = r

    BOARD_NM            = listR[0]['rshPprSerCdNm']
   
    # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    # print('연속URL:', NXT_KEY) # 주소

    nNewArticleCnt = 0
    
    for list in soupList:
        # print(list)

        REG_DT              = list['rshPprDruDtNm']
        REG_DT              = re.sub(r"[-./]", "", REG_DT)
        WRITER              = list['rshPprDruEmpFnm']
        BOARD_NM            = list['rshPprSerCdNm']
        LIST_ARTICLE_TITLE = list['rshPprTilCts']
        LIST_ARTICLE_URL =  list['hpgeFleUrlCts']
        DOWNLOAD_URL    = LIST_ARTICLE_URL
        json_data_list.append({
            "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
            "FIRM_NM":firm_info.get_firm_name(),
            "REG_DT":REG_DT,
            "WRITER":WRITER,
            "ATTACH_URL":LIST_ARTICLE_URL,
            "DOWNLOAD_URL": DOWNLOAD_URL,
            "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
            "SAVE_TIME": datetime.now().isoformat()
        })
            
    # 메모리 정리
    del response
    gc.collect()

    return nNewArticleCnt

def HANA_checkNewArticle():
    SEC_FIRM_ORDER = 3
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = [
        # 하나금융 Daily
        'https://www.hanaw.com/main/research/research/list.cmd?pid=4&cid=1',
        # 하나금융 산업 분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=1',
        # 하나금융 기업 분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=2',
        # 하나금융 주식 전략
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=1',
        # 하나금융 Small Cap
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=3',
        # 하나금융 기업 메모
        'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=4',
        # 하나금융 Quant
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=2',
        # 하나금융 포트폴리오
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=3',
        # 하나금융 투자정보
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=4',
        # 글로벌 투자전략
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=1',
        # 글로벌 산업분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=2',
        # 글로벌 기업분석
        'https://www.hanaw.com/main/research/research/list.cmd?pid=8&cid=3'
    ]

    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        try:
            response = requests.get(TARGET_URL, verify=False)
            time.sleep(0.5)
        except:
            return 0

        # HTML parse
        soup = BeautifulSoup(response.content, "html.parser")
        soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

        nNewArticleCnt = 0
        
        for list in soupList:
            # print('=============')
            # print(list)

            # 제목과 URL 추출
            LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').text.strip()
            LIST_ARTICLE_URL = 'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5) > div > a').get('href')
            DOWNLOAD_URL = LIST_ARTICLE_URL

            # 작성일자와 작성자 추출
            REG_DT = list.select_one('li.mb7.m-info.info > span.txtbasic').text.strip()
            WRITER = list.select_one('li.mb7.m-info.info > span.none.m-name').text.strip()
            
            # 디버그 출력 (옵션)
            # print("Title:", LIST_ARTICLE_TITLE)
            # print("URL:", LIST_ARTICLE_URL)
            # print("Download URL:", DOWNLOAD_URL)
            # print("Date (REG_DT):", REG_DT)
            # print("Writer:", WRITER)
            
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", REG_DT),
                "WRITER":WRITER,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
                
    # 메모리 정리
    del soup
    del response
    gc.collect()

    return nNewArticleCnt

# JSON API 타입
def KB_checkNewArticle():
    SEC_FIRM_ORDER      = 4
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    
    # KB증권 오늘의 레포트
    TARGET_URL   = 'https://rc.kbsec.com/ajax/categoryReportList.json'
    
    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )

    # 요청 payload 데이터
    payload = {
        "pageNo": 1,
        "pageSize": 500,
        "registdateFrom": datetime(datetime.now().year, 1, 1).strftime("%Y%m%d"),
        "registdateTo": GetCurrentDate("YYYYMMDD"),
        "templateid": "",
        "lowTempId": "",
        "folderid": "", #"37,38,186",
        "callGbn": "RCLIST"
    }

    scraper = WebScraper(TARGET_URL, firm_info)
    
    # HTML parse
    jres = scraper.PostJson(json=payload)

    soupList = jres['response']['reportList']
    # print(soupList)
    
    nNewArticleCnt = 0
    
    # print(len(soupList))
    # JSON To List
    for list in soupList:

        REG_DT              = re.sub(r"[-./]", "", list['publicDate'])
        WRITER              = list['analystNm']
        LIST_ARTICLE_TITLE = list['docTitleSub']
        if list['docTitle'] not in list['docTitleSub'] : LIST_ARTICLE_TITLE = list['docTitle'] + " : " + list['docTitleSub']
        else: LIST_ARTICLE_TITLE = list['docTitleSub']
        LIST_ARTICLE_URL = f"http://rdata.kbsec.com/pdf_data/{list['documentid']}.pdf"
        DOWNLOAD_URL     = LIST_ARTICLE_URL
        json_data_list.append({
            "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
            "FIRM_NM":firm_info.get_firm_name(),
            "REG_DT":REG_DT,
            "WRITER":WRITER,
            "ATTACH_URL":LIST_ARTICLE_URL,
            "DOWNLOAD_URL": DOWNLOAD_URL,
            "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
            "SAVE_TIME": datetime.now().isoformat()
        })
    
    # 메모리 정리
    del soupList
    gc.collect()

    return nNewArticleCnt

# KB증권 암호화 해제
def KB_decode_url(url):
    """
    주어진 URL에서 id와 Base64로 인코딩된 url 값을 추출하고, 인코딩된 url 값을 디코딩하여 반환하는 함수

    Parameters:
    url (str): URL 문자열

    Returns:
    str: 추출된 id 값과 디코딩된 url 값을 포함한 문자열
    """
    url = url.replace('&amp;', '&')
    # URL 파싱
    parsed_url = urlparse.urlparse(url)
    
    # 쿼리 문자열 파싱
    query_params = urlparse.parse_qs(parsed_url.query)
    
    # id와 url 추출
    id_value = query_params.get('id', [None])[0]
    encoded_url = query_params.get('url', [None])[0]
    
    if id_value is None or encoded_url is None:
        print('Invalid URL: id or url is missing')
        return "Invalid URL: id or url is missing"
    
    # Base64 디코딩
    try:
        # '&amp;'를 '&'로 변환
        encoded_url = encoded_url.replace('&amp;', '&')
        decoded_url = base64.b64decode(encoded_url).decode('utf-8')
    except Exception as e:
        return f"Error decoding url: {e}"
    
    print(f"Extracted id: {id_value}, Decoded URL: {decoded_url}")
    return decoded_url

def Samsung_checkNewArticle():
    SEC_FIRM_ORDER = 5
    ARTICLE_BOARD_ORDER = 0

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

        scraper = WebScraper(TARGET_URL, firm_info)
        
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
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soup
    gc.collect()

    return nNewArticleCnt

def Sangsanginib_checkNewArticle():
    SEC_FIRM_ORDER = 6
    ARTICLE_BOARD_ORDER = 0

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
            DOWNLOAD_URL = LIST_ARTICLE_URL
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":REG_DT,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soupList
    del response
    gc.collect()

    return nNewArticleCnt

def Sangsanginib_detail(NT_NO, CMS_CD):
    ntNo = NT_NO
    cmsCd = CMS_CD
    # print('Sangsanginib_detail***********************')
    url = "https://www.sangsanginib.com/notice/getNoticeDetail"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }

    data = {
        "pageNum": "1",
        "src": "all",
        "cmsCd": cmsCd,
        "rowNum": "10",
        "startRow": "0",
        "sdt": "",
        "edt": "",
        "ntNo": ntNo
    }

    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        print("Failed to fetch data.")
    
    jres = json.loads(response.text)
    jres = jres['file'][0] #PDF
    
    # https://www.sangsanginib.com/common/fileDownload?cmsCd=CM0078&ntNo=4315&fNo=1&fNm=%5BSangSangIn%5D2022038_428.pdf

    # 기본 URL과 쿼리 매개변수 딕셔너리
    base_url = 'https://www.sangsanginib.com/common/fileDownload'
    params = {
        'cmsCd': jres['CMS_CD'],
        'ntNo': jres['NT_NO'],
        'fNo': jres['FNO'], # PDF
        'fNm': jres['FNM']
    }
    # print(params)
    url = base_url
    if params:
        # print('urlparse(params)', urlparse.urlencode(params))
        encoded_params = urlparse.urlencode(params)  # 쿼리 매개변수를 인코딩
        url += '?' + encoded_params
    
    print(url)
    return url

def Shinyoung_checkNewArticle():
    SEC_FIRM_ORDER = 7
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 신영증권 리서치
    TARGET_URL = "https://www.shinyoung.com/Common/selectPaging/research_shinyoungData"

    
    # url = "https://www.shinyoung.com/Common/selectPaging/research_shinyoungData"
    
    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )

    # POST 요청을 보낼 데이터
    payload = {
        "KEYWORD": "",
        "rows": "50",
        "page": "1"
    }

    scraper = WebScraper(TARGET_URL, firm_info)
    
    # HTML parse
    jres = scraper.PostJson(params=payload)

    # print(jres['rows'])
    soupList = jres['rows']
    
    nNewArticleCnt = 0
    
    # JSON To List
    for list in soupList:
        # print('list***************** \n',list)
        
        REG_DT              = re.sub(r"[-./]", "", list['APPDATE'])
        WRITER              = list['EMPNM']
        # print('NT_NO=',list['NT_NO'], 'CMS_CD=',cmsCd[ARTICLE_BOARD_ORDER])
        LIST_ARTICLE_URL = Shinyoung_detail(SEQ=list['SEQ'], BBSNO=list['BBSNO'])
        LIST_ARTICLE_TITLE = list['TITLE']
        DOWNLOAD_URL = LIST_ARTICLE_URL
        json_data_list.append({
            "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
            "FIRM_NM":firm_info.get_firm_name(),
            "REG_DT":REG_DT,
            "WRITER":WRITER,
            "ATTACH_URL":LIST_ARTICLE_URL,
            "DOWNLOAD_URL": DOWNLOAD_URL,
            "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
            "SAVE_TIME": datetime.now().isoformat()
        })
            

    # 메모리 정리
    del soupList
    gc.collect()

    return nNewArticleCnt

def Shinyoung_detail(SEQ, BBSNO):
    # print('******************Shinyoung_detail***************')
    # ntNo = NT_NO
    # cmsCd = CMS_CD
    # POST 요청에 사용할 URL
    url = "https://www.shinyoung.com/Common/authTr/devPass"

    # 추가할 request header
    headers = {
        "Accept": "text/plain, */*; q=0.01",
        "Connection": "keep-alive",
        "Content-Length": "0",
        "Host": "www.shinyoung.com",
        "Origin": "https://www.shinyoung.com",
        "Referer": "https://www.shinyoung.com/?page=10078&head=0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }
    session = requests.Session()
    # POST 요청 보내기
    response = session.post(url, headers=headers)

    # 응답의 내용 확인
    if response.status_code != 200:
        print("요청에 실패하였습니다. 상태 코드:", response.status_code)
    
    # 서버에서 반환한 응답 확인 및 새로운 쿠키가 있다면 세션에 추가
    if 'Set-Cookie' in response.headers:
        # 새로운 쿠키를 세션에 추가
        new_cookie = response.headers['Set-Cookie']
        session.cookies.update({'new_cookie_name': new_cookie})

    #### https://www.shinyoung.com/Common/checkAuth

    url = "https://www.shinyoung.com/Common/checkAuth"

    # 추가할 request header
    headers = {
    "Accept": "text/plain, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Content-Length": "0",
    "Host": "www.shinyoung.com",
    "Origin": "https://www.shinyoung.com",
    "Referer": "https://www.shinyoung.com/?page=10078&head=0",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\""
    }

    # POST 요청 보내기
    response = session.post(url, headers=headers)

    # 응답의 내용 확인
    if response.status_code != 200:
        print("요청에 실패하였습니다. 상태 코드:", response.status_code)
    # POST 요청에 사용할 URL
    url = "https://www.shinyoung.com/Common/authTr/downloadFilePath"

    # POST 요청에 포함될 데이터
    data = {
        'SEQ': SEQ,
        'BBSNO': BBSNO
    }
    
    headers = {
        "Accept": "text/plain, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Content-Length": "18",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "www.shinyoung.com",
        "Origin": "https://www.shinyoung.com",
        "Referer": "https://www.shinyoung.com/?page=10078&head=0",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }

    # POST 요청 보내기
    response = session.post(url, data=data, headers=headers)

    # 응답의 내용 확인
    if response.status_code != 200:
        print("요청에 실패하였습니다. 상태 코드:", response.status_code)

    jres = json.loads(response.text)
    
    base_url = 'https://www.shinyoung.com/files/'

    url = base_url + jres['FILEINFO']['FILEPATH']

    # print('*******************완성된 URL',url)
    return url

def Miraeasset_checkNewArticle():
    SEC_FIRM_ORDER = 8
    ARTICLE_BOARD_ORDER = 0

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
        
        scraper = WebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        soup = scraper.Get()

        # 첫 번째 레코드의 제목을 바로 담습니다.
        soupList = soup.select("tbody tr")[2:]  # 타이틀 제거

        # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류

        # 게시물 정보 파싱
        for index, post in enumerate(soupList):
            if index == 0:  # 첫 번째 레코드는 이미 처리했으므로 건너뜁니다.
                continue

            # 작성 일자 파싱
            date_element = post.select_one("tr > td")
            REG_DT = date_element.get_text(strip=True) if date_element else ""

            # 제목 파싱
            title_element = post.select_one(".subject a")
            if not title_element:  # 제목 요소가 없는 경우
                continue  # 건너뜁니다.
            title = " : ".join(title_element.find_all(string=True))  # 제목 텍스트를 문자열로 합침

            # 첨부 파일 파싱
            attachment_element = post.select_one(".bbsList_layer_icon a")
            attachment_link = "없음"
            if attachment_element:
                attachment_link = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"]).group(1)

            # JSON 데이터 생성 및 리스트에 추가
            json_data_list.append({
                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                "FIRM_NM": firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", REG_DT),
                "ATTACH_URL": attachment_link,
                "DOWNLOAD_URL": attachment_link,
                "ARTICLE_TITLE": title,
                "SAVE_TIME": datetime.now().isoformat()
            })

            # print("제목:", title)
            # print("첨부 파일:", attachment_link)
            # print("작성 일자:", REG_DT)
            # print()
            

    # 메모리 정리
    del soup
    gc.collect()

    return json_data_list

def Kiwoom_checkNewArticle():
    SEC_FIRM_ORDER = 10
    ARTICLE_BOARD_ORDER = 0

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
            "stdate": datetime(datetime.now().year, 1, 1).strftime("%Y%m%d"),
            "eddate": GetCurrentDate("yyyymmdd"),
            "f_keyField": '', 
            "f_key": '',
            "_reqAgent": 'ajax',
            "dummyVal": 0
        }

        scraper = WebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.PostJson(params=payload)
            
        if jres['totalCount'] == 0 : return 0

        # print(jres['researchList'])
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        
        soupList = jres['researchList']

        nNewArticleCnt = 0
        
        # JSON To List
        for list in soupList:
            # {'pageNo': None, 'pageSize': 15, 'totalCount': None, 'startRow': None, 'endRow': None, 'f_key': None, 'f_keyField': None, 'rnum': 0, 'sqno': 3533, 'titl': 'Tesla 3Q24 실적 Review: 시장 기대치 상회하는 글로벌 인도량 가이던스 제시', 'expl': '이차전지 - Tesla 3Q24 실적 Review: 시장 기대치 상회하는 글로벌 인도량 가이던스 제시', 'workId': '권준수', 'workEmail': None, 'readCnt': 472, 'makeDt': '2024.10.25', 'attaFile': '1729807061019.pdf', 'attaFileName': 'Tesla 3Q24 실적_241025(final).pdf', 'ivstOpin': None, 'wingsSqno': None, 'relItemList': None, 'tpobNm': '이차전지', 'contL': None, 'itemNm': None, 'fseCdList': None, 'workIdList': None, 'today': None, 'stdate': None, 'eddate': None, 'isNew': 'N', 'brodId': None, 'fnGb': None, 'isScrap': 'N', 'prevSqno': 0, 'nextSqno': 0, 'prevTitl': None, 'nextTitl': None, 'prevMakeDt': None, 'nextMakeDt': None, 'no': 1, 'rSqno': 4147212, 'rMenuGb': 'SN', 'rMenuGbNm': '스팟노트'}

            # print(list)
            # 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb=CR&attaFile=1650493541463.pdf&makeDt=2022.04.21'
            LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}' 
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(list['rMenuGb'],  list['attaFile'], list['makeDt'])
            LIST_ARTICLE_TITLE = list['titl']

            DOWNLOAD_URL = LIST_ARTICLE_URL
            # print(list)
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", list['makeDt']),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soupList
    gc.collect()

    return nNewArticleCnt

def Hmsec_checkNewArticle():
    SEC_FIRM_ORDER = 9
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 현대차증권 투자전략
    TARGET_URL_0 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=1'
    
    # 현대차증권 Report & Note 
    TARGET_URL_1 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=2'
    
    # 현대차증권 해외주식
    TARGET_URL_2 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=8'
    
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )
        payload = {"curPage":1}

        scraper = WebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.PostJson(params=payload)
        
        
        REG_DT = jres['data_list'][0]['REG_DATE'].strip()
        FILE_NAME = jres['data_list'][0]['UPLOAD_FILE1'].strip()
        # print('REG_DATE:',REG_DATE)
        # print('FILE_NAME:',FILE_NAME)

        soupList = jres['data_list']
        
        nNewArticleCnt = 0
        
        # JSON To List
        for list in soupList:
            # print(list)
            # {'REG_TIME': '080734', 'TOTAL_VISITED': 8, 'SERIAL_NO': 33471, 'REG_DATE': '20241028', 'SUBJECT': '현대위아(011210) - 비용을 극복하는 수익 회복 지속능력 필요 ', 'UPLOAD_FILE1': '20241025211531427_ko.pdf', 'MENU_SUBJECT': 'Conmpany Report', 'NAME': '장문수', 'MENU_CODE': 201, 'CONTENTS': '<span style="font-size: 12px; font-family: 돋움; color: #4d4d4d; text-align: justify; line-height: 1'}
            # {'REG_TIME': '080745', 'TOTAL_VISITED': 4, 'SERIAL_NO': 33480, 'REG_DATE': '20241029', 'SUBJECT': 'Global Daily 2024년 10월 29일', 'UPLOAD_FILE1': '20241029080509837_ko.pdf', 'MENU_SUBJECT': '글로벌 투자정보', 'MENU_CODE': 802, 'CONTENTS': '<span style="font-size: 12px; font-family: 돋움; color: #4d4d4d; text-align: justify; line-height: 1'}
            # https://www.hmsec.com/documents/research/20230103075940673_ko.pdf
            DOWNLOAD_URL = 'https://www.hmsec.com/documents/research/{}' 
            DOWNLOAD_URL = DOWNLOAD_URL.format(list['UPLOAD_FILE1'])

            # https://docs.hmsec.com/SynapDocViewServer/job?fid=#&sync=true&fileType=URL&filePath=#
            LIST_ARTICLE_URL = 'https://docs.hmsec.com/SynapDocViewServer/job?fid={}&sync=true&fileType=URL&filePath={}' 
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(DOWNLOAD_URL, DOWNLOAD_URL)

            LIST_ARTICLE_TITLE = list['SUBJECT']

            REG_DT = list['REG_DATE'].strip()
            WRITER = list.get('name', '')
            # print(jres['data_list'])

            # LIST_ARTICLE_URL = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
            # ATTACH_FILE_NAME = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')

            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", REG_DT),
                "WRITER": WRITER,
                "ATTACH_URL":DOWNLOAD_URL,
                "ARTICLE_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    del soupList
    gc.collect()

    return nNewArticleCnt

def Koreainvestment_selenium_checkNewArticle():
    SEC_FIRM_ORDER = 13
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 한국투자증권 리서치 모바일
    TARGET_URL_0 =  "https://securities.koreainvestment.com/main/research/research/Search.jsp?schType=report"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")

        # Chrome 드라이버 초기화
        driver = webdriver.Chrome(options=chrome_options)

        # 웹 페이지 열기
        driver.get(TARGET_URL)

        # 페이지 로딩될때까지 대기
        driver.implicitly_wait(0)

        # 제목 엘리먼트 찾기
        title_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[1]/div[2]/span[1]')
        # 링크 엘리먼트 찾기
        link_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[2]')
        # Info 엘리먼트 찾기 
        info_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[1]/span')
        
        # for title, link in zip(title_elements, link_elements):
        #     # 제목 출력
        #     print("제목:", title.text)
        #     # onClick 프로퍼티값(링크) 출력
        #     print("링크:", link.get_attribute("onclick"))
        
        nNewArticleCnt = 0
        
        
        # List
        for title, link, info in zip(title_elements, link_elements, info_elements):
            LIST_ARTICLE_TITLE = title.text
            LIST_ARTICLE_URL = link.get_attribute("onclick")
            INFO_STR = info.text
            print("INFO_STR =>", INFO_STR)
            LIST_ARTICLE_URL = Koreainvestment_GET_LIST_ARTICLE_URL(LIST_ARTICLE_URL)
            DOWNLOAD_URL = LIST_ARTICLE_URL

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
            
            # https://file.truefriend.com/Storage/research/research05/20240726184612130_ko.pdf

        # # 링크와 제목 출력
        # for link_element in link_elements:
        #     title = link_element.text
        #     link = link_element.get_attribute("href")
        #     print("제목:", title)
        #     print("링크:", link)
        #     print()

        # 브라우저 닫기
        driver.quit()
        
    # 메모리 정리
    gc.collect()

    return nNewArticleCnt

def Koreainvestment_GET_LIST_ARTICLE_URL(string):
    string = string.replace("javascript:prePdfFileView2(", "").replace("&amp;", "&").replace(")", "").replace("(", "").replace("'", "")
    params = string.split(",")
    
    # 문자열에서 필요한 정보 추출
    category = "category1="+params[0].strip() +"&"+ "category2=" + params[1].strip()
    filename = params[2].strip()
    option = params[3].strip()
    datasubmitdate = params[4].strip()
    air_yn = params[5].strip()
    kor_yn = params[6].strip()
    special_yn = params[7].strip()

    # 함수 호출
    r = Koreainvestment_MAKE_LIST_ARTICLE_URL(category, filename, option, datasubmitdate, air_yn, kor_yn, special_yn)

    # 입력 URL을 파싱합니다.
    parsed_url = urlparse.urlparse(r)
    
    # 쿼리 파라미터를 파싱합니다.
    query_params = urlparse.parse_qs(parsed_url.query)
    
    # filepath와 filename 값을 가져옵니다.
    filepath = query_params.get('filepath', [''])[0]
    filename = query_params.get('filename', [''])[0]
    
    # 새로운 URL을 생성합니다.
    new_url = f"http://file.truefriend.com/Storage/{filepath}/{filename}"
    
    return new_url

def Koreainvestment_MAKE_LIST_ARTICLE_URL(filepath, filename, option, datasubmitdate, air_yn, kor_yn, special_yn):
    filename = urllib.parse.quote(filename)
    filepath = filepath
    
    # print('filepath =',filepath)
    host_name = "http://research.truefriend.com/streamdocs/openResearch"
    url = ""
    host_name2 = "https://kis-air.com/kor/"
    host_name3 = "https://kis-air.com/us/"

    if filepath.startswith("?") or filepath.startswith("&"):
        filepath = filepath[1:]

    params = filepath.split("&")
    # print('params',params)
    if len(params) == 2:
        if params == ['category1=01', 'category2=01'] or params == ['category1=01', 'category2=02'] or params == ['category1=01', 'category2=03'] or params == ['category1=01', 'category2=04'] or params == ['category1=01', 'category2=05']:
            filepath = "research/research01"
        elif params == ['category1=02', 'category2=01'] or params == ['category1=02', 'category2=02'] or params == ['category1=02', 'category2=03']:
            filepath = "research/research02"
        elif params == ['category1=03', 'category2=01'] or params == ['category1=03', 'category2=02'] or params == ['category1=03', 'category2=03']:
            filepath = "research/research03"
        elif params == ['category1=04', 'category2=00'] or params == ['category1=04', 'category2=01'] or params == ['category1=04', 'category2=02'] or params == ['category1=04', 'category2=03']:
            filepath = "research/research04"
        elif params[0] == 'category1=05' or params == ['category1=05']:
            filepath = "research/research05"
        elif params == ['category1=07', 'category2=01']:
            filepath = "research/research07"
        elif params == ['category1=08', 'category2=03'] or params == ['category1=08', 'category2=04'] or params == ['category1=08', 'category2=05']:
            filepath = "research/research08"
        elif params == ['category1=06', 'category2=02'] or params == ['category1=06', 'category2=01']:
            filepath = "research/research06"
        elif params == ['category1=09', 'category2=00']:
            filepath = "research/research11"
        elif params == ['category1=10', 'category2=01'] or params == ['category1=10', 'category2=04']:
            filepath = "research/research10"
        elif params == ['category1=10', 'category2=04']:
            filepath = "research/china"
        elif params == ['category1=01', 'category2=06']:
            filepath = "research/research12"
        elif params == ['category1=10', 'category2=06']:
            filepath = "research/research_emailcomment"
        elif params == ['category1=14', 'category2=01']:
            filepath = "research/research14"
        elif params == ['category1=13', 'category2=01']:
            filepath = "research/research11"
        elif params == ['category1=02', 'category2=04'] or params == ['category1=02', 'category2=12'] or params == ['category1=02', 'category2=06'] or params == ['category1=02', 'category2=13'] or params == ['category1=02', 'category2=08'] or params == ['category1=02', 'category2=09'] or params == ['category1=02', 'category2=10'] or params == ['category1=02', 'category2=11'] or params == ['category1=02', 'category2=14']:
            filepath = "research/research02"
        elif params == ['category1=15', 'category2=01']:
            filepath = "research/research01"
        elif params == ['category1=16', 'category2=01']:
            filepath = "research/research15"

    # print('filepath', filepath)
    if not option or option == None or option == "":
        option = "01"

    if kor_yn == 'Y' and air_yn == 'N' and special_yn == 'N' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name2}{datasubmitdate}/daily"
    elif kor_yn == 'Y' and air_yn == 'N' and special_yn == 'Y' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name2}{datasubmitdate}/special"
    elif kor_yn == 'N' and air_yn == 'N' and special_yn == 'N' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name3}{datasubmitdate}/daily"
    elif kor_yn == 'N' and air_yn == 'N' and special_yn == 'Y' and params == ['category1=15', 'category2=01']:
        datasubmitdate = datasubmitdate.replace(".", "-")
        url = f"{host_name3}{datasubmitdate}/special"
    else:
        url = f"{host_name}?filepath={urllib.parse.quote(filepath)}&filename={filename}&option={option}"

    # print(url)
    return url

def DAOL_checkNewArticle():
    SEC_FIRM_ORDER      = 14
    ARTICLE_BOARD_ORDER = 0

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
            'startDate': datetime(datetime.now().year, 1, 1).strftime("%Y/%m/%d"),
            'endDate': GetCurrentDate("yyyy/mm/dd"),
            'searchSelect': '0',
            'searchNm1': '',
            'searchNm2': query_params.get('rGubun')
        }

        # POST 요청 보내기
        response = requests.post(TARGET_URL, data=form_data, headers=headers)
        # HTML parse
        soup = BeautifulSoup(response.content, "html.parser")
        # print(soup)
        
        # soupList = soup.select('tr > td.al > a')
        soupList = soup.select('tr')

        # 응답 처리
        if response.status_code != 200:
            print("요청이 실패했습니다.")
            print("상태 코드:", response.status_code)
            continue

        nNewArticleCnt = 0
        for list in soupList:

            strData = list.get_text()
            if "게시물이 없습니다."  in strData:
                break
            REG_DT = list.select_one("td:nth-child(1)").get_text()
            list = list.select_one('td.al > a')
            LIST_ARTICLE_TITLE = list['title']
            LIST_ARTICLE_URL   =  list['href']
    
            parts = LIST_ARTICLE_URL.split(',')
            if len(parts) != 3:
                return "잘못된 입력 형식입니다."
            
            path = parts[0].split("'")[1]
            filename = parts[1].split("'")[1]
            research_id = parts[2].split(")")[0]
            
            LIST_ARTICLE_URL = f"https://www.ktb.co.kr/common/download.jspx?cmd=viewPDF&path={path}/{filename}"
            DOWNLOAD_URL     = LIST_ARTICLE_URL
            # print('LIST_ARTICLE_TITLE='+LIST_ARTICLE_TITLE)
            # print('NXT_KEY='+NXT_KEY)
            # ATTACH_URL = LIST_ARTICLE_URL
            # sendMessageText += GetSendMessageText(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
            
            # print(LIST_ARTICLE_TITLE)
            # print(LIST_ARTICLE_URL)
            # print()
            
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", REG_DT),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })

    # 메모리 정리
    del soup, soupList
    del response
    gc.collect()

    return nNewArticleCnt

def TOSSinvest_checkNewArticle():
    SEC_FIRM_ORDER      = 15
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()
 
    # 다올투자증권 산업분석
    TARGET_URL_0  = 'https://docs-api.tossinvest.com/api/v1/post/search?categoryId=138&searchTitleKeyword=&page=0&size=10&type=INVESTMENT_INFO'

    TARGET_URL_TUPLE = (TARGET_URL_0,)
    
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER
        )

        scraper = WebScraper(TARGET_URL, firm_info)
        
        # HTML parse
        jres = scraper.GetJson()
        
        # HTML parse
        soupList = jres['result']['list']
        
        print('*' *40)
        
        nNewArticleCnt = 0
        for list in soupList:
            # print(list)
            # [{'id': 10306, 'type': 'INVESTMENT_INFO', 'category': {'id': 138, 'type': 'INVESTMENT_INFO', 'categoryName': '리서치 보고서', 'categoryDepth': 1, 'upperCategory': None, 'position': 0, 'displayYn': 'Y'}, 'title': '다녀왔습니다, 실리콘밸리', 'contents': '<p>작성자: 이영곤, 이지선 애널리스트</p><p>본 리포트를 시작으로, 토스증권 리서치센터는 &#39;실리콘밸리 특집&#39; 시리즈를 연이어 발행할 예정입니다. 실리콘밸리 현장에서 직접 발로 뛰며 얻은 생생한 이야기를 전해드리겠습니다.</p><p><br></p><p><strong>본 리포트에서 저희가 말씀드리고자 하는 건 크게 3가지입니다.</strong></p><p><br></p><p><strong>첫째, 실리콘밸리 혁신의 비결은 인재, 자본, 인프라입니다.</strong></p><p>실리콘밸리 주변에는 스탠포드, 버클리 등 세계 최고 수준의 대학들이 위치해 있습니다. 이곳의 학생들은 자연스럽게 주변 테크 기업에 취직하거나 창업을 선택하게 됩니다. 기업 문화가 경직되어 있지 않기 때문에 아시아 출신이나 여성 인재들도 실리콘밸리로 모여듭니다.</p><p>기업이 성장하는 데 있어 자본은 중요한 요소입니다. 실리콘밸리 지역의 벤처캐피탈은 창업한 지 얼마 안 된 기업에 적극적으로 투자하는 편이라, 성공 가능성 있는 기업이 창업 초기 현금 조달을 하지 못해 사라져 버리는 일을 막는 데 큰 역할을 하고 있습니다.</p><p>실리콘밸리는 기술, 인력, 자본이 시너지를 낼 수 있는 환경입니다. 네트워킹 문화를 바탕으로, 아이디어 공유를 비롯한 협력 관계가 갖춰져 있기 때문입니다. 뿐만 아니라 미국 정부의 정책적인 지원도 혁신 생태계 조성에 기여했습니다.</p><p><br></p><p><strong>둘째, 실리콘밸리 기업들은 AI 산업 성장을 선도하고 있습니다.</strong></p><p>최근 들어 실리콘밸리가 예전 같지 않다는 목소리도 나오는데요. 실제로 코로나19 직후 이 지역 실업률이 급증했고, 벤처 투자금도 한창때에 비해 줄어들었습니다. 현지 네트워킹 행사에서 만난 사람들도 하나같이 &ldquo;올해 특히 일자리 구하기가 힘들다&rdquo;고 하소연했습니다.</p><p>하지만 실리콘밸리는 여전히 혁신이라는 키워드를 놓지 않고 있습니다. 혁신의 중심에는 AI가 있습니다. 생성형 AI 산업의 성장은 대형 클라우드 서비스 제공자뿐 아니라 주변 생태계에도 영향을 미쳐, 시장 규모가 한 번 더 크게 성장할 거라는 전망이 나옵니다.</p><p>챗GPT팀 연구원의 한마디는 실리콘밸리 혁신의 속도가 어느 정도인지 단적으로 보여줍니다. &ldquo;실리콘밸리에서 AI 기술을 논할 때 몇 달 전의 기술을 언급하는 게 얼마나 뒤떨어진 말인지 알아야 한다.&rdquo;</p><p><br></p><p><strong>셋째, 실리콘밸리에서 다양한 투자 아이디어를 얻었습니다.</strong></p><p>&quot;혁신적 기술의 탄생에 관심을 갖되 투자는 기술을 실현시키는 기업에 하자.&quot; IBM은 1990년대 이미 스마트폰과 비슷한 제품을 개발했지만 시장에서는 성공하지 못했습니다.</p><p>&quot;새로운 비즈니스 모델이 열리는 시기엔, 그 시장을 선점하는 기업에 주목하라.&quot; 우버는 스마트폰을 이용한 차량 호출 서비스 시장을 선점해 택시 산업을 상당 부분 대체해 나가고 있습니다.</p><p>&quot;변화에 빠르고 유연하게 대응할 수 있는 기업에 투자하라.&quot; 바꿔야 할 것과 바꾸지 말아야 할 것을 잘 구분한 넷플릭스처럼요.</p><p>&quot;기술의 혁신성만 보지 말고 상용화 가능성을 체크하고, 나아가 기술 표준이 될 수 있는지에 주목하라.&quot; 한때 자율주행차의 핵심 부품으로 주목받았던 라이다는 아직 기술 표준으로 자리잡지 못했습니다.</p><p>&quot;애플처럼 높은 고객 충성도가 유지되는 기업에 투자하라.&quot; 높은 고객 충성도는 기업의 큰 자산입니다.</p><p>&quot;미래 핵심 기술을 보유하고, 지배력을 유지할 수 있는 기업에 집중하라.&quot; 엔비디아는 단순히 반도체 만드는 것을 넘어 인공지능 생태계를 주관하는 기업이 되길 꿈꾸고 있습니다.</p><p><br></p><p><br></p><p><strong>* 좀 더 자세한 내용은 첨부 파일을 참고해주시기 바랍니다.</strong></p>', 'position': 0, 'displayYn': 'Y', 'displayDt': '2024-10-29T00:00:00', 'displayEndDt': None, 'author': 'myungkyoon.ki', 'createdAt': '2024-10-29T10:59:01', 'updatedAt': '2024-10-29T10:59:02', 'pinned': False, 'subTitle': '', 'postImage': 'https://home-files.tossinvest.com/files/investment-info/cf72dfb2-4e46-433a-8242-42b33d1a941e.pdf', 'refLink': '', 'files': [{'postId': 10306, 'type': 'INVESTMENT_INFO', 'fileName': 'TossRC_Silicon_Valley_1st_20241029.pdf', 'filePath': 'https://home-files.tossinvest.com/files/investment-info/cf72dfb2-4e46-433a-8242-42b33d1a941e.pdf', 'createdAt': '2024-10-29T10:59:01'}]}, 
            # {'id': 9678, 'type': 'INVESTMENT_INFO', 'category': {'id': 138, 'type': 'INVESTMENT_INFO', 'categoryName': '리서치 보고서', 'categoryDepth': 1, 'upperCategory': None, 'position': 0, 'displayYn': 'Y'}, 'title': '왜 미국 주식인가', 'contents': '<p style="text-align: left;">작성자: 이영곤, 이지선, 한상원 애널리스트</p><p><br></p><p>본 리포트는 &lsquo;개인투자자에게 미국 주식이 유리한 이유&rsquo;에 대해 3가지 관점에서 분석했습니다. 왜 미국주식일까요?</p><p><strong>첫째, 미국 주식은 &lsquo;좋은 시장&rsquo;에서 거래됩니다.</strong></p><p>미국 주식시장은 세계에서 가장 규모가 큰 시장으로, 좋은 투자처를 찾을 기회가 많습니다. 규모가 큰 만큼 유동성이 풍부해 하루 평균 거래액이 300조원을 넘습니다. 이는 한국의 30배 수준으로, 유동성이 풍부하면 주가가 왜곡될 위험이 낮습니다.</p><p>제도가 잘 갖춰져 있어 신뢰도도 높습니다. SEC(미국 증권거래위원회)의 관리 감독 하에 공정하고 투명하게 운영되기 때문에 타 주식시장에 비해 소액주주의 이익을 침해당할 위험도 낮습니다. 뿐만 아니라 배당, 자사주매입 등 기업의 이익을 주주에게 돌려주는 주주환원 움직임이 활발합니다.</p><p><strong>둘째, 미국에는 &lsquo;좋은 기업&rsquo;들이 많습니다.</strong></p><p>투자자에게 좋은 기업은 주가가 올라서 투자이익을 안겨주는 기업입니다. 주가가 오르려면 실적이 좋고 높은 멀티플을 부여받아야 합니다. 지난 30년간 미국은 높은 실적과 멀티플 덕분에 다른 나라 주식시장 대비 주가가 오른 기업들이 많았습니다. 특히 금융위기와 코로나 19 이후엔 미국 선호 현상이 더욱 심화되고 있습니다. 또한 미국에는 늘어난 이익을 배당의 형태로 주주들에게 돌려주는 기업들이 많습니다.</p><p>다수의 미국 기업들이 매출, 효율성 등 여러 가지 측면에서 전 세계 우수기업 리스트 상위권을 차지하고 있습니다. 이는 미국이 경제 규모, 천연자원, 국방력, 인적 자원 등 기업 성장의 원동력이 되는 요소들을 두루 갖추고 있기 때문입니다. 여기에 만족하지 않고 미국 기업들은 AI 등 미래 패러다임을 주도하고 있습니다.</p><p><strong>셋째, 미국 주식은 자산배분 효과가 있습니다.</strong></p><p>한국 투자자들의 자산은 원화에 쏠려 있습니다. 따라서 자산의 일정 비율을 달러로 바꿔두면 리스크를 줄일 수 있습니다. 기축통화인 달러는 한국의 투자자산과 반대로 움직이기 때문에 특히 자산배분 효과가 큽니다.</p><p>미국 주식을 사는 것 역시 그만큼의 달러를 보유한다는 의미와 같습니다. 실제로 과거 데이터를 살펴봤더니 코스피에만 투자하는 것보다 달러나 미국주식에 나눠 투자했을 때 리스크가 줄어드는 것으로 나타났습니다. 세계 경제에서 달러가 차지하는 비중을 고려했을 때 앞으로도 달러는 기축통화 자리를 지킬 확률이 높습니다. 따라서 미국 주식 투자의 자산배분 효과 역시 지속될 것으로 판단됩니다.</p><p><br></p><p><strong>* 좀 더 자세한 내용은 첨부 파일을 참고해주시기 바랍니다.</strong></p>', 'position': 0, 'displayYn': 'Y', 'displayDt': '2024-09-20T00:00:00', 'displayEndDt': None, 'author': 'bg.choi', 'createdAt': '2024-09-20T22:12:14', 'updatedAt': '2024-09-20T22:12:14', 'pinned': False, 'subTitle': '', 'postImage': 'https://home-files.tossinvest.com/files/investment-info/7ac1921e-c69d-4c18-a51b-776e27f9d731.pdf', 'refLink': '', 'files': [{'postId': 9678, 'type': 'INVESTMENT_INFO', 'fileName': 'TossRC_Why_US_Equities_20240923.pdf', 'filePath': 'https://home-files.tossinvest.com/files/investment-info/7ac1921e-c69d-4c18-a51b-776e27f9d731.pdf', 'createdAt': '2024-09-20T22:12:14'}]}]
            LIST_ARTICLE_TITLE = list['title']
            LIST_ARTICLE_URL   =  list['files'][0]['filePath']
            REG_DT             = list['createdAt']
            DOWNLOAD_URL        = LIST_ARTICLE_URL
            
            # print(LIST_ARTICLE_TITLE)
            # print(LIST_ARTICLE_URL)

            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":REG_DT.split('T')[0].replace('-', ''),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
    # 메모리 정리
    del jres, soupList
    gc.collect()

    return nNewArticleCnt

def Leading_checkNewArticle():
    SEC_FIRM_ORDER = 16
    ARTICLE_BOARD_ORDER = 0

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
        
        scraper = WebScraper(TARGET_URL, firm_info)
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
            
            reg_dt_element = list.select_one("td:nth-child(5)")
            REG_DT = reg_dt_element.get_text(strip=True)
            # 결과 출력
            # print("제목:", title)
            # print("첨부 파일:", attachment_link)
            # print()
            LIST_ARTICLE_TITLE = title
            LIST_ARTICLE_URL = attachment_link
            DOWNLOAD_URL     = attachment_link
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "REG_DT":re.sub(r"[-./]", "", REG_DT),
                "ATTACH_URL":LIST_ARTICLE_URL,
                "DOWNLOAD_URL": DOWNLOAD_URL,
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "SAVE_TIME": datetime.now().isoformat()
            })
            
            
    # 메모리 정리
    del soupList, list
    gc.collect()

    return nNewArticleCnt

async def Daeshin_checkNewArticle():
    SEC_FIRM_ORDER = 17
    ARTICLE_BOARD_ORDER = 0

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    """대신증권의 새 게시글 정보를 비동기로 확인하는 함수"""
    BASE_URL = "https://money2.creontrade.com/E5/m_net/ResearchCenter/Work/"
    url = BASE_URL + "mre_DM_Mobile_Research.aspx?b_code=91&m=0&p=0&v=0&word=SVBPKOq4sOyXheqzteqwnCkg7KO86rSA6riw7JeF&searchtype=Research&category="

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Referer": url
    }

    async def fetch_hidden_values(session, url):
        """초기 페이지에서 hidden 필드 값을 추출하는 함수"""
        async with session.get(url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # hidden 필드 값 추출
            viewstate = soup.find(id="__VIEWSTATE")['value']
            viewstate_gen = soup.find(id="__VIEWSTATEGENERATOR")['value']
            event_validation = soup.find(id="__EVENTVALIDATION")['value']
            
            return viewstate, viewstate_gen, event_validation

    async def fetch_page_data(session, page, viewstate, viewstate_gen, event_validation):
        """각 페이지의 데이터와 hidden 필드를 갱신하여 크롤링하는 함수"""
        data = {
            "ctl00$sm1": "ctl00$ContentPlaceHolder1$UpdatePanel1|ctl00$ContentPlaceHolder1$bt_refresh",
            "ctl00$ContentPlaceHolder1$hf_page": str(page),
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_gen,
            "__EVENTVALIDATION": event_validation,
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$bt_refresh": ""
        }

        async with session.post(url, headers=headers, data=data) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 게시글 목록 추출
            items = soup.find_all("li")
            if not items:
                return None  # 더 이상 데이터가 없으면 None 반환
            
            for item in items:
                title = item.find("strong", class_="title1").text.strip()
                reg_dt = item.find("span", class_="date").text.strip()
                author = item.find("span", class_="time").text.strip()
                
                # 더 일반적인 'a' 태그 찾기
                link_tag = item.find("a")
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    article_url = BASE_URL + href
                else:
                    print("No href found for this item")
                    continue
                
                # 개별 게시글의 ATTACH_URL 추출
                attach_url = await fetch_attach_url(session, article_url)

                # json 데이터 생성 및 리스트에 추가
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": re.sub(r"[-./]", "", reg_dt),
                    "ARTICLE_URL": article_url,
                    "ATTACH_URL": attach_url,
                    "DOWNLOAD_URL": attach_url,
                    "ARTICLE_TITLE": title,
                    "SAVE_TIME": datetime.now().isoformat()
                })

    async def fetch_attach_url(session, article_url):
        """ARTICLE_URL 페이지에서 ATTACH_URL 추출"""
        async with session.get(article_url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            attach_element = soup.find(id="btnPdfLoad")
            
            if attach_element:
                return attach_element['href']
            return None

    async with aiohttp.ClientSession() as session:
        # 초기 GET 요청으로 hidden 값 추출
        viewstate, viewstate_gen, event_validation = await fetch_hidden_values(session, url)
        
        # 각 페이지 비동기적으로 요청
        tasks = []
        for page in range(1, 5):
            tasks.append(fetch_page_data(session, page, viewstate, viewstate_gen, event_validation))
        
        # 모든 태스크 완료 대기
        await asyncio.gather(*tasks)

        return json_data_list
async def Daeshin_checkNewArticle():
    SEC_FIRM_ORDER = 17
    ARTICLE_BOARD_ORDER = 0

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    """대신증권의 새 게시글 정보를 비동기로 확인하는 함수"""
    BASE_URL = "https://money2.creontrade.com/E5/m_net/ResearchCenter/Work/"
    url = BASE_URL + "mre_DM_Mobile_Research.aspx?b_code=91&m=0&p=0&v=0&word=SVBPKOq4sOyXheqzteqwnCkg7KO86rSA6riw7JeF&searchtype=Research&category="

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Referer": url
    }

    async def fetch_hidden_values(session, url):
        """초기 페이지에서 hidden 필드 값을 추출하는 함수"""
        async with session.get(url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # hidden 필드 값 추출
            viewstate = soup.find(id="__VIEWSTATE")['value']
            viewstate_gen = soup.find(id="__VIEWSTATEGENERATOR")['value']
            event_validation = soup.find(id="__EVENTVALIDATION")['value']
            
            return viewstate, viewstate_gen, event_validation

    async def fetch_page_data(session, page, viewstate, viewstate_gen, event_validation):
        """각 페이지의 데이터와 hidden 필드를 갱신하여 크롤링하는 함수"""
        data = {
            "ctl00$sm1": "ctl00$ContentPlaceHolder1$UpdatePanel1|ctl00$ContentPlaceHolder1$bt_refresh",
            "ctl00$ContentPlaceHolder1$hf_page": str(page),
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": viewstate_gen,
            "__EVENTVALIDATION": event_validation,
            "__ASYNCPOST": "true",
            "ctl00$ContentPlaceHolder1$bt_refresh": ""
        }

        async with session.post(url, headers=headers, data=data) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            
            # 게시글 목록 추출
            items = soup.find_all("li")
            if not items:
                return None  # 더 이상 데이터가 없으면 None 반환
            
            for item in items:
                title = item.find("strong", class_="title1").text.strip()
                date = item.find("span", class_="date").text.strip()
                author = item.find("span", class_="time").text.strip()
                
                # 더 일반적인 'a' 태그 찾기
                link_tag = item.find("a")
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    article_url = BASE_URL + href
                else:
                    print("No href found for this item")
                    continue
                
                # 개별 게시글의 ATTACH_URL 추출
                attach_url = await fetch_attach_url(session, article_url)

                # json 데이터 생성 및 리스트에 추가
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "ARTICLE_URL": article_url,
                    "ATTACH_URL": attach_url,
                    "DOWNLOAD_URL": attach_url,
                    "ARTICLE_TITLE": title,
                    "SAVE_TIME": datetime.now().isoformat()
                })

    async def fetch_attach_url(session, article_url):
        """ARTICLE_URL 페이지에서 ATTACH_URL 추출"""
        async with session.get(article_url, headers=headers) as response:
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            attach_element = soup.find(id="btnPdfLoad")
            
            if attach_element:
                return attach_element['href']
            return None

    async with aiohttp.ClientSession() as session:
        # 초기 GET 요청으로 hidden 값 추출
        viewstate, viewstate_gen, event_validation = await fetch_hidden_values(session, url)
        
        # 각 페이지 비동기적으로 요청
        tasks = []
        for page in range(1, 5):
            tasks.append(fetch_page_data(session, page, viewstate, viewstate_gen, event_validation))
        
        # 모든 태스크 완료 대기
        await asyncio.gather(*tasks)

# 로그 디렉토리 설정 함수
def setup_log_directory():
    HOME_PATH = os.path.expanduser("~")
    LOG_PATH = os.path.join(HOME_PATH, "log", GetCurrentDate('YYYYMMDD'))
    os.makedirs(LOG_PATH, exist_ok=True)
    return LOG_PATH

def get_script_name():
    # 현재 스크립트의 이름 가져오기
    script_filename = os.path.basename(__file__)
    script_name = script_filename.split('.')
    script_name = script_name[0]
    print('script_filename', script_filename)
    return script_name

def setup_debug_directory():
    LOG_PATH = setup_log_directory()
    script_name = get_script_name()
    # requests 라이브러리의 로깅을 활성화
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    # log 파일명
    LOG_FILENAME =  GetCurrentDate('YYYYMMDD')+ '_' + script_name + ".dbg"
    print('__file__', __file__, LOG_FILENAME)
    # log 전체경로
    LOG_FULLFILENAME = os.path.join(LOG_PATH, LOG_FILENAME)
    print('LOG_FULLFILENAME',LOG_FULLFILENAME)
    logging.basicConfig(filename=LOG_FULLFILENAME, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    print("LOG_FULLFILENAME",LOG_FULLFILENAME)
    logging.debug('이것은 디버그 메시지입니다.')
    
    
def main():
    print('===================scrap_send===============')
    
    # 로그 디렉토리 설정
    setup_log_directory()

    # Set Debug
    # setup_debug_directory()

    # 동기 함수 리스트
    sync_check_functions = [
        LS_checkNewArticle,
        ShinHanInvest_checkNewArticle,
        NHQV_checkNewArticle,
        HANA_checkNewArticle,
        KB_checkNewArticle,
        Samsung_checkNewArticle,
        Sangsanginib_checkNewArticle,
        Shinyoung_checkNewArticle,
        Miraeasset_checkNewArticle,
        Hmsec_checkNewArticle,
        Kiwoom_checkNewArticle,
        Koreainvestment_selenium_checkNewArticle,
        DAOL_checkNewArticle,
        TOSSinvest_checkNewArticle,
        Leading_checkNewArticle,
    ]

    # 비동기 함수 리스트
    async_check_functions = [
        Daeshin_checkNewArticle,
        imfnsec_checkNewArticle
    ]

    total_data = []  # 전체 데이터를 저장할 리스트
    totalCnt = 0

    # 동기 함수 실행
    for check_function in sync_check_functions:
        print(f"{check_function.__name__} => 새 게시글 정보 확인")
        json_data_list = check_function()  # 각 함수가 반환한 json_data_list
        if json_data_list:  # 유효한 데이터가 있을 경우에만 처리
            print('=' * 40)
            print(f"{check_function.__name__} => {len(json_data_list)}개의 유효한 게시글 발견")
            total_data.extend(json_data_list)  # 전체 리스트에 추가
            totalCnt += len(json_data_list)
        
        time.sleep(1)

    # 비동기 함수 실행
    # 새 이벤트 루프 생성 및 설정
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # 비동기 함수 리스트 실행
        tasks = [func() for func in async_check_functions]  # 비동기 함수 호출을 태스크로 생성
        results = loop.run_until_complete(asyncio.gather(*tasks))  # 태스크 병렬 실행 및 결과 수집

        for idx, json_data_list in enumerate(results):
            async_check_function = async_check_functions[idx]
            print(f"{async_check_function.__name__} => 새 게시글 정보 확인")
            if json_data_list:  # 유효한 데이터가 있을 경우에만 처리
                print('=' * 40)
                print(f"{async_check_function.__name__} => {len(json_data_list)}개의 유효한 게시글 발견")
                total_data.extend(json_data_list)  # 전체 리스트에 추가
                totalCnt += len(json_data_list)

        print('==============전체 레포트 제공 회사 게시글 조회 완료==============')
        
        if total_data:
            inserted_count = insert_json_data_list(total_data, 'data_main_daily_send')  # 모든 데이터를 한 번에 삽입
            print(f"총 {totalCnt}개의 게시글을 스크랩하여.. DB에 Insert 시도합니다.")
            print(f"총 {inserted_count}개의 새로운 게시글을 DB에 삽입했습니다.")
            if inserted_count:
                loop.run_until_complete(scrap_send_main.main())
                loop.run_until_complete(scrap_upload_pdf.main())
        else:
            print("새로운 게시글이 스크랩 실패.")
    finally:
        loop.close()  # 이벤트 루프 종료
        
if __name__ == "__main__":
    main()