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

from package import googledrive

# TEST 
# from package import herokuDB
# from package import SecretKey

# import secretkey

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
SECRETS                                             = ""
CLEARDB_DATABASE_URL                                = ""
ORACLECLOUD_MYSQL_DATABASE_URL                      = ""
TELEGRAM_BOT_INFO                                   = ""
TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET              = ""
TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET             = ""
TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS                 = ""
TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS                  = ""
TELEGRAM_CHANNEL_ID_ITOOZA                          = ""
TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT                    = ""
TELEGRAM_CHANNEL_ID_REPORT_ALARM                    = ""
TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN                 = ""
TELEGRAM_CHANNEL_ID_TEST                            = ""
TELEGRAM_USER_ID_DEV                                = ""
IS_DEV                                              = ""

# 게시글 갱신 시간
REFRESH_TIME = 60 * 20 # 20분

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


#################### global 변수 정리 ###################################
FIRM_NM = ''
BOARD_NM = ''
#################### global 변수 정리 끝###################################

def EBEST_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER
    
    SEC_FIRM_ORDER = 0
    ARTICLE_BOARD_ORDER = 0

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
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''

    return sendMessageText

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
    
    ARTICLE_BOARD_NAME =  BOARD_NM 
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
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE) 
    if TEST_SEND_YN == 'Y' : r = ''
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
        # if  TEST_SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                # ATTACH_URL = 'https://docs.google.com/viewer?embedded=true&url='+EBEST_downloadFile(LIST_ARTICLE_URL)
                ATTACH_URL = EBEST_downloadFile(LIST_ARTICLE_URL)
                # if ARTICLE_BOARD_ORDER == 0 or ARTICLE_BOARD_ORDER == 1 :
                #     LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("(수정)", "")
                #     LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]")+1:len(LIST_ARTICLE_TITLE)]

                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("(수정)", "")
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find("]")+1:len(LIST_ARTICLE_TITLE)]
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

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
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').text
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

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += ShinHanInvest_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''

    return sendMessageText
 
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
    FIRST_ARTICLE_TITLE = jres['list'][0]['f1']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if TEST_SEND_YN == 'Y' : r = ''
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
        LIST_ARTICLE_TITLE = list['f1']

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                DownloadFile(URL = list['f3'], FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
                LIST_ARTICLE_URL = list['f3']
                try:
                    LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('shinhaninvest.com', 'shinhansec.com')
                    LIST_ARTICLE_URL = LIST_ARTICLE_URL.replace('/board/message/file.do?', '/board/message/file.pdf.do?')
                except Exception as e:
                    print("에러 발생:", e)
                    LIST_ARTICLE_URL = list['f3']
                    
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText


def KB_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 4
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 신한금융투자 산업분석
    TARGET_URL_0 = 'https://rc.kbsec.com/ajax/categoryReportList.json'
    TARGET_URL   = 'https://rc.kbsec.com/ajax/categoryReportList.json'
    # 신한금융투자 기업분석
    # TARGET_URL_1 = ''
    
    # TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    TARGET_URL_TUPLE = (TARGET_URL_0)
    
    
    sendMessageText = ''
    # URL GET
    try:
        sendMessageText += KB_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    except:
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''

    return sendMessageText
 
# JSON API 타입
def KB_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

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
        # print(jres)  # 데이터 출력 또는 처리
        # return
    else:
        print("요청에 실패했습니다. 상태 코드:", response.status_code)
        
   
    strList = jres['response']['reportList']
    print(strList)
    
    FIRST_ARTICLE_TITLE = strList[0]['docTitleSub']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if TEST_SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for list in strList:
        print(list)

        # if int(list['categoryid']) == 122 : # 기업  
        #     LIST_ARTICLE_TITLE = list['docTitle'] + " - " + list['urlLink']
        # elif int(list['categoryid']) == 110 : # 산업  
        LIST_ARTICLE_TITLE = list['docTitleSub']

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                LIST_ARTICLE_TITLE = list['docTitle'] + " : " + list['docTitleSub']
                LIST_ARTICLE_URL = list['urlLink'].replace("wInfo=(wInfo)&", "")
                # LIST_ARTICLE_URL = DownloadFile(URL = list['f3'], FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                # if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def NHQV_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 2
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # NH투자증권
    # TARGET_URL =  'https://m.nhqv.com/research/newestBoardList'
    TARGET_URL =  'https://m.nhqv.com/research/commonTr.json'
    
    TARGET_URL_TUPLE = (TARGET_URL)

    sendMessageText = ''
    
    try:
        sendMessageText += NHQV_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    except:
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''
                
    return sendMessageText
 
def NHQV_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN
    global BOARD_NM

    
    strNxtRshPprNo = ""
    payload = {
        "trName": "H3211",
        "rshPprDruTmSt": "00000000",
        "rshPprDruDtSt": GetCurrentDate("YYYYMMDD"),
        "rshPprDruDtEd": GetCurrentDate("YYYYMMDD"),
        "rshPprNo": ""
    }
    
    r = ""
    i = 1
    listR = []
    while True:
        
        print('************************************')
        try:
            webpage = requests.post(TARGET_URL,
                                    headers={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
                                                        'Accept':'application/json, text/javascript, */*; q=0.01'},
                                    data=payload)
            # print(webpage.text)
            jres = json.loads(webpage.text)
            # print(jres)
            
        except:
            return True
        
        nNewArticleCnt = int(jres['H3211']['H3211OutBlock1'][0]['iqrCnt'])
        
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
    FIRST_ARTICLE_TITLE = listR[0]['rshPprTilCts']
    FIRST_ARTICLE_URL =  listR[0]['hpgeFleUrlCts']

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
    
    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if TEST_SEND_YN == 'Y' : r = False
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return '' 
    
    # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')
    
    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        print('*******************************')
        print(list)

        BOARD_NM            = list['rshPprSerCdNm']
        LIST_ARTICLE_TITLE = list['rshPprTilCts']
        LIST_ARTICLE_URL =  list['hpgeFleUrlCts']

        print('BOARD_NM',BOARD_NM)
        print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
        print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
        print('NXT_KEY',NXT_KEY)
        
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                
                print(LIST_ARTICLE_URL)
                if LIST_ARTICLE_URL:
                    # LIST_ARTICLE_URL = DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
                    # 구글드라이브에 저장만(당분간)
                    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
                else: continue
                # print(LIST_ARTICLE_URL)
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def HANA_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 3
    ARTICLE_BOARD_ORDER = 0

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
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText

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
        ARTICLE_BOARD_NAME =  BOARD_NM 
        FIRST_ARTICLE_TITLE = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li:nth-child(1)> div.con > ul > li.mb4 > h3 > a:nth-child(1)')[FIRST_ARTICLE_INDEX].text
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
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
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
        LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').text
        LIST_ARTICLE_URL =  'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
        # LIST_ATTACT_FILE_NAME = list.select_one('div.con > ul > li:nth-child(5)> div > a').text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def HANA_downloadFile(LIST_ARTICLE_URL, LIST_ATTACT_FILE_NAME):
    global ATTACH_FILE_NAME
    ATTACH_FILE_NAME = LIST_ATTACT_FILE_NAME #BeautifulSoup(webpage.content, "html.parser").select_one('#contents > div > div.bbs_a_view > dl.b_bottom > dd > em:nth-child(1)> a').text
    
    DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = ATTACH_FILE_NAME)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def Samsung_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

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

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += Samsung_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText

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
        ARTICLE_BOARD_NAME =  BOARD_NM 
        FIRST_ARTICLE_TITLE = soup.select('#content > section.bbsLstWrap > ul > li:nth-child(1)> a > dl > dt > strong')[FIRST_ARTICLE_INDEX].text
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
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )
        if "(수정)"  in FIRST_ARTICLE_TITLE and NXT_KEY == FIRST_ARTICLE_TITLE.replace("(수정)", ""):  # 첫번째 게시글이 수정된 경우 무한발송 방지  
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''

    # for list in soupList:
    #     LIST_ARTICLE_TITLE = list.select('#content > section.bbsLstWrap > ul > li > a > dl > dt > strong')[FIRST_ARTICLE_INDEX].text
    #     if NXT_KEY == LIST_ARTICLE_TITLE: break
    #     else: DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_TITLE = list.select_one('#content > section.bbsLstWrap > ul > li > a > dl > dt > strong').text
        a_href = list.select_one('#content > section.bbsLstWrap > ul > li > a').attrs['href']
        a_href = a_href.replace('javascript:downloadPdf(', '').replace(';', '')
        a_href = a_href.split("'")
        a_href = a_href[1]
        LIST_ARTICLE_URL =  'https://www.samsungpop.com/common.do?cmd=down&saveKey=research.pdf&fileName=' + a_href+ '&contentType=application/pdf&inlineYn=Y'
        fileNameArray = a_href.split("/")
        # LIST_ATTACT_FILE_NAME = fileNameArray[1].strip()

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("(수정)", "")
                LIST_ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find(")")+1:len(LIST_ARTICLE_TITLE)]
                # print(LIST_ARTICLE_TITLE)
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)                
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def Sangsanginib_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

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

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += Sangsanginib_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText

