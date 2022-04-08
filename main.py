# -*- coding:utf-8 -*- 
import os
import sys
import datetime
from pytz import timezone
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
#import urllib3.parse as urlparse
#import urllib3.request

#urllib3.disable_warnings()

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
# secrets 
CLEARDB_DATABASE_URL                                = ""
TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET              = ""
TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET             = ""
TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS                 = ""
TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS                  = ""
TELEGRAM_CHANNEL_ID_ITOOZA                          = ""
TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT                    = ""
TELEGRAM_CHANNEL_ID_REPORT_ALARM                    = ""
TELEGRAM_CHANNEL_ID_TEST                            = ""
TELEGRAM_USER_ID_DEV                                = ""
SECRETS = ""

# 게시글 갱신 시간
REFRESH_TIME = 60 * 20 # 20분

# 회사이름
FIRM_NAME = (
    "이베스트 투자증권",    # 0
    "흥국증권",             # 1
    "상상인증권",           # 2
    "하나금융투자",          # 3
    "한양증권",              # 4
    "삼성증권",              # 5
    "교보증권",              # 6
    "DS투자증권",             # 7
    "SMIC(서울대 가치투자)"             # 8
    # "유안타증권",           # 4
)

# 게시판 이름
BOARD_NAME = (
    [ "이슈브리프" , "기업분석", "산업분석", "투자전략", "Quant", "Macro", "FI/ Credit", "Commodity" ], # 0 = 이베스트
    [ "투자전략", "산업/기업분석" ],                            # 1
    [ "산업리포트", "기업리포트" ],                             # 2
    [ "Daily", "산업분석", "기업분석", "주식전략", "Small Cap", "기업 메모", "Quant", "포트폴리오", "투자정보" ],            # 3
    [ "기업분석", "산업 및 이슈분석" ],                          # 4
    [ "국내기업분석", "국내산업분석", "해외기업분석" ],              # 5
    [ " " ],                                                # 6 (교보는 게시판 내 게시판 분류 사용)
    [ "기업분석", "투자전략/경제분석"],                          # 7 
    [ "기업분석"]                                                # 7 
    
    # [ "투자전략", "Report & Note", "해외주식" ],               # 4 => 유안타 데이터 보류 
)


KYOBO_BOARD_NAME = ''
# pymysql 변수
conn    = ''
cursor  = ''

# 연속키URL
NXT_KEY = ''
# 텔레그램 채널 발송 여부
SEND_YN = ''
TODAY_SEND_YN = ''
# 텔레그램 마지막 메세지 발송시간(단위 초)
SEND_TIME_TERM = 0 # XX초 전에 해당 증권사 메시지 발송
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
    EBEST_URL_0 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=146&left_menu_no=211&front_menu_no=1029&parent_menu_no=211'
    # 기업분석 게시판
    EBEST_URL_1 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=36&left_menu_no=211&front_menu_no=212&parent_menu_no=211'
    # 산업분석
    EBEST_URL_2 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=37&left_menu_no=211&front_menu_no=213&parent_menu_no=211'
    # 투자전략
    EBEST_URL_3 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=38&left_menu_no=211&front_menu_no=214&parent_menu_no=211'
    # Quant
    EBEST_URL_4 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=147&left_menu_no=211&front_menu_no=1036&parent_menu_no=211'
    # Macro
    EBEST_URL_5 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=39&left_menu_no=211&front_menu_no=215&parent_menu_no=211'
    # FI/ Credit
    EBEST_URL_6 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=183&left_menu_no=211&front_menu_no=1344&parent_menu_no=211'
    # Commodity
    EBEST_URL_7 = 'https://www.ebestsec.co.kr/EtwFrontBoard/List.jsp?board_no=145&left_menu_no=211&front_menu_no=1009&parent_menu_no=211'

    EBEST_URL_TUPLE = (EBEST_URL_0, EBEST_URL_1, EBEST_URL_2, EBEST_URL_3, EBEST_URL_4, EBEST_URL_5, EBEST_URL_6, EBEST_URL_7)

    ## EBEST만 로직 변경 테스트
    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(EBEST_URL_TUPLE):
        sendMessageText += EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    # 발송전 연속키 재 조회후 중복발송 필터링
    DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    print("SEND_TIME_TERM", SEND_TIME_TERM)
    if len(sendMessageText) > 0 and SEND_TIME_TERM > 1200 : sendText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)

def EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global LIST_ARTICLE_TITLE

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#contents > table > tbody > tr > td.subject > a')
    
    ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
    try:
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    except IndexError:
        return 

    try:
        FIRST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + soupList[FIRST_ARTICLE_INDEX].attrs['href'].replace("amp;", "")
    except:
        FIRST_ARTICLE_URL = ''

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

        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y' and 'test' not in FIRST_ARTICLE_TITLE :
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = 'https://docs.google.com/viewer?embedded=true&url='+EBEST_downloadFile(LIST_ARTICLE_URL)
                # sendMessageText += GetSendMessageTextMarkdown(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL, ATTACH_URL = ATTACH_URL)
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        elif 'test' in FIRST_ARTICLE_TITLE:
            print("test 게시물은 연속키 처리를 제외합니다.")
            # return True
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL, FIRST_ARTICLE_TITLE)
            return sendMessageText

    print(sendMessageText)
    return sendMessageText

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
    ATTACH_URL = attachFileCode.replace('Javascript:download("', ATTACH_BASE_URL).replace('")', '').replace('https', 'http')
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').text.strip()
    # DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    
    # EBEST 모바일 페이지 PDF 링크 생성(파일명 2번 인코딩하여 조립)
    # r = urlparse.quote(ATTACH_FILE_NAME)
    # r = urlparse.quote(r)
    # if ARTICLE_BOARD_ORDER == 0 : # 이슈브리프
    #     ATTACH_URL = "http://mweb.ebestsec.co.kr/download?addPath=%2F%2FEtwBoardData%2FB202103&filename="
    # elif ARTICLE_BOARD_ORDER == 1: # 기업분석
    #     ATTACH_URL = "http://mweb.ebestsec.co.kr/download?addPath=%2F%2FEtwBoardData%2FB202102&filename="
    # elif ARTICLE_BOARD_ORDER == 2: # 산업분석
    #     ATTACH_URL = "http://mweb.ebestsec.co.kr/download?addPath=%2F%2FEtwBoardData%2FB202103&filename="
    # elif ARTICLE_BOARD_ORDER == 3: # 투자전략
    #     ATTACH_URL = "http://mweb.ebestsec.co.kr/download?addPath=%2F%2FEtwBoardData%2FB202102&filename="
    # elif ARTICLE_BOARD_ORDER == 3: # QUANT
    #     ATTACH_URL = "http://mweb.ebestsec.co.kr/download?addPath=%2F%2FEtwBoardData%2FB202102&filename="
    # else:
    #     ATTACH_URL = "htts://mweb.ebestsec.co.kr/download?addPath=%2F%2FEtwBoardData%2FB202102&filename="

    # ATTACH_URL += r
    # print(ATTACH_URL)
    # time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return ATTACH_URL

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

    try:
        ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
        FIRST_ARTICLE_URL = 'http://www.heungkuksec.co.kr/research/industry/view.do?' + soupList[FIRST_ARTICLE_INDEX]['onclick'].replace("nav.go('view', '", "").replace("');", "").strip()
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

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
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
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
    try:
        ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
        FIRST_ARTICLE_URL = 'http://www.sangsanginib.com' + soupList[FIRST_ARTICLE_INDEX]['href'] #.replace("nav.go('view', '", "").replace("');", "").strip()
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

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
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
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
    # 하나금융 주식 전략
    TARGET_URL_3 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=1'
    # 하나금융 Small Cap
    TARGET_URL_4 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=3'
    # 하나금융 기업 메모
    TARGET_URL_5 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=3&cid=4'
    # 하나금융 Quant
    TARGET_URL_6 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=2'
    # 하나금융 포트폴리오
    TARGET_URL_7 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=3'
    # 하나금융 투자정보
    TARGET_URL_8 =  'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=4'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        sendMessageText += HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)
 
def HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

    try:
        ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
        FIRST_ARTICLE_TITLE = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li:nth-child(1)> div.con > ul > li.mb4 > h3 > a:nth-child(1)')[FIRST_ARTICLE_INDEX].text.strip()
        FIRST_ARTICLE_URL =  'https://www.hanaw.com' + soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li:nth-child(1)> div.con > ul > li:nth-child(5)> div > a')[FIRST_ARTICLE_INDEX].attrs['href']
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

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
        # LIST_ATTACT_FILE_NAME = list.select_one('div.con > ul > li:nth-child(5)> div > a').text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')


            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return sendMessageText

    
    print(sendMessageText)
    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText


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

    try:
        ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
        FIRST_ARTICLE_TITLE = soup.select('#content > div.content_area > table > tbody > tr:nth-child(1) > td.tx_left > a')[FIRST_ARTICLE_INDEX].text.strip()
        FIRST_ARTICLE_URL =  'http://www.hygood.co.kr' + soup.select('#content > div.content_area > table > tbody > tr:nth-child(1) > td.tx_left > a')[FIRST_ARTICLE_INDEX].attrs['href']
        FIRST_ARTICLE_URL_f = FIRST_ARTICLE_URL.split(";")[0]
        FIRST_ARTICLE_URL_b = FIRST_ARTICLE_URL.split("?")[1]
        FIRST_ARTICLE_URL = FIRST_ARTICLE_URL_f + "?" + FIRST_ARTICLE_URL_b
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

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
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL, FIRST_ARTICLE_TITLE)
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

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        sendMessageText += Samsung_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)
 
def Samsung_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#content > section.bbsLstWrap > ul > li')

    try:
        ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
        FIRST_ARTICLE_TITLE = soup.select('#content > section.bbsLstWrap > ul > li:nth-child(1)> a > dl > dt > strong')[FIRST_ARTICLE_INDEX].text.strip()
        a_href =soup.select('#content > section.bbsLstWrap > ul > li:nth-child(1)> a')[FIRST_ARTICLE_INDEX].attrs['href']
        a_href = a_href.replace('javascript:downloadPdf(', '').replace(';', '')
        a_href = a_href.split("'")
        a_href = a_href[1]
        FIRST_ARTICLE_URL =  'https://www.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName=' + a_href+ '&contentType=application/pdf'
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])
        if "(수정)"  in FIRST_ARTICLE_TITLE and NXT_KEY == FIRST_ARTICLE_TITLE.replace("(수정)", ""):  # 첫번째 게시글이 수정된 경우 무한발송 방지  
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
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
        # LIST_ATTACT_FILE_NAME = fileNameArray[1].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                # sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)                
            # else:
            #     print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            #     print(sendMessageText)
            #     sendText(sendMessageText)
            #     nNewArticleCnt = 0
            #     sendMessageText = ''
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0 or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            # else:
            #     # 현재 리스트 확인하여 발송후 초기화 
            #     sendText(sendMessageText)

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return sendMessageText
    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    print(sendMessageText)
    return sendMessageText

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
    global KYOBO_BOARD_NAME # 교보증권 전용 변수

    SEC_FIRM_ORDER      = 6
    ARTICLE_BOARD_ORDER = 0

    TARGET_URL = 'https://www.iprovest.com/weblogic/RSReportServlet?mode=list&menuCode=1&scr_id=32'
                 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('body > div > table > tbody > tr')

    try:
        FIRST_ARTICLE_TITLE = soup.select('body > div > table > tbody > tr:nth-child(1) > td.tLeft > div > a')[FIRST_ARTICLE_INDEX].text.strip()
        FIRST_ARTICLE_URL =  'https://www.iprovest.com' + soup.select('body > div > table > tbody > tr:nth-child(1) > td.tLeft > div > a')[FIRST_ARTICLE_INDEX].attrs['href'].strip()
        FIRST_ARTICLE_BOARD_NAME = soup.select('body > div > table > tbody > tr:nth-child(1) > td:nth-child(4) > i')[FIRST_ARTICLE_INDEX].text.strip()

        FIRST_ATTACT_FILE_URL = soup.select('body > div > table > tbody > tr:nth-child(1) > td:nth-child(7) > a')[FIRST_ARTICLE_INDEX].attrs['href'].strip()
        FIRST_ATTACT_FILE_URL = FIRST_ATTACT_FILE_URL.split("'")
        FIRST_ATTACT_FILE_URL = 'https://www.iprovest.com' + FIRST_ATTACT_FILE_URL[1].strip()
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

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
        KYOBO_BOARD_NAME = LIST_ARTICLE_BOARD_NAME
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
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ATTACT_FILE_URL, FIRST_ARTICLE_TITLE)
            return True

    return True

def KyoBo_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME
    print('첨부파일이름 :',ATTACH_FILE_NAME)
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

# DS투자증권
def DS_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 7


    # 이슈브리프
    DS_URL_0 = 'http://www.ds-sec.co.kr/bbs/board.php?bo_table=sub03_02'
    # 기업분석 게시판
    DS_URL_1 = 'http://www.ds-sec.co.kr/bbs/board.php?bo_table=sub03_03'
    
    DS_URL_TUPLE = (DS_URL_0, DS_URL_1)

    requests.packages.urllib3.disable_warnings()

    ## EBEST만 로직 변경 테스트
    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(DS_URL_TUPLE):
        sendMessageText += DS_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)

