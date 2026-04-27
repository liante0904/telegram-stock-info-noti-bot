# -*- coding:utf-8 -*-
import os
import sys
import asyncio
import aiohttp
import datetime
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config

# 주말이 아닌 평일을 확인하는 함수
def is_weekday(date_obj: datetime.datetime):
    return date_obj.weekday() < 5  # 월=0, 금=4, 토=5, 일=6

# 시작일부터 종료일까지 평일 리스트 생성
def generate_workdays(start_date: datetime.datetime, end_date: datetime.datetime):
    current_date = start_date
    weekdays = []
    while current_date <= end_date:
        if is_weekday(current_date):
            weekdays.append(current_date.strftime('%Y%m%d'))
        current_date += datetime.timedelta(days=1)
    return weekdays

async def NHQV_checkNewArticle(target_date=None):
    json_data_list = []
    sec_firm_order = 2
    article_board_order = 0

    urls = config.get_urls("NHQV_2")
    if not urls:
        logger.warning("No URLs found for NHQV_2")
        return []
    TARGET_URL = urls[0]
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }

    # 기본적으로 target_date가 없으면 현재 날짜로 설정
    if target_date is None:
        KST = datetime.timezone(datetime.timedelta(hours=9))
        now_kst = datetime.datetime.now(KST)
        current_weekday = now_kst.weekday()
        if current_weekday == 5:  # 토요일인 경우
            target_date = (now_kst + datetime.timedelta(days=2)).strftime('%Y%m%d')
        elif current_weekday == 6:  # 일요일인 경우
            target_date = (now_kst + datetime.timedelta(days=1)).strftime('%Y%m%d')
        else:
            target_date = now_kst.strftime('%Y%m%d')

    firm_info = FirmInfo(
        sec_firm_order=sec_firm_order,
        article_board_order=article_board_order
    )
    logger.debug(f"NHQV Scraper Start: {firm_info.get_firm_name()} for date {target_date}")

    payload = {
        "trName": "H3211",
        "rshPprDruTmSt": "00000000",
        "rshPprDruDtSt": target_date,
        "rshPprDruDtEd": target_date,
        "rshPprNo": ""
    }

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.post(TARGET_URL, headers=headers, data=payload) as response:
                    response.raise_for_status()
                    jres = await response.json()
            except Exception as e:
                logger.error(f"Error fetching NHQV articles for {target_date}: {e}")
                return []

            # 새 게시글 수 확인
            try:
                new_article_count = int(jres['H3211']['H3211OutBlock1'][0]['iqrCnt'])
                if new_article_count == 0:
                    logger.info(f"NHQV Scraper: No articles found for {target_date}")
                    break

                # 새로운 글 목록 가져오기
                articles = jres['H3211']['H3211OutBlock2']
                logger.info(f"NHQV Scraper: Found {len(articles)} articles for {target_date}")
                
                for article in articles:
                    url = article.get('hpgeFleUrlCts')
                    json_data_list.append({
                        "sec_firm_order": sec_firm_order,
                        "article_board_order": article_board_order,
                        "FIRM_NM": firm_info.get_firm_name(),
                        "REG_DT": article['rshPprDruDtNm'].replace(".", ""),
                        "WRITER": article['rshPprDruEmpFnm'],
                        "TELEGRAM_URL": url,
                        "PDF_URL": url,
                        "ARTICLE_TITLE": article['rshPprTilCts'],
                        "KEY": url,
                        "SAVE_TIME": datetime.datetime.now().isoformat()
                    })

                # 연속키 확인 (NH는 페이지당 최대 11개인 것으로 보임)
                if new_article_count >= 11:
                    payload['rshPprNo'] = articles[-1]['rshPprNo']
                    logger.debug("NHQV Scraper: Fetching next page via continuous key...")
                else:
                    break
            except (KeyError, IndexError) as e:
                logger.error(f"Unexpected JSON structure from NHQV: {e}")
                break

    return json_data_list

async def main():
    target_date = datetime.datetime.now().strftime('%Y%m%d')
    result = await NHQV_checkNewArticle(target_date)
    logger.info(f"Total NHQV articles fetched: {len(result)}")
    for item in result[:5]:
        logger.debug(item)

if __name__ == "__main__":
    asyncio.run(main())
