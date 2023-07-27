# -*- coding:utf-8 -*- 
import os
import sys
import datetime
from pytz import timezone
import telegram
import requests
import datetime
import time
import ssl
import json
import re
import asyncio
import pymysql
import pymysql.cursors
from typing import List
from bs4 import BeautifulSoup
import urllib.parse as urlparse
import urllib.request
import gd

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
# sleep key
SLEEP_KEY_DIR_FILE_NAME = './key/sleep.key'
INTERVAL_TIME = 3 # 10분 단위 적용
INTERVAL_INIT_TIME = 1
# secrets 
CLEARDB_DATABASE_URL                                = ""
TELEGRAM_BOT_INFO                                   = ""
TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET              = ""
TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET             = ""
TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS                 = ""
TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS                  = ""
TELEGRAM_CHANNEL_ID_ITOOZA                          = ""
TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT                    = ""
TELEGRAM_CHANNEL_ID_REPORT_ALARM                    = ""
TELEGRAM_CHANNEL_ID_TEST                            = ""
TELEGRAM_USER_ID_DEV                                = ""
IS_DEV                                              = ""
SECRETS = ""

# 게시글 갱신 시간
REFRESH_TIME = 60 * 20 # 20분

# 회사이름
FIRM_NAME = (
    "이베스트 투자증권",    # 0
    "신한금융투자",             # 1
    "상상인증권",           # 2
    "하나증권",          # 3
    "한양증권",              # 4
    "삼성증권",              # 5
    "교보증권",              # 6
    "DS투자증권",             # 7
    "SMIC(서울대 가치투자)",             # 8
    "현대차증권",             # 9
    "키움증권",             # 10
    "신영증권"
    # "유안타증권",           # 4
)

# 게시판 이름
BOARD_NAME = (
    [ "이슈브리프" , "기업분석", "산업분석", "투자전략", "Quant", "Macro", "FI/ Credit", "Commodity" ], # 0 = 이베스트
    [ "산업분석", "기업분석" ],                                                                      # 1 = 신한금융투자
    [ "산업리포트", "기업리포트" ],                                                                       # 2
    [ "Daily", "산업분석", "기업분석", "주식전략", "Small Cap", "기업 메모", "Quant", "포트폴리오", "투자정보" ],            # 3
    [ "기업분석", "산업 및 이슈분석" ],                                                                  # 4
    [ "국내기업분석", "국내산업분석", "해외기업분석" ],                                                      # 5
    [ " " ],                                                                                        # 6 (교보는 게시판 내 게시판 분류 사용)
    [ "기업분석", "투자전략/경제분석"],                                                                  # 7 
    [ "기업분석"],                                                # 8 
    [ "Daily"],                                                # 9
    [ "기업분석", "산업분석"],                                                # 10 
    [ "기업분석", "산업분석", "탐방노트", "해외주식"]                                                # 11 
    # [ "투자전략", "Report & Note", "해외주식" ],               # 4 => 유안타 데이터 보류 
)

# pymysql 변수
conn    = ''
cursor  = ''

# 연속키URL
NXT_KEY = ''
NXT_KEY_ARTICLE_TITLE = ''
# 게시판 URL
BOARD_URL = ''
# 테스트 발송여부
TEST_SEND_YN = ''
# 텔레그램 채널 발송 여부
SEND_YN = ''
TODAY_SEND_YN = ''
# 텔레그램 마지막 메세지 발송시간(단위 초)
SEND_TIME_TERM = 0 # XX초 전에 해당 증권사 메시지 발송
# 첫번째URL 
FIRST_ARTICLE_URL = ''
# SendAddText 글로벌 변수
SEND_ADD_MESSAGE_TEXT = ''
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

    TARGET_URL_TUPLE = (EBEST_URL_0, EBEST_URL_1, EBEST_URL_2, EBEST_URL_3, EBEST_URL_4, EBEST_URL_5, EBEST_URL_6, EBEST_URL_7)

    ## EBEST만 로직 변경 테스트
    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            sendMessageText = ''
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendAddText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)

def EBEST_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN
    global LIST_ARTICLE_TITLE
    
    try:
        webpage = requests.get(TARGET_URL, verify=False)
    except:
        return True
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    soupList = soup.select('#contents > table > tbody > tr > td.subject > a')
    
    ARTICLE_BOARD_NAME =  GetBoardName() 
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
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName(),'의 ', GetBoardName() )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName(),'의 ', GetBoardName() ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    
    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    print('TEST_SEND_YN ', TEST_SEND_YN)

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_URL = 'https://www.ebestsec.co.kr/EtwFrontBoard/' + list.attrs['href'].replace("amp;", "")
        LIST_ARTICLE_TITLE = list.text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
        # if  SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                # ATTACH_URL = 'https://docs.google.com/viewer?embedded=true&url='+EBEST_downloadFile(LIST_ARTICLE_URL)
                ATTACH_URL = EBEST_downloadFile(LIST_ARTICLE_URL)
                if ARTICLE_BOARD_ORDER == 0 or ARTICLE_BOARD_ORDER == 1 :
                    LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("(수정)", "")
                    LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]")+1:len(LIST_ARTICLE_TITLE)].strip()

                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                nNewArticleCnt = 0
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText
    
