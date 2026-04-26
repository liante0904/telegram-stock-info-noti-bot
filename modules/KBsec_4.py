# -*- coding:utf-8 -*-
import os
import gc
import re
import sys
import urllib.parse as urlparse
import base64
import asyncio
from datetime import datetime
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper
from models.ConfigManager import config

# JSON API 타입
async def KB_checkNewArticle():
    json_data_list = []
    SEC_FIRM_ORDER = 4
    ARTICLE_BOARD_ORDER = 0

    urls = config.get_urls("KBsec_4")
    if not urls:
        logger.warning("No URLs found for KBsec_4")
        return []
    TARGET_URL = urls[0]

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    logger.debug(f"KB Scraper Start: {firm_info.get_firm_name()}")

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
    try:
        jres = await scraper.PostJson(json_data=payload)
        if not jres or 'response' not in jres or 'reportList' not in jres['response']:
            logger.warning(f"KB Scraper: No data found for {TARGET_URL}")
            return []

        soupList = jres['response']['reportList']
        logger.info(f"KB Scraper: Found {len(soupList)} articles")

        # JSON To List 변환
        for item in soupList:
            MKT_TP = "KR"
            if item.get('pCategoryid') == 26:
                MKT_TP = "GLOBAL"
            REG_DT = re.sub(r"[-./]", "", item.get('publicDate', ''))
            WRITER = item.get('analystNm', '')
            docTitle = item.get('docTitle', '')
            docTitleSub = item.get('docTitleSub', '')
            
            LIST_ARTICLE_TITLE = docTitleSub
            if docTitle and docTitle not in docTitleSub:
                LIST_ARTICLE_TITLE = f"{docTitle} : {docTitleSub}"
            
            document_id = item.get('documentid')
            LIST_ARTICLE_URL = f"http://rdata.kbsec.com/pdf_data/{document_id}.pdf"
            
            json_data_list.append({
                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                "FIRM_NM": firm_info.get_firm_name(),
                "REG_DT": REG_DT,
                "WRITER": WRITER,
                "ATTACH_URL": LIST_ARTICLE_URL,
                "DOWNLOAD_URL": LIST_ARTICLE_URL,
                "TELEGRAM_URL": LIST_ARTICLE_URL,
                "PDF_URL": LIST_ARTICLE_URL,
                "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                "MKT_TP": MKT_TP,
                "KEY": LIST_ARTICLE_URL,
                "SAVE_TIME": datetime.now().isoformat()
            })
    except Exception as e:
        logger.error(f"Error scraping KB Securities: {e}")

    # 메모리 정리
    gc.collect()
    return json_data_list

# KB증권 암호화 해제 (Legacy or Utility)
def KB_decode_url(url):
    url = url.replace('&amp;', '&')
    parsed_url = urlparse.urlparse(url)
    query_params = urlparse.parse_qs(parsed_url.query)

    id_value = query_params.get('id', [None])[0]
    encoded_url = query_params.get('url', [None])[0]

    if id_value is None or encoded_url is None:
        logger.warning('Invalid URL for decoding: id or url is missing')
        return "Invalid URL: id or url is missing"

    try:
        encoded_url = encoded_url.replace('&amp;', '&')
        decoded_url = base64.b64decode(encoded_url).decode('utf-8')
        logger.debug(f"Extracted id: {id_value}, Decoded URL: {decoded_url}")
        return decoded_url
    except Exception as e:
        logger.error(f"Error decoding url: {e}")
        return f"Error decoding url: {e}"

# Main function to run the code
async def main():
    result = await KB_checkNewArticle()
    logger.info(f"Total articles fetched: {len(result)}")
    for item in result[:5]:
        logger.debug(item)

# 비동기 함수 실행
if __name__ == "__main__":
    asyncio.run(main())