def DS_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global LIST_ARTICLE_TITLE
    sendMessageText = ''

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    # print(soup)
    soupList = soup.select('#fboardlist > div > table > tbody > tr > td.td_subject > div > a')
    
    print(soupList)
    ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
    try:
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text.strip()
    except IndexError:
        return sendMessageText

    try:
        FIRST_ARTICLE_URL = soupList[FIRST_ARTICLE_INDEX].attrs['href'].replace("amp;", "")
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

    # 연속키 데이터 저장 여부 확인 구간
    print("SEC_FIRM_ORDER", SEC_FIRM_ORDER, "ARTICLE_BOARD_ORDER",ARTICLE_BOARD_ORDER)
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
        LIST_ARTICLE_URL =  list.attrs['href'].replace("amp;", "")
        LIST_ARTICLE_TITLE = list.text.strip().replace("]", ":")

        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y' and 'test' not in FIRST_ARTICLE_TITLE :
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = DS_downloadFile(LIST_ARTICLE_URL)
                # sendMessageText += GetSendMessageTextMarkdown(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL, ATTACH_URL = ATTACH_URL)
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        elif 'test' in FIRST_ARTICLE_TITLE:
            print("test 게시물은 연속키 처리를 제외합니다.")
            # return True
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            # else:
            #     print('####발송구간####')
            #     print(sendMessageText)
            #     sendText(sendMessageText)
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL, FIRST_ARTICLE_TITLE)
            return sendMessageText
    print(sendMessageText)
    return sendMessageText

def DS_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME
    global LIST_ARTICLE_TITLE

    webpage = requests.get(ARTICLE_URL, verify=False)
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    # 첨부파일 URL
    ATTACH_URL = soup.select_one('#bo_v_con > a')['href']
    # 첨부파일 이름
    ATTACH_FILE_NAME = soup.select_one('#bo_v_file > ul > li > a > strong').text.strip()
    
    return ATTACH_URL


# SMIC(SNU Midas Investment Club)
def SMIC_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 8


    # 이슈브리프
    SMIC_URL_0 = 'http://snusmic.com/research/'
    # 기업분석 게시판
    SMIC_URL_1 = ''
    
    SMIC_URL_TUPLE = (SMIC_URL_0, SMIC_URL_1)

    requests.packages.urllib3.disable_warnings()

    ## EBEST만 로직 변경 테스트
    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(SMIC_URL_TUPLE):
        if TARGET_URL == '' : continue
        sendMessageText += SMIC_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        print('여기')
        print(sendMessageText)
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)

def SMIC_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global LIST_ARTICLE_TITLE
    sendMessageText = ''

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    # print(soup)
    soupList = soup.select('#post-8 > div > div:nth-child(4) > div:nth-child(2) > div > div.uagb-post__items.uagb-post__columns-1.is-grid.uagb-post__columns-tablet-2.uagb-post__columns-mobile-1.uagb-post__equal-height > article > div > div.uagb-post__text > h3 > a')
    
    # print(soupList)
    ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
    try:
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text.strip()
    except IndexError:
        return sendMessageText

    try:
        FIRST_ARTICLE_URL = soupList[FIRST_ARTICLE_INDEX].attrs['href'].replace("amp;", "")
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

    # 연속키 데이터 저장 여부 확인 구간
    print("SEC_FIRM_ORDER", SEC_FIRM_ORDER, "ARTICLE_BOARD_ORDER",ARTICLE_BOARD_ORDER)
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
        LIST_ARTICLE_URL =  list.attrs['href'].replace("amp;", "")
        LIST_ARTICLE_TITLE = list.text.strip().replace("]", ":")

        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y' and 'test' not in FIRST_ARTICLE_TITLE :
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = SMIC_downloadFile(LIST_ARTICLE_URL)
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
                print(sendMessageText)

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        elif 'test' in FIRST_ARTICLE_TITLE:
            print("test 게시물은 연속키 처리를 제외합니다.")
            # return True
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            # else:
            #     print('####발송구간####')
            #     print(sendMessageText)
            #     sendText(sendMessageText)
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL, FIRST_ARTICLE_TITLE)
            return sendMessageText
    print(sendMessageText)
    return sendMessageText

def SMIC_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME
    global LIST_ARTICLE_TITLE

    webpage = requests.get(ARTICLE_URL, verify=False)
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    # 첨부파일 URL
    ATTACH_URL = soup.select_one('article > div > div > div > div > a')['href']
    # 첨부파일 이름
    # ATTACH_FILE_NAME = soup.select_one('#bo_v_file > ul > li > a > strong').text.strip()
    
    return ATTACH_URL

###

def mkStock_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 994
    ARTICLE_BOARD_ORDER = 994

    requests.packages.urllib3.disable_warnings()

    # MK증권
    TARGET_URL = 'http://vip.mk.co.kr/newSt/rate/monhigh.php'

    # MK증권 웹 크롤링
    mkStock_parse(ARTICLE_BOARD_ORDER, TARGET_URL)

# 웹크롤링 타입
def mkStock_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global LIST_ARTICLE_TITLE

    # webpage = requests.get(TARGET_URL, verify=False)

    # # HTML parse
    # soup = BeautifulSoup(webpage.content, "html.parser")
    # refrashTime = soup.select_one('body > div:nth-child(10) > div > table > tbody > tr > td:nth-child(1) > table:nth-child(2) > tbody > tr > td:nth-child(1) > span')
    # # refrashTime = refrashTime.strip()
    # print(refrashTime)

    # try:
    #     FIRST_ARTICLE_TITLE = refrashTime
    #     refrashTime = refrashTime.split(" ")
    #     DATE = refrashTime[0]
    #     TIME = refrashTime[1]
    #     TIMEsplit = TIME.split(":")
    #     HH = int(TIMEsplit[0])
    #     MM = int(TIMEsplit[1])
    # except IndexError:
    #     return 


    FIRST_ARTICLE_URL = 'http://vip.mk.co.kr/newSt/rate/monhigh.php'
    
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    print(dbResult)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        # print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])
        print('데이터베이스에 연속키가 존재합니다. ')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        # print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        print('데이터베이스에 연속키가 존재합니다. ')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, str(GetCurrentDate('YYYY/HH/DD')))

    # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    # print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('연속URL:', NXT_KEY) # 주소
    print('############')


    sendMessageText = FIRST_ARTICLE_URL
    TODAY = GetCurrentDate('YYYY/HH/DD')
    print('NXT_KEY', NXT_KEY)
    print('TODAY', TODAY)
    if NXT_KEY != TODAY:
        sendText(GetSendMessageTitle() + sendMessageText)
        NXT_KEY = TODAY

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, str(GetCurrentDate('YYYY/HH/DD')))

