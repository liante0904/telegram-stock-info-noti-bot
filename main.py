# -*- coding:utf-8 -*- 
import os
import sys
import datetime
import logging
from pytz import timezone
import telegram
import requests
import time
import ssl
import json
import re
import asyncio
import wget
import pymysql
import pymysql.cursors
from typing import List
from bs4 import BeautifulSoup
import urllib.parse as urlparse
import urllib.request

from package import googledrive
# selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
# secrets 
SECRETS                                             = ""
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
BASE_PATH                                           = ""
# pymysql 변수
conn    = ''
cursor  = ''

# 연속키URL
NXT_KEY = ''
NXT_KEY_BF = ''
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

def LS_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER
    
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

    ## EBEST만 로직 변경 테스트
    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += LS_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''

    return sendMessageText

def LS_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN
    global LIST_ARTICLE_TITLE

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
    }
 
    try:
        webpage = requests.get(TARGET_URL, verify=False, headers=headers)
    except:
        return True
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    soupList = soup.select('#contents > table > tbody > tr')

    # print(soupList[0])
    # soupListTest = soup.select('#contents > table > tbody > tr > td.subject')
    # r = soupListTest.select('a')
    # print(soupListTest[0].select('a'))#[0].get_text())
    # print(len(r))
    # for i in r:
    #     print(i)
    # return 

    ARTICLE_BOARD_NAME =  BOARD_NM 
    try:
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX].select('td.subject > a')[FIRST_ARTICLE_INDEX].get_text()
    except IndexError:
        print('IndexError')

    try:
        FIRST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + soupList[FIRST_ARTICLE_INDEX].select('td.subject > a').attrs['href'].replace("amp;", "")
    except:
        FIRST_ARTICLE_URL = ''

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE) 
    if TEST_SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return ''
    
    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속키:', NXT_KEY) # 주소
    print('############\n\n')

    # print('TEST_SEND_YN ', TEST_SEND_YN)

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        print(list.select('td')[3].get_text())
        date = list.select('td')[3].get_text()
        list = list.select('a')
        # print(list[0].text)
        # print('https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", ""))
        LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + list[0]['href'].replace("amp;", "")
        LIST_ARTICLE_TITLE = list[0].text

        print('LIST_ARTICLE_URL', LIST_ARTICLE_URL)
        print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                # ATTACH_URL = 'https://docs.google.com/viewer?embedded=true&url='+LS_downloadFile(LIST_ARTICLE_URL)
                ATTACH_URL = LS_downloadFile(LIST_ARTICLE_URL, date)
                
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
                return  ''
            else: break
                
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        # sendMessageText = GetSendMessageTitle() + sendMessageText

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText
    
def LS_downloadFile(ARTICLE_URL, date):
    global ATTACH_FILE_NAME
    global LIST_ARTICLE_TITLE
    ARTICLE_URL = ARTICLE_URL.replace('&category_no=&left_menu_no=&front_menu_no=&sub_menu_no=&parent_menu_no=&currPage=1', '')
    print('LS_downloadFile')
    print(date)
    ATTACH_BASE_URL = 'https://www.ls-sec.co.kr/_bt_lib/util/download.jsp?dataType='
    
    try:
        print(ARTICLE_URL)
        webpage = requests.get(ARTICLE_URL, verify=False)
        print('안됐나?')
    except:
        print('여기?')
        return True
    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    # print(soup)
    # 게시글 제목(게시판 리스트의 제목은 짤려서 본문 제목 사용)
    table = soup.select_one('#contents > table')
    tbody = table.select_one('tbody')
    trs = soup.select('tr')
    LIST_ARTICLE_TITLE = trs[0].select_one('td').text
    
    # 첨부파일 URL
    attachFileCode = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a')['href']
    
    ATTACH_URL = attachFileCode.replace('Javascript:download("', ATTACH_BASE_URL).replace('")', '').replace('https', 'http')
    
    # 첨부파일 이름
    ATTACH_FILE_NAME = BeautifulSoup(webpage.content, "html.parser").select_one('.attach > a').get_text()
    print(ATTACH_FILE_NAME)
    # param1 
    URL_PARAM = date
    # print('???>',URL_PARAM)
    URL_PARAM = URL_PARAM.split('.')
    print(URL_PARAM)
    URL_PARAM = 'B' + URL_PARAM[0] + URL_PARAM[1]

    print('인코딩전:',ATTACH_FILE_NAME)
    # URL 인코딩
    ATTACH_URL_FILE_NAME = urllib.parse.quote(ATTACH_FILE_NAME)
    print('인코딩:',ATTACH_URL_FILE_NAME)

    # https://www.ls-sec.co.kr/upload/EtwBoardData/B202405/%5BLS%20ELECTRIC_기업이슈_240524☆%5D성종화_1840_이슈브리프_LS%20ELECTRIC.pdf
    ATTACH_URL = 'https://www.ls-sec.co.kr/upload/EtwBoardData/{0}/{1}'
    ATTACH_URL = ATTACH_URL.format(URL_PARAM, ATTACH_URL_FILE_NAME)

    DownloadFile(URL = ATTACH_URL, FILE_NAME = ATTACH_FILE_NAME)
    print('*********확인용**************')
    print(ATTACH_URL)
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
    return ATTACH_URL


