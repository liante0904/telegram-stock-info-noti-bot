# -*- coding:utf-8 -*- 
import os
import gc
import sys
import datetime
from pytz import timezone
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import time
import json
import re
import urllib.parse as urlparse
import urllib.request
import base64
from bs4 import BeautifulSoup

from models.FirmInfo import FirmInfo
from models.WebScraper import WebScraper
from utils.json_util import save_data_to_local_json # import the function from json_util
from package.json_to_sqlite import insert_data
from utils.date_util import GetCurrentDate, GetCurrentDate_NH

# selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#################### global 변수 정리 ###################################
############공용 상수############


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
        today = datetime.date.today()
        # 7일 전 날짜 계산
        seven_days_ago = today - datetime.timedelta(days=7)

        nNewArticleCnt = 0
        
        for list in soupList:
            date = list.select('td')[3].get_text()
            list = list.select('a')
            # print(list[0].text)
            # print('https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", ""))
            LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", "")
            LIST_ARTICLE_TITLE = list[0].get_text()
            LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]")+1:len(LIST_ARTICLE_TITLE)]
            POST_DATE = date.strip()
            # print(POST_DATE)

            # POST_DATE를 datetime 형식으로 변환 (형식: yyyy.mm.dd)
            try:
                post_date_obj = datetime.datetime.strptime(POST_DATE, '%Y.%m.%d').date()
            except ValueError as e:
                print(f"날짜 형식 오류: {POST_DATE}, 오류: {e}")
                continue

            # 7일 이내의 게시물만 처리
            if post_date_obj < seven_days_ago:
                print(f"게시물 날짜 {POST_DATE}가 7일 이전이므로 중단합니다.")
                break

            item = LS_detail(LIST_ARTICLE_URL, date)
            print(item)
            if item:
                LIST_ARTICLE_URL = item['LIST_ARTICLE_URL']
                DOWNLOAD_URL     = item['LIST_ARTICLE_URL']
                LIST_ARTICLE_TITLE = item['LIST_ARTICLE_TITLE']
            
            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수
            
    # 메모리 정리
    del soup
    # del response
    gc.collect()
    return nNewArticleCnt

