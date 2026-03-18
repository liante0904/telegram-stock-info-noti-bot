# -*- coding:utf-8 -*- 
import os
import requests
import json
import asyncio
import aiohttp
import tempfile
from loguru import logger
from datetime import datetime, timedelta

from utils.json_util import save_data_to_local_json, filter_news_by_save_time
from utils.date_util import GetCurrentDate
from utils.telegram_util import sendMarkDownText

from dotenv import load_dotenv

load_dotenv()

############공용 상수############
# 이모지
EMOJI_FIRE = u'\U0001F525'
EMOJI_PICK = u'\U0001F449'

# 환경 변수
token = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT = os.getenv('TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT')
TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS = os.getenv('TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS')
TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS = os.getenv('TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS')

def setup_logger():
    HOME_PATH = os.path.expanduser("~")
    log_date = GetCurrentDate('YYYYMMDD')
    LOG_PATH = os.path.join(HOME_PATH, "log", log_date)
    os.makedirs(LOG_PATH, exist_ok=True)
    
    log_file = os.path.join(LOG_PATH, f"{log_date}_news.log")
    logger.add(log_file, rotation="00:00", retention="30 days", level="DEBUG", 
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    return LOG_PATH

def safe_json_dump(data, filename):
    """임시 파일을 사용하여 JSON을 안전하게 저장합니다 (Atomic Write)."""
    directory = os.path.dirname(filename)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with tempfile.NamedTemporaryFile('w', dir=directory, delete=False, encoding='utf-8') as tf:
        json.dump(data, tf, ensure_ascii=False, indent=4)
        tempname = tf.name
    os.replace(tempname, filename)

async def fetch(session, url):
    try:
        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
            if response.status != 200:
                logger.error(f"{url} 접속 실패 (Status: {response.status})")
                return None
            return await response.json()
    except Exception as e:
        logger.exception(f"Error fetching {url}: {e}")
        return None

async def ChosunBizBot_checkNewArticle():
    SEC_FIRM_ORDER      = 995
    ARTICLE_BOARD_ORDER = 995
    requests.packages.urllib3.disable_warnings()

    filename = './json/ChosunBizBot.json'
    filter_news_by_save_time(filename)

    TARGET_URL = 'https://mweb-api.stockplus.com/api/news_items/all_news.json?scope=latest&limit=100'
    
    async with aiohttp.ClientSession() as session:
        jres = await fetch(session, TARGET_URL)
        if jres is None:
            return

    sendMessageText = ''
    for stockPlus in jres['newsItems']:
        LIST_ARTICLE_URL = stockPlus['url']
        LIST_ARTICLE_TITLE = stockPlus['title']

        new_msg = save_data_to_local_json(
            filename=filename,
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm="조선비즈 - C-Biz봇",
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        
        if new_msg:
            logger.info(f"New Article Found (ChosunBiz): {LIST_ARTICLE_TITLE}")
            sendMessageText += new_msg

        if len(sendMessageText) >= 3500:
            logger.info("Message limit reached, sending partial update.")
            await sendMarkDownText(
                token=token,
                chat_id=TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT,
                sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText
            )
            sendMessageText = ''

    if sendMessageText:
        await sendMarkDownText(token=token,
                chat_id=TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT,
                sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText)
    else:
        logger.debug('ChosunBizBot: No new articles to send.')

async def NAVERNews_checkNewArticle_0():
    SEC_FIRM_ORDER = 998
    ARTICLE_BOARD_ORDER = 0
    requests.packages.urllib3.disable_warnings()

    filename = './json/naver_flashnews.json'
    filter_news_by_save_time(filename)

    TARGET_URL = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=flashnews'
    
    async with aiohttp.ClientSession() as session:
        jres = await fetch(session, TARGET_URL)
        if jres is None:
            return    

    jres = jres.get('result', {})

    sendMessageText = ''
    for news in jres.get('newsList', []):
        LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/flashnews/' + news['oid'] + '/' + news['aid']
        LIST_ARTICLE_TITLE = news['tit']

        new_msg = save_data_to_local_json(
            filename=filename,
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm="네이버 - 실시간 뉴스 속보",
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        
        if new_msg:
            logger.info(f"New Flash News Found: {LIST_ARTICLE_TITLE}")
            sendMessageText += new_msg

        if len(sendMessageText) >= 3500:
            logger.info("Flash news message limit reached, sending partial update.")
            await sendMarkDownText(token=token,
                                    chat_id=TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS,
                                    sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
            sendMessageText = ''

    if sendMessageText:
        await sendMarkDownText(token=token,
                                chat_id=TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS,
                                sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
    else:
        logger.debug('NAVER FlashNews: No new articles to send.')

existing_titles = set()
async def load_existing_data_into_memory(filename):
    global existing_titles
    if os.path.exists(filename) and os.path.getsize(filename) > 0:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                saved_jres = json.load(f)
            existing_titles = {item['tit'] for item in saved_jres.get('newsList', [])}
            logger.debug(f"Loaded {len(existing_titles)} articles into memory from {filename}")
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}. Starting fresh.")
            existing_titles = set()
    else:
        existing_titles = set()

async def check_for_duplicates_in_memory(jres):
    global existing_titles
    new_unique_data = [item for item in jres.get('newsList', []) if item.get('tit') not in existing_titles]
    existing_titles.update([item['tit'] for item in new_unique_data])
    return new_unique_data

async def save_new_data_to_file(filename, new_data):
    if new_data:
        saved_jres = {'newsList': []}
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    saved_jres = json.load(f)
            except Exception as e:
                logger.error(f"Warning: {filename} is corrupted: {e}")
        
        if 'newsList' not in saved_jres:
            saved_jres['newsList'] = []
            
        saved_jres['newsList'].extend(new_data)
        safe_json_dump(saved_jres, filename)
        logger.info(f"Saved {len(new_data)} new articles to {filename}")

async def NAVERNews_checkNewArticle_1():
    SEC_FIRM_ORDER = 998
    ARTICLE_BOARD_ORDER = 1
    TARGET_URL = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=ranknews'
    requests.packages.urllib3.disable_warnings()

    async with aiohttp.ClientSession() as session:
        jres = await fetch(session, TARGET_URL)
        if jres is None:
            return

    try:
        jres = jres['result']
    except Exception as e:
        logger.error(f"Error in jres structure: {e}")
        return

    filename = './json/naver_ranknews.json'
    filter_news_by_date(filename)
    await load_existing_data_into_memory(filename)

    filtered_jres = await check_for_duplicates_in_memory(jres)
    await save_new_data_to_file(filename, filtered_jres)

    sendMessageText = ""
    if filtered_jres:
        category = 'ranknews'
        for news in filtered_jres:
            LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/' + category + '/' + news['oid'] + '/' + news['aid']
            LIST_ARTICLE_TITLE = news['tit']
            logger.info(f"New Rank News Found: {LIST_ARTICLE_TITLE}")
            sendMessageText += await GetSendMessageText(ARTICLE_TITLE=LIST_ARTICLE_TITLE, ARTICLE_URL=LIST_ARTICLE_URL)

            if len(sendMessageText) > 3500:
                await sendMarkDownText(token=token,
                                       chat_id=TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS,
                                       sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText)
                sendMessageText = ""

        if sendMessageText:
            await sendMarkDownText(token=token,
                                   chat_id=TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS,
                                   sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText)
    else:
        logger.debug('NAVER RankNews: No new articles to send.')

def filter_news_by_date(filename):
    if not os.path.exists(filename) or os.path.getsize(filename) == 0:
        return
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        today = datetime.now()
        one_week_ago = today - timedelta(days=7)
        filtered_news_list = [
            news for news in data.get('newsList', [])
            if datetime.strptime(news.get('dt', '19000101000000'), '%Y%m%d%H%M%S') >= one_week_ago
        ]
        data['newsList'] = filtered_news_list
        safe_json_dump(data, filename)
    except Exception as e:
        logger.error(f"Error filtering news by date: {e}")

async def GetSendMessageText(ARTICLE_TITLE , ARTICLE_URL):
    sendMessageText = "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ARTICLE_URL + ")"  + "\n\n" 
    return sendMessageText

async def GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER): 
    msgFirmName = ""
    if SEC_FIRM_ORDER == 998:
        msgFirmName = "네이버 - "
        if  ARTICLE_BOARD_ORDER == 0 : msgFirmName += "실시간 뉴스 속보"
        else: msgFirmName += "가장 많이 본 뉴스"
    elif SEC_FIRM_ORDER == 995: msgFirmName = "조선비즈 - C-Biz봇"
    return "\n\n" + " ●"+  msgFirmName + "\n" 

async def main():
    setup_logger()
    logger.info("=================== news START ===================")
    
    logger.info("Checking ChosunBizBot news...")
    await ChosunBizBot_checkNewArticle() 
    
    logger.info("Checking NAVER FlashNews...")
    await NAVERNews_checkNewArticle_0() 
    
    logger.info("Checking NAVER RankNews...")
    await NAVERNews_checkNewArticle_1() 

if __name__ == '__main__':
    asyncio.run(main())
