# -*- coding:utf-8 -*- 
import os
import sys
# import urlparse
import telegram
import requests
import datetime
import time
import ssl
import json
import re
import pymysql
import pymysql.cursors
from typing import List
from bs4 import BeautifulSoup
#from urllib.parse import urlparse
import urllib.parse as urlparse
import urllib.request


from requests import get  # to make GET request

# 로직 설명
# 1. Main()-> 각 회사별 함수를 통해 반복 (추후 함수명 일괄 변경 예정)
#   - checkNewArticle -> parse -> downloadFile -> Send 
# 2. 연속키의 경우 현재 .key로 저장
#   - 추후 heroku db로 처리 예정(MySQL)
#   - DB연결이 안되는 경우, Key로 처리할수 있도록 예외처리 반영
# 3. 최초 조회되는 게시판 혹은 Key값이 없는 경우 메세지를 발송하지 않음.
# 4. 테스트와 운영을 구분하여 텔레그램 발송 채널 ID 구분 로직 추가
#   - 어떻게 구분지을지 생각해봐야함
# 5. 메시지 발송 방법 변경 (봇 to 사용자 -> 채널에 발송)

############공용 상수############
# 메시지 발송 ID
CHAT_ID = '-1001431056975' # 운영 채널(증권사 신규 레포트 게시물 알림방)
# CHAT_ID = '-1001474652718' # 테스트 채널
# CHAT_ID = '-1001436418974' # 네이버 실시간 속보 뉴스 채널
# CHAT_ID = '-1001150510299' # 네이버 많이본 뉴스 채널
# CHAT_ID = '-1001472616534' # 아이투자


# DATABASE
CLEARDB_DATABASE_URL = 'mysql://b0464b22432146:290edeca@us-cdbr-east-03.cleardb.com/heroku_31ee6b0421e7ff9?reconnect=true'

# 게시글 갱신 시간
REFRESH_TIME = 600

# 회사이름
FIRM_NAME = (
    "이베스트 투자증권",    # 0
    "흥국증권",             # 1
    "상상인증권",           # 2
    "하나금융투자",          # 3
    "한양증권",              # 4
    "삼성증권",              # 5
    "교보증권"              # 6
    # "유안타증권",           # 4
)

# 게시판 이름
BOARD_NAME = (
    [ "이슈브리프" , "기업분석", "산업분석", "투자전략", "Quant" ], # 0
    [ "투자전략", "산업/기업분석" ],                            # 1
    [ "산업리포트", "기업리포트" ],                             # 2
    [ "산업분석", "기업분석", "Daily" ],                       # 3
    [ "기업분석", "산업 및 이슈분석" ],                          # 4
    [ "국내기업분석", "국내산업분석", "해외기업분석" ],              # 5
    [ " " ]                                                 # 6 (교보는 게시판 내 게시판 분류 사용)
    # [ "투자전략", "Report & Note", "해외주식" ],               # 4 => 유안타 데이터 보류 
)

EBEST_BOARD_NAME  = ["이슈브리프" , "기업분석", "산업분석", "투자전략", "Quant"]
HEUNGKUK_BOARD_NAME = ["투자전략", "산업/기업분석"]
SANGSANGIN_BOARD_NAME = ["산업리포트", "기업리포트"]
HANA_BOARD_NAME = ["산업분석", "기업분석", "Daily"]
HANYANG_BOARD_NAME = ["기업분석", "산업분석"]
HMSEC_BOARD_NAME = ["투자전략", "Report & Note", "해외주식"]
SAMSUNG_BOARD_NAME  = ["국내기업분석", "국내산업분석", "해외기업분석"]
# pymysql 변수
conn    = ''
cursor  = ''

# 연속키URL
NXT_KEY = ''
# 텔레그램 채널 발송 여부
SEND_YN = ''
# 첫번째URL 
FIRST_ARTICLE_URL = ''

# LOOP 인덱스 변수
SEC_FIRM_ORDER = 0 # 증권사 순번
ARTICLE_BOARD_ORDER = 0 # 게시판 순번

# 이모지
EMOJI_FIRE = u'\U0001F525'
EMOJI_PICK = u'\U0001F449'

# 연속키용 상수
FIRST_ARTICLE_INDEX = 0

# 메세지 전송용 레포트 제목(말줄임표 사용 증권사)
LIST_ARTICLE_TITLE = ''

def EBEST_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER
    SEC_FIRM_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 이슈브리프
    TARGET_URL_0 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=146&left_menu_no=211&front_menu_no=1029&parent_menu_no=211'
    # 기업분석 게시판
    TARGET_URL_1 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=36&left_menu_no=211&front_menu_no=212&parent_menu_no=211'
    # 산업분석
    TARGET_URL_2 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=37&left_menu_no=211&front_menu_no=213&parent_menu_no=211'
    # 투자전략
    TARGET_URL_3 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=38&left_menu_no=211&front_menu_no=214&parent_menu_no=211'
    # Quant
    TARGET_URL_4 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=147&left_menu_no=211&front_menu_no=1036&parent_menu_no=211'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)

def EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global LIST_ARTICLE_TITLE

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#contents > table > tbody > tr > td.subject > a')
    
    ARTICLE_BOARD_NAME = EBEST_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + soupList[FIRST_ARTICLE_INDEX].attrs['href'].replace("amp;", "")

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + list.attrs['href'].replace("amp;", "")
        LIST_ARTICLE_TITLE = list.text

        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y':
            EBEST_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)
            return True

def EBEST_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME
    global LIST_ARTICLE_TITLE

    ATTACH_BASE_URL = 'https://www.ebestsec.co.kr/_bt_lib/util/download.jsp?dataType='

    webpage = requests.get(ARTICLE_URL, verify=False)
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    # 게시글 제목(게시판 리스트의 제목은 짤려서 본문 제목 사용)
    table = soup.select_one('#contents > table')
    tbody = table.select_one('tbody')
    trs = soup.select('tr')
    LIST_ARTICLE_TITLE = trs[0].select_one('td').text
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a')['href']
    ATTACH_URL = attachFileCode.replace('Javascript:download("', ATTACH_BASE_URL).replace('")', '')
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').text.strip()
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def HeungKuk_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 1
    requests.packages.urllib3.disable_warnings()

    # 흥국 투자전략
    TARGET_URL_0 = 'http://www.heungkuksec.co.kr/research/industry/list.do'
    # 흥국 산업/기업 분석
    TARGET_URL_1 = 'http://www.heungkuksec.co.kr/research/company/list.do'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        HeungKuk_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def HeungKuk_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#content > table > tbody > tr > td.left > a')

    ARTICLE_BOARD_NAME = HEUNGKUK_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?' + soupList[FIRST_ARTICLE_INDEX]['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
    
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?'+list['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
        LIST_ARTICLE_TITLE = list.text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            HeungKuk_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
            return True

def HeungKuk_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME

    try:
        webpage = requests.get(ARTICLE_URL, verify=False)
        
        # 첨부파일 URL
        attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('div.div_01 > a')['href']
        ATTACH_URL = 'http://www.heungkuksec.co.kr/' + attachFileCode
        # 첨부파일 이름
        ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('td.col_b669ad.left').text.strip()+ ".pdf"
    except:
        print('크롤링오류 혹은 첨부파일 없음')
        return
    else:
        
        DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
        time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def SangSangIn_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 2

    requests.packages.urllib3.disable_warnings()

    # 상상인 투자전략
    TARGET_URL_0 =  'http://www.sangsanginib.com/noticeList.fn?sgrp=S01&siteCmsCd=CM0001&topCmsCd=CM0004&cmsCd=CM0338&pnum=2&cnum=3'
    #  산업/기업 분석
    TARGET_URL_1 =  'http://www.sangsanginib.com/stocksList.fn?sgrp=S01&siteCmsCd=CM0001&topCmsCd=CM0004&cmsCd=CM0079&pnum=3&cnum=4'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        SangSangIn_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def SangSangIn_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#contents > div > div.bbs_a_type > table > tbody > tr > td.con > a')
    ARTICLE_BOARD_NAME = SANGSANGIN_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'http://www.sangsanginib.com' + soupList[FIRST_ARTICLE_INDEX]['href'] #.replace("nav.go('view', '", "").replace("');", "").strip()
    
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.sangsanginib.com' +list['href']
        LIST_ARTICLE_TITLE = list.text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            SangSangIn_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
            return True

def SangSangIn_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME

    webpage = requests.get(ARTICLE_URL, verify=False)
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a')['href']
    ATTACH_URL = 'http://www.sangsanginib.com' + attachFileCode
    
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a').text.strip()
    
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def HANA_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 3

    requests.packages.urllib3.disable_warnings()

    # 하나금융 Daily
    TARGET_URL_0 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=4&cid=1'
    # 하나금융 산업 분석
    TARGET_URL_1 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=1'
    # 하나금융 기업 분석
    TARGET_URL_2 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=2'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

    ARTICLE_BOARD_NAME = HANA_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li:nth-child(1)> div.con > ul > li.mb4 > h3 > a:nth-child(1)')[FIRST_ARTICLE_INDEX].text.strip()
    FIRST_ARTICLE_URL =  'https://www.hanaw.com' + soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li:nth-child(1)> div.con > ul > li:nth-child(5)> div > a')[FIRST_ARTICLE_INDEX].attrs['href']

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').text.strip()
        LIST_ARTICLE_URL =  'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
        LIST_ATTACT_FILE_NAME = list.select_one('div.con > ul > li:nth-child(5)> div > a').text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            HANA_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
            return True

