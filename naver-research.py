# -*- coding:utf-8 -*- 
import sys
import requests
import json
import os
import asyncio
from bs4 import BeautifulSoup
import urllib.request

from utils.telegram_util import sendMarkDownText
from utils.json_util import save_data_to_local_json, get_unsent_main_ch_data_to_local_json, update_main_ch_send_yn_to_y # import the function from json_util

############ global 변수 ############


from dotenv import load_dotenv

load_dotenv()  # .env 파일의 환경 변수를 로드합니다

token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM')
TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')

JSON_FILE_NAME = './json/naver_research.json'
############ global 변수 끝 ############

async def NAVER_Report_checkNewArticle():
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

        request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(request)
        rescode = response.getcode()

        if rescode != 200 :return print("네이버 레포트 접속이 원활하지 않습니다 ")

        try: jres = json.loads(response.read().decode('utf-8'))
        except: return True
        
        jres = jres['result']

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
                # sendText(GetSendMessageTitle(SEC_FIRM_ORDER=SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER=ARTICLE_BOARD_ORDER) + sendMessageText)
                await sendMarkDownText(token=token,
                chat_id=TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM,
                sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
                sendMessageText = ''

        if len(sendMessageText) == 0:
            print('최신 게시글이 채널에 발송 되어 있습니다.')
            return

        print(f'len(sendMessageText) {len(sendMessageText)}')
        if sendMessageText:
            print(sendMessageText)
            # sendText(GetSendMessageTitle(SEC_FIRM_ORDER=SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER=ARTICLE_BOARD_ORDER) + sendMessageText)
            await sendMarkDownText(token=token,
            chat_id=TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM,
            sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
            sendMessageText = ''
        else:
            print('최신 게시글이 채널에 발송 되어 있습니다.')


def NAVER_Report_parseURL(LIST_ARTICLE_URL):
    strUrl = ''
    request = urllib.request.Request(
        LIST_ARTICLE_URL,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
    )
    
    # 검색 요청 및 응답 처리
    response = urllib.request.urlopen(request)
    html = response.read()

    try:
        # UTF-8 디코딩
        html_decoded = html.decode("utf-8")
    except UnicodeDecodeError:
        html_decoded = html.decode("utf-8", errors="replace")

    print("페이지 URL:", LIST_ARTICLE_URL)
    
    # HTML 파싱
    soup = BeautifulSoup(html_decoded, "html.parser")

    # 방법 1: 텍스트로 "원문 보기" 버튼 찾기
    a_tag = soup.find("a", string="원문 보기")
    
    # 방법 1이 실패하면 방법 2: 텍스트를 포함하는 a 태그 찾기
    if not a_tag:
        a_tag = soup.find("a", string=lambda text: text and "원문 보기" in text)
    
    # 방법 2도 실패하면 방법 3: a 태그 안의 하위 요소에서 "원문 보기" 텍스트 찾기
    if not a_tag:
        a_tags = soup.find_all("a")
        for tag in a_tags:
            if tag.get_text(strip=True) == "원문 보기":
                a_tag = tag
                break
    
    # 방법 3도 실패하면 방법 4: "원문 보기"를 포함하는 a 태그 찾기
    if not a_tag:
        a_tags = soup.find_all("a")
        for tag in a_tags:
            if "원문 보기" in tag.get_text(strip=True):
                a_tag = tag
                break
    
    # href 값 가져오기
    if a_tag and "href" in a_tag.attrs:
        strUrl = f"https://m.stock.naver.com{a_tag['href']}"
        print("찾은 링크:", strUrl)
    else:
        print("원문 보기 링크를 찾을 수 없습니다.")
        # 디버깅을 위해 모든 a 태그 출력
        print("페이지의 모든 a 태그:")
        a_tags = soup.find_all("a")
        for i, tag in enumerate(a_tags[:10]):  # 처음 10개만 출력
            print(f"{i+1}: {tag.get_text(strip=True)} - {tag.get('href', 'href 없음')}")

    return strUrl


# 타이틀 생성 
# : 게시판 이름 삭제
def GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
    SendMessageTitle = ""
    msgFirmName = ""
    
    if SEC_FIRM_ORDER == 900: 
        msgFirmName = "[네이버 증권 "
        if ARTICLE_BOARD_ORDER == 0 : msgFirmName += "기업 리서치](https://m.stock.naver.com/investment/research/company)"
        elif ARTICLE_BOARD_ORDER == 1:  msgFirmName += "산업 리서치](https://m.stock.naver.com/investment/research/industry)"
        else: print(msgFirmName)
    
    SendMessageTitle += "\n\n" + " ●"+  msgFirmName + "\n" 
    
    return SendMessageTitle

async def main():
    try: strArgs = sys.argv[1]
    except: strArgs = ''

    if  strArgs : 
        print('test')
        return 

    print("NAVER_Report_checkNewArticle()=> 새 게시글 정보 확인") # 900
    await NAVER_Report_checkNewArticle()

    lists = get_unsent_main_ch_data_to_local_json(JSON_FILE_NAME)
    if lists:
        for sendMessageText in lists:
            await sendMarkDownText(token=token,
            chat_id=TELEGRAM_CHANNEL_ID_REPORT_ALARM,
            sendMessageText=sendMessageText)
        update_main_ch_send_yn_to_y(JSON_FILE_NAME)
    
if __name__ == "__main__":
	asyncio.run(main())