def ShinHanInvest_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 1
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 신한증권 국내산업분석
    TARGET_URL_0 = 'giindustry'
    # 'https://open2.shinhaninvest.com/phone/asset/module/getbbsdata.jsp?url=/mobile/json.list.do%3FboardName%3Dgiindustry%26curPage%3D1&param1=Q1&param2=+&param3=&param4=%2Fmobile%2Fjson.list.do%3FboardName%3Dgiindustry%26curPage%3D1&param5=Q&param6=99999&param7=&type=bbs2'
    
    # 신한증권 국내기업분석
    TARGET_URL_1 = 'gicompanyanalyst'
    #'https://open2.shinhaninvest.com/phone/asset/module/getbbsdata.jsp?url=/mobile/json.list.do%3FboardName%3Dgicompanyanalyst%26curPage%3D1&param1=Q1&param2=+&param3=&param4=%2Fmobile%2Fjson.list.do%3FboardName%3Dgicompanyanalyst%26curPage%3D1&param5=Q&param6=99999&param7=&type=bbs2'

    # 신한증권 국내스몰캡
    TARGET_URL_2 = 'giresearchIPO'
    
    # 신한증권 해외주식
    TARGET_URL_3 = 'foreignstock'
    #'https://open2.shinhaninvest.com/phone/asset/module/getbbsdata.jsp?url=/mobile/json.list.do%3FboardName%3Dgicompanyanalyst%26curPage%3D1&param1=Q1&param2=+&param3=&param4=%2Fmobile%2Fjson.list.do%3FboardName%3Dgicompanyanalyst%26curPage%3D1&param5=Q&param6=99999&param7=&type=bbs2'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1,TARGET_URL_2,TARGET_URL_3)

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
    url = (f"{base_url}?url=/mobile/json.list.do?boardName={board_name}&curPage={cur_page}"
           f"&param1={param1}&param2={param2}&param3={param3}&param4={param4}&param5={param5}"
           f"&param6={param6}&param7={param7}&type={type_param}")


    #request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    print('신한 request URL:', url)
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if TEST_SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for list in jres['list']:
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        print(list)

        LIST_ARTICLE_URL = 'https://docs.google.com/viewer?embedded=true&url='+ list['f3']
        LIST_ARTICLE_TITLE = list['f1']

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
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

    # KB증권 산업분석
    TARGET_URL_0 = 'https://rc.kbsec.com/ajax/categoryReportList.json'
    TARGET_URL   = 'https://rc.kbsec.com/ajax/categoryReportList.json'
    # KB증권 기업분석
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if TEST_SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for list in strList:
        print(list)

        LIST_ARTICLE_TITLE = list['docTitleSub']

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                if list['docTitle'] not in list['docTitleSub'] : LIST_ARTICLE_TITLE = list['docTitle'] + " : " + list['docTitleSub']
                else: LIST_ARTICLE_TITLE = list['docTitleSub']
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
    
    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if TEST_SEND_YN == 'Y' : r = False
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return '' 
    
    # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############\n\n')
    
    # 연속키있으나, 게시판에서 삭제된 경우 : 현재의 첫 게시물로 연속키 갱신
    # 중복 발송 방지
    if NXT_KEY not in str(soupList):
        print('기존 연속키:', NXT_KEY, '가 존재하지 않습니다.')
        print('첫번째 게시물 연속키를 저장합니다 :', FIRST_ARTICLE_TITLE)
        DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
        return ''

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
        
        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
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

    TARGET_URLS = [
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
        'https://www.hanaw.com/main/research/research/list.cmd?pid=2&cid=4'
    ]

    sendMessageText = ''
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URLS):
        try:
            sendMessageText += HANA_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except Exception as e:
            if len(sendMessageText) > 3500:
                print(f"발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n{sendMessageText}")
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return '' 
    
    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############\n\n')

    # 연속키있으나, 게시판에서 삭제된 경우 : 현재의 첫 게시물로 연속키 갱신
    # 중복 발송 방지
    if NXT_KEY not in str(soupList):
        print('기존 연속키:', NXT_KEY, '가 존재하지 않습니다.')
        print('첫번째 게시물 연속키를 저장합니다 :', FIRST_ARTICLE_TITLE)
        DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
        return ''

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_TITLE = list.select_one('div.con > ul > li.mb4 > h3 > a').text
        LIST_ARTICLE_URL =  'https://www.hanaw.com' + list.select_one('div.con > ul > li:nth-child(5)> div > a').attrs['href']
        # LIST_ATTACT_FILE_NAME = list.select_one('div.con > ul > li:nth-child(5)> div > a').text

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )
            
    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return ''

    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############\n\n')

    # 연속키있으나, 게시판에서 삭제된 경우 : 현재의 첫 게시물로 연속키 갱신
    # 중복 발송 방지
    if NXT_KEY not in str(soupList):
        print('기존 연속키:', NXT_KEY, '가 존재하지 않습니다.')
        print('첫번째 게시물 연속키를 저장합니다 :', FIRST_ARTICLE_TITLE)
        DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
        return ''

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

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                ARTICLE_TITLE = ''
                # 수정된 제목인지 확인
                if '(수정)' in LIST_ARTICLE_TITLE : r = True
                # 제목 가공
                ARTICLE_TITLE = LIST_ARTICLE_TITLE.replace("(수정)", "")
                ARTICLE_TITLE = LIST_ARTICLE_TITLE[LIST_ARTICLE_TITLE.find(")")+1:len(LIST_ARTICLE_TITLE)]
                if r : ARTICLE_TITLE = '(수정)' + LIST_ARTICLE_TITLE

                if ARTICLE_TITLE.isspace(): pass
                else: LIST_ARTICLE_TITLE = ARTICLE_TITLE
                # print(LIST_ARTICLE_TITLE)
                DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
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
    
    FIRST_ARTICLE_TITLE = jres[0]['getNoticeList'][0]['TITLE']
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
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
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
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
        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
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
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
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
        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
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
    print('******************Shinyoung_detail***************')
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
    if response.status_code == 200:
        # 여기에 크롤링할 내용을 처리하는 코드를 작성하세요.
        # response.text를 사용하여 HTML을 분석하거나, 필요한 데이터를 추출하세요.
        print('devPass:', response.text)
    else:
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
    if response.status_code == 200:
        # 여기에 크롤링할 내용을 처리하는 코드를 작성하세요.
        # response.text를 사용하여 HTML을 분석하거나, 필요한 데이터를 추출하세요.
        print('checkAuth', response.text)
    else:
        print("요청에 실패하였습니다. 상태 코드:", response.status_code)
    # POST 요청에 사용할 URL
    url = "https://www.shinyoung.com/Common/authTr/downloadFilePath"

    # POST 요청에 포함될 데이터
    data = {
        'SEQ': SEQ,
        'BBSNO': BBSNO
    }
    print(data)
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
    if response.status_code == 200:
        # 여기에 크롤링할 내용을 처리하는 코드를 작성하세요.
        # response.text를 사용하여 HTML을 분석하거나, 필요한 데이터를 추출하세요.
        print('최종파일')
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

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
    }
    
    try:
        response = requests.get(TARGET_URL, headers=headers)
        response.raise_for_status()  # 오류가 발생하면 예외를 발생시킵니다.
    except requests.exceptions.RequestException as e:
        print("웹 페이지에 접속하는 중 오류가 발생했습니다:", e)


    soup = BeautifulSoup(response.text, "html.parser")
    
    # 첫 번째 레코드의 제목을 바로 담습니다.
    posts = soup.select("tbody tr")[2:]  # 타이틀 제거
    FIRST_ARTICLE_TITLE = posts[0].select_one(".subject a").get_text()
    print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    ARTICLE_BOARD_NAME =  BOARD_NM 

    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return '' 
    
    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############\n\n')

    # 게시물 정보 파싱
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

    soupList = posts
    # 연속키있으나, 게시판에서 삭제된 경우 : 현재의 첫 게시물로 연속키 갱신
    # 중복 발송 방지
    if NXT_KEY not in str(soupList):
        print('기존 연속키:', NXT_KEY, '가 존재하지 않습니다.')
        print('첫번째 게시물 연속키를 저장합니다 :', FIRST_ARTICLE_TITLE)
        DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
        return ''

    nNewArticleCnt = 0
    sendMessageText = ''
    for list in soupList:
        LIST_ARTICLE_TITLE = list.select_one(".subject a").text
        LIST_ARTICLE_URL = "없음"
        attachment_element = list.select_one(".bbsList_layer_icon a")
        if attachment_element:
            LIST_ARTICLE_URL = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"]).group(1)

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                r = list.select_one(".subject a").find_all(string=True)
                r = " : ".join(r)
                DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
                sendMessageText += GetSendMessageTextMarkdown(ARTICLE_TITLE = r, ATTACH_URL = ATTACH_URL)
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

    # 키움증권 기업 분석
    TARGET_URL_0 =  'https://bbn.kiwoom.com/research/SResearchCRListAjax'
    # 키움증권 산업 분석
    TARGET_URL_1 =  'https://bbn.kiwoom.com/research/SResearchCIListAjax'
    # 키움증권 스팟 노트
    TARGET_URL_2 =  'https://bbn.kiwoom.com/research/SResearchSNListAjax'
    # 키움증권 미국/선진국
    TARGET_URL_3 =  'https://bbn.kiwoom.com/research/SResearchCCListAjax'

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1,TARGET_URL_2, TARGET_URL_3)

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
        "stdate": '20231023',
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
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
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
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

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
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
    
    # 현대차증권 해외주식
    TARGET_URL_2 =  'https://www.hmsec.com/research/research_list_ajax.do?Menu_category=8'
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2)

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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName() ,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName() ,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)

    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
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

        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                # LIST_ARTICLE_URL = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
                # ATTACH_FILE_NAME = DownloadFile(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')

                DownloadFile_wget(URL = LIST_ATTACHMENT_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
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

def LS_selenium_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 11
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 이베스트 리서치 모바일
    TARGET_URL_0 =  "https://m.ebestsec.co.kr/invest/research/"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += LS_selenium_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText

def LS_selenium_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    # 헤드리스 모드로 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")

    # Chrome 드라이버 초기화
    driver = webdriver.Chrome(options=chrome_options)

    # 웹 페이지 열기
    driver.get(TARGET_URL)

    # wait until someid is clickable
    wait = WebDriverWait(driver, 10)
    element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'board-list')))
    # EC.presence_of_element_located
    # 모든 링크 요소 선택하기
    link_elements = driver.find_elements(By.XPATH, "//div[@id='wrap']/div/div/div/div/ul/li/a")

    FIRST_ARTICLE_TITLE = link_elements[0].find_element(By.XPATH, './/strong').text
    print('FIRST_ARTICLE_TITLE',FIRST_ARTICLE_TITLE)
    
    print('SEC_FIRM_ORDER-?>?', SEC_FIRM_ORDER)
    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName() ,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName() ,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)

    if r and TEST_SEND_YN != 'Y': 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    
    # JSON To List
    # for list in jres['rows']:
    for link_element in link_elements:
        LIST_ARTICLE_URL = link_element.get_attribute('href')
        print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
        LIST_ARTICLE_TITLE = link_element.find_element(By.XPATH, './/strong').text
        print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                # sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                r = GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME =  BOARD_NM ,ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
                if LIST_ARTICLE_TITLE not in sendMessageText:sendMessageText += r # 신규 내용 아래 추가
                if TEST_SEND_YN == 'Y': 
                    print( sendMessageText)
                    continue
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

    # 브라우저 닫기
    driver.quit()
    
    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