def ChosunBizBot_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 995
    ARTICLE_BOARD_ORDER = 995

    requests.packages.urllib3.disable_warnings()

    # 조선Biz Cbot API
    # TARGET_URL = 'https://biz.chosun.com/pf/api/v3/content/fetch/story-feed?query=%7B%22excludeSections%22%3A%22%22%2C%22expandRelated%22%3Atrue%2C%22includeContentTypes%22%3A%22story%22%2C%22includeSections%22%3A%22%2Fstock%2Fc-biz_bot%22%2C%22size%22%3A20%7D&filter=%7Bcontent_elements%7B%5B%5D%2C_id%2Ccanonical_url%2Ccredits%7Bby%7B_id%2Cadditional_properties%7Boriginal%7Baffiliations%2Cbyline%7D%7D%2Cname%2Corg%2Curl%7D%7D%2Cdescription%7Bbasic%7D%2Cdisplay_date%2Cheadlines%7Bbasic%2Cmobile%7D%2Clabel%7Bshoulder_title%7Btext%2Curl%7D%7D%2Cpromo_items%7Bbasic%7B_id%2Cadditional_properties%7Bfocal_point%7Bmax%2Cmin%7D%7D%2Calt_text%2Ccaption%2Ccontent_elements%7B_id%2Calignment%2Calt_text%2Ccaption%2Ccontent%2Ccredits%7Baffiliation%7Bname%7D%2Cby%7B_id%2Cbyline%2Cname%2Corg%7D%7D%2Cheight%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Csubtype%2Ctype%2Curl%2Cwidth%7D%2Ccredits%7Baffiliation%7Bbyline%2Cname%7D%2Cby%7Bbyline%2Cname%7D%7D%2Cdescription%7Bbasic%7D%2Cfocal_point%7Bx%2Cy%7D%2Cheadlines%7Bbasic%7D%2Cheight%2Cpromo_items%7Bbasic%7B_id%2Cheight%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Csubtype%2Ctype%2Curl%2Cwidth%7D%7D%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Cstreams%7Bheight%2Cwidth%7D%2Csubtype%2Ctype%2Curl%2Cwebsites%2Cwidth%7D%2Clead_art%7Bduration%2Ctype%7D%7D%2Crelated_content%7Bbasic%7B_id%2Cabsolute_canonical_url%2Cheadlines%7Bbasic%2Cmobile%7D%2Creferent%7Bid%2Ctype%7D%2Ctype%7D%7D%2Csubtype%2Ctaxonomy%7Bprimary_section%7B_id%2Cname%7D%2Ctags%7Bslug%2Ctext%7D%7D%2Ctest%2Ctype%2Cwebsite_url%7D%2Ccount%2Cnext%7D&d=92&_website=chosunbiz'
    TARGET_URL = 'https://stockplus.com/api/news_items/all_news.json?scope=latest&limit=100'
    
    # 조선Biz 웹 크롤링 변경
    # TARGET_URL = 'https://biz.chosun.com/stock/c-biz_bot/'
    
    
    # 조선Biz Cbot API JSON 크롤링
    # ChosunBizBot_JSONparse(ARTICLE_BOARD_ORDER, TARGET_URL)


    # 조선Biz Cbot API JSON 크롤링
    ChosunBizBot_StockPlusJSONparse(ARTICLE_BOARD_ORDER, TARGET_URL)

    # ChosunBizBot_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    # 조선Biz Cbot 웹 크롤링
    # for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
    #     ChosunBizBot_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    #     time.sleep(5)
 
# JSON API 타입
def ChosunBizBot_JSONparse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    BASE_URL = 'biz.chosun.com'
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("ChosunBizBot_JSONparse 접속이 원활하지 않습니다 ")

    jres = json.loads(response.read().decode('utf-8'))

    jres = jres['content_elements']
    # print(jres)

    try:
        FIRST_ARTICLE_URL = BASE_URL + jres[0]['canonical_url'].strip()
        FIRST_ARTICLE_TITLE = jres[0]['headlines']['basic'].strip()
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    
    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','(ChosunBizBot_JSONparse)')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', '(ChosunBizBot_JSONparse)')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for chosun in jres:
        # print(chosun)
        LIST_ARTICLE_URL = BASE_URL + chosun['canonical_url'].strip()
        LIST_ARTICLE_TITLE = chosun['headlines']['basic'].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            else:
                sendText(sendMessageText)

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return True

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
    return True

# 웹크롤링 타입
def ChosunBizBot_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global LIST_ARTICLE_TITLE

    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#main > div.flex-chain-wrapper.sm.\|.box--margin-top-md.width--100.box--pad-top-md.box--pad-bottom-md.box--bg-undefined.box--border.box--border-black.box--border-xs.box--border-horizontal.box--border-horizontal-top.box--hidden-lg.box--hidden-md > section > div > div > div > div:nth-child(1) > div > div > div > div.story-card.story-card--art-left.\|.flex.flex--wrap > div.story-card-block.story-card-right.\|.grid__col--sm-9.grid__col--md-9.grid__col--lg-9 > div.story-card-component.story-card__headline-container.\|.text--overflow-ellipsis.text--left > a')
    print(soupList)
    # ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
    try:
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].text
    except IndexError:
        return 

    try:
        FIRST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + soupList[FIRST_ARTICLE_INDEX].attrs['href'].replace("amp;", "")
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER])

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ',FIRM_NAME[SEC_FIRM_ORDER],'의 ',BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER],'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)

    # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + list.attrs['href'].replace("amp;", "")
        LIST_ARTICLE_TITLE = list.text

        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y' and 'test' not in FIRST_ARTICLE_TITLE :
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = 'https://docs.google.com/viewer?embedded=true&url='+EBEST_downloadFile(LIST_ARTICLE_URL)
                # sendMessageText += GetSendMessageTextMarkdown(ARTICLE_BOARD_NAME = ARTICLE_BOARD_NAME, ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL, ATTACH_URL = ATTACH_URL)
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        elif 'test' in FIRST_ARTICLE_TITLE:
            print("test 게시물은 연속키 처리를 제외합니다.")
            # return True
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL, FIRST_ARTICLE_TITLE)
            return sendMessageText

    print(sendMessageText)
    return sendMessageText

# 증권플러스 뉴스 JSON API 타입
def ChosunBizBot_StockPlusJSONparse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("ChosunBizBot_StockPlusJSONparse 접속이 원활하지 않습니다 ")

    jres = json.loads(response.read().decode('utf-8'))

    jres = jres['newsItems']
    print(jres)

    try:
        FIRST_ARTICLE_URL = jres[0]['url'].strip()
        FIRST_ARTICLE_TITLE = jres[0]['title'].strip()
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''
            
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    
    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','(ChosunBizBot_JSONparse)')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', '(ChosunBizBot_JSONparse)')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for stockPlus in jres:
        LIST_ARTICLE_URL = stockPlus['url'].strip()
        LIST_ARTICLE_TITLE = stockPlus['title'].strip()
        LIST_ARTICLE_WRITER_NAME = stockPlus['writerName'].strip()
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                if LIST_ARTICLE_WRITER_NAME == '증권플러스': sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)                
                # print(sendMessageText)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            else:
                print(sendMessageText)
                sendText(sendMessageText)

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return True

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
    return True