def Sangsanginib_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    jres = ''
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

    try:
        webpage = requests.post(TARGET_URL, headers=headers, data=data)
        # print(webpage.text)
        jres = json.loads(webpage.text)
        # print(jres)
    except:
        return True
    print('#################도착###############')    
    # print(jres['getNoticeList'])
    print(jres[0]['getStarCnt'])
    FIRST_ARTICLE_TITLE = jres[0]['getNoticeList'][0]['TITLE']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM ,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM ,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
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
    for list in jres[0]['getNoticeList']:
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        print('list***************** \n',list)
        # 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb=CR&attaFile=1650493541463.pdf&makeDt=2022.04.21'
        # LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}' 
        # print('cmsCd[ARTICLE_BOARD_ORDER]',cmsCd[ARTICLE_BOARD_ORDER])
        print('NT_NO=',list['NT_NO'], 'CMS_CD=',cmsCd[ARTICLE_BOARD_ORDER])
        LIST_ARTICLE_URL = Sangsanginib_detail(NT_NO=list['NT_NO'], CMS_CD=cmsCd[ARTICLE_BOARD_ORDER])
        print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
        LIST_ARTICLE_TITLE = list['TITLE']
        print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                # if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText
        # sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        # sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def Sangsanginib_detail(NT_NO, CMS_CD):
    ntNo = NT_NO
    cmsCd = CMS_CD
    print('Sangsanginib_detail***********************')
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
    if response.status_code == 200:
        print(response.text)
    else:
        print("Failed to fetch data.")
    
    print(json.loads(response.text))
    print('**********JSON!!!!!')
    jres = json.loads(response.text)
    # print('##############11111',jres)
    jres = jres['file'][0] #PDF
    print('################222222',jres) 
    # https://www.sangsanginib.com/common/fileDownload?cmsCd=CM0078&ntNo=4315&fNo=1&fNm=%5BSangSangIn%5D2022038_428.pdf

    # 기본 URL과 쿼리 매개변수 딕셔너리
    base_url = 'https://www.sangsanginib.com/common/fileDownload'
    params = {
        'cmsCd': jres['CMS_CD'],
        'ntNo': jres['NT_NO'],
        'fNo': jres['FNO'], # PDF
        'fNm': jres['FNM']
    }
    print(params)
    url = base_url
    if params:
        print('urlparse(params)', urlparse.urlencode(params))
        encoded_params = urlparse.urlencode(params)  # 쿼리 매개변수를 인코딩
        url += '?' + encoded_params
    
    print('*******************완성된 URL',url)
    return url