def HANA_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME #BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a').text.strip()
    
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def HANYANG_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 4

    requests.packages.urllib3.disable_warnings()

    # 한양증권 기업분석
    TARGET_URL_0 =  'http://www.hygood.co.kr/board/researchAnalyzeCompany/list'
    # 한양증권 산업분석
    TARGET_URL_1 =  'http://www.hygood.co.kr/board/researchAnalyzeIssue/list'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        HANYANG_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def HANYANG_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#content > div.content_area > table > tbody > tr')

    ARTICLE_BOARD_NAME = HANYANG_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soup.select('#content > div.content_area > table > tbody > tr:nth-child(1) > td.tx_left > a')[FIRST_ARTICLE_INDEX].text.strip()
    FIRST_ARTICLE_URL =  'http://www.hygood.co.kr' + soup.select('#content > div.content_area > table > tbody > tr:nth-child(1) > td.tx_left > a')[FIRST_ARTICLE_INDEX].attrs['href']
    FIRST_ARTICLE_URL_f = FIRST_ARTICLE_URL.split(";")[0]
    FIRST_ARTICLE_URL_b = FIRST_ARTICLE_URL.split("?")[1]
    FIRST_ARTICLE_URL = FIRST_ARTICLE_URL_f + "?" + FIRST_ARTICLE_URL_b
    
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_TITLE = list.select_one('td.tx_left > a').text.strip()
        LIST_ARTICLE_URL   =  'http://www.hygood.co.kr' + list.select_one('td.tx_left > a').attrs['href']
        LIST_ARTICLE_URL_f = LIST_ARTICLE_URL.split(";")[0]
        LIST_ARTICLE_URL_b = LIST_ARTICLE_URL.split("?")[1]
        LIST_ARTICLE_URL = LIST_ARTICLE_URL_f + "?" + LIST_ARTICLE_URL_b

        LIST_ATTACT_FILE_URL = list.select_one('td:nth-child(4) > a').attrs['href']
        LIST_ATTACT_FILE_NAME = LIST_ARTICLE_TITLE.split(":")[0].strip() + ".pdf"

        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y':
            HANYANG_downloadFile(LIST_ATTACT_FILE_URL, LIST_ATTACT_FILE_NAME)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)
            return True


def HANYANG_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME #BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a').text.strip()
    
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def Samsung_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 5

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
        Samsung_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def Samsung_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#content > section.bbsLstWrap > ul > li')

    ARTICLE_BOARD_NAME = SAMSUNG_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soup.select('#content > section.bbsLstWrap > ul > li:nth-child(1)> a > dl > dt > strong')[FIRST_ARTICLE_INDEX].text.strip()
    a_href =soup.select('#content > section.bbsLstWrap > ul > li:nth-child(1)> a')[FIRST_ARTICLE_INDEX].attrs['href']
    a_href = a_href.replace('javascript:downloadPdf(', '').replace(';', '')
    a_href = a_href.split("'")
    a_href = a_href[1]
    FIRST_ARTICLE_URL =  'https://www.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName=' + a_href+ '&contentType=application/pdf'

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_TITLE = list.select('#content > section.bbsLstWrap > ul > li > a > dl > dt > strong')[FIRST_ARTICLE_INDEX].text.strip()
        a_href = list.select('#content > section.bbsLstWrap > ul > li > a')[FIRST_ARTICLE_INDEX].attrs['href']
        a_href = a_href.replace('javascript:downloadPdf(', '').replace(';', '')
        a_href = a_href.split("'")
        a_href = a_href[1]
        LIST_ARTICLE_URL =  'https://www.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName=' + a_href+ '&contentType=application/pdf'
        fileNameArray = a_href.split("/")
        LIST_ATTACT_FILE_NAME = fileNameArray[1].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            Samsung_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
            return True

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
    return True

def Samsung_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME
    
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

