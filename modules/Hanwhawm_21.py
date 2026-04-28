# -*- coding:utf-8 -*-
import os
import urllib.parse
import aiohttp
import datetime
from xml.etree import ElementTree as ET
import sys
import asyncio
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config

def get_start_of_year():
    return datetime.datetime(datetime.datetime.now().year, 1, 1).strftime("%Y%m%d")

async def Hanwha_checkNewArticle(stdate=None, eddate=None, page_size=100):
    if stdate is None:
        stdate = get_start_of_year()
    if eddate is None:
        KST = datetime.timezone(datetime.timedelta(hours=9))
        eddate = datetime.datetime.now(KST).strftime("%Y%m%d")
    if page_size is None:
        page_size = 1000

    sec_firm_order = 21
    article_board_order = 0
    firm_info = FirmInfo(
        sec_firm_order=sec_firm_order,
        article_board_order=article_board_order
    )
    logger.debug(f"Hanwha Scraper Start: {firm_info.get_firm_name()}")
    
    json_data_list = []

    BASE_URL = config.get_urls("Hanwhawm_21")[0]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"}

    async def fetch_data(session, page_val):
        params = {
            "pageSize": page_size,
            "mode": "depth2",
            "ch_gbn": "iOS",
            "pageVal": page_val
        }
        query_string = urllib.parse.urlencode(params)
        full_url = f"{BASE_URL}?{query_string}"

        try:
            async with session.get(full_url, headers=headers) as response:
                if response.status != 200:
                    logger.warning(f"Hanwha Request failed for page {page_val}: {response.status}")
                    return []
                xml_text = await response.text()
                return parse_xml(xml_text)
        except Exception as e:
            logger.error(f"HTTP request failed for page {page_val}: {e}")
            return []

    def parse_xml(xml_text):
        try:
            root = ET.fromstring(xml_text)
            articles = []
            for block in root.findall(".//block1"):
                try:
                    reg_date = block.find("dt_regdate").text or ""
                    reg_date = reg_date.replace("-", "").replace(".", "").replace("/", "")
                    depth3_id = block.find("depth3_id").text or ""
                    title = block.find("vc_title").text or "No Title"
                    writer = block.find("vc_penname").text or "Unknown"
                    file_name = block.find("fname").text or ""
                    store_name = block.find("sname").text or ""
                    dir_path = block.find("dir").text or ""
                    mkt_tp = "GLOBAL" if depth3_id == "anls19" else "KR"
                    
                    download_url = (
                        f"https://www.hanwhawm.com/main/common/common_file/fileView.cmd?category=1&getFD=2"
                        f"&file={urllib.parse.quote(file_name)}&store={urllib.parse.quote(store_name)}&dir={urllib.parse.quote(dir_path)}"
                        if file_name and store_name and dir_path else ""
                    )

                    articles.append({
                        "sec_firm_order": sec_firm_order,
                        "article_board_order": article_board_order,
                        "firm_nm": firm_info.get_firm_name(),
                        "reg_dt": reg_date,
                        "download_url": download_url,
                        "article_title": title,
                        "writer": writer,
                        "mkt_tp": mkt_tp,
                        "key": download_url,
                        "telegram_url": download_url,
                        "pdf_url": download_url,
                        "save_time": datetime.datetime.now().isoformat()
                    })
                except Exception as e:
                    continue
            return articles
        except Exception as e:
            logger.error(f"XML Parsing error: {e}")
            return []

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(session, page_val) for page_val in range(1, 6)]
        results = await asyncio.gather(*tasks)

    for result in results:
        if result:
            json_data_list.extend(result)

    logger.info(f"Hanwha Scraper: Found {len(json_data_list)} total articles")
    return json_data_list

if __name__ == "__main__":
    result = asyncio.run(Hanwha_checkNewArticle())
    logger.info(f"Total articles fetched: {len(result)}")
