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
import re
import asyncio
import pymysql
import pymysql.cursors
import urllib.request
import json
import urllib.parse as urlparse
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from typing import List
from bs4 import BeautifulSoup

from package import googledrive
from package.common import *
# from package import herokuDB

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
CLEARDB_DATABASE_URL                                = ""
ORACLECLOUD_MYSQL_DATABASE_URL                      = ""
TELEGRAM_BOT_INFO                                   = ""
TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET              = ""
TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET             = ""
TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS                 = ""
TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS                  = ""
TELEGRAM_CHANNEL_ID_ITOOZA                          = ""
TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT                    = ""
TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM              = ""
TELEGRAM_CHANNEL_ID_REPORT_ALARM                    = ""
TELEGRAM_CHANNEL_ID_TEST                            = ""
TELEGRAM_USER_ID_DEV                                = ""
IS_DEV                                              = ""
SECRETS = ""

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

def NAVER_52weekPrice_check():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 0
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()


    # 네이버 증권 52주 신고가 코스피
    TARGET_URL_0 = 'https://m.stock.naver.com/api/stocks/high52week/KOSPI?page=1&pageSize=100'
    # 네이버 증권 52주 신고가 코스닥
    TARGET_URL_1 = 'https://m.stock.naver.com/api/stocks/high52week/KOSDAQ?page=1&pageSize=100'
    # 네이버 증권 52주 신저가 코스피
    TARGET_URL_2 = 'https://m.stock.naver.com/api/stocks/low52week/KOSPI?page=1&pageSize=100'
    # 네이버 증권 52주 신저가 코스닥
    TARGET_URL_3 = 'https://m.stock.naver.com/api/stocks/low52week/KOSDAQ?page=1&pageSize=100'
        
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1,TARGET_URL_2,TARGET_URL_3)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += NAVER_52weekPrice_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
            sendAddText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ''
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''

    return sendMessageText


