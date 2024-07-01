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
   
def bondweb_selenium_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 110
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 본드웹 리서치 모바일
    TARGET_URL_0 =  "https://www.bondweb.co.kr/_research/01_latest_list.asp?keyword=&page=1&ca=2"
    
    TARGET_URL_TUPLE = (TARGET_URL_0, )#TARGET_URL_1, TARGET_URL_2, TARGET_URL_3, TARGET_URL_4, TARGET_URL_5, TARGET_URL_6, TARGET_URL_7, TARGET_URL_8)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += bondweb_selenium_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendAddText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ''
                
    return sendMessageText

def bondweb_selenium_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")


    # Chrome 드라이버 초기화
    driver = webdriver.Chrome(options=chrome_options)

    # 웹 페이지 열기
    driver.get(TARGET_URL)

    # 페이지 로딩될때까지 대기
    driver.implicitly_wait(0)

    # # 페이지 로딩을 위해 10초간 대기
    # wait = WebDriverWait(driver, 10) 
    # element = wait.until(EC.element_to_be_clickable((By.ID, 'searchResult'))) 
    # test_ele = driver.find_elements(By.XPATH , '/html/body/table/tbody/tr[2]/td[2]/table/tbody/tr[2]/td/table[2]/tbody/tr')
    # print(test_ele)
    # for i in test_ele:
    #     print(i)
    # return
    # 제목 엘리먼트 찾기
    title_elements = driver.find_elements(By.XPATH, '/html/body/table/tbody/tr[2]/td[2]/table/tbody/tr[2]/td/table[2]/tbody/tr/td[3]/a')
    # 링크 엘리먼트 찾기
    link_elements = driver.find_elements(By.XPATH, '/html/body/table/tbody/tr[2]/td[2]/table/tbody/tr[2]/td/table[2]/tbody/tr/td[2]/a')
    for i in link_elements:
        print(i[0], i[1], i[2])

    print(len(title_elements), len(link_elements))
    for title, link in zip(title_elements, link_elements):
        # 제목 출력
        print("제목:", title.text)
        # r = ''
        # if link.get_attribute("href"): r = "https://www.bondweb.co.kr/_research/"+ link.get_attribute("href")
        # else: r = ''

        print("링크:", link.get_attribute("href"))

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
                LIST_ARTICLE_URL = bondweb_GET_LIST_ARTICLE_URL(LIST_ARTICLE_URL)
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



def bondweb_MAKE_LIST_ARTICLE_URL(filepath, filename, option, datasubmitdate, air_yn, kor_yn, special_yn):
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

def bondweb_GET_LIST_ARTICLE_URL(string):
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
    r = bondweb_MAKE_LIST_ARTICLE_URL(category, filename, option, datasubmitdate, air_yn, kor_yn, special_yn)
    return r
 
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

def  DB_SelNxtKey(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
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

def DB_UpdNxtKeyNew(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER, NXT_KEY_BF, FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE):
    global NXT_KEY
    global TEST_SEND_YN
    cursor = MySQL_Open_Connect()
    dbQuery = "UPDATE NXT_KEY SET NXT_KEY_BF = %s,NXT_KEY = %s , NXT_KEY_ARTICLE_TITLE = %s WHERE 1=1 AND  SEC_FIRM_ORDER = %s   AND ARTICLE_BOARD_ORDER = %s;"
    dbResult = cursor.execute(dbQuery, (NXT_KEY_BF, FIRST_NXT_KEY, NXT_KEY_ARTICLE_TITLE, SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER ))
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
    
    print("bondweb_selenium_checkNewArticle()=> 새 게시글 정보 확인") # 50
    r = bondweb_selenium_checkNewArticle()
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

    
    print("bondweb_selenium_checkNewArticle()=> 새 게시글 정보 확인") # 50
    r = bondweb_selenium_checkNewArticle()
    if len(r) > 0 : sendMessageText += GetSendMessageTitle() + r


    if len(sendMessageText) > 0: sendAddText(sendMessageText, 'Y') # 쌓인 메세지를 무조건 보냅니다.
    else:                        sendAddText('', 'Y') # 쌓인 메세지를 무조건 보냅니다.

if __name__ == "__main__":
	main()