def EINFOMAXshort_checkNewArticle():
    global NXT_KEY
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 996
    ARTICLE_BOARD_ORDER = 996

    ARTICLE_BOARD_NAME = ''

    TARGET_URL = 'http://news.einfomax.co.kr/news/articleList.html?sc_area=A&view_type=sm&sc_word=%EA%B3%B5%EB%A7%A4%EB%8F%84+%EC%9E%94%EA%B3%A0+%EC%83%81%EC%9C%84+50%EC%A2%85%EB%AA%A9'

    requests.packages.urllib3.disable_warnings()                 

    webpage = requests.get(TARGET_URL, verify=False)


    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#user-container > div.float-center.max-width-1080 > div.user-content.list-wrap > section > article > div.article-list > section > div > div.list-titles > a')

    # print(soupList)
    try:
        FIRST_ARTICLE_URL = 'news.einfomax.co.kr'+soupList[FIRST_ARTICLE_INDEX].attrs['href'].strip()
        FIRST_ARTICLE_TITLE = soup.select_one('#user-container > div.float-center.max-width-1080 > div.user-content.list-wrap > section > article > div.article-list > section > div:nth-child(1) > div.list-titles > a').text.strip()
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','연합인포맥스','의 ', '공매도 잔고')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', '연합인포맥스','의 ', '공매도 잔고' ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL)

    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'news.einfomax.co.kr' + list.attrs['href'].strip()
        LIST_ARTICLE_TITLE = list.text.replace('[표] ','').strip()

        # 최종치 수급도 발송하도록 변경
        if ( NXT_KEY != LIST_ARTICLE_URL or NXT_KEY == '' ) and SEND_YN == 'Y':
            sendMarkdown(nNewArticleCnt, ARTICLE_BOARD_NAME , LIST_ARTICLE_TITLE , LIST_ARTICLE_URL, LIST_ARTICLE_URL)
            nNewArticleCnt += 1
            # send(ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            # EINFOMAXshort_downloadFile(LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL, FIRST_ARTICLE_TITLE)
            return True

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
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_URL, FIRST_ARTICLE_TITLE)
            return True