# JSON API 타입
def NAVER_52weekPrice_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode != 200 :return print("네이버 레포트 접속이 원활하지 않습니다 ")

    try: jres = json.loads(response.read().decode('utf-8'))
    except: return True
    # print(jres['totalCount'])

    total_count = int(jres['totalCount'])
    page_size = int(jres['pageSize'])
    total_pages = (total_count + page_size - 1) // page_size  # 올림 계산
    
    
    print('여기???',total_count,page_size ,  total_pages)

    # URL 파싱
    parsed_url = urllib.parse.urlparse(TARGET_URL)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    sendMessageText = ''
    for page in range(1, total_pages + 1):
        
        query_params['page'] = page
        new_query_string = urlencode(query_params, doseq=True)
        new_url = urlunparse(parsed_url._replace(query=new_query_string))

        request = urllib.request.Request(new_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        if rescode != 200:
            return f"Page {page} 접속이 원활하지 않습니다"

        try:
            jres = json.loads(response.read().decode('utf-8'))
        except: return True
        
        for r in jres['stocks']:
            # print("r['stockName']", r['stockName'] , "int(r['itemCode'])" , int(r['itemCode']) ,  ('스팩' in r['stockName'] and int(r['itemCode']) >= 400000))
            if 'et' in r['stockEndType']  : continue
            if ('스팩' in r['stockName'] and
                int(r['itemCode']) >= 400000): continue # 스팩은 표시 안함
            
            sendMessageText += '{0} ({1}%)      [네이버]({2}) , [fnguide]({3})\n'.format(
                                r['stockName'], r['fluctuationsRatio'] , r['endUrl'], convert_stock_url(r['endUrl']) )
            # print((sendMessageText))
            # return ''
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
            
    if len(sendMessageText) > 0:
        print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
        sendAddText(GetSendMessageTitle() + sendMessageText)
        sendMessageText = ''
    # print(sendMessageText)
    # return sendMessageText
    # return sendMessageText
    # # jres = jres['result']
    # # FIRST_ARTICLE_TITLE = jres[0]['title']
    # # print('FIRST_ARTICLE_TITLE:',FIRST_ARTICLE_TITLE)

    # # 연속키 데이터베이스화 작업
    # # 연속키 데이터 저장 여부 확인 구간
    # dbResult = DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER)
    # if dbResult: # 1
    #     # 연속키가 존재하는 경우
    #     print('데이터베이스에 연속키가 존재합니다. ','(네이버 뉴스 투자정보 리서치)')

    # else: # 0
    #     # 연속키가 존재하지 않는 경우 => 첫번째 게시물 연속키 정보 데이터 베이스 저장
    #     print('데이터베이스에 ', '(네이버 뉴스 투자정보 리서치)')
    #     NXT_KEY = DB_InsNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE)

    # # 연속키 체크
    # r = isNxtKey(FIRST_ARTICLE_TITLE)
    # print('****** 네이버 디버그용 **************')
    # print('TEST_SEND_YN', TEST_SEND_YN)
    # print(r)
    # if TEST_SEND_YN == 'Y' : r = ''
    # print('********************')
    # print(r)

    # if r: 
    #     print('*****최신 게시글이 채널에 발송 되어 있습니다. 연속키 == 첫 게시물****')
    #     return ''
    # else:
    #     print('&&&&&&&&&&&&& ', r)

    # # NaverNews 게시판에 따른 URL 지정
    # if ARTICLE_BOARD_ORDER == 0:category = 'company'
    # else:                      category = 'industry'

    # nNewArticleCnt = 0
    # sendMessageText = ''
    # brokerName = jres[0]['brokerName']
    # # JSON To List
    # for research in jres:
    #     # print('***************************')
    #     print(research)
    #     LIST_ARTICLE_URL = research['endUrl'] 
    #     LIST_ARTICLE_URL = NAVER_Report_parseURL(LIST_ARTICLE_URL)
    #     LIST_ARTICLE_TITLE = research['title']
    #     if ARTICLE_BOARD_ORDER == 0 : LIST_ARTICLE_TITLE = research['itemName'] +": "+ LIST_ARTICLE_TITLE # 기업분석
    #     else:                         LIST_ARTICLE_TITLE = research['category'] +": "+ LIST_ARTICLE_TITLE # 산업분석
    #     # if '하나증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
    #     # if '키움증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
    #     # if '삼성증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
    #     # if '신한투자증권'  in str(research['brokerName']) : continue # 해당 증권사는 이미 발송중이므로 제외
        
    #     '''
    #     {'researchCategory': '종목분석', 'category': '종목분석', 'itemCode': '090430', 
    #     'itemName': '아모레퍼시픽', 'researchId': 65663, 'title': '기다림은 길어지지만 방향성은 분명', 
    #     'brokerName': '한화투자증권', 'writeDate': '2023-06-23', 'readCount': '708', 
    #     'endUrl': 'https://m.stock.naver.com/research/company/65663'}

    #     {'researchCategory': '산업분석', 'category': '기타', 'researchId': 33786, 
    #     'title': '한화 항공/방위산업 Weekly', 'brokerName': '한화투자증권', 'writeDate': '2023-06-23', 
    #     'readCount': '288', 'endUrl': 'https://m.stock.naver.com/research/industry/33786'}
    #     '''
    #     print('NXT_KEY ' , NXT_KEY)
    #     print('LIST_ARTICLE_TITLE ', LIST_ARTICLE_TITLE)
        
    #     if ( NXT_KEY != LIST_ARTICLE_TITLE or NXT_KEY == '' or TEST_SEND_YN == 'Y' ) and SEND_YN == 'Y':
    #         nNewArticleCnt += 1 # 새로운 게시글 수
    #         if len(sendMessageText) < 3000:
    #             # 회사명 출력
    #             if nNewArticleCnt == 1 or brokerName != research['brokerName'] : # 첫 페이지 이거나 다음 회사명이 다를때만 출력
    #                 sendMessageText += "\n"+ "●"+research['brokerName'] + "\n"
    #                 brokerName = research['brokerName'] # 회사명 키 변경
    #             # 종목 & 산업 출력
    #             # if ARTICLE_BOARD_ORDER == 0 : sendMessageText += "●"+research['itemName'] + "\n" # 기업분석
    #             # else:                         sendMessageText += "●"+research['category'] + "\n" # 산업분석
    #             # 레포트 제목 출력
    #             # sendMessageText += research['title'] + "\n"
    #             # 레포트 URL 출력
    #             # sendMessageText += NAVER_Report_parseURL(LIST_ARTICLE_URL) + "\n"+ "\n"
    #             # if ARTICLE_BOARD_ORDER == 0 : sendMessageText += "●"+research['itemName'] + "\n" # 기업분석
    #             # else:                         sendMessageText += "●"+research['category'] + "\n" # 산업분석
    #             sendMessageText += GetSendMessageText(INDEX = nNewArticleCnt ,ARTICLE_BOARD_NAME = '',ARTICLE_TITLE = LIST_ARTICLE_TITLE, ARTICLE_URL = LIST_ARTICLE_URL)
    #         else:
    #             print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
    #             print(sendMessageText)
    #             sendText(GetSendMessageTitle() + sendMessageText)
    #             nNewArticleCnt = 0
    #             sendMessageText = ''

    #     elif SEND_YN == 'N':
    #         print('###점검중 확인요망###')
    #     else:
    #         DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    #         if nNewArticleCnt == 0  or len(sendMessageText) == 0:
    #             print('최신 게시글이 채널에 발송 되어 있습니다.')
    #             return
    #         else: break
                
    # print('**************')
    # print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    # # 뉴스, 네이버(뉴스, 레포트)의 경우 분리하여 발송
    # if nNewArticleCnt > 0  or len(sendMessageText) > 0:
    #     print(sendMessageText)
    #     sendText(GetSendMessageTitle() + sendMessageText)
    #     sendMessageText = ''

    # DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    # return sendMessageText

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

def convert_stock_url(naver_url):
    # 네이버 주식 URL에서 주식 코드를 추출
    stock_code = naver_url.split('/')[-1]
    
    # FN가이드 주식 URL 생성
    fnguide_url = f"https://m.comp.fnguide.com/m2/company_01.asp?pGB=1&gicode=A{stock_code}"
    
    return fnguide_url

async def sendAlertMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True)

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

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
    
    # if SEC_FIRM_ORDER == 999:
    #     msgFirmName = "매매동향"
    # elif SEC_FIRM_ORDER == 998:
    #     msgFirmName = "네이버 - "
    #     if  ARTICLE_BOARD_ORDER == 0 : msgFirmName += "실시간 뉴스 속보"
    #     else: msgFirmName += "가장 많이 본 뉴스"
    # elif SEC_FIRM_ORDER == 997: msgFirmName = "아이투자 - 랭킹스탁"
    # elif SEC_FIRM_ORDER == 996: msgFirmName = "연합인포맥스 - 공매도 잔고 상위"
    # elif SEC_FIRM_ORDER == 995: msgFirmName = "조선비즈 - C-Biz봇"
    # elif SEC_FIRM_ORDER == 994: msgFirmName = "매경 증권 52주 신고저가 알림"
    # elif SEC_FIRM_ORDER == 900: 
    #     msgFirmName = "[네이버 증권 "
    #     if ARTICLE_BOARD_ORDER == 0 : msgFirmName += "기업 리서치](https://m.stock.naver.com/investment/research/company)"
    #     elif ARTICLE_BOARD_ORDER == 1:  msgFirmName += "산업 리서치](https://m.stock.naver.com/investment/research/industry)"
    #     else: print(msgFirmName)
    # elif SEC_FIRM_ORDER == 123: msgFirmName = "[오늘의 레포트](https://comp.fnguide.com/SVO/WooriRenewal/Report.asp)"
    # else: # 증권사
    #     msgFirmName =  FIRM_NM 
    # msgFirmName
    # # SendMessageTitle += "\n" + EMOJI_FIRE + msgFirmName + EMOJI_FIRE + "\n" 
    # SendMessageTitle += "\n\n" + " ●"+  msgFirmName + "\n" 

    if ARTICLE_BOARD_ORDER == 0: SendMessageTitle = "\n\n" + " ●"+  '코스피 52주 신고가' + "\n"
    if ARTICLE_BOARD_ORDER == 1: SendMessageTitle = "\n\n" + " ●"+  '코스닥 52주 신고가' + "\n"
    if ARTICLE_BOARD_ORDER == 2: SendMessageTitle = "\n\n" + " ●"+  '코스피 52주 신저가' + "\n"
    if ARTICLE_BOARD_ORDER == 3: SendMessageTitle = "\n\n" + " ●"+  '코스닥 52주 신저가' + "\n"

    return SendMessageTitle

