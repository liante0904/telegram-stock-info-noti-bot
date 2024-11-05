# -*- coding:utf-8 -*- 
import os
import gc
import requests
import re
import sys
import asyncio
import aiohttp
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper
from utils.date_util import GetCurrentDate_NH


async def NHQV_checkNewArticle():
    json_data_list = []
    SEC_FIRM_ORDER = 2
    ARTICLE_BOARD_ORDER = 0

    requests.packages.urllib3.disable_warnings()

    TARGET_URL = 'https://m.nhqv.com/research/commonTr.json'
    
    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    
    payload = {
        "trName": "H3211",
        "rshPprDruTmSt": "00000000",
        "rshPprDruDtSt": GetCurrentDate_NH(),
        "rshPprDruDtEd": GetCurrentDate_NH(),
        "rshPprNo": ""
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }

    all_articles = []
    async with aiohttp.ClientSession() as session:
        scraper = AsyncWebScraper(target_url=TARGET_URL, headers=headers)
        while True:
            try:
                # JSON 포맷 없이 data로 payload 전송
                jres = await scraper.PostJson(session, params=payload, json_data=None)
                
            except Exception as e:
                print(f"Error fetching articles: {e}")
                return 0

            # 새 게시글 수 확인
            new_article_count = int(jres['H3211']['H3211OutBlock1'][0]['iqrCnt'])
            if new_article_count == 0:
                return new_article_count  # 새 글이 없으면 함수 종료

            # 새로운 글 목록 가져오기
            strList = jres['H3211']['H3211OutBlock2']
            all_articles.extend(strList)  # 누적하여 목록 저장
            
            # 연속키 확인 및 설정
            if new_article_count == 11:
                payload['rshPprNo'] = strList[-1]['rshPprNo']  # 마지막 글의 연속키 사용
            if new_article_count < 11:
                break  # 더 이상 글이 없으면 종료

    # 중복 제거
    unique_articles = [dict(t) for t in {tuple(d.items()) for d in all_articles}]

    # JSON 데이터 생성
    for article in unique_articles:
        REG_DT = re.sub(r"[-./]", "", article['rshPprDruDtNm'])
        WRITER = article['rshPprDruEmpFnm']
        LIST_ARTICLE_TITLE = article['rshPprTilCts']
        LIST_ARTICLE_URL = article['hpgeFleUrlCts']
        DOWNLOAD_URL = LIST_ARTICLE_URL
        
        json_data_list.append({
            "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
            "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
            "FIRM_NM": firm_info.get_firm_name(),
            "REG_DT": REG_DT,
            "WRITER": WRITER,
            "ATTACH_URL": LIST_ARTICLE_URL,
            "DOWNLOAD_URL": DOWNLOAD_URL,
            "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
            "SAVE_TIME": datetime.now().isoformat()
        })
            
    # 메모리 정리
    gc.collect()

    return json_data_list



async def main():
    result = await NHQV_checkNewArticle()
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