# 교보증권의 경우 연속키를 첨부파일 URL을 사용합니다.
def KyoBo_checkNewArticle():
    global NXT_KEY
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 6
    ARTICLE_BOARD_ORDER = 0

    TARGET_URL = 'https://www.iprovest.com/weblogic/RSReportServlet?mode=list&menuCode=1&scr_id=32'
                 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('body > div > table > tbody > tr')

    FIRST_ARTICLE_TITLE = soup.select('body > div > table > tbody > tr:nth-child(1) > td.tLeft > div > a')[FIRST_ARTICLE_INDEX].text.strip()
    FIRST_ARTICLE_URL =  'https://www.iprovest.com' + soup.select('body > div > table > tbody > tr:nth-child(1) > td.tLeft > div > a')[FIRST_ARTICLE_INDEX].attrs['href'].strip()
    FIRST_ARTICLE_BOARD_NAME = soup.select('body > div > table > tbody > tr:nth-child(1) > td:nth-child(4) > i')[FIRST_ARTICLE_INDEX].text.strip()

    FIRST_ATTACT_FILE_URL = soup.select('body > div > table > tbody > tr:nth-child(1) > td:nth-child(7) > a')[FIRST_ARTICLE_INDEX].attrs['href'].strip()
    FIRST_ATTACT_FILE_URL = FIRST_ATTACT_FILE_URL.split("'")
    FIRST_ATTACT_FILE_URL = 'https://www.iprovest.com' + FIRST_ATTACT_FILE_URL[1].strip()

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)
    print('FIRST_ARTICLE_BOARD_NAME:',FIRST_ARTICLE_BOARD_NAME)
    print('FIRST_ATTACT_FILE_URL:',FIRST_ATTACT_FILE_URL)
    
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER])
        print(FIRM_NAME[SEC_FIRM_ORDER], '증권사의 경우 게시판 연속키를 통합하여 사용합니다 ARTICLE_BOARD_ORDER = 0')
        print('교보증권은 첨부파일 URL을 연속키로 사용합니다.')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER], '게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        print(FIRM_NAME[SEC_FIRM_ORDER], '증권사의 경우 게시판 연속키를 통합하여 사용합니다 ARTICLE_BOARD_ORDER = 0')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ATTACT_FILE_URL)

    print('첫번째 게시글URL:', FIRST_ATTACT_FILE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        ## 연속키는 게시글 URL 사용##

        LIST_ARTICLE_TITLE = list.select_one('body > div > table > tbody > tr > td.tLeft > div > a').text.strip()
        LIST_ARTICLE_URL =  'https://www.iprovest.com' + list.select_one('body > div > table > tbody > tr > td.tLeft > div > a').attrs['href'].strip()
        SEND_LIST_ARTICLE_URL = LIST_ARTICLE_URL
        # 통합 게시판 이므로 게시글의 분류된 게시판 이름을 사용
        LIST_ARTICLE_BOARD_NAME =  list.select_one('body > div > table > tbody > tr > td:nth-child(4) > i').text.strip()
        ARTICLE_BOARD_NAME = LIST_ARTICLE_BOARD_NAME
        
        # 게시글 리스트에서 첨부파일 URL 획득
        LIST_ATTACT_FILE_URL = list.select_one('body > div > table > tbody > tr > td:nth-child(7) > a').attrs['href'].strip()
        LIST_ATTACT_FILE_URL = LIST_ATTACT_FILE_URL.split("'")
        # 게시글의 URL에서 파일이름 분리1
        LIST_ATTACT_FILE_NAME = LIST_ATTACT_FILE_URL[1].strip()
        LIST_ATTACT_FILE_URL = 'https://www.iprovest.com' + LIST_ATTACT_FILE_URL[1].strip()
        # 게시글의 URL에서 파일이름 분리2
        LIST_ATTACT_FILE_NAME = LIST_ATTACT_FILE_NAME.split("/")
        for r in LIST_ATTACT_FILE_NAME:
            if ".pdf" in r : LIST_ATTACT_FILE_NAME = r
        print(LIST_ATTACT_FILE_NAME)
        print('### 확인 구간###')
        print('NXT_KEY', NXT_KEY)
        print('LIST_ARTICLE_URL', LIST_ARTICLE_URL)
        print('LIST_ATTACT_FILE_URL', LIST_ATTACT_FILE_URL)
        
        if ( NXT_KEY != LIST_ATTACT_FILE_URL or NXT_KEY == '' ) and SEND_YN == 'Y':
            LIST_ARTICLE_URL = LIST_ATTACT_FILE_URL # 첨부파일 URL
            KyoBo_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME)
            LIST_ARTICLE_URL = SEND_LIST_ARTICLE_URL
            send(ARTICLE_BOARD_NAME, LIST_ARTICLE_TITLE, LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ATTACT_FILE_URL)
            return True

    return True

def KyoBo_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME
    print('첨부파일이름 :',ATTACH_FILE_NAME)
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

