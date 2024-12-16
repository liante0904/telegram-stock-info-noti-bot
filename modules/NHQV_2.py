# -*- coding:utf-8 -*- 
import os
import gc
import requests
import re
import sys
import asyncio
import aiohttp
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper
from utils.date_util import GetCurrentDate_NH
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper
from models.SQLiteManager import SQLiteManager

# 주말이 아닌 평일을 확인하는 함수
def is_weekday(date: datetime):
    return date.weekday() < 5  # 월=0, 금=4, 토=5, 일=6


# 시작일부터 종료일까지 평일 리스트 생성
def generate_workdays(start_date: datetime, end_date: datetime):
    current_date = start_date
    weekdays = []
    while current_date <= end_date:
        if is_weekday(current_date):
            weekdays.append(current_date.strftime('%Y%m%d'))
        current_date += timedelta(days=1)
    return weekdays


async def NHQV_checkNewArticle(target_date=None):
    json_data_list = []
    SEC_FIRM_ORDER = 2
    ARTICLE_BOARD_ORDER = 0

    TARGET_URL = 'https://m.nhqv.com/research/commonTr.json'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    
    # 기본적으로 target_date가 없으면 현재 날짜로 설정
    if target_date is None:
        target_date = GetCurrentDate_NH()
    
    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    
    payload = {
        "trName": "H3211",
        "rshPprDruTmSt": "00000000",
        "rshPprDruDtSt": target_date,
        "rshPprDruDtEd": target_date,
        "rshPprNo": ""
    }
    
    async with aiohttp.ClientSession() as session:
        scraper = AsyncWebScraper(target_url=TARGET_URL, headers=headers)
        while True:
            try:
                jres = await scraper.PostJson(session, params=payload, json_data=None)
            except Exception as e:
                print(f"Error fetching articles for {target_date}: {e}")
                return []

            # 새 게시글 수 확인
            new_article_count = int(jres['H3211']['H3211OutBlock1'][0]['iqrCnt'])
            if new_article_count == 0:
                break

            # 새로운 글 목록 가져오기
            articles = jres['H3211']['H3211OutBlock2']
            for article in articles:
                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": article['rshPprDruDtNm'].replace(".", ""),
                    "WRITER": article['rshPprDruEmpFnm'],
                    "TELEGRAM_URL": article['hpgeFleUrlCts'],
                    "ARTICLE_TITLE": article['rshPprTilCts'],
                    "KEY":article['hpgeFleUrlCts'],
                    "SAVE_TIME": datetime.now().isoformat()
                })

            # 연속키 확인
            if new_article_count == 11:
                payload['rshPprNo'] = articles[-1]['rshPprNo']
            else:
                break
    print(json_data_list)
    return json_data_list


async def main():
    start_date = datetime(2021, 1, 1)  # 2021년 초
    end_date = datetime(datetime.now().year, 9, 30)  # 올해 9월 말
    workdays = generate_workdays(start_date, end_date)

    all_results = []
    for workday in workdays:
        print(f"Fetching data for {workday}...")
        daily_results = await NHQV_checkNewArticle(workday)
        all_results.extend(daily_results)

    print(f"Total articles fetched: {len(all_results)}")
    db = SQLiteManager()
    inserted_count = db.insert_json_data_list(all_results, 'data_main_daily_send')  # 모든 데이터를 한 번에 삽입
    print(inserted_count)
    # 여기서 원하는 방식으로 데이터를 저장하거나 처리
    return all_results


if __name__ == "__main__":
    asyncio.run(main())
