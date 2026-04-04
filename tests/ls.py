import os
import gc
import logging
import json
import re
import urllib.parse as urlparse
import urllib.request
import asyncio
import aiohttp
from datetime import datetime, timedelta, date
import time

from bs4 import BeautifulSoup
from models.FirmInfo import FirmInfo
from models.WebScraper import AsyncWebScraper  # 비동기 웹 스크래퍼가 필요합니다.
from models.SQLiteManager import SQLiteManager
from package.json_to_sqlite import insert_json_data_list

async def fetch_html(session, url):
    async with session.get(url, ssl=False) as response:
        return await response.text()

async def LS_checkNewArticle():
    db_manager = SQLiteManager()
    json_data_list = []
    SEC_FIRM_ORDER = 0
    FIRM_NM = "LS증권"

    TARGET_URLS = [
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED',
        'REMOVED'
    ]

    async with aiohttp.ClientSession() as session:
        for ARTICLE_BOARD_ORDER, base_url in enumerate(TARGET_URLS):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )

            page = 1
            while True:
                if ARTICLE_BOARD_ORDER == 0:
                    print(f"{ARTICLE_BOARD_ORDER}는 이제 그만함")
                    break
                if page == 20:
                    break

                TARGET_URL = f"{base_url}&currPage={page}"
                html = await fetch_html(session, TARGET_URL)
                soup = BeautifulSoup(html, 'html.parser')

                if soup.select_one(".no_data") and "등록된 데이터가 없습니다." in soup.select_one(".no_data").text:
                    print(f"{TARGET_URL}: 등록된 데이터가 없으므로 종료합니다.")
                    break

                soupList = soup.select('#contents > table > tbody > tr')
                today = date.today()
                seven_days_ago = today - timedelta(days=7)

                for item in soupList:
                    str_txt = item.get_text()
                    if "등록된 데이터가 없습니다." in str_txt:
                        print("등록된 데이터가 없습니다.")
                        break

                    str_date = item.select('td')[3].get_text().strip()
                    post_date_obj = datetime.strptime(str_date, '%Y.%m.%d').date()

                    link_element = item.select_one('a')
                    LIST_ARTICLE_URL = 'https://www.ls-sec.co.kr/EtwFrontBoard/' + link_element['href'].replace("amp;", "")
                    LIST_ARTICLE_TITLE = link_element.get_text().strip().replace("...", "")
                    WRITER = item.select('td')[2].get_text().strip()
                    REG_DT = post_date_obj.strftime('%Y%m%d')

                    select_query = """
                    SELECT * FROM data_main_daily_send 
                    WHERE KEY like '%upload% AND 'FIRM_NM = ? AND ARTICLE_TITLE LIKE ? LIMIT 1
                    """
                    params = (FIRM_NM, f"%{LIST_ARTICLE_TITLE}%")
                    print(params)
                    result = db_manager.execute_query(select_query, params)

                    if result and "status" not in result:
                        record_id = result[0]['report_id']
                        update_query = """
                        UPDATE data_main_daily_send 
                        SET REG_DT = ?, KEY = ? 
                        WHERE report_id = ?
                        """
                        db_manager.execute_query(update_query, (REG_DT, LIST_ARTICLE_URL, record_id))
                        print(f"Updated record with report_id {record_id}: REG_DT={REG_DT}, KEY={LIST_ARTICLE_URL}")

                page += 1
                print(f"{page} 진행중...")
                await asyncio.sleep(0.5)

    gc.collect()
    return json_data_list

async def main():
    await LS_checkNewArticle()

if __name__ == "__main__":
    asyncio.run(main())