def Itooza_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 997
    ARTICLE_BOARD_ORDER = 997

    requests.packages.urllib3.disable_warnings()

    # 아이투자랭킹스탁
    TARGET_URL_0 =  'http://www.itooza.com/stock/stock_sub.htm?ss=16'
    # 아이투자 종목정보
    TARGET_URL_1 =  'http://www.itooza.com/stock/stock_sub.htm?ss=10'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        Itooza_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def Itooza_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    if ARTICLE_BOARD_ORDER == 1 : return 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#article-list > div.list-body > table > tbody > tr')

    ARTICLE_BOARD_NAME = "랭킹스탁"
    try:
        FIRST_ARTICLE_TITLE = soup.select('#article-list > div.list-body > table > tbody > tr:nth-child(1) > td.t > a')[FIRST_ARTICLE_INDEX].text.strip()
        FIRST_ARTICLE_URL   = soup.select('#article-list > div.list-body > table > tbody > tr:nth-child(1) > td.t > a')[FIRST_ARTICLE_INDEX].attrs['href']
    except:
        FIRST_ARTICLE_TITLE = soup.select('#article-list > div.list-body > table > tbody > tr:nth-child(1) > td.t > b > a')[FIRST_ARTICLE_INDEX].text.strip()
        FIRST_ARTICLE_URL   = soup.select('#article-list > div.list-body > table > tbody > tr:nth-child(1) > td.t > b > a')[FIRST_ARTICLE_INDEX].attrs['href']
        
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','아이투자','의 ', ARTICLE_BOARD_NAME)

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ','아이투자','의 ', ARTICLE_BOARD_NAME,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        try:
            LIST_ARTICLE_TITLE = list.select_one('td.t > a').text.strip()
            LIST_ARTICLE_URL   = list.select_one('td.t > a').attrs['href']
        except:
            LIST_ARTICLE_TITLE = list.select_one('td.t > b > a').text.strip()
            LIST_ARTICLE_URL   = list.select_one('td.t > b > a').attrs['href']

        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y':
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            Itooza_downloadFile(LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)
            return True

def Itooza_downloadFile(ARTICLE_URL):
    webpage = requests.get(ARTICLE_URL, verify=False)
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('img.bodyaddimage')
    print(attachFileCode)
    print(len(attachFileCode.text))
    
    if attachFileCode is None or attachFileCode == 'None': return print("아이투자 게시글에 이미지가 존재 하지 않습니다. ")
    ATTACH_URL = attachFileCode.attrs['src']
    sendPhoto(ATTACH_URL)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

###

def NAVERNews_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 998
    ARTICLE_BOARD_ORDER = 998

    requests.packages.urllib3.disable_warnings()

    # 네이버 실시간 속보
    TARGET_URL_0 = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=flashnews'
    
    # 네이버 많이 본 뉴스
    TARGET_URL_1 = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=ranknews'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        NAVERNews_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
# JSON API 타입
def NAVERNews_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    request = urllib.request.Request(TARGET_URL)
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("네이버 뉴스 접속이 원활하지 않습니다 ")

    jres = json.loads(response.read().decode('utf-8'))
    jres = jres['result']

    FIRST_ARTICLE_TITLE = jres['newsList'][0]['tit'].strip()
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','(네이버 뉴스)')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', '(네이버 뉴스)')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # NaverNews 게시판에 따른 URL 지정
    if ARTICLE_BOARD_ORDER == 0:category = 'flashnews'
    else:                      category = 'ranknews'

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for news in jres['newsList']:
        LIST_ARTICLE_URL = 'https://m.stock.naver.com/news/read.nhn?category='+ category + '&officeId=' + news['oid'] + '&articleId=' + news['aid']
        LIST_ARTICLE_TITLE = news['tit'].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0:
                print('새로운 게시물을 모두 발송하였습니다.')
            else:
                sendText(sendMessageText)

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
            return True

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
    return True

def NAVERNews_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME #BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a').text.strip()
    
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

