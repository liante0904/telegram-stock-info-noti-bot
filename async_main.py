import os
import sys
import datetime
import logging
from pytz import timezone
import telegram
import requests
import time
import json
import re
import asyncio
import wget
import urllib.parse as urlparse
import urllib.request
import base64
from typing import List
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from package import googledrive
from package.firm_info import *
from package.json_util import save_data_to_local_json  # import the function from json_util
from package.dateutil import GetCurrentDate, GetCurrentDay, GetCurrentTime
from package.fileutil import DownloadFile, DownloadFile_wget

# selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from requests import get  # to make GET request

load_dotenv()
TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')

# 타이틀 생성 
# : 게시판 이름 삭제
def GetSendMessageTitle(): 
    
    firm_info = get_firm_info(sec_firm_order = SEC_FIRM_ORDER, article_board_order = ARTICLE_BOARD_ORDER)
    # SendMessageTitle += "\n" + EMOJI_FIRE + msgFirmName + EMOJI_FIRE + "\n" 
    SendMessageTitle = "\n\n" + " ●"+  firm_info['firm_name'] + "\n" 
    
    return SendMessageTitle

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    print('===============sendMessage===============')
    global CHAT_ID
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")


def Sangsanginib_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER
    global firm_info
    

    SEC_FIRM_ORDER = 6
    ARTICLE_BOARD_ORDER = 0

    # requests.packages.urllib3.disable_warnings()

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
        firm_info = get_firm_info(sec_firm_order = SEC_FIRM_ORDER, article_board_order = ARTICLE_BOARD_ORDER)
        try:
            sendMessageText += Sangsanginib_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
            time.sleep(1)
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                asyncio.run(sendMessage(GetSendMessageTitle() + sendMessageText))
                sendMessageText = ''
                
    return sendMessageText

def Sangsanginib_parse(ARTICLE_BOARD_ORDER, TARGET_URL):

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
        webpage = requests.post(TARGET_URL, headers=headers, data=data, timeout=5)
        # print(webpage.text)
        jres = json.loads(webpage.text)
        # print(jres)
    except requests.exceptions.Timeout:
        print("요청이 타임아웃되었습니다.")
        # return False
    except requests.exceptions.RequestException as e:
        print(f"요청 중 오류 발생: {e}")
        # return False
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 오류: {e}")
        # return False
    

    # 연속키 데이터베이스화 작업
    
    firm_info = get_firm_info(sec_firm_order = SEC_FIRM_ORDER, article_board_order = ARTICLE_BOARD_ORDER)

    
    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for list in jres[0]['getNoticeList']:
        # {'f0': '등록일', 'f1': '제목', 'f2': '구분', 'f3': '파일명', 'f4': '본문', 'f5': '작성자', 'f6': '조회수'}
        # print('list***************** \n',list)
        # 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb=CR&attaFile=1650493541463.pdf&makeDt=2022.04.21'
        # LIST_ARTICLE_URL = 'https://bbn.kiwoom.com/research/SPdfFileView?rMenuGb={}&attaFile={}&makeDt={}' 
        # print('cmsCd[ARTICLE_BOARD_ORDER]',cmsCd[ARTICLE_BOARD_ORDER])
        # print('NT_NO=',list['NT_NO'], 'CMS_CD=',cmsCd[ARTICLE_BOARD_ORDER])

        LIST_ARTICLE_URL = Sangsanginib_detail(NT_NO=list['NT_NO'], CMS_CD=cmsCd[ARTICLE_BOARD_ORDER])
        LIST_ARTICLE_TITLE = list['TITLE']

        sendMessageText += save_data_to_local_json(
            filename='./json/data_main_daily_send.json',
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm=firm_info['firm_name'],
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        if sendMessageText:
            nNewArticleCnt += 1 # 새로운 게시글 수
            print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
            print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
            DownloadFile(URL = LIST_ARTICLE_URL, FILE_NAME = LIST_ARTICLE_TITLE +'.pdf')
        if len(sendMessageText) >= 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            print(sendMessageText)
            asyncio.run(sendMessage(GetSendMessageTitle() + sendMessageText))
            sendMessageText = ''
            nNewArticleCnt = 0

    if nNewArticleCnt == 0  or len(sendMessageText) == 0:
        print('최신 게시글이 채널에 발송 되어 있습니다.')
        return
                
    
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)


    return sendMessageText

def Sangsanginib_detail(NT_NO, CMS_CD):
    time.sleep(1)
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



def main():
    global SEC_FIRM_ORDER  # 증권사 순번
    global TEST_SEND_YN
    global SEND_YN


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
    
    

    
    sendMessageText = ''
    
    # check functions 리스트
    check_functions = [
        # LS_checkNewArticle,
        # ShinHanInvest_checkNewArticle,
        # NHQV_checkNewArticle,
        # HANA_checkNewArticle,
        # KB_checkNewArticle,
        # Samsung_checkNewArticle,
        Sangsanginib_checkNewArticle, # 주석 처리된 부분
        # Shinyoung_checkNewArticle,
        # Miraeasset_checkNewArticle,
        # Hmsec_checkNewArticle,
        # Kiwoom_checkNewArticle,
        # Koreainvestment_selenium_checkNewArticle,
        # DAOL_checkNewArticle
    ]

    for check_function in check_functions:
        print(f"{check_function.__name__} => 새 게시글 정보 확인")
        r = check_function()
        if len(r) > 0:
            sendMessageText += GetSendMessageTitle() + r
            if len(sendMessageText) > 3500 : 
                asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
                sendMessageText = ''
    
    if len(sendMessageText) > 0:
        asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
        sendMessageText = ''

if __name__ == "__main__":
    main()