def Koreainvestment_selenium_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 13
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 한국투자증권 리서치 모바일
    TARGET_URL_0 =  "https://securities.koreainvestment.com/main/research/research/Search.jsp?schType=report"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += Koreainvestment_selenium_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText

def Koreainvestment_selenium_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")

    # 헤드리스 모드로 설정
    # chrome_options = Options()
    # chrome_options.add_argument("--headless")

    # Chrome 드라이버 초기화
    driver = webdriver.Chrome(options=chrome_options)

    # 웹 페이지 열기
    driver.get(TARGET_URL)

    # 페이지 로딩될때까지 대기
    driver.implicitly_wait(0)

    # # 페이지 로딩을 위해 10초간 대기
    # wait = WebDriverWait(driver, 10) 
    # element = wait.until(EC.element_to_be_clickable((By.ID, 'searchResult'))) 

    # 제목 엘리먼트 찾기
    title_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[1]/div[2]/span[1]')
    # 링크 엘리먼트 찾기
    link_elements = driver.find_elements(By.XPATH, '//*[@id="searchResult"]/div/ul/li/a[2]')

    for title, link in zip(title_elements, link_elements):
        # 제목 출력
        print("제목:", title.text)
        # onClick 프로퍼티값(링크) 출력
        print("링크:", link.get_attribute("onclick"))

    FIRST_ARTICLE_TITLE = title_elements[0].text
    print('FIRST_ARTICLE_TITLE',FIRST_ARTICLE_TITLE)
    
    # 연속키 데이터베이스화 작업
    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)
    if dbResult: # 1
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', GetFirmName() ,'의 ', BOARD_NM )

    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', GetFirmName() ,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)


    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)

    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return ''
    
    nNewArticleCnt = 0
    sendMessageText = ''
    
    # List
    for title, link in zip(title_elements, link_elements):
        LIST_ARTICLE_TITLE = title.text
        print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
        LIST_ARTICLE_URL = link.get_attribute("onclick")
        print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                LIST_ARTICLE_URL = Koreainvestment_GET_LIST_ARTICLE_URL(LIST_ARTICLE_URL)
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


    # # 링크와 제목 출력
    # for link_element in link_elements:
    #     title = link_element.text
    #     link = link_element.get_attribute("href")
    #     print("제목:", title)
    #     print("링크:", link)
    #     print()

    # 브라우저 닫기
    driver.quit()
    
    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText


def Koreainvestment_MAKE_LIST_ARTICLE_URL(filepath, filename, option, datasubmitdate, air_yn, kor_yn, special_yn):
    filename = urllib.parse.quote(filename)
    filepath = filepath
    
    print('filepath =',filepath)
    host_name = "http://research.truefriend.com/streamdocs/openResearch"
    url = ""
    host_name2 = "https://kis-air.com/kor/"
    host_name3 = "https://kis-air.com/us/"

    if filepath.startswith("?") or filepath.startswith("&"):
        filepath = filepath[1:]

    params = filepath.split("&")
    print('params',params)
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
            print('????????')
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

    print('filepath', filepath)
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

    print(url)
    return url

def Koreainvestment_GET_LIST_ARTICLE_URL(string):
    string = string.replace("javascript:prePdfFileView2(", "").replace("&amp;", "&").replace(")", "").replace("(", "").replace("'", "")
    params = string.split(",")
    print(len(params),params)
    print('###############')
    for i in params:
        print(i)
    print('###############')
    
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
    return r

def DAOL_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

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

    # TARGET_URL   = 'https://www.daolsecurities.com/research/article/common.jspx?cmd=list&templet-bypass=true'
    # TARGET_URL     = ''
    
    # KB증권 기업분석
    # TARGET_URL_1 = ''
    # https://www.daolsecurities.com/research/article/common.jspx?rGubun=I01&sctrGubun=I02&web=0
    # https://www.daolsecurities.com/research/article/common.jspx?cmd=list&templet-bypass=true
    # TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6
                        , TARGET_URL_7, TARGET_URL_8, TARGET_URL_9, TARGET_URL_10, TARGET_URL_11,TARGET_URL_12)
    
    
    sendMessageText = ''
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        # URL GET
        try:
            sendMessageText += DAOL_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''

    return sendMessageText
 