def LS_detail(ARTICLE_URL, date):
    
    ARTICLE_URL = ARTICLE_URL.replace('&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1', '')
    
    item = {}  # 빈 딕셔너리로 초기화
    
    time.sleep(0.1)
    
    try:
        webpage = requests.get(ARTICLE_URL, verify=False)
    except:
        return True
    
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    
    # 게시글 제목
    trs = soup.select('tr')
    item['LIST_ARTICLE_TITLE'] = trs[0].select_one('td').text
    
    
    # 첨부파일 이름
    item['LIST_ARTICLE_FILE_NAME'] = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').get_text()
    
    # 첨부파일 URL 조립 예시  
    # => https://www.ls-sec.co.kr/upload/EtwBoardData/B202410/20241002_한국 9월 소비자물가.pdf
    
    # B포스팅 월
    URL_PARAM = date
    URL_PARAM = URL_PARAM.split('.')
    URL_PARAM_0 = 'B' + URL_PARAM[0] + URL_PARAM[1]

    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').get_text()
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

        nNewArticleCnt = 0
        # JSON To List
        for list in soupList:
            # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
            # print(list)

            LIST_ARTICLE_TITLE = list['f1']
            LIST_ARTICLE_URL = list['f3']

            try:
                LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('shinhaninvest.com', 'shinhansec.com')
                LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('/board/message/file.do?', '/board/message/file.pdf.do?')
            except Exception as e:
                print("에러 발생:", e)
                LIST_ARTICLE_URL = list['f3']
            
            DOWNLOAD_URL = LIST_ARTICLE_URL
            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수
    
    # 메모리 정리
    del scraper
    gc.collect()

    return nNewArticleCnt

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
        if nNewArticleCnt == 0: return None
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

        BOARD_NM            = list['rshPprSerCdNm']
        LIST_ARTICLE_TITLE = list['rshPprTilCts']
        LIST_ARTICLE_URL =  list['hpgeFleUrlCts']
        DOWNLOAD_URL    = LIST_ARTICLE_URL
        if save_data_to_local_json(
            filename='./json/data_main_daily_send.json',
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm=firm_info.get_firm_name(),
            attach_url=LIST_ARTICLE_URL,
            download_url=DOWNLOAD_URL,
            article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

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
            LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').text
            LIST_ARTICLE_URL =  'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
            DOWNLOAD_URL    = LIST_ARTICLE_URL
            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수
                
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
    # 요청 헤더
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    # 요청 payload 데이터
    payload = {
        "pageNo": 1,
        "pageSize": 60,
        "registdateFrom": GetCurrentDate("YYYYMMDD"),
        "registdateTo": GetCurrentDate("YYYYMMDD"),
        "templateid": "",
        "lowTempId": "",
        "folderid": "", #"37,38,186",
        "callGbn": "RCLIST"
    }

    # POST 요청 보내기
    response = requests.post(TARGET_URL, headers=headers, json=payload)

    # 응답 확인
    if response.status_code == 200:
        jres = response.json()
    else:
        print("요청에 실패했습니다. 상태 코드:", response.status_code)

    soupList = jres['response']['reportList']
    # print(soupList)
    
    nNewArticleCnt = 0
    
    # JSON To List
    for list in soupList:
        # print(list)

        LIST_ARTICLE_TITLE = list['docTitleSub']
        if list['docTitle'] not in list['docTitleSub'] : LIST_ARTICLE_TITLE = list['docTitle'] + " : " + list['docTitleSub']
        else: LIST_ARTICLE_TITLE = list['docTitleSub']
        LIST_ARTICLE_URL = list['urlLink'].replace("wInfo=(wInfo)&", "")
        LIST_ARTICLE_URL = KB_decode_url(LIST_ARTICLE_URL)
        DOWNLOAD_URL     = LIST_ARTICLE_URL
 
        if save_data_to_local_json(
            filename='./json/data_main_daily_send.json',
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm=firm_info.get_firm_name(),
            attach_url=LIST_ARTICLE_URL,
            download_url=DOWNLOAD_URL,
            article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수
    
    # 메모리 정리
    del soupList
    del response
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
        try:
            response = requests.get(TARGET_URL, verify=False)
        except:
            return 0

        # HTML parse
        soup = BeautifulSoup(response.content, "html.parser")
        soupList = soup.select('#content > section.bbsLstWrap > ul > li')

        try:
            # ARTICLE_BOARD_NAME =  BOARD_NM 
            a_href =soup.select('#content > section.bbsLstWrap > ul > li:nth-child(1)> a')[FIRST_ARTICLE_INDEX].attrs['href']
            a_href = a_href.replace('javascript:downloadPdf(', '').replace(';', '')
            a_href = a_href.split("'")
            a_href = a_href[1]
        except:
            return 0

        # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류

        nNewArticleCnt = 0
        
        for list in soupList:
            LIST_ARTICLE_TITLE = list.select_one('#content > section.bbsLstWrap > ul > li > a > dl > dt > strong').text
            a_href = list.select_one('#content > section.bbsLstWrap > ul > li > a').attrs['href']
            a_href = a_href.replace('javascript:downloadPdf(', '').replace(';', '')
            a_href = a_href.split("'")
            a_href = a_href[1]
            LIST_ARTICLE_URL =  'https://www.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName=' + a_href+ '&contentType=application/pdf&inlineYn=Y'
            # fileNameArray = a_href.split("/")
            # LIST_ATTACT_FILE_NAME = fileNameArray[1].strip()

            # 제목 가공
            LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("수정", "")
            LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find(")")+1:len(LIST_ARTICLE_TITLE)]
            DOWNLOAD_URL       = LIST_ARTICLE_URL
            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

    # 메모리 정리
    del soup
    del response
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
            "Referer": "https://www.sangsanginib.com/research/enterpriseReport/enterpriseReportMobView",
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
            # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
            # print('list***************** \n',list)
            # 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb=CR&attaFile=1650493541463.pdf&makeDt=2022.04.21'
            # LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}' 
            # print('cmsCd[ARTICLE_BOARD_ORDER]',cmsCd[ARTICLE_BOARD_ORDER])
            # print('NT_NO=',list['NT_NO'], 'CMS_CD=',cmsCd[ARTICLE_BOARD_ORDER])

            LIST_ARTICLE_URL = Sangsanginib_detail(NT_NO=list['NT_NO'], CMS_CD=cmsCd[ARTICLE_BOARD_ORDER])
            LIST_ARTICLE_TITLE = list['TITLE']
            DOWNLOAD_URL = LIST_ARTICLE_URL
            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

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
    # print('##############11111',jres)
    jres = jres['file'][0] #PDF
    # print('################222222',jres) 
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
    headers = {
        "Accept": "text/plain, */*; q=0.01",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.shinyoung.com/?page=10078&head=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    }

    # POST 요청을 보낼 데이터
    data = {
        "KEYWORD": "",
        "rows": "10",
        "page": "1"
    }
    
    jres = ''
    try:
        response = requests.post(TARGET_URL, headers=headers, data=data)
        if response.status_code == 200:
            # print(response.text)  # 응답 내용 출력
            jres = json.loads(response.text)
        else:
            print("Failed to fetch page:", response.status_code)
            return True
    except Exception as e:
        print("An error occurred:", str(e))
        return True

    # print(jres['rows'])
    soupList = jres['rows']
    
    nNewArticleCnt = 0
    
    # JSON To List
    for list in soupList:
        # print('list***************** \n',list)
        # print('NT_NO=',list['NT_NO'], 'CMS_CD=',cmsCd[ARTICLE_BOARD_ORDER])
        LIST_ARTICLE_URL = Shinyoung_detail(SEQ=list['SEQ'], BBSNO=list['BBSNO'])
        LIST_ARTICLE_TITLE = list['TITLE']
        DOWNLOAD_URL = LIST_ARTICLE_URL
        if save_data_to_local_json(
            filename='./json/data_main_daily_send.json',
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm=firm_info.get_firm_name(),
            attach_url=LIST_ARTICLE_URL,
            download_url=DOWNLOAD_URL,
            article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

    # 메모리 정리
    del soupList
    del response
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
    # print(data)
    # 추가할 request header
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
        # https://www.sangsanginib.com/common/fileDownload?cmsCd=CM0078&ntNo=4315&fNo=1&fNm=%5BSangSangIn%5D2022038_428.pdf

    jres = json.loads(response.text)
    
    # print('************\n',jres)
    # # 기본 URL과 쿼리 매개변수 딕셔너리
    # https://www.shinyoung.com/files/20240216/4b64adc924e8e.pdf
    base_url = 'https://www.shinyoung.com/files/'
    # params = {
    #     'cmsCd': jres['CMS_CD'],
    #     'ntNo': jres['NT_NO'],
    #     'fNo': jres['FNO'], # PDF
    #     'fNm': jres['FNM']
    # }
    url = base_url + jres['FILEINFO']['FILEPATH']
    # if params:
    #     print('urlparse(params)', urlparse.urlencode(params))
    #     encoded_params = urlparse.urlencode(params)  # 쿼리 매개변수를 인코딩
    #     url += '?' + encoded_params

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
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
        }
        
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
            title_element = post.select_one(".subject a")
            if not title_element:  # 제목 요소가 없는 경우
                continue  # 건너뜁니다.
            title = title_element.get_text()  # strip 제거
            attachment_element = post.select_one(".bbsList_layer_icon a")
            attachment_link = "없음"
            if attachment_element:
                attachment_link = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"]).group(1)
            print("제목:", title)
            print("첨부 파일:", attachment_link)
            print()

        # soupList = posts

        nNewArticleCnt = 0
        
        for list in soupList:
            LIST_ARTICLE_TITLE = list.select_one(".subject a").text
            LIST_ARTICLE_URL = "없음"
            attachment_element = list.select_one(".bbsList_layer_icon a")
            if attachment_element:
                LIST_ARTICLE_URL = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"]).group(1)
                # ATTACH_URL = LIST_ARTICLE_URL
                LIST_ARTICLE_TITLE = list.select_one(".subject a").find_all(string=True)
                LIST_ARTICLE_TITLE = " : ".join(LIST_ARTICLE_TITLE)
                DOWNLOAD_URL = LIST_ARTICLE_URL

            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

    # 메모리 정리
    del soup
    # del response
    gc.collect()

    return nNewArticleCnt

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
            "stdate": '20231023',
            "eddate": GetCurrentDate("yyyymmdd"),
            "f_keyField": '', 
            "f_key": '',
            "_reqAgent": 'ajax',
            "dummyVal": 0
        }

        try:
            response = requests.post(TARGET_URL,data=payload)
            # print(response.text)
            jres = json.loads(response.text)
        except:
            return 0
            
        if jres['totalCount'] == 0 : return ''

        # print(jres['researchList'])
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        
        soupList = jres['researchList']

        nNewArticleCnt = 0
        
        # JSON To List
        for list in soupList:
            # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
            # print(list)
            # 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb=CR&attaFile=1650493541463.pdf&makeDt=2022.04.21'
            LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}' 
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(list['rMenuGb'],  list['attaFile'], list['makeDt'])
            LIST_ARTICLE_TITLE = list['titl']

            DOWNLOAD_URL = LIST_ARTICLE_URL

            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

    # 메모리 정리
    del soupList
    del response
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

        jres = ''
        try:
            response = requests.post(url=TARGET_URL ,data=payload , headers={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'})
            # print(response.text)
            jres = json.loads(response.text)
        except:
            return 0
            
        # print(jres['data_list'])
        
        
        REG_DATE = jres['data_list'][0]['REG_DATE'].strip()
        FILE_NAME = jres['data_list'][0]['UPLOAD_FILE1'].strip()
        # print('REG_DATE:',REG_DATE)
        # print('FILE_NAME:',FILE_NAME)

        soupList = jres['data_list']
        
        nNewArticleCnt = 0
        
        # JSON To List
        for list in soupList:
            # print(list)
            # https://www.hmsec.com/documents/research/20230103075940673_ko.pdf
            DOWNLOAD_URL = 'https://www.hmsec.com/documents/research/{}' 
            DOWNLOAD_URL = DOWNLOAD_URL.format(list['UPLOAD_FILE1'])

            # https://docs.hmsec.com/SynapDocViewServer/job?fid=#&sync=true&fileType=URL&filePath=#
            LIST_ARTICLE_URL = 'https://docs.hmsec.com/SynapDocViewServer/job?fid={}&sync=true&fileType=URL&filePath={}' 
            LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(DOWNLOAD_URL, DOWNLOAD_URL)

            LIST_ARTICLE_TITLE = list['SUBJECT']

            REG_DATE = jres['data_list'][0]['REG_DATE'].strip()
            # print(jres['data_list'])
            SERIAL_NO = jres['data_list'][0]['SERIAL_NO']
            # print('REG_DATE:',REG_DATE)

            # LIST_ARTICLE_URL = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
            # ATTACH_FILE_NAME = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')

            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=DOWNLOAD_URL,
                article_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

    # 메모리 정리
    del soupList
    del response
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

        # for title, link in zip(title_elements, link_elements):
        #     # 제목 출력
        #     print("제목:", title.text)
        #     # onClick 프로퍼티값(링크) 출력
        #     print("링크:", link.get_attribute("onclick"))
        
        nNewArticleCnt = 0
        
        
        # List
        for title, link in zip(title_elements, link_elements):
            LIST_ARTICLE_TITLE = title.text
            LIST_ARTICLE_URL = link.get_attribute("onclick")

            LIST_ARTICLE_URL = Koreainvestment_GET_LIST_ARTICLE_URL(LIST_ARTICLE_URL)
            DOWNLOAD_URL = LIST_ARTICLE_URL

            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수
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
    # del soup
    # del response
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
        # print(soup)
        soupList = soup.select('tr > td.al > a')
        
        # print('*' *40)
        # print(soupList[0])
        # print('*' *40)

        # 응답 처리
        if response.status_code != 200:
            print("요청이 실패했습니다.")
            print("상태 코드:", response.status_code)
        
        nNewArticleCnt = 0
        
        for list in soupList:
            # print(list)
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

            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

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

        # 헤더 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        }

        jres = ''
        response = requests.get(TARGET_URL, headers=headers)
        # 응답 확인
        if response.status_code == 200:
            jres = response.json()
        else:
            print("요청에 실패했습니다. 상태 코드:", response.status_code)
            response.raise_for_status()  # 오류가 발생하면 예외를 발생시킵니다.
        
        # HTML parse
        soupList = jres['result']['list']
        
        print('*' *40)
        print(soupList)
        print(len(soupList))
        
        print('*' *40)
        
        nNewArticleCnt = 0
        for list in soupList:
            # print(list)
            LIST_ARTICLE_TITLE = list['title']
            LIST_ARTICLE_URL   =  list['files'][0]['filePath']
            print(LIST_ARTICLE_TITLE)
            print(LIST_ARTICLE_URL)
            return 
            parts = LIST_ARTICLE_URL.split(',')
            if len(parts) != 3:
                return "잘못된 입력 형식입니다."
            
            path = parts[0].split("'")[1]
            filename = parts[1].split("'")[1]
            research_id = parts[2].split(")")[0]
            
            LIST_ARTICLE_URL = f"https://www.ktb.co.kr/common/download.jspx?cmd=viewPDF&path={path}/{filename}"
            DOWNLOAD_URL = LIST_ARTICLE_URL

            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수

    # 메모리 정리
    del soup, soupList
    del response
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
            # 제목 파싱
            print('???',list)
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
            print("제목:", title)
            print("첨부 파일:", attachment_link)
            print()
            LIST_ARTICLE_TITLE = title
            LIST_ARTICLE_URL = attachment_link
            DOWNLOAD_URL     = attachment_link
            if save_data_to_local_json(
                filename='./json/data_main_daily_send.json',
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER,
                firm_nm=firm_info.get_firm_name(),
                attach_url=LIST_ARTICLE_URL,
                download_url=DOWNLOAD_URL,
                article_title=LIST_ARTICLE_TITLE): nNewArticleCnt += 1 # 새로운 게시글 수
            


    # 메모리 정리
    del soupList, list
    gc.collect()

    return nNewArticleCnt

def main():
    # 사용자의 홈 디렉토리 가져오기
    HOME_PATH = os.path.expanduser("~")

    # log 디렉토리 경로
    LOG_PATH = os.path.join(HOME_PATH, "log")

    # log 디렉토리가 존재하지 않으면 생성
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)

    # log 디렉토리 경로
    LOG_PATH = os.path.join(LOG_PATH, GetCurrentDate('YYYYMMDD'))

    # daily log 디렉토리가 존재하지 않으면 생성
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)

    # 현재 스크립트의 이름 가져오기
    script_filename = os.path.basename(__file__)
    script_name = script_filename.split('.')
    script_name = script_name[0]
    print('script_filename', script_filename)
        
    # log 파일명
    LOG_FILENAME =  GetCurrentDate('YYYYMMDD')+ '_' + script_name + ".dbg"
    print('__file__', __file__, LOG_FILENAME)
    # log 전체경로
    LOG_FULLFILENAME = os.path.join(LOG_PATH, LOG_FILENAME)
    print('LOG_FULLFILENAME',LOG_FULLFILENAME)
    # logging.basicConfig(filename=LOG_FULLFILENAME, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    # print("LOG_FULLFILENAME",LOG_FULLFILENAME)
    # logging.debug('이것은 디버그 메시지입니다.')
    insert_data()
    # check functions 리스트
    check_functions = [
        LS_checkNewArticle,
        ShinHanInvest_checkNewArticle,
        NHQV_checkNewArticle,
        HANA_checkNewArticle,
        KB_checkNewArticle,
        Samsung_checkNewArticle,
        Sangsanginib_checkNewArticle, # 주석 처리된 부분
        Shinyoung_checkNewArticle,
        Miraeasset_checkNewArticle,
        Hmsec_checkNewArticle,
        Kiwoom_checkNewArticle,
        Koreainvestment_selenium_checkNewArticle,
        DAOL_checkNewArticle,
        TOSSinvest_checkNewArticle,
        Leading_checkNewArticle,
    ]

    for check_function in check_functions:
        print(f"{check_function.__name__} => 새 게시글 정보 확인")
        cnt = check_function() 
        time.sleep(1)
        if cnt:
            print(f"{check_function.__name__} => 새 게시글 Insert 성공 ==> {cnt}개")
            insert_data()
            
        else:
            print(f"{check_function.__name__} => 새 게시글 Insert 실패 혹은 없음 ?")

if __name__ == "__main__":
    main()