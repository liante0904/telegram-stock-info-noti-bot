# -*- coding:utf-8 -*- 
import sys
import telegram
import requests
import asyncio
from bs4 import BeautifulSoup

from package.json_util import save_data_to_local_json, get_unsent_main_ch_data_to_local_json, update_main_ch_send_yn_to_y # import the function from json_util
# from package.common import *
from package.SecretKey import SecretKey

############공용 상수############
# sleep key
SEC_FIRM_ORDER = 0 # 증권사 순번
ARTICLE_BOARD_ORDER = 0 # 게시판 순번


#################### global 변수 정리 ###################################
#################### global 변수 정리 끝###################################

SECRET_KEY = SecretKey()

JSON_FILE_NAME = './json/hankyungconsen_research.json'

def HankyungConsen_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER = 100

    requests.packages.urllib3.disable_warnings()

    # 하나금융 Daily
    TARGET_URL =  'https://consensus.hankyung.com/analysis/list?search_date=today&search_text=&pagenum=1000'

    sendMessageText = ''
    try:
        sendMessageText += HankyungConsen_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
    except:
        if len(sendMessageText) > 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
            # sendAddText(GetSendMessageTitle() + sendMessageText)
            asyncio.run(sendMessage(sendMessageText))
            sendMessageText = ''
                
    return sendMessageText

def HankyungConsen_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    
    try:
        webpage = requests.get(TARGET_URL, verify=False, headers={'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8','User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'})
    except:
        return True

    # HTML parse
    soup = BeautifulSoup(webpage.content, "html.parser")
    # print(soup)
    soupList = soup.select('#contents > div.table_style01 > table > tbody > tr')
    try:
        FIRST_ARTICLE_TITLE = soup.select('#contents > div.table_style01 > table > tbody > tr:nth-child(1) > td.text_l > a')[0].text
        FIRST_ARTICLE_URL =  'https://consensus.hankyung.com' + soup.select('#contents > div.table_style01 > table > tbody > tr:nth-child(1) > td:nth-child(6) > div > a')[0].attrs['href']
    except:
        FIRST_ARTICLE_URL = ''
        FIRST_ARTICLE_TITLE = ''
    
    # print('게시판 이름:', ARTICLE_BOARD_NAME) # 게시판 종류
    # print('게시글 제목:', FIRST_ARTICLE_TITLE) # 게시글 제목
    # print('게시글URL:', FIRST_ARTICLE_URL) # 주소
    # print('연속URL:', NXT_KEY) # 주소
    print('############')

    nNewArticleCnt = 0
    sendMessageText = ''
    brokerName = soup.select('#contents > div.table_style01 > table > tbody > tr.first > td:nth-child(5)')[0].text
    first_article_processed = False
    # print('brokerName' ,brokerName)
    for list in soupList:
        
        # print('*****************')
        # print(list)
        LIST_ARTICLE_CLASS = list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(2)').text
        LIST_ARTICLE_TITLE = list.select_one('#contents > div.table_style01 > table > tbody > tr > td.text_l > a').text
        LIST_ARTICLE_URL =  'https://consensus.hankyung.com' + list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(6) > div > a').attrs['href']
        LIST_ARTICLE_BROKER_NAME =list.select_one('#contents > div.table_style01 > table > tbody > tr > td:nth-child(5)').text


        

        # Use the imported save_data_to_local_json function with filename parameter
        new_article_message = save_data_to_local_json(
            filename=JSON_FILE_NAME,
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm=LIST_ARTICLE_BROKER_NAME,
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        
        if new_article_message:
            # 회사명 출력
            nNewArticleCnt += 1  # 새로운 게시글 수
            print(LIST_ARTICLE_CLASS)
            print(LIST_ARTICLE_TITLE)
            print(LIST_ARTICLE_URL)
            print('LIST_ARTICLE_BROKER_NAME=',LIST_ARTICLE_BROKER_NAME)
            if not first_article_processed or brokerName != LIST_ARTICLE_BROKER_NAME:
                sendMessageText += "\n\n"+ "●"+ LIST_ARTICLE_BROKER_NAME + "\n"
                brokerName = LIST_ARTICLE_BROKER_NAME # 회사명 키 변경
                first_article_processed = True

            sendMessageText += new_article_message

        if len(sendMessageText) >= 3000:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            print(sendMessageText)
            # sendText(GetSendMessageTitle() + sendMessageText)
            asyncio.run(sendMessage(sendMessageText))
            nNewArticleCnt = 0
            sendMessageText = ''


    if nNewArticleCnt == 0 or len(sendMessageText) == 0:
        print('최신 게시글이 채널에 발송 되어 있습니다.')
        return

    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText) {len(sendMessageText)}')
    if nNewArticleCnt > 0 or len(sendMessageText) > 0:
        print(sendMessageText)
        # sendText(GetSendMessageTitle(SEC_FIRM_ORDER=SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER=ARTICLE_BOARD_ORDER) + sendMessageText)
        asyncio.run(sendMessage(sendMessageText))
        sendMessageText = ''

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = SECRET_KEY.TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

async def sendMessageToMain(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")


def main():
    global SEC_FIRM_ORDER  # 증권사 순번

    # print(GetCurrentDate('YYYYMMDD'),GetCurrentDay())
    
    try: strArgs = sys.argv[1]
    except: strArgs = ''

    
    sendMessageText = ''

    print("HankyungConsen_checkNewArticle()=> 새 게시글 정보 확인") # 12
    sendMessageText = HankyungConsen_checkNewArticle()

    if len(sendMessageText) > 0: asyncio.run(sendMessage(sendMessageText))

    lists = get_unsent_main_ch_data_to_local_json(JSON_FILE_NAME)
    if lists:
        for sendMessageText in lists:
            asyncio.run(sendMessageToMain(sendMessageText))
        update_main_ch_send_yn_to_y(JSON_FILE_NAME)
    
    return True


if __name__ == "__main__":
	main()