def EBEST_downloadFile(ARTICLE_URL):
    global ATTACH_FILE_NAME
    global LIST_ARTICLE_TITLE

    ATTACH_BASE_URL = 'https://www.ebestsec.co.kr/_bt_lib/util/download.jsp?dataType='
    
    try:
        webpage = requests.get(ARTICLE_URL, verify=False)
    except:
        return True
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
    r = DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    print('*********확인용**************')
    print(r)
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
    # time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return r

def ShinHanInvest_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 1
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 신한금융투자 산업분석
    TARGET_URL_0 = 'https://open2.shinhaninvest.com/phone/asset/module/getbbsdata.jsp?url=/mobile/json.list.do%3FboardName%3Dgiindustry%26curPage%3D1&param1=Q1&param2=+&param3=&param4=%2Fmobile%2Fjson.list.do%3FboardName%3Dgiindustry%26curPage%3D1&param5=Q&param6=99999&param7=&type=bbs2'
    
    # 신한금융투자 기업분석
    TARGET_URL_1 = 'https://open2.shinhaninvest.com/phone/asset/module/getbbsdata.jsp?url=/mobile/json.list.do%3FboardName%3Dgicompanyanalyst%26curPage%3D1&param1=Q1&param2=+&param3=&param4=%2Fmobile%2Fjson.list.do%3FboardName%3Dgicompanyanalyst%26curPage%3D1&param5=Q&param6=99999&param7=&type=bbs2'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        ShinHanInvest_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(1)
 
# JSON API 타입
def ShinHanInvest_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("네이버 뉴스 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True

    strList = jres['list']
    print(strList[0])
    print(strList[0]['f0'],strList[0]['f1'])
    # print(l[0]['f0'])
    # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
    FIRST_ARTICLE_TITLE = jres['list'][0]['f1'].strip()
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName(),'의 ', GetBoardName() )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName(),'의 ', GetBoardName() ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for list in jres['list']:
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        print(list)

        LIST_ARTICLE_URL = 'https://docs.google.com/viewer?embedded=true&url='+ list['f3']
        LIST_ARTICLE_TITLE = list['f1'].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  GetBoardName() ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                nNewArticleCnt = 0

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

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
        try:
            sendMessageText += HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            sendMessageText = ''
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendAddText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)
 
def HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    try:
        webpage = requests.get(TARGET_URL, verify=False)
    except:
        return True

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

    try:
        ARTICLE_BOARD_NAME =  GetBoardName() 
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
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName(),'의 ', GetBoardName() )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName(),'의 ', GetBoardName() ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return '' 
    
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

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                nNewArticleCnt = 0
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def HANA_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME #BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a').text.strip()
    
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

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
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendAddText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)
 
def Samsung_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    try:
        webpage = requests.get(TARGET_URL, verify=False)
    except:
        return True

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#content > section.bbsLstWrap > ul > li')

    try:
        ARTICLE_BOARD_NAME =  GetBoardName() 
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
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName(),'의 ', GetBoardName() )
        if "(수정)"  in FIRST_ARTICLE_TITLE and NXT_KEY == FIRST_ARTICLE_TITLE.replace("(수정)", ""):  # 첫번째 게시글이 수정된 경우 무한발송 방지  
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName(),'의 ', GetBoardName() ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    

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

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("(수정)", "")
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find(")")+1:len(LIST_ARTICLE_TITLE)].strip()
                # print(LIST_ARTICLE_TITLE)
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)                
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''
        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def Kiwoom_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 10

    requests.packages.urllib3.disable_warnings()

    # 삼성증권 기업 분석
    TARGET_URL_0 =  'https://bbn.kiwoom.com/research/SResearchCRListAjax'
    # 삼성증권 산업 분석
    TARGET_URL_1 =  'https://bbn.kiwoom.com/research/SResearchCIListAjax'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        sendMessageText += Kiwoom_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    if len(sendMessageText) > 0: sendAddText(GetSendMessageTitle() + sendMessageText)
    time.sleep(1)
 