def SEDAILY_checkNewArticle():
    global NXT_KEY
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 999
    ARTICLE_BOARD_ORDER = 999

    ARTICLE_BOARD_NAME = ''

    TARGET_URL = 'https://www.sedaily.com/Search/Search/SEList?Page=1&scDetail=&scOrdBy=0&catView=AL&scText=%EA%B8%B0%EA%B4%80%C2%B7%EC%99%B8%EA%B5%AD%EC%9D%B8%C2%B7%EA%B0%9C%EC%9D%B8%20%EC%88%9C%EB%A7%A4%EC%88%98%C2%B7%EB%8F%84%20%EC%83%81%EC%9C%84%EC%A2%85%EB%AA%A9&scPeriod=1w&scArea=t&scTextIn=&scTextExt=&scPeriodS=&scPeriodE=&command=&_=1612164364267'
                 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#NewsDataFrm > ul > li > a[href]')

    FIRST_ARTICLE_URL = 'https://www.sedaily.com'+soupList[FIRST_ARTICLE_INDEX].attrs['href']
    FIRST_ARTICLE_TITLE = soup.select_one('#NewsDataFrm > ul > li:nth-child(1) > a > div.text_area > h3').text.replace("[표]", "")
    
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','sedaily','의 ', '매매동향')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', 'sedaily','의 ', '매매동향' ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.sedaily.com'+list.attrs['href']
        LIST_ARTICLE_TITLE = list.select_one('div.text_area > h3').text.replace("[표]", "")

        if ( (NXT_KEY != LIST_ARTICLE_TITLE and "최종치" not in LIST_ARTICLE_TITLE) or NXT_KEY == '' ) and SEND_YN == 'Y':
            send(ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            SEDAILY_downloadFile(LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            if "최종치" in LIST_ARTICLE_TITLE : print('매매 동향 최종치 게시물은 보내지 않습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
            return True

    return True

def SEDAILY_downloadFile(ARTICLE_URL):
    webpage = requests.get(ARTICLE_URL, verify=False)
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('#v-left-scroll-in > div.article_con > div.con_left > div.article_view > figure > p > img')
    print(attachFileCode)
    ATTACH_URL = attachFileCode.attrs['src']
    sendPhoto(ATTACH_URL)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

def YUANTA_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 4

    return
    requests.packages.urllib3.disable_warnings()

    # 유안타 투자전략
    TARGET_URL_0 =  'https://www.myasset.com/myasset/research/rs_list/rs_view.cmd?cd006=&cd007=RE02&cd008=&searchKeyGubun=&keyword=&jongMok_keyword=&keyword_in=&startCalendar=&endCalendar=&pgCnt=&page=&SEQ=167479'
    #  산업/기업 분석
    TARGET_URL_1 =  'https://www.myasset.com/myasset/research/rs_list/rs_list.cmd?cd006=&cd007=RE02&cd008='
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)
    
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        YUANTA_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(5)
 
def YUANTA_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#RS_0201001_P1_FORM > div.tblRow.txtC.mHide.noVLine.js-tblHead > table > tbody ')

    ARTICLE_BOARD_NAME = SANGSANGIN_BOARD_NAME[ARTICLE_BOARD_ORDER]
    FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    FIRST_ARTICLE_URL = 'http://www.sangsanginib.com' + soupList[FIRST_ARTICLE_INDEX]['href'] #.replace("nav.go('view', '", "").replace("');", "").strip()
    
    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'http://www.sangsanginib.com' +list['href']
        LIST_ARTICLE_TITLE = list.text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            YUANTA_downloadFile(LIST_ARTICLE_URL)
            send(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('새로운 게시물을 모두 발송하였습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
            return True

def YUANTA_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME

    webpage = requests.get(ARTICLE_URL, verify=False)
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a')['href']
    ATTACH_URL = 'http://www.sangsanginib.com' + attachFileCode
    
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a').text.strip()
    
    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# 최초 send함수
# URL(프리뷰해제) 발송 + 해당 레포트 pdf 발송
def send(ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    global CHAT_ID

    print('send()')
    DISABLE_WEB_PAGE_PREVIEW = True # 메시지 프리뷰 여부 기본값 설정

    # 실제 전송할 메시지 작성
    sendMessageText = ''
    sendMessageText += GetSendMessageTitle(ARTICLE_TITLE)
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 :',me)

    if SEC_FIRM_ORDER == 999 or SEC_FIRM_ORDER == 998 or SEC_FIRM_ORDER == 997 : # 매매동향의 경우 URL만 발송하여 프리뷰 처리 
        DISABLE_WEB_PAGE_PREVIEW = False


    # if SEC_FIRM_ORDER == 998:
    #     if  ARTICLE_BOARD_ORDER == 0 : 
    #         CHAT_ID = '-1001436418974' # 네이버 실시간 속보 뉴스 채널
    #     else:
    #         CHAT_ID = '-1001150510299' # 네이버 많이본 뉴스 채널
    # elif SEC_FIRM_ORDER == 997:
    #         CHAT_ID = '-1001472616534' # 아이투자
    # else:
    #     CHAT_ID = '-1001431056975' # 운영 채널(증권사 신규 레포트 게시물 알림방)

    bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = DISABLE_WEB_PAGE_PREVIEW)

    if DISABLE_WEB_PAGE_PREVIEW: # 첨부파일이 있는 경우 => 프리뷰는 사용하지 않음
        try:
            time.sleep(1) # 메시지 전송 텀을 두어 푸시를 겹치지 않게 함
            bot.sendDocument(chat_id = GetSendChatId(), document = open(ATTACH_FILE_NAME, 'rb'))
            os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
        except:
            return
    
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# URL 발신용 전용 함수 : ex) 네이버 뉴스
def sendURL(ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    global CHAT_ID

    print('sendURL()')

    # 실제 전송할 메시지 작성
    sendMessageText = ''
    sendMessageText += GetSendMessageTitle(ARTICLE_TITLE)
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 :',me)

    # if SEC_FIRM_ORDER == 998:
    #     if  ARTICLE_BOARD_ORDER == 0 : 
    #         CHAT_ID = '-1001436418974' # 네이버 실시간 속보 뉴스 채널
    #     else:
    #         CHAT_ID = '-1001150510299' # 네이버 많이본 뉴스 채널
    # elif SEC_FIRM_ORDER == 997:
    #         CHAT_ID = '-1001472616534' # 아이투자
    # else:
    #     CHAT_ID = '-1001431056975' # 운영 채널(증권사 신규 레포트 게시물 알림방)

    bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText)
    
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def sendPhoto(ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('sendPhoto()')

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    bot.sendPhoto(chat_id = GetSendChatId(), photo = ARTICLE_URL)
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

def sendText(sendMessageText): # 가공없이 텍스트를 발송합니다.
    global CHAT_ID

    print('sendText()')

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    my_token_key = '1372612160:AAHVyndGDmb1N2yEgvlZ_DmUgShqk2F0d4w'
    bot = telegram.Bot(token = my_token_key)

    # if SEC_FIRM_ORDER == 998:
    #     if  ARTICLE_BOARD_ORDER == 0 : 
    #         CHAT_ID = '-1001436418974' # 네이버 실시간 속보 뉴스 채널
    #     else:
    #         CHAT_ID = '-1001150510299' # 네이버 많이본 뉴스 채널
    # elif SEC_FIRM_ORDER == 997:
    #         CHAT_ID = '-1001472616534' # 아이투자
    # else:
    #     CHAT_ID = '-1001431056975' # 운영 채널(증권사 신규 레포트 게시물 알림방)

    bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# URL에 파일명을 사용할때 한글이 포함된 경우 인코딩처리 로직 추가 
def DownloadFile(URL, FILE_NAME):
    global ATTACH_FILE_NAME
    print("DownloadFile()")

    if SEC_FIRM_ORDER == 6: # 교보증권 예외 로직
        # 로직 사유 : 레포트 첨부파일명에 한글이 포함된 경우 URL처리가 되어 있지 않음
        CONVERT_URL = URL 
        for c in URL: # URL내 한글이 있는 경우 인코딩 처리(URL에 파일명을 이용하여 조합함)
            # 코드셋 기준 파이썬:UTF-8 . 교보증권:EUC-KR
            # 1. 주소에서 한글 문자를 판별
            # 2. 해당 문자를 EUC-KR로 변환후 URL 인코딩
            print("##",c , "##", ord('가') <= ord(c) <= ord('힣') )
            if ord('가') <= ord(c) <= ord('힣'): 
                c_encode = c.encode('euc-kr')
                CONVERT_URL = CONVERT_URL.replace(c, urlparse.quote(c_encode) )
                print(CONVERT_URL)

        if URL != CONVERT_URL: 
            print("기존 URL에 한글이 포함되어 있어 인코딩처리함")
            print("CONVERT_URL", CONVERT_URL)
            URL = CONVERT_URL

    ATTACH_FILE_NAME = re.sub('[\/:*?"<>|]','',FILE_NAME) # 저장할 파일명 : 파일명으로 사용할수 없는 문자 삭제 변환
    print('convert URL:',URL)
    print('convert ATTACH_FILE_NAME:',ATTACH_FILE_NAME)
    with open(ATTACH_FILE_NAME, "wb")as file:  # open in binary mode
        response = get(URL, verify=False)     # get request
        file.write(response.content) # write to file
        
    return True

def GetSendMessageText(INDEX, ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL):

    print('GetSendMessageText')
    # 실제 전송할 메시지 작성
    sendMessageText = ''
    # 발신 게시판 종류
    if INDEX == 1:
        sendMessageText += GetSendMessageTitle(ARTICLE_TITLE)
    # 게시글 제목(굵게)
    sendMessageText += "**" + ARTICLE_TITLE + "**" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")"
    sendMessageText += "\n" + "\n"

    return sendMessageText

def GetSendMessageTitle(ARTICLE_TITLE):

    print('GetSendMessageTitle')
    SendMessageTitle = ''
    if SEC_FIRM_ORDER == 999:
        msgFirmName = "매매동향"
        ARTICLE_BOARD_NAME = ''
        if  "최종치" in ARTICLE_TITLE:
            print('sedaily의 매매동향 최종치 집계 데이터는 메시지 발송을 하지 않습니다.') # 장마감 최종치는 발송 안함
            return 
    elif SEC_FIRM_ORDER == 998:
        msgFirmName = "네이버 - "
        if  ARTICLE_BOARD_ORDER == 0 :
            ARTICLE_BOARD_NAME = "실시간 뉴스 속보"
        else:
            ARTICLE_BOARD_NAME = "가장 많이 본 뉴스"
    elif SEC_FIRM_ORDER == 997:
        msgFirmName = "아이투자 - "
    else:
        msgFirmName = FIRM_NAME[SEC_FIRM_ORDER] + " - "
        if SEC_FIRM_ORDER != 6: 
            ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]

    SendMessageTitle += EMOJI_FIRE + msgFirmName + ARTICLE_BOARD_NAME + EMOJI_FIRE + "\n"
    
    return SendMessageTitle


def GetSendChatId():

    print('GetSendChatId')
    SendMessageChatId = 0
    if SEC_FIRM_ORDER == 998:
        if  ARTICLE_BOARD_ORDER == 0 : 
            SendMessageChatId = '-1001436418974' # 네이버 실시간 속보 뉴스 채널
        else:
            SendMessageChatId = '-1001150510299' # 네이버 많이본 뉴스 채널
    elif SEC_FIRM_ORDER == 997:
            SendMessageChatId = '-1001472616534' # 아이투자
    else:
        SendMessageChatId = '-1001431056975' # 운영 채널(증권사 신규 레포트 게시물 알림방)
    
    return SendMessageChatId

def MySQL_Open_Connect():
    global conn
    global cursor
    
    # clearDB 
    # url = urlparse.urlparse(os.environ['CLEARDB_DATABASE_URL'])
    url = urlparse.urlparse('mysql://b0464b22432146:290edeca@us-cdbr-east-03.cleardb.com/heroku_31ee6b0421e7ff9?reconnect=true')
    conn = pymysql.connect(host=url.hostname, user=url.username, password=url.password, charset='utf8', db=url.path.replace('/', ''), cursorclass=pymysql.cursors.DictCursor, autocommit=True)
    cursor = conn.cursor()
    return cursor

def DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
    global NXT_KEY
    global SEND_YN
    global conn
    global cursor

    cursor = MySQL_Open_Connect()
    dbQuery = "SELECT * FROM NXT_KEY WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s "
    dbResult = cursor.execute(dbQuery, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print('SEC_FIRM_ORDER',row['SEC_FIRM_ORDER'], 'ARTICLE_BOARD_ORDER',row['ARTICLE_BOARD_ORDER'], 'NXT_KEY',row['NXT_KEY'])
        NXT_KEY = row['NXT_KEY']
        SEND_YN = row['SEND_YN']
    conn.close()
    return dbResult

def DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY):
    global NXT_KEY
    global conn
    global cursor
    cursor = MySQL_Open_Connect()
    dbQuery = "INSERT INTO NXT_KEY (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY)VALUES ( %s, %s, %s);"
    cursor.execute(dbQuery, ( SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY ))
    NXT_KEY = FIRST_NXT_KEY
    conn.close()
    return NXT_KEY

def DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY):
    global NXT_KEY
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET NXT_KEY = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, ( FIRST_NXT_KEY, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER ))
    if dbResult:
        NXT_KEY = FIRST_NXT_KEY
    conn.close()
    return dbResult

def main():
    global SEC_FIRM_ORDER  # 증권사 순번
    print('########Program Start Run########')

    # SEC_FIRM_ORDER는 임시코드 추후 로직 추가 예정 
    while True:

        print("EBEST_checkNewArticle()=> 새 게시글 정보 확인") # 0
        EBEST_checkNewArticle()
        
        print("HeungKuk_checkNewArticle()=> 새 게시글 정보 확인") # 1
        HeungKuk_checkNewArticle()

        print("SangSangIn_checkNewArticle()=> 새 게시글 정보 확인") # 2
        SangSangIn_checkNewArticle()

        print("HANA_checkNewArticle()=> 새 게시글 정보 확인") # 3
        HANA_checkNewArticle()

        # print("HANYANG_checkNewArticle()=> 새 게시글 정보 확인") # 4
        # HANYANG_checkNewArticle()

        print("Samsung_checkNewArticle()=> 새 게시글 정보 확인") # 5
        Samsung_checkNewArticle()

        print("KyoBo_checkNewArticle()=> 새 게시글 정보 확인") # 6
        KyoBo_checkNewArticle()

        print("Itooza_checkNewArticle()=> 새 게시글 정보 확인") # 997 미활성
        Itooza_checkNewArticle()

        print("NAVERNews_checkNewArticle()=> 새 게시글 정보 확인") # 998 미활성
        NAVERNews_checkNewArticle()

        print("SEDAILY_checkNewArticle()=> 새 게시글 정보 확인") # 999
        SEDAILY_checkNewArticle()

        # print("YUANTA_checkNewArticle()=> 새 게시글 정보 확인") # 4 가능여부 불확실 => 보류
        # YUANTA_checkNewArticle()
        print('######',REFRESH_TIME,'초 후 게시글을 재 확인 합니다.######')
        time.sleep(REFRESH_TIME)

if __name__ == "__main__":
	main()