def Itooza_downloadFile(ARTICLE_URL):
    webpage = requests.get(ARTICLE_URL, verify=False)
    # 첨부파일 URL처리
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('img.bodyaddimage')
    try:
        ATTACH_URL = attachFileCode.attrs['src']    
    except:
        print("아이투자 게시글에 이미지가 존재 하지 않습니다. ")
        return
    sendPhoto(ATTACH_URL)
    time.sleep(5) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

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

    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
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
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            else:
                sendText(sendMessageText)

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return True

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
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

    try:
        FIRST_ARTICLE_URL = 'https://www.sedaily.com'+soupList[FIRST_ARTICLE_INDEX].attrs['href']
        FIRST_ARTICLE_TITLE = soup.select_one('#NewsDataFrm > ul > li:nth-child(1) > a > div.text_area > h3').text.replace("[표]", "")
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''
        

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
    nNxtKeyChk = 0
    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.sedaily.com'+list.attrs['href']
        LIST_ARTICLE_TITLE = list.select_one('div.text_area > h3').text.replace("[표]", "")
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            pass
        else:
            nNxtKeyChk += 1

    if nNxtKeyChk: # 정상 상태
        pass
    else: # 중복 발송 상태(연속키 유무와 상관없음) 
        DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
        return True
        
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.sedaily.com'+list.attrs['href']
        LIST_ARTICLE_TITLE = list.select_one('div.text_area > h3').text.replace("[표]", "")

        # 최종치 수급도 발송하도록 변경
        #if ( (NXT_KEY != LIST_ARTICLE_TITLE and "최종치" not in LIST_ARTICLE_TITLE) or NXT_KEY == '' ) and SEND_YN == 'Y':
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            send(ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            # SEDAILY_downloadFile(LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            # if "최종치" in LIST_ARTICLE_TITLE : print('매매 동향 최종치 게시물은 보내지 않습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
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


def trevari_checkNewArticle():
    global NXT_KEY
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 777
    ARTICLE_BOARD_ORDER = 777

    requests.packages.urllib3.disable_warnings()

    TARGET_URL = 'https://trevari.co.kr/clubs/show?clubID=f62cf0f8-f9a6-4cee-af10-e904b3d9f0f0&status=FullClub'
                 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    #soupList = soup.select('#__next > div > div.jsx-2858481047.body > div > div.jsx-1664952319.floating-button > div > div > div')

    #FIRST_ARTICLE_URL = 'https://www.sedaily.com'+soupList[FIRST_ARTICLE_INDEX].attrs['href']
    strBtn = soup.select_one('#__next > div > div.jsx-2858481047.body > div > div.jsx-1261196552.club-info > div > div.jsx-1261196552.pc > div > div.jsx-1664952319.floating-button > div > div > div > button').text
    
    if "마감" not in strBtn:
        #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
        bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
        chat_id = TELEGRAM_USER_ID_DEV # 나의 텔레그램 아이디
        sendMessageText  = "*파운더의 사고방식-탐탐* 의 공석이 발생하였습니다! \n"
        sendMessageText += "https://trevari.co.kr/clubs/show?clubID=f62cf0f8-f9a6-4cee-af10-e904b3d9f0f0&status=FullClub" + "\n" 
        sendMessageText += "[링크]"+"(https://trevari.co.kr/clubs/show?clubID=f62cf0f8-f9a6-4cee-af10-e904b3d9f0f0&status=FullClub)"
        bot.sendMessage(chat_id=chat_id, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

    return 
    
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

        # 최종치 수급도 발송하도록 변경
        #if ( (NXT_KEY != LIST_ARTICLE_TITLE and "최종치" not in LIST_ARTICLE_TITLE) or NXT_KEY == '' ) and SEND_YN == 'Y':
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            send(ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            # SEDAILY_downloadFile(LIST_ARTICLE_URL)
            print('메세지 전송 URL:', LIST_ARTICLE_URL)
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            # if "최종치" in LIST_ARTICLE_TITLE : print('매매 동향 최종치 게시물은 보내지 않습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return True

    return True

def fnguideTodayReport_checkNewArticle():
    global NXT_KEY
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 123
    ARTICLE_BOARD_ORDER = 123


    # 유효 발송 시간에만 로직 실행

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','fnguideTodayReport_checkNewArticle')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', ' fnguideTodayReport_checkNewArticle 연속키는 존재하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, "오늘의레포트")
        return True
    if GetCurrentDay() == '토' or GetCurrentDay() == '일': return True
    if int(GetCurrentTime('HH')) == 9 and TODAY_SEND_YN == 'N': 
        pass # 로직 발송 조건 (9시에 오늘 발송이 아닐 경우)
    else:
        dbResult = DB_UpdTodaySendKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER= ARTICLE_BOARD_ORDER, TODAY_SEND_YN = 'N')
        return True


    requests.packages.urllib3.disable_warnings()

    TARGET_URL = 'https://comp.fnguide.com/SVO/WooriRenewal/Report_Data.asp?stext=&check=all'
                 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    # 종목 정보(레포트 수) 
    soupList1 = soup.select('tr > td.sub_mgl10')
    
    # 애널리스트 정보
    soupList2 = soup.select('tr > td:nth-child(5)')

    sendMessageText = GetSendMessageTitle()
    for listIsu, listAnalyst in zip(soupList1, soupList2):
        print('######################')
        try:
            listIsu = listIsu.text
        except:
            continue

        listIsu = listIsu.split("|")
        strIsuNm = listIsu[0].strip()
        strIsuNo = strIsuNm.split("(A")
        strIsuNo = strIsuNo[1].replace(")","")
        strIsuUrl = "[종목링크]" + "(" + "https://finance.naver.com/item/main.naver?code=" + strIsuNo + ")"
        listIsu = listIsu[1].split("-  ")
        strReportTitle = listIsu[0].strip()

        try:
            strInvestOpinion_1 = listIsu[1].strip()
        except:
            strInvestOpinion_1 = ''

        try:    
            strInvestOpinion_2 = listIsu[2].strip()
        except:
            strInvestOpinion_2 = ''

        strHead  = '*' + strIsuNm + ' - ' +strReportTitle + '*' + " | " +  strIsuUrl
        strBody  = '- '  + strInvestOpinion_1.strip() + '\n'
        strBody += '- '  + strInvestOpinion_2.strip()

        strTail = listAnalyst.get_text(' - ', strip=True)

        print(strHead)
        print(strBody)
        print(strTail)
        sendMessageText += strHead + "\n"
        sendMessageText += strBody + "\n" 
        sendMessageText += strTail + "\n" + "\n" 
        if len(sendMessageText) > 3500 : # 중간 발송
            sendText(sendMessageText)
            sendMessageText = ''

    # 나머지 최종 발송
    sendText(sendMessageText)
    dbResult = DB_UpdTodaySendKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER= ARTICLE_BOARD_ORDER, TODAY_SEND_YN = 'Y')

    return True

def personalNoti_checkNewArticle():
    global NXT_KEY
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 777
    ARTICLE_BOARD_ORDER = 777

    requests.packages.urllib3.disable_warnings()

    TARGET_URL = 'https://newmallthat.shinhancard.com/alhsec/ALHFM109N/ALHFM109R01.shc?althMllId=10001&althPdId=106901368&althGnbMllId=10001'
                 
    webpage = requests.get(TARGET_URL, verify=False)

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    

    #soupList = soup.select('#__next > div > div.jsx-2858481047.body > div > div.jsx-1664952319.floating-button > div > div > div')

    #FIRST_ARTICLE_URL = 'https://www.sedaily.com'+soupList[FIRST_ARTICLE_INDEX].attrs['href']
    # strBtn = soup.select_one('#__next > div > div.jsx-2858481047.body > div > div.jsx-1261196552.club-info > div > div.jsx-1261196552.pc > div > div.jsx-1664952319.floating-button > div > div > div > button').text
    strBtn = str(soup)
    print(strBtn)
    print("더 나은 서비스를 위해"  in strBtn)
    if "판매중인 상품이 아닙니다." not in strBtn and "더 나은 서비스를 위해" not in strBtn:
        #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
        bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
        chat_id = TELEGRAM_USER_ID_DEV # 나의 텔레그램 아이디
        sendMessageText  = "*신한 터치월렛 2세대* 재 판매 게시 \n"
        sendMessageText += "https://newmallthat.shinhancard.com/alhsec/ALHFM109N/ALHFM109R01.shc?althMllId=10001&althPdId=106901368&althGnbMllId=10001" + "\n" 
        sendMessageText += "[링크]"+"(https://newmallthat.shinhancard.com/alhsec/ALHFM109N/ALHFM109R01.shc?althMllId=10001&althPdId=106901368&althGnbMllId=10001)"
        bot.sendMessage(chat_id=chat_id, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    else:
        print('판매중단')
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

    ARTICLE_BOARD_NAME = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
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
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
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
    sendMessageText += GetSendMessageTitle()
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 :',me)

    if SEC_FIRM_ORDER == 999 or SEC_FIRM_ORDER == 998 or SEC_FIRM_ORDER == 997 : # 매매동향의 경우 URL만 발송하여 프리뷰 처리 
        DISABLE_WEB_PAGE_PREVIEW = False

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
    # sendMessageText += GetSendMessageTitle()
    sendMessageText += ARTICLE_TITLE + "\n"
    sendMessageText += EMOJI_PICK + ARTICLE_URL 

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    #생성한 텔레그램 봇 정보 출력
    #me = bot.getMe()
    #print('텔레그램 채널 정보 :',me)

    bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText)
    
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def sendPhoto(ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('sendPhoto()')

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    bot.sendPhoto(chat_id = GetSendChatId(), photo = ARTICLE_URL)
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

def sendText(sendMessageText): # 가공없이 텍스트를 발송합니다.
    global CHAT_ID

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    
    time.sleep(8) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def sendMarkdown(INDEX, ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL, ATTACH_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    global CHAT_ID
    global sendMessageText

    print('sendMarkdown()')
    DISABLE_WEB_PAGE_PREVIEW = True # 메시지 프리뷰 여부 기본값 설정


    # 첫 인덱스 타이틀
    if INDEX == 0:
        sendMessageText = ''
        sendMessageText += GetSendMessageTitle()

    sendMessageText += ARTICLE_TITLE + "\n" 

    # 원문 링크 , 레포트 링크
    if SEC_FIRM_ORDER == 996:
        sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")" + "\n" + "\n"
    else:
        sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")" + "        "+ EMOJI_PICK + "[레포트링크(클릭)]" + "("+ ATTACH_URL + ")" + "\n"

    if SEC_FIRM_ORDER == 996 and INDEX == 0 : return # 공매도 잔고의 경우 2건이상 일때 발송

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    
    time.sleep(4) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

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
    # 실제 전송할 메시지 작성
    sendMessageText = ''
    # 발신 게시판 종류
    if INDEX == 1:
        sendMessageText += GetSendMessageTitle() + "\n"
    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")"
    sendMessageText += "\n" + "\n"

    return sendMessageText

# 실제 전송할 메시지 작성 
# 유형   : Markdown
# Paran  : ARTICLE_TITLE -> 레포트 제목  , ATTACH_URL -> 레포트 URL(PDF)
def GetSendMessageTextMarkdown(ARTICLE_TITLE , ATTACH_URL):
    
    sendMessageText = ''

    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ATTACH_URL + ")"
    sendMessageText += "\n" + "\n"

    return sendMessageText
    
# 타이틀 생성 
# : 게시판 이름 삭제
def GetSendMessageTitle():

    SendMessageTitle = ""
    msgFirmName = ""
    
    if SEC_FIRM_ORDER == 999:
        msgFirmName = "매매동향"
    elif SEC_FIRM_ORDER == 998:
        msgFirmName = "네이버 - "
        if  ARTICLE_BOARD_ORDER == 0 : msgFirmName += "실시간 뉴스 속보"
        else: msgFirmName += "가장 많이 본 뉴스"
    elif SEC_FIRM_ORDER == 997: msgFirmName = "아이투자 - 랭킹스탁"
    elif SEC_FIRM_ORDER == 996: msgFirmName = "연합인포맥스 - 공매도 잔고 상위"
    elif SEC_FIRM_ORDER == 995: msgFirmName = "조선비즈 - C-Biz봇"
    elif SEC_FIRM_ORDER == 994: msgFirmName = "매경 증권 52주 신고저가 알림"
    elif SEC_FIRM_ORDER == 123: msgFirmName = "[오늘의 레포트](https://comp.fnguide.com/SVO/WooriRenewal/Report.asp)"
    else: # 증권사
        msgFirmName = FIRM_NAME[SEC_FIRM_ORDER]


    SendMessageTitle += "\n"+ "\n" + EMOJI_FIRE + msgFirmName + EMOJI_FIRE + "\n" + "\n" 
    
    return SendMessageTitle

def GetSendChatId():
    SendMessageChatId = 0
    if SEC_FIRM_ORDER == 998:
        if  ARTICLE_BOARD_ORDER == 0 : 
            SendMessageChatId = TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS # 네이버 실시간 속보 뉴스 채널
        else:
            SendMessageChatId = TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS # 네이버 많이본 뉴스 채널
    elif SEC_FIRM_ORDER == 997:
            SendMessageChatId = TELEGRAM_CHANNEL_ID_ITOOZA # 아이투자
    elif SEC_FIRM_ORDER == 995:
            SendMessageChatId = TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT # 조선비즈 C-bot
    else:
        SendMessageChatId = TELEGRAM_CHANNEL_ID_REPORT_ALARM # 운영 채널(증권사 신규 레포트 게시물 알림방)
    
    # SendMessageChatId = TELEGRAM_CHANNEL_ID_TEST
    return SendMessageChatId

def MySQL_Open_Connect():
    global conn
    global cursor
    
    # clearDB 
    # url = urlparse.urlparse(os.environ['CLEARDB_DATABASE_URL'])
    url = urlparse.urlparse(CLEARDB_DATABASE_URL)
    conn = pymysql.connect(host=url.hostname, user=url.username, password=url.password, charset='utf8', db=url.path.replace('/', ''), cursorclass=pymysql.cursors.DictCursor, autocommit=True)
    cursor = conn.cursor()
    return cursor

def DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
    global NXT_KEY
    global SEND_YN
    global SEND_TIME_TERM
    global TODAY_SEND_YN
    global conn
    global cursor

    cursor = MySQL_Open_Connect()
    dbQuery  = " SELECT 		SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s "
    dbResult = cursor.execute(dbQuery, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print(row)
        NXT_KEY = row['NXT_KEY']
        SEND_YN = row['SEND_YN']
        SEND_TIME_TERM = int(row['SEND_TIME_TERM'])
        TODAY_SEND_YN = row['TODAY_SEND_YN']

    conn.close()
    return dbResult


def DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY):
    global NXT_KEY
    global conn
    global cursor
    cursor = MySQL_Open_Connect()
    dbQuery = "INSERT INTO NXT_KEY (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, CHANGE_DATE_TIME)VALUES ( %s, %s, %s, DEFAULT);"
    cursor.execute(dbQuery, ( SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY ))
    NXT_KEY = FIRST_NXT_KEY
    conn.close()
    return NXT_KEY

def DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE):
    global NXT_KEY
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET NXT_KEY = %s , NXT_KEY_ARTICLE_TITLE = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, ( FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER ))
    if dbResult:
        NXT_KEY = FIRST_NXT_KEY
    conn.close()
    return dbResult

def DB_UpdTodaySendKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, TODAY_SEND_YN):
    global NXT_KEY
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET NXT_KEY = %s , NXT_KEY_ARTICLE_TITLE = %s , TODAY_SEND_YN = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, TODAY_SEND_YN, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    conn.close()
    return dbResult
 