def Kiwoom_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    payload = {
        "pageNo": 1,
        "pageSize": 10,
        "stdate": GetCurrentDate("yyyyhhdd"),
        "eddate": GetCurrentDate("yyyyhhdd"),
        "f_keyField": '', 
        "f_key": '',
        "_reqAgent": 'ajax',
        "dummyVal": 0
    }

    try:
        webpage = requests.post(TARGET_URL,data=payload)
        # print(webpage.text)
        jres = json.loads(webpage.text)
    except:
        return True
        
    if jres['totalCount'] == 0 : return ''
    print(jres['researchList'])

    # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
    FIRST_ARTICLE_TITLE = jres['researchList'][0]['titl'].strip()
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName() ,'의 ', GetBoardName() )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName() ,'의 ', GetBoardName() ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for list in jres['researchList']:
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        print(list)
        # 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb=CR&attaFile=1650493541463.pdf&makeDt=2022.04.21'
        LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}' 
        LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(list['rMenuGb'],  list['attaFile'], list['makeDt'])
        LIST_ARTICLE_TITLE = list['titl'].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  GetBoardName() ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def ChosunBizBot_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 995
    ARTICLE_BOARD_ORDER = 995

    requests.packages.urllib3.disable_warnings()

    # 조선Biz Cbot API
    # TARGET_URL = 'https://biz.chosun.com/pf/api/v3/content/fetch/story-feed?query=%7B%22excludeSections%22%3A%22%22%2C%22expandRelated%22%3Atrue%2C%22includeContentTypes%22%3A%22story%22%2C%22includeSections%22%3A%22%2Fstock%2Fc-biz_bot%22%2C%22size%22%3A20%7D&filter=%7Bcontent_elements%7B%5B%5D%2C_id%2Ccanonical_url%2Ccredits%7Bby%7B_id%2Cadditional_properties%7Boriginal%7Baffiliations%2Cbyline%7D%7D%2Cname%2Corg%2Curl%7D%7D%2Cdescription%7Bbasic%7D%2Cdisplay_date%2Cheadlines%7Bbasic%2Cmobile%7D%2Clabel%7Bshoulder_title%7Btext%2Curl%7D%7D%2Cpromo_items%7Bbasic%7B_id%2Cadditional_properties%7Bfocal_point%7Bmax%2Cmin%7D%7D%2Calt_text%2Ccaption%2Ccontent_elements%7B_id%2Calignment%2Calt_text%2Ccaption%2Ccontent%2Ccredits%7Baffiliation%7Bname%7D%2Cby%7B_id%2Cbyline%2Cname%2Corg%7D%7D%2Cheight%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Csubtype%2Ctype%2Curl%2Cwidth%7D%2Ccredits%7Baffiliation%7Bbyline%2Cname%7D%2Cby%7Bbyline%2Cname%7D%7D%2Cdescription%7Bbasic%7D%2Cfocal_point%7Bx%2Cy%7D%2Cheadlines%7Bbasic%7D%2Cheight%2Cpromo_items%7Bbasic%7B_id%2Cheight%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Csubtype%2Ctype%2Curl%2Cwidth%7D%7D%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Cstreams%7Bheight%2Cwidth%7D%2Csubtype%2Ctype%2Curl%2Cwebsites%2Cwidth%7D%2Clead_art%7Bduration%2Ctype%7D%7D%2Crelated_content%7Bbasic%7B_id%2Cabsolute_canonical_url%2Cheadlines%7Bbasic%2Cmobile%7D%2Creferent%7Bid%2Ctype%7D%2Ctype%7D%7D%2Csubtype%2Ctaxonomy%7Bprimary_section%7B_id%2Cname%7D%2Ctags%7Bslug%2Ctext%7D%7D%2Ctest%2Ctype%2Cwebsite_url%7D%2Ccount%2Cnext%7D&d=92&_website=chosunbiz'
    TARGET_URL = 'https://mweb-api.stockplus.com/api/news_items/all_news.json?scope=latest&limit=100'
    
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
    #     time.sleep(1)
 