def GetSendChatId():
    SendMessageChatId = 0
    return TELEGRAM_CHANNEL_ID_REPORT_ALARM

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

def GetSecretKey(*args):
    global CLEARDB_DATABASE_URL
    global ORACLECLOUD_MYSQL_DATABASE_URL
    global TELEGRAM_BOT_INFO
    global TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET
    global TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET
    global TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS
    global TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS
    global TELEGRAM_CHANNEL_ID_ITOOZA
    global TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT
    global TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM
    global TELEGRAM_CHANNEL_ID_REPORT_ALARM
    global TELEGRAM_CHANNEL_ID_TODAY_REPORT
    global TELEGRAM_CHANNEL_ID_TEST
    global TELEGRAM_USER_ID_DEV
    global IS_DEV


    SECRETS = ''
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
        CLEARDB_DATABASE_URL                        =   SECRETS['CLEARDB_DATABASE_URL']
        ORACLECLOUD_MYSQL_DATABASE_URL              =   SECRETS['ORACLECLOUD_MYSQL_DATABASE_URL']
        TELEGRAM_BOT_INFO                           =   SECRETS['TELEGRAM_BOT_INFO']
        TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET      =   SECRETS['TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET']
        TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET     =   SECRETS['TELEGRAM_BOT_TOKEN_MAGIC_FORMULA_SECRET']
        TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS         =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS']
        TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS          =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS']
        TELEGRAM_CHANNEL_ID_ITOOZA                  =   SECRETS['TELEGRAM_CHANNEL_ID_ITOOZA']
        TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT            =   SECRETS['TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT']
        TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM      =   SECRETS['TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM']
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
    global SECRETS # 시크릿 키
    global INTERVAL_TIME # 새로고침 주기 - 파일
    global TEST_SEND_YN

    GetSecretKey()

    print(GetCurrentDate('YYYYMMDD'),GetCurrentDay())
    
    try: strArgs = sys.argv[1]
    except: strArgs = ''

    if  strArgs : 
        TEST_SEND_YN = 'Y'
        sendMessageText = ''

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


    sendMessageText = ''
    print("NAVER_52weekPrice_check()=> 새 게시글 정보 확인") # 0
    r = NAVER_52weekPrice_check()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r
    
    sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.

if __name__ == "__main__":
	main()