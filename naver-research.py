# -*- coding:utf-8 -*- 
import sys
import requests
import json
import os
import asyncio
from bs4 import BeautifulSoup
import urllib.request

from utils.telegram_util import sendMarkDownText
from utils.json_util import save_data_list_to_local_json, get_unsent_main_ch_data_to_local_json, update_main_ch_send_yn_to_y, filter_news_by_save_time

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
    
    requests.packages.urllib3.disable_warnings()

    # 파일 크기 관리 (오래된 데이터 삭제)
    if os.path.exists(JSON_FILE_NAME):
        filter_news_by_save_time(JSON_FILE_NAME)

    # 네이버 증권 리서치 기업
    TARGET_URL_0 = 'https://m.stock.naver.com/front-api/research/list?category=company&pageSize=1000'
    # 네이버 증권 리서치 산업
    TARGET_URL_1 = 'https://m.stock.naver.com/front-api/research/list?category=industry&pageSize=1000'
    
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):

        request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(request)
        rescode = response.getcode()

        if rescode != 200 :return print("네이버 레포트 접속이 원활하지 않습니다 ")

        try: 
            content = response.read().decode('utf-8')
            jres = json.loads(content)
        except Exception as e: 
            print(f"JSON 파싱 에러: {e}")
            return True
        
        jres = jres['result']

        items_to_save = []
        for research in jres:
            LIST_ARTICLE_URL = NAVER_Report_parseURL(research['endUrl'])
            LIST_ARTICLE_TITLE = research['title']
            
            if ARTICLE_BOARD_ORDER == 0:
                if research.get('itemName') and research['itemName']+":" not in LIST_ARTICLE_TITLE: 
                    LIST_ARTICLE_TITLE = research['itemName'] + ": " + LIST_ARTICLE_TITLE  # 기업분석
            else:
                if research.get('category') and research['category']+":" not in LIST_ARTICLE_TITLE: 
                    LIST_ARTICLE_TITLE = research['category'] + ": " + LIST_ARTICLE_TITLE  # 산업분석

            items_to_save.append({
                "sec_firm_order": SEC_FIRM_ORDER,
                "article_board_order": ARTICLE_BOARD_ORDER,
                "firm_nm": research['brokerName'],
                "attach_url": LIST_ARTICLE_URL,
                "article_title": LIST_ARTICLE_TITLE
            })

        # 벌크 저장 및 신규 메시지 수신
        new_messages = save_data_list_to_local_json(JSON_FILE_NAME, items_to_save)
        
        if not new_messages:
            print(f'Board {ARTICLE_BOARD_ORDER}: 최신 게시글이 채널에 발송 되어 있습니다.')
            continue

        sendMessageText = ''
        brokerName = None
        
        # 신규 메시지 발송 처리
        # 주의: save_data_list_to_local_json은 items_to_save의 역순(최신순)일 가능성이 높음.
        # jres가 최신순이라면 그대로 처리해도 무방.
        
        # 원본 jres의 brokerName 정보를 가져오기 위해 index 사용 필요하지만,
        # save_data_list_to_local_json에서 이미 포맷팅된 메시지를 반환함.
        # format_message 내부에서 firm_nm 처리를 하므로 여기서는 3000자 제한만 체크.
        
        for msg in new_messages:
            if len(sendMessageText) + len(msg) >= 3000:
                await sendMarkDownText(token=token,
                    chat_id=TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM,
                    sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText)
                sendMessageText = msg
            else:
                sendMessageText += msg

        if sendMessageText:
            await sendMarkDownText(token=token,
                chat_id=TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM,
                sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText)


def NAVER_Report_parseURL(LIST_ARTICLE_URL):
    strUrl = ''
    try:
        request = urllib.request.Request(
            LIST_ARTICLE_URL,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        )
        
        # 검색 요청 및 응답 처리
        response = urllib.request.urlopen(request, timeout=10)
        html = response.read()

        try:
            # UTF-8 디코딩
            html_decoded = html.decode("utf-8")
        except UnicodeDecodeError:
            html_decoded = html.decode("utf-8", errors="replace")

        # HTML 파싱
        soup = BeautifulSoup(html_decoded, "html.parser")

        # 방법 1: 텍스트로 "원문 보기" 버튼 찾기
        a_tag = soup.find("a", string="원문 보기")
        
        if not a_tag:
            a_tag = soup.find("a", string=lambda text: text and "원문 보기" in text)
        
        if not a_tag:
            a_tags = soup.find_all("a")
            for tag in a_tags:
                if tag.get_text(strip=True) == "원문 보기":
                    a_tag = tag
                    break
        
        if not a_tag:
            a_tags = soup.find_all("a")
            for tag in a_tags:
                if "원문 보기" in tag.get_text(strip=True):
                    a_tag = tag
                    break
        
        if a_tag and "href" in a_tag.attrs:
            strUrl = f"https://m.stock.naver.com{a_tag['href']}"
        else:
            print(f"원문 보기 링크를 찾을 수 없습니다: {LIST_ARTICLE_URL}")
    except Exception as e:
        print(f"URL 파싱 에러 ({LIST_ARTICLE_URL}): {e}")

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
        else: msgFirmName += "리서치]"
    
    SendMessageTitle += "\n\n" + " ●"+  msgFirmName + "\n" 
    
    return SendMessageTitle

async def main():
    try: strArgs = sys.argv[1]
    except: strArgs = ''

    if  strArgs : 
        print('test mode')
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