# JSON API 타입
def ChosunBizBot_JSONparse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN
    BASE_URL = 'biz.chosun.com'
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("ChosunBizBot_JSONparse 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True
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


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for chosun in jres:
        # print(chosun)
        LIST_ARTICLE_URL = BASE_URL + chosun['canonical_url'].strip()
        LIST_ARTICLE_TITLE = chosun['headlines']['basic'].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')

    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
    return True

# 증권플러스 뉴스 JSON API 타입
def ChosunBizBot_StockPlusJSONparse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("ChosunBizBot_StockPlusJSONparse 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True

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


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for stockPlus in jres:
        LIST_ARTICLE_URL = stockPlus['url'].strip()
        LIST_ARTICLE_TITLE = stockPlus['title'].strip()
        LIST_ARTICLE_WRITER_NAME = stockPlus['writerName'].strip()
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                if LIST_ARTICLE_WRITER_NAME == '증권플러스': sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)                
                # print(sendMessageText)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            else:
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return True

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
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
        time.sleep(1)
 
# JSON API 타입
def NAVERNews_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("네이버 뉴스 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True
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


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    

    # NaverNews 게시판에 따른 URL 지정
    if ARTICLE_BOARD_ORDER == 0:category = 'flashnews'
    else:                      category = 'ranknews'

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for news in jres['newsList']:
        LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/'+ category + '/' + news['oid'] + '/' + news['aid']
        LIST_ARTICLE_TITLE = news['tit'].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText


def NAVER_Report_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 900
    ARTICLE_BOARD_ORDER = 900

    requests.packages.urllib3.disable_warnings()


    # 네이버 증권 리서치 기업
    TARGET_URL_0 = 'https://m.stock.naver.com/front-api/v1/research/list?category=company'
    # 네이버 증권 리서치 산업
    TARGET_URL_1 = 'https://m.stock.naver.com/front-api/v1/research/list?category=industry'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        NAVER_Report_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(1)
 
# JSON API 타입
def NAVER_Report_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode != 200 :return print("네이버 레포트 접속이 원활하지 않습니다 ")

    try: jres = json.loads(response.read().decode('utf-8'))
    except: return True
    
    jres = jres['result']
    FIRST_ARTICLE_TITLE = jres[0]['title']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ','(네이버 뉴스 투자정보 리서치)')

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', '(네이버 뉴스 투자정보 리서치)')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''

    # NaverNews 게시판에 따른 URL 지정
    if ARTICLE_BOARD_ORDER == 0:category = 'company'
    else:                      category = 'industry'

    nNewArticleCnt = 0
    sendMessageText = ''
    brokerName = jres[0]['brokerName']
    # JSON To List
    for research in jres:
        # print('***************************')
        print(research)
        LIST_ARTICLE_URL = research['endUrl'] 
        LIST_ARTICLE_URL = NAVER_Report_parseURL(LIST_ARTICLE_URL)
        LIST_ARTICLE_TITLE = research['title']
        if ARTICLE_BOARD_ORDER == 0 : LIST_ARTICLE_TITLE = research['itemName'] +": "+ LIST_ARTICLE_TITLE # 기업분석
        else:                         LIST_ARTICLE_TITLE = research['category'] +": "+ LIST_ARTICLE_TITLE # 산업분석
        # if '하나증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
        # if '키움증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
        # if '삼성증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
        # if '신한투자증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
        
        '''
        {'researchCategory': '종목분석', 'category': '종목분석', 'itemCode': '090430', 
        'itemName': '아모레퍼시픽', 'researchId': 65663, 'title': '기다림은 길어지지만 방향성은 분명', 
        'brokerName': '한화투자증권', 'writeDate': '2023-06-23', 'readCount': '708', 
        'endUrl': 'https://m.stock.naver.com/research/company/65663'}

        {'researchCategory': '산업분석', 'category': '기타', 'researchId': 33786, 
        'title': '한화 항공/방위산업 Weekly', 'brokerName': '한화투자증권', 'writeDate': '2023-06-23', 
        'readCount': '288', 'endUrl': 'https://m.stock.naver.com/research/industry/33786'}
        '''
        print('NXT_KEY ' , NXT_KEY)
        print('LIST_ARTICLE_TITLE ', LIST_ARTICLE_TITLE)
        
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3000:
                # 회사명 출력
                if nNewArticleCnt == 1 or brokerName != research['brokerName'] : # 첫 페이지 이거나 다음 회사명이 다를때만 출력
                    sendMessageText += "\n"+ "●"+research['brokerName'] + "\n"
                    brokerName = research['brokerName'] # 회사명 키 변경
                # 종목 & 산업 출력
                # if ARTICLE_BOARD_ORDER == 0 : sendMessageText += "●"+research['itemName'] + "\n" # 기업분석
                # else:                         sendMessageText += "●"+research['category'] + "\n" # 산업분석
                # 레포트 제목 출력
                # sendMessageText += research['title'] + "\n"
                # 레포트 URL 출력
                # sendMessageText += NAVER_Report_parseURL(LIST_ARTICLE_URL) + "\n"+ "\n"
                # if ARTICLE_BOARD_ORDER == 0 : sendMessageText += "●"+research['itemName'] + "\n" # 기업분석
                # else:                         sendMessageText += "●"+research['category'] + "\n" # 산업분석
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def NAVER_Report_parseURL(LIST_ARTICLE_URL):
    strUrl = ''
    request = urllib.request.Request(LIST_ARTICLE_URL, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request).read() 

    # HTML parse
    soup = BeautifulSoup(response, "html.parser")
    # print(soup)
    soupList = soup.select_one('#content > div.fs3 > div > div.ArticleDetailHeaderTools_article__jSo5t.ArticleDetailHeaderTools_article_original__A_8Dq > a')
    strUrl = soupList.attrs['href']

    return strUrl

def fnguideTodayReport_checkNewArticle():
    global NXT_KEY
    global TEST_SEND_YN
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
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, "0")
        return True

    if int(GetCurrentTime('HH')) == 0: 
        dbResult = DB_UpdTodaySendKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER= ARTICLE_BOARD_ORDER, TODAY_SEND_YN = 'N')
        return True
    # 오늘의 레포트 발송조건
    # 평일, 09시, 17시 (주말이거나 9시, 17시가 아닌 경우 호출하지 않음)
    
    if GetCurrentDay() == '토' or GetCurrentDay() == '일': return True
    if TODAY_SEND_YN == 'Y' : return True
    if int(GetCurrentTime('HH')) == 9 or int(GetCurrentTime('HH')) == 17  : pass
    else: return True
    requests.packages.urllib3.disable_warnings()

    TARGET_URL = 'https://comp.fnguide.com/SVO/WooriRenewal/Report_Data.asp?stext=&check=all'

    try:
        webpage = requests.get(TARGET_URL, verify=False)
    except: 
        return True
    
    print(BOARD_URL)
    print(NXT_KEY)
    sendMessageText  = '오늘의 레포트가 발송되었습니다. \n'
    sendMessageText += '확인하려면 링크를 클릭하세요. \n'
    sendMessageText += BOARD_URL + NXT_KEY
    asyncio.run(sendAlertMessage(sendMessageText)) #봇 실행하는 코드
    
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    # 종목 정보(레포트 수) 
    soupList1 = soup.select('tr > td.sub_mgl10')
    
    # 애널리스트 정보
    soupList2 = soup.select('tr > td:nth-child(5)')

    sendMessageText = ''
    pageCnt = 0
    articleCnt = 0
    for listIsu, listAnalyst in zip(soupList1, soupList2):
        print('######################')
        articleCnt += 1
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

        # 17시 발송건일때 이미 전송된 인덱스는 제외처리
        if articleCnt <= int(NXT_KEY_ARTICLE_TITLE) and int(GetCurrentTime('HH')) == 17 : continue   

        try:
            strInvestOpinion_1 = listIsu[1].strip()
        except:
            strInvestOpinion_1 = ''

        try:    
            strInvestOpinion_2 = listIsu[2].strip()
        except:
            strInvestOpinion_2 = ''

        strHead  = '*' + strIsuNm + ' - ' +strReportTitle + '*' + " | " +  strIsuUrl
        strBody  = '- '  + strInvestOpinion_1.strip()
        if len(strInvestOpinion_2) > 0:
            strBody += '\n'
            strBody += '- '  + strInvestOpinion_2.strip()

        strTail = listAnalyst.get_text(' - ', strip=True)

        print(strHead)
        print(strBody)
        print(strTail)
        sendMessageText += strHead + "\n"
        sendMessageText += strBody + "\n" 
        sendMessageText += strTail + "\n" + "\n" 
        if len(sendMessageText) > 3500 : # 중간 발송
            sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''
            pageCnt += 1

    # 나머지 최종 발송
    if len(sendMessageText) > 0 : # 중간 발송
        sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''
        pageCnt += 1

    # 연속키 갱신
    NXT_KEY = int(NXT_KEY) + int(pageCnt)
    dbResult = DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, articleCnt)

    # 9시, 17시 두차례 발송을 위해 17시 발송후 발송여부 갱신
    if int(GetCurrentTime('HH')) == 17 :
        # 발송 처리
        dbResult = DB_UpdTodaySendKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER= ARTICLE_BOARD_ORDER, TODAY_SEND_YN = 'Y')

    return True


