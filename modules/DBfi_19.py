import asyncio
import aiohttp
import json
import ssl
from datetime import datetime
import os
import sys
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from models.FirmInfo import FirmInfo
from models.ConfigManager import config

BASE_URL = config.get_urls("DBfi_19")[0]
HEADERS_TEMPLATE = {
    "User-Agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148",
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}

# SSL 검증 완전히 비활성화
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.set_ciphers("DEFAULT")


# DB금융투자 기사 체크 함수
async def DBfi_checkNewArticle():
    SEC_FIRM_ORDER = 19
    urls = [
        "/appData/rsh_entr_lst.json",
        "/appData/rsh_bond_lst.json",
        "/appData/rsh_stock_lst.json"
    ]
    json_data_list = []

    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=timeout) as session:
        for ARTICLE_BOARD_ORDER, url_path in enumerate(urls):
            firm_info = FirmInfo(
                sec_firm_order=SEC_FIRM_ORDER,
                article_board_order=ARTICLE_BOARD_ORDER
            )
            headers = {
                **HEADERS_TEMPLATE,
                "Referer": f"{BASE_URL}/mre/mre_CompanyAll_lst.do",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }

            logger.debug(f"DBfi Scraper Start: {firm_info.get_firm_name()} path {url_path}")
            try:
                async with session.post(f"{BASE_URL}{url_path}", headers=headers) as response:
                    if response.status == 200:
                        try:
                            jres = await response.json()
                            data_items = jres.get("data", [])
                            logger.info(f"DBfi Scraper: Found {len(data_items)} items for {url_path}")
                        except (json.JSONDecodeError, KeyError):
                            logger.warning(f"No items found or JSON error for URL {url_path}.")
                            continue

                        for item in data_items:
                            detail_url = f"{BASE_URL}/appData/descRsh/{item['rid']}.json"
                            json_data_list.append({
                                "SEC_FIRM_ORDER": SEC_FIRM_ORDER,
                                "ARTICLE_BOARD_ORDER": ARTICLE_BOARD_ORDER,
                                "FIRM_NM": firm_info.get_firm_name(),
                                "REG_DT": item['rdt'][:8],
                                "ARTICLE_URL": "",
                                "TELEGRAM_URL": "",
                                "PDF_URL": "",
                                "ARTICLE_TITLE": item['tit'],
                                "WRITER": item['wnm'],
                                "CATEGORY": item['div'],
                                "KEY": detail_url,
                                "SAVE_TIME": datetime.now().isoformat()
                            })
                    else:
                        logger.warning(f"Failed to fetch page data for URL {url_path}. Status code: {response.status}")
            except Exception as e:
                logger.error(f"Network or timeout error while fetching {url_path}: {e}")

    return json_data_list


# 상세 URL로 후처리 데이터 획득 함수
async def fetch_detailed_url(articles):
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context), timeout=timeout) as session:
        for article in articles:
            key_url = article["KEY"]

            try:
                async with session.post(key_url, headers=HEADERS_TEMPLATE) as response:
                    if response.status == 200:
                        try:
                            detail_data = await response.json()
                            encoded_url = detail_data['data'].get("url", "")
                            telegram_url = f"https://whub.dbsec.co.kr/pv/gate?q={encoded_url}"
                            article["TELEGRAM_URL"] = telegram_url
                            article["PDF_URL"] = telegram_url
                            logger.debug(f"DBfi: Detailed URL fetched for {article['ARTICLE_TITLE']}")
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON for {key_url}")
                    else:
                        logger.warning(f"Failed to fetch details from {key_url}. Status code: {response.status}")
            except Exception as e:
                logger.error(f"Network or timeout error while fetching detailed URL: {e}")

    return articles


async def main():
    articles = await DBfi_checkNewArticle()
    detailed_articles = await fetch_detailed_url(articles)
    logger.info(f"Fetched total {len(detailed_articles)} detailed articles.")


if __name__ == "__main__":
    asyncio.run(main())
