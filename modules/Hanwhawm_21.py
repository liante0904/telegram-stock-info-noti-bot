# -*- coding:utf-8 -*-
import os
import urllib.parse
import aiohttp
import asyncio
import re
from datetime import datetime
from xml.etree import ElementTree as ET
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.SQLiteManager import SQLiteManager
from utils.date_util import GetCurrentDate

def get_start_of_year():
    return datetime(datetime.now().year, 1, 1).strftime("%Y%m%d")

async def Hanwha_checkNewArticle(stdate=None, eddate=None, page_size=100):
    if stdate is None:
        stdate = get_start_of_year()
    if eddate is None:
        eddate = GetCurrentDate("yyyymmdd")
    if page_size is None:
        page_size = 1000
        
        

    print(stdate, eddate, page_size)
    SEC_FIRM_ORDER = 21  # 한화투자증권 고유 ID
    ARTICLE_BOARD_ORDER = 0
    firm_info = FirmInfo(
        sec_firm_order=SEC_FIRM_ORDER,
        article_board_order=ARTICLE_BOARD_ORDER
    )
    json_data_list = []

    BASE_URL = "https://www.hanwhawm.com/service/mobileapp/researchListNew.cmd"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}

    async def fetch_data(page_val):
        # Query string 생성
        params = {
            "pageSize": page_size,
            "depth2_id": "1002",  # Research depth ID
            "mode": "depth2",
            "ch_gbn": "iOS",
            "pageVal": page_val
        }

        # URL에 직접 쿼리 추가
        query_string = urllib.parse.urlencode(params)
        full_url = f"{BASE_URL}?{query_string}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(full_url, headers=headers) as response:
                    if response.status != 200:
                        print(f"Failed to fetch data: HTTP {response.status}")
                        return []
                    xml_text = await response.text()
                    return parse_xml(xml_text)
            except aiohttp.ClientError as e:
                print(f"HTTP request failed: {e}")
                return []


    def parse_xml(xml_text, firm_info=firm_info):
        try:
            root = ET.fromstring(xml_text)
            articles = []

            for block in root.findall(".//block1"):
                try:
                    reg_date = re.sub(r"[-./]", "", block.find("dt_regdate").text or "")
                    title = block.find("vc_title").text or "No Title"
                    writer = block.find("vc_penname").text or "Unknown"
                    file_name = block.find("fname").text or ""
                    store_name = block.find("sname").text or ""
                    dir_path = block.find("dir").text or ""

                    # URL 필드 검증 및 인코딩
                    attach_url = f"https://www.hanwhawm.com/{dir_path}/{file_name}" if file_name and dir_path else ""
                    download_url = (
                        f"https://www.hanwhawm.com/main/common/common_file/fileView.cmd?category=1&getFD=2"
                        f"&file={urllib.parse.quote(file_name)}&store={urllib.parse.quote(store_name)}&dir={urllib.parse.quote(dir_path)}"
                        if file_name and store_name and dir_path else ""
                    )

                    articles.append({
                        "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                        "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                        "FIRM_NM": firm_info.get_firm_name(),
                        "REG_DT": reg_date,
                        "ATTACH_URL": download_url,
                        "DOWNLOAD_URL": download_url,
                        "ARTICLE_TITLE": title,
                        "WRITER": writer,
                        "KEY": download_url,
                        "TELEGRAM_URL": download_url,
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
