import os
import gc
import aiohttp
import json
import asyncio
import re
import sys
from datetime import datetime
from loguru import logger

# FirmInfo 등을 위해 path 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.db_factory import get_db
from models.ConfigManager import config

sec_firm_order = 25

_ibk_urls = config.get_urls("IBKs_25")
URL_INFO = [
    {"name": "전략/시황", "url": _ibk_urls[0], "screen": "IKO010101", "path": "invreport"},
    {"name": "기업분석", "url": _ibk_urls[1], "screen": "IKO010201", "path": "busreport"},
    {"name": "산업분석", "url": _ibk_urls[2], "screen": "IKO010301", "path": "indreport"},
    {"name": "경제/채권", "url": _ibk_urls[3], "screen": "IKO010401", "path": "comment"},
    {"name": "해외기업분석", "url": _ibk_urls[4], "screen": "IKO010501", "path": "overseasreport", "menu_tp": "0"},
    {"name": "글로벌ETF", "url": _ibk_urls[5], "screen": "IKO010501", "path": "overseasreport", "menu_tp": "1"}
]

# 공통 헤더
BASE_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ko,en-US;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json; charset=UTF-8",
    "Origin": "https://m.ibks.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

async def fetch_data(session: aiohttp.ClientSession, url: str, headers: dict, payload: dict) -> dict:
    try:
        async with session.post(url, headers=headers, json=payload, timeout=15) as response:
            if response.status != 200:
                logger.warning(f"IBK request failed for {url} with status {response.status}")
                return {}
            response_text = await response.text()
            return json.loads(response_text)
    except Exception as e:
        logger.error(f"Error during request to {url}: {e}")
        return {}

async def process_reports(session: aiohttp.ClientSession, info: dict, page: int, board_idx: int):
    category_name = info["name"]
    target_url = info["url"]
    screen_code = info["screen"]
    
    firm_info = FirmInfo(sec_firm_order=sec_firm_order, article_board_order=board_idx)
    logger.debug(f"IBK Scraper: Processing [{category_name}] page {page}")
    
    headers = BASE_HEADERS.copy()
    headers["Referer"] = f"https://m.ibks.com/iko/{screen_code}.do"

    row_size = 50
    start_row = (page - 1) * row_size + 1
    end_row = page * row_size

    payload = {
        "screen": screen_code,
        "data": {
            "start_row": start_row,
            "end_row": end_row,
            "row_size": row_size,
            "pageNo": page,
            "search_value": ""
        }
    }

    if "menu_tp" in info:
        payload["data"]["menu_tp"] = info["menu_tp"]

    response = await fetch_data(session, target_url, headers, payload)
    if not response:
        return []

    report_list = response.get("data", {}).get("list", [])
    logger.info(f"IBK Scraper: Found {len(report_list)} articles for {category_name} page {page}")
    
    json_data_list = []

    for report in report_list:
        reg_dt = report.get('REG_DATE', '')
        reg_dt = re.sub(r"[-./]", "", reg_dt)
        
        file_name = report.get('ATTATCH1', '')
        gubun = report.get('GUBUN', '')
        
        if board_idx == 0:
            # 전략/시황 게시판은 대부분 invrespect 경로를 사용함 (DAIL, STRATEGY, MONT 등)
            path_name = 'invrespect'
        else:
            path_name = info["path"]

        LIST_ARTICLE_URL = f"https://download.ibks.com/emsdata/tradeinfo/{path_name}/{file_name}"
        
        article_title = report.get('TITLE', 'No Title').strip()
        writer = report.get('REG_NAME', '').strip()
        
        market_type = 'GLOBAL' if category_name in ["해외기업분석", "글로벌ETF"] else 'KR'
        
        json_data_list.append({
            "sec_firm_order": sec_firm_order,
            "article_board_order": board_idx,
            "firm_nm": firm_info.get_firm_name(),
            "reg_dt": reg_dt,
            "download_url": LIST_ARTICLE_URL,
            "article_title": article_title,
            "writer": writer,
            "telegram_url": LIST_ARTICLE_URL,
            "pdf_url": LIST_ARTICLE_URL,
            "key": LIST_ARTICLE_URL,
            "mkt_tp": market_type,
            "save_time": datetime.now().isoformat()
        })

    return json_data_list

async def IBK_checkNewArticle(page=1, board_idx=None, full_fetch=False):
    """
    IBK투자증권 새 게시글 확인
    """
    async with aiohttp.ClientSession() as session:
        all_results = []
        
        for idx, info in enumerate(URL_INFO):
            if board_idx is not None and idx != board_idx:
                continue

            if full_fetch:
                current_page = 1
                while True:
                    logger.debug(f"IBK Full Fetch: {info['name']} page {current_page}")
                    results = await process_reports(session, info, current_page, idx)
                    if not results:
                        break
                    all_results.extend(results)
                    current_page += 1
                    gc.collect()
            else:
                results = await process_reports(session, info, page, idx)
                all_results.extend(results)
                gc.collect()

    return all_results

async def main():
    board_idx = None
    full_fetch = False
    
    if len(sys.argv) > 1:
        try:
            board_idx = int(sys.argv[1])
            full_fetch = True
        except (ValueError, IndexError):
            logger.error("Usage: python3 modules/IBKs_25.py [board_index(0-5)]")
            return

    result = await IBK_checkNewArticle(board_idx=board_idx, full_fetch=full_fetch)
    logger.info(f"Total IBK articles fetched: {len(result)}")
    
    if result:
        db = get_db()
        inserted, updated = db.insert_json_data_list(result)
        logger.success(f"IBK: Done. Inserted {inserted}, Updated {updated}.")

if __name__ == '__main__':
    asyncio.run(main())
