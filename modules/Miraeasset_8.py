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
from models.db_factory import get_db
from models.ConfigManager import config

def Miraeasset_checkNewArticle():
    sec_firm_order      = 8
    article_board_order = 0
    json_data_list = []

    requests.packages.urllib3.disable_warnings()

    TARGET_URL_TUPLE = config.get_urls("Miraeasset_8")
    
    for idx, TARGET_URL in enumerate(TARGET_URL_TUPLE):
        firm_info = FirmInfo(
            sec_firm_order=sec_firm_order,
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
                reg_dt = list_item.select_one("td:nth-child(1)").get_text(strip=True) # 날짜
                reg_dt = re.sub(r"[-./]", "", reg_dt) # 날짜 포맷 정리
                
                LIST_ARTICLE_TITLE = list_item.select_one("td:nth-child(2)").get_text(strip=True) # 제목
                writer = list_item.select_one("td:nth-child(4)").get_text(strip=True) # 작성자
                
                LIST_ARTICLE_URL = "없음"
                download_url = "없음"
                attachment_element = list_item.select_one(".bbsList_layer_icon a")
                
                if attachment_element:
                    match = re.search(r"javascript:downConfirm\('(.*?)'", attachment_element["href"])
                    if match:
                        LIST_ARTICLE_URL = match.group(1)
                        
                    title_nodes = list_item.select(".subject a")
                    if title_nodes:
                        LIST_ARTICLE_TITLE = " : ".join([node.get_text(strip=True) for node in title_nodes])
                    download_url = LIST_ARTICLE_URL

                json_data_list.append({
                    "sec_firm_order": sec_firm_order,
                    "article_board_order": idx,
                    "firm_nm": firm_info.get_firm_name(),
                    "reg_dt": reg_dt,
                    "writer": writer,
                    "download_url": download_url,
                    "telegram_url": download_url,
                    "article_title": LIST_ARTICLE_TITLE,
                    "save_time": datetime.now().isoformat(),
                    "key": download_url
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
        db = get_db()
        inserted_count, updated_count = db.insert_json_data_list(result)
        logger.success(f"DB Sync: {inserted_count} new, {updated_count} updated.")