async def sendAlertMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    await bot.sendMessage(chat_id = TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True)


async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

async def sendDocument(ATTACH_FILE_NAME): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    await bot.sendDocument(chat_id = GetSendChatId(), document = open(ATTACH_FILE_NAME, 'rb'))

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

    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = DISABLE_WEB_PAGE_PREVIEW)
    asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드

    if DISABLE_WEB_PAGE_PREVIEW: # 첨부파일이 있는 경우 => 프리뷰는 사용하지 않음
        try:
            time.sleep(1) # 메시지 전송 텀을 두어 푸시를 겹치지 않게 함
            #bot.sendDocument(chat_id = GetSendChatId(), document = open(ATTACH_FILE_NAME, 'rb'))
            asyncio.run(sendDocument(ATTACH_FILE_NAME)) #봇 실행하는 코드
            os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
        except:
            return
    
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)


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

    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText)
    asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def sendPhoto(ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('sendPhoto()')

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    bot.sendPhoto(chat_id = GetSendChatId(), photo = ARTICLE_URL)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)
    return True

# 가공없이 텍스트를 발송합니다.
def sendText(sendMessageText): 
    global CHAT_ID

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# 인자 텍스트를 더해가며 발송합니다. 
# 더해진 텍스트가 텔레그램 제한인 3500자를 넘어가면 발송처리하고 초기화합니다
# 두번째 인자는 첫번째 인자 텍스트를 앞으로 더할지 뒤로 더할지 결정합니다. (F: 앞, B: 뒤에 텍스트를 더합니다)
# 인자를 결정하지 않은 경우 텍스트를 뒤로 붙이도록 설정
# 두번째 파라미터가 Y인 경우 길이와 상관없이 발송처리(집계된 데이터 발송용)
def sendAddText(sendMessageText, sendType='N'): 
    global SEND_ADD_MESSAGE_TEXT

    SEND_ADD_MESSAGE_TEXT += sendMessageText
    print('sendType ', sendType)
    print('sendMessageText ',sendMessageText)
    print('SEND_ADD_MESSAGE_TEXT ', SEND_ADD_MESSAGE_TEXT)

    if len(SEND_ADD_MESSAGE_TEXT) > 3500 or ( sendType == 'Y' and len(SEND_ADD_MESSAGE_TEXT) > 0 ) :
        print("sendAddText() (실제 발송요청)\n", SEND_ADD_MESSAGE_TEXT)
        sendText(SEND_ADD_MESSAGE_TEXT)
        SEND_ADD_MESSAGE_TEXT = ''

    return ''

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
        sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")"  + "\n" 
    else:
        sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")" + "        "+ EMOJI_PICK + "[레포트링크(클릭)]" + "("+ ATTACH_URL + ")"

    if SEC_FIRM_ORDER == 996 and INDEX == 0 : return # 공매도 잔고의 경우 2건이상 일때 발송

    #생성한 텔레그램 봇 정보 assign (@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

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
        
    r = gd.gd(str(ATTACH_FILE_NAME))
    print('********************')
    print(f'main URL {r}')
    return r

def GetSendMessageText(INDEX, ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL):
    # 실제 전송할 메시지 작성
    sendMessageText = ''
    # 발신 게시판 종류
    # if INDEX == 1:
    #     sendMessageText += GetSendMessageTitle() + "\n"
    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ARTICLE_URL + ")"  + "\n" 

    return sendMessageText

