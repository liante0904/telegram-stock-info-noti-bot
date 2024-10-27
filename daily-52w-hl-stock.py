# -*- coding:utf-8 -*- 
import requests
import urllib.request
import json
from urllib.parse import urlencode, urlunparse
from models.SecretKey import SecretKey
from utils.telegram_util import sendMarkDownText
import asyncio

SECRET_KEY = SecretKey()

async def NAVER_52weekPrice_check():
    requests.packages.urllib3.disable_warnings()

    # 네이버 증권 URL과 제목을 묶어서 리스트로 관리
    TARGETS = [
        ('https://m.stock.naver.com/api/stocks/high52week/KOSPI?page=1&pageSize=100', '코스피 52주 신고가'),
        ('https://m.stock.naver.com/api/stocks/high52week/KOSDAQ?page=1&pageSize=100', '코스닥 52주 신고가'),
        ('https://m.stock.naver.com/api/stocks/low52week/KOSPI?page=1&pageSize=100', '코스피 52주 신저가'),
        ('https://m.stock.naver.com/api/stocks/low52week/KOSDAQ?page=1&pageSize=100', '코스닥 52주 신저가')
    ]

    for TARGET_URL, title in TARGETS:
        sendMessageText = ''
        try:
            sendMessageText += NAVER_52weekPrice_parse(TARGET_URL)

            # 3500자씩 발송 (각 줄 단위로 나누기)
            await sendMessageInChunks(sendMessageText, title)
            sendMessageText = ''  # 발송 후 초기화

        except Exception as e:
            print(f"에러 발생: {e}")

async def sendMessageInChunks(message, title):
    chunk = f"\n\n ● {title}\n"  # 각 청크에 항상 제목이 포함되도록 초기화
    for line in message.splitlines(keepends=True):
        # 현재 줄을 추가해도 3500자를 넘지 않으면 추가
        if len(chunk) + len(line) <= 3500:
            chunk += line
        else:
            # 청크가 3500자를 넘으면 발송
            await sendMarkDownText(
                token=SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET,
                chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM,
                sendMessageText=chunk
            )
            # 새로운 청크에 타이틀을 추가하여 초기화
            chunk = f"\n\n ● {title}\n" + line

    # 남은 메시지 발송
    if chunk:
        await sendMarkDownText(
            token=SECRET_KEY.TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET,
            chat_id=SECRET_KEY.TELEGRAM_CHANNEL_ID_REPORT_ALARM,
            sendMessageText=chunk
        )


# JSON API 타입
def NAVER_52weekPrice_parse(TARGET_URL):
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode != 200:
        return "네이버 레포트 접속이 원활하지 않습니다 "

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return ''
    
    total_count = int(jres['totalCount'])
    page_size = int(jres['pageSize'])
    total_pages = (total_count + page_size - 1) // page_size

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
        except:
            return ''
        
        for r in jres['stocks']:
            if 'et' in r['stockEndType']:
                continue
            if '스팩' in r['stockName'] and int(r['itemCode']) >= 400000:
                continue

            sendMessageText += '{0} ({1}%)      [네이버]({2}) , [fnguide]({3})\n'.format(
                                r['stockName'], r['fluctuationsRatio'], r['endUrl'], convert_stock_url(r['endUrl'])
            )

    return sendMessageText
def convert_stock_url(naver_url):
    # 네이버 주식 URL에서 주식 코드를 추출
    stock_code = naver_url.split('/')[-1]
    # FN가이드 주식 URL 생성
    fnguide_url = f"https://m.comp.fnguide.com/m2/company_01.asp?pGB=1&gicode=A{stock_code}"
    return fnguide_url
 
if __name__ == "__main__":
    print("NAVER_52weekPrice_check()=> 새 게시글 정보 확인")  # 0
    asyncio.run(NAVER_52weekPrice_check())