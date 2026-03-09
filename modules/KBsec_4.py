# -*- coding:utf-8 -*-
import os
import gc
import re
import sys
import urllib.parse as urlparse
import base64
import asyncio
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper

# JSON API 타입
async def KB_checkNewArticle():
    json_data_list = []
    SEC_FIRM_ORDER = 4
    ARTICLE_BOARD_ORDER = 0

    # KB증권 오늘의 레포트
    TARGET_URL = 'https://rc.kbsec.com/ajax/categoryReportList.json'

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )

    # 요청 payload 데이터
    payload = {
        "pageNo": 1,
        "pageSize": 500,
        "registdateFrom": datetime(datetime.now().year, 1, 1).strftime("%Y%m%d"),
        "registdateTo": datetime.now().strftime("%Y%m%d"),
        "templateid": "",
        "lowTempId": "",
        "folderid": "",
        "callGbn": "RCLIST"
    }

    # 비동기 스크래퍼 인스턴스 생성 및 요청 수행
    scraper = AsyncWebScraper(TARGET_URL)
    jres = await scraper.PostJson(json_data=payload)

    # JSON 응답 처리
    soupList = jres['response']['reportList']
    nNewArticleCnt = 0

    # JSON To List 변환
    for item in soupList:
        print(item['pCategoryid'], item['docTitle'], item['docTitleSub'], item['publicDate'], item['documentid'])
        
        MKT_TP = "KR"
        if item['pCategoryid'] == 26:
            MKT_TP = "GLOBAL"
        REG_DT = re.sub(r"[-./]", "", item['publicDate'])
        WRITER = item['analystNm']
        LIST_ARTICLE_TITLE = item['docTitleSub']
        if item['docTitle'] not in item['docTitleSub']:
            LIST_ARTICLE_TITLE = f"{item['docTitle']} : {item['docTitleSub']}"
        LIST_ARTICLE_URL = f"http://rdata.kbsec.com/pdf_data/{item['documentid']}.pdf"
        json_data_list.append({
            "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
            "FIRM_NM": firm_info.get_firm_name(),
            "REG_DT": REG_DT,
            "WRITER": WRITER,
            "ATTACH_URL": LIST_ARTICLE_URL,
            "DOWNLOAD_URL": LIST_ARTICLE_URL,
            "TELEGRAM_URL": LIST_ARTICLE_URL,
            "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
            "MKT_TP": MKT_TP,
            "KEY:": LIST_ARTICLE_URL,
            "SAVE_TIME": datetime.now().isoformat()
        })
        nNewArticleCnt += 1

    # 메모리 정리
    del soupList
    gc.collect()

    return json_data_list

# KB증권 암호화 해제
def KB_decode_url(url):
    url = url.replace('&amp;', '&')
    parsed_url = urlparse.urlparse(url)
    query_params = urlparse.parse_qs(parsed_url.query)

    id_value = query_params.get('id', [None])[0]
    encoded_url = query_params.get('url', [None])[0]

    if id_value is None or encoded_url is None:
        print('Invalid URL: id or url is missing')
        return "Invalid URL: id or url is missing"

    try:
        encoded_url = encoded_url.replace('&amp;', '&')
        decoded_url = base64.b64decode(encoded_url).decode('utf-8')
    except Exception as e:
        return f"Error decoding url: {e}"

    print(f"Extracted id: {id_value}, Decoded URL: {decoded_url}")
    return decoded_url

# Main function to run the code
async def main():
    json_data_list = await KB_checkNewArticle()
    print(f"New Article Count: {len(json_data_list)}")
    print("JSON Data List:")
    # for item in json_data_list:
    #     print(item)

# 비동기 함수 실행
if __name__ == "__main__":
    asyncio.run(main())