# 실제 전송할 메시지 작성 
# 유형   : Markdown
# Paran  : ARTICLE_TITLE -> 레포트 제목  , ATTACH_URL -> 레포트 URL(PDF)
def GetSendMessageTextMarkdown(ARTICLE_TITLE , ATTACH_URL):
    
    sendMessageText = ''

    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[원문링크(클릭)]" + "("+ ATTACH_URL + ")"  + "\n" 

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
    elif SEC_FIRM_ORDER == 900: 
        msgFirmName = "[네이버 증권 "
        if ARTICLE_BOARD_ORDER == 0 : msgFirmName += "기업 리서치](https://m.stock.naver.com/investment/research/company)"
        elif ARTICLE_BOARD_ORDER == 1:  msgFirmName += "산업 리서치](https://m.stock.naver.com/investment/research/industry)"
        else: print(msgFirmName)
    elif SEC_FIRM_ORDER == 123: msgFirmName = "[오늘의 레포트](https://comp.fnguide.com/SVO/WooriRenewal/Report.asp)"
    else: # 증권사
        msgFirmName =  GetFirmName() 

    # SendMessageTitle += "\n" + EMOJI_FIRE + msgFirmName + EMOJI_FIRE + "\n" 
    SendMessageTitle += "\n\n" + " ●"+  msgFirmName + "\n" 
    
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
    elif SEC_FIRM_ORDER == 123: # 오늘의 레포트 채널 나누기 
        SendMessageChatId = TELEGRAM_CHANNEL_ID_TODAY_REPORT # 오늘의 레포트 채널
    else:
        SendMessageChatId = TELEGRAM_CHANNEL_ID_REPORT_ALARM # 운영 채널(증권사 신규 레포트 게시물 알림방)
    
    # SendMessageChatId = TELEGRAM_CHANNEL_ID_TEST
    return SendMessageChatId

def GetJsonData(TARGET_URL, METHOD_TYPE):
    global NXT_KEY
    global TEST_SEND_YN
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    #검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("ChosunBizBot_StockPlusJSONparse 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True

    # jres = jres['newsItems']
    print(jres)
    return jres

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


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for stockPlus in jres:
        LIST_ARTICLE_URL = stockPlus['url'].strip()
        LIST_ARTICLE_TITLE = stockPlus['title'].strip()
        LIST_ARTICLE_WRITER_NAME = stockPlus['writerName'].strip()
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                if LIST_ARTICLE_WRITER_NAME == '증권플러스': sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)                
                # print(sendMessageText)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')
            else:
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)

            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return True

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
    return True


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
    global BOARD_URL
    global NXT_KEY
    global TEST_SEND_YN
    global NXT_KEY_ARTICLE_TITLE
    global SEND_YN
    global SEND_TIME_TERM
    global TODAY_SEND_YN
    global conn
    global cursor

    cursor = MySQL_Open_Connect()
    dbQuery  = " SELECT 		SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, BOARD_URL, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s "
    dbResult = cursor.execute(dbQuery, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print(row)
        BOARD_URL = row['BOARD_URL']
        NXT_KEY = row['NXT_KEY']
        NXT_KEY_ARTICLE_TITLE = row['NXT_KEY_ARTICLE_TITLE']
        SEND_YN = row['SEND_YN']
        SEND_TIME_TERM = int(row['SEND_TIME_TERM'])
        TODAY_SEND_YN = row['TODAY_SEND_YN']

    conn.close()
    return dbResult

def DB_SelSleepKey(*args):
    global NXT_KEY
    global TEST_SEND_YN
    global SEND_YN
    global SEND_TIME_TERM
    global TODAY_SEND_YN
    global conn
    global cursor

    nSleepCnt = 0
    nSleepCntKey = 0

    cursor = MySQL_Open_Connect()
    dbQuery  = " SELECT 		SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   "
    dbResult = cursor.execute(dbQuery, (9999))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print(row)
        nSleepCnt = row['ARTICLE_BOARD_ORDER']
        nSleepCntKey = row['NXT_KEY']

    conn.close()
    SleepTuple = (int(nSleepCnt), int(nSleepCntKey))
    return SleepTuple

def DB_DelSleepKey(*args):
    cursor = MySQL_Open_Connect()
    dbQuery  = " DELETE  FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = 9999"
    dbResult = cursor.execute(dbQuery)

    conn.close()
    return dbResult

def DB_InsSleepKey(*args):
    global NXT_KEY
    global TEST_SEND_YN
    global conn
    global cursor
    cursor = MySQL_Open_Connect()
    dbQuery = "INSERT INTO NXT_KEY (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, CHANGE_DATE_TIME)VALUES ( 9999, 0, ' ', DEFAULT);"
    cursor.execute(dbQuery)
    conn.close()
    return dbQuery

def DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_NXT_KEY):
    global NXT_KEY
    global TEST_SEND_YN
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
    global TEST_SEND_YN
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET NXT_KEY = %s , NXT_KEY_ARTICLE_TITLE = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, ( FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER ))
    if dbResult:
        print('####DB업데이트 된 연속키####', end='\n')
        print(dbResult)
        NXT_KEY = FIRST_NXT_KEY
    conn.close()
    return dbResult

