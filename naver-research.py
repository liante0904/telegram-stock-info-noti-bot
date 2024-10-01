# -*- coding:utf-8 -*- 
import os
import sys
from pytz import timezone
import telegram
import requests
import datetime
import time
import json
import asyncio
from typing import List
from bs4 import BeautifulSoup
import urllib.request

from package import googledrive
from package.SecretKey import SecretKey
from package.json_util import save_data_to_local_json, get_unsent_main_ch_data_to_local_json, update_main_ch_send_yn_to_y # import the function from json_util

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

############ global 변수 ############
SEC_FIRM_ORDER = 0 # 증권사 순번
ARTICLE_BOARD_ORDER = 0 # 게시판 순번

SECRET_KEY = SecretKey()

JSON_FILE_NAME = './json/naver_research.json'
############ global 변수 끝 ############

def NAVER_Report_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 900
    ARTICLE_BOARD_ORDER = 900

    requests.packages.urllib3.disable_warnings()

    # 네이버 증권 리서치 기업
    TARGET_URL_0 = 'https://m.stock.naver.com/front-api/research/list?category=company'
    # 네이버 증권 리서치 산업
    TARGET_URL_1 = 'https://m.stock.naver.com/front-api/research/list?category=industry'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        NAVER_Report_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
        time.sleep(1)

# JSON API 타입
def NAVER_Report_parse(ARTICLE_BOARD_ORDER, TARGET_URL):

    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode != 200 :return print("네이버 레포트 접속이 원활하지 않습니다 ")

    try: jres = json.loads(response.read().decode('utf-8'))
    except: return True
    
    jres = jres['result']

    nNewArticleCnt = 0
    sendMessageText = ''
    brokerName = jres[0]['brokerName']
    first_article_processed = False

    for research in jres:
        LIST_ARTICLE_URL = NAVER_Report_parseURL(research['endUrl'])
        LIST_ARTICLE_TITLE = research['title']
        if ARTICLE_BOARD_ORDER == 0:
            if research['itemName']+":" not in LIST_ARTICLE_TITLE : 
                LIST_ARTICLE_TITLE = research['itemName'] + ": " + LIST_ARTICLE_TITLE  # 기업분석
        else:
            if research['category']+":" not in LIST_ARTICLE_TITLE : 
                LIST_ARTICLE_TITLE = research['category'] + ": " + LIST_ARTICLE_TITLE  # 산업분석

        # Use the imported save_data_to_local_json function with filename parameter
        new_article_message = save_data_to_local_json(
            filename=JSON_FILE_NAME,
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm=research['brokerName'],
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        
        if new_article_message:
            nNewArticleCnt += 1  # 새로운 게시글 수
            print(LIST_ARTICLE_URL)
            print(LIST_ARTICLE_TITLE)
            
            if not first_article_processed or brokerName != research['brokerName']:
                sendMessageText += "\n" + "●" + research['brokerName'] + "\n"
                brokerName = research['brokerName']  # 회사명 키 변경
                first_article_processed = True

            sendMessageText += new_article_message

        if len(sendMessageText) >= 3000:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            print(sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            nNewArticleCnt = 0
            sendMessageText = ''

    if nNewArticleCnt == 0 or len(sendMessageText) == 0:
        print('최신 게시글이 채널에 발송 되어 있습니다.')
        return

    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText) {len(sendMessageText)}')
    if nNewArticleCnt > 0 or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle(SEC_FIRM_ORDER=SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER=ARTICLE_BOARD_ORDER) + sendMessageText)
        sendMessageText = ''

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

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

async def sendMessageToMain(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")


# 가공없이 텍스트를 발송합니다.
def sendText(sendMessageText): 
    global CHAT_ID

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    return asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

def GetSendChatId():
    SendMessageChatId = 0
    return SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM

# 타이틀 생성 
# : 게시판 이름 삭제
def GetSendMessageTitle(SEC_FIRM_ORDER=SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER=ARTICLE_BOARD_ORDER): 
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
        msgFirmName =  '' 

    # SendMessageTitle += "\n" + EMOJI_FIRE + msgFirmName + EMOJI_FIRE + "\n" 
    SendMessageTitle += "\n\n" + " ●"+  msgFirmName + "\n" 
    
    return SendMessageTitle

def main():

    try: strArgs = sys.argv[1]
    except: strArgs = ''

    if  strArgs : 
        print('test')
        return 

    print("NAVER_Report_checkNewArticle()=> 새 게시글 정보 확인") # 900
    NAVER_Report_checkNewArticle()

    lists = get_unsent_main_ch_data_to_local_json(JSON_FILE_NAME)
    if lists:
        for sendMessageText in lists:
            asyncio.run(sendMessageToMain(sendMessageText))
        update_main_ch_send_yn_to_y(JSON_FILE_NAME)
    
    return True


if __name__ == "__main__":
	main()