def Shinyoung_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 7
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()
    # 신영증권 리서치
    TARGET_URL = "https://www.shinyoung.com/Common/selectPaging/research_shinyoungData"
    # # 상상인증권 투자전략
    # TARGET_URL_0 =  "https://www.sangsanginib.com/notice/getNoticeList"
    # # 상상인증권 산업 리포트
    # TARGET_URL_1 =  TARGET_URL_0
    # # 상상인증권 기업 리포트
    # TARGET_URL_2 =  TARGET_URL_0
    
    # TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

    sendMessageText = ''
    
    try:
        sendMessageText += Shinyoung_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    except:
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''
                
    return sendMessageText

def Shinyoung_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    jres = ''
    url = "https://www.shinyoung.com/Common/selectPaging/research_shinyoungData"
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

    try:
        webpage = requests.post(TARGET_URL, headers=headers, data=data)
        if webpage.status_code == 200:
            # print(webpage.text)  # 응답 내용 출력
            jres = json.loads(webpage.text)
        else:
            print("Failed to fetch page:", webpage.status_code)
            return True
    except Exception as e:
        print("An error occurred:", str(e))
        return True

    print(jres['rows'])
    
    FIRST_ARTICLE_TITLE = jres['rows'][0]['TITLE']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM ,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM ,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if TEST_SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    
    # JSON To List
    for list in jres['rows']:
        print('list***************** \n',list)
        # print('NT_NO=',list['NT_NO'], 'CMS_CD=',cmsCd[ARTICLE_BOARD_ORDER])
        LIST_ARTICLE_URL = Shinyoung_detail(SEQ=list['SEQ'], BBSNO=list['BBSNO'])
        print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
        LIST_ARTICLE_TITLE = list['TITLE']
        print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText
        # sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        # sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def Shinyoung_detail(SEQ, BBSNO):
    # ntNo = NT_NO
    # cmsCd = CMS_CD
    # POST 요청에 사용할 URL
    url = "https://www.shinyoung.com/Common/authTr/devPass"


    # 추가할 request header
    headers = {
        'Accept': 'text/plain, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Host': 'www.shinyoung.com',
        'Origin': 'https://www.shinyoung.com',
        'Pragma': 'no-cache',
        'Referer': 'https://www.shinyoung.com/?page=10026',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"'
    }

    # POST 요청 보내기
    response = requests.post(url, headers=headers)

    # 응답의 내용 확인
    if response.status_code == 200:
        # 여기에 크롤링할 내용을 처리하는 코드를 작성하세요.
        # response.text를 사용하여 HTML을 분석하거나, 필요한 데이터를 추출하세요.
        print(response.text)
    else:
        print("요청에 실패하였습니다. 상태 코드:", response.status_code)


    # POST 요청에 사용할 URL
    url = "https://www.shinyoung.com/Common/authTr/downloadFilePath"

    # POST 요청에 포함될 데이터
    data = {
        'SEQ': SEQ,
        'BBSNO': BBSNO
    }

    # 추가할 request header
    headers = {
        'Accept': 'text/plain, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko,en-US;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Cookie': 'JSESSIONID=KyWlsEhZ0A8LdQaILHM6Rm-zoVnF6FVb4QfC5E3u.was01',
        'Host': 'www.shinyoung.com',
        'Origin': 'https://www.shinyoung.com',
        'Pragma': 'no-cache',
        'Referer': 'https://www.shinyoung.com/?page=10026',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"'
    }

    # POST 요청 보내기
    response = requests.post(url, data=data, headers=headers)

    # 응답의 내용 확인
    if response.status_code == 200:
        # 여기에 크롤링할 내용을 처리하는 코드를 작성하세요.
        # response.text를 사용하여 HTML을 분석하거나, 필요한 데이터를 추출하세요.
        print(response.text)
    else:
        print("요청에 실패하였습니다. 상태 코드:", response.status_code)
        # https://www.sangsanginib.com/common/fileDownload?cmsCd=CM0078&ntNo=4315&fNo=1&fNm=%5BSangSangIn%5D2022038_428.pdf

    jres = json.loads(response.text)
    
    print('************\n',jres)
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

    print('*******************완성된 URL',url)
    return url

