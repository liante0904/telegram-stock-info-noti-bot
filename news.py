# -*- coding:utf-8 -*- 
import os
import telegram
import requests
import logging
import time
import json
import asyncio
import urllib.request

from package.common import *
from package.json_util import save_data_to_local_json  # import the function from json_util

from package.SecretKey import SecretKey

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

# 게시판 URL
BOARD_URL = ''
# 첫번째URL 
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

SECRET_KEY = SecretKey()
SECRET_KEY.load_secrets()

def ChosunBizBot_checkNewArticle():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 995
    ARTICLE_BOARD_ORDER = 995

    requests.packages.urllib3.disable_warnings()

    # 조선Biz Cbot API
    # TARGET_URL = 'https://biz.chosun.com/pf/api/v3/content/fetch/story-feed?query=%7B%22excludeSections%22%3A%22%22%2C%22expandRelated%22%3Atrue%2C%22includeContentTypes%22%3A%22story%22%2C%22includeSections%22%3A%22%2Fstock%2Fc-biz_bot%22%2C%22size%22%3A20%7D&filter=%7Bcontent_elements%7B%5B%5D%2C_id%2Ccanonical_url%2Ccredits%7Bby%7B_id%2Cadditional_properties%7Boriginal%7Baffiliations%2Cbyline%7D%7D%2Cname%2Corg%2Curl%7D%7D%2Cdescription%7Bbasic%7D%2Cdisplay_date%2Cheadlines%7Bbasic%2Cmobile%7D%2Clabel%7Bshoulder_title%7Btext%2Curl%7D%7D%2Cpromo_items%7Bbasic%7B_id%2Cadditional_properties%7Bfocal_point%7Bmax%2Cmin%7D%7D%7D%2Calt_text%2Ccaption%2Ccontent_elements%7B_id%2Calignment%2Calt_text%2Ccaption%2Ccontent%2Ccredits%7Baffiliation%7Bname%7D%2Cby%7B_id%2Cbyline%2Cname%7D%7D%2Cheight%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Csubtype%2Ctype%2Curl%2Cwidth%7D%2Ccredits%7Baffiliation%7Bbyline%2Cname%7D%2Cby%7Bbyline%2Cname%7D%7D%2Cdescription%7Bbasic%7D%2Cfocal_point%7Bx%2Cy%7D%2Cheadlines%7Bbasic%7D%2Cheight%2Cpromo_items%7Bbasic%7B_id%2Cheight%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Csubtype%2Ctype%2Curl%2Cwidth%7D%7D%2CresizedUrls%7B16x9_lg%2C16x9_md%2C16x9_sm%2C16x9_xl%2C16x9_xs%2C16x9_xxl%2C1x1_lg%2C1x1_md%2C1x1_sm%2C1x1_xl%2C1x1_xs%2C1x1_xxl%7D%2Cstreams%7Bheight%2Cwidth%7D%2Csubtype%2Ctype%2Curl%2Cwebsites%2Cwidth%7D%2Clead_art%7Bduration%2Ctype%7D%7D%2Crelated_content%7Bbasic%7B_id%2Cabsolute_canonical_url%2Cheadlines%7Bbasic%2Cmobile%7D%2Creferent%7Bid%2Ctype%7D%2Ctype%7D%7D%2Csubtype%2Ctaxonomy%7Bprimary_section%7B_id%2Cname%7D%2Ctags%7Bslug%2Ctext%7D%7D%2Ctest%2Ctype%2Cwebsite_url%7D%2Ccount%2Cnext%7D&d=92&_website=chosunbiz'
    TARGET_URL = 'https://mweb-api.stockplus.com/api/news_items/all_news.json?scope=latest&limit=100'
    
    # 조선Biz 웹 크롤링 변경
    # TARGET_URL = 'https://biz.chosun.com/stock/c-biz_bot/'
    
    # 조선Biz Cbot API JSON 크롤링
    ChosunBizBot_StockPlusJSONparse(ARTICLE_BOARD_ORDER, TARGET_URL)
 
