# -*- coding:utf-8 -*- 
import os
import gc
import requests
import re
from datetime import datetime
import sys
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.WebScraper import SyncWebScraper
from models.SQLiteManager import SQLiteManager

def Miraeasset_checkNewArticle():
    SEC_FIRM_ORDER      = 8
    ARTICLE_BOARD_ORDER = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    # 미래에셋 Daily
    TARGET_URL_0 = "REMOVED"
    TARGET_URL_TUPLE = (TARGET_URL_0, )
    
    for idx, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=SEC_FIRM_ORDER,
            article_board_order=idx
        )
        logger.debug(f"MiraeAsset Scraper: Fetching {firm_info.get_board_name()}")
        
        scraper = SyncWebScraper(TARGET_URL, firm_info)
        soup = scraper.Get()
        if not soup:
            logger.error(f"MiraeAsset Scraper: Failed to get content from {TARGET_URL}")
            continue

        # 첫 번째 레코드의 제목을 바로 담습니다.
        soupList = soup.select("tbody tr")[2:]  # 타이틀 제거
        logger.info(f"MiraeAsset Scraper: Found {len(soupList)} potential articles.")

        for list_item in soupList:
            try:
                REG_DT = list_item.select_one("td:nth-child(1)").get_text(strip=True) # 날짜
                REG_DT = re.sub(r"[-./]", "", REG_DT) # 날짜 포맷 정리
                
                LIST_ARTICLE_TITLE = list_item.select_one("td:nth-child(2)").get_text(strip=True) # 제목
                WRITER = list_item.select_one("td:nth-child(4)").get_text(strip=True) # 작성자
                
                LIST_ARTICLE_URL = "없음"
                DOWNLOAD_URL = "없음"
                attachment_element = list_item.select_one(".bbsList_layer_icon a")
                
                if attachment_element:
                    match = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"])
                    if match:
                        LIST_ARTICLE_URL = match.group(1)
                        
                    title_nodes = list_item.select(".subject a")
                    if title_nodes:
                        LIST_ARTICLE_TITLE = " : ".join([node.get_text(strip=True) for node in title_nodes])
                    DOWNLOAD_URL = LIST_ARTICLE_URL

                json_data_list.append({
                    "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                    "ARTICLE_BOARD_ORDER": idx,
                    "FIRM_NM": firm_info.get_firm_name(),
                    "REG_DT": REG_DT,
                    "WRITER": WRITER,
                    "DOWNLOAD_URL": DOWNLOAD_URL,
                    "TELEGRAM_URL": DOWNLOAD_URL,
                    "ARTICLE_TITLE": LIST_ARTICLE_TITLE,
                    "SAVE_TIME": datetime.now().isoformat(),
                    "KEY": DOWNLOAD_URL
                })
            except Exception as e:
                logger.error(f"Error parsing MiraeAsset article row: {e}")
                continue

    # 메모리 정리
    gc.collect()
    return json_data_list

if __name__ == "__main__":
    result = Miraeasset_checkNewArticle()
    if not result:
        logger.warning("No articles found.")
    else:
        logger.info(f"Scraped {len(result)} articles.")
        db = SQLiteManager()
        inserted_count, updated_count = db.insert_json_data_list(result)
        logger.success(f"DB Sync: {inserted_count} new, {updated_count} updated.")