def Miraeasset_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 8
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 미래에셋 Daily
    TARGET_URL_0 =  "https://securities.miraeasset.com/bbs/board/message/list.do?categoryId=1521"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += Miraeasset_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText

def Miraeasset_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    print('ddd?')
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Host": "securities.miraeasset.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers)
        response.raise_for_status()  # 오류가 발생하면 예외를 발생시킵니다.
    except requests.exceptions.RequestException as e:
        print("웹 페이지에 접속하는 중 오류가 발생했습니다:", e)


    print('ddd?')
    soup = BeautifulSoup(response.text, "html.parser")
    # 첫 번째 레코드의 제목을 바로 담습니다.
    first_post = soup.select_one("tbody tr")
    print('ddd?()', first_post[1])
    FIRST_ARTICLE_TITLE = first_post[1].select_one(".subject a").get_text()

    print("첫 번째 레코드의 제목:", FIRST_ARTICLE_TITLE)
    soupList = soup.select('#container > div.rc_area_con > div.daily_bbs.m-mb20 > ul > li')

    ARTICLE_BOARD_NAME =  BOARD_NM 

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
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

    # 게시물 정보 파싱
    posts = soup.select("tbody tr")
    for index, post in enumerate(posts):
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


    return
    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').text
        LIST_ARTICLE_URL =  'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
        # LIST_ATTACT_FILE_NAME = list.select_one('div.con > ul > li:nth-child(5)> div > a').text

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def Kiwoom_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 10
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 삼성증권 기업 분석
    TARGET_URL_0 =  'https://bbn.kiwoom.com/research/SResearchCRListAjax'
    # 삼성증권 산업 분석
    TARGET_URL_1 =  'https://bbn.kiwoom.com/research/SResearchCIListAjax'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += Kiwoom_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText
 