# 증권플러스 뉴스 JSON API 타입
def ChosunBizBot_StockPlusJSONparse(ARTICLE_BOARD_ORDER, TARGET_URL):
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200 :return print("ChosunBizBot_StockPlusJSONparse 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True

    jres = jres['newsItems']
    

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for stockPlus in jres:
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
            nNewArticleCnt += 1 # 새로운 게시글 수
            print()
            print(LIST_ARTICLE_URL)
            print(LIST_ARTICLE_TITLE)
            print(LIST_ARTICLE_WRITER_NAME)
            print()
            
        if len(sendMessageText) >= 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            print(sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            nNewArticleCnt = 0
            sendMessageText = ''

    if nNewArticleCnt == 0  or len(sendMessageText) == 0:
        print('최신 게시글이 채널에 발송 되어 있습니다.')
        return
    
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)

    return sendMessageText

def NAVERNews_checkNewArticle_0():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 998
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 네이버 실시간 속보
    TARGET_URL_0 = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=flashnews'
    
    NAVERNews_parse_0(ARTICLE_BOARD_ORDER, TARGET_URL_0)

# JSON API 타입
def NAVERNews_parse_0(ARTICLE_BOARD_ORDER, TARGET_URL):

    print('NAVERNews_parse_0')
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    # 검색 요청 및 처리
    response = urllib.request.urlopen(request)
    rescode = response.getcode()
    if rescode != 200:
        return print("네이버 뉴스 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True
    jres = jres['result']
    category = 'flashnews'


    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for news in jres['newsList']:
        LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/' + category + '/' + news['oid'] + '/' + news['aid']
        LIST_ARTICLE_TITLE = news['tit']

        sendMessageText += save_data_to_local_json(
            filename='./json/naver_flashnews.json',
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=ARTICLE_BOARD_ORDER,
            firm_nm="네이버 - 실시간 뉴스 속보",#firm_info['firm_name'],
            attach_url=LIST_ARTICLE_URL,
            article_title=LIST_ARTICLE_TITLE
        )
        if sendMessageText:
            nNewArticleCnt += 1 # 새로운 게시글 수
            print('LIST_ARTICLE_TITLE',LIST_ARTICLE_TITLE)
            print('LIST_ARTICLE_URL',LIST_ARTICLE_URL)
        if len(sendMessageText) >= 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            print(sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            nNewArticleCnt = 0
            sendMessageText = ''

    if nNewArticleCnt == 0  or len(sendMessageText) == 0:
        print('최신 게시글이 채널에 발송 되어 있습니다.')
        return
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        sendText(GetSendMessageTitle() + sendMessageText)

    return sendMessageText

def NAVERNews_checkNewArticle_1():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 998
    ARTICLE_BOARD_ORDER = 1

    requests.packages.urllib3.disable_warnings()

    # 네이버 많이 본 뉴스
    TARGET_URL_1 = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=ranknews'
    
    NAVERNews_parse_1(ARTICLE_BOARD_ORDER, TARGET_URL_1)

# JSON API 타입
def remove_duplicates(a_data, b_data):
    try:
        # b_data를 set으로 변환하여 중복 제거에 사용할 수 있게 함
        b_set = {json.dumps(item, sort_keys=True) for item in b_data['newsList']}
    except KeyError as e:
        print(f"KeyError in b_data: {e}")
        print(f"b_data: {json.dumps(b_data, indent=4, ensure_ascii=False)}")
        raise

    try:
        # a_data에서 b_data와 중복되지 않는 항목만 선택
        result = [item for item in a_data['newsList'] if json.dumps(item, sort_keys=True) not in b_set]
    except KeyError as e:
        print(f"KeyError in a_data: {e}")
        print(f"a_data: {json.dumps(a_data, indent=4, ensure_ascii=False)}")
        raise
    
    return result

def NAVERNews_parse_1(ARTICLE_BOARD_ORDER, TARGET_URL):

    logging.debug('NAVERNews_parse_1')
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    # 검색 요청 및 처리
    try:
        response = urllib.request.urlopen(request)
    except Exception as e:
        print(f"Error during request to {TARGET_URL}: {e}")
        return

    rescode = response.getcode()
    if rescode != 200:
        return print("네이버 뉴스 접속이 원활하지 않습니다 ")

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Error loading JSON from response: {e}")
        return True

    try:
        jres = jres['result']
    except KeyError as e:
        print(f"KeyError in jres: {e}")
        print(f"jres: {json.dumps(jres, indent=4, ensure_ascii=False)}")
        return True

    logging.debug(jres)

    directory = './json'

    # 파일명 결정
    filename = os.path.join(directory, 'naver_ranknews.json')

    # 파일 존재 여부 확인 및 저장
    if not os.path.exists(filename):
        # jres를 파일로 저장
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(jres, f, ensure_ascii=False, indent=4)
            filtered_jres = jres['newsList']
            print(f"saving JSON to file {filename}")
        except Exception as e:
            print(f"Error saving JSON to file {filename}: {e}")
            return True
    else:
        # 파일이 이미 존재하는 경우, 파일을 읽어오기
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                saved_jres = json.load(f)

            # 예외 처리: 'newsList' 키가 없을 경우 기본값 설정
            if 'newsList' not in saved_jres:
                print("Key 'newsList' not found in saved_jres, initializing with empty list")
                saved_jres['newsList'] = []
            logging.debug(saved_jres)
            logging.debug(jres)

            # 중복 제거 로직 추가
            try:
                existing_titles = {item['tit'] for item in saved_jres['newsList']}
            except KeyError as e:
                print(f"KeyError in saved_jres: {e}")
                existing_titles = set()
            
            try:
                new_unique_data = [item for item in jres['newsList'] if item.get('tit') not in existing_titles]
            except KeyError as e:
                print(f"KeyError in jres: {e}")
                new_unique_data = []
            
            filtered_jres = new_unique_data

            if filtered_jres:
                # 중복이 제거된 데이터를 기존 데이터에 추가하여 다시 저장
                saved_jres['newsList'].extend(filtered_jres)
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(saved_jres, f, ensure_ascii=False, indent=4)
                    print(f"Updated JSON saved to file {filename}")
                except Exception as e:
                    print(f"Error saving updated JSON to file {filename}: {e}")
                    return True
            else:
                print("중복된 항목이 없어 새로운 데이터가 없습니다.")

        except Exception as e:
            print(f"Error reading JSON from file {filename}: {e}")
            return True

    sendMessageText = ""

    # 중복 제거된 아이템 출력 및 메시지 생성
    if filtered_jres:
        # NaverNews 게시판에 따른 URL 지정
        category = 'ranknews'
        print('중복 제거된 아이템들:')
        for news in filtered_jres:
            LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/' + category + '/' + news['oid'] + '/' + news['aid']
            LIST_ARTICLE_TITLE = news['tit']
            sendMessageText += GetSendMessageText(INDEX=0, ARTICLE_BOARD_NAME='', ARTICLE_TITLE=LIST_ARTICLE_TITLE, ARTICLE_URL=LIST_ARTICLE_URL)

            # 메시지 길이가 3500을 넘으면 출력하고 초기화
            if len(sendMessageText) > 3500:
                print(sendMessageText)
                sendText(GetSendMessageTitle() + sendMessageText)
                sendMessageText = ""

        # 마지막으로 남은 메시지가 있으면 출력
        if sendMessageText:
            print(sendMessageText)
            sendText(GetSendMessageTitle() + sendMessageText)
            sendMessageText = ""

async def sendAlertMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True)

async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    global CHAT_ID
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    return await bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

# 가공없이 텍스트를 발송합니다.
def sendText(sendMessageText): 
    global CHAT_ID

    #생성한 텔레그램 봇 정보(@ebest_noti_bot)
    bot = telegram.Bot(token = SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET)
    #bot.sendMessage(chat_id = GetSendChatId(), text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")
    asyncio.run(sendMessage(sendMessageText)) #봇 실행하는 코드
    time.sleep(1) # 모바일 알림을 받기 위해 8초 텀을 둠(loop 호출시)

# 인자 텍스트를 더해가며 발송합니다. 
# 더해진 텍스트가 텔레그램 제한인 3500자를 넘어가면 발송처리하고 초기화합니다
# 두번째 인자는 첫번째 인자 텍스트를 앞으로 더할지 뒤로 더할지 결정합니다. (F: 앞, B: 뒤에 텍스트를 더합니다)
# 인자를 결정하지 않은 경우 텍스트를 뒤로 붙이도록 설정
# 두번째 파라미터가 Y인 경우 길이와 상관없이 발송처리(집계된 데이터 발송용)
def sendAddText(sendMessageText, sendType='N'): 
    global SEND_ADD_MESSAGE_TEXT

    SEND_ADD_MESSAGE_TEXT += sendMessageText
    print('sendType ', sendType)
    print('sendMessageText ',sendMessageText)
    print('SEND_ADD_MESSAGE_TEXT ', SEND_ADD_MESSAGE_TEXT)

    if len(SEND_ADD_MESSAGE_TEXT) > 3500 or ( sendType == 'Y' and len(SEND_ADD_MESSAGE_TEXT) > 0 ) :
        print("sendAddText() (실제 발송요청)\n", SEND_ADD_MESSAGE_TEXT)
        sendText(SEND_ADD_MESSAGE_TEXT)
        SEND_ADD_MESSAGE_TEXT = ''

    return ''

def GetSendMessageText(INDEX, ARTICLE_BOARD_NAME , ARTICLE_TITLE , ARTICLE_URL):
    # 실제 전송할 메시지 작성
    sendMessageText = ''
    # 발신 게시판 종류
    # if INDEX == 1:
    #     sendMessageText += GetSendMessageTitle() + "\n"
    # 게시글 제목(굵게)
    sendMessageText += "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ARTICLE_URL + ")"  + "\n\n" 

    return sendMessageText

    
# 타이틀 생성 
# : 게시판 이름 삭제
def GetSendMessageTitle(): 
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

def GetSendChatId():
    SendMessageChatId = 0
    if SEC_FIRM_ORDER == 998:
        if  ARTICLE_BOARD_ORDER == 0 : 
            SendMessageChatId = SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS # 네이버 실시간 속보 뉴스 채널
        else:
            SendMessageChatId = SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS # 네이버 많이본 뉴스 채널
    elif SEC_FIRM_ORDER == 995:
            SendMessageChatId = SECRET_KEY.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT # 조선비즈 C-bot
    
    # SendMessageChatId = SECRET_KEY.TELEGRAM_CHANNEL_ID_TEST
    return SendMessageChatId
 
def main():
    global SEC_FIRM_ORDER  # 증권사 순번

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

    # log 파일명
    LOG_FILENAME = GetCurrentDate('YYYYMMDD') + '_' + script_name + ".dbg"
    print('__file__', __file__, LOG_FILENAME)

    # log 전체경로
    LOG_FULLFILENAME = os.path.join(LOG_PATH, LOG_FILENAME)
    print('LOG_FULLFILENAME', LOG_FULLFILENAME)

    # # 로깅 설정 추가
    # logging.basicConfig(filename=LOG_FULLFILENAME, level=logging.DEBUG,
    #                     format='%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]', force=True)

    # # 콘솔 핸들러 추가
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.DEBUG)
    # console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'))
    # logging.getLogger().addHandler(console_handler)

    # 디버그 메시지 출력
    print("LOG_FULLFILENAME", LOG_FULLFILENAME)
    logging.debug('이것은 디버그 메시지입니다.')
    
    print(GetCurrentDay())
    
    print("ChosunBizBot_checkNewArticle()=> 새 게시글 정보 확인 # 995");  ChosunBizBot_checkNewArticle(); 
    print("NAVERNews_checkNewArticle_0()=> 새 게시글 정보 확인 # 998"); NAVERNews_checkNewArticle_0(); 
    print("NAVERNews_checkNewArticle_1()=> 새 게시글 정보 확인 # 998"); NAVERNews_checkNewArticle_1(); 

if __name__ == "__main__":
	main()
