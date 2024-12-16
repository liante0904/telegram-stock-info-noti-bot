# -*- coding:utf-8 -*- 
import os
import requests
import json
import asyncio
import aiohttp
import logging

from datetime import datetime, timedelta
from utils.json_util import save_data_to_local_json, filter_news_by_save_time
from utils.date_util import GetCurrentDate
from utils.telegram_util import sendMarkDownText
from models.SecretKey import SecretKey

############공용 상수############

# 이모지
EMOJI_FIRE = u'\U0001F525'
EMOJI_PICK = u'\U0001F449'

#################### global 변수 정리 끝###################################

SECRET_KEY = SecretKey()

token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET

async def fetch(session, url):
    async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
        if response.status != 200:
            print(f"{url} 접속이 원활하지 않습니다 ")
            return None
        return await response.json()

# 조선비즈 뉴스 데이터 처리
async def ChosunBizBot_checkNewArticle():
    SEC_FIRM_ORDER      = 995
    ARTICLE_BOARD_ORDER = 995
    requests.packages.urllib3.disable_warnings()


    directory = './json'
    filename = os.path.join(directory, 'ChosunBizBot.json')

    filter_news_by_save_time(filename)

    TARGET_URL = 'https://mweb-api.stockplus.com/api/news_items/all_news.json?scope=latest&limit=100'
    
    # 조선Biz 웹 크롤링 변경
    # TARGET_URL = 'https://biz.chosun.com/stock/c-biz_bot/'
    
    # 조선Biz Cbot API JSON 크롤링
    
    # request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    # response = urllib.request.urlopen(request)
    # rescode = response.getcode()
    # if rescode != 200 :return print("ChosunBizBot_StockPlusJSONparse 접속이 원활하지 않습니다 ")

    # try:
    #     jres = json.loads(response.read().decode('utf-8'))
    # except:
    #     return True

    async with aiohttp.ClientSession() as session:
        jres = await fetch(session, TARGET_URL)
        if jres is None:
            return

    sendMessageText = ''
    # JSON To List
    for stockPlus in jres['newsItems']:
        LIST_ARTICLE_URL = stockPlus['url']
        LIST_ARTICLE_TITLE = stockPlus['title']
        LIST_ARTICLE_WRITER_NAME = stockPlus['writerName']

        sendMessageText += save_data_to_local_json(
            filename='./json/ChosunBizBot.json',
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm="조선비즈 - C-Biz봇",#firm_info['firm_name'],
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        if sendMessageText:
            print()
            print(LIST_ARTICLE_URL)
            print(LIST_ARTICLE_TITLE)
            print(LIST_ARTICLE_WRITER_NAME)
            print()

        if len(sendMessageText) >= 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            await sendMarkDownText(
                token=token,
                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT,
                sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText
            )
            sendMessageText = ''

    if sendMessageText:
        print(sendMessageText)
        await sendMarkDownText(token=token,
                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT,
                sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
    else:
        print('최신 게시글이 채널에 발송 되어 있습니다.')

    return sendMessageText
    
async def NAVERNews_checkNewArticle_0():
    SEC_FIRM_ORDER = 998
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()


    directory = './json'
    filename = os.path.join(directory, 'naver_flashnews.json')

    filter_news_by_save_time(filename)

    # 네이버 실시간 속보
    TARGET_URL = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=flashnews'
    
    # 비동기 호출 
    async with aiohttp.ClientSession() as session:
        jres = await fetch(session, TARGET_URL)
        if jres is None:
            return    

    jres = jres['result']

    sendMessageText = ''
    # JSON To List
    for news in jres['newsList']:
        LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/flashnews/' + news['oid'] + '/' + news['aid']
        LIST_ARTICLE_TITLE = news['tit']

        sendMessageText += save_data_to_local_json(
            filename=filename,
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm="네이버 - 실시간 뉴스 속보",#firm_info['firm_name'],
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        if sendMessageText:
            print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
            print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
        if len(sendMessageText) >= 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            print(sendMessageText)
            await sendMarkDownText(token=token,
                                    chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS,
                                    sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
            sendMessageText = ''

    print('**************')
    print(f'len(sendMessageText): {len(sendMessageText)}')
    if sendMessageText:
        print(sendMessageText)
        await sendMarkDownText(token=token,
                                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS,
                                sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
    else:
        print('최신 게시글이 채널에 발송 되어 있습니다.')

    return sendMessageText

            
# 인메모리 데이터베이스에 기존 뉴스 로드
existing_titles = set()
async def load_existing_data_into_memory(filename):
    global existing_titles
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            saved_jres = json.load(f)
        existing_titles = {item['tit'] for item in saved_jres['newsList']}
        print(f"Loaded {len(existing_titles)} articles into memory")
    else:
        print("No existing file found. Starting fresh.")

# 중복 체크를 메모리 내에서 처리
async def check_for_duplicates_in_memory(jres):
    global existing_titles
    new_unique_data = [item for item in jres['newsList'] if item.get('tit') not in existing_titles]
    # 메모리에 중복된 기사 추가
    existing_titles.update([item['tit'] for item in new_unique_data])
    return new_unique_data

# 나머지 코드는 기존과 동일

# 기존 파일에 중복되지 않은 새로운 데이터를 저장
async def save_new_data_to_file(filename, new_data):
    if new_data:  # 새로운 데이터가 있을 때만 저장
        if os.path.exists(filename):
            with open(filename, 'r+', encoding='utf-8') as f:
                saved_jres = json.load(f)
                saved_jres['newsList'].extend(new_data)
                f.seek(0)  # 파일 시작 위치로 이동
                json.dump(saved_jres, f, ensure_ascii=False, indent=4)
        else:
            # 파일이 존재하지 않으면 새로운 파일을 생성
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({'newsList': new_data}, f, ensure_ascii=False, indent=4)
        print(f"Saved {len(new_data)} new articles to {filename}")

# 새로운 데이터를 체크하고 저장하는 함수
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
    except KeyError as e:
        print(f"KeyError in jres: {e}")
        return True

    directory = './json'
    filename = os.path.join(directory, 'naver_ranknews.json')


    # 함수 사용 예시
    filtered_file = filter_news_by_date(filename)  # 실제 파일 경로 입력

    # Load existing data into memory at the beginning
    await load_existing_data_into_memory(filename)

    # 중복 체크 후 새로운 데이터 필터링
    filtered_jres = await check_for_duplicates_in_memory(jres)
    
    # 신규 데이터가 있을 때만 파일에 저장
    await save_new_data_to_file(filename, filtered_jres)

    sendMessageText = ""

    # 중복 제거된 아이템 출력 및 메시지 생성
    if filtered_jres:
        category = 'ranknews'
        for news in filtered_jres:
            LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/' + category + '/' + news['oid'] + '/' + news['aid']
            LIST_ARTICLE_TITLE = news['tit']
            sendMessageText += await GetSendMessageText(ARTICLE_TITLE=LIST_ARTICLE_TITLE, ARTICLE_URL=LIST_ARTICLE_URL)

            if len(sendMessageText) > 3500:
                print(sendMessageText)
                await sendMarkDownText(token=token,
                                       chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS,
                                       sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText)
                sendMessageText = ""

        if sendMessageText:
            print(sendMessageText)
            await sendMarkDownText(token=token,
                                   chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS,
                                   sendMessageText= await GetSendMessageTitle(SEC_FIRM_ORDER, ARTICLE_BOARD_ORDER) + sendMessageText)
            sendMessageText = ""


def filter_news_by_date(filename):
    # 파일에서 JSON 데이터 읽기
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 오늘 날짜
    today = datetime.now()

    # 1주일 이내 날짜 계산
    one_week_ago = today - timedelta(days=7)

    # 뉴스 리스트 필터링
    filtered_news_list = [
        news for news in data['newsList']
        if datetime.strptime(news['dt'], '%Y%m%d%H%M%S') >= one_week_ago
    ]

    # 필터링된 데이터를 원래 구조에 맞게 업데이트
    data['newsList'] = filtered_news_list

    # 필터링된 데이터를 다시 JSON 파일로 저장
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
         

# 본문 생성
async def GetSendMessageText(ARTICLE_TITLE , ARTICLE_URL):
    sendMessageText = "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ARTICLE_URL + ")"  + "\n\n" 

    return sendMessageText

# 타이틀 생성 
async def GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER): 
    SendMessageTitle = ""
    msgFirmName = ""
    
    if SEC_FIRM_ORDER == 998:
        msgFirmName = "네이버 - "
        if  ARTICLE_BOARD_ORDER == 0 : msgFirmName += "실시간 뉴스 속보"
        else: msgFirmName += "가장 많이 본 뉴스"
    elif SEC_FIRM_ORDER == 995: msgFirmName = "조선비즈 - C-Biz봇"

    # SendMessageTitle += "\n" + EMOJI_FIRE + msgFirmName + EMOJI_FIRE + "\n" 
    SendMessageTitle += "\n\n" + " ●"+  msgFirmName + "\n" 
    
    return SendMessageTitle


def setup_logging(script_name, log_path, log_level=logging.DEBUG):
    """
    로깅 설정 함수.
    
    Args:
        script_name (str): 스크립트 이름으로 로그 파일을 구분.
        log_path (str): 로그 파일이 저장될 경로.
        log_level (int): 로깅 레벨 (기본값: DEBUG).
    """
    # log 파일명 생성
    log_filename = GetCurrentDate('YYYYMMDD') + '_' + script_name + ".dbg"

    # log 전체경로 생성
    log_fullfilename = os.path.join(log_path, log_filename)
    print('LOG_FULLFILENAME:', log_fullfilename)  # 디버그용 출력

    # 로깅 기본 설정 (파일 출력)
    logging.basicConfig(
        filename=log_fullfilename,
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]',
        force=True  # 기존 핸들러 강제로 교체
    )

    # 콘솔 핸들러 추가 (콘솔에도 출력하기 위해)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'))
    
    # 기존 로거에 콘솔 핸들러 추가
    logging.getLogger().addHandler(console_handler)

    # 디버그 메시지 출력
    logging.debug('로깅이 설정되었습니다.')
    
async def main():
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
    script_name = script_filename.split('.')[0]
    print('script_filename', script_filename)

    # script_name = os.path.basename(__file__).replace('.py', '')  # 스크립트 이름
    # log_path = './logs'  # 로그 파일이 저장될 경로
    
    # # 로그 경로가 없으면 생성
    # if not os.path.exists(log_path):
    #     os.makedirs(log_path)

    # # 로깅 설정 함수 호출
    # setup_logging(script_name, log_path)

    # # 예시 디버그 메시지
    # logging.debug('디버그 메시지 출력 예시')
    # logging.info('정보 메시지 출력 예시')
    # logging.warning('경고 메시지 출력 예시')
     
    print("ChosunBizBot_checkNewArticle()=> 새 게시글 정보 확인 # 995");  
    await ChosunBizBot_checkNewArticle(); 
    print("NAVERNews_checkNewArticle_0()=> 새 게시글 정보 확인 # 998"); 
    await NAVERNews_checkNewArticle_0(); 
    print("NAVERNews_checkNewArticle_1()=> 새 게시글 정보 확인 # 998"); 
    await NAVERNews_checkNewArticle_1(); 

if __name__ == '__main__':
    asyncio.run(main())