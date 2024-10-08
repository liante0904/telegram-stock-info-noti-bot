# -*- coding:utf-8 -*- 
import os
import requests
import json
import asyncio
import aiohttp

from utils.json_util import save_data_to_local_json  # import the function from json_util
from utils.date_util import GetCurrentDate, GetCurrentDay
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
    
async def ChosunBizBot_checkNewArticle():
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

    nNewArticleCnt = 0
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
            nNewArticleCnt += 1 # 새로운 게시글 수
            print()
            print(LIST_ARTICLE_URL)
            print(LIST_ARTICLE_TITLE)
            print(LIST_ARTICLE_WRITER_NAME)
            print()
            
        if len(sendMessageText) >= 3500:
            print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다.")
            print(sendMessageText)
            await sendMarkDownText(token=token,
                           chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT,
                           sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
            nNewArticleCnt = 0
            sendMessageText = ''


    if nNewArticleCnt == 0  or len(sendMessageText) == 0:
        print('최신 게시글이 채널에 발송 되어 있습니다.')
        return
    
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        await sendMarkDownText(token=token,
                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_CHOSUNBIZBOT,
                sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)

    return sendMessageText

async def NAVERNews_checkNewArticle_0():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 998
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 네이버 실시간 속보
    TARGET_URL = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=flashnews'
    
    # 동기 호출     
    # request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    # # 검색 요청 및 처리
    # response = urllib.request.urlopen(request)
    # rescode = response.getcode()
    # if rescode != 200:
    #     return print("네이버 뉴스 접속이 원활하지 않습니다 ")

    # try:
    #     jres = json.loads(response.read().decode('utf-8'))
    # except:
    #     return True

    # 비동기 호출 
    async with aiohttp.ClientSession() as session:
        jres = await fetch(session, TARGET_URL)
        if jres is None:
            return    

    
    jres = jres['result']

    nNewArticleCnt = 0
    sendMessageText = ''
    # JSON To List
    for news in jres['newsList']:
        LIST_ARTICLE_URL = 'https://m.stock.naver.com/investment/news/flashnews/' + news['oid'] + '/' + news['aid']
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
            await sendMarkDownText(token=token,
                                    chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS,
                                    sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
            nNewArticleCnt = 0
            sendMessageText = ''

    if nNewArticleCnt == 0  or len(sendMessageText) == 0:
        print('최신 게시글이 채널에 발송 되어 있습니다.')
        return
    print('**************')
    print(f'nNewArticleCnt {nNewArticleCnt} len(sendMessageText){len(sendMessageText)}' )
    if nNewArticleCnt > 0  or len(sendMessageText) > 0:
        print(sendMessageText)
        await sendMarkDownText(token=token,
                                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_FLASHNEWS,
                                sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)

    return sendMessageText

async def NAVERNews_checkNewArticle_1():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 998
    ARTICLE_BOARD_ORDER = 1

    requests.packages.urllib3.disable_warnings()

    # 네이버 많이 본 뉴스
    TARGET_URL = 'https://m.stock.naver.com/api/json/news/newsListJson.nhn?category=ranknews'
    

    # logging.debug('NAVERNews_parse_1')
    # request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    # # 검색 요청 및 처리
    # try:
    #     response = urllib.request.urlopen(request)
    # except Exception as e:
    #     print(f"Error during request to {TARGET_URL}: {e}")
    #     return

    # rescode = response.getcode()
    # if rescode != 200:
    #     return print("네이버 뉴스 접속이 원활하지 않습니다 ")

    # try:
    #     jres = json.loads(response.read().decode('utf-8'))
    # except Exception as e:
    #     print(f"Error loading JSON from response: {e}")
    #     return True

    async with aiohttp.ClientSession() as session:
        jres = await fetch(session, TARGET_URL)
        if jres is None:
            return
        
    try:
        jres = jres['result']
    except KeyError as e:
        print(f"KeyError in jres: {e}")
        print(f"jres: {json.dumps(jres, indent=4, ensure_ascii=False)}")
        return True

    # logging.debug(jres)

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
            # logging.debug(saved_jres)
            # logging.debug(jres)

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
            sendMessageText += GetSendMessageText(ARTICLE_TITLE=LIST_ARTICLE_TITLE, ARTICLE_URL=LIST_ARTICLE_URL)

            # 메시지 길이가 3500을 넘으면 출력하고 초기화
            if len(sendMessageText) > 3500:
                print(sendMessageText)
                await sendMarkDownText(token=token,
                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS,
                sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
                sendMessageText = ""

        # 마지막으로 남은 메시지가 있으면 출력
        if sendMessageText:
            print(sendMessageText)
            await sendMarkDownText(token=token,
                                    chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_NAVER_RANKNEWS,
                                    sendMessageText=GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER) + sendMessageText)
            sendMessageText = ""

# 본문 생성
def GetSendMessageText(ARTICLE_TITLE , ARTICLE_URL):
    sendMessageText = "*" + ARTICLE_TITLE.replace("_", " ").replace("*", "") + "*" + "\n"
    # 원문 링크
    sendMessageText += EMOJI_PICK  + "[링크]" + "("+ ARTICLE_URL + ")"  + "\n\n" 

    return sendMessageText

# 타이틀 생성 
def GetSendMessageTitle(SEC_FIRM_ORDER,  ARTICLE_BOARD_ORDER): 
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

    # # log 파일명
    # LOG_FILENAME = GetCurrentDate('YYYYMMDD') + '_' + script_name + ".dbg"
    # print('__file__', __file__, LOG_FILENAME)

    # # log 전체경로
    # LOG_FULLFILENAME = os.path.join(LOG_PATH, LOG_FILENAME)
    # print('LOG_FULLFILENAME', LOG_FULLFILENAME)

    # # 로깅 설정 추가
    # logging.basicConfig(filename=LOG_FULLFILENAME, level=logging.DEBUG,
    #                     format='%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]', force=True)

    # # 콘솔 핸들러 추가
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.DEBUG)
    # console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]'))
    # logging.getLogger().addHandler(console_handler)

    # 디버그 메시지 출력
    # print("LOG_FULLFILENAME", LOG_FULLFILENAME)
    # logging.debug('이것은 디버그 메시지입니다.')
    
    print(GetCurrentDay())
    
    print("ChosunBizBot_checkNewArticle()=> 새 게시글 정보 확인 # 995");  
    await ChosunBizBot_checkNewArticle(); 
    print("NAVERNews_checkNewArticle_0()=> 새 게시글 정보 확인 # 998"); 
    await NAVERNews_checkNewArticle_0(); 
    print("NAVERNews_checkNewArticle_1()=> 새 게시글 정보 확인 # 998"); 
    await NAVERNews_checkNewArticle_1(); 

if __name__ == '__main__':
    asyncio.run(main())