# 시간 및 날짜는 모두 한국 시간 (timezone('Asia/Seoul')) 으로 합니다.
def GetCurrentTime(*args):
    pattern = ''
    for pattern in args:
        print(pattern)
    
    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    TIME = time_now[11:].strip()
    TIME_SPLIT = TIME.split(":")

    if pattern == '':
        TIME = time_now[11:].strip()
    elif pattern == 'HH' or pattern == 'hh':
        TIME = TIME_SPLIT[0]
    elif pattern == 'MM' or pattern == 'mm':
        TIME = TIME_SPLIT[1]
    elif pattern == 'SS' or pattern == 'ss':
        TIME = TIME_SPLIT[2]
    elif pattern == 'HH:MM' or pattern == 'hh:mm':
        TIME = TIME_SPLIT[0] + ":" + TIME_SPLIT[1]
    elif pattern == 'HH:MM:SS' or pattern == 'hh:mm:ss':
        TIME = TIME
    elif pattern == 'HHMM' or pattern == 'hhmm':
        TIME = TIME_SPLIT[0] + TIME_SPLIT[1]
    elif pattern == 'HHMMSS' or pattern == 'hhmmss':
        TIME = TIME.replace(":", "")
    else:
        TIME = time_now[11:].strip()
    print(TIME)
    return TIME

# 한국 시간 (timezone('Asia/Seoul')) 날짜 정보를 구합니다.
def GetCurrentDate(*args):
    pattern = ''
    for pattern in args:
        print('pattern 입력값',pattern)
    
    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    DATE = time_now[:10].strip()
    DATE_SPLIT = DATE.split("-")

    print("버그찾기",DATE)
    if pattern == '':
        DATE = time_now[:10].strip()
    elif pattern == 'YY' or pattern == 'yy':
        DATE = DATE_SPLIT[0][2:]
    elif pattern == 'YYYY' or pattern == 'yyyy':
        DATE = DATE_SPLIT[0]
    elif pattern == 'MM' or pattern == 'mm':
        DATE = DATE_SPLIT[1]
    elif pattern == 'DD' or pattern == 'dd':
        DATE = DATE_SPLIT[2]
    elif pattern == 'YYYY/HH/DD' or pattern == 'yyyy/hh/dd':
        print('여기는')
        DATE = DATE_SPLIT[0] + "/" + DATE_SPLIT[1] + "/" + DATE_SPLIT[2]
    elif pattern == 'YYYY-HH-DD' or pattern == 'yyyy-hh-dd':
        DATE = time_now[:10].strip()
    elif pattern == 'YY-HH-DD' or pattern == 'yy-hh-dd':
        DATE = time_now[2:10].strip()
    else:
        DATE = time_now[:10].strip()

    print('최종',DATE)
    return DATE
    
# 한국 시간 (timezone('Asia/Seoul')) 요일 정보를 구합니다.
def GetCurrentDay(*args):
    daylist = ['월', '화', '수', '목', '금', '토', '일']
    
    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    DATE = time_now[:10].strip()
    DATE_SPLIT = DATE.split("-")
    
    return daylist[datetime.date(DATE_SPLIT[0],DATE_SPLIT[1],DATE_SPLIT[2]).weekday()]

