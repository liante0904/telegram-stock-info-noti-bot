# -*- coding:utf-8 -*-
import os
import gc
import aiohttp
import asyncio
import re
from datetime import datetime
from xml.etree import ElementTree as ET

from models.SQLiteManager import SQLiteManager
from utils.date_util import GetCurrentDate

def get_start_of_year():
    return datetime(datetime.now().year, 1, 1).strftime("%Y%m%d")

async def Hanwha_checkNewArticle(stdate=None, eddate=None, page_size=100):
    if stdate is None:
        stdate = get_start_of_year()
    if eddate is None:
        eddate = GetCurrentDate("yyyymmdd")

    SEC_FIRM_ORDER = 20  # 한화투자증권 고유 ID
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    BASE_URL = "https://www.hanwhawm.com/service/mobileapp/researchListNew.cmd"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}

    async def fetch_data(page_val):
        params = {
            "pageSize": page_size,
            "depth2_id": "1002",  # Research depth ID
            "mode": "depth2",
            "ch_gbn": "iOS",
            "pageVal": page_val
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, params=params, headers=headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch data: HTTP {response.status}")
                    return []
                xml_text = await response.text()
                return parse_xml(xml_text)

    def parse_xml(xml_text):
        try:
            root = ET.fromstring(xml_text)
            articles = []

            for block in root.findall(".//block1"):
                try:
                    reg_date = re.sub(r"[-./]", "", block.find("dt_regdate").text)
                    title = block.find("vc_title").text
                    writer = block.find("vc_penname").text
                    file_name = block.find("fname").text
                    dir_path = block.find("dir").text
                    attach_url = f"https://www.hanwhawm.com/{dir_path}/{file_name}"
                    
                    articles.append({
                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                        "FIRM_NM": "한화투자증권",
                        "REG_DT": reg_date,
                        "ATTACH_URL": attach_url,
                        "DOWNLOAD_URL": attach_url,
                        "ARTICLE_TITLE": title,
                        "WRITER": writer,
                        "TELEGRAM_URL": attach_url,
                        "SAVE_TIME": datetime.now().isoformat()
                    })
                except Exception as e:
                    print(f"Error parsing block: {e}")
                    continue

            return articles
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            return []

    # Pagination 처리
    tasks = [fetch_data(page_val) for page_val in range(1, 6)]  # 예시: 1~5페이지 크롤링
    results = await asyncio.gather(*tasks)

    for result in results:
        json_data_list.extend(result)

    return json_data_list

if __name__ == "__main__":
    # Main function to set parameters
    stdate = None  # Default to system year start if None
    eddate = None  # Default to system date if None
    page_size = 100  # Default value

    # Run the async function with specified parameters
    result = asyncio.run(Hanwha_checkNewArticle(stdate, eddate, page_size))
    print(result)
    
    if not result:
        print("No articles found.")
    else:
        db = SQLiteManager()
        inserted_count = db.insert_json_data_list(result, 'data_main_daily_send')
        print(f"Inserted {inserted_count} articles.")