def DB_UpdTodaySendKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, TODAY_SEND_YN):
    global NXT_KEY
    global TEST_SEND_YN
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET TODAY_SEND_YN = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, (TODAY_SEND_YN, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
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

def SetSleepTimeKey(*args):
    try: nSleepCntKey = args[0]
    except: nSleepCntKey = 0
    file = open( SLEEP_KEY_DIR_FILE_NAME , 'w')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
    file.write(  str(nSleepCntKey) )      # 파일에 문자열 저장
    print('nSleepCntKey:',nSleepCntKey, '연속키 파일 경로 :',SLEEP_KEY_DIR_FILE_NAME)
    file.close()                     # 파일 객체 닫기
    
def GetSleepTimeKey(*args):
    # 존재 여부 확인 후 연속키 파일 생성
    if not( os.path.isfile( SLEEP_KEY_DIR_FILE_NAME ) ): # 최초 실행 이거나 연속키 초기화
        # 연속키가 없는 경우 => 첫 게시글을 연속키로 저장
        file = open( SLEEP_KEY_DIR_FILE_NAME , 'w')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
        file.write(  str(INTERVAL_INIT_TIME) )      # 파일에 문자열 저장
        print('INTERVAL_INIT_TIME:',INTERVAL_INIT_TIME, '연속키 파일 경로 :',SLEEP_KEY_DIR_FILE_NAME)
        file.close()                     # 파일 객체 닫기
        return int(INTERVAL_INIT_TIME)
    else:   # 이미 실행
        file = open( SLEEP_KEY_DIR_FILE_NAME , 'r')    # hello.txt 파일을 쓰기 모드(w)로 열기. 파일 객체 반환
        SLEEP_KEY = file.readline()       # 파일 내 데이터 읽기
        print('SLEEP_KEY:', SLEEP_KEY)
        if SLEEP_KEY:
            print('SLEEP_KEY T')
        else:
            SLEEP_KEY = '0'
            
        print('Get_nxtKey')
        print('SLEEP_KEY:',SLEEP_KEY, '연속키 파일 경로 :',SLEEP_KEY_DIR_FILE_NAME)
        file.close()                     # 파일 객체 닫기
        return SLEEP_KEY

def SetSleepTime(*args):
    nSleepCntKey = GetSleepTimeKey()
    nSleepCntKey = int(nSleepCntKey)
    while nSleepCntKey < INTERVAL_TIME: 
        nSleepCntKey += 1
        SetSleepTimeKey(nSleepCntKey)
        sys.exit(0)
        
    SetSleepTimeKey(0)
    
    return True
# 증권사명을 가져옵니다. 
def GetFirmName(*args):
    strFirmName = ''
    try :
        strFirmName = FIRM_NAME[SEC_FIRM_ORDER]
    except :
        print('GetFirmName except')
        strFirmName = ''
        
    return strFirmName
# 게시판명을 가져옵니다. 
def GetBoardName(*args):
    strBoardName = ''
    try :
        strBoardName = BOARD_NAME[SEC_FIRM_ORDER][ARTICLE_BOARD_ORDER]
    except :
        print('GetBoardName except')
        strBoardName = ''
        
    return strBoardName

# 한국 시간 (timezone('Asia/Seoul')) 날짜 정보를 구합니다.
def GetCurrentDate(*args):
    pattern = ''
    for pattern in args:
        print('pattern 입력값',pattern)
    
    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    DATE = time_now[:10].strip()
    DATE_SPLIT = DATE.split("-")

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
        DATE = DATE_SPLIT[0] + "/" + DATE_SPLIT[1] + "/" + DATE_SPLIT[2]
    elif pattern == 'YYYY-HH-DD' or pattern == 'yyyy-hh-dd':
        DATE = time_now[:10].strip()
    elif pattern == 'YY-HH-DD' or pattern == 'yy-hh-dd':
        DATE = time_now[2:10].strip()
    elif pattern == 'YYYYHHDD' or pattern == 'yyyyhhdd':
        DATE = DATE_SPLIT[0] + DATE_SPLIT[1] + DATE_SPLIT[2]
    elif pattern == 'YYYY.HH.DD' or pattern == 'yyyy.hh.dd':
        DATE = DATE_SPLIT[0] + "." + DATE_SPLIT[1] + "." + DATE_SPLIT[2]
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
    return daylist[datetime.date(int(DATE_SPLIT[0]),int(DATE_SPLIT[1]),int(DATE_SPLIT[2])).weekday()]

def GetSecretKey(*args):
    global CLEARDB_DATABASE_URL
    global TELEGRAM_BOT_INFO
    global TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET
    global TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET
    global TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS
    global TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS
    global TELEGRAM_CHANNEL_ID_ITOOZA
    global TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT
    global TELEGRAM_CHANNEL_ID_REPORT_ALARM
    global TELEGRAM_CHANNEL_ID_TODAY_REPORT
    global TELEGRAM_CHANNEL_ID_TEST
    global TELEGRAM_USER_ID_DEV
    global IS_DEV

    SECRETS = ''
    print(os.getcwd())
    if os.path.isfile(os.path.join(os.getcwd(), 'secrets.json')): # 로컬 개발 환경
        with open("secrets.json") as f:
            SECRETS = json.loads(f.read())
        CLEARDB_DATABASE_URL                        =   SECRETS['CLEARDB_DATABASE_URL']
        TELEGRAM_BOT_INFO                           =   SECRETS['TELEGRAM_BOT_INFO']
        TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   SECRETS['TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET']
        TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   SECRETS['TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET']
        TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS']
        TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS']
        TELEGRAM_CHANNEL_ID_ITOOZA                  =   SECRETS['TELEGRAM_CHANNEL_ID_ITOOZA']
        TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   SECRETS['TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT']
        TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   SECRETS['TELEGRAM_CHANNEL_ID_REPORT_ALARM']
        TELEGRAM_CHANNEL_ID_TODAY_REPORT            =   SECRETS['TELEGRAM_CHANNEL_ID_TODAY_REPORT']
        TELEGRAM_CHANNEL_ID_TEST                    =   SECRETS['TELEGRAM_CHANNEL_ID_TEST']
        TELEGRAM_USER_ID_DEV                        =   SECRETS['TELEGRAM_USER_ID_DEV']
        IS_DEV                                      =   True
    else: # 서버 배포 환경(heroku)
        CLEARDB_DATABASE_URL                        =   os.environ.get('CLEARDB_DATABASE_URL')
        TELEGRAM_BOT_INFO                           =   os.environ.get('TELEGRAM_BOT_INFO')
        TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   os.environ.get('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
        TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   os.environ.get('TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET')
        TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
        TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   os.environ.get('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')
        TELEGRAM_CHANNEL_ID_ITOOZA                  =   os.environ.get('TELEGRAM_CHANNEL_ID_ITOOZA')
        TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   os.environ.get('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
        TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   os.environ.get('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
        TELEGRAM_CHANNEL_ID_TODAY_REPORT            =   os.environ.get('TELEGRAM_CHANNEL_ID_TODAY_REPORT')
        TELEGRAM_CHANNEL_ID_TEST                    =   os.environ.get('TELEGRAM_CHANNEL_ID_TEST')
        TELEGRAM_USER_ID_DEV                        =   os.environ.get('TELEGRAM_USER_ID_DEV')
        IS_DEV                                      =   False

def isNxtKey(*args):
    global NXT_KEY
    global TEST_SEND_YN
    global SEND_YN
    global SEND_TIME_TERM
    global TODAY_SEND_YN
    global conn
    global cursor

    print('isNxtKey')

    print('input ', args[0] , ' \nNXT_KEY ', NXT_KEY)
    if SEND_YN == 'N' or args[0] in NXT_KEY: return True
    else: return False
    
def main():
    global SEC_FIRM_ORDER  # 증권사 순번
    global REFRESH_TIME # 새로고침 주기
    global SECRETS # 시크릿 키
    global INTERVAL_TIME # 새로고침 주기 - 파일
    global TEST_SEND_YN

    GetSecretKey()

    print(GetCurrentDay())
    
    try: strArgs = sys.argv[1]
    except: strArgs = ''

    if 'news' in strArgs: print("ChosunBizBot_checkNewArticle()=> 새 게시글 정보 확인 # 995");  ChosunBizBot_checkNewArticle(); print("NAVERNews_checkNewArticle()=> 새 게시글 정보 확인 # 998"); NAVERNews_checkNewArticle(); return

    if strArgs: 
        TEST_SEND_YN = 'Y'

        payload = {"pageNo":1,"pageSize":12,"registdateFrom":"20220727","registdateTo":"20230727","keyword":"","templateid":"","lowTempId":"79,63,64,65,66,67,68,69,75,76,137,193,77,78,74,184,185,174,81,82,83,84,70,71,73,177,191,192,85,156,86,158,166,162,88,160,89,90,91,92,161,169,171,93,94,183,180,164,103,104,105,106,107,108,109,110,111,112,133,167,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,188","folderid":"","callGbn":"RCLIST"}

        try:
            webpage = requests.post('https://rc.kbsec.com/ajax/reNewCategoryReportList.json',data=payload , headers={'Content-Type':'application/json','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'})
            print(webpage.text)
            jres = json.loads(webpage.text)
        except:
            return True
            
        if jres['totalCount'] == 0 : return ''
        print(jres['researchList'])

        # EBEST_checkNewArticle()
        # print("NAVER_Report_checkNewArticle()=> 새 게시글 정보 확인") # 900
        # NAVER_Report_checkNewArticle()
        # gd.gd(str(strArgs))
        print('test')
        return 


    if GetCurrentDay() == '토' or GetCurrentDay() == '일':
        REFRESH_TIME = 60 * 60 * 2 # 2시간
        INTERVAL_TIME = 12
    else:
        REFRESH_TIME = 60 * 30 # 30분
        INTERVAL_TIME = 3
    
    # 개발 환경이 아닌 경우에만 인터벌 작동
    # if IS_DEV: pass
    # else: SetSleepTime()

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

        print("fnguideTodayReport_checkNewArticle()=> 새 게시글 정보 확인") # 123
        fnguideTodayReport_checkNewArticle()

        print("NAVER_Report_checkNewArticle()=> 새 게시글 정보 확인") # 900
        NAVER_Report_checkNewArticle()

        print("EBEST_checkNewArticle()=> 새 게시글 정보 확인") # 0
        EBEST_checkNewArticle()

        print("ShinHanInvest_checkNewArticle()=> 새 게시글 정보 확인") # 1
        ShinHanInvest_checkNewArticle()

        print("HANA_checkNewArticle()=> 새 게시글 정보 확인") # 3
        HANA_checkNewArticle()

        print("Samsung_checkNewArticle()=> 새 게시글 정보 확인") # 5
        Samsung_checkNewArticle()

        print("Kiwoom_checkNewArticle()=> 새 게시글 정보 확인") # 10
        Kiwoom_checkNewArticle()

        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.

        return 
        print('######',REFRESH_TIME,'초 후 게시글을 재 확인 합니다.######')
        time.sleep(REFRESH_TIME)

if __name__ == "__main__":
	main()