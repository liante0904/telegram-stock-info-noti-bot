# -*- coding:utf-8 -*- 
import os
import telegram
import requests
import asyncio
import urllib.request
import json
from urllib.parse import urlencode, urlunparse

from dotenv import load_dotenv
load_dotenv()  # .env 파일의 환경 변수를 로드합니다
env = os.getenv('ENV')
print(env)
if env == 'production':
    TELEGRAM_BOT_TOKEN_PROD                 = os.getenv('TELEGRAM_BOT_TOKEN_PROD')
    TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET  = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
    TELEGRAM_CHANNEL_ID_REPORT_ALARM        = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
    PROJECT_DIR                             = os.getenv('PROJECT_DIR')
    HOME_DIR                                = os.getenv('HOME_DIR')
    JSON_DIR                                = os.getenv('JSON_DIR')
else:
    TELEGRAM_BOT_TOKEN_PROD                 = os.getenv('TELEGRAM_BOT_TOKEN_PROD')
    TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET  = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
    TELEGRAM_CHANNEL_ID_REPORT_ALARM        = os.getenv('TELEGRAM_CHANNEL_ID_REPORT_ALARM')
    PROJECT_DIR                             = os.getenv('PROJECT_DIR')
    HOME_DIR                                = os.getenv('HOME_DIR')
    JSON_DIR                                = os.getenv('JSON_DIR')

def NAVER_52weekPrice_check():
    requests.packages.urllib3.disable_warnings()

    # 네이버 증권 URL과 제목을 묶어서 리스트로 관리
    TARGETS = [
        ('https://m.stock.naver.com/api/stocks/high52week/KOSPI?page=1&pageSize=100', '코스피 52주 신고가'),
        ('https://m.stock.naver.com/api/stocks/high52week/KOSDAQ?page=1&pageSize=100', '코스닥 52주 신고가'),
        ('https://m.stock.naver.com/api/stocks/low52week/KOSPI?page=1&pageSize=100', '코스피 52주 신저가'),
        ('https://m.stock.naver.com/api/stocks/low52week/KOSDAQ?page=1&pageSize=100', '코스닥 52주 신저가')
    ]

    sendMessageText = ''

    # URL GET
    for TARGET_URL, title in TARGETS:
        try:
            # 메시지 제목 생성
            sendMessageText += f"\n\n ● {title}\n"
            sendMessageText += NAVER_52weekPrice_parse(TARGET_URL)

            # 3500자 이상이면 중간 발송
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                asyncio.run(sendMessage(sendMessageText))  # 봇 실행
                sendMessageText = ''  # 발송 후 초기화

        except Exception as e:
            print(f"에러 발생: {e}")
    
    # 반복문 종료 후 sendMessageText에 남은 값이 있으면 발송
    if sendMessageText:
        asyncio.run(sendMessage(sendMessageText))  # 봇 실행

    return sendMessageText


# JSON API 타입
def NAVER_52weekPrice_parse(TARGET_URL):
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode != 200 :return print("네이버 레포트 접속이 원활하지 않습니다 ")

    try: jres = json.loads(response.read().decode('utf-8'))
    except: return True
    # print(jres['totalCount'])

    total_count = int(jres['totalCount'])
    page_size = int(jres['pageSize'])
    total_pages = (total_count + page_size - 1) // page_size  # 올림 계산

    # URL 파싱
    parsed_url = urllib.parse.urlparse(TARGET_URL)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    sendMessageText = ''
    for page in range(1, total_pages + 1):
        
        query_params['page'] = page
        new_query_string = urlencode(query_params, doseq=True)
        new_url = urlunparse(parsed_url._replace(query=new_query_string))

        request = urllib.request.Request(new_url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(request)
        rescode = response.getcode()
        if rescode != 200:
            return f"Page {page} 접속이 원활하지 않습니다"

        try:
            jres = json.loads(response.read().decode('utf-8'))
        except: return ''
        
        for r in jres['stocks']:
            # print("r['stockName']", r['stockName'] , "int(r['itemCode'])" , int(r['itemCode']) ,  ('스팩' in r['stockName'] and int(r['itemCode']) >= 400000))
            if 'et' in r['stockEndType']  : continue
            if ('스팩' in r['stockName'] and
                int(r['itemCode']) >= 400000): continue # 스팩은 표시 안함
            
            sendMessageText += '{0} ({1}%)      [네이버]({2}) , [fnguide]({3})\n'.format(
                                r['stockName'], r['fluctuationsRatio'] , r['endUrl'], convert_stock_url(r['endUrl']) )

    return sendMessageText

def convert_stock_url(naver_url):
    # 네이버 주식 URL에서 주식 코드를 추출
    stock_code = naver_url.split('/')[-1]
    
    # FN가이드 주식 URL 생성
    fnguide_url = f"https://m.comp.fnguide.com/m2/company_01.asp?pGB=1&gicode=A{stock_code}"
    
    return fnguide_url
 
async def sendMessage(sendMessageText): #실행시킬 함수명 임의지정
    bot = telegram.Bot(token = TELEGRAM_BOT_TOKEN_PROD)
    return await bot.sendMessage(chat_id = TELEGRAM_CHANNEL_ID_REPORT_ALARM, text = sendMessageText, disable_web_page_preview = True, parse_mode = "Markdown")

if __name__ == "__main__":
    print("NAVER_52weekPrice_check()=> 새 게시글 정보 확인")  # 0
    NAVER_52weekPrice_check()