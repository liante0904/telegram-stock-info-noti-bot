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
        # sendText(GetSendMessageTitle() + sendMessageText)
        # sendMessageText = ''

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
        # sendMessageText = ''

    DB_UpdNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, FIRST_ARTICLE_TITLE, FIRST_ARTICLE_TITLE)
    return sendMessageText

async def sendAlertMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True)


async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

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
    dbQuery  = " SELECT FIRM_NM, BOARD_NM, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, BOARD_URL, NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEND_YN, CHANGE_DATE_TIME, TODAY_SEND_YN, TIMESTAMPDIFF(second ,  CHANGE_DATE_TIME, CURRENT_TIMESTAMP) as SEND_TIME_TERM 		FROM nxt_key		WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s "
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
    
    print("ChosunBizBot_checkNewArticle()=> 새 게시글 정보 확인 # 995");  ChosunBizBot_checkNewArticle(); print("NAVERNews_checkNewArticle()=> 새 게시글 정보 확인 # 998"); NAVERNews_checkNewArticle(); return

if __name__ == "__main__":
	main()