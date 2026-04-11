# -*- coding:utf-8 -*- 
import gc
import aiohttp
import asyncio
import json
import re
from datetime import datetime

import os
import sys

from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper


async def Shinyoung_checkNewArticle():
    SEC_FIRM_ORDER      = 7
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    # 신영증권 리서치
    TARGET_URL = "https://www.shinyoung.com/Common/selectPaging/research_shinyoungData"

    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )

    # POST 요청을 보낼 데이터
    payload = {
        "KEYWORD": "",
        "rows": "50",
        "page": "1"
    }

    logger.debug(f"Shinyoung Scraper Start: {TARGET_URL}")
    async with aiohttp.ClientSession() as session:
        scraper = AsyncWebScraper(TARGET_URL)
        
        # HTML parse
        jres = await scraper.PostJson(session=session, params=payload)

        soupList = jres.get('rows', [])
        logger.info(f"Shinyoung Scraper: Found {len(soupList)} items")
        
        # JSON To List
        for item in soupList:
            MKT_TP              = "KR"    
            REG_DT              = re.sub(r"[-./]", "", item.get('APPDATE', ''))
            WRITER              = item.get('EMPNM', '')
            
            LIST_ARTICLE_URL = await Shinyoung_detail(session=session, SEQ=item.get('SEQ'), BBSNO=item.get('BBSNO'))
            LIST_ARTICLE_TITLE = item.get('TITLE', '')
            if "해외주식" in LIST_ARTICLE_TITLE :
                MKT_TP = "GLOBAL"
            DOWNLOAD_URL = LIST_ARTICLE_URL
            json_data_list.append({
                "SEC_FIRM_ORDER":SEC_FIRM_ORDER,
                "ARTICLE_BOARD_ORDER":ARTICLE_BOARD_ORDER,
                "FIRM_NM":firm_info.get_firm_name(),
                "ARTICLE_TITLE":LIST_ARTICLE_TITLE,
                "REG_DT":REG_DT,
                "WRITER":WRITER,
                "ATTACH_URL":LIST_ARTICLE_URL,
                "TELEGRAM_URL": DOWNLOAD_URL,
                "PDF_URL": DOWNLOAD_URL,
                "MKT_TP": MKT_TP,
                "KEY":LIST_ARTICLE_URL,
                "SAVE_TIME": datetime.now().isoformat()
            })
            

    # 메모리 정리
    gc.collect()
    return json_data_list

async def Shinyoung_detail(session, SEQ, BBSNO):
    # POST 요청에 사용할 URL
    url_pass = "https://www.shinyoung.com/Common/authTr/devPass"

    # 추가할 request header
    headers = {
        "Accept": "text/plain, */*; q=0.01",
        "Connection": "keep-alive",
        "Host": "www.shinyoung.com",
        "Origin": "https://www.shinyoung.com",
        "Referer": "https://www.shinyoung.com/?page=10078&head=0",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Google Chrome\";v=\"123\", \"Not:A-Brand\";v=\"8\", \"Chromium\";v=\"123\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\""
    }
    
    # POST 요청 보내기
    async with session.post(url_pass, headers=headers) as response:
        if response.status != 200:
            logger.error(f"Shinyoung Detail authTr/devPass failed: {response.status}")

    url_check = "https://www.shinyoung.com/Common/checkAuth"
    async with session.post(url_check, headers=headers) as response:
        if response.status != 200:
            logger.error(f"Shinyoung Detail checkAuth failed: {response.status}")

    url_path = "https://www.shinyoung.com/Common/authTr/downloadFilePath"
    data = {
        'SEQ': SEQ,
        'BBSNO': BBSNO
    }
    
    headers_path = headers.copy()
    headers_path["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

    async with session.post(url_path, data=data, headers=headers_path) as response:
        if response.status != 200:
            logger.error(f"Shinyoung Detail downloadFilePath failed: {response.status}")
        
        res_text = await response.text()
        jres = json.loads(res_text)
        
        base_url = 'https://www.shinyoung.com/files/'
        file_path = jres.get('FILEINFO', {}).get('FILEPATH', '')
        url = base_url + file_path
        return url

if __name__ == "__main__":
    asyncio.run(Shinyoung_checkNewArticle())