def Kiwoom_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    payload = {
        "pageNo": 1,
        "pageSize": 10,
        "stdate": GetCurrentDate("yyyymmdd"),
        "eddate": GetCurrentDate("yyyymmdd"),
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
    FIRST_ARTICLE_TITLE = jres['researchList'][0]['titl']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM ,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM ,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
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
        LIST_ARTICLE_TITLE = list['titl']

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def Hmsec_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 9
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 현대차증권 투자전략
    TARGET_URL_0 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=1'
    
    # 현대차증권 Report & Note 
    TARGET_URL_1 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=2' 
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += Hmsec_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText
 
def Hmsec_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    payload = {"curPage":1}

    jres = ''
    try:
        webpage = requests.post(url=TARGET_URL ,data=payload , headers={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'})
        print(webpage.text)
        jres = json.loads(webpage.text)
    except:
        return ''
        
    print(jres['data_list'])
    
    FIRST_ARTICLE_TITLE = jres['data_list'][0]['SUBJECT']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    
    REG_DATE = jres['data_list'][0]['REG_DATE'].strip()
    print('REG_DATE:',REG_DATE)
    
    FILE_NAME = jres['data_list'][0]['UPLOAD_FILE1'].strip()
    print('FILE_NAME:',FILE_NAME)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName() ,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName() ,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)

    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for list in jres['data_list']:
        print(list)
        # https://www.hmsec.com/documents/research/20230103075940673_ko.pdf
        LIST_ATTACHMENT_URL = 'https://www.hmsec.com/documents/research/{}' 
        LIST_ATTACHMENT_URL = LIST_ATTACHMENT_URL.format(list['UPLOAD_FILE1'])

        # https://docs.hmsec.com/SynapDocViewServer/job?fid=#&sync=true&fileType=URL&filePath=#
        LIST_ARTICLE_URL = 'https://docs.hmsec.com/SynapDocViewServer/job?fid={}&sync=true&fileType=URL&filePath={}' 
        LIST_ARTICLE_URL = LIST_ARTICLE_URL.format(LIST_ATTACHMENT_URL, LIST_ATTACHMENT_URL)

        LIST_ARTICLE_TITLE = list['SUBJECT']

        REG_DATE = jres['data_list'][0]['REG_DATE'].strip()
        print(jres['data_list'])
        SERIAL_NO = jres['data_list'][0]['SERIAL_NO']
        print('REG_DATE:',REG_DATE)
        print('LIST_ATTACHMENT_URL : ',LIST_ATTACHMENT_URL,'\nLIST_ARTICLE_URL : ',LIST_ARTICLE_URL, '\nLIST_ARTICLE_TITLE: ',LIST_ARTICLE_TITLE,'\nREG_DATE :', REG_DATE)
        print('SERIAL_NO:',SERIAL_NO)

        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                # LIST_ARTICLE_URL = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
                sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                # GET Content
                # payload = {
                #     "Menu_category": 6,
                #     "queryType": "",
                #     "serialNo": 30132,
                #     "curPage": 1
                # }
                # jres = ''
                # try:
                #     webpage = requests.post('https://m.hmsec.com/mobile/research/research01_view.do?Menu_category=6',data=payload)
                #     print(webpage.text)
                # except:
                #     return False

                # # HTML parse
                # soup = BeautifulSoup(webpage.content, "html.parser")
                # soupList = soup.select('body > div > table > tbody > tr')
                # return ""
                print(sendMessageText)
            else:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
                print(sendMessageText)
                nNewArticleCnt = 0
                sendMessageText = ''

        elif SEND_YN == 'N':
            print('###점검중 확인요망###')
        else:
            if nNewArticleCnt == 0  or len(sendMessageText) == 0:
                print('최신 게시글이 채널에 발송 되어 있습니다.')


            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
            return sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE) # 뉴스의 경우 연속 데이터가 다음 페이지로 넘어갈 경우 처리
            
    print(sendMessageText)
    return sendMessageText

def HankyungConsen_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 12

    requests.packages.urllib3.disable_warnings()

    TARGET_URL =  'https://consensus.hankyung.com/' #'http://www.bnkfn.co.kr/research/analysingCompany.jspx'

    sendMessageText = ''
    try:
        sendMessageText += HankyungConsen_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    except:
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''
                
    return sendMessageText

    # TARGET_URL_TUPLE = (TARGET_URL)

    # sendMessageText = ''
    # # URL GET
    # for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
    #     try:
    #         sendMessageText += HankyungConsen_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    #     except:
    #         if len(sendMessageText) > 3500:
    #             print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
    #             sendAddText(GetSendMessageTitle() + sendMessageText)
    #             sendMessageText = ''
                
    # return sendMessageText

def HankyungConsen_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN
    # TARGET_URL = 'https://consensus.hankyung.com/analysis/list?sdate=2023-03-15&edate=2023-09-15&now_page=1&search_value=&report_type=&pagenum=20&search_text=&business_code='
    try:
        webpage = requests.get(TARGET_URL, verify=False, headers={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'})
    except:
        return True

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    # print(soup)
    # return 
    soupList = soup.select('#contents > div.table_style01 > table > tbody > tr')
    print(soupList)
    try:
        ARTICLE_BOARD_NAME =  BOARD_NM 
        FIRST_ARTICLE_TITLE = soup.select('#contents > div.table_style01 > table > tbody > tr:nth-child(1) > td.text_l > a')[FIRST_ARTICLE_INDEX].text
        FIRST_ARTICLE_URL =  'https://consensus.hankyung.com' + soup.select('#contents > div.table_style01 > table > tbody > tr:nth-child(1) > td:nth-child(6) > div > a')[FIRST_ARTICLE_INDEX].attrs['href']
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''

    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)
    print('FIRST_ARTICLE_URL:',FIRST_ARTICLE_URL)

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    # r = isNxtKey(FIRST_ARTICLE_TITLE)
    # if SEND_YN == 'Y' : r = ''
    # if r: 
    #     print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
    #     return '' 
    
    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    brokerName = soup.select('#contents > div.table_style01 > table > tbody > tr.first > td:nth-child(5)')[FIRST_ARTICLE_INDEX].text
    print('brokerName' ,brokerName)
    for list in soupList:
        
        print('*****************')
        # print(list)
        LIST_ARTICLE_TITLE = list.select_one('#contents > div.table_style01 > table > tbody > tr > td.text_l > a').text
        LIST_ARTICLE_URL =  'https://consensus.hankyung.com' + list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(6) > div > a').attrs['href']
        LIST_ARTICLE_BROKER_NAME =list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(5)').text

        print(LIST_ARTICLE_TITLE)
        print(LIST_ARTICLE_URL)
        print('LIST_ARTICLE_BROKER_NAME=',LIST_ARTICLE_BROKER_NAME)
        ATTACH_URL = LIST_ARTICLE_URL
        
        if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            # 회사명 출력
            if nNewArticleCnt == 1 or brokerName != LIST_ARTICLE_BROKER_NAME : # 첫 페이지 이거나 다음 회사명이 다를때만 출력
                sendMessageText += "\n"+ "●"+ LIST_ARTICLE_BROKER_NAME + "\n"
                brokerName = LIST_ARTICLE_BROKER_NAME # 회사명 키 변경

            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = LIST_ARTICLE_TITLE, ATTACH_URL = ATTACH_URL)
                if TEST_SEND_YN == 'Y': return sendMessageText
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
                DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
                return
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

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
    
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")

    # 종목 정보(레포트 수) 
    soupList1 = soup.select('tr > td.sub_mgl10')
    
    # 애널리스트 정보
    soupList2 = soup.select('tr > td:nth-child(5)')

    sendMessageText = ''
    pageCnt = 0
    articleCnt = 0
    NxtArticleCnt = int(NXT_KEY_ARTICLE_TITLE)
    objMessage = ''
    FIRST_MESSAGE_KEY = ''
    for listIsu, listAnalyst in zip(soupList1, soupList2):
        print('######################')
        articleCnt += 1
        try:
            listIsu = listIsu.text
        except:
            continue
        print('***************오류********** == 시작')
        print(listIsu)
        print('***************오류********** ==> 끝')

        listIsu = listIsu.replace("`","")
        listIsu = listIsu.split("|")
        strIsuNm = listIsu[0].strip()
        strIsuNo = strIsuNm.split("(A")
        strIsuNo = strIsuNo[1].replace(")","")
        strIsuUrl = "[종목링크]" + "(" + "https://finance.naver.com/item/main.naver?code=" + strIsuNo + ")"
        listIsu = listIsu[1].split("-  ")
        strReportTitle = listIsu[0].strip().replace("1-","")

        # 17시 발송건일때 이미 전송된 인덱스는 제외처리
        if articleCnt <= NxtArticleCnt and int(GetCurrentTime('HH')) == 17 : continue   

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
            objMessage = sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''
            if pageCnt == 0 : FIRST_MESSAGE_KEY = str(objMessage.message_id)
            pageCnt += 1

    # 나머지 최종 발송
    if len(sendMessageText) > 0 : # 중간 발송
        print('=================================발송구간')
        print(sendMessageText)
        objMessage = sendText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''
        pageCnt += 1


    sendMessageText  = '오늘의 레포트가 발송되었습니다. \n'
    sendMessageText += '확인하려면 링크를 클릭하세요. \n'
    sendMessageText += BOARD_URL + FIRST_MESSAGE_KEY
    asyncio.run(sendAlertMessage(sendMessageText)) #봇 실행하는 코드

    # 연속키 갱신
    dbResult = DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, int(pageCnt), articleCnt)

    # 9시, 17시 두차례 발송을 위해 17시 발송후 발송여부 갱신
    if int(GetCurrentTime('HH')) == 17 :
        # 발송 처리
        dbResult = DB_UpdTodaySendKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER= ARTICLE_BOARD_ORDER, TODAY_SEND_YN = 'Y')

    return True