# JSON API 타입
def DAOL_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    # URL을 파싱하여 주소와 쿼리 파라미터를 추출
    parsed_url = urlparse.urlparse(TARGET_URL)

    # 쿼리 파라미터를 딕셔너리로 파싱
    query_params = urlparse.parse_qs(parsed_url.query)

    BASE_URL = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path 
    TARGET_URL = BASE_URL + '?cmd=list&templet-bypass=true'
    print('parsed_url:', parsed_url)
    print('BASE_URL:', BASE_URL)
    print('TARGET_URL:',TARGET_URL)
    # 파라미터 출력
    print("rGubun:", query_params.get('rGubun'))
    print("sctrGubun:", query_params.get('sctrGubun'))
    print("web:", query_params.get('web'))

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
    if response.status_code == 200:
        print("요청이 성공했습니다.")
        # print("응답 내용:", response.text)
    else:
        print("요청이 실패했습니다.")
        print("상태 코드:", response.status_code)
    
    
    # print('=' *40)
    # print('======>',soupList[FIRST_ARTICLE_INDEX])
    # print('======>',soupList[FIRST_ARTICLE_INDEX]['title'])
    # print('======>',soupList[FIRST_ARTICLE_INDEX].attrs['href'])
    # print('=' *40)
    

    FIRST_ARTICLE_URL = ''
    FIRST_ARTICLE_TITLE = ''

    try:
        ARTICLE_BOARD_NAME  =  BOARD_NM 
        FIRST_ARTICLE_TITLE = soupList[FIRST_ARTICLE_INDEX]['title']
        FIRST_ARTICLE_URL   = soupList[FIRST_ARTICLE_INDEX].attrs['href']

    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''



    # 연속키 데이터 저장 여부 확인 구간
    dbResult = DB_SelNxtKey(SEC_FIRM_ORDER = SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER = ARTICLE_BOARD_ORDER)


    if dbResult: # 1
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
        # 연속키가 존재하는 경우
        print('데이터베이스에 연속키가 존재합니다. ', FIRM_NM,'의 ', BOARD_NM )
        if NXT_KEY.isspace() or NXT_KEY == '':
            # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
            print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 공백입니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.')
            print('##########확인용',FIRST_ARTICLE_TITLE)
            DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    else: # 0
        # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
        print('데이터베이스에 ', FIRM_NM,'의 ', BOARD_NM ,'게시판 연속키는 존재하지 않습니다.\n', '첫번째 게시물을 연속키로 지정하고 메시지는 전송하지 않습니다.\n\n')
        NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)
    
    if not soupList: 
        print(FIRM_NM,'의 ', BOARD_NM ,'게시판 게시글이 존재하지 않습니다..\n')
        

    # 연속키 체크
    r = isNxtKey(FIRST_ARTICLE_TITLE)
    if SEND_YN == 'Y' : r = ''
    if r: 
        print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****\n\n')
        return '' 
    
    print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    print('연속URL:', NXT_KEY) # 주소
    print('############\n\n')

    # # 연속키있으나, 게시판에서 삭제된 경우 : 현재의 첫 게시물로 연속키 갱신
    # # 중복 발송 방지
    # if NXT_KEY not in str(soupList):
    #     print('기존 연속키:', NXT_KEY, '가 존재하지 않습니다.')
    #     print('첫번째 게시물 연속키를 저장합니다 :', FIRST_ARTICLE_TITLE)
    #     DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    #     return ''

    nNewArticleCnt = 0
    sendMessageText = ''
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
    
        print('LIST_ARTICLE_TITLE='+LIST_ARTICLE_TITLE)
        print('NXT_KEY='+NXT_KEY)
        if ( NXT_KEY not in LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
            nNewArticleCnt += 1 # 새로운 게시글 수
            if len(sendMessageText) < 3500:
                ATTACH_URL = LIST_ARTICLE_URL
                DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
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
        if SEND_YN == 'N':
            print('임시 발송 중단 회원사 입니다. => ', FIRM_NM, 'SEC_FIRM_ORDER :',SEC_FIRM_ORDER)
            return ''
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
        
        print(listIsu)
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

    print('sendType ', sendType)
    print('sendMessageText ',sendMessageText)

    # if sendType == 'Y' or len(sendMessageText) > 0:
    if len(sendMessageText) > 0:
        print("sendAddText() (실제 발송요청)\n", sendMessageText)
        sendText(sendMessageText)
        sendMessageText = ''

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
        sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ARTICLE_URL + ")"  + "\n" 
    else:
        sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ARTICLE_URL + ")" + "        "+ EMOJI_PICK + "[레포트링크]" + "("+ ATTACH_URL + ")"

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
            # print("##",c , "##", ord('가') <= ord(c) <= ord('힣') )
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

    if os.path.exists(ATTACH_FILE_NAME):
        print(f"파일 '{ATTACH_FILE_NAME}'이(가) 이미 존재합니다. 다운로드를 건너뜁니다.")
        return None
    
    with open(ATTACH_FILE_NAME, "wb")as file:  # open in binary mode
        response = get(URL, verify=False)     # get request
        file.write(response.content) # write to file

            
    r = googledrive.upload(str(ATTACH_FILE_NAME))
    print('********************')
    print(f'main URL {r}')
    return r

# wget을 이용하여 파일 다운로드 => 추후 다 변경할수도?
def DownloadFile_wget(URL, FILE_NAME):
    global ATTACH_FILE_NAME
    print("DownloadFile_wget()",URL, FILE_NAME)
    # 로직 사유 : 레포트 첨부파일명에 한글이 포함된 경우 URL처리가 되어 있지 않음
    CONVERT_URL = URL 
    for c in URL: # URL내 한글이 있는 경우 인코딩 처리(URL에 파일명을 이용하여 조합함)
        # 코드셋 기준 파이썬:UTF-8 . 교보증권:EUC-KR
        # 1. 주소에서 한글 문자를 판별
        # 2. 해당 문자를 EUC-KR로 변환후 URL 인코딩
        # print("##",c , "##", ord('가') <= ord(c) <= ord('힣') )
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

    if os.path.exists(ATTACH_FILE_NAME):
        print(f"파일 '{ATTACH_FILE_NAME}'이(가) 이미 존재합니다. 다운로드를 건너뜁니다.")
        return None

    wget.download(url=URL, out=ATTACH_FILE_NAME)
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
    sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ARTICLE_URL + ")"  + "\n" 

    return sendMessageText

# 실제 전송할 메시지 작성 
# 유형   : Markdown
# Paran  : ARTICLE_TITLE -> 레포트 제목  , ATTACH_URL -> 레포트 URL(PDF)
def GetSendMessageTextMarkdown(ARTICLE_TITLE , ATTACH_URL):
    
    sendMessageText = ''

    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ATTACH_URL + ")"  + "\n" 

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

def MySQL_Open_Connect():
    global conn
    global cursor
    
    # MySQL
    url = urlparse.urlparse(ORACLECLOUD_MYSQL_DATABASE_URL)
    try:
        conn = pymysql.connect(host=url.hostname, user=url.username, password=url.password, charset='utf8', db=url.path.replace('/', ''), cursorclass=pymysql.cursors.DictCursor, autocommit=True)
        # 연결 객체가 반환되면 연결 성공
        # print("MySQL 데이터베이스에 연결되었습니다.")
    except Exception as e:
        # 예외가 발생한 경우 오류 메시지 출력
        print("MySQL 데이터베이스 연결 실패:", e)
        return
    cursor = conn.cursor()
    return cursor

def DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
    global FIRM_NM
    global BOARD_NM
    global BOARD_URL
    global NXT_KEY
    global NXT_KEY_BF
    global TEST_SEND_YN
    global NXT_KEY_ARTICLE_TITLE
    global SEND_YN
    global SEND_TIME_TERM
    global TODAY_SEND_YN
    global conn
    global cursor

    cursor = MySQL_Open_Connect()
    dbQuery  = " SELECT FIRM_NM, BOARD_NM, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, BOARD_URL, NXT_KEY, NXT_KEY_BF, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM NXT_KEY		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s "
    dbResult = cursor.execute(dbQuery, (SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER))
    rows = cursor.fetchall()
    for row in rows:
        print('####DB조회된 연속키####', end='\n')
        print(row)
        FIRM_NM = row['FIRM_NM']
        BOARD_NM = row['BOARD_NM']
        BOARD_URL = row['BOARD_URL']
        NXT_KEY = row['NXT_KEY']
        NXT_KEY_BF = row['NXT_KEY_BF']
        NXT_KEY_ARTICLE_TITLE = row['NXT_KEY_ARTICLE_TITLE']
        SEND_YN = row['SEND_YN']
        SEND_TIME_TERM = int(row['SEND_TIME_TERM'])
        TODAY_SEND_YN = row['TODAY_SEND_YN']

    conn.close()
    return dbResult


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
# 'yyyymmdd'
def GetCurrentDate(*args):

    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    DATE = time_now[:10].strip()
    DATE_SPLIT = DATE.split("-")
    

    pattern = ''
    r = ''
    # r = ['y','m','d','Y','M','D']    
    if not args:
        pattern= ''.join(DATE_SPLIT) 
    else: pattern = args[0]
    # if ['y','m','d','Y','M','D'] not in pattern :  return ''.join(DATE_SPLIT)

    print('pattern->',pattern)
    pattern= pattern.replace('yyyy', DATE_SPLIT[0])
    pattern= pattern.replace('YYYY', DATE_SPLIT[0])
    pattern= pattern.replace('mm', DATE_SPLIT[1])
    pattern= pattern.replace('MM', DATE_SPLIT[1])
    pattern= pattern.replace('dd', DATE_SPLIT[2])
    pattern= pattern.replace('DD', DATE_SPLIT[2])


    print('최종', pattern)
    return pattern
    
# 한국 시간 (timezone('Asia/Seoul')) 요일 정보를 구합니다.
def GetCurrentDay(*args):
    daylist = ['월', '화', '수', '목', '금', '토', '일']
    
    time_now = str(datetime.datetime.now(timezone('Asia/Seoul')))[:19] # 밀리세컨즈 제거

    DATE = time_now[:10].strip()
    DATE_SPLIT = DATE.split("-")
    return daylist[datetime.date(int(DATE_SPLIT[0]),int(DATE_SPLIT[1]),int(DATE_SPLIT[2])).weekday()]

def GetSecretKey(*args):
    global SECRETS # 시크릿 키
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
    global BASE_PATH
    

    SECRETS = ''
    # current_file_path = os.path.abspath(__file__)

    # __main__ 모듈의 경로를 가져옵니다.
    main_module_path = sys.modules['__main__'].__file__

    # 절대 경로로 변환합니다.
    main_module_path = os.path.abspath(main_module_path)
    
    # 프로젝트 경로로 이동 
    BASE_PATH =os.path.dirname(main_module_path)
    print('BASE_PATH', BASE_PATH)
    if os.path.isfile(os.path.join(BASE_PATH, 'secrets.json')): # 로컬 개발 환경
        with open((os.path.join(BASE_PATH, 'secrets.json'))) as f:
            SECRETS = json.loads(f.read())
    #SECRETS = ''
    #print(os.getcwd())
    #if os.path.isfile(os.path.join(os.getcwd(), 'secrets.json')): # 로컬 개발 환경
    #    with open("secrets.json") as f:
    #        SECRETS = json.loads(f.read())        
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

def test_code():
    sendMessageText = ''
    print("LS_checkNewArticle()=> 새 게시글 정보 확인") # 0
    r = LS_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

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
    
    # print("Sangsanginib_checkNewArticle()=> 새 게시글 정보 확인") # 6
    # r = Sangsanginib_checkNewArticle()
    # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Shinyoung_checkNewArticle()=> 새 게시글 정보 확인") # 7
    r = Shinyoung_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Miraeasset_checkNewArticle()=> 새 게시글 정보 확인") # 8
    r = Miraeasset_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Hmsec_checkNewArticle()=> 새 게시글 정보 확인") # 9
    r = Hmsec_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Kiwoom_checkNewArticle()=> 새 게시글 정보 확인") # 10
    r = Kiwoom_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

    # print("LS_selenium_checkNewArticle()=> 새 게시글 정보 확인") # 11
    # r = LS_selenium_checkNewArticle()
    # if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    print("Koreainvestment_selenium_checkNewArticle()=> 새 게시글 정보 확인") # 12
    r = Koreainvestment_selenium_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

    print("DAOL_checkNewArticle()=> 새 게시글 정보 확인") # 14
    r = DAOL_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

    if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
    else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.

def main():
    global SEC_FIRM_ORDER  # 증권사 순번
    global TEST_SEND_YN
    global SEND_YN

    # 쉘 파라미터 가져오기
    try: strArgs = sys.argv[1]
    except: strArgs = ''

    # 사용자의 홈 디렉토리 가져오기
    HOME_PATH = os.path.expanduser("~")

    # log 디렉토리 경로
    LOG_PATH = os.path.join(HOME_PATH, "log")

    # log 디렉토리가 존재하지 않으면 생성
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
        print("LOG_PATH 디렉토리 생성됨:", LOG_PATH)
    else:
        print("LOG_PATH 디렉토리 이미 존재함:", LOG_PATH)

    # log 디렉토리 경로
    LOG_PATH = os.path.join(LOG_PATH, GetCurrentDate('YYYYMMDD'))

    # daily log 디렉토리가 존재하지 않으면 생성
    if not os.path.exists(LOG_PATH):
        os.makedirs(LOG_PATH)
        print("daily LOG_PATH 디렉토리 생성됨:", LOG_PATH)
    else:
        print("daily LOG_PATH 디렉토리 이미 존재함:", LOG_PATH)

    
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
    logging.basicConfig(filename=LOG_FULLFILENAME, level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    # print("LOG_FULLFILENAME",LOG_FULLFILENAME)
    # logging.debug('이것은 디버그 메시지입니다.')
    
    TEST_SEND_YN = ''
    GetSecretKey()

    print(GetCurrentDate('YYYYMMDD'),GetCurrentDay())
    
    if  strArgs : 
        TEST_SEND_YN = ''
        SEND_YN = 'Y'
        sendMessageText = ''

        # googledrive.upload("/home/ubuntu/test/telegram-stock-info-noti-bot/test.pdf")

        print("DAOL_checkNewArticle()=> 새 게시글 정보 확인") # 14
        r = DAOL_checkNewArticle()
        if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r

        if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
        else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.
        return
        test_code()

        # googledrive.upload(str(strArgs))
        print('test')
        return 

    TEST_SEND_YN = ''

    #print(GetCurrentDate('YYYY/HH/MM') , GetCurrentTime())
    TimeHourMin = int(GetCurrentTime('HHMM'))
    TimeHour = int(GetCurrentTime('HH'))
    
    # print("fnguideTodayReport_checkNewArticle()=> 새 게시글 정보 확인") # 123
    # fnguideTodayReport_checkNewArticle()

    sendMessageText = ''
    
    # check functions 리스트
    check_functions = [
        LS_checkNewArticle,
        ShinHanInvest_checkNewArticle,
        NHQV_checkNewArticle,
        HANA_checkNewArticle,
        KB_checkNewArticle,
        Samsung_checkNewArticle,
        # Sangsanginib_checkNewArticle, # 주석 처리된 부분
        Shinyoung_checkNewArticle,
        Miraeasset_checkNewArticle,
        Hmsec_checkNewArticle,
        Kiwoom_checkNewArticle,
        # LS_selenium_checkNewArticle, # 주석 처리된 부분
        Koreainvestment_selenium_checkNewArticle,
        DAOL_checkNewArticle
    ]

    for check_function in check_functions:
        print(f"{check_function.__name__} => 새 게시글 정보 확인")
        r = check_function()
        if len(r) > 0:
            sendMessageText += GetSendMessageTitle() + r
    
    if len(sendMessageText) > 0:
        sendAddText(sendMessageText, 'Y')
    else:
        sendAddText('', 'Y')

if __name__ == "__main__":
    main()