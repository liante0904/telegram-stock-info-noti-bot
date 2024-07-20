import requests
import urllib.request
import json
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
TARGET_URL = 'https://m.stock.naver.com/api/stocks/high52week/KOSPI?page=1&pageSize=100'
parsed_url = urllib.parse.urlparse(TARGET_URL)
query_params = urllib.parse.parse_qs(parsed_url.query)
print(parsed_url,query_params )
def NAVER_52weekPrice_parse(ARTICLE_BOARD_ORDER, TARGET_URL):
    global NXT_KEY
    global TEST_SEND_YN

    # URL 파싱
    parsed_url = urllib.request.urlparse(TARGET_URL)
    query_params = urllib.request.parse_qs(parsed_url.query)
    print(parsed_url,query_params )
    # 첫 페이지 요청
    request = urllib.request.Request(TARGET_URL, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode != 200:
        return "네이버 레포트 접속이 원활하지 않습니다"

    try:
        jres = json.loads(response.read().decode('utf-8'))
    except:
        return True

    total_count = int(jres['totalCount'])
    page_size = int(jres['pageSize'])
    total_pages = (total_count + page_size - 1) // page_size  # 올림 계산

    sendMessageText = ''
    for page in range(1, total_pages + 1):
        # 페이지 파라미터 업데이트
        query_params['page'] = [str(page)]
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
            return True

        for r in jres['stocks']:
            # 데이터 처리 로직 (예: 종목명, 등락률, 링크 등)
            stock_name = r['stockName']
            fluctuations_ratio = r['fluctuationsRatio']
            end_url = r['endUrl']
            sendMessageText += f"종목명: {stock_name}\n등락률: {fluctuations_ratio}%\n링크: {end_url}\n\n"

    return sendMessageText

def NAVER_52weekPrice_check():
    global ARTICLE_BOARD_ORDER
    global SEC_FIRM_ORDER

    SEC_FIRM_ORDER      = 0
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    # 네이버 증권 52주 신고가 코스피
    TARGET_URL_0 = 'https://m.stock.naver.com/api/stocks/high52week/KOSPI?page=1&pageSize=100'
    # 네이버 증권 52주 신고가 코스닥
    TARGET_URL_1 = 'https://m.stock.naver.com/api/stocks/high52week/KOSDAQ?page=1&pageSize=100'
    # 네이버 증권 52주 신저가 코스피
    TARGET_URL_2 = 'https://m.stock.naver.com/api/stocks/low52week/KOSPI?page=1&pageSize=100'
    # 네이버 증권 52주 신저가 코스닥
    TARGET_URL_3 = 'https://m.stock.naver.com/api/stocks/low52week/KOSDAQ?page=1&pageSize=100'
        
    TARGET_URL_TUPLE = (TARGET_URL_0, TARGET_URL_1, TARGET_URL_2, TARGET_URL_3)

    sendMessageText = ''
    # URL GET
    for ARTICLE_BOARD_ORDER, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        try:
            sendMessageText += NAVER_52weekPrice_parse(ARTICLE_BOARD_ORDER, TARGET_URL)
            sendMessageText = ''
        except:
            if len(sendMessageText) > 3500:
                print("발송 게시물이 남았지만 최대 길이로 인해 중간 발송처리합니다. \n", sendMessageText)
                sendMessageText = ''

    return sendMessageText
