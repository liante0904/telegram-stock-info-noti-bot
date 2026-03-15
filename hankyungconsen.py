# -*- coding:utf-8 -*- 
import requests
import asyncio
import os
from bs4 import BeautifulSoup
from loguru import logger

from utils.json_util import save_data_to_local_json, get_unsent_main_ch_data_to_local_json, update_main_ch_send_yn_to_y
from utils.telegram_util import sendMarkDownText
from utils.date_util import GetCurrentDate

from dotenv import load_dotenv

load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN = os.getenv('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
TELEGRAM_CHANNEL_ID_REPORT_ALARM = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')

JSON_FILE_NAME = './json/hankyungconsen_research.json'

def setup_logger():
    HOME_PATH = os.path.expanduser("~")
    log_date = GetCurrentDate('YYYYMMDD')
    LOG_PATH = os.path.join(HOME_PATH, "log", log_date)
    os.makedirs(LOG_PATH, exist_ok=True)
    
    log_file = os.path.join(LOG_PATH, f"{log_date}_hankyungconsen.log")
    logger.add(log_file, rotation="00:00", retention="30 days", level="DEBUG", 
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    return LOG_PATH

async def HankyungConsen_checkNewArticle():
    SEC_FIRM_ORDER = 100
    ARTICLE_BOARD_ORDER = 0
    requests.packages.urllib3.disable_warnings()

    TARGET_URL = 'https://consensus.hankyung.com/analysis/list?search_date=today&search_text=&pagenum=1000'
    sendMessageText = ''
    
    try:
        logger.info(f"Fetching Hankyung Consensus: {TARGET_URL}")
        webpage = requests.get(TARGET_URL, verify=False, headers={
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        })
        
        soup = BeautifulSoup(webpage.content, "html.parser")
        soupList = soup.select('#contents > div.table_style01 > table > tbody > tr')

        if not soupList:
            logger.debug("No articles found in Hankyung Consensus today.")
            return ""

        brokerName = soup.select('#contents > div.table_style01 > table > tbody > tr.first > td:nth-child(5)')[0].text
        first_article_processed = False
        
        for list_item in soupList:
            try:
                LIST_ARTICLE_CLASS = list_item.select_one('td:nth-child(2)').text
                LIST_ARTICLE_TITLE = list_item.select_one('td.text_l > a').text
                LIST_ARTICLE_URL = 'https://consensus.hankyung.com' + list_item.select_one('td:nth-child(6) > div > a').attrs['href']
                LIST_ARTICLE_BROKER_NAME = list_item.select_one('td:nth-child(5)').text

                new_article_message = save_data_to_local_json(
                    filename=JSON_FILE_NAME,
                    sec_firm_order=SEC_FIRM_ORDER,
                    article_board_order=ARTICLE_BOARD_ORDER,
                    firm_nm=LIST_ARTICLE_BROKER_NAME,
                    attach_url=LIST_ARTICLE_URL,
                    article_title=LIST_ARTICLE_TITLE
                )

                if new_article_message:
                    logger.info(f"New Hankyung Consensus Found: {LIST_ARTICLE_TITLE} ({LIST_ARTICLE_BROKER_NAME})")
                    if not first_article_processed or brokerName != LIST_ARTICLE_BROKER_NAME:
                        sendMessageText += "\n\n" + "●" + LIST_ARTICLE_BROKER_NAME + "\n"
                        brokerName = LIST_ARTICLE_BROKER_NAME
                        first_article_processed = True
                    sendMessageText += new_article_message

                if len(sendMessageText) >= 3000:
                    logger.info("Message limit reached, sending partial update.")
                    await sendMarkDownText(token=token,
                                           chat_id=TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN,
                                           sendMessageText=sendMessageText)
                    sendMessageText = ''
            except Exception as e:
                logger.error(f"Error processing Hankyung article item: {e}")
                continue

    except Exception as e:
        logger.exception(f"Error fetching/parsing Hankyung Consensus: {e}")

    if sendMessageText:
        await sendMarkDownText(token=token,
                               chat_id=TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN,
                               sendMessageText=sendMessageText)
    else:
        logger.debug('Hankyung Consensus: No new articles to send.')

    return sendMessageText

async def main():
    setup_logger()
    logger.info("=================== hankyungconsen START ===================")
    
    await HankyungConsen_checkNewArticle()

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