async def sendAlertMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True)

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

async def sendPlainText(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True)

async def sendDocument(ATTACH_FILE_NAME): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendDocument(chat_id = GetSendChatId(), document = open(ATTACH_FILE_NAME, 'rb'))

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
    

    if DISABLE_WEB_PAGE_PREVIEW: # 첨부파일이 있는 경우 => 프리뷰는 사용하지 않음
        try:
            time.sleep(1) # 메시지 전송 텀을 두어 푸시를 겹치지 않게 함
            #bot.sendDocument(chat_id = GetSendChatId(), document = open(ATTACH_FILE_NAME, 'rb'))
            r = asyncio.run(sendDocument(ATTACH_FILE_NAME)) #봇 실행하는 코드
            os.remove(ATTACH_FILE_NAME) # 파일 전송 후 PDF 삭제
            return r
        except:
            return
    else: 
        return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드    
    
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
    return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드

def sendPhoto(ARTICLE_URL): # 파일의 경우 전역변수로 처리 (downloadFile 함수)
    print('sendPhoto()')

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)

    return bot.sendPhoto(chat_id = GetSendChatId(), photo = ARTICLE_URL)
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# 가공없이 텍스트를 발송합니다.
def sendText(sendMessageText): 
    global CHAT_ID

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
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
    return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# URL에 파일명을 사용할때 한글이 포함된 경우 인코딩처리 로직 추가 
def DownloadFile(URL, FILE_NAME):
    global ATTACH_FILE_NAME
    print("DownloadFile()",URL, FILE_NAME)
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

    # 파일명 지정
    # 날짜 종목 제목 증권사 결국 이 순이 젤 좋아보이네
    # 날짜-대분류-소분류-제목-증권사.pdf
    # TODO 종목명 추가
    FILE_NAME = FILE_NAME.replace(".pdf", "").replace(".PDF", "") # 확장자 제거 후 시작
    print('FILE_NAME 확장자 제거 ,', FILE_NAME)
    FILE_NAME = FILE_NAME.replace(GetCurrentDate('YYYYMMDD')[2:8], "").replace(GetCurrentDate('YYYYMMDD'), "") # 날짜 제거 후 시작
    FILE_NAME = str(GetCurrentDate('YYYYMMDD')[2:8]) + "_" + BOARD_NM + "_" + FILE_NAME + "_" + FIRM_NM

    # 파일명 길이 체크 후, 길면 자르고, 확장자 붙여 마무리함
    MAX_FILE_NAME_LENGTH = 240
    if len(FILE_NAME)  > MAX_FILE_NAME_LENGTH : FILE_NAME = FILE_NAME[0:MAX_FILE_NAME_LENGTH]
    FILE_NAME += '.pdf'
    # if '.pdf' not in FILE_NAME : FILE_NAME = FILE_NAME + '.pdf'

    ATTACH_FILE_NAME = re.sub('[\/:*?"<>|]','',FILE_NAME) # 저장할 파일명 : 파일명으로 사용할수 없는 문자 삭제 변환
    print('convert URL:',URL)
    print('convert ATTACH_FILE_NAME:',ATTACH_FILE_NAME)
    with open(ATTACH_FILE_NAME, "wb")as file:  # open in binary mode
        response = get(URL, verify=False)     # get request
        file.write(response.content) # write to file
        
    r = googledrive.upload(str(ATTACH_FILE_NAME))
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
    elif SEC_FIRM_ORDER == 12: # 한경컨센 나누기
        SendMessageChatId = TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN # 한경 컨센
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
    # MySQL
    url = urlparse.urlparse(ORACLECLOUD_MYSQL_DATABASE_URL)
    conn = pymysql.connect(host=url.hostname, user=url.username, password=url.password, charset='utf8', db=url.path.replace('/', ''), cursorclass=pymysql.cursors.DictCursor, autocommit=True)
    cursor = conn.cursor()
    return cursor

def DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
    global FIRM_NM
    global BOARD_NM
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
    dbQuery  = " SELECT FIRM_NM, BOARD_NM, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, BOARD_URL, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM NXT_KEY		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s "
    dbResult = cursor.execute(dbQuery, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print(row)
        FIRM_NM = row['FIRM_NM']
        BOARD_NM = row['BOARD_NM']
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
    dbQuery  = " SELECT 		SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM NXT_KEY		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   "
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
    dbQuery  = " DELETE  FROM NXT_KEY		WHERE 1=1 AND  SEC_FIRM_ORDER = 9999"
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
        strFirmName = FIRM_NM
    except :
        print('GetFirmName except')
        strFirmName = ''
        
    return strFirmName

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
    elif pattern == 'YYYYMMDD' or pattern == 'yyyymmdd':
        DATE = DATE_SPLIT[0] + DATE_SPLIT[1] +  DATE_SPLIT[2]
    elif pattern == 'YYYY/HH/DD' or pattern == 'yyyy/hh/dd':
        DATE = DATE_SPLIT[0] + "/" + DATE_SPLIT[1] + "/" + DATE_SPLIT[2]
    elif pattern == 'YYYY-HH-DD' or pattern == 'yyyy-hh-dd':
        DATE = time_now[:10].strip()
    elif pattern == 'YY-HH-DD' or pattern == 'yy-hh-dd':
        DATE = time_now[2:10].strip()
    elif pattern == 'YYYYHHDD' or pattern == 'yyyyhhdd':
        DATE = DATE_SPLIT[0] + DATE_SPLIT[1] + DATE_SPLIT[2]
    elif pattern == 'YYYY.MM.DD' or pattern == 'yyyy.mm.dd':
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
    global SECRETS # 시크릿 키
    global CLEARDB_DATABASE_URL
    global ORACLECLOUD_MYSQL_DATABASE_URL
    global TELEGRAM_BOT_INFO
    global TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET
    global TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET
    global TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS
    global TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS
    global TELEGRAM_CHANNEL_ID_ITOOZA
    global TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT
    global TELEGRAM_CHANNEL_ID_REPORT_ALARM
    global TELEGRAM_CHANNEL_ID_TODAY_REPORT
    global TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN
    global TELEGRAM_CHANNEL_ID_TEST
    global TELEGRAM_USER_ID_DEV
    global IS_DEV
    

    SECRETS = ''
    print(os.getcwd())
    if os.path.isfile(os.path.join(os.getcwd(), 'secrets.json')): # 로컬 개발 환경
        with open("secrets.json") as f:
            SECRETS = json.loads(f.read())
        CLEARDB_DATABASE_URL                        =   SECRETS['CLEARDB_DATABASE_URL']
        
        ORACLECLOUD_MYSQL_DATABASE_URL              =   SECRETS['ORACLECLOUD_MYSQL_DATABASE_URL'] 
        TELEGRAM_BOT_INFO                           =   SECRETS['TELEGRAM_BOT_INFO']
        TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   SECRETS['TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET']
        TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   SECRETS['TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET']
        TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS']
        TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS']
        TELEGRAM_CHANNEL_ID_ITOOZA                  =   SECRETS['TELEGRAM_CHANNEL_ID_ITOOZA']
        TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   SECRETS['TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT']
        TELEGRAM_CHANNEL_ID_REPORT_ALARM            =   SECRETS['TELEGRAM_CHANNEL_ID_REPORT_ALARM']
        TELEGRAM_CHANNEL_ID_TODAY_REPORT            =   SECRETS['TELEGRAM_CHANNEL_ID_TODAY_REPORT']
        TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN         =   SECRETS['TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN']
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
        TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN         =   os.environ.get('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
        TELEGRAM_CHANNEL_ID_TEST                    =   os.environ.get('TELEGRAM_CHANNEL_ID_TEST')
        TELEGRAM_USER_ID_DEV                        =   os.environ.get('TELEGRAM_USER_ID_DEV')
        IS_DEV                                      =   False

# 첫 게시글과 연속키 일치 여부를 판별 
# 일치(TRUE)=> 새 게시물이 모두 전송되어 있음
# 불일치(FALSE)=> 새 게시물이 게시되어 전송함
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
    global INTERVAL_TIME # 새로고침 주기 - 파일
    global TEST_SEND_YN

    TEST_SEND_YN = ''
    GetSecretKey()

    print(GetCurrentDate('YYYYMMDD'),GetCurrentDay())
    
    try: strArgs = sys.argv[1]
    except: strArgs = ''

    if  strArgs : 
        TEST_SEND_YN = 'Y'
        sendMessageText = ''
        
        # print("Sangsanginib_checkNewArticle()=> 새 게시글 정보 확인") # 6
        # r = Sangsanginib_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        # print("Shinyoung_checkNewArticle()=> 새 게시글 정보 확인") # 7
        # r = Shinyoung_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r        


        print("Miraeasset_checkNewArticle()=> 새 게시글 정보 확인") # 8
        r = Miraeasset_checkNewArticle()
        if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r


        if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.
        return
        # sendAddText() # 쌓인 메세지를 무조건 보냅니다.        
        sendText("http://146.56.168.28:5000/static/pdf/"+urlparse.quote('240117_산업분석_통신서비스; 4Q23 Preview 총선 전 점검_신한투자증권.pdf'))
        # asyncio.run(sendMessage()
        # print("KB_checkNewArticle()=> 새 게시글 정보 확인") # 4
        # r = KB_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
        # if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        # else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.
        # fnguideTodayReport_checkNewArticle()
        # print("EBEST_checkNewArticle()=> 새 게시글 정보 확인") # 0

        # print("HankyungConsen_checkNewArticle()=> 새 게시글 정보 확인") # 12
        # r = HankyungConsen_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        # if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        # else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.

        # print("EBEST_checkNewArticle()=> 새 게시글 정보 확인") # 0
        # r = EBEST_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        # print("ShinHanInvest_checkNewArticle()=> 새 게시글 정보 확인") # 1
        # r = ShinHanInvest_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        # print("HANA_checkNewArticle()=> 새 게시글 정보 확인") # 3
        # r = HANA_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        # print("Samsung_checkNewArticle()=> 새 게시글 정보 확인") # 5
        # r = Samsung_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        # print("Kiwoom_checkNewArticle()=> 새 게시글 정보 확인") # 10
        # r = Kiwoom_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        # print("Hmsec_checkNewArticle()=> 새 게시글 정보 확인") # 9
        # r = Hmsec_checkNewArticle()
        # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
 

        if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.

        # print("HANA_checkNewArticle()=> 새 게시글 정보 확인") # 3
        # sendMessageText += HANA_checkNewArticle()

        # print("Samsung_checkNewArticle()=> 새 게시글 정보 확인") # 5
        # sendMessageText += Samsung_checkNewArticle()

        # print("Kiwoom_checkNewArticle()=> 새 게시글 정보 확인") # 10
        # sendMessageText += Kiwoom_checkNewArticle()

        # if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        # else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.

        # payload = {"pageNo":1,"pageSize":12,"registdateFrom":"20220727","registdateTo":"20230727","keyword":"","templateid":"","lowTempId":"79,63,64,65,66,67,68,69,75,76,137,193,77,78,74,184,185,174,81,82,83,84,70,71,73,177,191,192,85,156,86,158,166,162,88,160,89,90,91,92,161,169,171,93,94,183,180,164,103,104,105,106,107,108,109,110,111,112,133,167,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,188","folderid":"","callGbn":"RCLIST"}

        # try:
        #     webpage = requests.post('https://rc.kbsec.com/ajax/reNewCategoryReportList.json',data=payload , headers={'Content-Type':'application/json','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'})
        #     print(webpage.text)
        #     jres = json.loads(webpage.text)
        # except:
        #     return True
            
        # if jres['totalCount'] == 0 : return ''
        # print(jres['researchList'])

        # googledrive.upload(str(strArgs))
        print('test')
        return 

    TEST_SEND_YN = ''
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
    
    # print("fnguideTodayReport_checkNewArticle()=> 새 게시글 정보 확인") # 123
    # fnguideTodayReport_checkNewArticle()

    sendMessageText = ''
    
    # print("EBEST_checkNewArticle()=> 새 게시글 정보 확인") # 0
    # r = EBEST_checkNewArticle()
    # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

    print("ShinHanInvest_checkNewArticle()=> 새 게시글 정보 확인") # 1
    r = ShinHanInvest_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("NHQV_checkNewArticle()=> 새 게시글 정보 확인") # 2
    r = NHQV_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

    print("HANA_checkNewArticle()=> 새 게시글 정보 확인") # 3
    r = HANA_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

    print("KB_checkNewArticle()=> 새 게시글 정보 확인") # 4
    r = KB_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

    print("Samsung_checkNewArticle()=> 새 게시글 정보 확인") # 5
    r = Samsung_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Sangsanginib_checkNewArticle()=> 새 게시글 정보 확인") # 6
    r = Sangsanginib_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Shinyoung_checkNewArticle()=> 새 게시글 정보 확인") # 7
    r = Shinyoung_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    # print("Miraeasset_checkNewArticle()=> 새 게시글 정보 확인") # 8
    # r = Miraeasset_checkNewArticle()
    # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Hmsec_checkNewArticle()=> 새 게시글 정보 확인") # 9
    r = Hmsec_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Kiwoom_checkNewArticle()=> 새 게시글 정보 확인") # 10
    r = Kiwoom_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r


    if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
    else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.

    return 
    print('######',REFRESH_TIME,'초 후 게시글을 재 확인 합니다.######')
    time.sleep(REFRESH_TIME)

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
        return 

if __name__ == "__main__":
	main()