# -*- coding:utf-8 -*- 
import sys
import requests
import json
import os
import asyncio
from bs4 import BeautifulSoup
import urllib.request
from loguru import logger

from utils.telegram_util import sendMarkDownText
from utils.json_util import save_data_to_local_json, get_unsent_main_ch_data_to_local_json, update_main_ch_send_yn_to_y
from utils.date_util import GetCurrentDate

from dotenv import load_dotenv

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM')
TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')

JSON_FILE_NAME = './json/naver_research.json'

def setup_logger():
    HOME_PATH = os.path.expanduser("~")
    log_date = GetCurrentDate('YYYYMMDD')
    LOG_PATH = os.path.join(HOME_PATH, "log", log_date)
    os.makedirs(LOG_PATH, exist_ok=True)
    
    log_file = os.path.join(LOG_PATH, f"{log_date}_naver-research.log")
    logger.add(log_file, rotation="00:00", retention="30 days", level="DEBUG", 
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    return LOG_PATH

async def NAVER_Report_checkNewArticle():
    SEC_FIRM_ORDER      = 900
    requests.packages.urllib3.disable_warnings()

    TARGET_URL_0 = 'https://m.stock.naver.com/front-api/research/list?category=company&pageSize=1000'
    TARGET_URL_1 = 'https://m.stock.naver.com/front-api/research/list?category=industry&pageSize=1000'
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1)

    for board_order, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        logger.info(f"Checking Naver Research: {TARGET_URL}")
        try:
            request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(request)
            if response.getcode() != 200:
                logger.error(f"Naver Research Access Failed: {response.getcode()}")
                continue
            
            jres = json.loads(response.read().decode('utf-8'))
            jres = jres.get('result', [])
        except Exception as e:
            logger.exception(f"Error fetching Naver Research: {e}")
            continue

        sendMessageText = ''
        brokerName = jres[0]['brokerName'] if jres else ""
        first_article_processed = False

        for research in jres:
            LIST_ARTICLE_URL = NAVER_Report_parseURL(research['endUrl'])
            LIST_ARTICLE_TITLE = research['title']
            
            if board_order == 0:
                if research['itemName']+":" not in LIST_ARTICLE_TITLE : 
                    LIST_ARTICLE_TITLE = research['itemName'] + ": " + LIST_ARTICLE_TITLE
            else:
                if research['category']+":" not in LIST_ARTICLE_TITLE : 
                    LIST_ARTICLE_TITLE = research['category'] + ": " + LIST_ARTICLE_TITLE

            new_article_message = save_data_to_local_json(
                filename=JSON_FILE_NAME,
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=board_order,
                firm_nm=research['brokerName'],
                attach_url=LIST_ARTICLE_URL,
                article_title=LIST_ARTICLE_TITLE
            )
            
            if new_article_message:
                logger.info(f"New Naver Research Found: {LIST_ARTICLE_TITLE}")
                if not first_article_processed or brokerName != research['brokerName']:
                    sendMessageText += "\n" + "●" + research['brokerName'] + "\n"
                    brokerName = research['brokerName']
                    first_article_processed = True
                sendMessageText += new_article_message

            if len(sendMessageText) >= 3000:
                logger.info("Message limit reached, sending partial update.")
                await sendMarkDownText(token=token,
                                       chat_id=TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM,
                                       sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER, board_order) + sendMessageText)
                sendMessageText = ''

        if sendMessageText:
            await sendMarkDownText(token=token,
                                   chat_id=TELEGRAM_CHANNEL_ID_NAVER_REPORT_ALARM,
                                   sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER, board_order) + sendMessageText)
        else:
            logger.debug(f'Naver Research (Board {board_order}): No new articles to send.')

def NAVER_Report_parseURL(LIST_ARTICLE_URL):
    strUrl = ''
    try:
        request = urllib.request.Request(
            LIST_ARTICLE_URL,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}
        )
        response = urllib.request.urlopen(request)
        html = response.read()
        try:
            html_decoded = html.decode("utf-8")
        except UnicodeDecodeError:
            html_decoded = html.decode("utf-8", errors="replace")

        soup = BeautifulSoup(html_decoded, "html.parser")
        a_tag = soup.find("a", string=lambda text: text and "원문 보기" in text)
        if not a_tag:
            a_tags = soup.find_all("a")
            for tag in a_tags:
                if "원문 보기" in tag.get_text(strip=True):
                    a_tag = tag
                    break
        
        if a_tag and "href" in a_tag.attrs:
            strUrl = f"https://m.stock.naver.com{a_tag['href']}"
        else:
            logger.warning(f"Could not find 'Original View' link for {LIST_ARTICLE_URL}")
    except Exception as e:
        logger.error(f"Error parsing Naver Research URL: {e}")

    return strUrl

def GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER):
    msgFirmName = ""
    if SEC_FIRM_ORDER == 900: 
        msgFirmName = "[네이버 증권 "
        if ARTICLE_BOARD_ORDER == 0 : msgFirmName += "기업 리서치](https://m.stock.naver.com/investment/research/company)"
        else: msgFirmName += "산업 리서치](https://m.stock.naver.com/investment/research/industry)"
    return "\n\n" + " ●"+  msgFirmName + "\n" 

async def main():
    setup_logger()
    logger.info("=================== naver-research START ===================")
    
    try:
        if len(sys.argv) > 1 and sys.argv[1] == 'test':
            logger.info("Running in test mode.")
            return 
    except: pass

    await NAVER_Report_checkNewArticle()

    lists = get_unsent_main_ch_data_to_local_json(JSON_FILE_NAME)
    if lists:
        logger.info(f"Sending {len(lists)} unsent messages to main channel.")
        for sendMessageText in lists:
            await sendMarkDownText(token=token,
                                   chat_id=TELEGRAM_CHANNEL_ID_REPORT_ALARM,
                                   sendMessageText=sendMessageText)
        update_main_ch_send_yn_to_y(JSON_FILE_NAME)
    
if __name__ == "__main__":
	asyncio.run(main())