def GetSecretKey(*args):
    global CLEARDB_DATABASE_URL
    global TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET
    global TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET
    global TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS
    global TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS
    global TELEGRAM_CHANNEL_ID_ITOOZA
    global TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT
    global TELEGRAM_CHANNEL_ID_REPORT_ALARM
    global TELEGRAM_CHANNEL_ID_TEST
    global TELEGRAM_USER_ID_DEV

    SECRETS = ''
    print(os.getcwd())
    if os.path.isfile(os.path.join(os.getcwd(), 'secrets.json')): # 로컬 개발 환경
        with open("secrets.json") as f:
            SECRETS = json.loads(f.read())
        CLEARDB_DATABASE_URL                        =   SECRETS['CLEARDB_DATABASE_URL']
        TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   SECRETS['TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET']
        TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   SECRETS['TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET']
        TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS']
        TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS']
        TELEGRAM_CHANNEL_ID_ITOOZA                  =   SECRETS['TELEGRAM_CHANNEL_ID_ITOOZA']
        TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   SECRETS['TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT']
        TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   SECRETS['TELEGRAM_CHANNEL_ID_REPORT_ALARM']
        TELEGRAM_CHANNEL_ID_TEST                    =   SECRETS['TELEGRAM_CHANNEL_ID_TEST']
        TELEGRAM_USER_ID_DEV                        =   SECRETS['TELEGRAM_USER_ID_DEV']
    else: # 서버 배포 환경(heroku)
        CLEARDB_DATABASE_URL                        =   os.environ.get('CLEARDB_DATABASE_URL')
        TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   os.environ.get('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
        TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   os.environ.get('TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET')
        TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
        TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')
        TELEGRAM_CHANNEL_ID_ITOOZA                  =   os.environ.get('TELEGRAM_CHANNEL_ID_ITOOZA')
        TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   os.environ.get('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
        TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   os.environ.get('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
        TELEGRAM_CHANNEL_ID_TEST                    =   os.environ.get('TELEGRAM_CHANNEL_ID_TEST')
        TELEGRAM_USER_ID_DEV                        =   os.environ.get('TELEGRAM_USER_ID_DEV')

def main():
    global SEC_FIRM_ORDER  # 증권사 순번
    global REFRESH_TIME # 새로고침 주기
    global SECRETS # 시크릿 키

    print('########Program Start Run########')
    
    GetSecretKey()
    
    if GetCurrentDay() == '토' or GetCurrentDay() == '일':
        REFRESH_TIME = 60 * 60 * 2 # 2시간
    else:
        REFRESH_TIME = 60 * 20 # 20분

    #print(GetCurrentDate('YYYY/HH/MM') , GetCurrentTime())
    TimeHourMin = int(GetCurrentTime('HHMM'))
    TimeHour = int(GetCurrentTime('HH'))
    
    # SEC_FIRM_ORDER는 임시코드 추후 로직 추가 예정 
    while True:
        print('########  새로고침 주기는 ', REFRESH_TIME, '초 입니다 (평일 20분, 주말 2시간) ########')
        if TimeHourMin < 0 : 
            print("GetCurrentTime() Error => 시간 논리 에러")
            return 
        elif TimeHourMin in range(0, 500) and TimeHourMin in range(2200, 2400): # 22~다음날 05시까지 유휴
            print('######',"현재시간:", GetCurrentTime() ,REFRESH_TIME,'초 스케줄을 실행합니다.######')
            print('CASE1')
        elif TimeHourMin in range(600, 830):  # 06~ 08:30분 : 30분 단위로 게시글을 체크하여 발송
            print('######',"현재시간:", GetCurrentTime() , REFRESH_TIME * 3,'초 단위로 스케줄을 실행합니다.######')
            print('CASE2')
        elif TimeHourMin in range(830, 1100):  # 08:30~ 11:00분 : 30분 단위로 게시글을 체크하여 발송
            print('######',"현재시간:", GetCurrentTime() , REFRESH_TIME * 3,'초 단위로 스케줄을 실행합니다.######')
            print('CASE3')
        elif TimeHourMin in range(1100, 1600):  # 11:00~ 16:00분 : 30분 단위로 게시글을 체크하여 발송
            print('######',"현재시간:", GetCurrentTime() , REFRESH_TIME * 3,'초 단위로 스케줄을 실행합니다.######')
            print('CASE4')
        elif TimeHourMin in range(1600, 1800):  # 16:00~ 22:00분 : 30분 단위로 게시글을 체크하여 발송
            print('######',"현재시간:", GetCurrentTime() , REFRESH_TIME * 3,'초 단위로 스케줄을 실행합니다.######')
            print('CASE5')


        # print("trevari_checkNewArticle()=> 새 게시글 정보 확인") # 777
        # trevari_checkNewArticle()

        print("fnguideTodayReport_checkNewArticle()=> 새 게시글 정보 확인") # 123
        fnguideTodayReport_checkNewArticle()

        print("personalNoti_checkNewArticle()=> 새 게시글 정보 확인") # 777
        personalNoti_checkNewArticle()

        print("EBEST_checkNewArticle()=> 새 게시글 정보 확인") # 0
        EBEST_checkNewArticle()

        print("SangSangIn_checkNewArticle()=> 새 게시글 정보 확인") # 2
        SangSangIn_checkNewArticle()

        print("HANA_checkNewArticle()=> 새 게시글 정보 확인") # 3
        HANA_checkNewArticle()

        print("Samsung_checkNewArticle()=> 새 게시글 정보 확인") # 5
        Samsung_checkNewArticle()

        print("DS_checkNewArticle()=> 새 게시글 정보 확인") # 6
        DS_checkNewArticle()

        print("SMIC_checkNewArticle()=> 새 게시글 정보 확인") # 7
        SMIC_checkNewArticle()

       # if TimeHour == 16: # 장마감 16시에만 한번 발송
        #    sendMessageText = 'http://vip.mk.co.kr/newSt/rate/monhigh.php'
         #   sendText(GetSendMessageTitle() + sendMessageText)
            # print("mkStock_checkNewArticle()=> 새 게시글 정보 확인") # 994
            # mkStock_checkNewArticle()

        print("ChosunBizBot_checkNewArticle()=> 새 게시글 정보 확인") # 995
        ChosunBizBot_checkNewArticle()

        # if TimeHourMin in range(800, 900):  # 08~ 09:90분만 조회
        #     print("EINFOMAXshort_checkNewArticle()=> 새 게시글 정보 확인") # 996
        #     EINFOMAXshort_checkNewArticle()

        # print("Itooza_checkNewArticle()=> 새 게시글 정보 확인") # 997 미활성
        # Itooza_checkNewArticle()

        print("NAVERNews_checkNewArticle()=> 새 게시글 정보 확인") # 998 미활성
        NAVERNews_checkNewArticle()

        print("SEDAILY_checkNewArticle()=> 새 게시글 정보 확인") # 999
        SEDAILY_checkNewArticle()
 
        # 미사용
        # print("HeungKuk_checkNewArticle()=> 새 게시글 정보 확인") # 1
        # HeungKuk_checkNewArticle()
        
        # 미사용
        # print("HANYANG_checkNewArticle()=> 새 게시글 정보 확인") # 4
        # HANYANG_checkNewArticle()

        # print("KyoBo_checkNewArticle()=> 새 게시글 정보 확인") # 6
        # KyoBo_checkNewArticle()

        # print("YUANTA_checkNewArticle()=> 새 게시글 정보 확인") # 4 가능여부 불확실 => 보류
        # YUANTA_checkNewArticle()
        print('######',REFRESH_TIME,'초 후 게시글을 재 확인 합니다.######')
        time.sleep(REFRESH_TIME)

if __name__ == "__main__":
	main()
